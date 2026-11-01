# generic_page.py
#
# Copyright 2023 Nokse
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gettext import gettext as _

from gi.repository import Gtk

from tidalapi.media import Track
from tidalapi.page import (
    HorizontalList,
    HorizontalListWithContext,
    ItemList,
    PageLinks,
    ShortcutList,
    TextBlock,
    TrackList,
)

from ..lib import utils
from ..widgets import HTShorcutsWidget
from .page import Page


class HTGenericPage(Page):
    """A generic page that can display any TIDAL API page content.

    This page dynamically renders content from TIDAL API page objects,
    automatically creating appropriate widgets based on the content type
    (tracks, carousels, shortcuts, etc.). It's used for displaying various
    TIDAL pages like home, explore, genres, and search results.
    """

    __gtype_name__ = "HTGenericPage"

    function = None
    page = None

    @classmethod
    def new_from_function(cls, function) -> "HTGenericPage":
        """Create a new generic page instance from a function that returns page data.

        This is useful for dynamic pages such as the home page, explore page,
        genres, or search results. The provided function is called to fetch
        the page content when the page is loaded.

        Args:
            function: A callable that returns a TIDAL API page object when called

        Returns:
            HTGenericPage: A new instance configured with the provided function
        """
        instance = cls()

        instance.function = function

        return instance

    def _load_async(self) -> None:
        self.page = self.function()

    def _load_finish(self) -> None:
        self.set_title(self.page.title or "")

        if getattr(self, "console_home", False):
            self._add_console_home_sections()

        for category in self.page.categories:
            items = [
                item for item in getattr(category, "items", []) if item is not None
            ]

            if isinstance(category, TrackList) or all(
                isinstance(item, Track) for item in items
            ):
                self.new_track_list_for(category.title, items)

            elif isinstance(category, TextBlock):
                self.append(
                    Gtk.Label(
                        justify=0,
                        xalign=0,
                        wrap=True,
                        margin_start=12,
                        margin_top=12,
                        margin_bottom=12,
                        margin_end=12,
                        label=category.text,
                    )
                )

            elif isinstance(category, PageLinks):
                self.new_link_carousel_for(category.title or _("More"), items)

            elif isinstance(category, ShortcutList):
                self.append(HTShorcutsWidget(items))

            elif isinstance(
                category, (ItemList, HorizontalList, HorizontalListWithContext)
            ):
                self.new_carousel_for(category.title, items)

    # How many liked songs to show on the console home page before "More"
    CONSOLE_LIKED_SONGS_SHOWN = 10

    def _add_console_home_sections(self) -> None:
        """Console mode home: Liked Songs, then your playlists, at the top."""

        def all_liked_songs(limit=50, offset=0):
            return utils.favourite_tracks[offset : offset + limit]

        self.new_track_list_for(
            _("Liked Songs"),
            utils.favourite_tracks[: self.CONSOLE_LIKED_SONGS_SHOWN],
            more_function=all_liked_songs,
        )
        self.new_carousel_for(
            _("Your Playlists"), utils.playlist_and_favorite_playlists
        )
