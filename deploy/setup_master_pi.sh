#!/usr/bin/env bash
# quick setup for the building-master Pi
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "apt: rmw_zenoh + colcon"
sudo apt-get update
sudo apt-get install -y ros-jazzy-rmw-zenoh-cpp python3-colcon-common-extensions

echo
echo "ALL DONE. Build + run the master:"
echo "colcon build && source install/setup.bash"
echo "./deploy/run_master.sh"
