"""컨베이어 벨트 속도 제어 + 사과 주기적 생성/삭제 노드.

- belt_speed 를 /apc/conveyor/cmd_vel 로 1Hz 반복 발행 (브리지 → TrackController)
- spawn_period 마다 /world/<world>/create 로 사과 1개 생성 (크기·색 무작위)
  간격은 SpawnSchedule 이 sim 시간으로 계산 (/clock 받기 전에는 생성 안 함 — spawn_schedule.py 참고)
- apple_model: 'sphere'(단색 구, 기본) / 'ycb'(YCB 013_apple 3D 스캔 메시, yaw 무작위)
- 컨베이어 끝 아래 논리 카메라(/apc/sim/apple_sink)에 사과가 잡히면 /world/<world>/remove
- belt_speed, spawn_period 는 실행 중 `ros2 param set` 으로 바로 변경 가능
- mock:=true 면 Gazebo 서비스를 호출하지 않고 로그만 출력
"""
from __future__ import annotations

import math
import random

from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from ros_gz_interfaces.msg import Entity, LogicalCameraImage
from ros_gz_interfaces.srv import DeleteEntity, SpawnEntity
from std_msgs.msg import Float64

from apc_simulation.apple_factory import (
    APPLE_MODELS, apple_sdf, names_to_remove, random_apple)
from apc_simulation.spawn_schedule import SpawnSchedule

APPLE_PREFIX = 'apple_'
SPAWN_TICK = 0.05   # s, 생성 시점 확인 주기 (실제 간격은 spawn_period)


