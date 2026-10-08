# The Chat Place User Guide

Welcome to The Chat Place, your keyboard- and screen-reader-friendly companion for Claude Code. This guide will walk you through everything you need to know to use the app effectively.

## What is The Chat Place?

The Chat Place is a desktop app that brings all your Claude Code sessions into one accessible place. Think of it as a home for your chats—it lists every session the Claude desktop app has open, shows you conversations you can read and scroll through, and lets you reply entirely from The Chat Place without switching windows.

You can also start your own sessions right from The Chat Place. They run with the same Claude subscription you use in Claude Code, and everything costs nothing to read (reading happens on your computer) but uses your plan's credits when you send messages.

### Why you'd use it

- **One place for everything.** See all your sessions at once, sorted how you like (by what needs you, newest first, by folder, or by a group you create).
- **Keyboard and screen reader friendly.** Everything is accessible with your keyboard and screen reader from JAWS, NVDA, or VoiceOver.
- **Works with what you have.** Read desktop app sessions at no cost. Start new sessions when you want to work in your own window instead of switching to Claude.
- **Groups.** Organize sessions into groups—work projects in one, experiments in another, ideas in a third—so you can focus on what matters right now.
- **Tools and permissions.** You control what Claude can do: approve each tool before it runs, or give blanket permission for a session or forever.
- **Offline-first design.** Everything except sending a message happens on your PC: no waiting, no uploads.

## Getting started

### Install

You need Windows 10 or 11, or an Intel Mac, and **Claude Code already installed and signed into a Claude subscription**.

