# The Chat Place User Guide

The Chat Place is a keyboard and screen reader friendly home for your Claude Code chats. It lists
the sessions the Claude desktop app has, shows each one as a conversation you can arrow through,
tells you when a session answers, and can run sessions of its own that you read and reply to
entirely from here.

This guide starts with the everyday things and goes deeper as it goes on. Each part has its own
heading, so your screen reader's heading keys move between them. For every key in one list, use
Help, Keyboard Shortcuts (F1).

The Chat Place is an independent project by Kelly Ford. It works with Claude Code and the Claude
desktop app, but it isn't made, sponsored or endorsed by Anthropic, and isn't affiliated with it.

## Before you start

You need:

- Windows 10 or 11, or a Mac with Apple silicon.
- Claude Code, installed with its native installer and signed in to your Claude subscription.
  This is the `claude` command, using the same sign-in as the Claude desktop app. The npm version
  of Claude Code isn't used.

The Chat Place never uses an API key. Reading sessions costs nothing, because everything it reads
is on your own computer. Messages you send in its own sessions are Claude Code turns, which count
against your plan's monthly Agent SDK credit; past that credit, turns stop unless you've turned on
extra usage, which is billed. View, Usage and Context (Ctrl+Shift+U) says where you stand.

### Installing

**Windows:** download `TheChatPlace-windows-Setup.exe` from the newest release on the
[releases page](https://github.com/kellylford/AIChat/releases) and run it. It installs for you
only, needs no administrator rights, adds The Chat Place to the Start menu, and starts it. The
portable zip from the same release runs without installing, but doesn't update itself.

**Mac:** download `TheChatPlace-macos-arm64.dmg`, open it, and drag The Chat Place onto
Applications. The first time it speaks through VoiceOver, macOS asks whether The Chat Place may
control VoiceOver: allow it, and turn on "Allow VoiceOver to be controlled with AppleScript" in
VoiceOver Utility, General.

If Claude Code isn't signed in, your sessions are still listed; only sending a message needs a
sign-in. Help, Claude Code Sign-in says whether it is signed in, and offers to sign you in if not.

## The window

The window has three parts, in Tab order:

1. The **session list**: every session, one per line.
2. The **messages** of the session you've loaded.
3. The **reply box**, with Send and Stop. For a Claude desktop app session, the same place holds
   a short note saying why you reply in Claude, with Open in Claude and Continue Here buttons.

Tab and Shift+Tab move between them, and Ctrl+1, Ctrl+2 and Ctrl+3 go straight to each one. F6
and Shift+F6 move between the parts and the **status bar**, which holds whatever was said last;
Ctrl+9 goes straight to the status bar. Escape in the messages or the reply box takes you back to
the session list, on the same session.

## Reading a session

### Finding it in the list

Each line in the session list reads the session's title, its folder, its state (needs you,
working or idle) and when it was last active, for example: "Fix the release build, QuickMail,
needs you: Choose a version number, active 1 minute ago".

By default, sessions that need you come first, then the ones that are working, then the rest,
newest first. The list refreshes itself every few seconds. While you're in it, rows stay where
they are, so nothing moves under you; F5 puts the list back in order.

