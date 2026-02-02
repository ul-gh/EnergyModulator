"""Configuration for energy_modulator package.

2025-12-25 Ulrich Lukas
"""

# ruff: noqa: ERA001, S104, S108
from dataclasses import dataclass
from importlib.metadata import version


@dataclass
class EnergyModulatorServerConfig:
    """Settings for Energy Modulator server and store."""


@dataclass
class LocalLoggerConfig:
    """Settings for local logging."""

    # Log output time interval in seconds.
    LOG_INTERVAL: float = 60.0


@dataclass
class Sdm630EmulatorConfig:
    """Settings for emulated SDM630 energy meter."""

    # Serial port connected to Modbus-"Meter" port of the inverter
    # modbus_port: str = "/dev/ttyUSB1"
    modbus_port: str = "/tmp/ttyV0"
    baudrate: int = 9600
    version: str = version("energy_modulator")


@dataclass
class SmaEmReceiverConfig:
    """Settings for Sunny Home Manager (SHM) UDP multicast receiver."""

    #### Settings for udp multicast endpoint.
    # Serial number of the SMA energy meter or SHM to receive.
    # If set to None, receive data from any meter device.
    EXPECTED_DEVICE: int | None = 3007895701
    # MULTICAST_BIND_ADDR: str = "::"
    MULTICAST_GROUP: str = "239.12.255.254"
    MULTICAST_PORT: int = 9522
    # If there are multiple network interfaces, choose the one connected to SMA energy meter or SHM.
    MULTICAST_BIND_ADDR: str = "0.0.0.0"
    # Minimum length of valid datagrams. 608 bytes is consistent with other implementations.
    DATAGRAM_MAX_SIZE: int = 608
    # Receive queue size. For real-time system control, outdated process data has
    # no relevance and thus we configure for only one queue entry which holds the
    # most recent values from the last received UDP datagram from the meter.
    RECV_QUEUE_SIZE: int = 1


@dataclass
class MqttConfig:
    """Settings for MQTT control and telemetry."""

    # Setting this to false disables transmitting of MQTT telegrams
    ACTIVATED: bool = True
    TOPIC_POWER_CONTROL: str = "cmd/energy_modulator/set_power_offset"
    TOPIC_MEASUREMENTS: str = "tele/energy_modulator/measurements"
    BROKER: str = "nas1"
    PORT: int = 1883
    # MQTT minimum broadcast (transmit) time interval in seconds.
    # If the inverter stops requesting energy meter data,
    # MQTT broadcast is also stopped.
    INTERVAL: float = 10.0
