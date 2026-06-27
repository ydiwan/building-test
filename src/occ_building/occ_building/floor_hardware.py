"""Per-floor-Pi hardware node.

Owns one floor's hardware (via a FloorDriver), publishes per-group typed state on
`<building>/floor_<n>/<group>/state`, and serves control services. One node per
floor Pi serializes the shared I2C bus in-process.

Adds two stateful behaviours, both driven by a fast control timer:
  * Windows (servo-backed): named presets (closed/open_in/open_out, angles from
    config) + manual angle, swept smoothly at a single configurable speed.
  * Lighting modes: manual / motion_auto / off. In motion_auto a PIR turns all
    floor lights to `on_brightness` for `hold_time`, then fades to 0 over
    `fade_time` (retrigger resets). manual = SetLeds controls; off = disabled.

Conversion to a lifecycle node stays cheap: all work is in configure/activate/
deactivate/cleanup (see git history / REWRITE_PLAN.md).
"""
import signal
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile

from std_msgs.msg import Header

from occ_interfaces.msg import (
    Aht20Status, EnvironmentState, LedStatus, LightingState, MotionState,
    PirStatus, PowerState, WattmeterStatus, WindowState, WindowStatus,
)
from occ_interfaces.srv import SetLeds, SetLightingMode, SetWindows

