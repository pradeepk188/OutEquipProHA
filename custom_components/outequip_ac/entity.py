"""Shared base entity for the OutEquip Pro AC integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity

from .client import OutEquipAcClient
from .const import CONF_NAME, DOMAIN, SIGNAL_UPDATE, STATE_CONNECTED


class OutEquipAcEntity(Entity):
    """Base entity tied to one AC's client + its update signal."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, client: OutEquipAcClient, entry: ConfigEntry, key: str) -> None:
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.data.get(CONF_NAME) or "OutEquip Pro AC",
            manufacturer="OutEquip",
            model="OutEquip Pro Rooftop AC",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def connected(self) -> bool:
        return self._client.state.connection == STATE_CONNECTED


def get_client(hass: HomeAssistant, entry: ConfigEntry) -> OutEquipAcClient:
    return hass.data[DOMAIN][entry.entry_id]
