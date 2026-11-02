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
sleep 45
adb exec-out screencap -p > "$OUT/1-after-launch.png"
# Save the app log now, in case the emulator dies during the key presses.
adb logcat -d > "$OUT/logcat-launch.txt"
grep -i "HTPROBE\|python\|FATAL\|AndroidRuntime\|DEBUG" "$OUT/logcat-launch.txt" | tail -150
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
adb logcat -d > "$OUT/logcat.txt" 2>/dev/null || true
grep -i "HTPROBE\|python\|Gdk\|Gtk\|FATAL\|DEBUG" "$OUT/logcat.txt" | tail -200
exit 0
