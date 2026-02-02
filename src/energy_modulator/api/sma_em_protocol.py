"""Protocol definition for async udp multicast endpoint and decoder for SMA EM datagrams."""

import asyncio
import logging
import json
from dataclasses import asdict, dataclass
from typing import cast, final, override

from pysmaplus.definitions_speedwire import speedwireHeader, speedwireHeader6069

from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.utils import SingleItemQueue

logger = logging.getLogger(__name__)


@dataclass
class EmHeader:
    """EM protocol header data."""

    protocolID: int  # noqa: N815
    susyid: int
    device: str
    serial: int
    ip: str
    sw_version: str


@dataclass
class EmReadings:
    """Represents floating-point energy meter readings."""

    # Header data
    em_header: EmHeader | None = None
    # Power import (positive) or export (negative) in Watts.
    power: float = float("NaN")
    # Energy import and eyport in kWh
    energy_import: float = float("NaN")
    energy_export: float = float("NaN")
    # Frequency in Hz
    frequency: float = float("NaN")
    # Power import (positive) or export (negative) in Watts.
    power_l1: float = float("NaN")
    power_l2: float = float("NaN")
    power_l3: float = float("NaN")
    # Current in Amps and Voltages in Volts.
    current_l1: float = float("NaN")
    voltage_l1: float = float("NaN")
    current_l2: float = float("NaN")
    voltage_l2: float = float("NaN")
    current_l3: float = float("NaN")
    voltage_l3: float = float("NaN")

    def update(self, em_header: EmHeader, obis_measurements: dict[str, int]) -> None:
        """Update EmReadings with decoded values from UDP receiver.

        This sets the header data and translates raw measurement results
        (identified by OBIS ID) into float readings.

        Errors are silently discarded.
        """
        self.em_header = em_header
        try:
            self.power = (obis_measurements["1:4:0"] - obis_measurements["2:4:0"]) / 10.0
            self.energy_import = obis_measurements["1:8:0"] / 3600000.0
            self.energy_export = obis_measurements["2:8:0"] / 3600000.0
            self.frequency = obis_measurements["14:4:0"] / 1000.0
            self.power_l1 = (obis_measurements["21:4:0"] - obis_measurements["22:4:0"]) / 10.0
            self.power_l2 = (obis_measurements["41:4:0"] - obis_measurements["42:4:0"]) / 10.0
            self.power_l3 = (obis_measurements["61:4:0"] - obis_measurements["62:4:0"]) / 10.0
            self.current_l1 = obis_measurements["31:4:0"] / 1000.0
            self.voltage_l1 = obis_measurements["32:4:0"] / 1000.0
            self.current_l2 = obis_measurements["51:4:0"] / 1000.0
            self.voltage_l2 = obis_measurements["52:4:0"] / 1000.0
            self.current_l3 = obis_measurements["71:4:0"] / 1000.0
            self.voltage_l3 = obis_measurements["72:4:0"] / 1000.0
        except (TypeError, KeyError, ValueError):
            pass
    
    def as_json(self) -> str:
        """Return EmReadings in JSON format (for MQTT telemetry)."""
        return json.dumps(asdict(self))


