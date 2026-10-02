# OutEquipProHA

A Home Assistant custom integration for the OutEquip Pro rooftop AC,
talking directly to its built-in BLE module (`bleak`, via HA's own
Bluetooth stack) — no Venus OS/Victron GX device involved.

Installable via [HACS](https://hacs.xyz/) as a custom repository, or by
copying `custom_components/outequip_ac/` into your `config/custom_components/`
folder by hand.

## Setup

1. Settings → Devices & Services → Add Integration → **OutEquip Pro AC**.
2. HA scans its Bluetooth cache for anything already advertising a name
   starting with `KT2026` (the AC's module naming pattern) and lists
   probable candidates. Pick yours, or choose **Enter MAC address
   manually** if it isn't listed yet (nothing is hardcoded — every unit's
   MAC is entered through this flow, not baked into the integration).
3. The integration is added with everything unavailable except two
   buttons: **Connect** and **Disconnect**. The AC's BLE module only
   accepts one connection at a time, so this integration holds the link
   only while you want it to, same as the phone app would.
4. Press **Connect**. Once connected, **Power**, **Mode**, **Fan speed**,
   **Setpoint temperature**, and **Swing** controls become available, along
   with read-only intake/outlet temperature and supply voltage sensors.
   Press **Disconnect** when done (or just leave it — it won't
   auto-reconnect; press Connect again next time).

## Scope (v0.1)

This starts intentionally small. A sibling project
([`VeOutEquipAC`](https://github.com/pradeepk188/VeOutEquipAC)) bridges the
same AC onto a Venus OS/Victron GX device instead, and needed substantial
troubleshooting to get there reliably (a Raspberry Pi's onboard BLE chip
failing to complete the AC module's connection handshake, adapter
power-cycling workarounds, exponential reconnect backoff, etc. — see that
repo's `NOTES.md`). None of that has been ported here yet. If Home
Assistant's own Bluetooth stack hits the same class of problem, the fix
(most likely a USB Bluetooth adapter or an ESPHome Bluetooth proxy instead
of an onboard/SoC radio) is expected to be the same, but troubleshooting
logic will be added here incrementally, once actually needed against real
hardware, rather than copied in speculatively.

The protocol layer (`ac_protocol.py`) — frame format, register map,
quirks like the power-off-forces-Cool workaround and the register-66
"Active" handshake — is ported verbatim from that project, since it's
already confirmed against a real BLE capture of the OutEquipPro app.
