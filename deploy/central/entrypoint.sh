#!/usr/bin/env bash
# Shared entrypoint for the central image
set -e
source /opt/ros/jazzy/setup.bash
[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export ZENOH_ROUTER_CHECK_ATTEMPTS="${ZENOH_ROUTER_CHECK_ATTEMPTS:-0}"
if [ -n "${OCC_ZENOH_CONNECT:-}" ]; then
  export ZENOH_CONFIG_OVERRIDE="connect/endpoints=[\"${OCC_ZENOH_CONNECT}\"]"
fi
exec "$@"
