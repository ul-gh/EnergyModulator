"""Implement energy_modulator application tasks.

See documentation in README.md.
"""
import asyncio
import logging

from typing import Self
from types import TracebackType

#from energy_modulator.conf.energy_modulator_config import EnergyModulatorServerConfig as conf
from energy_modulator.store import EnergyModulatorStore
from energy_modulator.api.local_logger import LocalLogger
from energy_modulator.api.sdm630_emulator import Sdm630Emulator
from energy_modulator.api.sma_em_receiver import SmaEmReceiver

logger = logging.getLogger(__name__)


class EnergyModulatorServer:
    """Energy Modulator Server App."""

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


    def stop(self) -> None:
        """Cancel all EnergyModulatorServer tasks."""
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        logger.info("Cancelled EnergyModulatorServer tasks.")


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