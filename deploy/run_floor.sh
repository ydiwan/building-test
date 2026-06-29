#!/usr/bin/env bash
# Bring a floor Pi onto the Zenoh fabric: start the local Zenoh router (-> building
# master) if needed, then launch the floor node under rmw_zenoh.
#
#   Usage: ./deploy/run_floor.sh <floor_number>
#   Override the master host if it isn't 'hospital-master':  OCC_MASTER_HOST=192.168.1.50 ./deploy/run_floor.sh 1
set +u
FLOOR="${1:?usage: run_floor.sh <floor_number>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MASTER="${OCC_MASTER_HOST:-hospital-master}"

export PATH="/usr/bin:$PATH"
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_ROUTER_CHECK_ATTEMPTS=0          # node waits for its local router
source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"

if ! pgrep -f rmw_zenohd >/dev/null; then
  echo "starting floor Zenoh router (-> ${MASTER}:7447) ..."
  ZENOH_ROUTER_CONFIG_URI="$REPO/deploy/zenoh/floor_router.json5" \
  ZENOH_CONFIG_OVERRIDE="connect/endpoints=[\"tcp/${MASTER}:7447\"]" \
    ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/rmw_zenohd.log 2>&1 &
  sleep 3
fi
exec ros2 launch occ_building floor.launch.py floor:="$FLOOR"
