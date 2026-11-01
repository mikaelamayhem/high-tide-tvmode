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
import os
from pathlib import Path
from typing import Callable

import gi
from gi.repository import GLib, Gtk

from .spatial_focus import move_focus

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
BTN_TL2 = 312  # triggers, on controllers that report them as buttons
BTN_TR2 = 313
BTN_SELECT = 314
BTN_START = 315
BTN_DPAD_UP = 544
BTN_DPAD_DOWN = 545
BTN_DPAD_LEFT = 546
BTN_DPAD_RIGHT = 547

ABS_X = 0
ABS_Y = 1
ABS_Z = 2  # left trigger
ABS_RX = 3
ABS_RY = 4
ABS_RZ = 5  # right trigger
ABS_HAT0X = 16
ABS_HAT0Y = 17

BUTTON_ACTIONS = {
    BTN_SOUTH: "select",
    BTN_EAST: "back",
    BTN_WEST: "play-pause",
    BTN_NORTH: "search",
    BTN_TL: "tab-previous",
    BTN_TR: "tab-next",
    BTN_TL2: "previous",
    BTN_TR2: "next",
    BTN_START: "settings",
    BTN_SELECT: "section-next",
}

# Triggers reported as axes: fire once when pushed past halfway
TRIGGER_ACTIONS = {
    ABS_Z: "previous",
    ABS_RZ: "next",
}
TRIGGER_THRESHOLD = 0.5

# Left stick left/right changes the volume, right stick up/down scrolls.
# The D-pad moves focus. Values are per tick at full tilt; a small tilt
# moves much slower.
SCROLL_SPEED = 28  # pixels
VOLUME_SPEED = 0.008  # of full volume, so about 2 seconds from 0 to 100%
STICK_INTERVAL_MS = 16
STICK_DEADZONE = 0.2

DPAD_DIRECTIONS = {
    BTN_DPAD_UP: Gtk.DirectionType.UP,
    BTN_DPAD_DOWN: Gtk.DirectionType.DOWN,
    BTN_DPAD_LEFT: Gtk.DirectionType.LEFT,
    BTN_DPAD_RIGHT: Gtk.DirectionType.RIGHT,
}

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
        on_scroll: Callable[[float], None] | None = None,
        on_volume: Callable[[float], None] | None = None,
    ) -> None:
        self._on_scroll = on_scroll
        self._on_volume = on_volume
        self._volume_tilt = 0.0  # left stick x
        self._scroll_tilt = 0.0  # right stick y
        self._stick_source: int | None = None
        self._triggers_pressed: set[int] = set()
        self._window = window
        self._on_action = on_action
        self._on_devices_changed = on_devices_changed
        self._enabled = False
        self._devices: list = []
        self._held_direction: Gtk.DirectionType | None = None
        self._repeat_source: int | None = None
        # Which direction each D-pad hat axis is currently pushed to
        self._axis_direction: dict[int, Gtk.DirectionType | None] = {}
        self._starting = True

        if Manette is None:
            logger.warning("libmanette not found, controller support is off")
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
        self._log_startup_state()

    def _log_startup_state(self) -> None:
        """Log what we can see, to help when no controller shows up."""
        try:
            events = sorted(Path("/dev/input").glob("event*"))
        except OSError:
            events = []
        readable = [p for p in events if os.access(p, os.R_OK)]
        logger.info(
            "Controller support ready: %d controller(s) %s, "
            "%d of %d input devices readable",
            len(self._devices),
            self.device_names,
            len(readable),
            len(events),
        )
        if events and not readable:
            logger.warning(
                "Can't read /dev/input. For Flatpak, allow it with: "
                "flatpak override --user --device=input io.github.nokse22.high-tide"
            )

    @property
    def device_names(self) -> list[str]:
        return [device.get_name() or "" for device in self._devices]

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._stop_repeat()
            self._volume_tilt = self._scroll_tilt = 0.0
            self._update_sticks()

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
        if not has_axis:
            return
        if axis in TRIGGER_ACTIONS:
            self._on_trigger(axis, value)
            return
        tilt = value if abs(value) > STICK_DEADZONE else 0.0
        if axis == ABS_X:
            self._volume_tilt = tilt
        elif axis == ABS_RY:
            self._scroll_tilt = tilt
        else:
            return
        self._update_sticks()

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

    def _on_trigger(self, axis: int, value: float) -> None:
        if value > TRIGGER_THRESHOLD:
            if axis not in self._triggers_pressed:
                self._triggers_pressed.add(axis)
                if self._enabled:
                    self._on_action(TRIGGER_ACTIONS[axis])
        elif value < TRIGGER_THRESHOLD / 2:
            self._triggers_pressed.discard(axis)

    # Sticks: volume and scrolling

    def _update_sticks(self) -> None:
        moving = self._volume_tilt or self._scroll_tilt
        if moving and self._enabled:
            if self._stick_source is None:
                self._stick_source = GLib.timeout_add(
                    STICK_INTERVAL_MS, self._stick_tick
                )
        elif self._stick_source is not None:
            GLib.source_remove(self._stick_source)
            self._stick_source = None

    def _stick_tick(self) -> bool:
        if not (self._volume_tilt or self._scroll_tilt):
            self._stick_source = None
            return GLib.SOURCE_REMOVE
        # Squaring the tilt makes small pushes move slowly
        if self._scroll_tilt and self._on_scroll is not None:
            self._on_scroll(self._scroll_tilt * abs(self._scroll_tilt) * SCROLL_SPEED)
        if self._volume_tilt and self._on_volume is not None:
            self._on_volume(self._volume_tilt * abs(self._volume_tilt) * VOLUME_SPEED)
        return GLib.SOURCE_CONTINUE

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
        # Show the focus highlight, like after a real key press
        self._window.set_focus_visible(True)
        # Go to whatever is next on screen in that direction
        move_focus(self._window, direction)
