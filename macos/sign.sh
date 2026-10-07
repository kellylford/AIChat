#!/bin/bash
# ============================================================================
# Developer ID signing for TheChatPlace.app (from Image Description Toolkit's
# sign_macos.sh)
# ============================================================================
# Signs inside-out under the hardened runtime with a secure timestamp, which
# notarization requires: every nested library first, deepest first, then the
# bundle with the entitlements. Not `codesign --deep`, which Apple deprecated:
# it puts the app's entitlements on every library and skips code it doesn't
# recognise.
#
#   bash macos/sign.sh dist/TheChatPlace.app
#
# Environment:
#   TCP_SIGNING_IDENTITY  "Developer ID Application: Name (TEAMID)"; if unset,
#                         the first Developer ID Application identity found
#   TCP_KEYCHAIN          keychain to search (CI uses a throwaway one)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTITLEMENTS="$SCRIPT_DIR/entitlements.plist"
APP="${1:?Usage: $0 <path-to-.app>}"
[ -d "$APP" ] || { echo "ERROR: not found: $APP"; exit 1; }

KEYCHAIN_ARGS=()
[ -n "${TCP_KEYCHAIN:-}" ] && KEYCHAIN_ARGS=(--keychain "$TCP_KEYCHAIN")

IDENTITY="${TCP_SIGNING_IDENTITY:-}"
if [ -z "$IDENTITY" ]; then
    IDENTITY=$(security find-identity -v -p codesigning ${TCP_KEYCHAIN:+"$TCP_KEYCHAIN"} \
        | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)"/\1/') || true
fi
if [ -z "$IDENTITY" ]; then
    echo "ERROR: No Developer ID Application identity found."
    echo "       Set TCP_SIGNING_IDENTITY, or import the certificate first."
    security find-identity -v -p codesigning || true
    exit 1
fi
echo "Signing identity: $IDENTITY"

sign_one() {
    local path="$1"; shift
    # Wheels ship libraries signed by other teams; drop that first.
    codesign --remove-signature "$path" 2>/dev/null || true
    codesign --force --options runtime --timestamp "$@" \
        "${KEYCHAIN_ARGS[@]+"${KEYCHAIN_ARGS[@]}"}" --sign "$IDENTITY" "$path"
}

# Libraries and nested executables, deepest path first.
while IFS= read -r lib; do
    [ -n "$lib" ] || continue
    sign_one "$lib"
done < <(find "$APP/Contents" -type f \( -name "*.so" -o -name "*.dylib" -o -perm -u+x \) \
            ! -path "*/Contents/MacOS/TheChatPlace" -exec sh -c \
            'file -b "$1" | grep -q Mach-O && echo "$1"' _ {} \; \
         | awk '{print length" "$0}' | sort -rn | cut -d' ' -f2-)

# Frameworks (Python.framework), deepest first, then the bundle itself.
while IFS= read -r fw; do
    [ -n "$fw" ] || continue
    sign_one "$fw"
done < <(find "$APP/Contents" -type d -name "*.framework" | awk '{print length" "$0}' | sort -rn | cut -d' ' -f2-)

sign_one "$APP" --entitlements "$ENTITLEMENTS"

codesign --verify --strict --deep --verbose=2 "$APP"
echo "Gatekeeper (rejects until notarized):"
spctl --assess --type execute --verbose=2 "$APP" 2>&1 || true
echo "Signed: $APP"
