import asyncio
import logging

from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)


class SmaEmProtocol(asyncio.DatagramProtocol):
    """Protocol handlers as required by asyncio low-level API."""

    # Set when connection is made.
    _transport_udp: asyncio.DatagramTransport

    def __init__(
            self,
            connection_lost: asyncio.Future[None],
            store: EnergyModulatorStore,
        ) -> None:
        """Initialize SmaEmProtocol."""
        # Awaited in application in an endless loop for connection supervision.
        self._connection_lost = connection_lost
        self.store = store

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Callback called when a connection is made.

        The argument is the transport representing the pipe connection.
        To receive data, wait for data_received() calls. When the connection
        is closed, connection_lost() is called.
        """
        self._transport_udp = transport
        logger.info("Connection made..")

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:  # noqa: ARG002
        """Callback called when a UDP datagram arrives."""
        self.store.put_nowait(data)

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