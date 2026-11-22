#!/usr/bin/env bash
# =============================================================================
# Gazebo 시뮬레이션 성능 측정 스크립트 (Smart APC)
#
# 사용법:
#   bash scripts/bench_sim.sh <월드파일> <초> [gui|headless]
#   예) bash scripts/bench_sim.sh src/apc_simulation/worlds/apc_world.sdf 60 headless
#       bash scripts/bench_sim.sh apc_world_4lane_test.sdf 60 gui
#
# 하는 일:
#   1. sim.launch.py 로 월드 + 브리지 + 사과 스포너 실행
#   2. 워밍업(WARMUP 초, 기본 10) 후 <초> 동안 수집
#      - /world/<이름>/stats 의 real_time_factor (평균·최소)
#      - gz sim 프로세스(gz-sim-main) CPU% 평균, 메모리(RSS) 최대
#      - 시스템 전체 CPU 사용률 평균, 사용 중 메모리 최대 (free 의 used 기준)
#   3. PC 정보(CPU·코어·RAM·GPU 렌더러) 출력 → 팀원끼리 비교용
#   4. 실행한 프로세스 전부 종료
#
# 결과 저장: log/bench/<시각>_<월드>_<모드>/summary.txt (log/ 는 커밋 제외 폴더)
# 환경변수: WARMUP(기본 10초)
#           SIM_EXTRA: sim.launch.py 에 추가로 넘길 인자 (공백 구분)
#             예) SIM_EXTRA="spawn_amr:=false" bash scripts/bench_sim.sh apc_world.sdf 60 headless
#                 → AMR 로봇 없이 측정 (로봇 있을 때/없을 때 RTF 비교용)
# ※ WSL 에서는 ~/.bashrc 의 GALLIUM_DRIVER=d3d12 (GPU 렌더링) 가 적용된 터미널에서 실행할 것
# =============================================================================
set -uo pipefail

usage() {
  echo "사용법: bash scripts/bench_sim.sh <월드파일> <초> [gui|headless]" >&2
  exit 1
}

