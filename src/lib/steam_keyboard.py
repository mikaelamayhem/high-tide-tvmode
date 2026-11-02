# steam_keyboard.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Open Steam's on-screen keyboard when a text field gets focus.

Steam shows its keyboard when asked through the steam://open/keyboard link.
This only works while Steam is running (Big Picture or Game Mode), so we
check for Steam first and never start Steam just to show a keyboard.
"""

import logging
import os
from pathlib import Path

from gi.repository import Gio, Gtk

logger = logging.getLogger(__name__)

STEAM_KEYBOARD_URI = "steam://open/keyboard"

# Set by Steam on apps it launches, and by gamescope (Game Mode)
_STEAM_ENV_VARS = (
    "SteamGameId",
    "SteamAppId",
    "SteamClientLaunch",
    "GAMESCOPE_WAYLAND_DISPLAY",
)

_STEAM_PID_FILES = (
    Path.home() / ".steam" / "steam.pid",
    Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam.pid",
)


def is_steam_running() -> bool:
    """Best effort check that the Steam client is running."""
    if any(os.environ.get(name) for name in _STEAM_ENV_VARS):
        return True

    for pid_file in _STEAM_PID_FILES:
        try:
            pid = int(pid_file.read_text().strip())
        except (OSError, ValueError):
            continue
        if Path(f"/proc/{pid}").exists():
            return True

    return False


def open_steam_keyboard() -> bool:
    """Ask Steam to show its on-screen keyboard. Returns True if asked."""
    if not is_steam_running():
        return False
    try:
        Gio.AppInfo.launch_default_for_uri(STEAM_KEYBOARD_URI, None)
    except Exception:
        logger.exception("Could not open the Steam on-screen keyboard")
        return False
    return True


def is_text_input(widget: Gtk.Widget | None) -> bool:
    """True for widgets the user types into (entries, search, text views).

    In GTK 4 the focused widget of an entry is the Gtk.Text inside it.
    """
    if isinstance(widget, (Gtk.Text, Gtk.TextView)):
        return widget.get_editable()
    return False


class SteamKeyboardWatcher:
    """Watches a window's focus and opens the keyboard on text fields.

    The keyboard opens when focus moves onto a text field, not on every
    focus change inside the same field.
    """

    def __init__(self, window: Gtk.Window) -> None:
        self._window = window
        self._enabled = False
        self._last_was_text = False
        window.connect("notify::focus-widget", self._on_focus_changed)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._last_was_text = False

    def _on_focus_changed(self, window: Gtk.Window, *args) -> None:
        from . import spatial_focus

        focused = is_text_input(window.get_focus())
        # With a controller, the keyboard opens when you press A on the
        # text box instead, so moving past it doesn't pop it up
        if spatial_focus.moving:
            self._last_was_text = focused
            return
        if self._enabled and focused and not self._last_was_text:
            open_steam_keyboard()
        self._last_was_text = focused
