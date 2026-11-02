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
adb shell input keyevent KEYCODE_DPAD_DOWN
sleep 3
adb exec-out screencap -p > "$OUT/2-after-dpad-down.png"
adb shell input keyevent KEYCODE_DPAD_RIGHT
sleep 2
adb shell input keyevent KEYCODE_BUTTON_A
sleep 3
adb exec-out screencap -p > "$OUT/3-after-right-and-a.png"
adb shell input keyevent KEYCODE_DPAD_CENTER
sleep 3
adb exec-out screencap -p > "$OUT/4-after-dpad-center.png"
adb logcat -d > "$OUT/logcat.txt"
grep -i "HTPROBE\|gtk\|gdk\|FATAL\|AndroidRuntime" "$OUT/logcat.txt" | tail -200
exit 0
