#!/usr/bin/env bash
# ClaudeSpeak speaker (macOS). Speaks a text file through the configured route.
#
# Routes:
#   voiceover  - hands the text to VoiceOver, so it uses the user's own voice,
#                rate and punctuation level, and their usual silence key stops it.
#                Requires "Allow VoiceOver to be controlled with AppleScript"
#                (VoiceOver Utility > General).
#   say        - a separate system voice, independent of any screen reader.
#   auto       - voiceover if VoiceOver is running, else say.
#
# Never throws: a speech failure must not break the session.
set -uo pipefail

CLAUDE_DIR="$HOME/.claude"
path=""
config="$CLAUDE_DIR/speak-config.json"

while [ $# -gt 0 ]; do
    case "$1" in
        --path|-Path|-p)         path="${2:-}"; shift 2 ;;
        --config|-ConfigPath|-c) config="${2:-}"; shift 2 ;;
        *) [ -z "$path" ] && path="$1"; shift ;;
    esac
done

[ -n "$path" ] && [ -s "$path" ] || exit 0

# IDT adaptation: jq does not ship with macOS, so fall back to plutil (which
# does, and reads JSON). Behaviour is identical when jq is present.
jqv() {
    if command -v jq >/dev/null 2>&1; then
        jq -r "$1 // empty" "$config" 2>/dev/null
    else
        local key="${1#.}" value
        value=$(/usr/bin/plutil -extract "$key" raw -o - -- "$config" 2>/dev/null) || return 0
        [ "$value" = "null" ] && return 0
        printf '%s\n' "$value"
    fi
}

engine=$(jqv '.engine'); : "${engine:=say}"
voice=$(jqv '.voice')
rate=$(jqv '.rate')

vo_running() {
    pgrep -f 'VoiceOver.app/Contents/MacOS/VoiceOver' >/dev/null 2>&1
}

# The engine falls through on purpose, so a clean exit only proves that *something* spoke.
# This records which route was actually taken, which is the difference between "your config
# is wrong" and "your config is right and the route was unavailable". Written before exec,
# because after exec there is no more script.
WORKDIR="${TMPDIR:-/tmp}/claude-speak"
log_route() {
    mkdir -p "$WORKDIR" 2>/dev/null || return 0
    printf '%s  requested=%s  used=%s  voice=%s  rate=%s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "$engine" "$1" "${voice:-<system default>}" "${rate:-<default>}" \
        > "$WORKDIR/last-route.log" 2>/dev/null || true
}

# Not exec, unlike say: VoiceOver can refuse ("AppleEvent handler failed",
# -10000, when "Allow VoiceOver to be controlled with AppleScript" is off), and
# then this falls through to say rather than speaking nothing. Nothing is lost
# for interrupting: osascript returns as soon as VoiceOver has the text, and
# VoiceOver's own speech is stopped by its own key, not by killing a process.
speak_voiceover() {
    log_route voiceover
    local error
    if error=$(/usr/bin/osascript - "$path" 2>&1 >/dev/null <<'APPLESCRIPT'
on run argv
    set p to item 1 of argv
    set t to (read POSIX file p as «class utf8»)
    tell application "VoiceOver" to output t
end run
APPLESCRIPT
    ); then
        exit 0
    fi
    mkdir -p "$WORKDIR" 2>/dev/null && printf '%s  VoiceOver refused: %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$error" >> "$WORKDIR/voiceover-refused.log" 2>/dev/null
}

speak_say() {
    log_route say
    local args=()
    [ -n "$voice" ] && args+=(-v "$voice")
    if [ -n "$rate" ] && [ "$rate" != "null" ]; then args+=(-r "$rate"); fi
    args+=(-f "$path")
    exec /usr/bin/say "${args[@]}"
}

case "$engine" in
    voiceover) vo_running && speak_voiceover ;;
    say)       ;;
    *)         vo_running && speak_voiceover ;;   # auto, and anything unrecognised
esac

# Fall through: the configured route was unavailable. Something should still speak.
speak_say
exit 0
