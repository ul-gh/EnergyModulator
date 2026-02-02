"""Energy Modulator MQTT client providing remote control API and telemetry."""
# pyright: reportUninitializedInstanceVariable=false

import asyncio
import contextlib
import logging
from typing import final

import aiomqtt

from energy_modulator.conf.energy_modulator_config import MqttConfig as conf
from energy_modulator.store import EnergyModulatorStore
from energy_modulator.utils import async_fixed_time_intervals

logger = logging.getLogger(__name__)


@final
class MqttClient:
    """Energy Modulator MQTT client providing remote control API and telemetry."""
    _endpoint_task: asyncio.Task[None]
    _telemetry_task: asyncio.Task[None]

    def __init__(self, store: EnergyModulatorStore) -> None:
        self._store = store

    async def run_forever(self) -> None:
        """Run MqttApi task."""
        try:
            await self._run_client_tasks()
        except aiomqtt.MqttError:
            logger.error("Connection lost. Reconnecting...")
            await asyncio.sleep(conf.RECONNECT_TIMEOUT)

    async def _run_client_tasks(self) -> None:
        """Run MQTT control API endpoint task and MQTT telemetry task."""
        async with aiomqtt.Client(
            conf.BROKER,
            conf.PORT,
            clean_session=True,
            timeout=conf.RECONNECT_TIMEOUT,
        ) as client:
            async with asyncio.TaskGroup() as tg:
                self._endpoint_task = tg.create_task(
                    self._run_endpoint_task(client),
                    name="MQTT control endpoint task",
                )
                self._telemetry_task = tg.create_task(
                    self._run_telemetry_task(client),
                    name="MQTT telemetry task",
                )

    async def _run_endpoint_task(self, client: aiomqtt.Client) -> None:
        """Subscribe to API control topic channel and process control messages."""
        _ = await client.subscribe(conf.TOPIC_POWER_CONTROL)
        p_offset = 0.0
        async for msg in client.messages:
            with contextlib.suppress(ValueError):
                p_offset = float(msg.payload)
            await self._store.set_p_offset(p_offset)

    async def _run_telemetry_task(self, client: aiomqtt.Client) -> None:
        """Push telemetry data periodically."""
        async for _ in async_fixed_time_intervals(conf.TELEMETRY_INTERVAL):
            payload = self._store.em_readings.as_json()
            await client.publish(conf.TOPIC_MEASUREMENTS, payload)

                
