"""Constants for the OutEquip Pro AC integration."""

DOMAIN = "outequip_ac"

CONF_MAC = "mac"
CONF_NAME = "name"

# The AC's BLE module advertises a name like "KT2026050001550" (confirmed
# against one real unit). Used both as a HA bluetooth-matcher pattern
# (manifest.json) for passive/automatic discovery, and to filter the
# candidate list shown by the config flow's manual scan step.
NAME_PREFIX = "KT2026"

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"

RESPONSE_TIMEOUT_S = 3.0
MIN_WRITE_SPACING_S = 0.4
POLL_INTERVAL_S = 6.0
ACTIVE_HANDSHAKE_TIMEOUT_S = 5.0

SIGNAL_UPDATE = f"{DOMAIN}_update"

STATE_DISCONNECTED = "disconnected"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_FAILED = "failed"
