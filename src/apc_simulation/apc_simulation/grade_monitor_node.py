"""판정 결과·AMR 상태를 한국어로 보여 주는 모니터 노드.

실행 (시뮬 실행 중, 새 터미널):
  ros2 run apc_simulation grade_monitor
  ros2 run apc_simulation grade_monitor --ros-args -p show_amr:=false   # 판정만

출력 예:
  [판정] 사과 #91   특     지름  89.3 mm  신뢰도  76%  → 구역 A   (시뮬 68.8초)
  [AMR] amr_1  이동 중  사과 #91 → 구역 A  대기 작업 0개
  [누적] 총 12개: 특 3 / 상 4 / 보통 3 / 비상품 2      (사과 5개마다)

`ros2 topic echo /apc/apple_grade` 와 같은 내용을 사람이 읽기 쉽게 바꾼 것 (토픽은 구독만 함).
"""
from apc_interfaces.msg import AmrStatus, AppleGrade
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from apc_simulation.monitor_format import format_amr, format_grade, GradeTally


class GradeMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__('grade_monitor')
        self.declare_parameter('show_amr', True)
        self.declare_parameter('summary_every', 5)      # 사과 N개마다 누적 요약 (0 = 안 함)
        self.summary_every = int(self.get_parameter('summary_every').value)
        self.tally = GradeTally()
        self.last_amr = None
        self.create_subscription(AppleGrade, '/apc/apple_grade', self._on_grade, 10)
        if bool(self.get_parameter('show_amr').value):
            self.create_subscription(AmrStatus, '/apc/amr_status', self._on_amr, 10)
        print('사과 판정 결과를 기다리는 중... (Ctrl+C 로 종료)', flush=True)

    def _on_grade(self, msg: AppleGrade) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        print(format_grade(msg.apple_id, msg.grade, msg.diameter_mm, msg.confidence,
                           msg.defect_ratio, msg.zone_id, stamp), flush=True)
        self.tally.add(msg.grade)
        total = sum(self.tally.counts.values())
        if self.summary_every > 0 and total % self.summary_every == 0:
            print(self.tally.summary(), flush=True)

    def _on_amr(self, msg: AmrStatus) -> None:
        line = format_amr(msg.robot_id, msg.state, msg.current_apple_id, msg.target_zone,
                          msg.queue_length)
        if line != self.last_amr:                         # 1 Hz 반복 발행은 바뀔 때만 출력
            print(line, flush=True)
            self.last_amr = line


def main(args=None) -> None:
    rclpy.init(args=args)
    node = GradeMonitorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        print(node.tally.summary(), flush=True)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