- **Windows:** Download `TheChatPlace-windows-Setup.exe` from [the releases page](https://github.com/kellylford/AIChat/releases), run it, and you're done. It starts automatically.
- **Mac:** Download `TheChatPlace-macos-arm64.dmg`, open it, and drag The Chat Place into Applications.

### First launch

Open The Chat Place. You'll see:

1. **Session list** on the left—all your Claude Code sessions, sorted by what needs you first.
2. **Messages** in the middle—the conversation of whichever session you open.
3. **Reply box** on the right (or below)—where you type to send a message.

The list refreshes every few seconds, and everything else updates as Claude works.

The session list's name tells you what you're seeing: "Session list, needs you, 3 of 42" means you're looking at sessions waiting for you, and there are 42 total. If you see no sessions, the desktop app might not have any open, or you can start your own with **Ctrl+N**.

### Opening a session

Arrow down in the session list to find one you want to read. **Enter** loads it: the messages appear in the middle, focus moves there, and you hear "Loaded Build (idle, on Sonnet), 12 messages."

Arrow through the messages. Each message reads as you land on it: **"You: Fix the release build"** or **"Claude: I'll start by checking the current status."** Your screen reader reads the whole message by default (turn that off in Settings if you only want the first line).

To go back to the session list without loading a different session, **Escape** or **Backspace**.

## Common workflows

### Finding the session you need

You have a lot of sessions. Here's how to find the right one.

**Find by status (needs you first):** The default view shows sessions that need your attention first, then working ones, then idle. This is usually what you want: if something is stuck, it floats to the top. To change the sort, **Alt+V, O** (View menu, Sort Sessions).

**Find by search:** **Ctrl+F** in the session list opens a search. Type part of the title, folder, or what the session needs, and the list narrows down. **Escape** shows all again. This is handy when you have dozens of sessions and remember the folder name (like "build") but not the session title.

**Find by group:** Create a group for your daily work, your experiments, or your long-running jobs. When you focus on just one group, the list is shorter. **Ctrl+G** adds a session to a group (or creates a new one); **Alt+V, H** picks which group to view.

### Reading a message

In the messages list, arrow to a message and listen. Your screen reader reads the whole thing: headings, lists, code blocks ("Code block, Python, 14 lines").

For a long message, **Enter** (or **Shift+F10** then Read Full Message) opens it as a formatted page. Move by heading (**H**), list (**L**), table (**T**), and code block (**R**). **Escape** comes back to the list on the same message.

For code blocks, **Shift+F10** then Code Blocks lists them all, so you can pick the one you need and copy just that one without copying the whole message.

**Ctrl+Shift+C** copies the last code block straight away.

### Replying to your own session

If it's a session you started (not a desktop app session), **Tab** takes you to the reply box. Type your message, and **Ctrl+Enter** sends it.

While Claude is working, you can queue up another message by typing and pressing **Ctrl+Enter** again. The messages are marked "Queued" until Claude finishes and they go out together.

To stop Claude from working and make it answer your message right now, press **Ctrl+Enter** on the queued message while a turn is running.

### Approving permissions and answering questions

Claude sometimes needs you: to run a command, answer a question, or approve a plan. When that happens, The Chat Place announces it ("Build needs you. Claude wants to run npm ci. Ctrl+Shift+A answers.") and the session shows as needing you in the list.

**Ctrl+Shift+A** opens the answer dialog:

- **Permission request:** You see the command or file Claude wants to change. Approve it once, approve it for this session only ("Don't ask again this session for npm(ci)"), or deny it with a reason Claude will see. The default button is Deny—if you do nothing and **Escape**, it's denied.
- **Questions:** Each question is a set of options. Pick one or type your own; send your answers or don't.
- **Plans:** **Ctrl+Shift+A** shows the plan, and you can approve it (choosing whether to accept edits, run auto, or ask about each change) or keep planning with what to change.

Once you answer (or wait it out), focus goes back where it was. Nothing happens if you **Escape**—you answer later when you have time.

**For a desktop app session,** you can't reply here, but you can press **Ctrl+O** to open it in Claude. It shows up there with the context of what's been said so far, ready for you to answer.

### Watching Claude work

Claude sometimes shows what it's doing: Running Bash, Reading files, Looking things up. By default, this is silent unless something fails. Turn on **Ctrl+T** (Show Tool Activity) to hear each tool as Claude uses it: **"Using Bash: npm ci; Read: package.json; Then Write: config.js."**

For your own sessions, you also hear what Claude writes between tools—its thinking, its next step—so a long turn isn't silent.

In the messages, tool calls and results are hidden unless you turn on Show Tool Activity. Then you see them in the chat, so you can tell what Claude did and whether it worked.

## Organizing with groups

Groups are a powerful way to organize sessions, and they're easier than you might think.

### Creating and using groups

**Ctrl+G** with a session selected adds it to a group. You can pick an existing group or type a new name. Sessions can be in multiple groups.

Once you have some sessions in groups, **Alt+V, H** opens a menu to show all sessions, or just the ones in a group you pick. When you've been focusing on one group, switching back to "all" might show you've missed something, so the list jumps back to the default order (needs you first, newest first).

Group names are your own—call them "Today," "Blocked," "Websites," "LongTerm," or whatever makes sense to you.

### The Chat Place's groups and the desktop app's groups

The Chat Place has its own groups (stored on your computer). The desktop app also has groups. Both show up here:

- In **Alt+V, H** (Show Sessions), you can view The Chat Place's groups or the desktop app's groups.
- In each session's row, you see its groups.
- **Ctrl+G** shows both kinds, so you can add a session to either.

If you add one of The Chat Place's sessions to a desktop app group, The Chat Place automatically keeps a group of the same name on its side, so both stay in sync.

### Why groups matter

With 50 sessions, scrolling through the list to find the right one wastes time. But if you group them—"Work," "Ideas," "Long-term," "Done"—you can switch between those groups in seconds and see only what's relevant right now.

## Working with code

### Seeing what Claude changed

**Ctrl+Shift+D** lists the files Claude changed in the current turn (or the whole session, if you pick that option). It shows line counts: **"main.py, 12 lines added, 3 removed, in src"**.

**Enter** on a file opens a text box that reads the changes line by line. You get a clear picture of what Claude did.

### Copying code

**Ctrl+Shift+C** copies the message's last code block straight to your clipboard—no need to read the full message first. Paste it straight into your editor.

If there are multiple code blocks, open the message with **Enter**, move to the one you need, and **Shift+F10** then Code Blocks. Pick the one you want and Copy.

## Your own sessions

You can start sessions right from The Chat Place instead of using the desktop app.

### Creating a session

**Ctrl+N** opens the New Session dialog:

1. Pick a folder (The Chat Place defaults to your current project folder).
2. Give it a title.
3. Pick a model: Default (your Claude Code setting), or Opus, Sonnet, or Haiku.
4. Pick a permission mode (Auto is the default; you can also use Manual or Plan).
5. Type your first message.

The first message doesn't cost anything to cancel if Claude Code isn't signed in. If signing in fails, your message goes back in the reply box and you can try again.

Once Claude answers, you're in the messages list, and **Ctrl+Enter** sends the next message.

### Permission modes

- **Auto:** Claude can do anything safe by Claude Code's rules (you can't usually see the rules, but they block things like writing outside your project folder).
- **Manual:** You approve each tool before Claude runs it.
- **Plan:** Claude shows you its plan before it runs tools, and you can ask it to change the plan.
- **Accept edits:** Claude can run tools and edit files on its own, but shows you important changes afterward.

