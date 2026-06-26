cmake_minimum_required(VERSION 3.8)
project(brover_simulation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch meshes rviz urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/keyboard_teleop.py
    scripts/odom_pose2d_publisher.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
