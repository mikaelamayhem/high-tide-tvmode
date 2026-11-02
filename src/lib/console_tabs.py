# console_tabs.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Home / Discover / Queue / Lyrics tabs at the top of console mode."""

from gettext import gettext as _
from typing import Callable

from gi.repository import Adw, Gtk

# (tag, label, icon)
CONSOLE_TABS = (
    ("home", _("Home"), "user-home-symbolic"),
    ("discover", _("Discover"), "explore2-large-symbolic"),
    ("queue", _("Queue"), "view-list-ordered-symbolic"),
    ("lyrics", _("Lyrics"), "chat-bubble-text-symbolic"),
)
CONSOLE_TAB_TAGS = tuple(tag for tag, _label, _icon in CONSOLE_TABS)


class ConsoleTabBar(Gtk.Box):
    """A row of tabs with the LB and RB icons on either side."""

    def __init__(self, glyphs, on_select: Callable[[str], None]) -> None:
        super().__init__(spacing=12, halign=Gtk.Align.CENTER, margin_top=8)
        self.add_css_class("console-tabs")
        self._buttons: dict[str, Gtk.ToggleButton] = {}

        self.append(glyphs.new_icon("lb"))
        group = None
        for tag, label, icon in CONSOLE_TABS:
            content = Adw.ButtonContent(label=label, icon_name=icon)
            button = Gtk.ToggleButton(child=content, focusable=False)
            button.add_css_class("flat")
            button.add_css_class("console-tab")
            if group is None:
                group = button
            else:
                button.set_group(group)
            button.connect(
                "clicked", lambda _b, tag=tag: on_select(tag)
            )
            self._buttons[tag] = button
            self.append(button)
        self.append(glyphs.new_icon("rb"))

    def set_current(self, tag: str) -> None:
        button = self._buttons.get(tag)
        if button is not None and not button.get_active():
            button.set_active(True)


class ConsolePanelPage(Adw.NavigationPage):
    """A page that holds the Queue or Lyrics panel in console mode."""

    __gtype_name__ = "HTConsolePanelPage"

    def __init__(self, tag: str, title: str) -> None:
        super().__init__(tag=tag, title=title)

    def disconnect_all(self) -> None:
        # Kept and reused between visits, so nothing to clean up
        pass
