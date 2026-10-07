# The Chat Place

A home for your Claude Code chats: an accessible companion for Claude Code.

The Chat Place is an independent project by Kelly Ford. It works with Claude Code and the
Claude desktop app, but it isn't made, sponsored or endorsed by Anthropic, and isn't affiliated
with it. Claude and Claude Code are trademarks of Anthropic.

Keyboard shortcuts: [docs/keyboard-shortcuts.md](docs/keyboard-shortcuts.md) (also as
[HTML](docs/keyboard-shortcuts.html) and [plain text](docs/keyboard-shortcuts.txt)), the same list
as Help, Keyboard Shortcuts (F1) in the app.

> **Status: version 0.1.1, a pre-release** (0.1.0, the first release, came out on 7 October 2026). Used with JAWS on Kelly's PC; the
> installer, uninstaller and update check have been tested in the vmtest VM. Downloading and
> installing an update needs two published releases, so it is first tried with 0.1.1. It has not
> yet had a pass with NVDA. The Mac build is new: built, smoke-tested and Developer ID signed on
> Kelly's Mac, but not yet notarized in CI or used with VoiceOver.

A keyboard and screen reader friendly reader for Claude Code sessions. It lists every session the
Claude desktop app has open, shows each one as a conversation you can arrow through, tells you
when a session answers, and switches the desktop app to a session when you need the real thing.
It can also start sessions of its own, which you can read and reply to entirely from here.

It runs on your existing Claude subscription, signed in to Claude Code, and never uses an API
key. Its own sessions' turns are Claude Code turns in headless mode (`claude -p`). Anthropic's
help article [Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
says those count against a monthly credit; past it, turns stop unless you've turned on extra
usage, which is billed. View, Usage and Context (Ctrl+Shift+U) says where you
stand. Reading the desktop app's sessions costs nothing.

## What it does

One window, three parts, in Tab order: the **session list**, the **messages** of the loaded
session, and the **reply box** with Send and Stop. Shift+Tab goes back the same way, and the
session list is always there. **F6** and **Shift+F6** move between those parts and the **status
bar**, which holds whatever was said last ("12 sessions: 1 need you", "Claude is using Bash.") in
a read-only box to read by line, word and character; **Ctrl+9** goes straight there. The status
bar isn't a Tab stop, and your screen reader's own read-status-bar key still works.

- **Session list.** Each item reads its title, its repo folder, its state (needs you, working or
  idle), and when it was last active: "Fix the release build, QuickMail, needs you: Choose a
  version number, active 1 minute ago". By default sessions that need you come first, then
  working ones, then the rest, newest first. **View, Sort Sessions** (Alt+V, O) chooses another
  order: by status (that default), newest first, oldest first, by title, or by folder (A to Z,
  newest first within one title or folder). The choice is remembered, and choosing it reorders
  the list at once, keeping you on the same session. The list refreshes itself every five
  seconds. While you're in the list, rows don't move: a changed session is updated where it is
  and a new one is added at the end. F5, or a refresh while you're elsewhere, puts it back in
  order, keeping you on the same session.
  **View, Show Sessions** (Alt+V, H) chooses which sessions are listed: all, needs you or
  working, needs you, desktop app sessions, The Chat Place's own, Remote Control sessions (ones
  the desktop app has linked for Remote Control), archived (the desktop app's archived
  sessions, otherwise hidden), hidden (the ones you've hidden), or one of your groups. The
  list's name says what it shows and how many ("Session list, needs you, 2 of 139"), and the
  choice is remembered.
  Arrowing doesn't load anything; **Enter loads that session** into the messages list, moves you
  there, and says "Loaded Quiet one, 12 messages."
- **Hide or delete a session.** **Delete** (File, Hide Session) takes the selected session out of
  the list without changing it; View, Show Sessions, Hidden lists hidden sessions, and File, Bring
  Back Session returns one. **Shift+Delete** (File, Delete Session Permanently) deletes one of The
  Chat Place's own sessions for good, from any view, hidden or not: after you confirm (No is the
  default), its Claude Code transcript is deleted from the computer and it leaves the list, its
  groups and the hidden list. It waits while the session is working, here or in a terminal.
  Desktop app sessions can only be hidden; delete those in the desktop app.
  On a Mac laptop these are Fn+Delete and Fn+Shift+Delete (the forward-delete key).
- **Find** (Ctrl+F, View, Find). In the session list it asks for some text and shows only
  sessions whose title, folder or "needs you" note contains it, within the current view; the
  list's name says so ("Session list, matching \"build\", 3 of 139") and Escape shows them
  all again. In the messages it finds the next message containing the text, searching each
  message's whole text, not just the first line you see; F3 and Shift+F3 find the next and
  previous, going round from the other end when they reach one (and saying so).
