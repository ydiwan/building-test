import json
import os
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from occ_interfaces.msg import CityIngest

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None

INGEST_PREFIX = '/occ/ingest/'
CITYINGEST_TYPE = 'occ_interfaces/msg/CityIngest'
TAG_KEYS = {'idx', 'pin', 'id', 'channel', 'index'}


class CitySink(Node):
    def __init__(self):
        super().__init__('city_sink')
        self.declare_parameter('influx_url', os.environ.get('INFLUXDB_URL', 'http://localhost:8086'))
        self.declare_parameter('influx_token', os.environ.get('INFLUXDB_TOKEN', ''))
        self.declare_parameter('influx_org', os.environ.get('INFLUXDB_ORG', 'occ'))
        self.declare_parameter('influx_bucket', os.environ.get('INFLUXDB_BUCKET', 'occ'))
        self.declare_parameter('discovery_period', 5.0)

        self._url = self.get_parameter('influx_url').value
        self._token = self.get_parameter('influx_token').value
        self._org = self.get_parameter('influx_org').value
        self._bucket = self.get_parameter('influx_bucket').value

        self._client = None
        self._write_api = None
        self._connect()

        self._subscribed = set()
        self.create_timer(float(self.get_parameter('discovery_period').value), self._discover)
        self._discover()
        self.get_logger().info(
            f'city_sink up: {self._url} org={self._org} bucket={self._bucket}, '
            f'watching {INGEST_PREFIX}+/+/+')

    def _connect(self):
        if InfluxDBClient is None:
            self.get_logger().error('influxdb_client not installed; writes will be dropped')
            return
        try:
            self._client = InfluxDBClient(url=self._url, token=self._token, org=self._org)
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'InfluxDB connect failed ({exc}); will retry on write')
            self._client = self._write_api = None

    def _discover(self):
        for name, types in self.get_topic_names_and_types():
            if name in self._subscribed or not name.startswith(INGEST_PREFIX):
                continue
            if CITYINGEST_TYPE not in types:
                continue
            self.create_subscription(CityIngest, name, self._on_ingest, 10)
            self._subscribed.add(name)
            self.get_logger().info(f'subscribed: {name}')

    def _on_ingest(self, msg):
        try:
            data = json.loads(msg.data_json) if msg.data_json else {}
        except json.JSONDecodeError as exc:
            self.get_logger().warn(f'bad data_json from {msg.system_id}: {exc}')
            return
        ts = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        if ts == 0:
            ts = None
        base_tags = {'system_type': msg.system_type or 'unknown',
                     'system_id': msg.system_id or 'unknown',
                     'data_type': msg.data_type or 'unknown'}
        points = []
        self._walk(data, '', base_tags, points, msg.system_type or 'ingest', ts)
        self._write(points)

    def _walk(self, node, path, tags, points, measurement, ts):
        if isinstance(node, dict):
            fields = {}
            local_tags = dict(tags)
            children = []
            for key, val in node.items():
                if isinstance(val, (dict, list)):
                    children.append((self._join(path, key), val))
                elif isinstance(val, bool):
                    fields[key] = val
                elif isinstance(val, (int, float)):
                    if key in TAG_KEYS:
                        local_tags[key] = str(val)
                    else:
                        fields[key] = float(val)
                elif isinstance(val, str):
                    local_tags[key] = val
            if fields:
                pt = dict(local_tags)
                if path:
                    pt['path'] = path
                points.append((measurement, pt, fields, ts))
            for cpath, cval in children:
                self._walk(cval, cpath, local_tags, points, measurement, ts)
        elif isinstance(node, list):
            for elem in node:
                self._walk(elem, path, tags, points, measurement, ts)

    @staticmethod
    def _join(path, key):
        return f'{path}/{key}' if path else str(key)

    def _write(self, points):
        if not points:
            return
        if self._write_api is None:
            self._connect()
            if self._write_api is None:
                return
        records = []
        for measurement, tags, fields, ts in points:
            pt = Point(measurement)
            for tk, tv in tags.items():
                pt.tag(tk, tv)
            for fk, fv in fields.items():
                pt.field(fk, fv)
            if ts is not None:
                pt.time(ts, WritePrecision.NS)
            records.append(pt)
        try:
            self._write_api.write(bucket=self._bucket, org=self._org, record=records)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'InfluxDB write failed ({exc}); dropping {len(records)} points')
            self._write_api = None

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None


def main(args=None):
    rclpy.init(args=args)
    node = CitySink()
    signal.signal(signal.SIGTERM, lambda *_: rclpy.shutdown())
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
