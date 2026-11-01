# console_background.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A blurred, enlarged copy of the album art behind the whole app."""

from gi.repository import Adw, Gdk, Graphene, Gtk

BLUR_RADIUS = 80
# How much darker to make the art, so text stays readable
DIM = Gdk.RGBA(red=0, green=0, blue=0, alpha=0.5)
FADE_MS = 900


class ConsoleBackground(Gtk.Widget):
    """Draws album art blurred to fill the widget, fading between songs."""

    __gtype_name__ = "HTConsoleBackground"

    def __init__(self) -> None:
        super().__init__(hexpand=True, vexpand=True, can_target=False)
        self._paintable: Gdk.Paintable | None = None
        self._handler: int | None = None
        # The art we're fading away from, frozen as a still image
        self._previous: Gdk.Paintable | None = None
        self._progress = 1.0

        self._fade = Adw.TimedAnimation.new(
            self,
            0.0,
            1.0,
            FADE_MS,
            Adw.CallbackAnimationTarget.new(self._on_fade_step),
        )
        self._fade.set_easing(Adw.Easing.EASE_IN_OUT_CUBIC)
        self._fade.connect("done", self._on_fade_done)

    def set_paintable(self, paintable: Gdk.Paintable | None) -> None:
        if paintable is self._paintable:
            return

        if self._paintable is not None:
            if self._handler is not None:
                self._paintable.disconnect(self._handler)
                self._handler = None
            # Freeze the old art (it may be an animated cover) to fade it out
            self._previous = self._paintable.get_current_image()

        self._paintable = paintable
        if paintable is not None:
            # Animated covers redraw when their frame changes
            self._handler = paintable.connect(
                "invalidate-contents", lambda *_: self.queue_draw()
            )

        # Fade in, from the old art or from plain dark on first show
        self._fade.reset()
        self._fade.play()

    def _on_fade_step(self, value: float) -> None:
        self._progress = value
        self.queue_draw()

    def _on_fade_done(self, *args) -> None:
        self._previous = None
        self._progress = 1.0
        self.queue_draw()

    def _draw_art(self, snapshot, paintable, width, height, opacity) -> None:
        art_width = paintable.get_intrinsic_width()
        art_height = paintable.get_intrinsic_height()
        if art_width <= 0 or art_height <= 0 or opacity <= 0:
            return
        # Cover the whole area, a bit larger so blurred edges stay hidden
        scale = max(width / art_width, height / art_height) * 1.2
        draw_width, draw_height = art_width * scale, art_height * scale
        snapshot.push_opacity(opacity)
        snapshot.push_blur(BLUR_RADIUS)
        snapshot.save()
        snapshot.translate(
            Graphene.Point().init((width - draw_width) / 2, (height - draw_height) / 2)
        )
        paintable.snapshot(snapshot, draw_width, draw_height)
        snapshot.restore()
        snapshot.pop()
        snapshot.pop()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width, height = self.get_width(), self.get_height()
        if width <= 0 or height <= 0:
            return
        area = Graphene.Rect().init(0, 0, width, height)
        snapshot.push_clip(area)

        if self._previous is not None:
            self._draw_art(snapshot, self._previous, width, height, 1.0)
        if self._paintable is not None:
            self._draw_art(snapshot, self._paintable, width, height, self._progress)

        snapshot.append_color(DIM, area)
        snapshot.pop()
