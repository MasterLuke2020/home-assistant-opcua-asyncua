from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
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


NODE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_HUB): cv.string,
        vol.Required(CONF_NODEID): cv.string,
    }
)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NODES): vol.All(cv.ensure_list, [NODE_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup OPC UA binary sensors from YAML."""

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
            AsyncuaBinarySensor(
                coordinator=coordinator,
                name=name,
                key=key,
                unique_id=unique_id,
            )
        )

        started_coordinators.add(hub_name)

    async_add_entities(entities)

    for hub_name in started_coordinators:
        # Nicht awaiten: OPC-UA darf den Home-Assistant-Startup nicht blockieren.
        hass.async_create_task(hass.data[DOMAIN][hub_name].start_subscription())


class AsyncuaBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """OPC UA binary sensor."""

    def __init__(self, coordinator, name: str, key: str, unique_id: str | None = None):
        super().__init__(coordinator)

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._key = key

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def is_on(self) -> bool | None:
        data: dict[str, Any] | None = self.coordinator.data

        if data is None:
            return None

        value = data.get(self._key)

        if value is None:
            return None

        return bool(value)
