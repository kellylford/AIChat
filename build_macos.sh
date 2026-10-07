#!/bin/bash
# ============================================================================
# Build The Chat Place on this Mac: tests, TheChatPlace.app, a smoke test,
# and the disk image. The same steps as the macOS job in the release workflow
# (.github/workflows/release-thechatplace.yml); build.cmd is the Windows one.
#
#   ./build_macos.sh                     build into dist/ and releases/
#   ./build_macos.sh ~/Desktop/builds    and copy the .dmg there
#
# Or double-click build_macos.command in Finder.
#
# Unsigned unless you ask (the README in the .dmg then says how to open it):
#   TCP_SIGN_CODE=1   sign with your Developer ID Application certificate
#                     (TCP_SIGNING_IDENTITY picks one; see macos/sign.sh)
#   TCP_NOTARIZE=1    and notarize the .dmg (credentials: macos/notarize.sh)
#
# Uses the repo's .venv, and runs macsetup.sh to make it the first time.
# Apple Silicon only, as Image Description Toolkit's Mac build is.
# ============================================================================
set -euo pipefail

OUTPUT_DIR="${1:-}"
[ -n "$OUTPUT_DIR" ] && OUTPUT_DIR="$(cd "$(dirname "$OUTPUT_DIR")" 2>/dev/null && pwd)/$(basename "$OUTPUT_DIR")"
cd "$(dirname "$0")"

PY=.venv/bin/python
APP=dist/TheChatPlace.app
BUNDLE_ID=net.theideaplace.thechatplace
DMG=releases/TheChatPlace-macos-arm64.dmg
SIGN="${TCP_SIGN_CODE:-0}"
NOTARIZE="${TCP_NOTARIZE:-0}"
[ "$NOTARIZE" = "1" ] && SIGN=1

fail() { echo ""; echo "BUILD FAILED: $*"; exit 1; }

echo "========================================================================"
echo "Building The Chat Place for macOS"
echo "========================================================================"

if [ "$(uname -m)" != "arm64" ]; then
    fail "this builds for Apple Silicon, and this Mac is $(uname -m)."
fi

# ------------------------------------------------------------------ .venv ----
if [ ! -x "$PY" ]; then
    echo ""
    echo "No .venv yet: running macsetup.sh..."
    ./macsetup.sh --yes || fail "macsetup.sh couldn't set up .venv."
fi
echo ""
echo "Installing what the build needs into .venv..."
"$PY" -m pip install --quiet -r requirements-build.txt || fail "pip install"

# ------------------------------------------------------------------ tests ----
echo ""
echo "Running the tests..."
"$PY" -m pytest -q tests || fail "the tests."

VERSION=$("$PY" tools/check_version.py) || fail "tools/check_version.py"
echo ""
echo "The Chat Place $VERSION"

# -------------------------------------------------------------------- app ----
# --onedir --windowed makes an .app whose libraries can each be signed (a
# onefile app unpacks unsigned copies at every start). The speech scripts are
# data files. velopack is left out: only Windows installs its own updates.
echo ""
echo "Building the app (PyInstaller)..."
rm -rf "$APP"
"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir --name TheChatPlace \
    --osx-bundle-identifier "$BUNDLE_ID" --exclude-module velopack \
    --add-data "thechatplace/speech:thechatplace/speech" \
    TheChatPlace.pyw || fail "PyInstaller"
[ -x "$APP/Contents/MacOS/TheChatPlace" ] || fail "no $APP/Contents/MacOS/TheChatPlace"

# What PyInstaller can't set from the command line. NSAppleEventsUsageDescription
# is what macOS shows when speech first asks VoiceOver to speak.
PLIST="$APP/Contents/Info.plist"
plist_set() {
    /usr/libexec/PlistBuddy -c "Set :$1 $2" "$PLIST" 2>/dev/null \
        || /usr/libexec/PlistBuddy -c "Add :$1 string $2" "$PLIST"
}
plist_set CFBundleShortVersionString "$VERSION"
plist_set CFBundleVersion "$VERSION"
plist_set CFBundleDisplayName "The Chat Place"
plist_set CFBundleName "The Chat Place"
plist_set NSHumanReadableCopyright "Copyright Kelly Ford. MIT License."
plist_set NSAppleEventsUsageDescription \
    "The Chat Place asks VoiceOver to speak announcements, such as when Claude replies."
# Editing Info.plist breaks PyInstaller's ad-hoc signature; make a new one.
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || fail "ad-hoc signing"

# ------------------------------------------------------------- smoke test ----
echo ""
echo "Smoke test of the built app..."
rm -f smoke-local.json
"$APP/Contents/MacOS/TheChatPlace" --smoke-test smoke-local.json \
    || { cat smoke-local.json 2>/dev/null; fail "the built app's smoke test."; }
cat smoke-local.json
echo ""

# --------------------------------------------------------------- signing ----
if [ "$SIGN" = "1" ]; then
    echo ""
    echo "Signing with Developer ID..."
    bash macos/sign.sh "$APP" || fail "signing"
fi

# ------------------------------------------------------------ disk image ----
echo ""
bash macos/create_dmg.sh "$APP" "$DMG" "$VERSION" "$([ "$SIGN" = "1" ] && echo signed)" \
    || fail "the disk image."
if [ "$SIGN" = "1" ]; then
    codesign --force --timestamp ${TCP_KEYCHAIN:+--keychain "$TCP_KEYCHAIN"} \
        --sign "${TCP_SIGNING_IDENTITY:-Developer ID Application}" "$DMG" || fail "signing the .dmg"
fi
if [ "$NOTARIZE" = "1" ]; then
    bash macos/notarize.sh "$DMG" || fail "notarization"
fi

if [ -n "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    cp "$DMG" "$OUTPUT_DIR/" || fail "couldn't copy into $OUTPUT_DIR"
fi

echo ""
echo "========================================================================"
echo "BUILD SUCCESSFUL: The Chat Place $VERSION ($([ "$SIGN" = "1" ] && echo signed || echo unsigned)$([ "$NOTARIZE" = "1" ] && echo ", notarized"))"
echo "========================================================================"
echo "  Disk image: $DMG"
echo "  App:        $APP"
[ -n "$OUTPUT_DIR" ] && echo "  Copied to:  $OUTPUT_DIR"
exit 0
