"""Implement energy_modulator application tasks.

See documentation in README.md.
"""
import asyncio
import logging
import threading

#from energy_modulator.conf.energy_modulator_config import EnergyModulatorServerConfig as conf
from energy_modulator.store import EnergyModulatorStore
from energy_modulator.api.local_logger import LocalLogger
from energy_modulator.api.sdm630_emulator import Sdm630Emulator
from energy_modulator.api.sma_em_receiver import SmaEmReceiver

logger = logging.getLogger(__name__)


class EnergyModulatorServer:
    """Energy Modulator Server App."""

    main_thread: threading.Thread
    sma_em_receiver: SmaEmReceiver


    def __init__(self) -> None:
        """Init Energy Modulator Server."""
        self.tasks: list[asyncio.Task[None]] = []


    async def run(self) -> None:
        """Run supervised UDP multicast endpoint and logger task.

        Note: Log level is logging.INFO.
        Normal loglevel is logging.WARNING i.e. screen output is OFF by default.
        """
        self.store = EnergyModulatorStore()
        self.local_logger = LocalLogger(self.store)
        self.sma_em_receiver = SmaEmReceiver(self.store)
        self.sdm630_emulator = Sdm630Emulator(self.store)
        async with asyncio.TaskGroup() as tg:
            # UDP Multicast endpoint for SMA Energy Metering Protocol
            self.tasks.append(tg.create_task(self.sma_em_receiver.run_forever(), name="sma_em_receiver"))
            # Local logging task
            self.tasks.append(tg.create_task(self.local_logger.run_forever(), name="local_logger"))


    def cancel_tasks(self) -> None:
        """Cancel all tasks."""
        for task in self.tasks:
            task.cancel()
        self.tasks = []
        self.main_thread.join()
        logger.info("Stopped app running in thread id: %s", self.main_thread)