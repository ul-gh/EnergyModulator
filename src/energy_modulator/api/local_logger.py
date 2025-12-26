"""Power output logging for SmaEmReceiver."""

import asyncio
import logging

from energy_modulator.conf.energy_modulator_config import LocalLoggerConfig as conf
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)

class LocalLogger:
    """Log output of meter active power readings for total, L1, L2 and L3.

    Note: Log level is logging.INFO.
    Normal loglevel is logging.WARNING i.e. screen output is OFF by default.
    """

    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize LocalLogger."""
        self.store = store

    async def run_forever(self) -> None:
        """(Supposedly) forever running co-routine for power output logger."""
        while True:
            await asyncio.sleep(conf.LOG_INTERVAL)
            p_tot, p_l1, p_l2, p_l3 = await self.store.get()
            msg = f", Active Power, W, tot,L1,L2,L3, {p_tot:5.0f}, {p_l1:5.0f}, {p_l2:5.0f}, {p_l3:5.0f}"
            logger.info(msg)
