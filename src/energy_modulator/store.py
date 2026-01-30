"""State storage for energy_modulator."""

from typing import Callable, Self

from energy_modulator.api.sma_em_protocol import EmReadings


class EnergyModulatorStore:
    """Application state representation for Energy Modulator Server.

    This will commit state changes to the listeners.
    """

    p_offset: float = 0.0
    em_readings: EmReadings

    def __init__(self) -> None:
        self._update_callbacks: list[Callable[[Self], None]] = []

    async def set_p_offset(self, p_offset: float) -> None:
        self.p_offset = p_offset

    async def set_em_readings(self, em_readings: EmReadings) -> None:
        """Input EM data readings. This triggers necessary actions."""
        self.em_readings = em_readings
        self._run_hooks()

    def add_update_cb(self, cb: Callable[[Self], None]) -> None:
        """Add co-routine awaited for on data updates."""
        self._update_callbacks.append(cb)

    def _run_hooks(self) -> None:
        for cb in self._update_callbacks:
            cb(self)