- **Groups**, like groups in Claude on the web: **Ctrl+G** (File, Add to Group) puts the
  selected session in a group, or a new one; File, Remove from Group takes it out; File,
  Manage Groups lists your groups with how many sessions each has, to make, rename or delete
  them (deleting a group never touches its sessions). A session can be in several groups, and
  its row says which ("…, group Work"). The Chat Place's groups are kept in
  `%APPDATA%\TheChatPlace\groups.json`; the desktop app's files are never changed.
  The **desktop app's own groups** show too: in View, Show Sessions, in each session's row,
  and in Add to Group. They're read from the desktop app's settings each refresh, so a change
  there shows here; they're changed in the desktop app. Adding one of The Chat Place's sessions
  to a desktop app group keeps a Chat Place group of the same name, shown together with it.
- **What "needs you" means.** For a Claude desktop app session: it isn't working right now (it can
  still be open in the desktop app), and the desktop
  app's summary of its latest turn says it's waiting on you, either with a "needs action" note
  (read after "needs you:") or a status such as blocked, needs input or review ready. The desktop
  app doesn't write that summary after every turn, so a session can be waiting on you and still
  show as idle. For one of The Chat Place's own sessions: Claude is waiting right now for a
  permission, a question or a plan (Ctrl+Shift+A), which ends when you answer; or its last turn
  failed, or tools were refused in it, which is saved with the session and lasts, even across a
  restart, until its next turn starts.
