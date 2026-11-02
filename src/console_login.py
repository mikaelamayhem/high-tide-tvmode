# console_login.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Console mode sign-in: scan a QR code and finish on your phone."""

import io
import logging
from gettext import gettext as _
from typing import Any

import tidalapi
from gi.repository import Adw, Gdk, GLib, Gtk

from .lib.phone_login import PhoneLoginServer
from .login import LoginDialog

try:
    import segno
except ImportError:
    segno = None

logger = logging.getLogger(__name__)

QR_SIZE = 300


def qr_texture(text: str) -> Gdk.Texture | None:
    """A QR code image for a piece of text, or None without segno."""
    if segno is None:
        return None
    buffer = io.BytesIO()
    segno.make(text, error="m").save(buffer, kind="png", scale=12, border=3)
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(buffer.getvalue()))


class ConsoleLoginDialog(Adw.Dialog):
    """Sign in by scanning a QR code with a phone on the same network."""

    __gtype_name__ = "HTConsoleLoginDialog"

    def __init__(self, win: Any, session: tidalapi.Session, scale: float = 1.0):
        super().__init__(title=_("Sign In"), content_width=640)
        self.win = win
        self.session = session

        self.server = PhoneLoginServer(session.pkce_login_url(), self._finish_login)
        phone_url = self.server.start()
        texture = qr_texture(phone_url) if phone_url else None

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            margin_top=12,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
            halign=Gtk.Align.CENTER,
        )

        if texture is not None:
            title = Gtk.Label(
                label=_("Scan with your phone to sign in"),
                wrap=True,
                justify=2,
                max_width_chars=40,
            )
            title.add_css_class("title-2")
            box.append(title)

            qr_frame = Gtk.Picture(
                paintable=texture, can_shrink=True, content_fit=Gtk.ContentFit.CONTAIN
            )
            size = round(QR_SIZE * scale)
            qr_frame.set_size_request(size, size)
            qr_frame.set_halign(Gtk.Align.CENTER)
            qr_frame.add_css_class("console-qr")
            box.append(qr_frame)

            hint = Gtk.Label(
                label=_(
                    "Your phone needs to be on the same Wi-Fi as this device. "
                    "Or open this address on any phone or computer:"
                ),
                wrap=True,
                justify=2,
                max_width_chars=50,
            )
            hint.add_css_class("dim-label")
            box.append(hint)

            # Not selectable, so the controller lands on the button, not the text
            address = Gtk.Label(label=phone_url, wrap=True)
            address.add_css_class("monospace")
            box.append(address)
        else:
            sorry = Gtk.Label(
                label=_(
                    "Phone sign-in isn't available here, because this device "
                    "isn't connected to a local network."
                ),
                wrap=True,
                justify=2,
                max_width_chars=50,
            )
            box.append(sorry)

        self.status = Gtk.Label(wrap=True, justify=2, visible=False)
        box.append(self.status)

        other_way = Gtk.Button(label=_("Sign in on this screen instead"))
        other_way.add_css_class("pill")
        other_way.set_halign(Gtk.Align.CENTER)
        other_way.connect("clicked", self._on_other_way)
        box.append(other_way)
        self.set_focus(other_way)

        toolbar = Adw.ToolbarView(content=box)
        toolbar.add_top_bar(Adw.HeaderBar())
        self.set_child(toolbar)

        self.connect("closed", lambda *_: self.server.stop())

    def _finish_login(self, redirect_url: str) -> str | None:
        """Runs on the phone page's thread. None means success."""
        GLib.idle_add(self._show_status, _("Signing in…"), False)
        try:
            token_json = self.session.pkce_get_auth_token(redirect_url)
            self.session.process_auth_token(token_json, is_pkce_token=True)
        except Exception as error:
            logger.exception("Phone sign-in failed")
            GLib.idle_add(self._show_status, _("Sign-in failed, try again"), True)
            return str(error) or _("Tidal didn't accept that address")

        if not self.session.check_login():
            GLib.idle_add(self._show_status, _("Sign-in failed, try again"), True)
            return _("Tidal rejected the sign-in")

        GLib.idle_add(self._on_success)
        return None

    def _show_status(self, text: str, is_error: bool) -> bool:
        self.status.set_label(text)
        self.status.set_visible(True)
        if is_error:
            self.status.add_css_class("error")
        else:
            self.status.remove_css_class("error")
        return GLib.SOURCE_REMOVE

    def _on_success(self) -> bool:
        self.win.secret_store.save(is_pkce=True)
        self.win.on_logged_in()
        self.close()
        return GLib.SOURCE_REMOVE

    def _on_other_way(self, *args) -> None:
        self.close()
        LoginDialog(self.win, self.session).present(self.win)
