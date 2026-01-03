"""Async receiver for SMA Sunny Home Manager or Energy Meter UDP multicast datagrams.

2025-12-23 Ulrich Lukas
"""
import asyncio
import logging
import socket
from typing import Any

from energy_modulator.store import EnergyModulatorStore
from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.api.sma_em_protocol import SmaEmProtocol


logger = logging.getLogger(__name__)


class SmaEmReceiver:
    """Receive UDP multicast datagrams from SMA Home Manager or Energy Meter.

    These are broadcast at a configurable interval by the energy meter,
    commonly 0.2 ... 1 seconds.

    Read-out values are obtained by callling the respective getter functions.
    """

    expected_device: str | None = conf.EXPECTED_DEVICE
    data_received: asyncio.Future[dict[str, Any]]
    _protocol: SmaEmProtocol
    _transport: asyncio.DatagramTransport | None = None
    _udp_multicast_endpoint_task: asyncio.Task[None]
    _data_processing_task: asyncio.Task[None]


    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize SmaEmReceiver."""
        self.store = store


    async def run_forever(self) -> None:
        """Run UDP multicast endpoint task and data processing task.
        """
        # Result set by protocol handler for SmaEmProtocol. Awaited in _run_data_processing.
        self.data_received = asyncio.Future()
        while True:
            async with asyncio.TaskGroup() as tg:
                logger.info("Launching SmaEmReceiver tasks...")
                self._udp_multicast_endpoint_task = tg.create_task(
                    self._run_udp_multicast_endpoint(), name="udp_multicast_endpoint_task"
                )
                # Must be started after
                self._data_processing_task = tg.create_task(
                    self._run_data_processing(), name="data_processing_task"
                )
    
    def stop(self) -> None:
        """Cancel all SmaEmReceiver tasks."""
        logger.info("SmaEmReceiver.stop() called..")
        self._data_processing_task.cancel()
        self._udp_multicast_endpoint_task.cancel()

    async def _run_data_processing(self) -> None:
        """Decode received datagrams and put values into app data store."""
        loop = asyncio.get_running_loop()
        while True:
            await self.store.em_data.put(await self.data_received)
            self.data_received = loop.create_future()

    async def _run_udp_multicast_endpoint(self) -> None:
        """Receive incoming UDP multicast datagrams.

        This adds a task running the UDP multicast endpoint to the event loop
        and then blocks (awaits a connection loss future) until the connection
        is lost or terminated.

        Data is extracted from the transport protocol using a receive queue.
        """
        loop = asyncio.get_running_loop()
        connection_lost = loop.create_future()
        sock = self._create_udp_multicast_socket()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: SmaEmProtocol(self, connection_lost),
            sock=sock,
        )
        try:
            await connection_lost
        finally:
            self._transport.close()


    def _create_udp_multicast_socket(self) -> socket.socket:
        # This can be socket.AF_INET (IPv4) or socket.AF_INET6 (IPv6).
        address_family = socket.getaddrinfo(conf.MULTICAST_GROUP, None)[0][0]
        if address_family != socket.getaddrinfo(conf.MULTICAST_BIND_ADDR, None)[0][0]:
            msg = "MULTICAST_GROUP and MULTICAST_BIND_ADDR must be both IPv4 or IPv6, not mixed!"
            raise ValueError(msg)
        # Create socket and configure with multicast group membership request.
        sock = socket.socket(address_family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        ip_mreq = (socket.inet_pton(address_family, conf.MULTICAST_GROUP)
                   + socket.inet_pton(address_family, conf.MULTICAST_BIND_ADDR))
        if address_family == socket.AF_INET: # IPv4
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, ip_mreq)
        else:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, ip_mreq)
        # Bind the socket to the interface address and port.
        sock.bind((conf.MULTICAST_BIND_ADDR, conf.MULTICAST_PORT))
        return sock

