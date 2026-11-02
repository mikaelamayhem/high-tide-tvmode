# console_more.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

""""More" as the last item of a row or list, for console mode.

With a controller, "More" is easiest to reach as the next stop after the
last album or song, instead of a small button in the section header.
"""

from gettext import gettext as _
from typing import Callable

from gi.repository import Gtk

from .console_mode import scale_widget_sizes

# Same size as an album card (see card_widget.blp)
_CARD_WIDTH = 167
_CARD_HEIGHT = 214
_ART_SIZE = 155
_ICON_SIZE = 48


def new_more_tile(on_click: Callable[[], None]) -> Gtk.Button:
    """An album-sized "More" tile for the end of a carousel."""
    art = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.START)
    art.set_size_request(_ART_SIZE, _ART_SIZE)
    art.add_css_class("console-more-art")
    art.append(
        Gtk.Image(
            icon_name="go-next-symbolic",
            pixel_size=_ICON_SIZE,
            hexpand=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
    )

    label = Gtk.Label(label=_("More"), xalign=0)
    label.add_css_class("title-4")

    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=3,
        margin_top=6,
        margin_bottom=6,
        margin_start=6,
        margin_end=6,
    )
    box.append(art)
    box.append(label)

    tile = Gtk.Button(child=box, halign=Gtk.Align.CENTER, valign=Gtk.Align.START)
    tile.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
    tile.add_css_class("flat")
    tile.add_css_class("card-bg")
    tile.add_css_class("console-more-tile")
    tile._ht_console_target = True
    tile.connect("clicked", lambda *_: on_click())
    scale_widget_sizes(tile)
    return tile


def new_more_row() -> Gtk.ListBoxRow:
    """A "More" row for the end of a song list.

    The list's row-activated handler opens the full list; the row's name is
    "more" so it can tell this row apart from songs.
    """
    box = Gtk.Box(spacing=12, margin_top=12, margin_bottom=12, margin_start=12)
    box.append(Gtk.Image(icon_name="go-next-symbolic"))
    label = Gtk.Label(label=_("More"), xalign=0)
    label.add_css_class("heading")
    box.append(label)

    row = Gtk.ListBoxRow(child=box, selectable=False)
    row.set_name("more")
    row.add_css_class("console-more-row")
    row._ht_console_target = True
    return row
