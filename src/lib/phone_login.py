# phone_login.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Sign in to Tidal from a phone, for console mode.

The TV shows a QR code. It opens a small page served by High Tide on the
local network. That page sends the phone to Tidal's normal sign-in, then
takes back the address Tidal ends on and finishes the sign-in here. This
keeps the same sign-in method as the desktop (needed for lossless and
Hi-Res streams), without typing anything on the TV.
"""

import html
import logging
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>High Tide sign in</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1e1e22; color: #f2f2f2;
         margin: 0; padding: 24px; line-height: 1.45; }}
  main {{ max-width: 480px; margin: 0 auto; }}
  h1 {{ font-size: 1.5em; }}
  .step {{ background: #2c2c32; border-radius: 16px; padding: 16px 18px; margin: 16px 0; }}
  .num {{ color: #78aeed; font-weight: bold; }}
  a.button, button {{ display: block; text-align: center; background: #3584e4; color: #fff;
         border: 0; border-radius: 999px; padding: 14px; font-size: 1.05em;
         font-weight: bold; text-decoration: none; width: 100%; margin-top: 10px; }}
  textarea {{ width: 100%; box-sizing: border-box; min-height: 90px; border-radius: 12px;
         border: 1px solid #555; background: #18181b; color: #f2f2f2; padding: 10px;
         font-size: 1em; margin-top: 10px; }}
  .msg {{ padding: 14px 18px; border-radius: 16px; }}
  .ok {{ background: #26a269; }}
  .err {{ background: #c01c28; }}
</style></head>
<body><main>
<h1>Sign in to High Tide</h1>
{message}
<div class="step"><span class="num">1.</span> Sign in to your Tidal account.
  <a class="button" href="{login_url}" target="_blank" rel="noopener">Open Tidal sign-in</a>
</div>
<div class="step"><span class="num">2.</span> After signing in you'll land on a
  "Page not found" page. That's expected. Copy that page's full address, come back
  to this tab and paste it here.
  <form method="post" action="{path}">
    <textarea name="url" placeholder="https://tidal.com/android/login/auth?code=..."
      required></textarea>
    <button type="submit">Finish sign-in</button>
  </form>
</div>
</main></body></html>
"""


def local_ip_address() -> str | None:
    """The address other devices on the network can reach us at."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Nothing is sent; this only picks the outgoing network interface
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
    except OSError:
        return None


class PhoneLoginServer:
    """A tiny web page on the local network that finishes Tidal sign-in.

    Args:
        login_url: Tidal's sign-in address for this session
        finish: called (on the server thread) with the address the phone
            ended on; returns None on success or an error message
    """

    def __init__(self, login_url: str, finish: Callable[[str], str | None]) -> None:
        self._login_url = login_url
        self._finish = finish
        # A secret path, so other devices on the network can't use the page
        self._path = "/" + secrets.token_urlsafe(9)
        self._server: ThreadingHTTPServer | None = None
        self.url: str | None = None

    def start(self) -> str | None:
        """Start serving. Returns the address for the QR code, or None."""
        address = local_ip_address()
        if address is None:
            return None
        handler = self._make_handler()
        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", 0), handler)
        except OSError:
            logger.exception("Could not start the phone sign-in page")
            return None
        port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://{address}:{port}{self._path}"
        return self.url

    def stop(self) -> None:
        if self._server is not None:
            server, self._server = self._server, None
            threading.Thread(target=server.shutdown, daemon=True).start()

    def _render(self, message: str = "") -> bytes:
        return _PAGE.format(
            message=message,
            login_url=html.escape(self._login_url, quote=True),
            path=html.escape(self._path, quote=True),
        ).encode()

    def _make_handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status: int, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path != owner._path:
                    self._send(404, b"Not found")
                    return
                self._send(200, owner._render())

            def do_POST(self):
                if self.path != owner._path:
                    self._send(404, b"Not found")
                    return
                length = min(int(self.headers.get("Content-Length") or 0), 16384)
                form = parse_qs(self.rfile.read(length).decode(errors="replace"))
                redirect_url = (form.get("url") or [""])[0].strip()

                error = owner._finish(redirect_url) if redirect_url else (
                    "Paste the address first."
                )
                if error is None:
                    body = (
                        '<!doctype html><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width, '
                        'initial-scale=1"><body style="font-family:system-ui;'
                        'background:#1e1e22;color:#f2f2f2;padding:24px">'
                        '<p class="msg" style="background:#26a269;padding:14px 18px;'
                        'border-radius:16px">You\'re signed in. You can put your '
                        "phone away and go back to the TV.</p></body>"
                    ).encode()
                    self._send(200, body)
                else:
                    message = (
                        f'<p class="msg err">Sign-in didn\'t work: '
                        f"{html.escape(error)}. Try again from step 1.</p>"
                    )
                    self._send(200, owner._render(message))

            def log_message(self, *args):
                pass  # keep the app's log clean

        return Handler
