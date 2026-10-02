"""
Async BLE client + decoded register state for one OutEquipPro rooftop AC.

Deliberately minimal for v0.1: a single connect attempt per button press
(no automatic reconnect loop, no adapter power-cycling/reset logic). The
Venus OS sibling project needed a lot of that to fight a specific Raspberry
Pi onboard-BLE-chip incompatibility (see its NOTES.md) — rather than port
that complexity in blind, this starts clean and only grows troubleshooting
logic if/when it's actually needed against HA's own Bluetooth stack.

Connection is explicit: the AC's BLE module only accepts one central at a
time, so this integration holds the link only between a Connect button
press and a Disconnect button press (or an unrecoverable error), not
continuously — same reasoning as the Venus OS driver, simpler mechanism.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from . import ac_protocol as proto
from .const import (
    ACTIVE_HANDSHAKE_TIMEOUT_S,
    MIN_WRITE_SPACING_S,
    NOTIFY_CHAR_UUID,
    POLL_INTERVAL_S,
    RESPONSE_TIMEOUT_S,
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_FAILED,
    WRITE_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)


class AcState:
    """Decoded register values. Plain attribute bag, not a dataclass, so
    entities can read it directly without a copy each update."""

    def __init__(self) -> None:
        self.connection: str = STATE_DISCONNECTED
        self.power: bool | None = None
        self.mode: int | None = None
        self.mode_name: str | None = None
        self.fan_speed: int | None = None
        self.setpoint: int | None = None
        self.swing: bool | None = None
        self.intake_temp: int | None = None
        self.outlet_temp: int | None = None
        self.supply_voltage: float | None = None
        self.last_update: float | None = None
        self.last_error: str | None = None


class OutEquipAcClient:
    """Owns one on-demand BLE link to the AC and its decoded state."""

    def __init__(
        self,
        mac_address: str,
        ble_device_resolver: Callable[[], BLEDevice | None],
        on_update: Callable[[], None],
    ) -> None:
        self.mac_address = mac_address
        self._resolve_ble_device = ble_device_resolver
        self._on_update = on_update

        self.state = AcState()
        self._client: BleakClient | None = None
        self._rx_buf = bytearray()
        self._cmd_lock = asyncio.Lock()
        self._last_write_time = 0.0
        self._notify_event = asyncio.Event()
        self._poll_task: asyncio.Task | None = None
        self._active_handshake_event = asyncio.Event()
        self._active_handshake_value: int | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    # -- lifecycle --------------------------------------------------------

    async def connect(self) -> None:
        if self.connected:
            return
        self.state.connection = STATE_CONNECTING
        self.state.last_error = None
        self._on_update()

        ble_device = self._resolve_ble_device()
        if ble_device is None:
            self._fail(
                "AC not visible to Home Assistant's Bluetooth scanner right "
                f"now (MAC {self.mac_address}). Make sure the AC is powered "
                "on and within range of a Bluetooth adapter or proxy."
            )
            raise ConnectionError(self.state.last_error)

        try:
            client = await establish_connection(
                BleakClient, ble_device, f"OutEquipAC {self.mac_address}"
            )
            await client.start_notify(NOTIFY_CHAR_UUID, self._on_notify)
            self._client = client
            self._rx_buf.clear()
            await self._do_active_handshake()
        except (BleakError, TimeoutError) as err:
            self._fail(str(err))
            self._client = None
            raise ConnectionError(str(err)) from err

        self.state.connection = STATE_CONNECTED
        self._on_update()
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def disconnect(self) -> None:
        if self._poll_task is not None:
            self._poll_task.cancel()
            self._poll_task = None
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.disconnect()
            except BleakError:
                _LOGGER.debug("Error disconnecting from AC", exc_info=True)
        self.state.connection = STATE_DISCONNECTED
        self._on_update()

    def _fail(self, message: str) -> None:
        self.state.connection = STATE_FAILED
        self.state.last_error = message
        self._on_update()

    # -- protocol -----------------------------------------------------------

    def _on_notify(self, _handle, data: bytearray) -> None:
        self._rx_buf.extend(data)
        while True:
            try:
                frame = proto.try_decode(self._rx_buf)
            except (proto.ChecksumError, proto.FrameError):
                _LOGGER.warning("Dropping malformed frame data: %r", bytes(data))
                self._rx_buf.clear()
                return
            if frame is None:
                return
            self._notify_event.set()
            self._apply_frame(frame)

    async def _send(self, payload: bytes) -> None:
        if self._client is None:
            raise ConnectionError("Not connected")
        async with self._cmd_lock:
            elapsed = time.monotonic() - self._last_write_time
            if elapsed < MIN_WRITE_SPACING_S:
                await asyncio.sleep(MIN_WRITE_SPACING_S - elapsed)
            self._notify_event.clear()
            await self._client.write_gatt_char(WRITE_CHAR_UUID, payload, response=False)
            self._last_write_time = time.monotonic()

    async def _wait_for_notification(self, timeout: float) -> bool:
        try:
            await asyncio.wait_for(self._notify_event.wait(), timeout)
        except asyncio.TimeoutError:
            return False
        return True

    async def _do_active_handshake(self) -> None:
        """Register 66 (Active) must be queried immediately after
        connecting, and 1 written back if it replies 2, before anything
        else is queried -- confirmed required against real hardware."""
        self._active_handshake_event.clear()
        self._active_handshake_value = None
        await self._send(proto.make_query(proto.REG_ACTIVE))
        deadline = time.monotonic() + ACTIVE_HANDSHAKE_TIMEOUT_S
        while time.monotonic() < deadline and not self._active_handshake_event.is_set():
            await self._wait_for_notification(0.5)
        if not self._active_handshake_event.is_set():
            _LOGGER.warning("No reply to Active handshake within timeout; proceeding anyway")
            return
        if self._active_handshake_value == 2:
            await self._send(proto.make_write(proto.REG_ACTIVE, 1))
            await asyncio.sleep(0.5)

    async def _poll_loop(self) -> None:
        registers = proto.DEFAULT_POLL_REGISTERS
        index = 0
        try:
            while self.connected:
                reg = registers[index % len(registers)]
                index += 1
                await self._send(proto.make_query(reg))
                deadline = time.monotonic() + RESPONSE_TIMEOUT_S
                got_reply = False
                while time.monotonic() < deadline:
                    if await self._wait_for_notification(0.5):
                        got_reply = True
                        break
                if not got_reply:
                    _LOGGER.debug("No reply to poll of register %s within timeout", reg)
                await asyncio.sleep(
                    max(0.0, POLL_INTERVAL_S / len(registers) - MIN_WRITE_SPACING_S)
                )
        except asyncio.CancelledError:
            raise
        except (BleakError, ConnectionError) as err:
            _LOGGER.warning("BLE session failed: %s", err)
            self._client = None
            self._fail(str(err))

    def _apply_frame(self, frame: proto.Frame) -> None:
        reg, val = frame.register, frame.value
        if reg == proto.REG_ACTIVE:
            self._active_handshake_value = val
            self._active_handshake_event.set()
        elif reg == proto.REG_POWER:
            self.state.power = val == proto.ON_OFF_ON
        elif reg == proto.REG_MODE:
            self.state.mode = val
            self.state.mode_name = proto.MODE_NAMES.get(val, f"Unknown ({val})")
        elif reg == proto.REG_SETPOINT:
            self.state.setpoint = val
        elif reg == proto.REG_FAN_SPEED:
            self.state.fan_speed = val
        elif reg == proto.REG_SWING:
            self.state.swing = val == proto.ON_OFF_ON
        elif reg == proto.REG_INTAKE_TEMP:
            self.state.intake_temp = proto.to_signed_byte(val)
        elif reg == proto.REG_OUTLET_TEMP:
            self.state.outlet_temp = proto.to_signed_byte(val)
        elif reg == proto.REG_VOLTAGE:
            # Endianness for reg 18 is unconfirmed -- decivolts either way;
            # sanity-check against a plausible 12V/24V system range and flip
            # if garbage (same heuristic as the Venus OS driver).
            volts = val / 10.0
            if not (5.0 <= volts <= 60.0):
                swapped = int.from_bytes(val.to_bytes(2, "big"), "little")
                volts = swapped / 10.0
            self.state.supply_voltage = round(volts, 1)
        self.state.last_update = time.time()
        self._on_update()

    # -- write helpers (entity -> device) ------------------------------------

    async def set_power(self, on: bool) -> None:
        if not on:
            # Firmware quirk: always switch to Cooling before powering off,
            # or heat mode phantom-engages periodically while nominally off.
            await self._send(proto.make_write(proto.REG_MODE, proto.MODE_COOL))
        await self._send(
            proto.make_write(proto.REG_POWER, proto.ON_OFF_ON if on else proto.ON_OFF_OFF)
        )

    async def set_mode(self, mode: int) -> None:
        await self._send(proto.make_write(proto.REG_MODE, mode))

    async def set_fan_speed(self, speed: int) -> None:
        await self._send(proto.make_write(proto.REG_FAN_SPEED, max(1, min(5, speed))))

    async def set_setpoint(self, temp: int) -> None:
        await self._send(proto.make_write(proto.REG_SETPOINT, temp))

    async def set_swing(self, on: bool) -> None:
        await self._send(
            proto.make_write(proto.REG_SWING, proto.ON_OFF_ON if on else proto.ON_OFF_OFF)
        )
