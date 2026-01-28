"""State storage for energy_modulator."""

from typing import Callable, Coroutine, Self

from energy_modulator.api.sma_em_protocol import EmReadings
from energy_modulator.utils.async_buffers_queues import HybridItemBuffer


class EnergyModulatorStore:
    """Application state representation for Energy Modulator Server.

    This will commit state changes to the listeners.
    """

    em_readings: HybridItemBuffer[EmReadings]
    p_offset: float = 0.0

    def __init__(self) -> None:
        super().__init__()
        self.em_readings = HybridItemBuffer()
        self._update_callbacks: list[Callable[[Self], None]] = []
        self._update_coroutines: list[Coroutine[None, None, None]] = []

    async def set_p_offset(self, p_offset: float) -> None:
        self.p_offset = p_offset
        await self._run_hooks()

    async def set_em_readings(self, em_readings: EmReadings) -> None:
        """Input EM data readings. This triggers necessary actions."""
        self.em_readings.put_nowait(em_readings)
        await self._run_hooks()

    def add_update_callback(self, cb: Callable[[Self], None]) -> None:
        """Add callback called on data updates."""
        self._update_callbacks.append(cb)

    def add_update_coroutine(self, coro: Coroutine[None, None, None]) -> None:
        """Add co-routine awaited for on data updates."""
        self._update_coroutines.append(coro)

    async def _run_hooks(self) -> None:
        for cb in self._update_callbacks:
            cb(self)
        for coro in self._update_coroutines:
            await coro
