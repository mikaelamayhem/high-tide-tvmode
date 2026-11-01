# console_background.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A blurred, enlarged copy of the album art behind the whole app."""

from gi.repository import Gdk, Graphene, Gtk

BLUR_RADIUS = 80
# How much darker to make the art, so text stays readable
DIM = Gdk.RGBA(red=0, green=0, blue=0, alpha=0.5)


class ConsoleBackground(Gtk.Widget):
    """Draws a paintable blurred to fill the widget, like a TV music app."""

    __gtype_name__ = "HTConsoleBackground"

    def __init__(self) -> None:
        super().__init__(hexpand=True, vexpand=True, can_target=False)
        self._paintable: Gdk.Paintable | None = None
        self._handler: int | None = None

    def set_paintable(self, paintable: Gdk.Paintable | None) -> None:
        if self._paintable is not None and self._handler is not None:
            self._paintable.disconnect(self._handler)
            self._handler = None
        self._paintable = paintable
        if paintable is not None:
            # Animated covers redraw when their frame changes
            self._handler = paintable.connect(
                "invalidate-contents", lambda *_: self.queue_draw()
            )
        self.queue_draw()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width, height = self.get_width(), self.get_height()
        if width <= 0 or height <= 0:
            return
        area = Graphene.Rect().init(0, 0, width, height)
        snapshot.push_clip(area)

        paintable = self._paintable
        art_width = paintable.get_intrinsic_width() if paintable else 0
        art_height = paintable.get_intrinsic_height() if paintable else 0
        if art_width > 0 and art_height > 0:
            # Cover the whole area, a bit larger so blurred edges stay hidden
            scale = max(width / art_width, height / art_height) * 1.2
            draw_width, draw_height = art_width * scale, art_height * scale
            snapshot.push_blur(BLUR_RADIUS)
            snapshot.save()
            snapshot.translate(
                Graphene.Point().init(
                    (width - draw_width) / 2, (height - draw_height) / 2
                )
            )
            paintable.snapshot(snapshot, draw_width, draw_height)
            snapshot.restore()
            snapshot.pop()

        snapshot.append_color(DIM, area)
        snapshot.pop()
