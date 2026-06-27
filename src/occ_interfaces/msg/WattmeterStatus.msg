# A single INA219 wattmeter reading.
string  location "N/A"     # human label, e.g. "lobby", "floor_1_front"
uint8   idx                # index of this wattmeter
float64 shunt_voltage_mv
float64 bus_voltage_v
float64 current_ma
float64 power_mw
