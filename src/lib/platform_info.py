# platform_info.py
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""What platform High Tide runs on, for the few places that differ."""

import sys

# Python 3.13+ reports "android" on Android.
IS_ANDROID = sys.platform == "android"

# GStreamer time unit (nanoseconds per second), usable without GStreamer.
NS_PER_SECOND = 1_000_000_000
