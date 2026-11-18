"""사과 등급 판정 노드 (객관적 검증 로그 포함).

- mock:=true  -> 카메라 없이 주기적으로 무작위 AppleGrade 발행 (다른 파트 개발용)
- mock:=false -> /apc/camera/image_raw 를 받아 YOLO 모델로 판정 + 검증 로그 기록

토픽/메시지 규약: docs/03_architecture.md
"""
import csv
from datetime import datetime
from pathlib import Path
import random
import time

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from ultralytics import YOLO

from apc_interfaces.msg import AppleGrade
from apc_vision.grading import GRADE_NAMES, grade_from_features

NOMINAL_DEFECT_BY_GRADE = {
    0: 0.00,  # 특
    1: 0.02,  # 상
    2: 0.08,  # 보통
    3: 0.25,  # 비상품
}

CSV_HEADERS = [
    'timestamp',
    'session_id',
    'model_file',
    'algorithm',
    'val_mAP50',
    'val_precision',
    'val_recall',
    'apple_id',
    'grade_code',
    'grade_name',
    'confidence',
    'diameter_mm',
    'defect_ratio',
    'inference_ms',
]


def _compute_iou(box_a, box_b) -> float:
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b
    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0.0:
        return 0.0
    area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)
    area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)
    denom = area_a + area_b - inter_area
    return inter_area / denom if denom > 0.0 else 0.0


