# console_slide.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A sideways slide between console tabs (LB/RB).

The tab pages live in an Adw.NavigationView, whose push and pop animations
overlap pages in ways that look random when hopping between tabs. Instead
the switch happens without animation, and this overlay draws the old page
sliding out while the new one slides in.
"""

from gi.repository import Adw, GLib, Graphene, Gtk

DURATION_MS = 260


class ConsoleTabSlide(Gtk.Widget):
    """Sits over the window and draws the slide while it runs."""

    __gtype_name__ = "HTConsoleTabSlide"

    def __init__(self) -> None:
        super().__init__(can_target=False)
        self._ht_console_scaled = True
        self._old_image = None
        self._new_page = None
        self._area: Gtk.Widget | None = None
        self._direction = 1
        self._progress = 1.0
        self._animation = None
        self._tick_id: int | None = None
        self._frames = 0

    def switch(self, area: Gtk.Widget, page_of, do_switch, direction: int) -> None:
        """Run do_switch() and slide from the old page to the new one.

        Args:
            area: the widget the pages are shown in (the NavigationView)
            page_of: returns the page currently shown in the area
            do_switch: changes the page, without its own animation
            direction: 1 slides the new page in from the right, -1 from the left
        """
        old_page = page_of()
        if old_page is None or not self.get_mapped() or not area.get_mapped():
            do_switch()
            return

        self._finish()
        self._old_image = Gtk.WidgetPaintable(widget=old_page).get_current_image()
        do_switch()
        new_page = page_of()
        if new_page is None or new_page is old_page:
            self._old_image = None
            return

        # The pages are drawn here while sliding. GTK only draws (and so
        # lets us copy) a page that is shown, so show the new one at 1% for
        # two frames, copy it, then hide it while the copies slide
        self._area = area
        self._direction = direction
        self._progress = 0.0
        self._frames = 0
        area.set_opacity(0.01)
        self._tick_id = area.add_tick_callback(self._on_tick, new_page)
        self.queue_draw()

    def _on_tick(self, area, clock, new_page) -> bool:
        self._frames += 1
        if self._frames < 2:
            return GLib.SOURCE_CONTINUE
        self._tick_id = None
        if self._area is None:
            return GLib.SOURCE_REMOVE
        self._new_page = Gtk.WidgetPaintable(widget=new_page).get_current_image()
        area.set_opacity(0.0)

        self._animation = Adw.TimedAnimation.new(
            self, 0.0, 1.0, DURATION_MS,
            Adw.CallbackAnimationTarget.new(self._set_progress),
        )
        self._animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)
        self._animation.connect("done", lambda *_: self._finish())
        self._animation.play()
        return GLib.SOURCE_REMOVE

    def _set_progress(self, value: float) -> None:
        self._progress = value
        self.queue_draw()

    def _finish(self) -> None:
        animation, self._animation = self._animation, None
        if animation is not None and animation.get_state() == Adw.AnimationState.PLAYING:
            animation.skip()
        if self._area is not None and self._tick_id is not None:
            self._area.remove_tick_callback(self._tick_id)
        self._tick_id = None
        if self._area is not None:
            self._area.set_opacity(1.0)
        self._area = None
        self._old_image = None
        self._new_page = None
        self._progress = 1.0
        self.queue_draw()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if self._area is None:
            return
        ok, rect = self._area.compute_bounds(self)
        if not ok:
            return
        x, y = rect.get_x(), rect.get_y()
        width, height = rect.get_width(), rect.get_height()
        shift = width * self._progress * self._direction

        snapshot.push_clip(rect)
        if self._old_image is not None:
            snapshot.save()
            snapshot.translate(Graphene.Point().init(x - shift, y))
            self._old_image.snapshot(snapshot, width, height)
            snapshot.restore()
        if self._new_page is not None:
            snapshot.save()
            snapshot.translate(
                Graphene.Point().init(x - shift + width * self._direction, y)
            )
            self._new_page.snapshot(snapshot, width, height)
            snapshot.restore()
        snapshot.pop()
