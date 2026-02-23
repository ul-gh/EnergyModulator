"""Implement energy_modulator application tasks.

See documentation in README.md.
"""

import asyncio
import logging
from collections.abc import Coroutine

from energy_modulator.api.data_logger import DataLogger
from energy_modulator.api.mqtt_client import MqttClient
from energy_modulator.api.sdm630_emulator import Sdm630Emulator
from energy_modulator.api.sma_em_receiver import SmaEmReceiver
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)


class EnergyModulatorServer:
    """Implement EnergyModulatorServer."""

    def __init__(self, *, datalog_enabled: bool) -> None:
        """Initialize EnergyModulatorServer."""
        # Application state storage object.
        self.store: EnergyModulatorStore = EnergyModulatorStore()
        # UDP multicast endpoint receiving datagrams from energy meter using SMA EM protocol.
        self.sma_em_receiver: SmaEmReceiver = SmaEmReceiver(self.store)
        # Eastron SDM630 Modbus RTU energy meter emulator.
        self.sdm630_emulator: Sdm630Emulator = Sdm630Emulator(self.store)
        # MQTT client providing remote control API and telemetry.
        self.mqtt_client: MqttClient = MqttClient(self.store)
        # Fixed time-cycle CSV logger.
        self.data_logger: DataLogger | None = DataLogger(self.store) if datalog_enabled else None
        # Reference to event loop for faster access.
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        # List of server tasks.
        self._tasks: list[asyncio.Task[None]] = []
        # Set by calling stop(). run_forever() method terminates if this event is set to True.
        self._stop_server: asyncio.Event = asyncio.Event()


    def stop(self) -> None:
        """Stop all EnergyModulatorServer tasks.

        This can be called from another thread.
        """
        _ = self.run_coroutine_threadsafe(self.async_stop())


    async def run_forever(self) -> None:
        """Run all EnergyModulatorServer taskss."""
        async with asyncio.TaskGroup() as tg:
            self._add_task(tg, self.sma_em_receiver.run_forever(), name="sma_em_receiver")
            self._add_task(tg, self.sdm630_emulator.run_forever(), name="sdm630_emulator")
            self._add_task(tg, self.mqtt_client.run_forever(), name="mqtt_client")
            if self.data_logger is not None:
                self._add_task(tg, self.data_logger.run_forever(), name="data_logger")
            _ = await self._stop_server.wait()


    async def async_stop(self) -> None:
        """Stop all server tasks. This is NOT thread-safe to call.."""
        logger.info("EnergyModulatorServer.async<-stop() called.")
        self.sma_em_receiver.stop()
        for task in self._tasks:
            _ = task.cancel()
        self._tasks.clear()
        self._stop_server.set()


    def run_coroutine_threadsafe(self, coro: Coroutine[object, object, object]) -> object:
        """Run coroutine on the server event loop and return the result.

        Intended for diagnostics and debugging use when running in a REPL (IPython).
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def _add_task(self, tg: asyncio.TaskGroup, coro: Coroutine[None, None, None], name: str) -> None:
        """Create task on task group tg and add task handle to the list of tasks."""
        self._tasks.append(tg.create_task(coro, name=name))





