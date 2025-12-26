"""Power output logging for SmaEmReceiver."""

import asyncio
import logging

from energy_modulator.conf.energy_modulator_config import LocalLoggerConfig as conf
from energy_modulator.store import EnergyModulatorStore


class LocalLogger:
    """Log output of meter active power readings for total, L1, L2 and L3.

    Note: Log level is logging.INFO.
    Normal loglevel is logging.WARNING i.e. screen output is OFF by default.
    """

    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize LocalLogger."""
        # Application data store
        self.store = store
        # Logger configuration
        self.logger = logging.Logger(__name__)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt="%(asctime)s, %(message)s", datefmt="%Y-%m-%d, %H:%M:%S")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)


    async def run_forever(self) -> None:
        """(Supposedly) forever running co-routine for power output logger."""
        # CSV header: Component, Date, Time, Measurement, Unit, Channel, Channel, Channel, Channel
        msg = "Active Power, W, Total, L1, L2, L3, %5.0f, %5.0f, %5.0f, %5.0f"
        while True:
            await asyncio.sleep(conf.LOG_INTERVAL)
            p_tot, p_l1, p_l2, p_l3 = await self.store.get_power()
            self.logger.info(msg, p_tot, p_l1, p_l2, p_l3)