# Latched "latest state": a late-joining GUI immediately gets current values.
LATCHED = QoSProfile(
    depth=1,
    history=HistoryPolicy.KEEP_LAST,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

LIGHTING_MODES = ('manual', 'motion_auto', 'off')


class FloorHardware(Node):
    def __init__(self):
        super().__init__('floor_hardware')
        self.declare_parameter('building_name', 'hospital')
        self.declare_parameter('floor', 1)
        self.declare_parameter('sample_time', 2.0)       # sensor publish period
        self.declare_parameter('control_period', 0.05)   # actuator (sweep/fade) tick
        self.declare_parameter('driver', 'real')         # 'real' on a Pi; 'mock' for dev
        # hardware counts
        self.declare_parameter('aht20_count', 4)
        self.declare_parameter('wattmeter_count', 1)
        self.declare_parameter('pir_pins', [18])
        self.declare_parameter('led_count', 4)
        self.declare_parameter('window_count', 9)
        # window presets (degrees) + sweep speed
        self.declare_parameter('window_preset_closed', 90)
        self.declare_parameter('window_preset_open_in', 170)
        self.declare_parameter('window_preset_open_out', 10)
        self.declare_parameter('window_sweep_deg_per_sec', 60.0)
        # lighting
        self.declare_parameter('lighting_mode', 'manual')
        self.declare_parameter('lighting_on_brightness', 0.8)
        self.declare_parameter('lighting_hold_time', 10.0)   # X seconds
        self.declare_parameter('lighting_fade_time', 3.0)    # Y seconds

        self._driver = None
        self._sample_timer = None
        self._control_timer = None
        self._frame_id = ''

        self.configure()
        self.activate()

    @staticmethod
    def _make_driver(kind, hw):
        """Lazily import the chosen driver: the node needs neither the hardware
        libs nor the mock unless that driver is actually selected."""
        if kind in ('real', 'hardware'):
            from occ_building.drivers.real import RealFloorDriver
            return RealFloorDriver(**hw)
        if kind == 'mock':
            from occ_building.drivers.mock import MockFloorDriver
            return MockFloorDriver(**hw)
        raise RuntimeError(f"unknown driver '{kind}' (expected 'real' or 'mock')")

    # --- lifecycle-shaped methods ------------------------------------------
    def configure(self):
        gp = self.get_parameter
        self._frame_id = f"{gp('building_name').value}/floor_{gp('floor').value}"
        self._sample_time = float(gp('sample_time').value)
        self._control_period = float(gp('control_period').value)

        self._led_count = int(gp('led_count').value)
        self._win_count = int(gp('window_count').value)
        self._presets = {
            'closed': int(gp('window_preset_closed').value),
            'open_in': int(gp('window_preset_open_in').value),
            'open_out': int(gp('window_preset_open_out').value),
        }
        self._sweep_speed = float(gp('window_sweep_deg_per_sec').value)

        self._mode = gp('lighting_mode').value
        if self._mode not in LIGHTING_MODES:
            self._mode = 'manual'
        self._on_brightness = float(gp('lighting_on_brightness').value)
        self._hold_time = float(gp('lighting_hold_time').value)
        self._fade_time = float(gp('lighting_fade_time').value)

        self._driver = self._make_driver(gp('driver').value, dict(
            aht20=gp('aht20_count').value,
            wattmeter=gp('wattmeter_count').value,
            pir_pins=list(gp('pir_pins').value),
            leds=self._led_count,
            servos=self._win_count,
        ))

        # window sweep state: start every window closed
        closed = float(self._presets['closed'])
        self._win_current = {i: closed for i in range(self._win_count)}
        self._win_target = {i: closed for i in range(self._win_count)}
        self._win_state = {i: 'closed' for i in range(self._win_count)}

        # motion-auto lighting state
        self._auto_phase = 'idle'     # idle | on | fading
        self._auto_level = 0.0
        self._hold_until = 0.0
        self._fade_start = 0.0
        self._fade_from = 0.0

        # publishers
        self._env_pub = self.create_publisher(EnvironmentState, 'environment/state', LATCHED)
        self._pow_pub = self.create_publisher(PowerState, 'power/state', LATCHED)
        self._mot_pub = self.create_publisher(MotionState, 'motion/state', LATCHED)
        self._led_pub = self.create_publisher(LightingState, 'lighting/state', LATCHED)
        self._win_pub = self.create_publisher(WindowState, 'windows/state', LATCHED)

        # services
        self._set_leds_srv = self.create_service(SetLeds, 'lighting/set', self._on_set_leds)
        self._set_mode_srv = self.create_service(SetLightingMode, 'lighting/set_mode', self._on_set_mode)
        self._set_win_srv = self.create_service(SetWindows, 'windows/set', self._on_set_windows)
        self.get_logger().info(
            f'configured ({self._frame_id}, driver={gp("driver").value}, mode={self._mode})')

    def activate(self):
        # drive windows to their initial (closed) angle and seed latched state
        self._driver.set_servos({i: int(self._win_current[i]) for i in range(self._win_count)})
        if self._mode == 'off':
            self._set_all_leds(0.0)
        self._publish_windows()
        self._publish_lighting()
        self._sample_timer = self.create_timer(self._sample_time, self._sample)
        self._control_timer = self.create_timer(self._control_period, self._control)
        self.get_logger().info('active')

    def deactivate(self):
        for t in (self._sample_timer, self._control_timer):
            if t is not None:
                self.destroy_timer(t)
        self._sample_timer = self._control_timer = None
        self.get_logger().info('deactivated')

    def cleanup(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None
        self.get_logger().info('cleaned up')

    # --- sensor sampling ---------------------------------------------------
    def _header(self) -> Header:
        h = Header()
        h.stamp = self.get_clock().now().to_msg()
        h.frame_id = self._frame_id
        return h

    def _sample(self):
        env = EnvironmentState(header=self._header())
        env.sensors = [
            Aht20Status(location=r.location, idx=r.idx,
                        temperature=r.temperature, relative_humidity=r.relative_humidity)
            for r in self._driver.read_environment()]
        self._env_pub.publish(env)

        pw = PowerState(header=self._header())
        pw.sensors = [
            WattmeterStatus(location=r.location, idx=r.idx,
                            shunt_voltage_mv=r.shunt_voltage_mv, bus_voltage_v=r.bus_voltage_v,
                            current_ma=r.current_ma, power_mw=r.power_mw)
            for r in self._driver.read_power()]
        self._pow_pub.publish(pw)

        mo = MotionState(header=self._header())
        mo.sensors = [PirStatus(location=r.location, pin=r.pin, state=r.state)
                      for r in self._driver.read_motion()]
        self._mot_pub.publish(mo)

    # --- actuator control tick (windows + lighting) ------------------------
    def _control(self):
        self._sweep_windows()
        self._update_lighting()

    def _sweep_windows(self):
        step = self._sweep_speed * self._control_period
        moved = {}
        for i in range(self._win_count):
            cur, tgt = self._win_current[i], self._win_target[i]
            if cur == tgt:
                continue
            if abs(tgt - cur) <= step:
                cur = tgt
            else:
                cur += step if tgt > cur else -step
            self._win_current[i] = cur
            moved[i] = int(round(cur))
        if moved:
            self._driver.set_servos(moved)
            self._publish_windows()

    def _update_lighting(self):
        if self._mode == 'manual':
            return  # SetLeds is in charge
        if self._mode == 'off':
            if any(v > 0.0 for _, v in self._driver.get_leds()):
                self._set_all_leds(0.0)
                self._publish_lighting()
            return

        # motion_auto
        now = time.monotonic()
        motion = any(r.state for r in self._driver.read_motion())
        if motion:
            if self._auto_phase != 'on' or self._auto_level != self._on_brightness:
                self._auto_level = self._on_brightness
                self._set_all_leds(self._auto_level)
                self._publish_lighting()
            self._auto_phase = 'on'
            self._hold_until = now + self._hold_time
            return
        if self._auto_phase == 'on' and now >= self._hold_until:
            self._auto_phase = 'fading'
            self._fade_start = now
            self._fade_from = self._auto_level
        if self._auto_phase == 'fading':
            elapsed = now - self._fade_start
            if elapsed >= self._fade_time or self._fade_time <= 0.0:
                level, self._auto_phase = 0.0, 'idle'
            else:
                level = self._fade_from * (1.0 - elapsed / self._fade_time)
            if abs(level - self._auto_level) > 1e-3 or (level == 0.0 and self._auto_level != 0.0):
                self._auto_level = level
                self._set_all_leds(level)
                self._publish_lighting()

    def _set_all_leds(self, level):
        self._driver.set_leds({i: level for i in range(self._led_count)})

    # --- publishing --------------------------------------------------------
    def _publish_lighting(self):
        msg = LightingState(header=self._header(), mode=self._mode)
        msg.leds = [LedStatus(idx=i, value=v) for i, v in self._driver.get_leds()]
        self._led_pub.publish(msg)

    def _publish_windows(self):
        msg = WindowState(header=self._header())
        msg.windows = [WindowStatus(idx=i, state=self._win_state[i],
                                    angle=int(round(self._win_current[i])))
                       for i in range(self._win_count)]
        self._win_pub.publish(msg)

    # --- services ----------------------------------------------------------
    def _on_set_leds(self, request, response):
        if self._mode != 'manual':
            response.success = False
            self.get_logger().warn(f'lighting/set ignored: mode is {self._mode}, not manual')
            return response
        applied = self._driver.set_leds({led.idx: led.value for led in request.leds})
        response.success = len(applied) == len(request.leds)
        response.confirmed_idxs = list(applied.keys())
        response.confirmed_values = list(applied.values())
        self._publish_lighting()
        return response

    def _on_set_mode(self, request, response):
        mode = request.mode
        if mode not in LIGHTING_MODES:
            response.success = False
            response.mode = self._mode
            return response
        self._mode = mode
        if mode == 'off':
            self._set_all_leds(0.0)
        elif mode == 'motion_auto':
            self._auto_phase, self._auto_level = 'idle', 0.0
            self._set_all_leds(0.0)
        self._publish_lighting()
        response.success = True
        response.mode = mode
        self.get_logger().info(f'lighting mode -> {mode}')
        return response

    def _on_set_windows(self, request, response):
        ok_idxs, ok_angles, ok_states = [], [], []
        for w in request.windows:
            i = w.idx
            if not (0 <= i < self._win_count):
                continue
            label = w.state
            if label in self._presets:
                angle = self._presets[label]
            elif label in ('', 'custom'):
                angle = max(0, min(180, int(w.angle)))
                label = 'custom'
            else:
                continue  # unknown preset name
            self._win_target[i] = float(angle)
            self._win_state[i] = label
            ok_idxs.append(i)
            ok_angles.append(angle)
            ok_states.append(label)
        response.success = len(ok_idxs) == len(request.windows)
        response.confirmed_idxs = ok_idxs
        response.confirmed_angles = ok_angles
        response.confirmed_states = ok_states
        return response


def main(args=None):
    rclpy.init(args=args)
    node = FloorHardware()
    signal.signal(signal.SIGTERM, lambda *_: rclpy.shutdown())
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.deactivate()
        node.cleanup()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
