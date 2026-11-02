import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# The Android build has no portal or keyring service, and may not have
# GStreamer yet, so these are optional there.
for _namespace, _version in (("Gst", "1.0"), ("Xdp", "1.0"), ("Secret", "1")):
    try:
        gi.require_version(_namespace, _version)
    except ValueError:
        if sys.platform != "android":
            raise
