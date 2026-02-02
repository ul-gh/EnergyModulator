"""Power output logging for SmaEmReceiver."""

import logging
import sys
from typing import final

from energy_modulator.conf.energy_modulator_config import LocalLoggerConfig as conf
from energy_modulator.store import EnergyModulatorStore
from energy_modulator.utils import async_fixed_time_intervals


@final
class LocalLogger:
    """CSV log output of meter active power readings for total, L1, L2 and L3.

    Note: Log level is logging.INFO.
    Normal loglevel is logging.WARNING i.e. screen output is OFF by default.

    CSV line format:
    Date, Time, Property, Unit, ch_name, ch_name, ch_name_name, value, value, value, value

    Example output:
    2025-12-26, 10:53:36, Active Power, W, Total, L1, L2, L3, xxx, xxx, xxx, xxx
    """

    def __init__(self, store: EnergyModulatorStore) -> None:
        """Initialize LocalLogger."""
        # Application data store
        self.store = store
        # Logger configuration
        self.logger = logging.Logger(__name__, level=logging.INFO)  # noqa: LOG001
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(fmt="%(asctime)s, %(message)s", datefmt="%Y-%m-%d, %H:%M:%S")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    async def run_forever(self) -> None:
        """(Supposedly) forever running co-routine for power output logger."""
        # CSV header: Component, Date, Time, Measurement, Unit, Channel, Channel, Channel, Channel
        msg_p = "Active Power, W, Total, L1, L2, L3, %5.0f, %5.0f, %5.0f, %5.0f"
        msg_offset = "Power Offset Setpoint, W, %5.0f"
        async for _ in async_fixed_time_intervals(conf.LOG_INTERVAL):
            power = self.store.em_readings.power
            power_l1 = self.store.em_readings.power_l1
            power_l2 = self.store.em_readings.power_l2
            power_l3 = self.store.em_readings.power_l3
            self.logger.info(msg_p, power, power_l1, power_l2, power_l3)
            self.logger.info(msg_offset, self.store.p_offset)
