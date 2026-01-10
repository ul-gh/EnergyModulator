"""State storage for energy_modulator."""

from typing import Callable

from energy_modulator.api.sma_em_protocol import EmReadings
from energy_modulator.utils.async_buffers_queues import HybridItemBuffer


class EnergyModulatorStore:
    """Application state representation for Energy Modulator Server.

    This will commit state changes to the listeners.
    """

    def __init__(self) -> None:
        super().__init__()
        self.em_readings: HybridItemBuffer[EmReadings] = HybridItemBuffer()
        self._em_data_hooks: list[Callable[[EmReadings], None]] = []

    def set_em_readings(self, em_readings: EmReadings) -> None:
        """Input EM data readings. This triggers necessary actions."""
        self.em_readings.put_nowait(em_readings)
        for hook in self._em_data_hooks:
            hook(em_readings)

    def add_em_data_hook(self, hook: Callable[[EmReadings], None]) -> None:
        """Add callback for updating data context of SDM 630 emulator etc."""
        self._em_data_hooks.append(hook)