- **Messages:** newest last, with focus on the newest. Each row shows "You:" or "Claude:" and its
  first line, but your screen reader reads the **whole message** as you arrow onto it, as words
  (headings and list items as sentences, and each code block as what it is: "Code block,
  Python, 14 lines"). Settings, Reading
  messages turns that off, to hear just the first line. The list's name says the session's state
  and whether it's read-only. **Enter**
  (or the context menu's Read Full Message, with the Applications key or Shift+F10) shows the
  whole message as a formatted page, so your screen reader's browse mode moves by heading (H),
  table (T, then its cell commands), list (L) and code block (each is a region, R, named like
  "Code block, Python, 14 lines"). Links open in your browser. **Read as Plain Text** (Alt+P)
  switches to a read-only text box, to read by line, word and character, and Settings can make
  that the default. Escape closes either, back on the same message. The page needs Microsoft's
  Edge WebView2 runtime, which comes with Windows 11; without it, the text box opens. Nothing in
  the page is fetched from the internet, and HTML in a message is shown as text, never run.
  **Code Blocks** on the context menu lists the message's code blocks by language and size, with
  the selected one's code in a box to read by line (Enter on a block goes there) and a Copy
  button for just that block;
  **Ctrl+Shift+C** copies the message's last code block straight away.
  Question cards read as "Claude asked: Which version?" with the
  options in the full text, then "You answered: ...". Refused tools read "Permission denied:
  ...". Tool calls and tool results are hidden unless you turn on Show Tool Activity (Ctrl+T).
  With it on, the open session's tool calls are also **spoken as they happen**, so a long turn
  isn't silent: "Using Bash: git status; Read: main.py." In The Chat Place's own sessions, what
  Claude writes between tool calls ("Let me check the build.") is spoken too. A run of calls is
  gathered for a moment and said together, counted when there are many ("Using Read 4 times,
  then Bash."), and never cuts off your screen reader. At the summary level tools are always
  counted; at silent only the status bar shows them. Tool results aren't spoken.
  New messages arrive at the end without moving you.
- **Reply box:** for The Chat Place's own sessions, type and press Ctrl+Enter (or Send). You stay in
  the reply box. For desktop app sessions the same place holds a read-only note saying why
  replying happens in Claude, and an Open in Claude button.
- **Escape** in the messages or the reply box (or Backspace in the messages) goes back to the
  session list, on the same session. Enter there on the session that's already loaded takes you
  back to its messages where you left them, without reloading.
- **Commands and skills** (Ctrl+/, the Commands button after Stop, or File, Insert Command
  or Skill), in The Chat Place's own
  sessions: a searchable list of your skills and custom commands, then Claude Code's own
  (/compact, /context, /code-review and the rest), each with its description and what it
  takes. Type to filter by name or description, Down to the list, Enter to choose: it goes
  at the start of the reply box ("/compact "), replacing a command already there and keeping
  what you typed, ready to finish and send. The list is Claude Code's own for the session's
  folder, asked for in the background when the session loads (no turn, no cost) and kept
  current by each turn. If it isn't there yet, you hear "Commands are ready" when it is; the list
  never opens by itself.
- **Attachments**, in The Chat Place's own sessions: **Attach Files** (Alt+T, after Commands;
  Ctrl+Shift+F) adds files and images to your next message, and **Ctrl+V** in the reply box
  attaches a picture on the clipboard, such as a screenshot from Win+Shift+S. They're listed
  under the reply box ("2 attachments: screenshot.png, log.txt"); Delete there removes one.
  Images go to Claude as images, so it can describe what's on screen; other files are named
  in the message as `@"path"`, which Claude Code reads in for Claude. A message can be
  just attachments. Each session keeps its own until they're sent. Pasted pictures are saved
  in `%APPDATA%\TheChatPlace\pasted images`.
- **Export** (Ctrl+E, File, Export Session) saves the selected session's conversation,
  or the loaded one's, to a file: **Markdown**, a **web page** (formatted like the full-message
  view, nothing fetched from the internet) or **plain text**, chosen by the Save as type list
  or the file name's extension. Each message is a heading ("Claude, 10:43") and its text as
  written, with the message's own headings moved down two levels so the file's outline stays
  session, message, section. Tool activity is included when Show Tool Activity is on. It
  starts in Documents, named after the session and the date, works in the background (a long
  session never freezes the window), and says where it saved; the status bar keeps that to read
  back. Headings carry the time, and the date whenever the day changes.
- **Open in Claude** (Ctrl+O) switches the desktop app to the session, for approving a permission
  prompt or answering a question card in a desktop app session.
- **Continue Here** (Ctrl+Shift+N, or the button beside Open in Claude) carries a desktop app
  session on in The Chat Place, as a copy: a new Chat Place session in the same folder, with the
  whole conversation so far in its messages, that you reply to here. You type its first message
  in the same dialog as New Session; the title starts as "<title> (continued)". The desktop app
  session isn't changed, and what you do in the copy doesn't appear in it.
- **New Session** (Ctrl+N) starts a session of The Chat Place's own: choose a folder, a title,
  the model (Alt+D), a permission mode (auto by default; accept edits, manual and plan are
  offered) and the first message. The models are Default (your Claude Code setting), Opus,
  Sonnet and Haiku, each the latest of its family. The model is kept with the session and
  passed to every turn. Arriving in the messages, you hear it ("Messages in Build (idle, on
  Opus)"). Fable isn't offered: on some plans it bills to usage credits, and in the headless
  mode The Chat Place uses, Claude Code does that without asking. So if a turn would run on
  Fable anyway (Claude Code's own default, or a fallback), The Chat Place stops it before
  anything is sent and says why. **File, Change Model** changes a session's model from its
  next turn. If that first message never reaches Claude (Claude Code not signed in, say), it goes
  back into the reply box and Send starts the session again.
- **Remote Control.** Settings can turn on Remote Control for The Chat Place's sessions, and
  **File, Remote Control** turns it on or off for one session (or back to the Settings
  default). A session on Remote Control can be reached from claude.ai and your other devices
  while one of its turns is running: each turn is its own Claude Code process, so between turns
  it shows as offline. The same Remote Control session is joined every turn, and File, Remote
  Control copies its claude.ai address. Turning it on copies the conversation to claude.ai,
  where it stays (turning Remote Control off, or deleting the session, doesn't remove it;
  archive it on claude.ai). While a turn runs, anyone signed in to your account on claude.ai
  can type into it or answer its questions; a question answered there is cleared here.
- **Claude asks, you answer.** In The Chat Place's own sessions, when Claude needs permission
  for something the permission mode doesn't allow, asks you a question, or has a plan for you
  to approve, the turn waits for you. It's announced ("Build needs you. Claude wants to run
  git push. Ctrl+Shift+A answers."), and the session shows as needing you in the list.
  **Ctrl+Shift+A** opens the answer:
  - **Permission:** the whole request (the command, or the file and what would change) to
    read by line, then **Allow**, **Allow for this session** (shown when Claude Code suggests
    a rule, and named in full, such as "don't ask again this session for Bash(git push:*)"),
    or **Deny**, which is the default button and can carry a reason Claude reads.
  - **Questions:** each question is a group of options with their descriptions, with Other
    and a box to type your own answer; Send Answers, or Don't Answer.
  - **Plan:** the plan to read (Read Formatted shows it as a page, by heading), then **Approve**, choosing the mode to carry on in (accept
    edits, auto or manual), or **Keep Planning** with what to change, which is the default.

  Escape in any of them answers later; nothing is approved or refused by waiting. "For this
  session" lasts for the session, not just the turn: The Chat Place keeps the rule with the
  session and gives it to every later turn. It never writes Claude Code's settings files.
- **Announcements.** When the open session gets a new reply, or one of The Chat Place's sessions
  finishes a turn, or any listed session stops working, it's announced through your screen reader
  (or a system voice) and put on the status bar. Settings (Ctrl+Comma) chooses full (the whole
  reply), summary (the session's name and the first sentence) or silent (status bar only), whether
  every listed session is announced or just the open one, and the speech route; its Reading
  messages group chooses whether full messages open as a formatted page or plain text.
  Ctrl+Shift+R repeats the last announcement.
- **The status bar** (F6, or Ctrl+9) has parts, as in QuickMail, and Left and Right move between
  them: what was last said, then the loaded session and what it's doing (read-only text), then
  buttons that appear when there's something to act on: how full the context is (Usage and
  Context), how many sessions need you (goes to the first), and an available update. Tab leaves
  the status bar. Your screen reader's read-status-bar key reads all the parts.
- **Answers to what you do are spoken too**, briefly and without cutting off your screen reader:
  "Tool activity shown.", "Message copied.", and so on (unless announcements are set to silent).
- **Your own message is read back when it's sent**, so you hear what actually went to Claude,
  and where: "Sent to Hub probe: Fix the build." During a turn it's "Queued for Hub probe: …",
  and when the queued message goes out you hear only "Sent your queued message", not the
  message again. It follows the announcement level: at full, the message up to about 300
  characters, then "… and 412 more words"; at summary, its first sentence; at silent, nothing.
  Markdown is read as words: a code block is "Code block omitted", and headings and list items
  are read as separate sentences. Turn it off in Settings with "Read your own messages back when
  they're sent" (Alt+M), and you hear just "Sent. Hub probe is working."
- **Notifications** while you're in another window: when one of The Chat Place's own
  sessions finishes a turn, fails or needs you (a permission or a question), when a desktop app
  session starts needing you, and when the loaded session finishes. Choosing one brings
  The Chat Place forward with that session loaded. Settings, Windows notifications (on a Mac,
  Notifications) chooses every finished turn of its own sessions (the default), only when a
  session needs you, or off. While you're in The Chat Place (or one of its dialogs), the
  announcement is enough and none are shown.
  - On Windows they're ordinary Windows notifications from The Chat Place's icon in the
    notification area: read by your screen reader, and quiet under Do Not Disturb. Choosing the
    icon itself brings The Chat Place forward.
  - On a Mac they're macOS notifications, in Notification Center and under Focus like any other.
    macOS asks once whether The Chat Place may send them (System Settings, Notifications changes
    that). Each one remembers its own session, so choosing an older one still opens the right
    session.
- **Changed Files** (Ctrl+Shift+D, View menu) lists the files Claude changed since your latest
  message, or in the whole session, each with its line counts ("main_frame.py, 40 lines added, 12
  removed, in thechatplace\ui"). Enter on a file reads its changes in a text box, a line at a
  time: where each change is, then "Removed:", "Added:" and "Unchanged:" lines. It's built from the
  transcript, so it works for desktop app sessions too, with no git needed. Changes made by a
  subagent Claude hands work to, and notebook edits, aren't counted yet. When the loaded
  session's turn ends, the announcement (at the full level) is followed by a one-line summary:
  "Changed 3 files: main_frame.py, 40 lines added, 12 removed; …".
- **Usage and Context** (Ctrl+Shift+U, View menu) says how full the loaded session's context is
  ("Context 62% full: 124,000 of 200,000 tokens"), from the token counts of Claude's latest
  reply (the percentage only once the window's size is known: Claude Code reports it for a model
  when one of The Chat Place's sessions runs a turn on it, and a session past 200,000 tokens has the
  1,000,000 window), and how much of your plan's limits are used, as the latest turn reported them ("5-hour
  limit 8% used, resets at 10:00 AM. Weekly limit 34% used, resets on Friday at 9:00 AM.").
  It's said once, unasked, when the loaded session's context passes 80%, when a limit passes
  90% or is reached, and when Claude Code compacts a conversation (the messages list shows
  "Conversation compacted" too). A turn that fails on a usage limit says so in plain words,
  with when it resets.
- **Turn Status** (Ctrl+Shift+T) says how long Claude has been working on the current turn and what
  it last did. There's no time limit on a turn; Stop (Ctrl+Period) ends it, along with anything it
  started, such as a build.
- **Claude Code Sign-in** (Help menu) says whether Claude Code is signed in, to which plan and
  as whom ("Claude Code is signed in to your Claude Max plan as …"). If it isn't, it offers to
  sign in: `claude auth login` opens in its own window and your browser shows Claude's sign-in
  page. The Chat Place also checks at start-up and says so only if there's a problem. Your
  sessions are listed whether or not Claude Code is signed in (they're read from disk); only
  sending a message needs a sign-in.
- **Report a Bug** (Help menu) asks for a summary, what happened, what you expected and the
  steps, and shows exactly what else the report includes before it goes anywhere: versions
  (The Chat Place, Windows, Python, wxPython, Claude Code), the announcement level and speech
  engine, the list's view and sort, and how many sessions it lists. Never a session's title,
  folder or messages. **Open on GitHub** copies the whole report and opens GitHub's new-issue
  page with it filled in; **Copy Report** only copies it. Filing on GitHub needs access to the
  repository; anyone else can Copy Report and email it to support@theideaplace.net.

## Install

You need Windows 10 or 11, or a Mac with Apple silicon, and **Claude Code installed with its
native installer and signed in** to a Claude subscription (the `claude` command, the same login
the desktop app uses).

**Windows.** Download `TheChatPlace-windows-Setup.exe` from the newest release on
[the releases page](https://github.com/kellylford/AIChat/releases) and run it.
It installs for you only, with no administrator rights, adds The Chat Place to the Start menu, and
starts it. The portable zip from the same release runs without installing, but doesn't update
itself.

The app is built for x64; Arm PCs run it under Windows's x64 emulation.

**Mac.** Download `TheChatPlace-macos-arm64.dmg` from the same release, open it, and drag
The Chat Place onto Applications (or anywhere you like: it updates itself wherever it is). The
disk image is signed and notarized, so it opens without a warning. The first time speech goes through VoiceOver, macOS asks whether The Chat Place may
control VoiceOver; allow it, and turn on "Allow VoiceOver to be controlled with AppleScript" in
VoiceOver Utility, General. Your sessions and settings are in
`~/Library/Application Support/TheChatPlace`.

## Updates

The installed app checks for a new version a few seconds after it starts, and whenever you choose
Help, Check for Updates. At start it only speaks up when there is a new version, and then only
says so: it never opens a dialog you didn't ask for. From Help it always says what it found ("up to
date", "no release has been published yet", or an error), even with announcements set to silent.

From Help, a new version is offered in a Yes/No dialog where No is the default. If you choose Yes,
it downloads the update, closes, and starts the new version. It won't install while Claude is
working in one of its sessions, and it warns you if a reply box holds text you haven't sent. If a
turn starts, a dialog opens, or you type a reply while it downloads, it asks again or leaves the
update to be installed the next time The Chat Place starts.

The Mac app updates the same way. Velopack's updater is inside the app itself, so it works
wherever you keep it.

**Updating never touches your sessions or settings.** On Windows the app lives in
`%LOCALAPPDATA%\TheChatPlace`, which Velopack replaces on update and removes on uninstall, and
your data is in `%APPDATA%\TheChatPlace`. On a Mac, Velopack replaces the app itself, and your
data is in `~/Library/Application Support/TheChatPlace`. The updater refuses to run if the data
were ever inside what it replaces. What the updater did is logged in `update.log` in the data
folder.

The version is in Help, About. Releases come from tags named `v<version>`, and
each release carries two Velopack update feeds, `windows` (`releases.windows.json`) and `osx`
(`releases.osx.json`). The updater finds the newest `v*` release in this repository itself
and reads the feed from that release only (`REPO_URL`, `RELEASES_API`, `TAG_PREFIX` and `CHANNEL`
in `thechatplace/updater.py`).

## Run from source (development)

You need Python 3.11 to 3.13 (wxPython has wheels for those). The repo's virtual environment is
`.venv` (ignored by git). The setup scripts make it, install everything the app, the tests and
the build need (`requirements-build.txt`), and check it all imports, as Image Description
Toolkit's do. Each replaces an existing `.venv`.

| | Set up | Run | Test |
|---|---|---|---|
| Windows | `winsetup.bat` | `.venv\Scripts\pythonw TheChatPlace.pyw` | `.venv\Scripts\python -m pytest tests` |
| Mac | `./macsetup.sh`, or double-click `macsetup.command` | `.venv/bin/python -m thechatplace` | `.venv/bin/python -m pytest tests` |

`python -m thechatplace` works on Windows too. A copy run from source doesn't update itself; Help, Check
for Updates says so, and names the newest release.

### Build it yourself

The build scripts are in `BuildAndRelease/`, laid out as in Image Description Toolkit:
`MacBuilds/` and `WinBuilds/`. Each does what the release workflow's job for that platform does:
makes `.venv` if it isn't there, runs the tests, builds the app with PyInstaller, smoke-tests it,
and packs it with Velopack, whose tool `vpk` needs the .NET SDK (the scripts install `vpk` at the
version the workflow uses). Results go in `releases\` and `dist\`; give a folder to copy the
installer or disk image there too, relative to where you ran the script.

**Windows.** `BuildAndRelease\WinBuilds\build_windows.cmd`, from a command prompt or by
double-clicking (the window then stays open to read the result). It makes the installer and
portable zip, **unsigned**: Windows signing is Azure Artifact Signing, which only the workflow
does, so SmartScreen may warn when you run Setup (More info, then Run anyway). Without the .NET SDK
it builds just the app, says why, and exits with an error.

```
BuildAndRelease\WinBuilds\build_windows.cmd
BuildAndRelease\WinBuilds\build_windows.cmd C:\Users\kelly\OneDrive\thehub
```

**Mac.** `BuildAndRelease/MacBuilds/build_macos.sh`, or double-click `build_macos.command`. It
makes `releases/TheChatPlace-macos-arm64.dmg` and the `osx` update feed, for Apple silicon. Like
IDT's, a local Mac build is **signed** with your Developer ID Application certificate when the
keychain has one; notarizing is up to you. The .NET SDK comes from `brew install dotnet`.

```
BuildAndRelease/MacBuilds/build_macos.sh                    signed if you have the certificate
BuildAndRelease/MacBuilds/build_macos.sh ~/Desktop/builds   and copy the .dmg there
TCP_SIGN_CODE=0 BuildAndRelease/MacBuilds/build_macos.sh    unsigned
TCP_NOTARIZE=1 BuildAndRelease/MacBuilds/build_macos.sh     signed and notarized (credentials: notarize.sh)
```

The Mac build follows GHManage's: the app is signed inside-out (`sign.sh`), `vpk pack` adds
Velopack's updater (`UpdateMac`) and signs that and the bundle, and the disk image is made from
the packed app, never from `dist/`. An app without `UpdateMac` runs perfectly and never updates
again, so the build checks that Velopack inside the packed app finds its updater. An unsigned
disk image's README.txt says how to open it (System Settings, Privacy & Security, Open Anyway).

### Releasing

The version lives in one place, `__version__` in `thechatplace/__init__.py`. To release:

1. Set `__version__`, and write `release-notes/v<version>.md` (what it is, what's new, downloads,
   requirements), in one commit on main.
2. Tag it `v<version>` and push the tag.

`.github/workflows/release-thechatplace.yml` then builds both platforms side by side, and
publishes one GitHub release (a pre-release before 1.0) only if both succeed:

- **Windows:** runs the tests, fails if the tag and `__version__` disagree, builds the app with
  PyInstaller, smoke-tests the built exe, signs it with Azure Artifact Signing, packs the Velopack
  installer, portable zip and update feed (signing Setup, the updater and the launcher too), and
  checks every signature.
- **Mac:** runs `build_macos.sh` with the Developer ID certificate in a throwaway keychain, so the
  app is signed, packed with its updater and notarized, the disk image notarized and stapled, and
  Gatekeeper's verdict checked. It needs the repository secrets `MACOS_CERTIFICATE_P12`,
  `MACOS_CERTIFICATE_PASSWORD`, `NOTARY_KEY_P8`, `NOTARY_KEY_ID` and `NOTARY_ISSUER_ID`, which
  `The-Idea-Place-Projects/signing/sync-secrets.py` sets from the signing kit; a tag fails without
  them rather than publish an unsigned app.

Run by hand or for a pull request, it does everything but publish, and keeps the files as
workflow artifacts; tick "sign" on a hand run, or label a pull request `sign-build`, to sign (and
notarize) and check them too.

## Keyboard shortcuts

The same list is in the app under Help, Keyboard Shortcuts (F1), as a page with a heading and a
table for each group, so you can move by heading and read each key with what it does. Alt+P
shows it as plain text instead.

| Where | Key | What it does |
|---|---|---|
| Anywhere | Tab, Shift+Tab | Session list, messages, reply box, and back |
| Anywhere | Ctrl+1, Ctrl+2, Ctrl+3 | Go to the session list, the messages, the reply box |
| Anywhere | F6, Shift+F6 | Next or previous part: session list, messages, reply box, status bar |
| Anywhere | Ctrl+9 | Go to the status bar; Left and Right move between its parts |
| Messages, reply box or status bar | Escape | Back to the session list, on the same session |
| Messages | Backspace | Also back to the session list |
| Session list | Enter | Load that session and move to its messages |
| Session list | Ctrl+O | Open the selected session in the Claude desktop app |
| Session list | Ctrl+N | New Chat Place session |
| Session list | Ctrl+G | Add the selected session to a group |
| Session list | Ctrl+F | Show only sessions matching some text (Escape shows all) |
| Messages | Ctrl+F, F3, Shift+F3 | Find a message by its text; next; previous |
| Anywhere | Ctrl+E | Export the session to a file |
| Reply box | Ctrl+/ | Insert a slash command or skill |
| Anywhere | Ctrl+Shift+F | Attach files or images to the next message |
| Anywhere | Ctrl+Shift+D | Changed files, and each change to read by line |
| Anywhere | Ctrl+Shift+U | Usage and context: how full the context is, and plan limits |
| Anywhere | Alt+V, H | Show Sessions: choose which sessions are listed |
| Anywhere | Ctrl+Shift+N | Continue the selected (or loaded) desktop app session here, as a copy |
| Session list | F5 | Refresh the list now and put it in order |
| Session list | Delete | Hide the selected session (View, Show Sessions, Hidden lists it; File, Bring Back Session returns it) |
| Session list | Shift+Delete | Delete one of The Chat Place's own sessions permanently, after you confirm |
| Messages | Enter, or Applications key then Read Full Message | Read the whole message; Escape comes back to it |
| Messages | Ctrl+C | Copy the whole message |
| Messages | Ctrl+Shift+C | Copy the message's last code block |
| Messages | Ctrl+T | Show or hide tool activity |
| Messages | Ctrl+O | Open this session in the Claude desktop app |
| Reply box | Ctrl+Enter | Send (Chat Place sessions only); you stay in the reply box |
| Reply box | Ctrl+Period | Stop the running turn |
| Reply box | Ctrl+Shift+T | Turn status: how long it has been working, and on what |
| Anywhere | Ctrl+Shift+A | Answer Claude: a permission request, a question or a plan |
| Anywhere | F1 | Keyboard shortcuts |
| Anywhere | Ctrl+Comma | Settings |
| Anywhere | Ctrl+Shift+R | Repeat the last announcement |
| Anywhere | Alt+F4 | Quit |

Menus are File (Alt+F), View (Alt+V) and Help (Alt+H). Controls have their own Alt letters
(Alt+L the session list, Alt+M the messages, Alt+Y the reply box, Alt+D Send), and none of them
takes a menu's letter.

## How it works

Everything it reads is on your own PC, so reading costs nothing.

| What | Where |
|---|---|
| The desktop app's sessions | `%APPDATA%\Claude\claude-code-sessions\<id>\<org>\local_<id>.json`: title, folder, last activity, archived, and sometimes a summary of the last turn that says whether it needs you. Archived sessions are left out. The Microsoft Store version of the desktop app keeps the same files in `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude-code-sessions`; both places are read, and a session in both is read from the newer copy. |
| Whether a session is working | `%USERPROFILE%\.claude\sessions\<pid>.json`, which says busy or idle while Claude Code runs it. Files whose process has gone are ignored. |
| The conversation | `%USERPROFILE%\.claude\projects\<folder>\<session>.jsonl`, where `<folder>` is the session's folder with every character that isn't a letter or digit turned into `-`. This was checked against every transcript on Kelly's PC; if it ever misses, the app searches all the project folders for the session id instead. |
| The Chat Place's own sessions | `%APPDATA%\TheChatPlace\sessions.json` (and `speech.json` for settings). If `sessions.json` can't be read, it's renamed to `sessions.json.bad-<date>` rather than overwritten, and the app says so. |
| Errors | `%APPDATA%\TheChatPlace\error.log`: anything that went wrong unexpectedly, with its traceback |

None of these formats is documented, and Claude Code says the transcript format changes between
versions. So all the knowledge of it is in one small module (`thechatplace/transcript.py`) that
skips record types it doesn't know, never crashes on a line it can't read, and says "couldn't read
N lines" instead. A long transcript is read once, then only its new lines as it grows.

**The Chat Place never writes to the desktop app's files or to any transcript.** The only files it
writes are its own, in `%APPDATA%\TheChatPlace`. Only one copy runs at a time; starting a second
brings the first to the front.

### Its own sessions, and why desktop sessions are read-only

The Chat Place drives its own sessions with the `claude` command in print (headless) mode:
`claude -p --input-format stream-json --output-format stream-json --verbose --permission-mode <mode>
--permission-prompts host --permission-prompt-tool stdio`, with `--session-id` and `--name` for the
first message and `--resume <id>` for each reply, plus `--allowedTools` with any rules you chose
"for this session". The message goes in on standard input as a stream-json message, and standard
input stays open for the turn so The Chat Place can answer what Claude asks; it's closed when the
turn's result arrives. That runs under the same login as the desktop app, never an API key; it
uses the plan's Agent SDK credit, as any `claude -p` does.

- It never uses `--bare`, which needs an API key.
- It needs the native `claude.exe`. The npm install's `claude.cmd` is refused, because Windows runs
  a `.cmd` through `cmd.exe`, which would let characters in a session title run a command.
- Before starting `claude` it removes two named sets of environment variables, and keeps the rest
  (your `CLAUDE_CODE_GIT_BASH_PATH`, `CLAUDE_CONFIG_DIR`, proxy and timeout settings). The first set
  is what a Claude session puts in the environment of anything started inside it: started from
  there, the app would otherwise pass on variables that point `claude` at the desktop app's local
  proxy and tell it someone else will refresh its sign-in, and the run then waits for a refresh
  that never comes. The second is anything that would move billing off the subscription:
  `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, and the Bedrock, Vertex and
  Foundry switches. Both lists are in `claude_cli.py`.
- As a second check, `claude` reports where its credentials came from before it sends anything.
  If that's an API key rather than the subscription login, The Chat Place stops the run and says so.

Desktop app sessions are read-only because two programs resuming one session run their turns into
the same transcript at once and tangle it. Only the desktop app writes to its sessions, and only
The Chat Place writes to its own. The rule is enforced in code: The Chat Place refuses to build a
`--resume` command for any session it didn't start, any session the desktop app knows about
(archived ones included), or any `local_` id, and there are tests for each. It also won't send
into one of its own sessions while that session is running somewhere else. Continue Here is the
one exception that reads a desktop session through `claude`, and it doesn't write to it:
`--resume <desktop id> --fork-session --session-id <new id>` copies the history into a new
session. Checked with Claude Code 2.1.286: the desktop session's transcript was byte for byte the
same afterwards, and Claude knew the earlier conversation. One turn runs at a time
per session. Send during a turn queues the message: The Chat Place says "Queued", and once the
turn's reply has been announced, it sends the message. More messages sent while one is waiting
join it, and they go together as one message. Each queued message is at the end of the
messages list as "Queued: …": Delete removes it, and its context menu has Send Now (Ctrl+Enter:
Claude stops what it's doing and answers it straight away, in the same turn), Edit Queued Message
(back into the message box, to change and send again) and Remove Queued Message. Turn status
(Ctrl+Shift+T) says when a message is queued. If the turn fails, or you press Stop, the queued text goes back in the message box
instead, ahead of anything typed since, with the cursor left at the end. While one of
The Chat Place's sessions is loaded, Send and Stop are never disabled, so from the message box, Tab
is always Send and the next Tab is always Stop. When a turn is running, Tab doesn't jump past
Send to Stop.

Every announcement is also written to `speech.log` in `%TEMP%\thechatplace-speak` (on a Mac,
`$TMPDIR/thechatplace-speak`), one line each: the time, whether it interrupts or waits its turn,
the speech engine, and its opening words. A line means the text was handed to the speech engine,
not that it was heard: a later announcement that interrupts can cut it off. The log shows
whether a reply went to the screen reader at all when you didn't hear it.

A turn runs `claude` in a Windows job object, so Stop, or quitting the app, ends `claude` and every
program it started (a build or test run, say), not just `claude` itself. The same happens when a
turn finishes normally: anything Claude started and left running, such as a development server,
ends with the turn. (Ask Claude to start long-running servers in a terminal of your own instead.)
`claude` is started suspended and only let run once it's in the job, so nothing it starts can
slip out first.

### What headless sessions do with questions and permissions

Checked with Claude Code 2.1.286 (issues #187 and #188):

- **Permission prompts, questions and plans come to The Chat Place.** With
  `--permission-prompts host --permission-prompt-tool stdio`, anything that would ask arrives on
  the turn's output as a `can_use_tool` request, the same control protocol the Agent SDK uses,
  and the turn waits for the answer on its input. AskUserQuestion and ExitPlanMode come the same
  way: a question is answered by allowing the tool with the answers added to its input, a plan
  is approved by allowing it with a switch of permission mode, and Keep Planning denies it with
  your note. Each was checked against the real CLI: an allowed Write wrote its file; a denied
  one didn't, and Claude quoted the reason it was given; an approved plan carried on in accept
  edits without asking again.
- **Refusals still happen without asking** where Claude Code's own rules say so (a write outside
  the session's folder, say, or auto mode's safety check). The Chat Place adds those to the
  announcement ("1 tool was refused: ..."), marks the session "needs you", and the chat shows a
  "Permission denied" line.
- Question cards in desktop app sessions are shown as text in the chat ("Claude asked: ...,
  Options: ...", then "You answered: ...") and answered in Claude.

## Limitations

- The Mac version is new and hasn't had a full pass with VoiceOver. Edit boxes, lists and
  choices have their names under VoiceOver, as under JAWS and NVDA. But the text a screen reader
  reads for each row of the messages list (the whole message) uses MSAA, which wxPython has only
  on Windows, so VoiceOver reads the row's own text instead. The OS-specific parts are in
  `thechatplace/platform_paths.py`, `thechatplace/ui/a11y.py`, `thechatplace/ui/mac_a11y.py` and
  the speech scripts.
- "Needs you" for desktop sessions depends on the desktop app's turn summary, which it doesn't
  always write. A session without one shows as idle once it stops working.
- A desktop session's transcript can be gone if it's older than Claude Code's retention period
  (`cleanupPeriodDays`, 90 days on Kelly's PC). The chat says so.
- The Chat Place's own sessions don't appear in the desktop app, so Open in Claude doesn't work for
  them; the app says so.
- Subagent conversations are left out of the chat.
- Turns of The Chat Place's own sessions are also spoken by ClaudeSpeak's Stop hook, if that's
  installed, since `claude -p` runs hooks; so a reply can be heard twice.
- The desktop app's file formats are undocumented and could change with any update.

## Files

| Path | What |
|---|---|
| `TheChatPlace.pyw` | Double-click launcher |
| `thechatplace/transcript.py` | Transcript parser |
| `thechatplace/sessions.py` | Desktop metadata, live state, sorting, the list wording |
| `thechatplace/own_store.py` | The Chat Place's own sessions |
| `thechatplace/claude_cli.py` | `claude` commands, the `--resume` guard, the environment, stream-json events, running a turn |
| `thechatplace/hub.py` | Gathering the list, noticing finished turns |
| `thechatplace/announce.py` | What gets announced |
| `thechatplace/rendering.py` | A message's markdown as a safe HTML page, for the formatted view |
| `thechatplace/speech.py`, `thechatplace/speech/` | Speech, adapted from Image Description Toolkit (ClaudeSpeak's engine scripts) |
| `thechatplace/platform_paths.py` | Every path and OS call |
| `thechatplace/ui/` | The wxPython window and dialogs |
| `tests/` | pytest tests, built on made-up records shaped like the real ones |
| `thechatplace/updater.py` | Velopack updates, adapted from GHManage's updater |
| `tools/check_version.py` | Prints the version; checks a release tag against it |
| `tools/make_version_info.py` | The Windows version resource for the built exe |
| `winsetup.bat`, `macsetup.sh` (`.command`) | Set up `.venv` on Windows or a Mac |
| `BuildAndRelease/WinBuilds/build_windows.cmd` | Build on Windows (unsigned) |
| `BuildAndRelease/MacBuilds/` | Build on a Mac (`build_macos.sh`, `.command`), and its signing, notarizing, entitlements and disk image |
| `requirements-build.txt` | Everything a build needs; pins PyInstaller |
| `release-notes/` | One file per release, used as the GitHub release's notes and the update's notes |
