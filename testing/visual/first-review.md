# The first visual review (#155)

The first look at The Chat Place's screens, taken on 2026-10-10 with the visual probe
(`tools/ui_probe.py`, run through `tools/ui_probe_vm.ps1` in the test VM). It covered 34
surfaces in six Windows variants, 204 pictures in all:
- light at 100, 150 and 175% scaling;
- dark mode for apps;
- High Contrast Aquatic (dark) and Desert (light).

Agents reviewed each variant against `tools/ui_review_prompt.md`, opening every picture and
measuring colours from its pixels. `descriptions.md` beside this file says what each screen
looks like.

## What it found

| Issue | What | Where |
|---|---|---|
| #175 | Status bar buttons are 16 pixels tall and need 23, so the bottoms of letters are cut off ("needs vou", "readv") | Every main-window picture, every variant |
| #176 | Long labels run off the dialog's edge: the Remote Control check box, Report a Bug's note (the support address is hidden), Session List Columns' intro, Usage's first row. Question and Settings have large empty bands | settings, bug-report, session-columns, usage, question |
| #177 | Windows dark mode isn't followed: the app stays light, and only the formatted pages turn dark, inside light dialogs | Every dark-100 picture |
| #178 | Continue Here's Title box opens scrolled to its end and its About box cuts a line in half; New Session's Folder box is cramped | continue-here, new-session |
| #179 | The split between the session list and the session moves with the status text (378, 326, then 268 pixels), and status bar fields cut mid-word | main-own, main-desktop, main-own-working |
| #180 | The Last message column (#146) is out of sight at the default window size | main-last-message |
| #181 | Both lists show the same blue selection; only a faint dotted outline (1.89:1) says which has focus | Every main-window picture, light and dark |
| #182 | A first run shows an empty white list and no word on how to start | main-empty |
| #185 | The app isn't DPI aware, so Windows stretches it at 150% and 175% and text is soft | light-150, light-175 |
| #186 | At 175% on a 1080-pixel screen, tall dialogs run under the taskbar and their buttons can't be seen | new-session, continue-here, bug-report, about-you, plan and the formatted pages at 175% |

Noted, not filed:
- **The messages list:** it shows a message's first line as written, so a heading reads "Claude: ## What changed".
- **Attachments:** the attachment list has no visible label (it has an accessible name).
- **Window titles:** in High Contrast Desert they are faint, but that is Windows drawing an inactive title bar, not the app.

A formatted message's code block lost its edge under High Contrast, because a background colour
was all that marked it. The phase 3 change of #155 gives it a border there.

## What passed

- **Contrast:** every text and background pair measured passes WCAG AA in light, dark (the
  formatted pages) and both High Contrast themes. The lowest app-drawn pair is white on the
  selection blue, at 4.53:1.
- **High Contrast:** both themes reach every part of the app, including the custom-drawn status
  bar, list selection and the formatted pages.
- **Rendering:** no screen is blank, and none shows stray `&` marks, mojibake or placeholder
  text.

## The probe's own mistakes, found and fixed along the way

- **High Contrast themes:** the first runs used the wrong ones. Their files name themselves only
  by resource strings, so the probe now finds each by its window colour.
- **Window size at 150%:** the main window was forced to 1000 by 720 and ran under the taskbar.
  It now fits the screen, as the app sizes itself.
- **A formatted page photographed blank:** the probe now waits until the page shows more than one
  colour.
- **A turn in progress said "idle":** it now refreshes first, as the app's timer would.
