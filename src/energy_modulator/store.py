"""State storage for energy_modulator."""

from collections.abc import Callable
from typing import Self

from energy_modulator.api.sma_em_protocol import EmReadings


class EnergyModulatorStore:
    """Application state representation for Energy Modulator Server.

    This will commit state changes to the listeners.
    """

    p_offset: float
    em_readings: EmReadings
    _update_callbacks: list[Callable[[Self], None]]

    def __init__(self) -> None:
        self.p_offset = 0.0
        self.em_readings = EmReadings()
        self._update_callbacks = []

    async def set_p_offset(self, p_offset: float) -> None:
        """Set power offset setpoint."""
        self.p_offset = p_offset

    async def set_em_readings(self, em_readings: EmReadings) -> None:
        """Input EM data readings. This triggers the data update callback actions."""
        self.em_readings = em_readings
        self._run_update_cbs()

    def add_update_cb(self, cb: Callable[[Self], None]) -> None:
        """Add co-routine awaited for on data updates."""
        self._update_callbacks.append(cb)

    def _run_update_cbs(self) -> None:
        for cb in self._update_callbacks:
            cb(self)
