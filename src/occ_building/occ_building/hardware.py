import time
from dataclasses import dataclass
from threading import Lock, Thread

import adafruit_ahtx0
import adafruit_tca9548a
import adafruit_tlc59711
import board
import busio
from adafruit_motor import servo as _servo
from adafruit_pca9685 import PCA9685
from gpiozero import DigitalInputDevice

from occ_building.ina219 import INA219

_MUX_ADDRESSES = [0x71 + i for i in range(8)]
_SENSORS_PER_MUX = 4
_INA219_ADDRESSES = [0x40, 0x41, 0x44, 0x45]
_PCA9685_ADDRESS = 0x46
_SERVO_MIN_PULSE = 750
_SERVO_MAX_PULSE = 2250
_TLC_PIXELS = 4
_PIR_POLL_S = 0.1


@dataclass
class Aht20Reading:
    idx: int
    temperature: float
    relative_humidity: float
    location: str = "N/A"


@dataclass
class WattmeterReading:
    idx: int
    shunt_voltage_mv: float
    bus_voltage_v: float
    current_ma: float
    power_mw: float
    location: str = "N/A"


@dataclass
class PirReading:
    pin: int
    state: bool
    location: str = "N/A"


class _LedBoard(adafruit_tlc59711.TLC59711):
    def set_channel(self, channel_index, value):
        max_channels = _TLC_PIXELS * 3
        v = int(max(0.0, min(1.0, value)) * 65535)
        start = self._buffer_index_lookuptable[max_channels - 1 - channel_index]
        self._buffer[start] = (v >> 8) & 0xFF
        self._buffer[start + 1] = v & 0xFF


class Hardware:
    def __init__(self, *, aht20=4, wattmeter=1, pir_pins=(18,), leds=4, servos=9,
                 motion_delay=3, pca_address=_PCA9685_ADDRESS,
                 servo_min_pulse=_SERVO_MIN_PULSE, servo_max_pulse=_SERVO_MAX_PULSE):
        self._i2c = board.I2C()

        self._aht20 = []
        idx = 0
        num_mux = ((int(aht20) - 1) // _SENSORS_PER_MUX + 1) if aht20 else 0
        for m in range(num_mux):
            mux = adafruit_tca9548a.TCA9548A(self._i2c, address=_MUX_ADDRESSES[m])
            for ch in range(_SENSORS_PER_MUX):
                if idx >= int(aht20):
                    break
                self._aht20.append(adafruit_ahtx0.AHTx0(mux[ch]))
                idx += 1

        self._wattmeters = []
        for i in range(int(wattmeter)):
            ina = INA219(1, _INA219_ADDRESSES[i])
            while not ina.begin():
                time.sleep(2)
            ina.linear_cal(1000, 1000)
            self._wattmeters.append(ina)

        self._pir_pins = list(pir_pins)
        self._motion_delay = max(0, int(motion_delay) - 2)
        self._pir = {}
        self._pir_dev = {}
        for pin in self._pir_pins:
            self._pir_dev[pin] = DigitalInputDevice(pin, pull_up=False)
            self._pir[pin] = {'state': False, 'last': 0.0, 'lock': Lock()}
        self._pir_run = True
        for pin in self._pir_pins:
            Thread(target=self._pir_loop, args=(pin,), daemon=True).start()

        self._led_count = int(leds)
        self._led_levels = {i: 0.0 for i in range(self._led_count)}
        self._tlc = None
        if self._led_count:
            spi = busio.SPI(board.SCK, MOSI=board.MOSI)
            self._tlc = _LedBoard(spi, pixel_count=_TLC_PIXELS)
            for ch in self._led_levels:
                self._tlc.set_channel(ch, 0.0)
            self._tlc.show()

        self._servo_count = int(servos)
        self._servo_angles = {}
        self._servos = []
        self._pca = None
        if self._servo_count:
            self._pca = PCA9685(self._i2c, address=pca_address)
            self._pca.frequency = 50
            for i in range(self._servo_count):
                s = _servo.Servo(self._pca.channels[i],
                                 min_pulse=servo_min_pulse, max_pulse=servo_max_pulse)
                s.angle = 90
                self._servos.append(s)
                self._servo_angles[i] = 90

    def _pir_loop(self, pin):
        st = self._pir[pin]
        dev = self._pir_dev[pin]
        while self._pir_run:
            if dev.value:
                with st['lock']:
                    st['state'] = True
                    st['last'] = time.time()
            else:
                with st['lock']:
                    if st['state'] and (time.time() - st['last'] >= self._motion_delay):
                        st['state'] = False
            time.sleep(_PIR_POLL_S)

    def read_environment(self):
        return [Aht20Reading(idx=i, temperature=float(s.temperature),
                             relative_humidity=float(s.relative_humidity))
                for i, s in enumerate(self._aht20)]

    def read_power(self):
        return [WattmeterReading(idx=i, shunt_voltage_mv=float(w.get_shunt_voltage_mV()),
                                 bus_voltage_v=float(w.get_bus_voltage_V()),
                                 current_ma=float(w.get_current_mA()),
                                 power_mw=float(w.get_power_mW()))
                for i, w in enumerate(self._wattmeters)]

    def read_motion(self):
        out = []
        for pin in self._pir_pins:
            with self._pir[pin]['lock']:
                out.append(PirReading(pin=pin, state=bool(self._pir[pin]['state'])))
        return out

    def get_leds(self):
        return sorted(self._led_levels.items())

    def set_leds(self, values):
        applied = {}
        for idx, val in values.items():
            if 0 <= idx < self._led_count:
                v = max(0.0, min(1.0, float(val)))
                self._led_levels[idx] = v
                self._tlc.set_channel(idx, v)
                applied[idx] = v
        if applied and self._tlc is not None:
            self._tlc.show()
        return applied

    def get_servos(self):
        return sorted(self._servo_angles.items())

    def set_servos(self, angles):
        applied = {}
        for idx, ang in angles.items():
            if 0 <= idx < self._servo_count:
                a = max(0, min(180, int(ang)))
                self._servos[idx].angle = a
                self._servo_angles[idx] = a
                applied[idx] = a
        return applied

    def close(self):
        self._pir_run = False
        if self._pca is not None:
            try:
                self._pca.deinit()
            except Exception:
                pass
        for dev in self._pir_dev.values():
            try:
                dev.close()
            except Exception:
                pass
