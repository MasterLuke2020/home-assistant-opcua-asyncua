from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    SensorEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_HUB = "hub"
CONF_NODEID = "nodeid"
CONF_UNIQUE_ID = "unique_id"
CONF_NODES = "nodes"
CONF_UNIT = "unit"
CONF_DEVICE_CLASS = "device_class"
CONF_STATE_CLASS = "state_class"


NODE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_HUB): cv.string,
        vol.Required(CONF_NODEID): cv.string,
        vol.Optional(CONF_UNIT): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
        vol.Optional(CONF_STATE_CLASS): cv.string,
    }
)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NODES): vol.All(cv.ensure_list, [NODE_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    entities = []
    started_coordinators = set()

    for entry in config[CONF_NODES]:
        hub_name = entry[CONF_HUB]
        coordinator = hass.data[DOMAIN][hub_name]

        name = entry["name"]
        nodeid = entry[CONF_NODEID]
        unique_id = entry.get(CONF_UNIQUE_ID)

        key = name

        if coordinator.data is None:
            coordinator.async_set_updated_data({})

        coordinator.register_data_node(key, nodeid)

        entities.append(
            AsyncuaSensor(
                coordinator=coordinator,
                name=name,
                key=key,
                unique_id=unique_id,
                unit=entry.get(CONF_UNIT),
                device_class=entry.get(CONF_DEVICE_CLASS),
                state_class=entry.get(CONF_STATE_CLASS),
            )
        )

        started_coordinators.add(hub_name)

    async_add_entities(entities)

    for hub_name in started_coordinators:
        # Nicht awaiten: OPC-UA darf den Home-Assistant-Startup nicht blockieren.
        hass.async_create_task(hass.data[DOMAIN][hub_name].start_subscription())


class AsyncuaSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        name: str,
        key: str,
        unique_id: str | None = None,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
    ):
        super().__init__(coordinator)

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._key = key

        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data

        if data is None:
            return None

        return data.get(self._key)

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None
