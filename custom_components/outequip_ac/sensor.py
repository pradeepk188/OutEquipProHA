"""Read-only sensors (temps, voltage, connection state) for the OutEquip Pro AC."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import OutEquipAcEntity, get_client


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    client = get_client(hass, entry)
    async_add_entities(
        [
            OutEquipAcConnectionSensor(client, entry),
            OutEquipAcIntakeTempSensor(client, entry),
            OutEquipAcOutletTempSensor(client, entry),
            OutEquipAcVoltageSensor(client, entry),
        ]
    )


class OutEquipAcConnectionSensor(OutEquipAcEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="connection_state",
        translation_key="connection_state",
        icon="mdi:bluetooth",
        device_class=SensorDeviceClass.ENUM,
        options=["disconnected", "connecting", "connected", "failed"],
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "connection_state")

    @property
    def native_value(self) -> str:
        return self._client.state.connection

    @property
    def extra_state_attributes(self):
        err = self._client.state.last_error
        return {"last_error": err} if err else {}


class OutEquipAcIntakeTempSensor(OutEquipAcEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="intake_temperature",
        translation_key="intake_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "intake_temperature")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def native_value(self):
        return self._client.state.intake_temp


class OutEquipAcOutletTempSensor(OutEquipAcEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="outlet_temperature",
        translation_key="outlet_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "outlet_temperature")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def native_value(self):
        return self._client.state.outlet_temp


class OutEquipAcVoltageSensor(OutEquipAcEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="supply_voltage",
        translation_key="supply_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    )

    def __init__(self, client, entry) -> None:
        super().__init__(client, entry, "supply_voltage")

    @property
    def available(self) -> bool:
        return self.connected

    @property
    def native_value(self):
        return self._client.state.supply_voltage
