"""Simulated floor hardware so the whole node + topic/service contract can be
developed and verified on a dev PC with no Pi attached. Real drivers (INA219,
AHT20 mux, PCA9685, TLC59711, PIR) drop in behind the same FloorDriver API.
"""
import random
import time

from .base import Aht20Reading, FloorDriver, PirReading, WattmeterReading


class MockFloorDriver(FloorDriver):
    def __init__(self, *, aht20=4, wattmeter=1, pir_pins=(18,), leds=4, servos=9):
        self._aht20 = int(aht20)
        self._wattmeter = int(wattmeter)
        self._pir_pins = list(pir_pins)
        self._leds = {i: 0.0 for i in range(int(leds))}
        self._servos = {i: 0 for i in range(int(servos))}

    def read_environment(self):
        return [
            Aht20Reading(idx=i,
                         temperature=round(random.uniform(21.0, 24.0), 2),
                         relative_humidity=round(random.uniform(40.0, 50.0), 2))
            for i in range(self._aht20)
        ]

    def read_power(self):
        out = []
        for i in range(self._wattmeter):
            current = round(random.uniform(100.0, 600.0), 1)
            bus = round(random.uniform(4.9, 5.2), 3)
            out.append(WattmeterReading(
                idx=i,
                shunt_voltage_mv=round(current * 0.01, 3),
                bus_voltage_v=bus,
                current_ma=current,
                power_mw=round(bus * current, 1),
            ))
        return out

    def read_motion(self):
        # Deterministic square wave (6 s active / 10 s idle) so motion-auto lighting
        # (on -> hold -> fade) can be observed without real hardware.
        active = (time.monotonic() % 16.0) < 6.0
        return [PirReading(pin=p, state=active) for p in self._pir_pins]

    def get_leds(self):
        return sorted(self._leds.items())

    def set_leds(self, values):
        applied = {}
        for idx, val in values.items():
            if idx in self._leds:
                clamped = max(0.0, min(1.0, float(val)))
                self._leds[idx] = clamped
                applied[idx] = clamped
        return applied

    def get_servos(self):
        return sorted(self._servos.items())

    def set_servos(self, angles):
        applied = {}
        for idx, ang in angles.items():
            if idx in self._servos:
                clamped = max(0, min(180, int(ang)))
                self._servos[idx] = clamped
                applied[idx] = clamped
        return applied
