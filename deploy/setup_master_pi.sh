#!/usr/bin/env bash
# Setup for the building-master Pi (Ubuntu 24.04 + ROS 2 Jazzy).
# The master has NO floor hardware: it runs the aggregator node + the building's
# Zenoh router. So it only needs the Zenoh middleware (no adafruit/gpio deps).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== apt: rmw_zenoh + colcon =="
sudo apt-get update
sudo apt-get install -y ros-jazzy-rmw-zenoh-cpp python3-colcon-common-extensions

echo
echo "DONE. Build + run the master:"
echo "  cd $REPO_ROOT && export PATH=/usr/bin:\$PATH && source /opt/ros/jazzy/setup.bash"
echo "  colcon build && source install/setup.bash"
echo "  ./deploy/run_master.sh"
