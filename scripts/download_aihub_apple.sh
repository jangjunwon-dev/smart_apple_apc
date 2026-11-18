#!/usr/bin/env bash
# =============================================================================
# AI Hub 「농산물 품질(QC) 이미지」 — 사과(부사·양광) 파일만 받기 (WSL Ubuntu)
#
# 사용법:
#   bash scripts/download_aihub_apple.sh                 # 라벨 + 검증 이미지 (≈3.7GB)
#   bash scripts/download_aihub_apple.sh --train         # + 학습 이미지 (≈24.3GB 추가)
#   bash scripts/download_aihub_apple.sh --drive "/mnt/g/내 드라이브/smart_apple_apc/data/raw"
#                                                        # 받은 뒤 공유 드라이브 폴더로 복사
# 준비 (최초 1회):
#   1. aihub.or.kr 로그인 → 데이터 페이지(dataSetSn=149) → 다운로드(데이터 신청) → 승인
#   2. AI 데이터 찾기 → AI 허브 오픈 API → API key 발급 (회원 메일로 수신)
#   3. API key 는 실행 시 입력하거나 환경변수 AIHUB_APIKEY 로 전달 (파일에 저장 금지)
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/data/raw/aihub_qc_apple"
DATASET_KEY=149
GET_TRAIN=0
DRIVE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --train) GET_TRAIN=1; shift ;;
    --drive) DRIVE_DIR="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1"; exit 1 ;;
  esac
done

# 파일키|저장 하위폴더|파일명
FILES=(
  # 라벨(JSON) ≈14MB
  "396903|train/labels|Apple_fuji_L.zip"      "396904|train/labels|Apple_fuji_M.zip"
  "396905|train/labels|Apple_fuji_S.zip"      "396906|train/labels|Apple_yanggwang_L.zip"
  "396907|train/labels|Apple_yanggwang_M.zip" "396908|train/labels|Apple_yanggwang_S.zip"
  "397011|val/labels|Apple_fuji_L.zip"        "397012|val/labels|Apple_fuji_M.zip"
  "397013|val/labels|Apple_fuji_S.zip"        "397014|val/labels|Apple_yanggwang_L.zip"
  "397015|val/labels|Apple_yanggwang_M.zip"   "397016|val/labels|Apple_yanggwang_S.zip"
  # 검증 이미지 ≈3.7GB
  "397065|val/images|Apple_fuji_L.zip"        "397066|val/images|Apple_fuji_M.zip"
  "397067|val/images|Apple_fuji_S.zip"        "397068|val/images|Apple_yanggwang_L.zip"
  "397069|val/images|Apple_yanggwang_M.zip"   "397070|val/images|Apple_yanggwang_S.zip"
)
if [[ $GET_TRAIN -eq 1 ]]; then
  FILES+=(
    # 학습 이미지 ≈24.3GB
    "396957|train/images|Apple_fuji_L.zip"      "396958|train/images|Apple_fuji_M.zip"
    "396959|train/images|Apple_fuji_S.zip"      "396960|train/images|Apple_yanggwang_L.zip"
    "396961|train/images|Apple_yanggwang_M.zip" "396962|train/images|Apple_yanggwang_S.zip"
  )
fi

# --- 디스크 여유 확인 --------------------------------------------------------
NEED_GB=$([[ $GET_TRAIN -eq 1 ]] && echo 60 || echo 10)   # 다운로드+병합 여유분 포함
FREE_GB=$(df -BG --output=avail "$REPO_ROOT" | tail -1 | tr -dc '0-9')
if (( FREE_GB < NEED_GB )); then
  echo "[ERR] 디스크 여유 ${FREE_GB}GB < 필요 ${NEED_GB}GB. .wslconfig 또는 디스크 정리 필요"; exit 1
fi

# --- aihubshell 준비 ---------------------------------------------------------
AIHUBSHELL="$HOME/.local/bin/aihubshell"
if [[ ! -x "$AIHUBSHELL" ]]; then
  echo "[INFO] aihubshell 설치 → $AIHUBSHELL"
  mkdir -p "$(dirname "$AIHUBSHELL")"
  curl -fsSL -o "$AIHUBSHELL" https://api.aihub.or.kr/api/aihubshell.do
  chmod +x "$AIHUBSHELL"
fi

if [[ -z "${AIHUB_APIKEY:-}" ]]; then
  read -r -s -p "AI Hub API key (입력 내용은 보이지 않음): " AIHUB_APIKEY; echo
fi
[[ -n "$AIHUB_APIKEY" ]] || { echo "[ERR] API key 가 비어 있습니다"; exit 1; }

# --- 다운로드 → 분할 파일 병합 ----------------------------------------------
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$DEST"

for entry in "${FILES[@]}"; do
  IFS='|' read -r key sub name <<< "$entry"
  target="$DEST/$sub/$name"
  if [[ -s "$target" ]]; then echo "⏭  이미 있음: $sub/$name"; continue; fi

  echo "⬇  $sub/$name (filekey $key)"
  rm -rf "${WORK:?}"/*
  ( cd "$WORK" && "$AIHUBSHELL" -mode d -datasetkey "$DATASET_KEY" -filekey "$key" \
      -aihubapikey "$AIHUB_APIKEY" ) \
    || { echo "[ERR] 다운로드 실패 — 데이터 신청 승인·API key 확인"; exit 1; }

  mkdir -p "$(dirname "$target")"
  mapfile -d '' parts < <(find "$WORK" -name "${name}.part*" -print0 | sort -zV)
  if (( ${#parts[@]} > 0 )); then
    cat "${parts[@]}" > "${target}.tmp" && mv "${target}.tmp" "$target"
  else
    whole="$(find "$WORK" -name "$name" -print -quit)"
    [[ -n "$whole" ]] || { echo "[ERR] 받은 파일을 찾지 못함: $name"; exit 1; }
    mv "$whole" "$target"
  fi
  echo "✅ $target"
done
unset AIHUB_APIKEY

# --- 무결성 확인 -------------------------------------------------------------
echo; echo "=== 압축 파일 확인 ==="
command -v unzip >/dev/null || sudo apt install -y unzip
find "$DEST" -name '*.zip' | sort | while read -r z; do
  if unzip -tq "$z" >/dev/null 2>&1; then
    printf "✅ %-34s %6s개  %s\n" "${z#"$DEST"/}" "$(unzip -Z1 "$z" | grep -vc '/$')" "$(du -h "$z" | cut -f1)"
  else
    printf "❌ %-34s 손상 — 해당 파일 지우고 다시 실행\n" "${z#"$DEST"/}"
  fi
done

# --- 공유 드라이브로 복사 (선택) --------------------------------------------
if [[ -n "$DRIVE_DIR" ]]; then
  [[ -d "$DRIVE_DIR" ]] || { echo "[ERR] 드라이브 폴더 없음: $DRIVE_DIR"; exit 1; }
  echo; echo "[INFO] 공유 드라이브로 복사 → $DRIVE_DIR/aihub_qc_apple"
  mkdir -p "$DRIVE_DIR/aihub_qc_apple"
  cp -rnv "$DEST"/. "$DRIVE_DIR/aihub_qc_apple/" | tail -5
  echo "✅ 복사 완료 (Google Drive 앱이 업로드를 마칠 때까지 PC를 켜 두세요)"
fi
echo; echo "저장 위치: $DEST"
