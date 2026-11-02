# spatial_focus.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Move focus to the nearest widget on screen in a direction (TV style).

GTK's own arrow key focus follows the widget tree, which can skip over
lists or step into buttons inside a row. For a controller we want what
you see: pressing down goes to whatever is right below.
"""

from gi.repository import Adw, Graphene, Gtk

# How far from the edge the selected item stays when scrolling to it
_SCROLL_MARGIN = 48
_SCROLL_DURATION_MS = 220

_DOWN = Gtk.DirectionType.DOWN
_UP = Gtk.DirectionType.UP
_LEFT = Gtk.DirectionType.LEFT
_RIGHT = Gtk.DirectionType.RIGHT

# How much a sideways offset counts against a candidate, compared with
# distance in the direction of travel
_SIDEWAYS_WEIGHT = 2.0


# Lists themselves can take focus, but their rows are what we want
_LIST_TYPES = (Gtk.ListBox, Gtk.FlowBox, Gtk.ListView, Gtk.GridView)


def is_target(widget: Gtk.Widget) -> bool:
    """Whether the D-pad may land on a widget in the main window.

    Only songs, albums (and other cards), "More" and the player buttons
    set _ht_console_target. Dialogs and popovers allow everything.
    """
    return bool(getattr(widget, "_ht_console_target", False))


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


def _candidates(
    root: Gtk.Widget, skip: tuple = (), targets_only: bool | None = None
) -> list[Gtk.Widget]:
    # In the main window only the chosen kinds of widget count; in a
    # dialog or popover anything focusable does
    if targets_only is None:
        targets_only = isinstance(root, Gtk.Window)
    found = []
    stack = [root]
    while stack:
        widget = stack.pop()
        if not widget.get_mapped() or widget in skip:
            continue
        if widget is not root and isinstance(widget, Gtk.Popover):
            continue
        if (
            widget is not root
            and _is_candidate(widget)
            and (not targets_only or is_target(widget))
        ):
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


def _is_inside(widget: Gtk.Widget, areas: tuple) -> bool:
    return any(widget is area or widget.is_ancestor(area) for area in areas)


def focus_first(window: Gtk.Window, within: Gtk.Widget) -> bool:
    """Select the top-left song, card or button inside part of the window."""
    window.set_focus_visible(True)
    return _first_candidate(within, (), targets_only=True)


def _first_candidate(
    root: Gtk.Widget, skip: tuple, targets_only: bool | None = None
) -> bool:
    """Focus the top-left widget, for when there's no current selection."""
    best = None
    best_key = None
    for candidate in _candidates(root, skip, targets_only):
        rect = _bounds(candidate, root)
        if rect is None:
            continue
        key = (round(rect.get_y()), rect.get_x())
        if best_key is None or key < best_key:
            best, best_key = candidate, key
    return _focus(best) if best is not None else False


def _target_of(widget: Gtk.Widget | None) -> Gtk.Widget | None:
    """The selectable item a widget belongs to (itself or an ancestor)."""
    while widget is not None:
        if is_target(widget):
            return widget
        widget = widget.get_parent()
    return None


def _focus(widget: Gtk.Widget) -> bool:
    """Focus a widget and smoothly scroll it into view."""
    viewports = []
    parent = widget.get_parent()
    while parent is not None:
        if isinstance(parent, Gtk.Viewport):
            # We scroll ourselves, with an animation
            parent.set_scroll_to_focus(False)
            viewports.append(parent)
        parent = parent.get_parent()
    focused = widget.grab_focus()
    for viewport in viewports:
        scroll_into_view(widget, viewport.get_parent())
    return focused


