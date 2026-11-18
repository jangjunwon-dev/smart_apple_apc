# Copilot 지침

이 저장소의 공통 AI 지침은 루트의 `AGENTS.md` 입니다. 반드시 그 규칙을 따르세요.

핵심 요약:
- 환경 고정: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic(ros_gz). Humble/Gazebo Classic 코드 금지.
- `src/apc_interfaces` 메시지·토픽 이름은 팀 합의 없이 수정 금지.
- 모든 노드는 `mock` 파라미터 유지.
- 주석·로그는 한국어, 식별자는 영어 snake_case, PEP 8(줄 길이 99).
- 빌드: `python -m colcon build --symlink-install` (venv 활성화 상태).
