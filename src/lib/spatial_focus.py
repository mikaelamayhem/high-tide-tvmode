# spatial_focus.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Move focus to the nearest widget on screen in a direction (TV style).

GTK's own arrow key focus follows the widget tree, which can skip over
lists or step into buttons inside a row. For a controller we want what
you see: pressing down goes to whatever is right below.
"""

from gi.repository import Adw, Graphene, Gtk

_DOWN = Gtk.DirectionType.DOWN
_UP = Gtk.DirectionType.UP
_LEFT = Gtk.DirectionType.LEFT
_RIGHT = Gtk.DirectionType.RIGHT

# How much a sideways offset counts against a candidate, compared with
# distance in the direction of travel
_SIDEWAYS_WEIGHT = 2.0


# Lists themselves can take focus, but their rows are what we want
_LIST_TYPES = (Gtk.ListBox, Gtk.FlowBox, Gtk.ListView, Gtk.GridView)


def _is_candidate(widget: Gtk.Widget) -> bool:
    return (
        not isinstance(widget, _LIST_TYPES)
        and widget.get_focusable()
        and widget.get_can_focus()
        and widget.is_sensitive()
        and widget.get_mapped()
        and widget.get_width() > 0
        and widget.get_height() > 0
    )


def _search_root(window: Gtk.Window, focus: Gtk.Widget | None) -> Gtk.Widget:
    """Stay inside an open popover or dialog."""
    widget = focus
    while widget is not None:
        if isinstance(widget, (Adw.Dialog, Gtk.Popover)):
            return widget
        widget = widget.get_parent()
    # A dialog may be open while focus is still behind it
    get_visible_dialog = getattr(window, "get_visible_dialog", None)
    dialog = get_visible_dialog() if get_visible_dialog else None
    return dialog if dialog is not None else window


def _candidates(root: Gtk.Widget) -> list[Gtk.Widget]:
    found = []
    stack = [root]
    while stack:
        widget = stack.pop()
        if not widget.get_mapped():
            continue
        if widget is not root and isinstance(widget, Gtk.Popover):
            continue
        if widget is not root and _is_candidate(widget):
            found.append(widget)
        child = widget.get_first_child()
        while child is not None:
            stack.append(child)
            child = child.get_next_sibling()
    return found


def _bounds(widget: Gtk.Widget, root: Gtk.Widget) -> Graphene.Rect | None:
    ok, rect = widget.compute_bounds(root)
    return rect if ok else None


def _score(current, candidate, direction) -> float | None:
    """Lower is better; None if the candidate isn't in that direction."""
    cx, cy = current.get_x(), current.get_y()
    cw, ch = current.get_width(), current.get_height()
    x, y, w, h = candidate.get_x(), candidate.get_y(), candidate.get_width(), candidate.get_height()

    if direction in (_UP, _DOWN):
        if direction == _DOWN:
            ahead = y - (cy + ch)
            if y + h / 2 <= cy + ch / 2 + 1:
                return None
        else:
            ahead = cy - (y + h)
            if y + h / 2 >= cy + ch / 2 - 1:
                return None
        sideways = max(0.0, max(cx, x) - min(cx + cw, x + w))
        if sideways == 0:
            # Overlapping: prefer the one lined up with the current one's
            # left edge, so going down from a wide row lands on the first
            # card of a row of cards
            sideways = abs(x - cx) * 0.1
    else:
        if direction == _RIGHT:
            ahead = x - (cx + cw)
            if x + w / 2 <= cx + cw / 2 + 1:
                return None
        else:
            ahead = cx - (x + w)
            if x + w / 2 >= cx + cw / 2 - 1:
                return None
        sideways = max(0.0, max(cy, y) - min(cy + ch, y + h))
        if sideways == 0:
            sideways = abs(y - cy) * 0.1

    return max(0.0, ahead) + sideways * _SIDEWAYS_WEIGHT


# True while the controller is moving focus, so passing over a text box
# doesn't pop up the on-screen keyboard
moving = False


def move_focus(window: Gtk.Window, direction: Gtk.DirectionType) -> bool:
    """Focus the nearest widget in a direction. Returns True if focus moved."""
    global moving
    moving = True
    try:
        return _move_focus(window, direction)
    finally:
        moving = False


def _move_focus(window: Gtk.Window, direction: Gtk.DirectionType) -> bool:
    focus = window.get_focus()
    if focus is None:
        return window.child_focus(Gtk.DirectionType.TAB_FORWARD)

    # Moving up or down from a button inside a list row moves by whole rows
    if direction in (_UP, _DOWN):
        row = focus
        while row is not None and not isinstance(
            row, (Gtk.ListBoxRow, Gtk.FlowBoxChild)
        ):
            row = row.get_parent()
        if row is not None and _is_candidate(row):
            focus = row

    root = _search_root(window, focus)
    if root is not window and not focus.is_ancestor(root):
        # Focus is behind an open dialog: jump into the dialog
        return root.child_focus(Gtk.DirectionType.TAB_FORWARD)
    current = _bounds(focus, root)
    if current is None:
        return window.child_focus(direction)

    best = None
    best_score = None
    for candidate in _candidates(root):
        if candidate is focus:
            continue
        # Skip containers of the focused widget (e.g. its own row)
        if focus.is_ancestor(candidate):
            continue
        rect = _bounds(candidate, root)
        if rect is None:
            continue
        score = _score(current, rect, direction)
        if score is not None and (best_score is None or score < best_score):
            best, best_score = candidate, score

    if best is None:
        return False
    return best.grab_focus()
