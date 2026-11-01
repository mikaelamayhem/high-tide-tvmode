# console_mode.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Console mode: a full screen, controller friendly layout.

Console mode is on when the "console-mode" setting is set, or when the app
was started with --console (which only lasts for that session). Later
console features (scaling, controller input, on-screen keyboard) hook in
through apply_console_mode().
"""

from gi.repository import Gio, Gtk

CONSOLE_CSS_CLASS = "console-mode"


def is_console_mode(settings: Gio.Settings, app: Gtk.Application | None) -> bool:
    """Return True if console mode is on, from the setting or --console."""
    forced = bool(getattr(app, "console_forced", False))
    return forced or settings.get_boolean("console-mode")


def apply_console_mode(window: Gtk.Window, enabled: bool) -> None:
    """Turn the console layout on or off for a window."""
    if enabled:
        window.add_css_class(CONSOLE_CSS_CLASS)
        window.fullscreen()
    else:
        window.remove_css_class(CONSOLE_CSS_CLASS)
        window.unfullscreen()
