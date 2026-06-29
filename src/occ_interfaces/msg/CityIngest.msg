# ROS2 Standard
std_msgs/Header header

# metadata used for InfluxDB tagging and filtering
string system_type      # ex: "building", "uav", "mechanical", "infrastructure"
string system_id        # ex: "hospital_f2", "drone_01", "factory_arm1"
string data_type        # ex: "telemetry", "state", "event", "diagnostics"

# Combines all sensor readings or system states into a single string.
string data_json