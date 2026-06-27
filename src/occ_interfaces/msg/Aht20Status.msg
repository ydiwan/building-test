# A single AHT20 temperature/humidity sensor reading (behind the floor I2C mux).
string  location "N/A"     # human label, e.g. "lobby", "floor_1_front"
uint8   idx                # index of this sensor on the multiplexer
float64 temperature        # degrees Celsius
float64 relative_humidity  # percent (0-100)
