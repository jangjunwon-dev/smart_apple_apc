"""AMR 키보드 조종 노드 — WASD / 화살표로 /cmd_vel(TwistStamped) 발행.

실행 (시뮬이 떠 있는 상태에서, 새 터미널):
  ros2 run apc_simulation amr_teleop
  ros2 run apc_simulation amr_teleop --ros-args -p linear_speed:=0.15 -p angular_speed:=0.8

  w / ↑ 앞   s / ↓ 뒤   a / ← 왼쪽 회전   d / → 오른쪽 회전
  누르고 있는 동안만 움직이고, 떼면 멈춤.  space / x 즉시 정지,  f 시점이 로봇 따라가기 켜기/끄기,  q 또는 Ctrl+C 종료
  ※ 이 터미널 창을 클릭해 둔 상태에서 눌러야 함 (Gazebo 창이 아니라)
  ※ 터미널은 키 두 개를 동시에 못 받아서 '앞 + 회전' 같은 대각선 이동은 안 됨

파라미터:
  cmd_vel_topic  (기본 /cmd_vel)      linear_speed  (기본 0.2 m/s, TB3 Waffle 최대 0.26)
  angular_speed  (기본 1.0 rad/s)     hold_timeout  (기본 0.6 s, 입력이 끊긴 뒤 멈출 때까지)
  rate           (기본 20 Hz)          follow_target (기본 amr_1, f 키로 따라갈 gz 모델 이름)
"""
import os
import select
import subprocess
import sys
import termios
import threading
import time
import tty

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from apc_simulation.camera_follow import follow_command, parse_list
from apc_simulation.teleop_keys import FOLLOW_KEYS, QUIT_KEYS, TeleopState, parse_keys

HELP = """
---------------------------------------------
 AMR 키보드 조종  (이 터미널을 클릭한 상태로)
   w / ↑ : 앞      s / ↓ : 뒤
   a / ← : 왼쪽    d / → : 오른쪽   (제자리 회전)
   누르고 있는 동안만 움직임
   f : 시점이 로봇 따라가기 켜기/끄기
   space / x : 정지    q / Ctrl+C : 종료
---------------------------------------------"""


class AmrTeleopNode(Node):
    def __init__(self) -> None:
        super().__init__('amr_teleop')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('linear_speed', 0.2)
        self.declare_parameter('angular_speed', 1.0)
        self.declare_parameter('hold_timeout', 0.6)
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('follow_target', 'amr_1')
        self.follow_target = str(self.get_parameter('follow_target').value)
        self.following = False
        self.follow_busy = threading.Lock()

        topic = str(self.get_parameter('cmd_vel_topic').value)
        self.state = TeleopState(
            float(self.get_parameter('linear_speed').value),
            float(self.get_parameter('angular_speed').value),
            float(self.get_parameter('hold_timeout').value))
        self.period = 1.0 / float(self.get_parameter('rate').value)
        self.pub = self.create_publisher(TwistStamped, topic, 10)
        self.last_sent = (None, None)
        self.get_logger().info(
            f'{topic} 로 발행 (앞뒤 {self.state.linear_speed} m/s, '
            f'회전 {self.state.angular_speed} rad/s)')

    def publish(self, lin: float, ang: float) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x = lin
        msg.twist.angular.z = ang
        self.pub.publish(msg)
        if (lin, ang) != self.last_sent:
            self.get_logger().info(f'속도: 앞뒤 {lin:+.2f} m/s, 회전 {ang:+.2f} rad/s')
            self.last_sent = (lin, ang)

    def toggle_follow(self) -> None:
        """f 키: Gazebo GUI 시점이 로봇을 따라가게(또는 해제). gz 명령은 느려서 별도 스레드."""
        if not self.follow_busy.acquire(blocking=False):
            return                    # 이전 요청 처리 중
        want = not self.following
        threading.Thread(target=self._follow_worker, args=(want,), daemon=True).start()

    def _follow_worker(self, want: bool) -> None:
        try:
            services = parse_list(_gz_output(['gz', 'service', '-l']))
            topics = parse_list(_gz_output(['gz', 'topic', '-l']))
            cmd = follow_command(services, topics, self.follow_target, want)
            if cmd is None:
                self.get_logger().warning(
                    '시점 따라가기 기능을 찾지 못했습니다 (Gazebo 창이 없거나 headless). '
                    f'직접: Gazebo 창 오른쪽 Entity Tree 에서 {self.follow_target} 우클릭 → Follow')
                return
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            out = (res.stdout + res.stderr).strip()
            if res.returncode == 0 and 'false' not in out.lower():
                self.following = want
                self.get_logger().info(
                    f'시점: {self.follow_target} 따라가기 ' + ('켬 (다시 f 로 끄기)' if want else '끔'))
            else:
                self.get_logger().warning(
                    f'시점 따라가기 실패 ({" ".join(cmd[:4])}): {out[:200]} — '
                    f'Gazebo 창에서 {self.follow_target} 우클릭 → Follow 로 대신 할 수 있습니다')
        except (OSError, subprocess.TimeoutExpired) as e:
            self.get_logger().warning(f'시점 따라가기 명령 실패: {e}')
        finally:
            self.follow_busy.release()

    def run(self, fd: int) -> None:
        """키 입력을 읽어 rate 주기로 속도를 발행. q / Ctrl+C 면 반환."""
        while rclpy.ok():
            ready, _, _ = select.select([fd], [], [], self.period)
            now = time.monotonic()
            if ready:
                data = os.read(fd, 64)
                if not data:          # 입력 종료(EOF)
                    return
                for key in parse_keys(data):
                    if key in QUIT_KEYS:
                        return
                    if key in FOLLOW_KEYS:
                        self.toggle_follow()
                        continue
                    self.state.press(key, now)
            self.publish(*self.state.velocity(now))
            rclpy.spin_once(self, timeout_sec=0.0)


def _gz_output(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def main(args=None) -> None:
    if not sys.stdin.isatty():
        print('키보드 입력을 받을 터미널에서 실행하세요 (launch 파일 안에서는 동작하지 않음).',
              file=sys.stderr)
        sys.exit(1)
    rclpy.init(args=args)
    node = AmrTeleopNode()
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    print(HELP)
    try:
        tty.setcbreak(fd)         # 한 글자씩 바로 읽기, 화면에 글자 안 찍힘
        node.run(fd)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)   # 터미널 원래대로
        try:
            for _ in range(3):    # 끝날 때 확실히 정지
                node.publish(0.0, 0.0)
        except Exception:         # noqa: BLE001 — 종료 중 오류는 무시
            pass
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
