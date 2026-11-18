"""🅐 사과 등급 판정 노드.

- mock:=true  → 카메라 없이 주기적으로 무작위 AppleGrade 발행 (다른 파트 개발용)
- mock:=false → /apc/camera/image_raw 를 받아 YOLO 모델로 판정 (TODO: 🅐 구현)

토픽/메시지 규약: docs/03_architecture.md
"""
import random

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from apc_interfaces.msg import AppleGrade

from apc_vision.grading import grade_from_features


class GraderNode(Node):

    def __init__(self):
        super().__init__('grader_node')
        self.declare_parameter('mock', True)
        self.declare_parameter('mock_period_sec', 2.0)
        self.declare_parameter('model_path', 'models/apple_grader.pt')
        self.declare_parameter('image_topic', '/apc/camera/image_raw')

        self.mock = self.get_parameter('mock').value
        self.pub = self.create_publisher(AppleGrade, '/apc/apple_grade', 10)
        self.next_apple_id = 1

        if self.mock:
            period = float(self.get_parameter('mock_period_sec').value)
            self.timer = self.create_timer(period, self._publish_mock)
            self.get_logger().info(f'[MOCK] {period:.1f}초마다 무작위 등급 발행')
        else:
            topic = self.get_parameter('image_topic').value
            self.sub = self.create_subscription(Image, topic, self._on_image, 10)
            self.model = None  # TODO(🅐): ultralytics YOLO 모델 로드
            self.get_logger().info(f'[REAL] {topic} 구독 시작')

    def _make_msg(self, grade, confidence, diameter_mm, defect_ratio):
        msg = AppleGrade()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_link'
        msg.apple_id = self.next_apple_id
        msg.grade = grade
        msg.confidence = float(confidence)
        msg.diameter_mm = float(diameter_mm)
        msg.defect_ratio = float(defect_ratio)
        msg.zone_id = ''
        self.next_apple_id += 1
        return msg

    def _publish_mock(self):
        diameter = random.uniform(60.0, 95.0)
        defect = random.choice([0.0, 0.0, 0.02, 0.05, 0.15, 0.3])
        grade = grade_from_features(diameter, defect)
        msg = self._make_msg(grade, random.uniform(0.7, 0.99), diameter, defect)
        self.pub.publish(msg)
        self.get_logger().info(
            f'apple#{msg.apple_id} grade={grade} d={diameter:.1f}mm defect={defect:.2f}')

    def _on_image(self, image_msg: Image):
        # TODO(🅐):
        # 1. cv_bridge 로 OpenCV 이미지 변환
        # 2. YOLO 로 사과 검출 + 결함 분할 → diameter_mm, defect_ratio 추정
        # 3. grade_from_features() 또는 분류 모델로 등급 산출
        # 4. 같은 사과 중복 발행 방지(트래킹) 후 self.pub.publish()
        pass


def main(args=None):
    rclpy.init(args=args)
    node = GraderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
