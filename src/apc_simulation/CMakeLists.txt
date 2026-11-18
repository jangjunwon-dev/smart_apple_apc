cmake_minimum_required(VERSION 3.8)
project(apc_simulation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# 파이썬 모듈(apc_simulation/) 설치
ament_python_install_package(${PROJECT_NAME})

# 노드 실행 파일 (ros2 run apc_simulation apple_spawner_node)
install(PROGRAMS scripts/apple_spawner_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch worlds config
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_apple_factory test/test_apple_factory.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}
  )
endif()

ament_package()
