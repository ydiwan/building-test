#!/usr/bin/env bash
# start zenoh router and aggregator
#   Usage: ./deploy/run_master.sh                  (floors default [1,2,3,4])
#          ./deploy/run_master.sh floors:='[3]'    (ex: while only floor 3 is online)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"

export PATH="/usr/bin:$PATH"
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_ROUTER_CHECK_ATTEMPTS=0
set +u
source /opt/ros/jazzy/setup.bash
source "$REPO/install/setup.bash"
set -u

# Set OCC_GLOBAL_HOST to connect this building's router UP to the central global router
if ! pgrep -f rmw_zenohd >/dev/null; then
  echo "starting master Zenoh router..."
  if [ -n "${OCC_GLOBAL_HOST:-}" ]; then
    echo "  -> connecting UP to global router ${OCC_GLOBAL_HOST}:7447"
    ZENOH_ROUTER_CONFIG_URI="$REPO/deploy/zenoh/master_router.json5" \
    ZENOH_CONFIG_OVERRIDE="connect/endpoints=[\"tcp/${OCC_GLOBAL_HOST}:7447\"]" \
      ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/rmw_zenohd.log 2>&1 &
  else
    ZENOH_ROUTER_CONFIG_URI="$REPO/deploy/zenoh/master_router.json5" \
      ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/rmw_zenohd.log 2>&1 &
  fi
  sleep 3
fi
exec ros2 launch occ_building building_master.launch.py "$@"
