"""Async receiver for SMA Sunny Home Manager or Energy Meter UDP multicast datagrams.

2025-12-23 Ulrich Lukas
"""
# pyright: reportUninitializedInstanceVariable=false

import asyncio
import logging
import socket
from typing import final

from energy_modulator.api.sma_em_protocol import EmReadings, SmaEmProtocol
from energy_modulator.conf.energy_modulator_config import SmaEmReceiverConfig as conf
from energy_modulator.store import EnergyModulatorStore
from energy_modulator.utils.async_buffers_queues import SingleItemQueue

logger = logging.getLogger(__name__)


@final
class SmaEmReceiver:
    """Receive UDP multicast datagrams from SMA Home Manager or Energy Meter.

    These are broadcast at a configurable interval by the energy meter,
    commonly 0.2 ... 1 seconds.

    Read-out values are obtained by callling the respective getter functions.
    """

    data_received: SingleItemQueue[EmReadings]
    _udp_multicast_endpoint_task: asyncio.Task[None]
    _state_updater_task: asyncio.Task[None]

    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize SmaEmReceiver."""
        self.store: EnergyModulatorStore = store

    async def run_forever(self) -> None:
        """Run UDP multicast endpoint task and data processing task."""
        self.data_received = SingleItemQueue[EmReadings]()
        while True:
            async with asyncio.TaskGroup() as tg:
                logger.info("Launching SmaEmReceiver tasks...")
                # Produces EmReadings and puts in self.data_received.
                self._udp_multicast_endpoint_task = tg.create_task(
                    self._run_udp_multicast_endpoint_task(),
                    name="udp_multicast_endpoint_task",
                )
                # Consumes EmReadings from self.data_received.
                self._state_updater_task = tg.create_task(
                    self._run_state_updater_task(),
                    name="state_updater_task",
                )

    def stop(self) -> None:
        """Cancel all SmaEmReceiver tasks."""
        logger.info("SmaEmReceiver.stop() called..")
        _ = self._state_updater_task.cancel()
        _ = self._udp_multicast_endpoint_task.cancel()

    async def _run_udp_multicast_endpoint_task(self) -> None:
        """Receive incoming UDP multicast datagrams.

        This adds a task running the UDP multicast endpoint to the event loop
        and then blocks (awaits a connection loss future) until the connection
        is lost or terminated.

        Data is extracted from the transport protocol using a receive queue.
        """
        loop = asyncio.get_running_loop()
        connection_lost = loop.create_future()
        sock = self._create_udp_multicast_socket()
        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: SmaEmProtocol(self.data_received, connection_lost),
            sock=sock,
        )
        try:
            await connection_lost
        finally:
            transport.close()

    async def _run_state_updater_task(self) -> None:
        """Update application state data store."""
        while True:
            em_readings = await self.data_received.get()
            await self.store.set_em_readings(em_readings)

    def _create_udp_multicast_socket(self) -> socket.socket:
        # This can be socket.AF_INET (IPv4) or socket.AF_INET6 (IPv6).
        address_family = socket.getaddrinfo(conf.MULTICAST_GROUP, None)[0][0]
        if address_family != socket.getaddrinfo(conf.MULTICAST_BIND_ADDR, None)[0][0]:
            msg = "MULTICAST_GROUP and MULTICAST_BIND_ADDR must be both IPv4 or IPv6, not mixed!"
            raise ValueError(msg)
        # Create socket and configure with multicast group membership request.
        sock = socket.socket(address_family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # See: https://stackoverflow.com/questions/14388706/how-do-so-reuseaddr-and-so-reuseport-differ?rq=1
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # noqa: ERA001
        ip_mreq = socket.inet_pton(address_family, conf.MULTICAST_GROUP) + socket.inet_pton(
            address_family,
            conf.MULTICAST_BIND_ADDR,
        )
        if address_family == socket.AF_INET:  # IPv4
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, ip_mreq)
        else:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, ip_mreq)
        # Bind the socket to the interface address and port.
        sock.bind((conf.MULTICAST_BIND_ADDR, conf.MULTICAST_PORT))
        return sock
