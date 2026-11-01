# console_hints.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""The bar of controller button hints shown at the bottom in console mode."""

from gettext import gettext as _

from gi.repository import Gtk

ICON_RESOURCE = "/io/github/nokse22/high-tide/icons/console/{style}/{button}.svg"
ICON_SIZE = 28

# (buttons, label). Several buttons share one hint, like LB/RB.
HINTS = (
    (("dpad",), _("Move")),
    (("a",), _("Select")),
    (("b",), _("Back")),
    (("x",), _("Play/Pause")),
    (("y",), _("Search")),
    (("lb", "rb"), _("Player/Lyrics/Queue")),
    (("lt", "rt"), _("Previous/Next")),
    (("rstick",), _("Scroll/Volume")),
    (("select",), _("Home/Explore/Collection")),
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
