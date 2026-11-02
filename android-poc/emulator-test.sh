#!/bin/sh
# Installs the probe APK on the emulator, opens it, sends D-pad presses and
# saves screenshots + log lines into android-poc/out/.
set -x
OUT=android-poc/out
mkdir -p "$OUT"
APK=$(ls .pixiewood/android/app/build/outputs/apk/debug/*x86_64*.apk 2>/dev/null | head -1)
[ -n "$APK" ] || APK=$(ls .pixiewood/android/app/build/outputs/apk/debug/*.apk | head -1)
adb install -r "$APK"
PKG=io.github.mikaelamayhem.hightidetvprobe
adb shell pm list packages | grep -i hightide
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 || adb shell monkey -p "$(adb shell pm list packages | grep -i hightide | head -1 | cut -d: -f2 | tr -d '\r')" 1
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
