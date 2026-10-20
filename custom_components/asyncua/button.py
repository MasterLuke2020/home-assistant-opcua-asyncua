import asyncio
import logging

import voluptuous as vol

from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_NODES, CONF_NODE_ID, CONF_HUB

_LOGGER = logging.getLogger(__name__)

CONF_UNIQUE_ID = "unique_id"

NODE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_HUB): cv.string,
        vol.Required(CONF_NODE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NODES): vol.All(cv.ensure_list, [NODE_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    entities = []

    for node_cfg in config[CONF_NODES]:
        hub_name = node_cfg[CONF_HUB]
        coordinator = hass.data[DOMAIN][hub_name]

        key = node_cfg[CONF_UNIQUE_ID]
        coordinator.register_write_node(key, node_cfg[CONF_NODE_ID])

        entities.append(
            AsyncuaButton(
                coordinator=coordinator,
                key=key,
                name=node_cfg["name"],
            )
        )

    async_add_entities(entities)


class AsyncuaButton(ButtonEntity):
    def __init__(self, coordinator, key, name):
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = key
        self._pulse_time = 0.5  # Sekunden

    @property
    def available(self) -> bool:
        # Der Button/Switch soll bedienbar bleiben; beim Drücken wird bei Bedarf verbunden.
        return True

    async def async_press(self) -> None:
        """Wird aufgerufen, wenn der Button in Home Assistant gedrückt wird."""
        try:
            await self._pulse()
        except Exception as err:
            _LOGGER.exception("Fehler beim Drücken von %s", self._key)
            raise HomeAssistantError(
                f"OPC-UA Button '{self._attr_name}' konnte nicht geschrieben werden"
            ) from err

    async def _pulse(self) -> None:
        """Setzt den OPC-UA-Node kurz auf TRUE und danach wieder auf FALSE."""
        nodeid = self.coordinator.nodes[self._key]

        # Keep each pulse atomic even if the same button is pressed repeatedly.
        # Always attempt FALSE again when a pulse fails or is cancelled.
        async with self.coordinator.pulse_lock_for(nodeid):
            try:
                _LOGGER.debug("Pulse TRUE für %s (%s)", self._key, nodeid)
                await self.coordinator.async_write_bool(nodeid, True)
                await asyncio.sleep(self._pulse_time)
            finally:
                _LOGGER.debug("Pulse FALSE für %s (%s)", self._key, nodeid)
                await self.coordinator.async_write_bool(nodeid, False)

        _LOGGER.debug("Pulse abgeschlossen für %s", self._key)
