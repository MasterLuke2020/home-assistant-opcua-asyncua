import logging

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
    """Setup OPC-UA switches from YAML.

    Switches sind echte Schalter: ON schreibt TRUE, OFF schreibt FALSE.
    Sie werden als Datenpunkte registriert, damit ihr Status per Subscription
    wieder schnell aus der PLC gelesen wird.
    """
    entities = []

    for node in config[CONF_NODES]:
        hub_name = node[CONF_HUB]
        coordinator = hass.data[DOMAIN][hub_name]

        key = node[CONF_UNIQUE_ID]
        coordinator.register_data_node(key, node[CONF_NODE_ID])

        entities.append(
            AsyncuaSwitch(
                coordinator=coordinator,
                key=key,
                name=node["name"],
            )
        )

    async_add_entities(entities)


class AsyncuaSwitch(CoordinatorEntity, SwitchEntity):
    """Persistent OPC-UA switch."""

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = key
        self._optimistic_value: bool | None = None

    @property
    def available(self) -> bool:
        # Bedienbar lassen; beim Schalten verbindet/reconnectet der Coordinator bei Bedarf.
        return True

    @property
    def is_on(self):
        if self._optimistic_value is not None:
            return self._optimistic_value

        data = self.coordinator.data or {}
        value = data.get(self._key)

        if value is None:
            return None

        return bool(value)

    async def async_turn_on(self, **kwargs):
        await self._write_state(True)

    async def async_turn_off(self, **kwargs):
        await self._write_state(False)

    async def _write_state(self, value: bool):
        nodeid = self.coordinator.nodes[self._key]

        # Optimistisch sofort anzeigen, damit das Frontend nicht träge wirkt.
        self._optimistic_value = value
        self.async_write_ha_state()

        try:
            _LOGGER.debug("Switch write %s für %s (%s)", value, self._key, nodeid)
            await self.coordinator.async_write_bool(nodeid, value)

            # lokalen Coordinator-Status sofort aktualisieren; die Subscription bestätigt danach.
            new_data = dict(self.coordinator.data or {})
            new_data[self._key] = value
            self.coordinator.async_set_updated_data(new_data)

        except Exception as err:
            # Optimistischen Status zurücknehmen, wenn Schreiben fehlgeschlagen ist.
            self._optimistic_value = None
            self.async_write_ha_state()
            _LOGGER.exception("Fehler beim Schalten von %s", self._key)
            raise HomeAssistantError(
                f"OPC-UA Switch '{self._attr_name}' konnte nicht geschrieben werden"
            ) from err
        finally:
            self._optimistic_value = None
            self.async_write_ha_state()
