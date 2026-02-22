"""Implement energy_modulator application tasks.

See documentation in README.md.
"""

import argparse
import asyncio
import logging
import threading
from collections.abc import Coroutine

from energy_modulator.api.data_logger import DataLogger
from energy_modulator.api.mqtt_client import MqttClient
from energy_modulator.api.sdm630_emulator import Sdm630Emulator
from energy_modulator.api.sma_em_receiver import SmaEmReceiver
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)


class EnergyModulatorServer:
    """Energy Modulator Server App."""

    loop: asyncio.AbstractEventLoop
    store: EnergyModulatorStore
    data_logger: DataLogger
    sma_em_receiver: SmaEmReceiver
    sdm630_emulator: Sdm630Emulator
    mqtt_client: MqttClient

    def __init__(self, cmdline: argparse.Namespace) -> None:
        """Init EnergyModulatorServer."""
        self.cmdline = cmdline
        self.tasks: list[asyncio.Task[None]] = []
        self.thread: threading.Thread | None = None

    def run(self) -> None:
        """Run EnergyModulatorServer on asyncio event loop."""
        asyncio.run(self.run_forever())

    def run_threaded(self) -> None:
        """Run EnergyModulatorServer in new background thread."""
        self.thread = threading.Thread(target=self.run, name="energy_modulator_server", daemon=False)
        self.thread.start()
        logger.info("EnergyModulatorServer running in thread: %s", self.thread)

    def stop(self) -> None:
        """Cancel all EnergyModulatorServer tasks."""
        logger.info("EnergyModulatorServer.stop() called..")
        self.sma_em_receiver.stop()
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        if self.thread is not None:
            self.thread.join()

    def run_coroutine_threadsafe(self, coro: Coroutine[object, object, object]) -> object:
        """Run coroutine on the server event loop and return the result.

        Intended for diagnostics and debugging use when running in a REPL (IPython).
        """
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    async def run_forever(self) -> None:
        """Run all EnergyModulatorServer tasks."""
        self.loop = asyncio.get_running_loop()
        # Application state storage object.
        self.store = EnergyModulatorStore()
        # Fixed time-cycle CSV logger.
        if self.cmdline.datalog:
            self.data_logger = DataLogger(self.store)
        # UDP multicast endpoint receiving datagrams from energy meter using SMA EM protocol.
        self.sma_em_receiver = SmaEmReceiver(self.store)
        # Eastron SDM630 Modbus RTU energy meter emulator.
        self.sdm630_emulator = Sdm630Emulator(self.store)
        # MQTT client providing remote control API and telemetry.
        self.mqtt_client = MqttClient(self.store)
        async with asyncio.TaskGroup() as tg:
            self.tasks.append(tg.create_task(self.sma_em_receiver.run_forever(), name="sma_em_receiver"))
            if self.cmdline.datalog:
                self.tasks.append(tg.create_task(self.data_logger.run_forever(), name="local_logger"))
            self.tasks.append(tg.create_task(self.sdm630_emulator.run_forever(), name="sdm630_emulator"))
            self.tasks.append(tg.create_task(self.mqtt_client.run_forever(), name="mqtt_client"))