To find one session among many, press **Ctrl+F** in the list and type part of its title, its
folder or what it needs. The list shows only the matches, and its name says so ("Session list,
matching "build", 3 of 139"). Escape shows them all again.

### Loading it

Arrowing through the list doesn't load anything. Press **Enter** on a session to load it: you move
to its messages and hear, for example, "Loaded Fix the build, 12 messages." Pressing Enter on the
session that's already loaded takes you back to where you were in it.

### Reading the messages

The newest message is last, and you start on it. Each line shows "You:" or "Claude:" and the
message's first line, but your screen reader reads the **whole message** as you arrow onto it.
Headings and list items are read as sentences, and a code block is read as what it is, such as
"Code block, Python, 14 lines". If you'd rather hear just the first line, turn that off in
Settings, Reading messages.

Press **Enter** on a message to read it as a formatted page. There, your screen reader's browse
mode moves by heading (H), table (T), list (L) and code block (each code block is a region, so R
moves to it). Links open in your browser. **Read as Plain Text** (Alt+P) shows the message in a
plain text box instead, to read by line, word and character. Escape closes either one and puts
you back on the same message. On Windows the formatted page needs Microsoft's Edge WebView2
runtime, which comes with Windows 11; without it, the plain text box opens.

Other things you can do with a message:

- **Ctrl+C** copies the whole message.
- **Ctrl+Shift+B** lists the message's code blocks, by language and size, with each one's code to
  read and a Copy button for just that block. **Ctrl+Shift+C** copies the last code block at once.
- **Ctrl+F** finds a message containing some text, searching each message's whole text. F3 and
  Shift+F3 find the next and previous match.
- The Applications key (or Shift+F10) opens the message's menu.

Claude's questions to you appear as "Claude asked: …" followed by "You answered: …". Tools Claude
was refused appear as "Permission denied: …".

### Seeing what Claude is doing

Claude's tool calls and their results are hidden until you turn on **Show Tool Activity**
(Ctrl+T). With it on, the open session's tool calls are also spoken as they happen, so a long turn
isn't silent: "Using Bash: git status; Read: main.py." A run of calls is gathered up and said
together ("Using Read 4 times, then Bash."), and it never cuts off your screen reader.

## Desktop app sessions and The Chat Place's own

There are two kinds of session in the list, and what you can do differs.

**Claude desktop app sessions** are read-only here. You can read them, find in them, export them
and see what they changed, but you reply in the desktop app. That's deliberate: if two programs
both worked in one session at the same time, its conversation would get tangled. **Open in Claude**
(Ctrl+O) switches the desktop app to the session, to answer it, approve a permission or answer a
question card.

**The Chat Place's own sessions** are ones you start here. You read and reply to them entirely in
The Chat Place, and they don't appear in the desktop app.

If you'd like to carry on a desktop app session here, use **Continue Here** (Ctrl+Shift+N, or the
button beside Open in Claude). It makes a new Chat Place session in the same folder, with the
whole conversation so far, and you type its first message. Its title starts as the original's,
followed by "(continued)". The desktop app session isn't changed, and what you do in the copy
doesn't appear in it.

## Starting a session and replying

### A new session

Press **Ctrl+N** (File, New Session) and fill in:

- **Folder:** the project folder Claude works in. It starts in your GitHub folder if you have one,
  otherwise your home folder.
- **Title:** optional; without one, it's made from the first words of your message.
- **Model:** Default (your Claude Code setting), Opus, Sonnet or Haiku, each the latest of its
  kind. File, Change Model changes it later, from the next turn. Fable isn't offered, because on
  some plans it bills to usage credits without asking; if a turn would run on Fable anyway, The
  Chat Place stops it before anything is sent, and says why.
- **Permission mode:** how much Claude may do without asking. Auto, the default, lets Claude
  decide what's safe to run. Accept edits lets it change files without asking. Manual asks before
  anything that needs approval. Plan has Claude make a plan, without changing anything, for you
  to approve.
- **First message:** what you'd like Claude to do.

