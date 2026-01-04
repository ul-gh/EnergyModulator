"""Protocol definition for async udp multicast endpoint and decoder for SMA EM datagrams."""
import asyncio
import logging

from dataclasses import dataclass
from pysmaplus.definitions_speedwire import speedwireHeader, speedwireHeader6069
from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from energy_modulator.api.sma_em_receiver import SmaEmReceiver

logger = logging.getLogger(__name__)

@dataclass
class EmDataDecoded:
    protocolID: int
    susyid: int
    device: str
    serial: int
    ip: str
    sw_version: str
    # dict keys are OBIS IDs, e.g. "1:4:0"
    measurements: dict[str, int]


def decode_speedwire_em_datagram(p: bytes, addr: tuple[str, int]) -> EmDataDecoded:
    """Decode a Speedwire-Packet

    Args:
        p: Network-Packet

    Returns:
        dict: Dict with all the decoded information

    Decode function based on pysmaplus@5e49754ecc73af0e5a5ff02b36afc7a164ce3684
    (https://github.com/littleyoda/pysma).
    
    This has been stripped off debug information.
    """
    sw = speedwireHeader.from_packed(p[0:18])
    if not sw.check6069():
        raise ValueError("Decoding speedwire packed failed. Wrong header!")
    sw6069 = speedwireHeader6069.from_packed(p[18:28])
    data = EmDataDecoded(
        protocolID=sw.protokoll,
        susyid=sw6069.src_susyid,
        device="SHM2/EM",
        serial=sw6069.src_serial,
        ip=addr[0] + ":" + str(addr[1]),
        sw_version="",
        measurements={},
    )
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
            data.measurements[obis] = value
            pos += 4 + mtyp
        elif mchannel == 144 and mtyp == 0:
            value = f"{p[pos + 4]}.{p[pos + 5]}.{p[pos + 6]}.{chr(p[pos + 7])}"
            data.sw_version = value
            pos += 4 + 4
        else:
            # If we silently ignore this here, position has to be increased:
            # pos += 4 + 4
            raise ValueError("Decoding speedwire packed failed. Invalid data!")
    return data


class SmaEmProtocol(asyncio.DatagramProtocol):
    """Protocol handlers as required by asyncio low-level API."""

    # Set when connection is made.
    _transport_udp: asyncio.DatagramTransport

    def __init__(
            self,
            receiver: "SmaEmReceiver",
            connection_lost: asyncio.Future[None],
        ) -> None:
        """Initialize SmaEmProtocol."""
        self._receiver = receiver
        self._connection_lost = connection_lost

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Callback called when a connection is made.

        The argument is the transport representing the pipe connection.
        To receive data, wait for data_received() calls. When the connection
        is closed, connection_lost() is called.
        """
        self._transport_udp = transport
        logger.info("Connection made..")

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Callback called when a UDP datagram arrives."""
        receiver = self._receiver
        if receiver.data_received.done():
            return
        try:
            data_decoded = decode_speedwire_em_datagram(data, addr)
        except (KeyError, ValueError, TypeError, UnicodeDecodeError) as e:
            logger.error("Error decoding SMA EM datagram: %s", e.args[0])
            return
        if receiver.expected_device is not None and data_decoded.serial != receiver.expected_device:
            msg = "Received telegram from different device serial number. Wanted: %d.  Got: %d"
            logger.debug(msg, receiver.expected_device, data_decoded.serial)
            return
        receiver.data_received.set_result(data_decoded)

    def error_received(self, exc: Exception) -> None:
        """Callback called when a send or receive operation raises an OSError.

        (Other than BlockingIOError or InterruptedError.)
        """
        logger.exception("Error received!")
        # See below, we do not want to raise an exception here.
        if self._connection_lost.done():
            return
        self._connection_lost.set_exception(exc)

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