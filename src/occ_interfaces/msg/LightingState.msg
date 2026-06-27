# All LED channel levels for one floor, plus the active lighting mode.
# Published latched on <building>/floor_<n>/lighting/state.
std_msgs/Header header
string          mode    # "manual" | "motion_auto" | "off"
LedStatus[]     leds
