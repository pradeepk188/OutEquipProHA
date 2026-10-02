"""The OutEquip Pro AC integration.

Talks directly to the AC's built-in BLE module from Home Assistant's own
Bluetooth stack (bleak, via HA's bluetooth integration for device lookup).
Connection is explicit, not automatic: a Connect button starts a BLE
session and poll loop, a Disconnect button ends it -- the AC's BLE module
only accepts one central at a time, so staying connected permanently would
lock out the OutEquipPro phone app.
"""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client import OutEquipAcClient
from .const import CONF_MAC, DOMAIN, SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["button", "switch", "select", "number", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    mac = entry.data[CONF_MAC]

    def _resolve_ble_device():
        return bluetooth.async_ble_device_from_address(hass, mac, connectable=True)

    def _on_update() -> None:
        async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_{entry.entry_id}")

    client = OutEquipAcClient(mac, _resolve_ble_device, _on_update)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: OutEquipAcClient = hass.data[DOMAIN].pop(entry.entry_id)
        if client.connected:
            await client.disconnect()
    return unload_ok
