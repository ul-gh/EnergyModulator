"""Async receiver for SMA Sunny Home Manager or Energy Meter UDP multicast datagrams.

2025-12-23 Ulrich Lukas
"""
import asyncio
import logging
import socket
from typing import cast

from energy_modulator.store import EnergyModulatorStore
from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.api.sma_em_protocol import SmaEmProtocol
from include.sma_em.speedwiredecoder import decode_speedwire # type: ignore


logger = logging.getLogger(__name__)


class SmaEmReceiver:
    """Receive UDP multicast datagrams from SMA Home Manager or Energy Meter.

    These are broadcast at a configurable interval by the energy meter,
    commonly 0.2 ... 1 seconds.

    Read-out values are obtained by callling the respective getter functions.
    """

    _protocol: SmaEmProtocol
    _transport: asyncio.DatagramTransport | None = None


    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize SmaEmReceiver."""
        self.store = store


    async def get_power(self) -> tuple[float, float, float, float]:
        """Return total power (power sum), power L1, power L2 and power L3."""
        emparts = cast("dict[str, float]", await self.get_readings())
        power_l1 = emparts["p1consume"] - emparts["p1supply"]
        power_l2 = emparts["p2consume"] - emparts["p2supply"]
        power_l3 = emparts["p3consume"] - emparts["p3supply"]
        power_sum = power_l1 + power_l2 + power_l3
        return power_sum, power_l1, power_l2, power_l3


    async def get_readings(self) -> dict[str, float|int|str]:
        """Get meter read-out values, returned as a dict."""
        bytes_in = await self.store.get()
        return cast("dict[str, float|int|str]", decode_speedwire(bytes_in))


    async def run_forever(self) -> None:
        """Run and supervise UDP multicast endpoint task.

        When the connection is lost, the endpoint task is re-started.
        """
        while True:
            try:
                await self._run_udp_multicast_endpoint()
            except Exception:
                logger.exception("UDP multicast endpoint crashed!")
            logger.warning("Restarting _run_udp_multicast_endpoint task..")


    async def _run_udp_multicast_endpoint(self) -> None:
        """Receive incoming UDP multicast datagrams and fill buffer.

        This adds a task running the UDP multicast endpoint to the event loop
        and then blocks (awaits a connection loss future) until the connection
        is lost or terminated.

        Data is extracted from the transport protocol using a receive queue.
        """
        loop = asyncio.get_running_loop()
        connection_lost = loop.create_future()
        sock = self._create_udp_multicast_socket()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: SmaEmProtocol(connection_lost, self.store),
            sock=sock,
        )
        cancelled = False
        try:
            await connection_lost
        except asyncio.CancelledError:
            cancelled = True
        finally:
            if not cancelled:
                self._transport.close()


    def _create_udp_multicast_socket(self) -> socket.socket:
        # This can be socket.AF_INET (IPv4) or socket.AF_INET6 (IPv6).
        address_family = socket.getaddrinfo(conf.MULTICAST_GROUP, None)[0][0]
        if address_family != socket.getaddrinfo(conf.MULTICAST_INTERFACE, None)[0][0]:
            msg = "MULTICAST_GROUP and MULTICAST_INTERFACE must be both IPv4 or IPv6, not mixed!"
            raise ValueError(msg)
        # Create socket and configure with multicast group membership request.
        sock = socket.socket(address_family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        ip_mreq = (socket.inet_pton(address_family, conf.MULTICAST_GROUP)
                   + socket.inet_pton(address_family, conf.MULTICAST_INTERFACE))
        if address_family == socket.AF_INET: # IPv4
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, ip_mreq)
        else:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, ip_mreq)
        # Bind the socket to the interface address and port.
        sock.bind((conf.MULTICAST_INTERFACE, conf.MULTICAST_PORT))
        return sock

