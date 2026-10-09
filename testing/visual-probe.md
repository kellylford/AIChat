# The visual probe

The probe (#155) opens every screen of The Chat Place on made-up data, and saves a
picture of each with a JSON description of its controls. Claude then reviews the
pictures against a checklist and describes them in words. That's how the app's look is
checked without anyone needing to see it.

## What it photographs

`python tools/ui_probe.py --list` lists the surfaces:
- the main window in several states (as it opens, an own session, mid-turn, a desktop
  session, tool activity, the Last message column, an update waiting, no sessions);
- every dialog, opened through its own menu command wherever the made-up data allows;
- the formatted view (shortcuts, user guide, a message with a heading, list, code, table
  and link).

`tests/test_ui_probe.py` fails if a dialog class has no surface, so a new dialog has to
be added to the probe.

The data is the hidden-window tests' (`tests/fake_env.py`): no real sessions, no real
`%APPDATA%`, no real `claude`, no speech.

## Windows: in the test VM

The probe shows real windows, and the variants change Windows' theme and scaling, so it
runs in the ClaudeTesting VM, never on a PC someone is using. From the repo:

```
vmtest begin
powershell -File tools\ui_probe_vm.ps1                       # every variant
powershell -File tools\ui_probe_vm.ps1 -Variant light-100 -Surface settings,permission
vmtest save                                                  # when done for now
```

The variants are in `tools/ui_probe_plan.json`: light at 100, 150 and 200% scaling, dark
apps, and High Contrast Aquatic and Desert. `tools/ui_probe_guest.ps1` sets each one
inside the VM, runs the probe, and puts the display back. It refuses to run outside a
virtual machine.

The first run installs Python 3.12 and the app's packages in the VM, which takes a few
minutes. The pictures come back to a new folder under `%TEMP%\tcp-ui-probe`.

## macOS: by hand

On a Mac, from the repo with its `.venv`, and with Screen Recording allowed for the
terminal (System Settings, Privacy & Security, Screen Recording):

```
.venv/bin/python tools/ui_probe.py --out ~/Desktop/tcp-probe --tag mac-light
```

Switch to Dark appearance and run it again with `--tag mac-dark`.

## Reviewing a run

Ask Claude to review the run folder with `tools/ui_review_prompt.md`. It gives each
picture a PASS, FAIL or UNSURE verdict, writes the description of each surface in
`testing/visual/descriptions.md`, and lists each defect once, to file as an issue.

The probe's own flags are in each `manifest-<tag>.json` (`problems`): text smaller than
it needs, controls overlapping, controls outside the window. They're measured, so treat
them as findings to confirm in the picture, not opinions.
