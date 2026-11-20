import csv
import json
import math
import os
import random
import time
from collections import defaultdict
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
        self.declare_parameter('mm_per_pixel', 0.359)
        self.declare_parameter('conf_threshold', 0.45)
        self.declare_parameter('roi_axis', 'y')
        self.declare_parameter('roi_min_ratio', 0.30)
        self.declare_parameter('roi_max_ratio', 0.70)
        self.declare_parameter('edge_margin_px', 15.0)
        self.declare_parameter('vote_frames', 5)
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
        self.edge_margin_px = float(self.get_parameter('edge_margin_px').value)
        self.vote_frames = max(1, int(self.get_parameter('vote_frames').value))
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
            self.metrics_str = 'mAP50=0.681 / P=0.569 / R=0.781'
        else:
            self.metrics_str = f'N/A (미검증 가중치: {self.model_filename})'

        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(AppleGrade, '/apc/apple_grade', 10)
        self.subscription = self.create_subscription(
            Image, self.image_topic, self.image_callback, 10
        )

        self.graded_ids = set()
        self.track_buffers = {}
        self.recent_events = []
        self.total_graded_count = 0
        self.mock_seq = 0
        self.fallback_apple_id = 0

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
                f'ROI({self.roi_axis}축 {self.roi_min_ratio:.2f}~{self.roi_max_ratio:.2f}, vote={self.vote_frames})'
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
        margin = self.edge_margin_px
        if x1 <= margin or x2 >= (w - margin) or y1 <= margin or y2 >= (h - margin):
            return False
        if self.roi_axis in ('x', 'both'):
            if not (w * self.roi_min_ratio <= cx <= w * self.roi_max_ratio):
                return False
        if self.roi_axis in ('y', 'both'):
            if not (h * self.roi_min_ratio <= cy <= h * self.roi_max_ratio):
                return False
        return True

    def _resolve_track_id(self, raw_id, cx, cy, now):
        if raw_id > 0:
            if raw_id > self.fallback_apple_id:
                self.fallback_apple_id = raw_id
            if raw_id in self.track_buffers or raw_id in self.graded_ids:
                return raw_id

        # ByteTrack ID가 끊겨 새 번호가 부여되더라도 직전 프레임 위치(55px 이내)면 동일 버퍼로 병합
        for existing_id, buf in self.track_buffers.items():
            px, py = buf['last_pos']
            if (now - buf['last_seen']) < 0.25 and math.hypot(cx - px, cy - py) < 55.0:
                return existing_id

        if raw_id > 0:
            return raw_id
        self.fallback_apple_id += 1
        return self.fallback_apple_id

    def _finalize_track(self, track_id, infer_ms, now):
        buf = self.track_buffers.pop(track_id, None)
        if not buf or not buf['samples']:
            return

        cx, cy = buf['last_pos']
        if track_id in self.graded_ids:
            return
        if any(math.hypot(cx - px, cy - py) < 45.0 for (_, px, py) in self.recent_events):
            self.graded_ids.add(track_id)
            return

        samples = buf['samples']
        best_conf = max(s[2] for s in samples)
        if best_conf < self.conf_threshold:
            return

        # 1) 지름: 그림자 한쪽 축 연장을 배제하기 위해 단축(min(w, h)) 기반 샘플들의 중앙값 사용
        diams = sorted(s[0] for s in samples)
        mid = len(diams) // 2
        diameter_mm = round(
            diams[mid] if len(diams) % 2 == 1 else (diams[mid - 1] + diams[mid]) / 2.0,
            2,
        )

        # 2) 등급: ROI 내 누적 프레임의 신뢰도 가중 투표로 단일 프레임 흔들림 제거
        scores = defaultdict(float)
        for _, cid, c in samples:
            scores[cid] += c
        cls_id = max(scores.items(), key=lambda kv: kv[1])[0]

        self.graded_ids.add(track_id)
        if len(self.graded_ids) > 500:
            self.graded_ids.clear()
        self.recent_events.append((now, cx, cy))

        grade_label = GRADE_LABELS.get(cls_id, f'class_{cls_id}')
        self._publish_result(track_id, cls_id, best_conf, diameter_mm)
        self.total_graded_count += 1

        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                ts, self.model_filename, self.metrics_str, track_id,
                cls_id, grade_label, round(best_conf, 4), diameter_mm, round(infer_ms, 2)
            ])

        self._update_summary_md({
            'timestamp': ts,
            'track_id': track_id,
            'grade': cls_id,
            'grade_label': grade_label,
            'diameter_mm': diameter_mm,
            'confidence': best_conf,
            'infer_ms': infer_ms,
        })

        self.get_logger().info(
            f'[판정완료] ID={track_id} ({len(samples)}프레임 투표) | grade={cls_id}({grade_label}) | '
            f'지름={diameter_mm}mm | conf={best_conf:.2f} | {infer_ms:.1f}ms'
        )

    def image_callback(self, msg: Image):
        if self.mock:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]

        # 경계선 부근 추론 연속성을 위해 내부 탐색 임계값은 낮추고 최종 확정 시 conf_threshold 적용
        infer_conf = min(self.conf_threshold, 0.35)
        t0 = time.perf_counter()
        results = self.model.track(
            frame,
            persist=True,
            tracker='bytetrack.yaml',
            conf=infer_conf,
            verbose=False,
        )
        infer_ms = (time.perf_counter() - t0) * 1000.0

        now = time.time()
        self.recent_events = [(t, px, py) for (t, px, py) in self.recent_events if now - t < 1.5]

        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                raw_id = int(box.id[0].item()) if box.id is not None else -1

                if self.strict_grade_range and not (0 <= cls_id <= 3):
                    continue

                track_id = self._resolve_track_id(raw_id, cx, cy, now)
                if track_id in self.graded_ids:
                    continue

                if self._in_roi_and_not_clipped(x1, y1, x2, y2, cx, cy, w, h):
                    bw = max(0.0, x2 - x1)
                    bh = max(0.0, y2 - y1)
                    diameter_mm = min(bw, bh) * self.mm_per_pixel

                    buf = self.track_buffers.setdefault(
                        track_id, {'samples': [], 'last_seen': now, 'last_pos': (cx, cy)}
                    )
                    buf['samples'].append((diameter_mm, cls_id, conf))
                    buf['last_seen'] = now
                    buf['last_pos'] = (cx, cy)

                    if len(buf['samples']) >= self.vote_frames:
                        self._finalize_track(track_id, infer_ms, now)
                elif track_id in self.track_buffers:
                    # ROI를 벗어나는 시점에 누적된 샘플이 있으면 즉시 확정
                    self.track_buffers[track_id]['last_seen'] = now
                    self.track_buffers[track_id]['last_pos'] = (cx, cy)
                    self._finalize_track(track_id, infer_ms, now)

        # 시야에서 완전히 사라진 미확정 버퍼 정리 및 확정 발행
        stale_ids = [
            tid for tid, buf in self.track_buffers.items()
            if (now - buf['last_seen']) > 0.25
        ]
        for tid in stale_ids:
            self._finalize_track(tid, infer_ms, now)


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
