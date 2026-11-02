# console_fixed_layout.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Draw the console layout at one fixed size and scale it to the window.

Games lay out their HUD for one reference screen and stretch it to any
resolution, so it looks identical at 720p and 4K. This does the same:
the window content is laid out on a 2560x1440 canvas, then drawn scaled
to the real size. GTK maps mouse clicks and focus through the same
scaling. If the window isn't 16:9, the canvas grows in the other
direction instead of shrinking the layout, so nothing gets smaller.
"""

from gi.repository import Graphene, Gsk, Gtk

# The window size the console layout is designed at (1440p)
REFERENCE_WIDTH = 2560
REFERENCE_HEIGHT = 1440


def _scale_for(width: int, height: int) -> float:
    """Fit the reference canvas inside the window (like a game would)."""
    if width <= 0 or height <= 0:
        return 1.0
    return min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT)


class FixedLayoutBin(Gtk.Widget):
    """Holds one child and scales it to fit, while enabled."""

    __gtype_name__ = "HTFixedLayoutBin"

    def __init__(self, child: Gtk.Widget) -> None:
        super().__init__()
        self._enabled = False
        self._child = child
        child.set_parent(self)

    def set_enabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self._enabled = enabled
            self.queue_resize()

    def get_scale(self) -> float:
        """How much the layout is currently scaled by (1.0 when off)."""
        if not self._enabled:
            return 1.0
        return _scale_for(self.get_width(), self.get_height())

    def do_measure(self, orientation, for_size):
        if self._enabled:
            # The window can be any size; the content is scaled to fit
            return 0, 0, -1, -1
        return self._child.measure(orientation, for_size)

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        if not self._enabled or height <= 0 or width <= 0:
            self._child.allocate(width, height, baseline, None)
            return

        scale = _scale_for(width, height)
        child_width = round(width / scale)
        child_height = round(height / scale)
        # Never squeeze the content below its minimum (e.g. a very narrow
        # window); it is clipped instead
        min_width, _nat, _b1, _b2 = self._child.measure(
            Gtk.Orientation.HORIZONTAL, -1
        )
        min_height, _nat, _b1, _b2 = self._child.measure(
            Gtk.Orientation.VERTICAL, max(child_width, min_width)
        )
        child_width = max(child_width, min_width)
        child_height = max(child_height, min_height)

        transform = Gsk.Transform.new().scale(scale, scale)
        self._child.allocate(child_width, child_height, -1, transform)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if self._enabled:
            snapshot.push_clip(
                Graphene.Rect().init(0, 0, self.get_width(), self.get_height())
            )
            self.snapshot_child(self._child, snapshot)
            snapshot.pop()
        else:
            self.snapshot_child(self._child, snapshot)

    def do_dispose(self) -> None:
        if self._child is not None:
            self._child.unparent()
            self._child = None
