#!/bin/sh
set -eu
cd "$(dirname "$0")"
swift build -c release
app_path="dist/Sidra Homes.app"
mkdir -p "$app_path/Contents/MacOS"
cp .build/release/SidraHomes "$app_path/Contents/MacOS/"
cp Info.plist "$app_path/Contents/"
mkdir -p "$app_path/Contents/Resources" .build/Sidra.iconset
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" ../../web/sidra-icon.png --out ".build/Sidra.iconset/icon_${size}x${size}.png" >/dev/null
    double_size=$((size * 2))
    sips -z "$double_size" "$double_size" ../../web/sidra-icon.png --out ".build/Sidra.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns .build/Sidra.iconset -o "$app_path/Contents/Resources/Sidra.icns"
codesign --force --entitlements App.entitlements --sign - "$app_path"
printf 'Local ad-hoc build: %s\n' "$app_path"
