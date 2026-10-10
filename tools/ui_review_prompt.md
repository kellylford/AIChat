# Reviewing a probe run (#155)

Give this to Claude with a probe run folder: the PNGs, their JSON descriptions and
`manifest-<tag>.json` for each variant. Claude looks at every picture itself (the Read
tool shows images), and writes two things.

The person reading the result can't see the screen. The words are all they get, so they
must say what is there, plainly and exactly.

## Ground rules

- **No screenshot, no claim.** Say only what is in a picture you opened. Never describe a
  screen from the code or the JSON alone.
- **The JSON is the measuring tape.** Use it for exact sizes, positions, labels, list
  contents and the probe's own flags (`problems`: text cut off, overlaps, outside the
  window). The picture is for what the JSON can't know: colours, contrast, how it reads
  as a whole.
- **Unsure is UNSURE.** If you can't tell, the verdict is UNSURE with what you'd need to
  decide. Never PASS by default.
- **Observations, not possibilities.** "The Send button's label is cut to 'Sen'" — not
  "labels might be truncated".
- **Measure contrast, don't eyeball it.** Sample the text and background colours from the
  picture (state the hex values) and give the WCAG ratio. Text needs 4.5:1 (3:1 if large),
  borders and focus indicators 3:1.

## 1. The checklist, for every picture

| # | Check | Fails when |
|---|---|---|
| 1 | Blank render | The window is empty, one colour, or the web view is white/black |
| 2 | Text cut off | A label, button or heading is clipped (JSON `text cut off`, or visible) |
| 3 | Overlap | Controls sit on top of each other (JSON `overlaps`, or visible) |
| 4 | Outside the window | A control runs past the window's edge |
| 5 | Contrast | Any text or focus indicator below the ratios above |
| 6 | Theme followed | In `dark-*`, `hc-*` or `mac-dark`, a part stays in light colours (or the reverse) |
| 7 | Focus visible | The focused control can't be told from the others |
| 8 | Stray text | `&` shown literally, mojibake, `None`, `{...}`, placeholder text |
| 9 | Expected content | What the surface's `about` says should be there isn't |
| 10 | Layout sense | Cramped, misaligned or oddly proportioned enough that a sighted user would notice |

Output, per picture, a JSON object in one array:

```json
{"file": "settings-light-100.png", "verdict": "PASS|FAIL|UNSURE",
 "failed": [5, 6], "note": "What you saw that failed, with numbers."}
```

Then a short summary: how many PASS/FAIL/UNSURE, and each distinct defect once (with
every picture it appears in), most serious first. Each distinct defect becomes its own
GitHub issue, citing #155 and the pictures.

## 2. A description of each surface (first review, and whenever a surface changes)

Write `testing/visual/descriptions.md`: one section per surface, from its `light-100`
picture, with a short note on how the other variants differ. For each:

- **Layout**, top to bottom and left to right: what is where, and roughly how much of the
  window each part takes ("the session list takes the left third, full height").
- **Sizes and spacing** in plain terms, with numbers from the JSON where they help.
- **Colours** by name ("white background, dark grey text, the selected row blue with white
  text"), and how the dark and High Contrast variants change them.
- **What looks off**: crowded, empty, misaligned, inconsistent with the other dialogs.

Plain sentences. Don't explain why something helps a screen reader user; say what it looks
like.

## 3. Comparing with the baseline (later phases)

For a surface whose picture or JSON changed against `testing/visual/baseline/`, say what
changed in words ("the Send button moved below the reply box; the reply box is 40 pixels
shorter"), then give the checklist verdict for the new picture.
