# gamepad.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Controller input for console mode, using libmanette.

Buttons are turned into named actions ("select", "back", "play-pause"...)
that the window handles. The D-pad and left stick move keyboard focus,
with key repeat while held.

If libmanette is not installed, console mode still works with a keyboard,
mouse or Steam Input's keyboard emulation; there is just no direct
controller support.
"""

import logging
from typing import Callable

import gi
from gi.repository import GLib, Gtk

try:
    gi.require_version("Manette", "0.2")
    from gi.repository import Manette
except (ImportError, ValueError):
    Manette = None

logger = logging.getLogger(__name__)

# Linux input event codes, which libmanette uses for standard buttons
BTN_SOUTH = 304  # A / Cross
BTN_EAST = 305  # B / Circle
BTN_NORTH = 307  # Y / Triangle (libmanette maps by position)
BTN_WEST = 308  # X / Square
BTN_TL = 310
BTN_TR = 311
BTN_SELECT = 314
BTN_START = 315
BTN_DPAD_UP = 544
BTN_DPAD_DOWN = 545
BTN_DPAD_LEFT = 546
BTN_DPAD_RIGHT = 547

ABS_X = 0
ABS_Y = 1
ABS_HAT0X = 16
ABS_HAT0Y = 17

BUTTON_ACTIONS = {
    BTN_SOUTH: "select",
    BTN_EAST: "back",
    BTN_WEST: "play-pause",
    BTN_NORTH: "search",
    BTN_TL: "previous",
    BTN_TR: "next",
    BTN_START: "settings",
    BTN_SELECT: "home",
}

DPAD_DIRECTIONS = {
    BTN_DPAD_UP: Gtk.DirectionType.UP,
    BTN_DPAD_DOWN: Gtk.DirectionType.DOWN,
    BTN_DPAD_LEFT: Gtk.DirectionType.LEFT,
    BTN_DPAD_RIGHT: Gtk.DirectionType.RIGHT,
}

STICK_THRESHOLD = 0.6
REPEAT_DELAY_MS = 400
REPEAT_INTERVAL_MS = 120

BUTTON_STYLES = ("xbox", "playstation", "steamdeck")


def is_available() -> bool:
    """True if libmanette could be loaded."""
    return Manette is not None


def guess_button_style(device_name: str) -> str:
    """Pick an icon set from the controller's name."""
    name = device_name.lower()
    if any(
        word in name
        for word in ("sony", "playstation", "dualsense", "dualshock", "ps4", "ps5")
    ) or name == "wireless controller":
        return "playstation"
    if "steam deck" in name or "valve" in name:
        return "steamdeck"
    return "xbox"


