#!/bin/bash
# ============================================================================
# Double-click in Finder to make the disk image again from the last build,
# as Image Description Toolkit's create_macos_dmg.command does. The window
# stays open to read the result.
#
# It uses the app build_macos.sh packed (releases/TheChatPlace-osx-Portable.zip),
# the one with Velopack's updater in it, and writes
# releases/TheChatPlace-macos-arm64.dmg. When that app is signed with a
# Developer ID certificate, the disk image is signed with the same one.
# Notarizing stays with build_macos.sh (TCP_NOTARIZE=1).
#
# To build everything, double-click build_macos.command instead.
# ============================================================================
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.." || exit 1

ZIP=releases/TheChatPlace-osx-Portable.zip
DMG=releases/TheChatPlace-macos-arm64.dmg

finish() {
    echo ""
    read -r -p "Press Enter to close..."
    exit "$1"
}

if [ ! -f "$ZIP" ]; then
    echo "There's no $ZIP yet."
    echo "Double-click build_macos.command first: it builds the app and the disk image."
    finish 1
fi

VERSION=$(.venv/bin/python tools/check_version.py 2>/dev/null) || VERSION=""
if [ -z "$VERSION" ]; then
    echo "Couldn't read the version (is .venv set up? Double-click macsetup.command)."
    finish 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
# ditto, not unzip: it keeps the symlinks and attributes the signature covers.
ditto -x -k "$ZIP" "$WORK"
APP=$(find "$WORK" -maxdepth 1 -name "*.app" | head -1)
if [ -z "$APP" ] || [ ! -f "$APP/Contents/MacOS/UpdateMac" ]; then
    echo "The app in $ZIP has no Velopack updater (UpdateMac)."
    echo "Double-click build_macos.command to build it again."
    finish 1
fi

# Signed if the app is: the disk image gets the app's own certificate.
IDENTITY=$(codesign -dvv "$APP" 2>&1 | sed -n 's/^Authority=\(Developer ID Application: .*\)$/\1/p' | head -1)

echo "Making the disk image for The Chat Place $VERSION..."
bash "$HERE/create_dmg.sh" "$APP" "$DMG" "$VERSION" "$([ -n "$IDENTITY" ] && echo signed)" \
    2> >(grep -v "hdiutil: WARNING" >&2) || { echo "Couldn't make the disk image."; finish 1; }

if [ -n "$IDENTITY" ]; then
    echo "Signing it ($IDENTITY)..."
    codesign --force --timestamp --sign "$IDENTITY" "$DMG" || { echo "Couldn't sign it."; finish 1; }
    echo "Signed, not notarized: for public download, build with TCP_NOTARIZE=1."
else
    echo "Unsigned, as the app in it is."
fi
echo ""
echo "Done: $DMG"
finish 0
