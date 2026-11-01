# console_mode.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Console mode: a full screen, controller friendly layout.

Console mode is on when the "console-mode" setting is set, or when the app
was started with --console (which only lasts for that session). Later
console features (controller input, on-screen keyboard) hook in through
apply_console_mode().

Scaling works in three layers:
- text: Gtk.Settings "gtk-xft-dpi" makes every font bigger
- controls: a CSS provider makes buttons, rows and icons bigger
- artwork: scale_widget_sizes() enlarges fixed size images on new widgets
"""

from gi.repository import Gdk, Gio, Gtk

CONSOLE_CSS_CLASS = "console-mode"

# Gtk's default dpi, stored as dpi * 1024
_BASE_XFT_DPI = 96 * 1024

_state = {"enabled": False, "scale": 1.0}
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


def apply_console_mode(window: Gtk.Window, enabled: bool, scale_percent: int) -> None:
    """Turn the console layout on or off for a window."""
    _state["enabled"] = enabled
    _state["scale"] = max(scale_percent, 100) / 100

    if enabled:
        window.add_css_class(CONSOLE_CSS_CLASS)
        window.fullscreen()
    else:
        window.remove_css_class(CONSOLE_CSS_CLASS)
        window.unfullscreen()

    _apply_text_scale(get_scale())
    _apply_css_scale(get_scale())


def _apply_text_scale(scale: float) -> None:
    global _default_xft_dpi

    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is None:
        return
    if _default_xft_dpi is None:
        current = gtk_settings.props.gtk_xft_dpi
        _default_xft_dpi = current if current > 0 else _BASE_XFT_DPI

    if scale == 1.0:
        # Give control back to the desktop's own font scaling
        gtk_settings.reset_property("gtk-xft-dpi")
    else:
        gtk_settings.props.gtk_xft_dpi = int(_default_xft_dpi * scale)


def _apply_css_scale(scale: float) -> None:
    global _css_provider

    display = Gdk.Display.get_default()
    if display is None:
        return

    if _css_provider is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _css_provider)
        _css_provider = None

    if scale == 1.0:
        return

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
    window.console-mode *:focus-visible {{
        outline-width: {px(3)};
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
