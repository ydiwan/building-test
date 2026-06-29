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
  "msg/CityIngest.msg"
  "msg/Aht20Status.msg"
  "msg/WattmeterStatus.msg"
  "msg/PirStatus.msg"
  "msg/LedStatus.msg"
  "msg/WindowStatus.msg"
  "msg/EnvironmentState.msg"
  "msg/PowerState.msg"
  "msg/MotionState.msg"
  "msg/LightingState.msg"
  "msg/WindowState.msg"
  "srv/SetLeds.srv"
  "srv/SetWindows.srv"
  "srv/SetLightingMode.srv"
  DEPENDENCIES std_msgs
)

ament_package()
