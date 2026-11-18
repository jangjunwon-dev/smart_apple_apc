"""🅑 AMR 운반 작업 관리 노드.

/apc/apple_grade 를 받아 등급별 적재 구역(zones.yaml)을 배정하고 운반 작업 큐를 관리한다.

- mock:=true  → Nav2 없이 이동 시간을 흉내 내며 상태만 발행
- mock:=false → Nav2 NavigateToPose 액션으로 실제 주행 (TODO: 🅑 구현)

토픽/메시지 규약: docs/03_architecture.md
"""
from collections import deque

import rclpy
from rclpy.node import Node

from apc_interfaces.msg import AmrStatus, AppleGrade

DEFAULT_ZONE_BY_GRADE = {
    AppleGrade.GRADE_SPECIAL: 'ZONE_A',
    AppleGrade.GRADE_GOOD: 'ZONE_B',
    AppleGrade.GRADE_NORMAL: 'ZONE_C',
    AppleGrade.GRADE_REJECT: 'ZONE_R',
}


class TaskManagerNode(Node):

    def __init__(self):
        super().__init__('task_manager_node')
        self.declare_parameter('mock', True)
        self.declare_parameter('robot_id', 'amr_1')
        self.declare_parameter('mock_travel_sec', 5.0)
        # zones.yaml 에서 덮어씀: zone_<ID>_xy: [x, y]
        for zone in DEFAULT_ZONE_BY_GRADE.values():
            self.declare_parameter(f'zone_{zone}_xy', [0.0, 0.0])

        self.mock = self.get_parameter('mock').value
        self.robot_id = self.get_parameter('robot_id').value
        self.queue = deque()
        self.state = AmrStatus.STATE_IDLE
        self.current = None          # (apple_id, zone_id)
        self.remaining_sec = 0.0

        self.sub = self.create_subscription(AppleGrade, '/apc/apple_grade', self._on_grade, 10)
        self.pub = self.create_publisher(AmrStatus, '/apc/amr_status', 10)
        self.tick = 0.5
        self.timer = self.create_timer(self.tick, self._step)
        self.status_timer = self.create_timer(1.0, self._publish_status)

        mode = 'MOCK' if self.mock else 'NAV2'
        self.get_logger().info(f'[{mode}] {self.robot_id} 작업 관리 시작')

    # ------------------------------------------------------------------
    def _on_grade(self, msg: AppleGrade):
        zone = msg.zone_id or DEFAULT_ZONE_BY_GRADE.get(msg.grade, 'ZONE_R')
        self.queue.append((msg.apple_id, zone))
        self.get_logger().info(f'작업 추가: apple#{msg.apple_id} → {zone} (대기 {len(self.queue)})')

    def _step(self):
        if self.state == AmrStatus.STATE_IDLE and self.queue:
            self.current = self.queue.popleft()
            self._set_state(AmrStatus.STATE_MOVING)
            if self.mock:
                self.remaining_sec = float(self.get_parameter('mock_travel_sec').value)
            else:
                self._send_nav_goal(self.current[1])
            return

        if self.mock and self.state == AmrStatus.STATE_MOVING:
            self.remaining_sec -= self.tick
            if self.remaining_sec <= 0.0:
                self._set_state(AmrStatus.STATE_UNLOADING)
        elif self.state == AmrStatus.STATE_UNLOADING:
            self.get_logger().info(f'하역 완료: apple#{self.current[0]} @ {self.current[1]}')
            self.current = None
            self._set_state(AmrStatus.STATE_IDLE)

    def _send_nav_goal(self, zone_id: str):
        # TODO(🅑): nav2_msgs/action/NavigateToPose 액션 클라이언트로 zone 좌표 이동
        #   - 좌표: self.get_parameter(f'zone_{zone_id}_xy').value
        #   - 결과 콜백에서 self._set_state(AmrStatus.STATE_UNLOADING)
        self.get_logger().warn(f'Nav2 미구현 → {zone_id} 즉시 도착 처리')
        self._set_state(AmrStatus.STATE_UNLOADING)

    # ------------------------------------------------------------------
    def _set_state(self, state: int):
        self.state = state
        self._publish_status()

    def _publish_status(self):
        msg = AmrStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.robot_id = self.robot_id
        msg.state = self.state
        msg.current_apple_id = self.current[0] if self.current else 0
        msg.target_zone = self.current[1] if self.current else ''
        msg.queue_length = len(self.queue)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TaskManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
