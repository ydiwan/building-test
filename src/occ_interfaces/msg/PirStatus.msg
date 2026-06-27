# A single PIR motion sensor reading.
string location "N/A"   # human label, e.g. "lobby", "floor_1_front"
uint8  pin              # BCM/GPIO pin number
bool   state            # true = motion detected (includes hold delay)
