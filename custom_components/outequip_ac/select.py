"""Mode select for the OutEquip Pro AC integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ac_protocol as proto
from .entity import OutEquipAcEntity, get_client

MODE_OPTIONS = list(proto.MODE_NAMES.values())


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client = get_client(hass, entry)
    async_add_entities([OutEquipAcModeSelect(client, entry)])


class OutEquipAcModeSelect(OutEquipAcEntity, SelectEntity):
    entity_description = SelectEntityDescription(
        key="mode", translation_key="mode", icon="mdi:fan-auto"
    )
    _attr_options = MODE_OPTIONS

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "mode")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def current_option(self) -> str | None:
        return self._client.state.mode_name

    async def async_select_option(self, option: str) -> None:
        mode = proto.MODE_NAMES_REVERSE.get(option)
        if mode is not None:
            await self._client.set_mode(mode)
