"""Implement energy_modulator application tasks.

See documentation in README.md.
"""

import argparse
import asyncio
import logging
from types import TracebackType
from typing import Self

from energy_modulator.api.local_logger import LocalLogger
from energy_modulator.api.mqtt_api import MqttApi
from energy_modulator.api.sdm630_emulator import Sdm630Emulator
from energy_modulator.api.sma_em_receiver import SmaEmReceiver

# from energy_modulator.conf.energy_modulator_config import EnergyModulatorServerConfig as conf
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)


class EnergyModulatorServer:
    """Energy Modulator Server App."""

    loop: asyncio.AbstractEventLoop
    store: EnergyModulatorStore
    local_logger: LocalLogger
    sma_em_receiver: SmaEmReceiver
    sdm630_emulator: Sdm630Emulator
    mqtt_api: MqttApi

    def __init__(self, cmdline: argparse.Namespace) -> None:
        """Init EnergyModulatorServer."""
        self.cmdline = cmdline
        self.tasks: list[asyncio.Task[None]] = []

    async def run_forever(self) -> None:
        """Run all EnergyModulatorServer tasks."""
        self.loop = asyncio.get_running_loop()
        # Application state storage object.
        self.store = EnergyModulatorStore()
        # Fixed time-cycle CSV logger.
        if self.cmdline.datalog:
            self.local_logger = LocalLogger(self.store)
        # UDP multicast endpoint receiving datagrams from energy meter using SMA EM protocol.
        self.sma_em_receiver = SmaEmReceiver(self.store)
        # Eastron SDM630 Modbus RTU energy meter emulator.
        self.sdm630_emulator = Sdm630Emulator(self.store)
        # Control interface API over MQTT.
        self.mqtt_api = MqttApi(self.store)
        async with asyncio.TaskGroup() as tg:
            self.tasks.append(tg.create_task(self.sma_em_receiver.run_forever(), name="sma_em_receiver"))
            if self.cmdline.datalog:
                self.tasks.append(tg.create_task(self.local_logger.run_forever(), name="local_logger"))
            self.tasks.append(tg.create_task(self.sdm630_emulator.run_forever(), name="sdm630_emulator"))
            self.tasks.append(tg.create_task(self.mqtt_api.run_forever(), name="mqtt_api"))

    def stop(self) -> None:
        """Cancel all EnergyModulatorServer tasks."""
        logger.info("EnergyModulatorServer.stop() called..")
        self.sma_em_receiver.stop()
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()

    def __enter__(self) -> Self:
        """Initialize and return self as context manager."""
        return self

    def __exit__(
        self,
        exc_t: type[BaseException] | None,
        exc_v: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Context manager exit method."""
        self.stop()
        return exc_t is None