def decode_speedwire_em_datagram(p: bytes, addr: tuple[str, int]) -> tuple[EmHeader, dict[str, int]]:
    """Decode a Speedwire-Packet.

    Parameters
    ----------
        p: Network-Packet

    Returns
    -------
        dict: Dict with all the decoded information

    Decode function based on pysmaplus@5e49754ecc73af0e5a5ff02b36afc7a164ce3684
    (https://github.com/littleyoda/pysma).

    This has been modified and stripped off debug information.
    """
    sw = speedwireHeader.from_packed(p[0:18])
    if not sw.check6069():
        msg = "Decoding speedwire packed failed. Wrong header!"
        raise ValueError(msg)
    sw6069 = speedwireHeader6069.from_packed(p[18:28])
    header = EmHeader(
        protocolID=sw.protokoll,
        susyid=sw6069.src_susyid,
        device="SHM2/EM",
        serial=sw6069.src_serial,
        ip=addr[0] + ":" + str(addr[1]),
        sw_version="",
    )
    obis_measurements: dict[str, int] = {}
    length = sw.smanet2_length + 16
    pos = 28
    while pos < min(length, conf.DATAGRAM_MAX_SIZE):
        mchannel = int.from_bytes(p[pos : pos + 1], byteorder="big")
        mvalueindex = int.from_bytes(p[pos + 1 : pos + 2], byteorder="big")
        mtyp = int.from_bytes(p[pos + 2 : pos + 3], byteorder="big")
        mtariff = int.from_bytes(p[pos + 3 : pos + 4], byteorder="big")
        obis = f"{mvalueindex}:{mtyp}:{mtariff}"
        if mtyp in [4, 8]:
            # 4 actucal / current => 8 Bytes
            # 8 counter / sum => 12 Bytes
            value = int.from_bytes(p[pos + 4 : pos + 4 + mtyp], byteorder="big")
            obis_measurements[obis] = value
            pos += 4 + mtyp
        elif mchannel == 144 and mtyp == 0:  # noqa: PLR2004
            value = f"{p[pos + 4]}.{p[pos + 5]}.{p[pos + 6]}.{chr(p[pos + 7])}"
            header.sw_version = value
            pos += 4 + 4
        else:
            # If we silently ignore the error, increase position. Does not hurt when raising.
            pos += 4 + 4
            msg = "Decoding speedwire packed failed. Invalid data!"
            raise ValueError(msg)
    return header, obis_measurements


@final
class SmaEmProtocol(asyncio.DatagramProtocol):
    """Protocol handlers as required by asyncio low-level API."""

    # Set when connection is made.
    _transport_udp: asyncio.DatagramTransport  # pyright: ignore[reportUninitializedInstanceVariable]

    def __init__(
        self,
        data_received: SingleItemQueue[EmReadings],
        connection_lost: asyncio.Future[None],
    ) -> None:
        """Initialize SmaEmProtocol."""
        self._data_received = data_received
        self._connection_lost = connection_lost
        self._em_readings = EmReadings()

    @override
    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Callback called when a connection is made.

        The argument is the transport representing the pipe connection.
        To receive data, wait for data_received() calls. When the connection
        is closed, connection_lost() is called.
        """
        self._transport_udp = transport
        logger.info("Connection made..")

    @override
    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Callback called when a UDP datagram arrives."""
        try:
            header, obis_measurements = decode_speedwire_em_datagram(data, addr)
            self._em_readings.update(header, obis_measurements)
        except (KeyError, ValueError, TypeError, UnicodeDecodeError) as e:
            logger.error("Error decoding SMA EM datagram: %s", cast("str", e.args[0]))  # noqa: TRY400
            return
        if conf.EXPECTED_DEVICE is not None and header.serial != conf.EXPECTED_DEVICE:
            msg = "Received telegram from different device serial number. Wanted: %d.  Got: %d"
            logger.debug(msg, conf.EXPECTED_DEVICE, header.serial)
            return
        self._data_received.put_nowait(self._em_readings)

    @override
    def error_received(self, exc: Exception) -> None:
        """Callback called when a send or receive operation raises an OSError.

        (Other than BlockingIOError or InterruptedError.)
        """
        logger.exception("Error received!")
        # See below, we do not want to raise an exception here.
        if self._connection_lost.done():
            return
        self._connection_lost.set_exception(exc)

    @override
    def connection_lost(self, exc: Exception | None) -> None:
        """Callback called when the connection is lost or closed.

        The argument is an exception object or None (the latter meaning a
        regular EOF is received or the connection was aborted or closed).
        """
        logger.warning("SmaEmProtocol connection_lost handler called!")
        # Necessary as calling transport.close() will trigger this again
        if self._connection_lost.done():
            return
        if exc is not None:
            logger.exception("Exception in SmaEmProtocol connection_lost handler!")
            self._connection_lost.set_exception(exc)
        else:
            self._connection_lost.set_result(None)
