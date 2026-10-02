"""
Frame codec for the OutEquipPro / Kingtec / Velit air-conditioner protocol.

Ported from the `VeOutEquipAC` Venus OS driver project, where this exact
register map and frame format were confirmed against a real OutEquipPro
unit (BLE HCI capture of the stock Android app, 2026-09-13 — see that
repo's NOTES.md for the full derivation). This file is intentionally a
plain, transport-agnostic codec (stdlib only) so it can be reused here
without pulling in any of that project's Venus-OS/bluepy-specific code.

Frame layout (8 bytes fixed + payload):
    5A 5A | LEN | DEV | REG | VAL | CHK | 0D 0A
    preamble(2) len(1) devtype(1) reg(1) val(1) checksum(1) postamble(2)

LEN counts dev+reg+val+checksum+postamble (value_len = length - 5).
CHK is an 8-bit additive sum of every preceding byte, masked to 0xFF.
Reading a register = sending it with value 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PREAMBLE = b"\x5a\x5a"
POSTAMBLE = b"\x0d\x0a"
DEVICE_TYPE_AC = 0x01

# --- Registers -------------------------------------------------------------

REG_POWER = 1
REG_MODE = 2
REG_SETPOINT = 3
REG_FAN_SPEED = 4
REG_INTAKE_TEMP = 7
REG_OUTLET_TEMP = 8
REG_SWING = 16
REG_VOLTAGE = 18
REG_ACTIVE = 66  # BLE handshake key, required immediately after connecting

# Keep this list short deliberately (v0.1): only what the UI actually
# surfaces. REG_POWER is last, not first -- querying it first in rotation
# was confirmed (on the Venus OS driver) to disconnect the AC within 1-3s
# every time.
DEFAULT_POLL_REGISTERS = (
    REG_MODE,
    REG_SETPOINT,
    REG_FAN_SPEED,
    REG_INTAKE_TEMP,
    REG_OUTLET_TEMP,
    REG_SWING,
    REG_VOLTAGE,
    REG_POWER,
)

ON_OFF_OFF = 1
ON_OFF_ON = 2

MODE_COOL = 1
MODE_HEAT = 2
MODE_FAN = 3
MODE_ECO_COOL = 4
MODE_SLEEP_COOL = 5
MODE_TURBO_COOL = 6
MODE_WET = 7

MODE_NAMES = {
    MODE_COOL: "Cool",
    MODE_HEAT: "Heat",
    MODE_FAN: "Fan",
    MODE_ECO_COOL: "Eco Cool",
    MODE_SLEEP_COOL: "Sleep Cool",
    MODE_TURBO_COOL: "Turbo Cool",
    MODE_WET: "Wet/Dehumidify",
}
MODE_NAMES_REVERSE = {v: k for k, v in MODE_NAMES.items()}


class ChecksumError(ValueError):
    pass


class FrameError(ValueError):
    pass


@dataclass(frozen=True)
class Frame:
    device_type: int
    register: int
    value: int  # single byte (0-255); every register documented so far fits

    def encode(self) -> bytes:
        body = bytes([self.device_type, self.register, self.value & 0xFF])
        length = len(body) + 1 + len(POSTAMBLE)
        header = PREAMBLE + bytes([length])
        payload = header + body
        checksum = sum(payload) & 0xFF
        return payload + bytes([checksum]) + POSTAMBLE

    @staticmethod
    def decode(raw: bytes) -> "Frame":
        if len(raw) < 8:
            raise FrameError(f"frame too short: {raw!r}")
        if raw[0:2] != PREAMBLE:
            raise FrameError(f"bad preamble: {raw[0:2]!r}")
        length = raw[2]
        dev_type = raw[3]
        reg = raw[4]
        value_len = length - 5
        if value_len < 1:
            raise FrameError(f"implausible length byte {length} in {raw!r}")
        value_bytes = raw[5:5 + value_len]
        checksum_index = 5 + value_len
        checksum = raw[checksum_index]
        postamble = raw[checksum_index + 1: checksum_index + 3]
        if postamble != POSTAMBLE:
            raise FrameError(f"bad postamble: {postamble!r} in {raw!r}")
        computed = sum(raw[0:checksum_index]) & 0xFF
        if computed != checksum:
            raise ChecksumError(
                f"checksum mismatch: got {checksum:#x}, computed {computed:#x} in {raw!r}"
            )
        value = int.from_bytes(value_bytes, byteorder="big", signed=False)
        return Frame(device_type=dev_type, register=reg, value=value)


def make_query(register: int, device_type: int = DEVICE_TYPE_AC) -> bytes:
    """Build a frame that queries `register` (value=0 means 'read')."""
    return Frame(device_type=device_type, register=register, value=0).encode()


def make_write(register: int, value: int, device_type: int = DEVICE_TYPE_AC) -> bytes:
    """Build a frame that writes `value` to `register`."""
    return Frame(device_type=device_type, register=register, value=value).encode()


def try_decode(buf: bytearray) -> Optional[Frame]:
    """Pull one complete frame out of a growing receive buffer, mutating
    `buf` to remove the consumed bytes. Returns None if not enough data yet.
    """
    start = buf.find(PREAMBLE)
    if start == -1:
        if len(buf) > 64:
            del buf[:-2]
        return None
    if start > 0:
        del buf[:start]
    if len(buf) < 4:
        return None
    length = buf[2]
    total_len = 3 + length
    if len(buf) < total_len:
        return None
    raw = bytes(buf[:total_len])
    del buf[:total_len]
    return Frame.decode(raw)


def to_signed_byte(val: int) -> int:
    val &= 0xFF
    return val - 256 if val >= 128 else val