class ConsoleGamepad:
    """Listens to every connected controller and reports actions.

    Args:
        window: the window whose focus the D-pad moves
        on_action: called with an action name from BUTTON_ACTIONS
        on_devices_changed: called with the list of connected device names
    """

    def __init__(
        self,
        window: Gtk.Window,
        on_action: Callable[[str], None],
        on_devices_changed: Callable[[list[str]], None],
    ) -> None:
        self._window = window
        self._on_action = on_action
        self._on_devices_changed = on_devices_changed
        self._enabled = False
        self._devices: list = []
        self._held_direction: Gtk.DirectionType | None = None
        self._repeat_source: int | None = None
        # Which direction each stick/hat axis is currently pushed to
        self._axis_direction: dict[int, Gtk.DirectionType | None] = {}
        self._starting = True

        if Manette is None:
            logger.info("libmanette not found, controller support is off")
            return

        self._monitor = Manette.Monitor.new()
        self._monitor.connect("device-connected", self._on_device_connected)
        self._monitor.connect("device-disconnected", self._on_device_disconnected)

        iterator = self._monitor.iterate()
        while True:
            has_next, device = iterator.next()
            if not has_next:
                break
            self._add_device(device)
        self._starting = False

    @property
    def device_names(self) -> list[str]:
        return [device.get_name() or "" for device in self._devices]

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._stop_repeat()

    # Devices

    def _add_device(self, device) -> None:
        self._devices.append(device)
        device.connect("button-press-event", self._on_button_press)
        device.connect("button-release-event", self._on_button_release)
        device.connect("absolute-axis-event", self._on_absolute_axis)
        device.connect("hat-axis-event", self._on_hat_axis)
        logger.info("Controller connected: %s", device.get_name())
        if not self._starting:
            self._on_devices_changed(self.device_names)

    def _on_device_connected(self, monitor, device) -> None:
        self._add_device(device)

    def _on_device_disconnected(self, monitor, device) -> None:
        if device in self._devices:
            self._devices.remove(device)
        self._stop_repeat()
        self._on_devices_changed(self.device_names)

    # Buttons

    def _on_button_press(self, device, event) -> None:
        if not self._enabled:
            return
        has_button, button = event.get_button()
        if not has_button:
            return

        if button in DPAD_DIRECTIONS:
            self._start_move(DPAD_DIRECTIONS[button])
        elif button in BUTTON_ACTIONS:
            self._on_action(BUTTON_ACTIONS[button])

    def _on_button_release(self, device, event) -> None:
        has_button, button = event.get_button()
        if has_button and DPAD_DIRECTIONS.get(button) == self._held_direction:
            self._stop_repeat()

    # Sticks and hats

    def _on_absolute_axis(self, device, event) -> None:
        has_axis, axis, value = event.get_absolute()
        if not has_axis or axis not in (ABS_X, ABS_Y):
            return
        if abs(value) < STICK_THRESHOLD:
            direction = None
        elif axis == ABS_X:
            direction = Gtk.DirectionType.LEFT if value < 0 else Gtk.DirectionType.RIGHT
        else:
            direction = Gtk.DirectionType.UP if value < 0 else Gtk.DirectionType.DOWN
        self._set_axis_direction(axis, direction)

    def _on_hat_axis(self, device, event) -> None:
        has_hat, axis, value = event.get_hat()
        if not has_hat or axis not in (ABS_HAT0X, ABS_HAT0Y):
            return
        if value == 0:
            direction = None
        elif axis == ABS_HAT0X:
            direction = Gtk.DirectionType.LEFT if value < 0 else Gtk.DirectionType.RIGHT
        else:
            direction = Gtk.DirectionType.UP if value < 0 else Gtk.DirectionType.DOWN
        self._set_axis_direction(axis, direction)

    def _set_axis_direction(self, axis: int, direction) -> None:
        previous = self._axis_direction.get(axis)
        if direction == previous:
            return
        self._axis_direction[axis] = direction
        if direction is None:
            if self._held_direction == previous:
                self._stop_repeat()
        elif self._enabled:
            self._start_move(direction)

    # Focus movement with repeat

    def _start_move(self, direction: Gtk.DirectionType) -> None:
        self._stop_repeat()
        self._held_direction = direction
        self._move_focus(direction)
        self._repeat_source = GLib.timeout_add(REPEAT_DELAY_MS, self._repeat_first)

    def _repeat_first(self) -> bool:
        self._repeat_source = GLib.timeout_add(REPEAT_INTERVAL_MS, self._repeat)
        return GLib.SOURCE_REMOVE

    def _repeat(self) -> bool:
        if self._held_direction is None:
            self._repeat_source = None
            return GLib.SOURCE_REMOVE
        self._move_focus(self._held_direction)
        return GLib.SOURCE_CONTINUE

    def _stop_repeat(self) -> None:
        self._held_direction = None
        if self._repeat_source is not None:
            GLib.source_remove(self._repeat_source)
            self._repeat_source = None

    def _move_focus(self, direction: Gtk.DirectionType) -> None:
        # Same as pressing an arrow key: GTK moves focus from the current
        # widget to the nearest one in that direction
        self._window.child_focus(direction)