You can change the mode for the next turn in **File, Change Model**.

### Continuing a desktop session here

If you're working in the desktop app and want to switch to The Chat Place, **Ctrl+Shift+N** with the desktop session selected carries it on as a copy in The Chat Place. A new session starts with all the conversation so far, and you reply to it here. The desktop session is unchanged; they're separate from that point on.

## Settings and preferences

**Ctrl+Comma** opens Settings.

### Announcements

Choose how much you want to hear:

- **Full:** The whole reply, or the status ("Context 62% full").
- **Summary:** Just the session name and first sentence.
- **Silent:** Nothing spoken, just the status bar (read with **F6** or Ctrl+Shift+U).

### Reading messages

- By default, the full message is read as you arrow onto it. If you want just the first line, turn off "Read the whole message."
- Messages open as a formatted page (best for headings and tables) or plain text (best for reading by line).

### Attachments and files

Attach files with **Ctrl+Shift+F** (Attach Files button). Image files become images Claude can see; text files are named as `@"filename"`. You can also **Ctrl+V** to paste a screenshot.

Attachments stay with the session until you send the message. **Delete** in the attachments list removes one.

### Remote Control

If you want to reach your session from claude.ai or another device while a turn is running, turn on **File, Remote Control**. The session copies to claude.ai, and you can type into it from there. Between turns, it shows as offline.

## Understanding the status bar

**F6** or **Ctrl+9** brings up the status bar, which tells you:

- What was last announced ("Context 62% full").
- The loaded session and what it's doing ("Build (idle, on Sonnet)").
- How full the context is (for sessions running near their token limit).
- How many sessions need you (choose this to go to the first one that needs you).
- An available update (if one is ready to download).

**Left** and **Right** move between these parts. **Tab** leaves. Your screen reader's read-status-bar key reads all the parts at once.

## Advanced features

### Exporting a session

**Ctrl+E** saves a session to a file. Pick Markdown (best for editing), HTML (best for sharing), or plain text (best for reading by line). The file includes the whole conversation and the date.

### View code blocks

**Shift+F10** then Code Blocks in the messages list shows all code blocks in the message, with the selected one's code in a box below. **Copy** copies just that block, **Enter** opens it.

### Check your context size

**Ctrl+Shift+U** shows how full your context is: **"Context 62% full, 124,000 of 200,000 tokens."** It also shows your plan's usage limits. This is useful when you have a long session and Claude is running near the limit.

### Repeat the last announcement

**Ctrl+Shift+R** repeats what was last said. Useful if you missed it or want to hear it again.

## Tips and tricks

### Keyboard navigation

