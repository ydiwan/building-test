cmake_minimum_required(VERSION 3.8)
project(occ_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)

# Generate interfaces
rosidl_generate_interfaces(${PROJECT_NAME}
  # DB uplink (schema-agnostic ingest)
  "msg/CityIngest.msg"
  # Per-device records (reuse PoC field conventions)
  "msg/Aht20Status.msg"
  "msg/WattmeterStatus.msg"
  "msg/PirStatus.msg"
  "msg/LedStatus.msg"
  "msg/WindowStatus.msg"
  # Per-floor state wrappers (GUI-facing typed topics)
  "msg/EnvironmentState.msg"
  "msg/PowerState.msg"
  "msg/MotionState.msg"
  "msg/LightingState.msg"
  "msg/WindowState.msg"
  # Actuator control services
  "srv/SetLeds.srv"
  "srv/SetWindows.srv"
  "srv/SetLightingMode.srv"
  DEPENDENCIES std_msgs
)

ament_package()
