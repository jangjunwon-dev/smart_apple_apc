cmake_minimum_required(VERSION 3.10)
project(apc_simulation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# 파이썬 모듈(apc_simulation/) 설치
ament_python_install_package(${PROJECT_NAME})

# 노드 실행 파일 (ros2 run apc_simulation apple_spawner_node)
install(PROGRAMS scripts/apple_spawner_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch worlds config models
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_apple_factory test/test_apple_factory.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  # 사과 생성 간격 계산 (/clock 전 타이머 위상 문제 회귀 테스트)
  ament_add_pytest_test(test_spawn_schedule test/test_spawn_schedule.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
  # 월드 구역 좌표 ↔ apc_amr/config/zones.yaml 일치 검사
  ament_add_pytest_test(test_zones_consistency test/test_zones_consistency.py)
endif()

ament_package()