class GraderNode(Node):

    def __init__(self):
        super().__init__('grader_node')
        self.declare_parameter('mock', True)
        self.declare_parameter('mock_period_sec', 2.0)
        self.declare_parameter('model_path', 'models/apple_grader.pt')
        self.declare_parameter('image_topic', '/apc/camera/image_raw')
        self.declare_parameter('conf_threshold', 0.45)
        self.declare_parameter('mm_per_pixel', 0.15)
        self.declare_parameter('track_iou_threshold', 0.35)
        self.declare_parameter('track_max_missed', 8)
        self.declare_parameter('log_dir', 'logs')

        self.mock = self.get_parameter('mock').value
        self.pub = self.create_publisher(AppleGrade, '/apc/apple_grade', 10)
        self.next_apple_id = 1
        self._tracks = []
        self._csv_file = None
        self._csv_writer = None

        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._stats = {
            'frames': 0,
            'detections': 0,
            'grade_counts': {0: 0, 1: 0, 2: 0, 3: 0},
            'conf_sum': 0.0,
            'latency_ms_sum': 0.0,
        }

        if self.mock:
            period = float(self.get_parameter('mock_period_sec').value)
            self.timer = self.create_timer(period, self._publish_mock)
            self.get_logger().info(f'[MOCK] {period:.1f}초마다 무작위 등급 발행')
        else:
            self.conf_threshold = float(self.get_parameter('conf_threshold').value)
            self.mm_per_pixel = float(self.get_parameter('mm_per_pixel').value)
            self.track_iou_threshold = float(self.get_parameter('track_iou_threshold').value)
            self.track_max_missed = int(self.get_parameter('track_max_missed').value)

            model_path = self._resolve_ws_path(self.get_parameter('model_path').value, must_exist=True)
            self.model = YOLO(str(model_path))
            self.model_meta = self._extract_model_meta(model_path)

            log_dir = self._resolve_ws_path(self.get_parameter('log_dir').value, must_exist=False)
            self._init_verification_logger(log_dir)

            topic = self.get_parameter('image_topic').value
            self.sub = self.create_subscription(Image, topic, self._on_image, 10)
            self.get_logger().info(
                f"[REAL] 모델={self.model_meta['model_file']} | 알고리즘={self.model_meta['algorithm']} | "
                f"검증수치(mAP50={self.model_meta['val_mAP50']}, P={self.model_meta['val_precision']}, "
                f"R={self.model_meta['val_recall']}) | 검증로그={self.csv_path}"
            )

    def _resolve_ws_path(self, raw_path: str, must_exist: bool) -> Path:
        p = Path(raw_path).expanduser()
        if p.is_absolute():
            if must_exist and not p.is_file():
                raise FileNotFoundError(f'파일을 찾을 수 없습니다: {p}')
            return p
        if must_exist and p.is_file():
            return p.resolve()
        ws_candidate = Path.home() / 'apc_ws' / raw_path
        if must_exist and not ws_candidate.is_file():
            raise FileNotFoundError(f'YOLO 가중치 파일을 찾을 수 없습니다: {raw_path}')
        return ws_candidate

    def _extract_model_meta(self, model_path: Path) -> dict:
        ckpt = getattr(self.model, 'ckpt', None) or {}
        train_args = ckpt.get('train_args', {}) if isinstance(ckpt, dict) else {}
        algo_raw = train_args.get('model', 'yolo11s.pt')
        algorithm = Path(str(algo_raw)).stem

        meta = {
            'model_file': model_path.name,
            'algorithm': algorithm,
            'val_mAP50': 'N/A',
            'val_precision': 'N/A',
            'val_recall': 'N/A',
        }

        exp_md = Path.home() / 'apc_ws/docs/experiments.md'
        if exp_md.is_file():
            for line in reversed(exp_md.read_text(encoding='utf-8').splitlines()):
                if line.startswith('| `') and '|' in line:
                    cols = [c.strip().strip('`') for c in line.strip('|').split('|')]
                    if len(cols) >= 10:
                        meta['algorithm'] = Path(cols[2]).stem
                        meta['val_precision'] = cols[6]
                        meta['val_recall'] = cols[7]
                        meta['val_mAP50'] = cols[8]
                        break
        return meta

    def _init_verification_logger(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir
        self.csv_path = log_dir / 'inference_verification.csv'
        is_new = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
        self._csv_file = open(self.csv_path, 'a', newline='', encoding='utf-8')
        self._csv_writer = csv.writer(self._csv_file)
        if is_new:
            self._csv_writer.writerow(CSV_HEADERS)
            self._csv_file.flush()

    def _write_verification_row(self, msg: AppleGrade, inference_ms: float):
        if self._csv_writer is None:
            return
        label = GRADE_NAMES.get(int(msg.grade), str(msg.grade)).strip()
        self._csv_writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            self.session_id,
            self.model_meta['model_file'],
            self.model_meta['algorithm'],
            self.model_meta['val_mAP50'],
            self.model_meta['val_precision'],
            self.model_meta['val_recall'],
            msg.apple_id,
            msg.grade,
            label,
            f'{msg.confidence:.4f}',
            f'{msg.diameter_mm:.2f}',
            f'{msg.defect_ratio:.3f}',
            f'{inference_ms:.2f}',
        ])
        self._csv_file.flush()

    def _save_session_summary(self):
        if self.mock or not hasattr(self, 'log_dir'):
            return
        frames = self._stats['frames']
        dets = self._stats['detections']
        avg_conf = (self._stats['conf_sum'] / dets) if dets > 0 else 0.0
        avg_ms = (self._stats['latency_ms_sum'] / frames) if frames > 0 else 0.0
        fps = (1000.0 / avg_ms) if avg_ms > 0.0 else 0.0
        gc = self._stats['grade_counts']

        summary_md = (
            f"# 비전 추론 객관적 검증 리포트 (`{self.session_id}`)\n\n"
            f"| 항목 | 수치 / 내용 |\n"
            f"| :--- | :--- |\n"
            f"| 사용 모델 파일 | `{self.model_meta['model_file']}` |\n"
            f"| 모델 알고리즘 | `{self.model_meta['algorithm']}` |\n"
            f"| 검증 데이터 성능 (mAP50 / P / R) | `{self.model_meta['val_mAP50']}` / `{self.model_meta['val_precision']}` / `{self.model_meta['val_recall']}` |\n"
            f"| Confidence 임계값 | `{self.conf_threshold}` |\n"
            f"| 총 처리 프레임 수 | `{frames}` frames |\n"
            f"| 신규 판정 사과 수 | `{dets}` 개 (특:{gc[0]}, 상:{gc[1]}, 보통:{gc[2]}, 비상품:{gc[3]}) |\n"
            f"| 평균 판정 신뢰도 (Confidence) | `{avg_conf:.3f}` |\n"
            f"| 평균 추론 속도 | `{avg_ms:.2f} ms/frame` (`{fps:.1f} FPS`) |\n"
            f"| 상세 로그 파일 | `{self.csv_path}` |\n"
        )
        summary_path = self.log_dir / 'latest_verification_summary.md'
        summary_path.write_text(summary_md, encoding='utf-8')
        self.get_logger().info(
            f"[검증 요약 저장] {summary_path} | 모델={self.model_meta['algorithm']} "
            f"(mAP50={self.model_meta['val_mAP50']}) | 판정={dets}건 | 평균신뢰도={avg_conf:.3f} | 속도={avg_ms:.1f}ms"
        )

    def _imgmsg_to_bgr(self, msg: Image) -> np.ndarray:
        enc = msg.encoding.lower()
        if enc in ('bgr8', 'rgb8'):
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step // 3, 3)[:, :msg.width, :]
            return arr[:, :, ::-1].copy() if enc == 'rgb8' else arr.copy()
        if enc in ('bgra8', 'rgba8'):
            arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step // 4, 4)[:, :msg.width, :3]
            return arr[:, :, ::-1].copy() if enc == 'rgba8' else arr.copy()
        if enc == 'mono8':
            gray = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width]
            return np.repeat(gray[:, :, None], 3, axis=2)
        raise ValueError(f'지원하지 않는 이미지 인코딩입니다: {msg.encoding}')

    def _make_msg(self, grade, confidence, diameter_mm, defect_ratio):
        msg = AppleGrade()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_link'
        msg.apple_id = self.next_apple_id
        msg.grade = int(grade)
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

    def _match_track(self, bbox):
        best_idx = -1
        best_iou = self.track_iou_threshold
        for i, tr in enumerate(self._tracks):
            iou = _compute_iou(bbox, tr['bbox'])
            if iou >= best_iou:
                best_iou = iou
                best_idx = i
        return best_idx

    def _on_image(self, image_msg: Image):
        try:
            frame_bgr = self._imgmsg_to_bgr(image_msg)
        except Exception as exc:
            self.get_logger().error(f'이미지 변환 실패: {exc}')
            return

        t0 = time.perf_counter()
        results = self.model.predict(frame_bgr, conf=self.conf_threshold, verbose=False)
        inference_ms = (time.perf_counter() - t0) * 1000.0

        self._stats['frames'] += 1
        self._stats['latency_ms_sum'] += inference_ms

        if not results:
            return

        boxes = results[0].boxes
        for tr in self._tracks:
            tr['missed'] += 1

        if boxes is not None and len(boxes) > 0:
            xyxy_list = boxes.xyxy.cpu().numpy()
            conf_list = boxes.conf.cpu().numpy()
            cls_list = boxes.cls.cpu().numpy().astype(int)

            for bbox, conf, grade in zip(xyxy_list, conf_list, cls_list):
                bbox_tuple = tuple(float(v) for v in bbox)
                idx = self._match_track(bbox_tuple)

                if idx >= 0:
                    self._tracks[idx]['bbox'] = bbox_tuple
                    self._tracks[idx]['missed'] = 0
                    continue

                self._tracks.append({'bbox': bbox_tuple, 'missed': 0})
                w_px = max(0.0, bbox_tuple[2] - bbox_tuple[0])
                h_px = max(0.0, bbox_tuple[3] - bbox_tuple[1])
                diameter_mm = max(w_px, h_px) * self.mm_per_pixel
                defect_ratio = NOMINAL_DEFECT_BY_GRADE.get(int(grade), 0.05)

                msg = self._make_msg(grade, float(conf), diameter_mm, defect_ratio)
                self.pub.publish(msg)

                self._stats['detections'] += 1
                self._stats['conf_sum'] += float(conf)
                if int(grade) in self._stats['grade_counts']:
                    self._stats['grade_counts'][int(grade)] += 1

                self._write_verification_row(msg, inference_ms)

                label = GRADE_NAMES.get(int(grade), str(grade)).strip()
                self.get_logger().info(
                    f"[REAL|{self.model_meta['algorithm']}|mAP50={self.model_meta['val_mAP50']}] "
                    f"apple#{msg.apple_id} grade={grade}({label}) conf={conf:.2f} "
                    f"d={diameter_mm:.1f}mm ({inference_ms:.1f}ms)"
                )

        self._tracks = [tr for tr in self._tracks if tr['missed'] <= self.track_max_missed]

    def destroy_node(self):
        self._save_session_summary()
        if self._csv_file is not None:
            self._csv_file.close()
            self._csv_file = None
        super().destroy_node()


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
