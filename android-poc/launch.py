"""Start High Tide inside the Android app (replaces src/high-tide.in).

main.c runs this with the bundled Python. Everything High Tide needs sits
next to this file: the high_tide package, high-tide.gresource and the
pure-Python dependencies in pydeps/."""

import gettext
import locale
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(here, "pydeps"))
sys.path.insert(1, here)

from gi.repository import Gio, GLib  # noqa: E402

# The GTK Android runtime points XDG_DATA_HOME at the app's external files
# dir, which survives updates. Put HOME and the cache next to it.
data_home = GLib.get_user_data_dir()
os.environ.setdefault("HOME", os.path.dirname(data_home))
os.environ["XDG_CACHE_HOME"] = os.path.join(os.path.dirname(data_home), "cache", "high-tide")
os.makedirs(os.environ["XDG_CACHE_HOME"], exist_ok=True)
os.makedirs(data_home, exist_ok=True)

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
gettext.install("high-tide")

Gio.Resource.load(os.path.join(here, "high-tide.gresource"))._register()

from high_tide import main  # noqa: E402

# Android TV: always start in console mode.
sys.argv = ["high-tide", "--console"]
print("HTPROBE launching High Tide", flush=True)
sys.exit(main.main("android-dev"))
