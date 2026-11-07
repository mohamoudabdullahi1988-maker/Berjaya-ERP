#!/bin/sh
set -eu
cd "$(dirname "$0")"
swift build -c release
app_path="dist/Sidra Homes.app"
mkdir -p "$app_path/Contents/MacOS"
cp .build/release/SidraHomes "$app_path/Contents/MacOS/"
cp Info.plist "$app_path/Contents/"
codesign --force --entitlements App.entitlements --sign - "$app_path"
printf 'Local ad-hoc build: %s\n' "$app_path"
