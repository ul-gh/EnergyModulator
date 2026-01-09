"""State storage for energy_modulator."""

from dataclasses import dataclass
from typing import Callable

from energy_modulator.api.sma_em_protocol import EmDataDecoded
from energy_modulator.utils.async_buffers_queues import HybridItemBuffer


@dataclass
class EmReadings:
    power_sum: float = float("NaN")
    power_l1: float = float("NaN")
    power_l2: float = float("NaN")
    power_l3: float = float("NaN")


class EnergyModulatorStore:
    """Application state representation for Energy Modulator Server.

    This will commit state changes to the listeners.
    """

    def __init__(self) -> None:
        super().__init__()
        self.em_readings: HybridItemBuffer[EmReadings] = HybridItemBuffer()
        self._em_data_hooks: list[Callable[[EmReadings], None]] = []

    def set_em_data(self, data: EmDataDecoded) -> None:
        """Input EM data readings. This triggers necessary actions."""
        measurements = data.measurements
        try:
            readings = EmReadings(
                power_sum=(measurements["1:4:0"] - measurements["2:4:0"]) / 10.0,
                power_l1=(measurements["21:4:0"] - measurements["22:4:0"]) / 10.0,
                power_l2=(measurements["41:4:0"] - measurements["42:4:0"]) / 10.0,
                power_l3=(measurements["61:4:0"] - measurements["62:4:0"]) / 10.0,
            )
        except (TypeError, KeyError, ValueError):
            # This sets "NaN" values for all power measurements.
            readings = EmReadings()
        self.em_readings.put_nowait(readings)
        for hook in self._em_data_hooks:
            hook(readings)

    def add_em_data_hook(self, hook: Callable[[EmReadings], None]) -> None:
        """Add callback for updating data context of SDM 630 emulator etc."""
        self._em_data_hooks.append(hook)
