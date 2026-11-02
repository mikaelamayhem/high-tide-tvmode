"""High Tide Android TV probe, stage 2: the same test window as before,
written in Python with PyGObject, plus a network check (Tidal sign-in
needs HTTPS to work). Lines starting with HTPROBE go to logcat."""

import platform
import ssl
import sys
import threading
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402


def log(msg):
    print("HTPROBE", msg, flush=True)


log(f"python {sys.version} on {platform.machine()}, PyGObject {gi.__version__}")


def android_ca_bundle():
    """Collect Android's system CA certificates as one PEM string.

    Android names the files by OpenSSL's old hash, which current OpenSSL
    can't use as a lookup directory, so read them all instead."""
    import os
    import re

    pem = re.compile(r"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.S)
    certs = []
    for d in ("/apex/com.android.conscrypt/cacerts", "/system/etc/security/cacerts"):
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            with open(os.path.join(d, name), encoding="ascii", errors="ignore") as f:
                certs += pem.findall(f.read())
        if certs:
            break
    log(f"loaded {len(certs)} CA certificates")
    return "\n".join(certs)


def check_network(label):
    """Fetch the Tidal API root over HTTPS and report the outcome."""
    try:
        ctx = ssl.create_default_context(cadata=android_ca_bundle())
        req = urllib.request.Request("https://api.tidal.com/v1/", method="GET")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                result = f"HTTPS OK ({r.status})"
        except urllib.error.HTTPError as e:
            # Any HTTP answer means TLS and DNS work.
            result = f"HTTPS OK (Tidal answered {e.code})"
    except Exception as e:  # noqa: BLE001
        result = f"HTTPS failed: {e!r}"
    log("network " + result)
    GLib.idle_add(label.set_text, "Network: " + result)


def on_activate(app):
    win = Adw.ApplicationWindow(application=app, title="High Tide TV probe")
    view = Adw.ToolbarView()
    view.add_top_bar(Adw.HeaderBar())

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                  valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER,
                  margin_start=12, margin_end=12)
    title = Gtk.Label(label="High Tide TV probe (Python)")
    title.add_css_class("title-1")
    box.append(title)
    box.append(Gtk.Label(label=(
        f"Python {platform.python_version()}, PyGObject {gi.__version__}, "
        f"GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}, "
        f"libadwaita {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}"),
        wrap=True, justify=Gtk.Justification.CENTER))

    row = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=4,
                      column_spacing=12, row_spacing=12, halign=Gtk.Align.CENTER)
    last_key = Gtk.Label(label="Press a button on the remote or controller", wrap=True,
                         justify=Gtk.Justification.CENTER)
    last_key.add_css_class("title-3")

    for name in ("Home", "Discover", "Queue", "Lyrics"):
        b = Gtk.Button(label=name)
        b.add_css_class("pill")

        def clicked(_b, n=name):
            log(f"clicked {n}")
            last_key.set_text(f"Activated: {n}")

        b.connect("clicked", clicked)
        row.append(b)

    net = Gtk.Label(label="Network: checking…", wrap=True)
    box.append(row)
    box.append(last_key)
    box.append(net)
    view.set_content(box)
    win.set_content(view)

    keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)

    def on_key(_c, keyval, keycode, _state):
        text = f"Last key: {Gtk.accelerator_name(keyval, 0)} (code {keycode})"
        last_key.set_text(text)
        log("key " + text)
        return False

    keys.connect("key-pressed", on_key)
    win.add_controller(keys)
    win.present()
    log("window presented")
    threading.Thread(target=check_network, args=(net,), daemon=True).start()


app = Adw.Application(application_id="io.github.mikaelamayhem.HighTideTvProbe")
app.connect("activate", on_activate)
app.run(sys.argv)
