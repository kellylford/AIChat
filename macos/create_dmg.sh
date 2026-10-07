#!/bin/bash
# ============================================================================
# The Chat Place's disk image: TheChatPlace.app, a link to Applications to
# drag it onto, and a short README.txt. From Image Description Toolkit's
# create_macos_dmg.sh, without its Finder window styling.
# ============================================================================
#   bash macos/create_dmg.sh dist/TheChatPlace.app releases/TheChatPlace-macos-arm64.dmg <version> [signed]
#
# With "signed" the README leaves out the unsigned-build note.
# ============================================================================
set -euo pipefail

APP="${1:?Usage: $0 <app> <dmg> <version> [signed]}"
DMG="${2:?Usage: $0 <app> <dmg> <version> [signed]}"
VERSION="${3:?Usage: $0 <app> <dmg> <version> [signed]}"
SIGNED="${4:-}"
VOLUME="The Chat Place"

[ -d "$APP" ] || { echo "ERROR: not found: $APP"; exit 1; }
mkdir -p "$(dirname "$DMG")"

STAGING=$(mktemp -d)
WORK=$(mktemp -d)
MOUNT="$WORK/mount"
cleanup() {
    hdiutil detach "$MOUNT" -force >/dev/null 2>&1 || true
    rm -rf "$STAGING" "$WORK"
}
trap cleanup EXIT

# ditto keeps signatures and extended attributes, which cp can lose.
ditto "$APP" "$STAGING/TheChatPlace.app"

cat > "$STAGING/README.txt" <<README
The Chat Place $VERSION
=======================

A keyboard and screen reader friendly home for your Claude Code chats.

To install, drag TheChatPlace.app onto Applications, then open it from
Applications (or with Spotlight: Cmd+Space, "The Chat Place").

You need Claude Code installed and signed in to a Claude subscription
(https://claude.com/claude-code). The Chat Place never uses an API key.

To update, download the new disk image (Help, Check for Updates says when
there is one and opens its page), quit The Chat Place, and drag the new app
onto Applications, replacing the old one. Your sessions and settings are in
~/Library/Application Support/TheChatPlace and are kept.
README
if [ "$SIGNED" != "signed" ]; then
    cat >> "$STAGING/README.txt" <<'README'

This build isn't signed by Apple, so the first time you open it macOS says it
can't check it. Open System Settings, Privacy & Security, scroll to Security,
and choose Open Anyway next to The Chat Place; then open it again.
README
fi

# The Applications link is made on the mounted image, not in the staging
# folder: IDT found that hdiutil's -srcfolder can follow it and try to copy
# all of /Applications.
echo "Creating the disk image..."
hdiutil create -srcfolder "$STAGING" -volname "$VOLUME" -fs APFS -format UDRW \
    -ov "$WORK/rw.dmg" >/dev/null
mkdir -p "$MOUNT"
hdiutil attach "$WORK/rw.dmg" -readwrite -noverify -noautoopen -nobrowse -mountpoint "$MOUNT" >/dev/null
ln -s /Applications "$MOUNT/Applications"
sync
hdiutil detach "$MOUNT" >/dev/null

rm -f "$DMG"
hdiutil convert "$WORK/rw.dmg" -format UDZO -imagekey zlib-level=9 -o "$DMG" >/dev/null
echo "Disk image: $DMG"