- **Tab** and **Shift+Tab** move through the three parts of the window (session list, messages, reply box) and cycle.
- **Ctrl+1, Ctrl+2, Ctrl+3** jump straight to the session list, messages, or reply box.
- **F6** and **Shift+F6** move to the next or previous part, including the status bar.

### Session list views

- Default shows sessions that need you first (great when you're playing catch-up).
- "Newest first" shows the one you just worked on at the top (great when you're in flow).
- "By folder" groups sessions by project folder (great when you're context-switching between projects).

### Searching vs. grouping

If you have five sessions in one folder and need to find one by title, search is faster. If you have 50 sessions across folders, groups are faster.

### Queued messages

While Claude is working, you can type your next message and queue it with **Ctrl+Enter**. It waits until the current turn finishes, then goes out. If you change your mind, **Delete** on the queued message removes it, or **Ctrl+Shift+T** shows you what's queued.

### Opening in Claude

- For a desktop app session, **Ctrl+O** switches to it in Claude (useful for approving permissions or answering questions).
- For your own session, The Chat Place is where you work—you can't edit it in Claude.

## Getting help

### Keyboard shortcuts

**F1** shows the full list of keyboard shortcuts. It's organized by section (Moving Around, Session List, Messages, etc.) so you can move by heading to find what you need.

### Settings

**Ctrl+Comma** opens Settings. Everything here is explained as you go through it.

### Reporting a bug

**Help, Report a Bug** (Alt+H) lets you describe what went wrong, what you expected, and the steps to reproduce it. The report includes your version, OS, and screen reader, but not your sessions or messages.

### Sign in

**Help, Claude Code Sign-in** shows whether Claude Code is signed in and to which plan. If it's not signed in, you can sign in right there.

## What's unique about The Chat Place

### It's read-only for desktop sessions

The Chat Place reads your desktop app sessions but never writes to them. This is intentional: if two programs write to one session at the same time, the conversation gets tangled. So if you want to reply to a desktop session, you either switch to Claude or use **Ctrl+Shift+N** to start a copy here.

### It keeps your own sessions on your PC

When you start a session in The Chat Place, it's stored on your computer (in `%APPDATA%\TheChatPlace` on Windows, `~/Library/Application Support/TheChatPlace` on Mac), not in the cloud. When you open it next time, it's there.

### It's independent of Anthropic

The Chat Place is made by Kelly Ford and is not affiliated with, endorsed by, or affiliated with Anthropic. It works with Claude Code and respects your subscription and login, but it's a separate project.

## Troubleshooting

### I don't see any sessions

- The Claude desktop app has to be open and have sessions. Open Claude and start a conversation, or wait for one to finish.
- If you have sessions in Claude but don't see them here, restart The Chat Place.

### I want to reply to a desktop app session

You can't reply directly—they're read-only to keep things from tangling. You can:

- **Ctrl+O** to open it in Claude and reply there.
- **Ctrl+Shift+N** to start a copy here, which becomes a new Chat Place session you can reply to.

### Claude isn't running my tool

- For a tool that asks, you didn't approve it fast enough. Ctrl+Shift+A to approve.
- For a permission denied, you denied it (or Claude Code's rules block it). The message says why.
- For a tool you expected but didn't see, turn on **Ctrl+T** (Show Tool Activity) so you can see what Claude tried and what was refused.

### I lost my sessions

Sessions are stored on your computer. They're not backed up automatically. If something goes wrong with your `%APPDATA%\TheChatPlace` folder (or the equivalent on Mac), you might lose them. Regular backups of that folder are a good idea if your sessions are important.

## Learning more

- **README.md** in the repository has the full technical details.
- **Keyboard Shortcuts** (F1) is a good reference once you get the basics.
- **Report a Bug** (Alt+H) is how to tell Kelly about problems or ideas.

---

**The Chat Place is in active development.** If you find something that doesn't work or think something should be there but isn't, please report it. You can file bugs on GitHub or email support@theideaplace.net with the report from the Help menu.
