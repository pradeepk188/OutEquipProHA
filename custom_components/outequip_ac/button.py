"""Connect / Disconnect buttons for the OutEquip Pro AC integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import OutEquipAcEntity, get_client

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client = get_client(hass, entry)
    async_add_entities(
        [
            OutEquipAcConnectButton(client, entry),
            OutEquipAcDisconnectButton(client, entry),
        ]
    )


class OutEquipAcConnectButton(OutEquipAcEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="connect", translation_key="connect", icon="mdi:bluetooth-connect"
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "connect")

    async def async_press(self) -> None:
        try:
            await self._client.connect()
        except ConnectionError as err:
            raise HomeAssistantError(str(err)) from err


class OutEquipAcDisconnectButton(OutEquipAcEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="disconnect", translation_key="disconnect", icon="mdi:bluetooth-off"
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "disconnect")

    async def async_press(self) -> None:
        await self._client.disconnect()
