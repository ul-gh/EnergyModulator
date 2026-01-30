"""Energy Modulator MQTT API for remote control and telemetry."""

import contextlib
import logging
from typing import cast

import aiomqtt

from energy_modulator.conf.energy_modulator_config import MqttConfig as conf
from energy_modulator.store import EnergyModulatorStore

logger = logging.getLogger(__name__)

# Does this test the connection?
MQTT_TIMEOUT: float = 5.0


class MqttApi:
    """Energy Modulator MQTT API for remote control and telemetry."""

    def __init__(self, store: EnergyModulatorStore) -> None:
        self._store = store

    async def run_forever(self) -> None:
        """Run MqttApi task."""
        async with aiomqtt.Client(
            conf.BROKER,
            conf.PORT,
            clean_session=True,
            timeout=MQTT_TIMEOUT,
        ) as client:
            await client.subscribe(conf.TOPIC_POWER_CONTROL)
            p_offset = 0.0
            async for msg in client.messages:
                with contextlib.suppress(ValueError):
                    p_offset = float(cast("bytes", msg.payload))
                await self._store.set_p_offset(p_offset)
