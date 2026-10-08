# Potential Feature Requests for The Chat Place

Based on the user guide and codebase analysis, here are feature requests that would enhance The Chat Place:

## High Priority (User Experience Impact)

### 1. Subagent Conversations Support
**Current state:** Subagent (sidechain) conversations are excluded from the transcript view.

**User impact:** When Claude uses subagents for complex work, users can't follow that work in The Chat Place. They only see the summary result.

**Suggested improvement:** Display subagent conversations as a sub-thread or collapsible section within the parent message, so users can see the agent's reasoning and work.

**File reference:** `thechatplace/transcript.py:26` - currently skips these records

---

### 2. Transcript Status and Completeness Indicator
**Current state:** The app silently handles missing or incomplete transcripts but doesn't clearly indicate which sessions have them.

**User impact:** Users may have sessions they think are complete but are actually missing portions (e.g., due to cleanup period or offline time).

**Suggested improvement:**
- Add a visual/audio indicator (badge, icon, or note) when a session's transcript is incomplete
- Show in the session row or in a tooltip: "Transcript incomplete: records from before October 1 are archived"
- Option to view the available transcript even if incomplete

**File reference:** `thechatplace/sessions.py` - session metadata handling

---

### 3. Global Search Across All Sessions
**Current state:** `Ctrl+F` searches within the loaded session's messages. Search in the session list only searches titles, folders, and group tags.

**User impact:** Users with many sessions can't quickly find where something was discussed across all conversations (e.g., "Which session did we discuss database migration?").

**Suggested improvement:**
- Add `Ctrl+Shift+F` or a separate "Find in all sessions" feature
- Search message content across all loaded transcripts
- Show results as a list with session name, time, and context snippet
- Keyboard navigation between results

**Files involved:** `thechatplace/transcript.py`, `thechatplace/ui/main_frame.py`

---

## Medium Priority (Nice to Have)

### 4. Session Creation Quick Links
**Current state:** Creating a new session requires `Ctrl+N`, then navigating through a dialog.

**User impact:** Users who frequently create sessions in the same folder have to repeat folder selection.

**Suggested improvement:**
- Remember recently used folders and show them as quick-pick buttons
- Add "New Session in [Current Folder]" to the context menu
- Remember the last model/permission mode choice per folder

---

### 5. Transcript Retention/Archiving Strategy
**Current state:** Sessions older than 90 days are cleaned up by Claude Code without warning.

**User impact:** Users don't know when they'll lose access to a session they thought was archived.

**Suggested improvement:**
- Show the expected cleanup date for each session
- Offer a way to manually export/archive sessions before cleanup
- Option to mark sessions as "don't cleanup" (if possible through Claude Code integration)

---

### 6. Keyboard Shortcut Discoverability
**Current state:** Full shortcuts list is only in Help (F1) or the README.

**User impact:** New users might not know shortcuts exist, or discover them accidentally.

**Suggested improvement:**
- Show a mini-tooltip or hint for the next available shortcut when first launching ("Tip: Tab moves between panels, Ctrl+F finds sessions, F1 for more")
- Highlight shortcuts in context menus (e.g., "Send (Ctrl+Enter)")
- Configurable "show tips" setting

---

## Lower Priority (Polish)

### 7. Session Duplication
**Current state:** "Continue Here" forks a desktop session; you can manually export and re-import, but there's no simple "duplicate this session" option.

**User impact:** Users experimenting with different approaches need to re-create setup work.

**Suggested improvement:**
- Add "Duplicate Session" option that copies the entire conversation and lets you rename it
- Confirm before duplicating (could be large)

---

### 8. Message Threading/Branching
**Current state:** All messages are linear; no way to explore "what if I had said X instead of Y".

**User impact:** Users can't easily test alternatives without losing context of the original path.

**Suggested improvement:** Low priority—complex feature, would require significant UI changes

---

### 9. Customizable Announcement Triggers
**Current state:** Announcements are full/summary/silent, applied globally or to open session.

**User impact:** Some users might want announcements for specific sessions only (e.g., "notify me when Build finishes, but not when News finishes").

**Suggested improvement:**
- Per-session announcement level
- Notification filters by session tag or group

---

## Known Limitations (Not Bugs)

These are documented limitations that are by-design:

- **Mac VoiceOver:** The Mac version is new and hasn't had a full VoiceOver pass. This is in progress.
- **Desktop Session Read-Only:** Desktop sessions can't be edited here by design (to prevent transcript tangling).
- **Subagent Conversations:** Currently excluded; this is noted in the README.
- **File Format Stability:** Desktop app's file formats are undocumented and could change; The Chat Place is designed to handle this gracefully.

---

## Reporting Bugs vs. Feature Requests

Users and contributors can file these using:
- **GitHub Issues:** For bugs or well-defined feature requests with strong use cases
- **Help, Report a Bug:** For unexpected behavior or crashes
- **Email:** support@theideaplace.net for feedback

Include version number (`Help, About`), OS, steps to reproduce (for bugs), and the use case (for features).