def scroll_into_view(widget: Gtk.Widget, scrolled: Gtk.Widget | None) -> None:
    """Animate a scrolled window so a widget inside it is fully visible."""
    if not isinstance(scrolled, Gtk.ScrolledWindow):
        return
    ok, rect = widget.compute_bounds(scrolled)
    if not ok:
        return
    for adjustment, start, size in (
        (scrolled.get_vadjustment(), rect.get_y(), rect.get_height()),
        (scrolled.get_hadjustment(), rect.get_x(), rect.get_width()),
    ):
        page = adjustment.get_page_size()
        if page <= 0 or adjustment.get_upper() - adjustment.get_lower() <= page:
            continue
        margin = min(_SCROLL_MARGIN, max(0.0, (page - size) / 2))
        if start < margin:
            delta = start - margin
        elif start + size > page - margin:
            delta = start + size - (page - margin)
        else:
            continue
        # Aim from where a running animation is heading, not where it is
        current = getattr(adjustment, "_ht_scroll_to", None)
        if current is None:
            current = adjustment.get_value()
        target = min(
            adjustment.get_upper() - page,
            max(adjustment.get_lower(), current + delta),
        )
        _animate(scrolled, adjustment, target)


def _animate(scrolled: Gtk.ScrolledWindow, adjustment, target: float) -> None:
    previous = getattr(adjustment, "_ht_scroll_animation", None)
    if previous is not None:
        previous.pause()
    animation = Adw.TimedAnimation.new(
        scrolled,
        adjustment.get_value(),
        target,
        _SCROLL_DURATION_MS,
        Adw.CallbackAnimationTarget.new(adjustment.set_value),
    )
    animation.set_easing(Adw.Easing.EASE_OUT_CUBIC)

    def done(*_args):
        if getattr(adjustment, "_ht_scroll_animation", None) is animation:
            adjustment._ht_scroll_animation = None
            adjustment._ht_scroll_to = None

    animation.connect("done", done)
    adjustment._ht_scroll_animation = animation
    adjustment._ht_scroll_to = target
    animation.play()


def find_vertical_scroller(root: Gtk.Widget | None) -> Gtk.ScrolledWindow | None:
    """The first scrolled window under a widget that scrolls up and down."""
    stack = [root] if root is not None else []
    while stack:
        widget = stack.pop(0)
        if isinstance(widget, Gtk.ScrolledWindow) and widget.get_mapped():
            adjustment = widget.get_vadjustment()
            if adjustment.get_upper() - adjustment.get_lower() > adjustment.get_page_size():
                return widget
        child = widget.get_first_child()
        while child is not None:
            stack.append(child)
            child = child.get_next_sibling()
    return None


def _move_focus(window: Gtk.Window, direction: Gtk.DirectionType) -> bool:
    # Areas the D-pad never enters (e.g. the player sidebar, which has its
    # own buttons). Set by the window as console_focus_skip.
    skip = tuple(getattr(window, "console_focus_skip", ()))

    focus = window.get_focus()
    if focus is None or _is_inside(focus, skip):
        return _first_candidate(_search_root(window, None), skip)

    root = _search_root(window, focus)
    if isinstance(root, Gtk.Window):
        # Measure from the song or card that holds the focus (e.g. focus
        # may be on a link inside a card after a mouse click)
        target = _target_of(focus)
        if target is None and not isinstance(focus, (Gtk.Text, Gtk.Editable)):
            # Focus is somewhere the D-pad can't go (e.g. after a page
            # change): start again from the top item
            return _first_candidate(root, skip)
        focus = target or focus

    # Moving up or down from a button inside a list row moves by whole rows
    if direction in (_UP, _DOWN):
        row = focus
        while row is not None and not isinstance(
            row, (Gtk.ListBoxRow, Gtk.FlowBoxChild)
        ):
            row = row.get_parent()
        if row is not None and _is_candidate(row):
            focus = row

    if root is not window and not focus.is_ancestor(root):
        # Focus is behind an open dialog: jump into the dialog
        return root.child_focus(Gtk.DirectionType.TAB_FORWARD)
    current = _bounds(focus, root)
    if current is None:
        return window.child_focus(direction)

    best = None
    best_score = None
    for candidate in _candidates(root, skip):
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
    return _focus(best)