[[ $# -lt 2 || $# -gt 3 ]] && usage
WORLD_ARG="$1"
DURATION="$2"
MODE="${3:-gui}"
WARMUP="${WARMUP:-10}"
[[ "$DURATION" =~ ^[0-9]+$ && "$DURATION" -gt 0 ]] || { echo "❌ <초> 는 양의 정수" >&2; usage; }
[[ "$WARMUP" =~ ^[0-9]+$ ]] || { echo "❌ WARMUP 은 0 이상의 정수" >&2; exit 1; }
[[ "$MODE" == "gui" || "$MODE" == "headless" ]] || usage

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---------- 월드 파일 찾기 (경로 그대로 → worlds/ 안 이름 순) ----------
if [[ -f "$WORLD_ARG" ]]; then
  WORLD_FILE="$(realpath "$WORLD_ARG")"
elif [[ -f "$ROOT/src/apc_simulation/worlds/$WORLD_ARG" ]]; then
  WORLD_FILE="$ROOT/src/apc_simulation/worlds/$WORLD_ARG"
else
  echo "❌ 월드 파일을 찾을 수 없음: $WORLD_ARG" >&2
  exit 1
fi
WORLD_NAME="$(grep -oP '<world\s+name="\K[^"]+' "$WORLD_FILE" | head -1)"
[[ -n "$WORLD_NAME" ]] || { echo "❌ SDF 에서 <world name> 을 찾지 못함" >&2; exit 1; }

# ---------- ROS 환경 (setup.bash 는 미정의 변수를 쓰므로 source 동안 set -u 해제) ----------
set +u
# shellcheck disable=SC1091
source /opt/ros/lyrical/setup.bash
if [[ -f "$ROOT/install/setup.bash" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/install/setup.bash"
else
  echo "❌ install/setup.bash 없음 — 먼저 python -m colcon build --symlink-install" >&2
  exit 1
fi
set -u

# ---------- WSL GPU 렌더링 기본값 (이미 설정돼 있으면 그 값을 유지) ----------
# ~/.bashrc 는 대화형 셸에서만 읽히므로 다른 방식으로 실행해도 같은 조건으로 측정되게 함
if grep -qi microsoft /proc/version 2>/dev/null; then
  export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
  if command -v nvidia-smi >/dev/null 2>&1; then
    export MESA_D3D12_DEFAULT_ADAPTER_NAME="${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"
  fi
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

# ---------- 렌더러 확인: CPU(llvmpipe) 렌더링이면 경고 ----------
GPU=""
if command -v glxinfo >/dev/null 2>&1; then
  GPU="$(glxinfo -B 2>/dev/null | sed -n 's/^OpenGL renderer string: //p')"
fi
GPU="${GPU:-unknown}"
echo "🖥  렌더러: $GPU"
if [[ "$GPU" == *llvmpipe* ]]; then
  echo "⚠ CPU 렌더링 중 — 결과가 실제보다 느리게 나옴"
fi

# ---------- 사전 점검: 남아 있는 Gazebo 가 있으면 결과가 섞이므로 중단 ----------
if pgrep -f '[g]z-sim-main' >/dev/null; then
  echo "❌ 이미 실행 중인 Gazebo(gz-sim-main)가 있음 — 종료 후 다시 실행하세요:" >&2
  pgrep -fa '[g]z-sim-main' | cut -c1-150 >&2
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$ROOT/log/bench/${STAMP}_$(basename "$WORLD_FILE" .sdf)_${MODE}"
mkdir -p "$OUT_DIR"
LAUNCH_LOG="$OUT_DIR/launch.log"
STATS_LOG="$OUT_DIR/stats.jsonl"
SAMPLES="$OUT_DIR/samples.csv"
SUMMARY="$OUT_DIR/summary.txt"

LAUNCH_PID=""
STATS_PID=""

# ---------- 정리: 실행한 프로세스 그룹 전체 종료 ----------
cleanup() {
  trap - EXIT INT TERM
  [[ -n "$STATS_PID" ]] && kill "$STATS_PID" 2>/dev/null
  if [[ -n "$LAUNCH_PID" ]] && kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "⏹  시뮬레이션 종료 중..."
    kill -INT -- "-$LAUNCH_PID" 2>/dev/null
    for _ in $(seq 1 20); do
      kill -0 "$LAUNCH_PID" 2>/dev/null || break
      sleep 0.5
    done
    kill -KILL -- "-$LAUNCH_PID" 2>/dev/null
  fi
  # 그룹 밖으로 빠져나간 프로세스까지 확인 (이 월드 파일로 띄운 것만)
  sleep 1
  pkill -KILL -f "[g]z-sim-main.*$(basename "$WORLD_FILE")" 2>/dev/null
  pkill -KILL -f '[p]arameter_bridge.*apc_gz_bridge' 2>/dev/null
  pkill -KILL -f '[a]pple_spawner_node' 2>/dev/null
  pkill -KILL -f '[p]arameter_bridge.*amr_gz_bridge' 2>/dev/null
  pkill -KILL -f '[r]obot_state_publisher' 2>/dev/null
  if pgrep -f '[g]z-sim-main' >/dev/null; then
    echo "⚠️  gz-sim-main 이 남아 있음 — 직접 확인: pgrep -fa gz-sim-main"
  else
    echo "🧹 프로세스 정리 완료"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# ---------- 1. 실행 ----------
HEADLESS=false
[[ "$MODE" == "headless" ]] && HEADLESS=true
SIM_EXTRA="${SIM_EXTRA:-}"
read -r -a SIM_EXTRA_ARGS <<<"$SIM_EXTRA"
echo "▶  월드: $WORLD_FILE (world=$WORLD_NAME), 모드: $MODE, 측정: ${DURATION}s, 워밍업: ${WARMUP}s"
[[ -n "$SIM_EXTRA" ]] && echo "   추가 인자: $SIM_EXTRA"
setsid ros2 launch apc_simulation sim.launch.py \
  world:="$WORLD_FILE" headless:="$HEADLESS" "${SIM_EXTRA_ARGS[@]}" >"$LAUNCH_LOG" 2>&1 &
LAUNCH_PID=$!

echo "⏳ /world/$WORLD_NAME/stats 대기..."
READY=false
for _ in $(seq 1 30); do
  if timeout 3 gz topic -e -t "/world/$WORLD_NAME/stats" -n 1 >/dev/null 2>&1; then
    READY=true
    break
  fi
  kill -0 "$LAUNCH_PID" 2>/dev/null || break
  sleep 1
done
if [[ "$READY" != true ]]; then
  echo "❌ Gazebo 가 시작되지 않음 — 로그: $LAUNCH_LOG" >&2
  tail -20 "$LAUNCH_LOG" >&2
  exit 1
fi

# 4레인 시험 월드: 밀어내기 장치 왕복 순환 시작
# (gz topic -p 는 구독자 연결 전에 발행하면 메시지가 유실될 수 있음 → 순환 확인 후 재시도)
if grep -q '/apc/bench/tick' "$WORLD_FILE"; then
  TICK_OK=false
  for _ in $(seq 1 5); do
    gz topic -t /apc/bench/tick -m gz.msgs.Int32 -p 'data: 1'
    if timeout 4 gz topic -e -t /apc/bench/tick -n 2 >/dev/null 2>&1; then
      TICK_OK=true
      break
    fi
    sleep 1
  done
  if [[ "$TICK_OK" == true ]]; then
    echo "🔁 밀어내기 장치 왕복 시작 확인 (/apc/bench/tick)"
  else
    echo "❌ 밀어내기 장치 왕복이 시작되지 않음 — 측정 중단" >&2
    exit 1
  fi
fi

echo "🔥 워밍업 ${WARMUP}s..."
sleep "$WARMUP"

# ---------- 2. 수집 ----------
echo "📊 ${DURATION}s 동안 수집 중..."
SPAWN_BEFORE=$(grep -c ' 생성 (r=' "$LAUNCH_LOG")
REMOVE_BEFORE=$(grep -c ']: apple_[0-9]* 삭제' "$LAUNCH_LOG")
timeout "$DURATION" gz topic -e -t "/world/$WORLD_NAME/stats" --json-output >"$STATS_LOG" 2>/dev/null &
STATS_PID=$!

# 1초 간격 샘플링: gz-sim-main CPU%·RSS, 시스템 CPU%, 사용 메모리(free used = MemTotal - MemAvailable)
python3 -I - "$DURATION" "$SAMPLES" <<'PY'
import os
import sys
import time

duration, out_path = int(sys.argv[1]), sys.argv[2]
hz = os.sysconf('SC_CLK_TCK')


def gz_pids():
    pids = []
    for d in os.listdir('/proc'):
        if not d.isdigit():
            continue
        try:
            with open(f'/proc/{d}/cmdline', 'rb') as f:
                cmd = f.read().split(b'\0')[0]
        except OSError:
            continue
        if cmd.endswith(b'gz-sim-main'):
            pids.append(int(d))
    return pids


def proc_ticks(pid):
    try:
        with open(f'/proc/{pid}/stat') as f:
            fields = f.read().rsplit(')', 1)[1].split()
        return int(fields[11]) + int(fields[12])       # utime + stime
    except (OSError, IndexError):
        return None


def proc_rss_mb(pid):
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


def sys_cpu():
    with open('/proc/stat') as f:
        vals = [int(v) for v in f.readline().split()[1:]]
    idle = vals[3] + vals[4]                               # idle + iowait
    return sum(vals[:8]), idle


def mem_used_mb():
    info = {}
    with open('/proc/meminfo') as f:
        for line in f:
            k, v = line.split(':')
            info[k] = int(v.split()[0])
    return (info['MemTotal'] - info['MemAvailable']) / 1024


prev_t = time.monotonic()
prev_ticks = {p: proc_ticks(p) for p in gz_pids()}
prev_sys = sys_cpu()
with open(out_path, 'w') as out:
    out.write('t,gz_cpu_pct,gz_rss_mb,sys_cpu_pct,mem_used_mb,gz_procs\n')
    end = prev_t + duration
    while time.monotonic() < end:
        time.sleep(1.0)
        now = time.monotonic()
        dt = now - prev_t
        pids = gz_pids()
        ticks = {p: proc_ticks(p) for p in pids}
        gz_cpu = 0.0
        for p, t in ticks.items():
            if t is not None and prev_ticks.get(p) is not None:
                gz_cpu += (t - prev_ticks[p]) / hz / dt * 100
        rss = sum(proc_rss_mb(p) for p in pids)
        total, idle = sys_cpu()
        d_total, d_idle = total - prev_sys[0], idle - prev_sys[1]
        sys_pct = (1 - d_idle / d_total) * 100 if d_total > 0 else 0.0
        out.write(f'{now:.2f},{gz_cpu:.1f},{rss:.1f},{sys_pct:.1f},{mem_used_mb():.1f},'
                  f'{len(pids)}\n')
        out.flush()
        prev_t, prev_ticks, prev_sys = now, ticks, (total, idle)
PY
wait "$STATS_PID" 2>/dev/null
STATS_PID=""
SPAWNED=$(( $(grep -c ' 생성 (r=' "$LAUNCH_LOG") - SPAWN_BEFORE ))
REMOVED=$(( $(grep -c ']: apple_[0-9]* 삭제' "$LAUNCH_LOG") - REMOVE_BEFORE ))
SPAWNER_WARN=$(grep -c 'apple_spawner\]: .*\(건너뜀\|수명 초과\|실패\)' "$LAUNCH_LOG")

# ---------- 3. PC 정보 ----------
CPU_MODEL="$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -1)"
CORES="$(nproc)"
RAM_MB="$(free -m | awk '/^Mem:/{print $2}')"
OGRE_GPU="$(grep -h 'GL_RENDERER' ~/.gz/rendering/ogre2.log 2>/dev/null | tail -1 | sed 's/.*GL_RENDERER = //')"

# ---------- 4. 결과 ----------
python3 -I - "$STATS_LOG" "$SAMPLES" <<PY | tee "$SUMMARY"
import csv
import json
import sys

rtf = []
first = last = None
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if 'realTimeFactor' in m:
            rtf.append(float(m['realTimeFactor']))
        sim = m.get('simTime', {})
        real = m.get('realTime', {})
        pair = (int(sim.get('sec', 0)) + int(sim.get('nsec', 0)) * 1e-9,
                int(real.get('sec', 0)) + int(real.get('nsec', 0)) * 1e-9)
        first = first or pair
        last = pair

rows = list(csv.DictReader(open(sys.argv[2])))


def col(name):
    return [float(r[name]) for r in rows]


def avg(v):
    return sum(v) / len(v) if v else float('nan')


span_rtf = float('nan')
if first and last and last[1] > first[1]:
    span_rtf = (last[0] - first[0]) / (last[1] - first[1])

print('=' * 60)
print(' Smart APC 시뮬레이션 성능 측정 결과')
print('=' * 60)
print(f' 월드        : $(basename "$WORLD_FILE") (world=$WORLD_NAME)')
print(f' 모드        : $MODE   측정 ${DURATION}s (워밍업 ${WARMUP}s 제외)   시각 $STAMP')
print(f' 추가 인자   : ${SIM_EXTRA:-(없음)}')
print('-' * 60)
print(f' RTF 평균    : {avg(rtf):.3f}')
print(f' RTF 최소    : {min(rtf) if rtf else float("nan"):.3f}')
print(f' RTF 구간    : {span_rtf:.3f}   (sim 경과 / real 경과, 참고용)')
print(f' RTF 샘플 수 : {len(rtf)}')
print('-' * 60)
print(f' gz sim CPU 평균   : {avg(col("gz_cpu_pct")):.1f} %  (코어 1개 = 100%)')
print(f' gz sim 메모리 최대: {max(col("gz_rss_mb"), default=float("nan")):.0f} MB  (RSS 합계)')
print(f' 시스템 CPU 평균   : {avg(col("sys_cpu_pct")):.1f} %  (전체 코어 기준, 100% = 모두 사용)')
print(f' 사용 메모리 최대  : {max(col("mem_used_mb"), default=float("nan")):.0f} MB  (free used)')
print('-' * 60)
print(f' 사과 생성/삭제    : $SPAWNED / $REMOVED   (스포너 경고 누적 $SPAWNER_WARN 건)')
print('-' * 60)
print(' PC 정보')
print(f'  CPU   : $CPU_MODEL ($CORES 코어/스레드)')
print(f'  RAM   : $RAM_MB MB')
print(f'  GPU   : $GPU')
print(f'  Ogre  : ${OGRE_GPU:-unknown}  (Gazebo 마지막 렌더러 로그)')
print(f'  환경  : GALLIUM_DRIVER=${GALLIUM_DRIVER:-(없음)}  '
      f'MESA_D3D12_DEFAULT_ADAPTER_NAME=${MESA_D3D12_DEFAULT_ADAPTER_NAME:-(없음)}  '
      f'QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-(없음)}')
print(f'  커널  : $(uname -r)')
print('=' * 60)
print(f' 원본 로그: $OUT_DIR')
PY
