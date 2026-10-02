"""Fan speed + setpoint temperature numbers for the OutEquip Pro AC integration."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
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
            OutEquipAcFanSpeedNumber(client, entry),
            OutEquipAcSetpointNumber(client, entry),
        ]
    )


class OutEquipAcFanSpeedNumber(OutEquipAcEntity, NumberEntity):
    entity_description = NumberEntityDescription(
        key="fan_speed", translation_key="fan_speed", icon="mdi:fan"
    )
    _attr_native_min_value = 1
    _attr_native_max_value = 5
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "fan_speed")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def native_value(self) -> float | None:
        return self._client.state.fan_speed

    async def async_set_native_value(self, value: float) -> None:
        await self._client.set_fan_speed(int(value))


class OutEquipAcSetpointNumber(OutEquipAcEntity, NumberEntity):
    entity_description = NumberEntityDescription(
        key="setpoint",
        translation_key="setpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement="°F",
    )
    _attr_native_min_value = 60
    _attr_native_max_value = 90
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "setpoint")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def native_value(self) -> float | None:
        return self._client.state.setpoint

    async def async_set_native_value(self, value: float) -> None:
        await self._client.set_setpoint(int(value))
