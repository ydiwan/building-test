"""ROS-agnostic interface to one floor Pi's hardware.

Drivers own the physical buses (I2C/SPI/GPIO) and return plain dataclasses, so
they can be unit-tested off-hardware and carry no ROS dependency. The node maps
these records to occ_interfaces messages.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Aht20Reading:
    idx: int
    temperature: float          # degrees Celsius
    relative_humidity: float    # percent
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


class FloorDriver(ABC):
    """One floor Pi's hardware, owning its shared buses (serialized in-process)."""

    @abstractmethod
    def read_environment(self) -> list[Aht20Reading]: ...

    @abstractmethod
    def read_power(self) -> list[WattmeterReading]: ...

    @abstractmethod
    def read_motion(self) -> list[PirReading]: ...

    @abstractmethod
    def get_leds(self) -> list[tuple[int, float]]:
        """Current (idx, brightness 0.0-1.0) for every LED channel."""

    @abstractmethod
    def set_leds(self, values: dict[int, float]) -> dict[int, float]:
        """Apply {idx: brightness}; return {idx: clamped_value} actually applied."""

    @abstractmethod
    def get_servos(self) -> list[tuple[int, int]]:
        """Current (idx, angle 0-180) for every servo."""

    @abstractmethod
    def set_servos(self, angles: dict[int, int]) -> dict[int, int]:
        """Apply {idx: angle}; return {idx: clamped_angle} actually applied."""

    def close(self) -> None:
        """Release bus handles. Override if the driver holds hardware resources."""
