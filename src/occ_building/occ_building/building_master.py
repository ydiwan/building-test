import json
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile

from occ_interfaces.msg import CityIngest, EnvironmentState, MotionState, PowerState

LATCHED = QoSProfile(depth=1, history=HistoryPolicy.KEEP_LAST,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)

class BuildingMaster(Node):
    def __init__(self):
        super().__init__('building_master')
        self.declare_parameter('building_name', 'hospital')
        self.declare_parameter('floors', [1, 2, 3, 4])
        self.declare_parameter('publish_period', 2.0)
        self._building = self.get_parameter('building_name').value
        floors = list(self.get_parameter('floors').value)
        period = float(self.get_parameter('publish_period').value)
        self._latest = {f: {} for f in floors}
        for f in floors:
            base = f'/{self._building}/floor_{f}'
            self.create_subscription(EnvironmentState, f'{base}/environment/state',
                                     lambda m, f=f: self._store(f, 'environment', self._env(m)), LATCHED)
            self.create_subscription(PowerState, f'{base}/power/state',
                                     lambda m, f=f: self._store(f, 'power', self._power(m)), LATCHED)
            self.create_subscription(MotionState, f'{base}/motion/state',
                                     lambda m, f=f: self._store(f, 'motion', self._motion(m)), LATCHED)
        topic = f'occ/ingest/building/{self._building}/telemetry'
        self._ingest_pub = self.create_publisher(CityIngest, topic, 10)
        self.create_timer(period, self._publish)
        self.get_logger().info(f'building_master up: {self._building}, floors={floors} -> {topic}')

    @staticmethod
    def _env(msg):
        return [{'idx': s.idx, 'location': s.location, 'temperature': s.temperature,
                 'relative_humidity': s.relative_humidity} for s in msg.sensors]

    @staticmethod
    def _power(msg):
        return [{'idx': s.idx, 'location': s.location, 'bus_voltage_v': s.bus_voltage_v,
                 'current_ma': s.current_ma, 'power_mw': s.power_mw} for s in msg.sensors]

    @staticmethod
    def _motion(msg):
        return [{'pin': s.pin, 'location': s.location, 'state': s.state} for s in msg.sensors]

    def _store(self, floor, group, data):
        self._latest[floor][group] = data

    def _publish(self):
        payload = {f'floor_{f}': g for f, g in self._latest.items() if g}
        if not payload:
            return
        msg = CityIngest()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.system_type = 'building'
        msg.system_id = self._building
        msg.data_type = 'telemetry'
        msg.data_json = json.dumps(payload)
        self._ingest_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = BuildingMaster()
    signal.signal(signal.SIGTERM, lambda *_: rclpy.shutdown())
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
