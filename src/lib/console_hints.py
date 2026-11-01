# console_hints.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""The bar of controller button hints shown at the bottom in console mode."""

from gettext import gettext as _

from gi.repository import GLib, Gtk

ICON_RESOURCE = "/io/github/nokse22/high-tide/icons/console/{style}/{button}.svg"
ICON_SIZE = 28

# (buttons, label). Several buttons share one hint, like LT/RT.
# Bumpers, X and the triggers have icons next to the controls they use,
# so they are not repeated here.
HINTS = (
    (("dpad",), _("Move")),
    (("a",), _("Select")),
    (("b",), _("Back")),
    (("y",), _("Search")),
    (("lstick",), _("Volume")),
    (("rstick",), _("Scroll")),
    (("start",), _("Settings")),
)


class ConsoleHintsBar(Gtk.Box):
    """A row of button icons with what each button does."""

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
            halign=Gtk.Align.CENTER,
            margin_top=8,
            margin_bottom=8,
        )
        self.add_css_class("console-hints")
        self._icons: list[tuple[Gtk.Image, str]] = []

        for buttons, label in HINTS:
            hint = Gtk.Box(spacing=6)
            for button in buttons:
                image = Gtk.Image()
                hint.append(image)
                self._icons.append((image, button))
            hint.append(Gtk.Label(label=label))
            self.append(hint)

        self.set_style("xbox", 1.0)

    def set_style(self, style: str, scale: float) -> None:
        """Show icons for a controller style ("xbox", "playstation"...)."""
        for image, button in self._icons:
            image.set_from_resource(ICON_RESOURCE.format(style=style, button=button))
            image.set_pixel_size(round(ICON_SIZE * scale))


class ConsoleGlyphs:
    """Button icons placed right next to the controls they operate."""

    def __init__(self) -> None:
        self._icons: list[tuple[Gtk.Image, str]] = []
        self._style = "xbox"
        self._scale = 1.0
        self._visible = False

    def _new_icon(self, button: str) -> Gtk.Image:
        image = Gtk.Image(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        image._ht_console_scaled = True
        self._icons.append((image, button))
        self._update(image, button)
        return image

    def add_below(self, widget: Gtk.Widget, button: str) -> None:
        """Show a button icon under a widget inside a horizontal Gtk.Box."""
        parent = widget.get_parent()
        if not isinstance(parent, Gtk.Box):
            return
        previous = widget.get_prev_sibling()
        column = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER
        )
        parent.remove(widget)
        parent.insert_child_after(column, previous)
        column.append(widget)
        column.append(self._new_icon(button))

    def add_around(self, widget: Gtk.Widget, left: str, right: str) -> Gtk.Box:
        """Return a box with button icons on both sides of a widget.

        The caller puts the returned box where the widget used to be.
        """
        row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        row.append(self._new_icon(left))
        row.append(widget)
        row.append(self._new_icon(right))
        return row

    def set_style(self, style: str, scale: float, visible: bool) -> None:
        self._style, self._scale, self._visible = style, scale, visible
        for image, button in self._icons:
            self._update(image, button)

    def _update(self, image: Gtk.Image, button: str) -> None:
        image.set_from_resource(
            ICON_RESOURCE.format(style=self._style, button=button)
        )
        image.set_pixel_size(round(ICON_SIZE * self._scale))
        image.set_visible(self._visible)


class VolumeOsd(Gtk.Box):
    """A popup that shows the volume while the stick changes it."""

    HIDE_AFTER_MS = 1200

    def __init__(self) -> None:
        super().__init__(
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            visible=False,
        )
        self.add_css_class("osd")
        self.add_css_class("console-volume-osd")
        self._ht_console_scaled = True

        self._icon = Gtk.Image(icon_name="audio-volume-high-symbolic")
        self._bar = Gtk.LevelBar(min_value=0, max_value=1, hexpand=True)
        self._bar.set_size_request(240, -1)
        self._label = Gtk.Label(width_chars=4, xalign=1)
        for child in (self._icon, self._bar, self._label):
            self.append(child)

        self._hide_source: int | None = None

    def show_volume(self, volume: float) -> None:
        """Show the volume (0 to 1) and hide again shortly after."""
        volume = max(0.0, min(1.0, volume))
        self._bar.set_value(volume)
        self._label.set_label(f"{round(volume * 100)}%")
        if volume == 0:
            icon = "audio-volume-muted-symbolic"
        elif volume < 0.34:
            icon = "audio-volume-low-symbolic"
        elif volume < 0.67:
            icon = "audio-volume-medium-symbolic"
        else:
            icon = "audio-volume-high-symbolic"
        self._icon.set_from_icon_name(icon)
        self.set_visible(True)

        if self._hide_source is not None:
            GLib.source_remove(self._hide_source)
        self._hide_source = GLib.timeout_add(self.HIDE_AFTER_MS, self._hide)

    def _hide(self) -> bool:
        self._hide_source = None
        self.set_visible(False)
        return GLib.SOURCE_REMOVE
