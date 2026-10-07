#!/bin/bash
# ============================================================================
# Notarize and staple a signed .dmg (from Image Description Toolkit's
# notarize_macos.sh)
# ============================================================================
#   bash BuildAndRelease/MacBuilds/notarize.sh releases/TheChatPlace-macos-arm64.dmg
#
# Credentials, either:
#   NOTARY_KEY_PATH + NOTARY_KEY_ID + NOTARY_ISSUER_ID   App Store Connect API key (CI)
#   NOTARY_APPLE_ID + NOTARY_PASSWORD + NOTARY_TEAM_ID   Apple ID, app-specific password
#   NOTARY_PROFILE                                       a `notarytool store-credentials` profile
# ============================================================================
set -euo pipefail

TARGET="${1:?Usage: $0 <path-to-.dmg>}"
[ -e "$TARGET" ] || { echo "ERROR: not found: $TARGET"; exit 1; }

if [ -n "${NOTARY_KEY_PATH:-}" ] && [ -n "${NOTARY_KEY_ID:-}" ] && [ -n "${NOTARY_ISSUER_ID:-}" ]; then
    CRED_ARGS=(--key "$NOTARY_KEY_PATH" --key-id "$NOTARY_KEY_ID" --issuer "$NOTARY_ISSUER_ID")
elif [ -n "${NOTARY_APPLE_ID:-}" ] && [ -n "${NOTARY_PASSWORD:-}" ] && [ -n "${NOTARY_TEAM_ID:-}" ]; then
    CRED_ARGS=(--apple-id "$NOTARY_APPLE_ID" --password "$NOTARY_PASSWORD" --team-id "$NOTARY_TEAM_ID")
elif [ -n "${NOTARY_PROFILE:-}" ]; then
    CRED_ARGS=(--keychain-profile "$NOTARY_PROFILE" ${TCP_KEYCHAIN:+--keychain "$TCP_KEYCHAIN"})
else
    echo "ERROR: No notarization credentials (see the top of $0)."
    exit 1
fi

echo "Submitting $TARGET to Apple's notary service (usually 2-15 minutes)..."
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT
xcrun notarytool submit "$TARGET" "${CRED_ARGS[@]}" --wait 2>&1 | tee "$LOG" || true

if ! grep -q "status: Accepted" "$LOG"; then
    ID=$(grep -Eo 'id: [0-9a-f-]{36}' "$LOG" | head -1 | awk '{print $2}' || true)
    echo "NOTARIZATION FAILED"
    # The detailed log names the offending binary, which the summary doesn't.
    [ -n "$ID" ] && xcrun notarytool log "$ID" "${CRED_ARGS[@]}" || true
    exit 1
fi

xcrun stapler staple "$TARGET"
xcrun stapler validate "$TARGET"
echo "Notarized and stapled: $TARGET"
