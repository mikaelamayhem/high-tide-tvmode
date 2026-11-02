# console_mode.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Console mode: a full screen, controller friendly layout.

Console mode is on when the "console-mode" setting is set, or when the app
was started with --console (which only lasts for that session). Later
console features (controller input, on-screen keyboard) hook in through
apply_console_mode().

With "match the screen" on, the scale also follows the screen height
(like a game HUD designed for 1080p), so the layout takes the same share
of the screen at 720p, 1080p or 4K.

Scaling works in three layers:
- text: Gtk.Settings "gtk-xft-dpi" makes every font bigger
- controls: a CSS provider makes buttons, rows and icons bigger
- artwork: scale_widget_sizes() enlarges fixed size images on new widgets
"""

from gi.repository import Adw, Gdk, Gio, Gtk

CONSOLE_CSS_CLASS = "console-mode"

# Gtk's default dpi, stored as dpi * 1024
_BASE_XFT_DPI = 96 * 1024

# The screen height the interface size is designed for when matching the
# screen; heights are in logical pixels, so desktop scaling is included
_REFERENCE_HEIGHT = 1080

_state = {"enabled": False, "scale": 1.0, "auto": False}
_css_provider: Gtk.CssProvider | None = None
_default_xft_dpi: int | None = None


def is_console_mode(settings: Gio.Settings, app: Gtk.Application | None) -> bool:
    """Return True if console mode is on, from the setting or --console."""
    forced = bool(getattr(app, "console_forced", False))
    return forced or settings.get_boolean("console-mode")


def is_enabled() -> bool:
    """True while console mode is on."""
    return _state["enabled"]


def get_scale() -> float:
    """The current console scale factor, or 1.0 outside console mode."""
    return _state["scale"] if _state["enabled"] else 1.0


def screen_height(window: Gtk.Window) -> int | None:
    """The height of the screen the window is on, in logical pixels."""
    display = window.get_display() or Gdk.Display.get_default()
    if display is None:
        return None
    monitor = None
    surface = window.get_surface()
    if surface is not None:
        monitor = display.get_monitor_at_surface(surface)
    if monitor is None:
        monitors = display.get_monitors()
        monitor = monitors.get_item(0) if monitors.get_n_items() else None
    if monitor is None:
        return None
    return monitor.get_geometry().height or None


def compute_scale(window: Gtk.Window, scale_percent: int, auto: bool) -> float:
    """The scale factor for a window from the settings."""
    if not auto:
        return max(scale_percent, 100) / 100
    height = screen_height(window) or _REFERENCE_HEIGHT
    return min(4.0, max(0.5, scale_percent / 100 * height / _REFERENCE_HEIGHT))


def apply_console_mode(
    window: Gtk.Window, enabled: bool, scale_percent: int, auto: bool = False
) -> None:
    """Turn the console layout on or off for a window."""
    _state["enabled"] = enabled
    _state["auto"] = auto and enabled
    _state["scale"] = compute_scale(window, scale_percent, auto)

    # Light text reads best on the dimmed album art background
    Adw.StyleManager.get_default().set_color_scheme(
        Adw.ColorScheme.FORCE_DARK if enabled else Adw.ColorScheme.DEFAULT
    )
    if enabled:
        window.add_css_class(CONSOLE_CSS_CLASS)
        window.fullscreen()
    else:
        window.remove_css_class(CONSOLE_CSS_CLASS)
        window.unfullscreen()

    _apply_window_buttons(enabled)
    _apply_text_scale(get_scale())
    _apply_css_scale(get_scale())


def _apply_window_buttons(enabled: bool) -> None:
    """Hide the window icon and minimize/maximize/close buttons.

    A full screen console app doesn't need them; the controller closes
    things with B, and the icon took the space of the LB hint.
    """
    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is None:
        return
    if enabled:
        gtk_settings.props.gtk_decoration_layout = ":"
    else:
        gtk_settings.reset_property("gtk-decoration-layout")


def _apply_text_scale(scale: float) -> None:
    global _default_xft_dpi

    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is None:
        return
    if _default_xft_dpi is None:
        current = gtk_settings.props.gtk_xft_dpi
        _default_xft_dpi = current if current > 0 else _BASE_XFT_DPI

    if scale == 1.0 and not _state["auto"]:
        # Give control back to the desktop's own font scaling
        gtk_settings.reset_property("gtk-xft-dpi")
    else:
        # Matching the screen ignores the desktop's font scaling, so the
        # text is the same size on every machine
        base = _BASE_XFT_DPI if _state["auto"] else _default_xft_dpi
        gtk_settings.props.gtk_xft_dpi = int(base * scale)


def _apply_css_scale(scale: float) -> None:
    global _css_provider

    display = Gdk.Display.get_default()
    if display is None:
        return

    if _css_provider is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _css_provider)
        _css_provider = None

    if scale == 1.0 and not _state["auto"]:
        return

    # Text already follows the desktop's font scaling (e.g. 125% in KDE)
    # on top of ours, so grow icons and controls by the same amount to keep
    # them in proportion with the text
    if not _state["auto"]:
        scale *= (_default_xft_dpi or _BASE_XFT_DPI) / _BASE_XFT_DPI

    def px(value: float) -> str:
        return f"{round(value * scale)}px"

    css = f"""
    window.console-mode button {{
        min-height: {px(34)};
        min-width: {px(34)};
        padding: {px(5)} {px(12)};
    }}
    window.console-mode button.circular,
    window.console-mode button.flat.circular {{
        min-width: {px(34)};
        padding: {px(5)};
    }}
    window.console-mode image {{
        -gtk-icon-size: {px(16)};
    }}
    window.console-mode row,
    window.console-mode listview > row {{
        min-height: {px(50)};
    }}
    window.console-mode headerbar {{
        min-height: {px(47)};
    }}
    window.console-mode scale slider {{
        min-width: {px(20)};
        min-height: {px(20)};
    }}
    """

    _css_provider = Gtk.CssProvider()
    _css_provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(
        display, _css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
    )


def scale_widget_sizes(root: Gtk.Widget) -> None:
    """Enlarge fixed size images and size requests inside a new widget.

    Call this once, at the end of a widget's __init__. It does nothing outside
    console mode. Widgets made before a scale change keep their old size
    until the page is opened again.
    """
    scale = get_scale()
    if scale == 1.0:
        return

    stack = [root]
    while stack:
        widget = stack.pop()

        # Skip widgets that were already scaled (e.g. a card inside a page)
        if getattr(widget, "_ht_console_scaled", False):
            continue
        widget._ht_console_scaled = True

        if isinstance(widget, Gtk.Image):
            size = widget.get_pixel_size()
            if size > 0:
                widget.set_pixel_size(round(size * scale))

        width, height = widget.get_size_request()
        if width > 0 or height > 0:
            widget.set_size_request(
                round(width * scale) if width > 0 else width,
                round(height * scale) if height > 0 else height,
            )

        child = widget.get_first_child()
        while child is not None:
            stack.append(child)
            child = child.get_next_sibling()