If the first message never reaches Claude (Claude Code isn't signed in, for example), it goes back
into the reply box, and Send starts the session again.

### Replying

In one of The Chat Place's own sessions, type in the reply box and press **Ctrl+Enter** (or Send).
You stay in the reply box, and you hear what was sent and where, such as "Sent to Fix the build:
Run the tests." When Claude finishes, its answer is announced.

While Claude is working, you can still send. Your message is queued ("Queued for Fix the build:
…"), shown at the end of the messages as "Queued: …", and sent once the current turn finishes.
On a queued message, Ctrl+Enter sends it now (Claude answers it straight away, in the same turn),
and its menu can also edit or remove it. **Stop** (Ctrl+Period) ends the turn, and anything it
started, such as a build; a queued message then goes back into the reply box.

**Ctrl+Shift+T** (Turn Status) says how long Claude has been working on this turn and what it last
did. There's no time limit on a turn.

### Commands, skills and attachments

These are for The Chat Place's own sessions:

- **Ctrl+/** (or the Commands button) lists your skills and slash commands, then Claude Code's
  own, such as /compact and /context, each with its description. Type to filter, Down to the list,
  Enter to choose: it goes at the start of the reply box, ready to finish and send.
- **Ctrl+Shift+F** (or Attach Files) adds files and pictures to your next message, and **Ctrl+V**
  in the reply box attaches a picture on the clipboard, such as a screenshot. The attachments are
  listed under the reply box, and Delete there removes one. Claude sees pictures as pictures, and
  reads other files from where they are.

## When Claude needs you

In one of The Chat Place's own sessions, when Claude needs a permission, asks you a question, or
has a plan for you to approve, the turn waits for you. You hear it ("Fix the build needs you.
Claude wants to run git push. Ctrl+Shift+A answers."), and the session shows as "needs you" in
the list. Press **Ctrl+Shift+A** to answer:

- **A permission:** read the whole request (the command, or the file and what would change), then
  choose **Allow**, **Deny**, or, when Claude Code suggests a rule, **Allow for this session**,
  named in full ("don't ask again this session for Bash(git push:*)"). Deny is the default button,
  so pressing Enter by mistake never allows anything, and you can give a reason Claude reads.
- **A question:** each question is a group of choices, with Other and a box for your own answer.
  Send Answers, or Don't Answer.
- **A plan:** read it (Read Formatted shows it as a page, by heading), then **Approve**, choosing
  how Claude carries on, or **Keep Planning**, the default, with what to change.

**Escape answers later.** Nothing is allowed or refused by waiting: the turn keeps waiting, and
Ctrl+Shift+A brings the same request back. "Allow for this session" lasts for the rest of that
session, not just the turn. The Chat Place never changes Claude Code's own settings files.

For a desktop app session, a "needs you" means the desktop app's summary of its latest turn says
it's waiting on you. Answer it in the desktop app (Ctrl+O). The desktop app doesn't write that
summary after every turn, so a desktop session can be waiting on you and still show as idle.

## Organizing your sessions

With many sessions, these keep the list manageable.

### Choosing which sessions are listed

**View, Show Sessions** (Alt+V, H) chooses what the list shows: all sessions; the ones that need
you or are working; just the ones that need you; desktop app sessions; The Chat Place's own;
Remote Control sessions; ungrouped sessions; archived ones; hidden ones; or one of your groups.
**View, Sort Sessions** (Alt+V, O) chooses the order: by status, newest first, oldest first, by
title, or by folder. Both choices are remembered.

### Groups

A group collects related sessions, such as everything for one project or everything you're
waiting to hear back on, so you can show just those.

- **Ctrl+G** (File, Add to Group) puts the selected session in a group, or in a new one.
- File, Remove from Group takes it out.
- File, Manage Groups lists your groups, with how many sessions each has, to make, rename or
  delete them. Deleting a group never deletes its sessions.

A session can be in several groups, and its line in the list says which ("group Work"). To see
one group, choose it in View, Show Sessions. Ungrouped, in the same menu, lists the sessions that
aren't in any group yet.

The desktop app's own groups show here too: in View, Show Sessions, in each session's line, and in
Add to Group. They can only be changed in the desktop app. Choosing one of them in Add to Group
makes a Chat Place group of the same name, which is shown together with the desktop app's.

### Renaming, hiding and deleting

- **F2** renames the selected session. One of The Chat Place's own sessions is renamed outright.
  A desktop app session's new name shows only here, since the desktop app's files are never
  changed; clear the name to go back to the desktop app's.
- **Delete** hides a session without changing it. View, Show Sessions, Hidden lists hidden
  sessions, and File, Bring Back Session returns one.
- **Shift+Delete** deletes one of The Chat Place's own sessions permanently, conversation and all,
  after you confirm (No is the default). Desktop app sessions can only be hidden here; delete
  those in the desktop app.

On a Mac laptop, Delete and Shift+Delete are Fn+Delete and Fn+Shift+Delete.

The session's menu (the Applications key or Shift+F10 in the session list) has all of these, and
the other commands for the selected session.

## Announcements and notifications

When the open session gets a reply, when one of The Chat Place's sessions finishes a turn, or when
any listed session stops working, it's announced through your screen reader (or a system voice)
and put on the status bar. **Ctrl+Shift+R** repeats the last announcement.

**Settings** (Ctrl+Comma) chooses how much is said:

- **Full** reads the whole reply.
- **Summary** reads the session's name and the reply's first sentence.
- **Silent** puts it on the status bar only.

Settings also chooses whether every listed session is announced or just the open one, which
speech engine and rate to use, and whether your own messages are read back when they're sent.

When you're in another window, The Chat Place can show a notification when one of its sessions
finishes a turn, fails or needs you, or when a desktop app session starts needing you. Choosing
the notification brings The Chat Place forward with that session loaded. Settings, Windows
notifications (on a Mac, Notifications) chooses every finished turn (the default), only when a
session needs you, or off. While you're in The Chat Place, the announcement is enough and no
notification is shown.

## More things you can do

- **Changed Files** (Ctrl+Shift+D) lists the files Claude changed since your latest message, or in
  the whole session, with how many lines were added and removed. Enter on a file reads its changes
  line by line. It works for desktop app sessions too.
- **Usage and Context** (Ctrl+Shift+U) says how full the session's context is ("Context 62% full:
  124,000 of 200,000 tokens") and how much of your plan's limits are used. It's also said once,
  unasked, when the context passes 80%, or a limit passes 90%.
- **Export** (Ctrl+E) saves a session's conversation as Markdown, a web page or plain text.
- **What Claude Knows About You** (Ctrl+Shift+K) lists what Claude Code keeps about you: your
  instructions (CLAUDE.md files), the memories it saved, your skills, subagents, commands and
  settings. Enter reads one, and Edit in Your Editor opens it in your own editor.
- **Remote Control** (File, Remote Control) lets you reach one of The Chat Place's sessions from
  claude.ai and your phone while a turn runs. Turning it on copies the conversation to claude.ai,
  where it stays, and anyone signed in to your account there can type into it. Settings can make
  it the default for The Chat Place's sessions.

## Updates

The installed app checks for a new version shortly after it starts, and says so only if there is
one. **Help, Check for Updates** asks right away and offers to install it (No is the default). It
won't install while Claude is working in one of its sessions, and it warns you about a reply you
haven't sent. Updating never touches your sessions or settings.

## When something isn't right

**I don't see a session I expected.** Check View, Show Sessions: you may be showing only some
sessions, and archived and hidden sessions aren't in All. A Find (Ctrl+F) also narrows the list;
Escape in the list clears it. F5 refreshes the list at once. Only Claude Code sessions are
listed, not the desktop app's ordinary chats.

**I can't reply to a session.** It's a desktop app session. Press Ctrl+O to answer it in the
desktop app, or Ctrl+Shift+N to continue it here as a copy.

**Claude is waiting and nothing is happening.** It may need you: press Ctrl+Shift+A. Ctrl+Shift+T
says what the turn is doing.

**A turn stopped with a usage limit.** The announcement says which limit and when it resets.
Ctrl+Shift+U shows how much of each limit is used.

**An old session's messages are gone.** Claude Code deletes old conversations after a while (its
`cleanupPeriodDays` setting). The session can still be listed, and the messages list says its
conversation is no longer there.

**A reply is spoken twice.** If you've installed ClaudeSpeak, its hook also speaks The Chat
Place's turns.

**Something else.** Help, Report a Bug asks what happened and shows exactly what the report
includes before it goes anywhere: version numbers and settings, never your sessions' titles,
folders or messages. Open on GitHub files it; Copy Report copies it, to email to
support@theideaplace.net.

## Good to know

- The Chat Place never writes to the desktop app's files or to any conversation. The only files it
  writes are its own: on Windows in `%APPDATA%\TheChatPlace`, on a Mac in
  `~/Library/Application Support/TheChatPlace`. The conversations themselves are Claude Code's.
- The Mac version is new, and hasn't had a full pass with VoiceOver yet. In particular, VoiceOver
  reads each line of the messages list as shown, not the whole message; Enter still opens the
  whole message.
- Conversations Claude hands to a subagent aren't shown.
- The desktop app's file formats aren't documented, so a desktop app update could change what The
  Chat Place can read.

For every keyboard shortcut, see Help, Keyboard Shortcuts (F1), or the
[keyboard shortcuts page](https://github.com/kellylford/AIChat/blob/main/docs/keyboard-shortcuts.md).
The [README](https://github.com/kellylford/AIChat#readme) has the full details of everything here.
