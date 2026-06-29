#!/usr/bin/env bash
# start zenoh router pointing to master and launch floor.launch,py
#   Usage: ./deploy/run_floor.sh <floor_number>
set -u
OCC_MASTER_HOST="10.213.1.90" # hospital master
FLOOR="${1:?usage: run_floor.sh <floor_number>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MASTER="${OCC_MASTER_HOST:-hospital-master}"

export PATH="/usr/bin:$PATH"
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_ROUTER_CHECK_ATTEMPTS=0
set +u
source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"
set -u

if ! pgrep -f rmw_zenohd >/dev/null; then
  echo "starting floor Zenoh router (-> ${MASTER}:7447) ..."
  ZENOH_ROUTER_CONFIG_URI="$REPO/deploy/zenoh/floor_router.json5" \
  ZENOH_CONFIG_OVERRIDE="connect/endpoints=[\"tcp/${MASTER}:7447\"]" \
    ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/rmw_zenohd.log 2>&1 &
  sleep 3
fi
exec ros2 launch occ_building floor.launch.py floor:="$FLOOR"
