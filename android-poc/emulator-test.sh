#!/bin/sh
# Installs the probe APK on the emulator, opens it, sends D-pad presses and
# saves screenshots + log lines into android-poc/out/.
set -x
OUT=android-poc/out
mkdir -p "$OUT"
find android-poc/.pixiewood -name '*.apk' -exec ls -la {} +
APK=$(find android-poc/.pixiewood -name '*x86_64*.apk' | head -1)
[ -n "$APK" ] || APK=$(find android-poc/.pixiewood -name '*universal*.apk' | head -1)
[ -n "$APK" ] || APK=$(find android-poc/.pixiewood -name '*.apk' | head -1)
adb install -r "$APK" || exit 1
PKG=io.github.mikaelamayhem.hightidetvprobe
adb shell pm list packages | grep -i hightide
adb logcat -c
PKG=$(adb shell pm list packages | grep -i hightide | head -1 | cut -d: -f2 | tr -d '\r')
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
sleep 20
adb exec-out screencap -p > "$OUT/1-after-launch.png"
# Known GTK Android issue: the first frame may wait for input. Tap once.
adb shell input tap 5 5
sleep 3
adb exec-out screencap -p > "$OUT/2-after-tap.png"
n=3
for key in DPAD_DOWN DPAD_RIGHT DPAD_RIGHT DPAD_CENTER BUTTON_A BUTTON_B BUTTON_L1 BUTTON_R1 BUTTON_START; do
  adb shell input keyevent KEYCODE_$key
  sleep 2
  adb exec-out screencap -p > "$OUT/$n-after-$key.png"
  n=$((n+1))
done
adb logcat -d > "$OUT/logcat.txt"
grep -i "HTPROBE\|Gdk\|Gtk\|FATAL" "$OUT/logcat.txt" | tail -100
exit 0
