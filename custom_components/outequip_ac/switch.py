"""Power + Swing switches for the OutEquip Pro AC integration.

Unavailable (greyed out) until the AC is connected.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import OutEquipAcEntity, get_client


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client = get_client(hass, entry)
    async_add_entities(
        [
            OutEquipAcPowerSwitch(client, entry),
            OutEquipAcSwingSwitch(client, entry),
        ]
    )


class OutEquipAcPowerSwitch(OutEquipAcEntity, SwitchEntity):
    entity_description = SwitchEntityDescription(
        key="power", translation_key="power", icon="mdi:air-conditioner"
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "power")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def is_on(self) -> bool | None:
        return self._client.state.power

    async def async_turn_on(self, **kwargs) -> None:
        await self._client.set_power(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._client.set_power(False)


class OutEquipAcSwingSwitch(OutEquipAcEntity, SwitchEntity):
    entity_description = SwitchEntityDescription(
        key="swing", translation_key="swing", icon="mdi:arrow-up-down"
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "swing")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def is_on(self) -> bool | None:
        return self._client.state.swing

    async def async_turn_on(self, **kwargs) -> None:
        await self._client.set_swing(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._client.set_swing(False)
