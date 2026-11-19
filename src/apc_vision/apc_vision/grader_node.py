import csv
import json
import math
import os
import random
import time
from datetime import datetime

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from ultralytics import YOLO

from apc_interfaces.msg import AppleGrade


GRADE_LABELS = {
    0: '특(Special)',
    1: '상(High)',
    2: '보통(Normal)',
    3: '등외(Out-of-grade)',
}


class GraderNode(Node):
    def __init__(self):
        super().__init__('grader_node')

        default_model = os.path.expanduser('~/apc_ws/models/apple_grader.pt')
        default_log_dir = os.path.expanduser('~/apc_ws/logs')

        self.declare_parameter('mock', False)
        self.declare_parameter('mock_period', 2.0)
        self.declare_parameter('image_topic', '/apc/camera/image_raw')
        self.declare_parameter('model_path', default_model)
        self.declare_parameter('mm_per_pixel', 1.44)
        self.declare_parameter('conf_threshold', 0.45)
        self.declare_parameter('roi_axis', 'y')
        self.declare_parameter('roi_min_ratio', 0.30)
        self.declare_parameter('roi_max_ratio', 0.70)
        self.declare_parameter('strict_grade_range', True)
        self.declare_parameter('log_dir', default_log_dir)

        self.mock = bool(self.get_parameter('mock').value)
        self.mock_period = float(self.get_parameter('mock_period').value)
        self.image_topic = str(self.get_parameter('image_topic').value)
        self.model_path = str(self.get_parameter('model_path').value)
        self.mm_per_pixel = float(self.get_parameter('mm_per_pixel').value)
        self.conf_threshold = float(self.get_parameter('conf_threshold').value)
        self.roi_axis = str(self.get_parameter('roi_axis').value).lower()
        self.roi_min_ratio = float(self.get_parameter('roi_min_ratio').value)
        self.roi_max_ratio = float(self.get_parameter('roi_max_ratio').value)
        self.strict_grade_range = bool(self.get_parameter('strict_grade_range').value)
        self.log_dir = str(self.get_parameter('log_dir').value)

        if self.roi_axis not in ('x', 'y', 'both'):
            self.get_logger().warning(f"잘못된 roi_axis='{self.roi_axis}', 기본값 'y'로 설정합니다.")
            self.roi_axis = 'y'

        os.makedirs(self.log_dir, exist_ok=True)
        self.csv_path = os.path.join(self.log_dir, 'inference_verification.csv')
        self.md_path = os.path.join(self.log_dir, 'latest_verification_summary.md')

        self.model_filename = os.path.basename(self.model_path)
        if self.model_filename == 'apple_grader.pt':
            self.metrics_str = 'mAP50=0.681, P=0.569, R=0.781'
        else:
            self.metrics_str = f'N/A (미검증 가중치: {self.model_filename})'

        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(AppleGrade, '/apc/apple_grade', 10)
        self.subscription = self.create_subscription(
            Image, self.image_topic, self.image_callback, 10
        )

        self.graded_ids = set()
        self.recent_events = []
        self.total_graded_count = 0
        self.mock_seq = 0

        self._init_logs()

        if self.mock:
            self.model = None
            self.mock_timer = self.create_timer(self.mock_period, self.mock_timer_callback)
            self.get_logger().info(
                f'[MOCK] 모의 판정 모드 시작 ({self.mock_period}초 주기 발행 -> /apc/apple_grade)'
            )
        else:
            self.mock_timer = None
            self.model = YOLO(self.model_path)
            self.get_logger().info(
                f'[REAL] 모델={self.model_filename} | 검증수치({self.metrics_str}) | '
                f'토픽={self.image_topic} | mm_per_pixel={self.mm_per_pixel} | '
                f'ROI({self.roi_axis}축 {self.roi_min_ratio:.2f}~{self.roi_max_ratio:.2f})'
            )

    def _init_logs(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'model', 'metrics', 'track_id',
                    'grade', 'grade_label', 'confidence', 'diameter_mm', 'infer_ms'
                ])

    def _update_summary_md(self, last_record):
        content = (
            f'# Vision Apple Grader 검증 요약 리포트\n\n'
            f'- **최근 업데이트:** {last_record["timestamp"]}\n'
            f'- **적용 모델:** `{self.model_filename}`\n'
            f'- **모델 검증 지표:** {self.metrics_str}\n'
            f'- **구독 카메라 토픽:** `{self.image_topic}`\n'
            f'- **픽셀 환산 계수 (`mm_per_pixel`):** {self.mm_per_pixel}\n'
            f'- **중앙 판정 구역 (ROI):** {self.roi_axis}축 {int(self.roi_min_ratio*100)}% ~ {int(self.roi_max_ratio*100)}%\n'
            f'- **누적 판정 건수:** {self.total_graded_count}건\n\n'
            f'## 최근 판정 샘플\n'
            f'- **Track ID:** {last_record["track_id"]}\n'
            f'- **등급 (`grade`):** {last_record["grade"]} ({last_record["grade_label"]})\n'
            f'- **추정 지름:** {last_record["diameter_mm"]} mm\n'
            f'- **신뢰도 / 추론시간:** {last_record["confidence"]:.3f} / {last_record["infer_ms"]:.1f} ms\n'
        )
        with open(self.md_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _publish_result(self, track_id, grade, confidence, diameter_mm):
        msg = AppleGrade()
        if hasattr(msg, 'get_fields_and_field_types'):
            fields = msg.get_fields_and_field_types()
            if 'grade' in fields:
                msg.grade = int(grade)
            if 'diameter_mm' in fields:
                msg.diameter_mm = float(diameter_mm)
            elif 'diameter' in fields:
                msg.diameter = float(diameter_mm)
            if 'confidence' in fields:
                msg.confidence = float(confidence)
            if 'track_id' in fields:
                msg.track_id = int(track_id)
            elif 'apple_id' in fields:
                msg.apple_id = int(track_id)
            if 'data' in fields and 'grade' not in fields:
                msg.data = json.dumps({
                    'track_id': int(track_id),
                    'grade': int(grade),
                    'diameter_mm': float(diameter_mm),
                    'confidence': round(float(confidence), 4),
                }, ensure_ascii=False)
        self.publisher_.publish(msg)

    def mock_timer_callback(self):
        self.mock_seq += 1
        grade = random.choice([0, 1, 2, 3])
        diameter_mm = round(random.uniform(68.0, 92.0), 1)
        confidence = round(random.uniform(0.80, 0.98), 3)
        grade_label = GRADE_LABELS.get(grade, f'class_{grade}')

        self._publish_result(self.mock_seq, grade, confidence, diameter_mm)
        self.get_logger().info(
            f'[MOCK 발행] ID={self.mock_seq} | grade={grade}({grade_label}) | '
            f'지름={diameter_mm}mm | conf={confidence:.2f}'
        )

    def _in_roi_and_not_clipped(self, x1, y1, x2, y2, cx, cy, w, h):
        margin = 5.0
        if self.roi_axis in ('x', 'both'):
            if x1 <= margin or x2 >= (w - margin):
                return False
            if not (w * self.roi_min_ratio <= cx <= w * self.roi_max_ratio):
                return False
        if self.roi_axis in ('y', 'both'):
            if y1 <= margin or y2 >= (h - margin):
                return False
            if not (h * self.roi_min_ratio <= cy <= h * self.roi_max_ratio):
                return False
        return True

    def image_callback(self, msg: Image):
        if self.mock:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]

        t0 = time.perf_counter()
        results = self.model.track(
            frame,
            persist=True,
            tracker='bytetrack.yaml',
            conf=self.conf_threshold,
            verbose=False,
        )
        infer_ms = (time.perf_counter() - t0) * 1000.0

        if not results or results[0].boxes is None:
            return

        now = time.time()
        self.recent_events = [(t, px, py) for (t, px, py) in self.recent_events if now - t < 1.5]

        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            track_id = int(box.id[0].item()) if box.id is not None else -1

            if self.strict_grade_range and not (0 <= cls_id <= 3):
                self.get_logger().warning(
                    f'[범위초과 무시] class_id={cls_id} (conf={conf:.2f}) -> 0~3 범위 밖이므로 발행 생략'
                )
                continue

            if not self._in_roi_and_not_clipped(x1, y1, x2, y2, cx, cy, w, h):
                continue

            if track_id != -1 and track_id in self.graded_ids:
                continue
            if any(math.hypot(cx - px, cy - py) < 45.0 for (_, px, py) in self.recent_events):
                if track_id != -1:
                    self.graded_ids.add(track_id)
                continue

            if track_id != -1:
                self.graded_ids.add(track_id)
                if len(self.graded_ids) > 500:
                    self.graded_ids.clear()
            self.recent_events.append((now, cx, cy))

            diameter_px = ((x2 - x1) + (y2 - y1)) / 2.0
            diameter_mm = round(diameter_px * self.mm_per_pixel, 2)
            grade_label = GRADE_LABELS.get(cls_id, f'class_{cls_id}')

            self._publish_result(track_id, cls_id, conf, diameter_mm)
            self.total_graded_count += 1

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    ts, self.model_filename, self.metrics_str, track_id,
                    cls_id, grade_label, round(conf, 4), diameter_mm, round(infer_ms, 2)
                ])

            self._update_summary_md({
                'timestamp': ts,
                'track_id': track_id,
                'grade': cls_id,
                'grade_label': grade_label,
                'diameter_mm': diameter_mm,
                'confidence': conf,
                'infer_ms': infer_ms,
            })

            self.get_logger().info(
                f'[판정완료] ID={track_id} | grade={cls_id}({grade_label}) | '
                f'지름={diameter_mm}mm | conf={conf:.2f} | {infer_ms:.1f}ms'
            )


def main(args=None):
    rclpy.init(args=args)
    node = GraderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
