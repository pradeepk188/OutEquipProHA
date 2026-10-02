"""Config flow for the OutEquip Pro AC integration.

No hardcoded MAC address: this scans Home Assistant's own Bluetooth
discovery cache for nearby devices and flags anything whose advertised
name starts with "KT2026" (the OutEquipPro/Kingtec BLE module's naming
pattern, confirmed against one real unit) as a probable candidate. A
manual-entry fallback is always available in case the AC hasn't been seen
by HA's scanner yet, or uses a different name.
"""

from __future__ import annotations

import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_MAC, CONF_NAME, DOMAIN, NAME_PREFIX

MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
MANUAL_ENTRY = "__manual__"


class OutEquipAcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Scan for, or manually enter, one OutEquip Pro AC unit."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, str] = {}  # address -> display name
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None

    # -- automatic discovery (manifest.json "bluetooth" matcher) -----------

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        assert self._discovery_info is not None
        if user_input is not None:
            return self._create_entry(
                self._discovery_info.address, self._discovery_info.name
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    # -- manual flow: scan list with a manual-entry fallback -----------------

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            address = user_input[CONF_MAC]
            if address == MANUAL_ENTRY:
                return await self.async_step_manual()
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self._create_entry(address, self._discovered[address])

        current_addresses = self._async_current_ids()
        self._discovered = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if info.address in current_addresses:
                continue
            name = info.name or info.address
            if name.upper().startswith(NAME_PREFIX):
                self._discovered[info.address] = name

        if not self._discovered:
            return await self.async_step_manual()

        options = {addr: f"{name} ({addr})" for addr, name in self._discovered.items()}
        options[MANUAL_ENTRY] = "Enter MAC address manually..."
        schema = vol.Schema({vol.Required(CONF_MAC): vol.In(options)})
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_manual(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_MAC].strip().upper()
            if not MAC_RE.match(address):
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self._create_entry(address, user_input.get(CONF_NAME) or address)

        schema = vol.Schema(
            {
                vol.Required(CONF_MAC): str,
                vol.Optional(CONF_NAME): str,
            }
        )
        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    def _create_entry(self, address: str, name: str) -> FlowResult:
        return self.async_create_entry(
            title=name, data={CONF_MAC: address, CONF_NAME: name}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OutEquipAcOptionsFlow(config_entry)


class OutEquipAcOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