class AppleSpawnerNode(Node):
    """컨베이어 위 사과 흐름을 관리하는 노드."""

    def __init__(self) -> None:
        super().__init__('apple_spawner')
        self.declare_parameter('mock', False)
        self.declare_parameter('world_name', 'apc_world')
        self.declare_parameter('belt_speed', 0.3)          # m/s (+x 방향)
        self.declare_parameter('spawn_period', 4.0)        # s
        self.declare_parameter('spawn_x', -3.35)           # 컨베이어 시작 지점
        self.declare_parameter('spawn_y', 0.0)
        self.declare_parameter('belt_top_z', 0.8)          # 벨트 윗면 높이
        self.declare_parameter('max_lifetime', 40.0)       # s, 위치를 못 받을 때 안전 삭제
        self.declare_parameter('radius_min', 0.035)
        self.declare_parameter('radius_max', 0.048)
        self.declare_parameter('max_apples', 6)
        self.declare_parameter('seed', -1)                 # -1 = 무작위
        self.declare_parameter('apple_model', 'sphere')    # sphere | ycb

        self.apple_model = str(self._p('apple_model'))
        if self.apple_model not in APPLE_MODELS:
            msg = f'apple_model 은 {APPLE_MODELS} 중 하나여야 함 (입력: {self.apple_model!r})'
            self.get_logger().error(msg)
            raise ValueError(msg)

        self.mock = self._p('mock')
        world = self._p('world_name')
        seed = self._p('seed')
        self.rng = random.Random(None if seed < 0 else seed)
        # yaw 전용 난수 → 크기·색 순서는 apple_model 과 상관없이 같은 seed 면 동일
        self.yaw_rng = random.Random(None if seed < 0 else seed + 1)

        self.belt_pub = self.create_publisher(Float64, '/apc/conveyor/cmd_vel', 10)
        self.create_subscription(
            LogicalCameraImage, '/apc/sim/apple_sink', self._on_sink, 10)
        self.spawn_cli = self.create_client(SpawnEntity, f'/world/{world}/create')
        self.remove_cli = self.create_client(DeleteEntity, f'/world/{world}/remove')

        self.count = 0
        self.alive: dict[str, float] = {}     # 이름 → 생성 시각(s)
        self.removing: set[str] = set()

        self.create_timer(1.0, self._publish_belt_speed)
        self.create_timer(1.0, self._check_lifetime)
        # spawn_period 주기 타이머를 직접 쓰지 않음: /clock 전에 만든 타이머는 첫 실행 뒤
        # 다음 실행이 sim 0 기준 격자에 맞춰져 사과 2개가 붙어서 생성됨 (spawn_schedule.py)
        self.schedule = SpawnSchedule(float(self._p('spawn_period')))
        self.create_timer(SPAWN_TICK, self._on_spawn_tick)

        self.add_on_set_parameters_callback(self._validate_params)
        self.add_post_set_parameters_callback(self._apply_params)

        self.get_logger().info(
            f'사과 스포너 시작 (mock={self.mock}, 모델={self.apple_model}, 속도={self._p("belt_speed")} m/s, '
            f'주기={self._p("spawn_period")} s)')

    def _p(self, name: str):
        return self.get_parameter(name).value

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    # ---------- 파라미터 실시간 변경 ----------
    def _validate_params(self, params: list[Parameter]) -> SetParametersResult:
        for p in params:
            if p.name == 'spawn_period' and not (
                    isinstance(p.value, (int, float)) and p.value > 0):
                return SetParametersResult(
                    successful=False, reason='spawn_period 는 0보다 커야 함')
            if p.name == 'belt_speed' and not isinstance(p.value, (int, float)):
                return SetParametersResult(
                    successful=False, reason='belt_speed 는 숫자여야 함')
        return SetParametersResult(successful=True)

    def _apply_params(self, params: list[Parameter]) -> None:
        for p in params:
            if p.name == 'belt_speed':
                self._publish_belt_speed()
                self.get_logger().info(f'벨트 속도 변경: {float(p.value):.3f} m/s')
            elif p.name == 'spawn_period':
                self.schedule.set_period(float(p.value))
                self.get_logger().info(f'사과 생성 주기 변경: {float(p.value):.2f} s')

    # ---------- 벨트 ----------
    def _publish_belt_speed(self) -> None:
        self.belt_pub.publish(Float64(data=float(self._p('belt_speed'))))

    # ---------- 생성 ----------
    def _on_spawn_tick(self) -> None:
        now = self._now()
        if self.schedule.due(now):
            self._spawn_apple(now)

    def _spawn_apple(self, now: float) -> None:
        if len(self.alive) >= self._p('max_apples'):
            self.get_logger().warning('사과 수가 max_apples 에 도달해 생성 건너뜀')
            return
        spec = random_apple(self.rng, self._p('radius_min'), self._p('radius_max'))
        yaw = self.yaw_rng.uniform(0.0, 2.0 * math.pi) if self.apple_model == 'ycb' else 0.0
        self.count += 1
        name = f'{APPLE_PREFIX}{self.count:04d}'
        if self.apple_model == 'ycb':
            look = f'ycb, yaw={math.degrees(yaw):.0f}°'
        else:
            look = f'rgb={tuple(round(c, 2) for c in spec.color)}'
        desc = f'{name} 생성 (t={now:.2f} s, r={spec.radius:.3f} m, {look})'

        if self.mock:
            self.get_logger().info(f'[mock] {desc}')
            return
        if not self.spawn_cli.service_is_ready():
            self.get_logger().warning('create 서비스 미준비 (Gazebo/브리지 확인) — 생성 건너뜀')
            return

        req = SpawnEntity.Request()
        req.entity_factory.name = name
        req.entity_factory.sdf = apple_sdf(name, spec, self.apple_model, yaw)
        req.entity_factory.pose.position.x = float(self._p('spawn_x'))
        req.entity_factory.pose.position.y = float(self._p('spawn_y'))
        # 구 바닥이 벨트 윗면보다 5mm 위에서 시작
        req.entity_factory.pose.position.z = float(self._p('belt_top_z')) + spec.radius + 0.005
        req.entity_factory.relative_to = 'world'
        self.alive[name] = now
        future = self.spawn_cli.call_async(req)
        future.add_done_callback(lambda f, n=name, d=desc: self._on_spawned(f, n, d))

    def _on_spawned(self, future, name: str, desc: str) -> None:
        res = future.result()
        if res is not None and res.success:
            self.get_logger().info(desc)
        else:
            self.alive.pop(name, None)
            self.get_logger().error(f'{name} 생성 실패')

    # ---------- 삭제 ----------
    def _on_sink(self, msg: LogicalCameraImage) -> None:
        """컨베이어 끝에서 떨어져 수거 지점 센서에 잡힌 사과 삭제."""
        detected = [m.name for m in msg.model]
        for name in names_to_remove(detected, self.alive, self.removing):
            self._remove(name)

    def _check_lifetime(self) -> None:
        now = self._now()
        limit = self._p('max_lifetime')
        if limit <= 0:          # 0 이하 = 사용 안 함
            return
        for name, born in list(self.alive.items()):
            if now - born > limit:
                self.get_logger().warning(f'{name} 수명 초과 → 삭제')
                self._remove(name)

    def _remove(self, name: str) -> None:
        if name in self.removing or self.mock:
            return
        if not self.remove_cli.service_is_ready():
            return
        self.removing.add(name)
        req = DeleteEntity.Request()
        req.entity.name = name
        req.entity.type = Entity.MODEL
        future = self.remove_cli.call_async(req)
        future.add_done_callback(lambda f, n=name: self._on_removed(f, n))

    def _on_removed(self, future, name: str) -> None:
        self.removing.discard(name)
        res = future.result()
        if res is not None and res.success:
            self.alive.pop(name, None)
            self.get_logger().info(f'{name} 삭제')
        else:
            self.get_logger().warning(f'{name} 삭제 실패 — 다음 위치 갱신 때 재시도')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AppleSpawnerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass  # Ctrl+C / launch 종료 시 조용히 종료
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
