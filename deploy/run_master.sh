#!/usr/bin/env bash
# Bring up the building master: start the master Zenoh router (top of the tree for
# now) if needed, then launch the aggregator node under rmw_zenoh.
#
#   Usage: ./deploy/run_master.sh                  (floors default [1,2,3,4])
#          ./deploy/run_master.sh floors:='[1]'    (e.g. while only floor 1 is up)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"

export PATH="/usr/bin:$PATH"
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_ROUTER_CHECK_ATTEMPTS=0
source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"

if ! pgrep -f rmw_zenohd >/dev/null; then
  echo "starting master Zenoh router ..."
  ZENOH_ROUTER_CONFIG_URI="$REPO/deploy/zenoh/master_router.json5" \
    ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/rmw_zenohd.log 2>&1 &
  sleep 3
fi
exec ros2 launch occ_building building_master.launch.py "$@"
