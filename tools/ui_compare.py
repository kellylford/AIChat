"""Compare a probe run with the baseline (#155): which screens changed, and how.

    python tools/ui_compare.py RUN_FOLDER [--baseline testing/visual/baseline/windows]
    python tools/ui_compare.py RUN_FOLDER --accept [surface-tag ...]

A screen has changed when its controls did (one added, gone, renamed, moved
or resized by more than a couple of pixels: exact, from the JSON, whatever
the fonts) or when its picture did (more than a sliver of pixels differing
by more than a little, which catches colour and theme changes the JSON
can't see). The report lists each changed screen with what changed in words,
and writes a picture of where its pixels differ to RUN_FOLDER/diff/.

--accept copies the run's pictures and descriptions into the baseline: all
of them, or the ones named (``settings-light-100``). Accept only after the
review (tools/ui_review_prompt.md, part 3) says the change is right.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = ROOT / "testing" / "visual" / "baseline" / "windows"

#: Pixels whose channels differ by no more than this count as the same
#: (anti-aliasing and ClearType move by a few levels between runs).
CHANNEL_TOLERANCE = 24
#: A picture changed when more than this share of its pixels did.
CHANGED_SHARE = 0.001
#: Controls that moved or grew by no more than this many pixels haven't.
MOVE_TOLERANCE = 2

#: Pixels at the picture's edge that aren't compared.
EDGE = 2

_app = None  # the wx.App pixel_change makes when run on its own


def _key(control: dict) -> tuple:
    return control["class"], control["name"], control["label"]


def layout_changes(old: dict, new: dict) -> list:
    """What changed between two descriptions, in words."""
    changes = []
    if old.get("title") != new.get("title"):
        changes.append(f"title {old.get('title')!r} became {new.get('title')!r}")
    if old.get("size") != new.get("size"):
        changes.append(f"window size {old.get('size')} became {new.get('size')}")
    before = {}
    for control in old.get("controls", []):
        before.setdefault(_key(control), []).append(control)
    after = {}
    for control in new.get("controls", []):
        after.setdefault(_key(control), []).append(control)

    def name(key):
        cls, control_name, label = key
        return f"{cls} {label or control_name!r}" if label else f"{cls} {control_name!r}"

    for key in before:
        if key not in after:
            changes.append(f"{name(key)} is gone")
    for key in after:
        if key not in before:
            changes.append(f"{name(key)} is new")
    for key in before:
        for a, b in zip(before[key], after.get(key, [])):
            ax, ay, aw, ah = a["rect"]
            bx, by, bw, bh = b["rect"]
            if max(abs(ax - bx), abs(ay - by)) > MOVE_TOLERANCE:
                changes.append(f"{name(key)} moved from ({ax}, {ay}) to ({bx}, {by})")
            if max(abs(aw - bw), abs(ah - bh)) > MOVE_TOLERANCE:
                changes.append(f"{name(key)} went from {aw}x{ah} to {bw}x{bh}")
            if a.get("items") != b.get("items") and "items" in a:
                changes.append(f"{name(key)}'s items changed")
            for problem in b.get("problems", []):
                if problem not in a.get("problems", []):
                    changes.append(f"{name(key)}: now {problem}")
    return changes


def pixel_change(old_png: Path, new_png: Path, diff_png: Path | None = None) -> float:
    """The share of pixels that differ (1.0 if the sizes differ). Writes a
    picture of where, if asked: changed pixels red over a faded copy."""
    import wx
    global _app
    if not wx.GetApp():
        # Kept: an App nobody holds is gone at once, and wx.Image needs one.
        _app = wx.App(False)
    old, new = wx.Image(str(old_png)), wx.Image(str(new_png))
    if old.GetSize() != new.GetSize():
        return 1.0
    a, b = bytes(old.GetData()), bytes(new.GetData())
    if a == b:
        return 0.0
    width, height = new.GetWidth(), new.GetHeight()
    changed = 0
    marks = bytearray(len(b))
    for i in range(0, len(b), 3):
        x, y = (i // 3) % width, (i // 3) // width
        # The window's outer border is Windows' drawing over whatever is
        # behind it (a screen copy at 150% and above), not the app's.
        edge = x < EDGE or y < EDGE or x >= width - EDGE or y >= height - EDGE
        if not edge and (abs(a[i] - b[i]) > CHANNEL_TOLERANCE
                         or abs(a[i + 1] - b[i + 1]) > CHANNEL_TOLERANCE
                         or abs(a[i + 2] - b[i + 2]) > CHANNEL_TOLERANCE):
            changed += 1
            marks[i:i + 3] = b"\xff\x00\x00"
        else:
            grey = 200 + (b[i] + b[i + 1] + b[i + 2]) // 3 * 55 // 255
            marks[i:i + 3] = bytes((grey, grey, grey))
    if diff_png is not None and changed:
        diff_png.parent.mkdir(parents=True, exist_ok=True)
        wx.Image(width, height, marks).SaveFile(str(diff_png), wx.BITMAP_TYPE_PNG)
    return changed / (width * height)


def compare(run: Path, baseline: Path) -> dict:
    run_names = {p.stem for p in run.glob("*.json") if not p.stem.startswith("manifest")}
    base_names = {p.stem for p in baseline.glob("*.json") if not p.stem.startswith("manifest")} \
        if baseline.is_dir() else set()
    # Only the variants this run took: a run of light-100 alone isn't missing
    # the other variants' pictures.
    tags = {p.stem[len("manifest-"):] for p in run.glob("manifest-*.json")}
    if tags:
        base_names = {n for n in base_names if any(n.endswith(f"-{tag}") for tag in tags)}
    result ={"new": sorted(run_names - base_names), "missing": sorted(base_names - run_names),
              "unchanged": [], "changed": {}}
    for stem in sorted(run_names & base_names):
        old = json.loads((baseline / f"{stem}.json").read_text(encoding="utf-8"))
        new = json.loads((run / f"{stem}.json").read_text(encoding="utf-8"))
        changes = layout_changes(old, new)
        share = 0.0
        if (baseline / f"{stem}.png").exists() and (run / f"{stem}.png").exists():
            share = pixel_change(baseline / f"{stem}.png", run / f"{stem}.png",
                                 run / "diff" / f"{stem}.png")
        if share > CHANGED_SHARE:
            changes.append(f"{share:.1%} of the picture's pixels changed"
                           if share < 1 else "the picture is a different size")
        if changes:
            result["changed"][stem] = changes
        else:
            result["unchanged"].append(stem)
    return result


def report(result: dict) -> str:
    lines = ["# Probe compared with the baseline", "",
             f"{len(result['changed'])} changed, {len(result['unchanged'])} unchanged, "
             f"{len(result['new'])} new, {len(result['missing'])} missing.", ""]
    if result["changed"]:
        lines.append("## Changed")
        for stem, changes in result["changed"].items():
            lines.append(f"- **{stem}**")
            lines.extend(f"  - {change}" for change in changes)
        lines.append("")
    for heading, key in (("New (no baseline yet)", "new"), ("Missing from this run", "missing")):
        if result[key]:
            lines += [f"## {heading}", *[f"- {stem}" for stem in result[key]], ""]
    return "\n".join(lines)


def accept(run: Path, baseline: Path, names) -> list:
    baseline.mkdir(parents=True, exist_ok=True)
    stems = names or sorted(p.stem for p in run.glob("*.json") if not p.stem.startswith("manifest"))
    if not names:
        # Accepting a whole run keeps its manifests: which Windows, scaling
        # and theme the baseline was taken in.
        for manifest in run.glob("manifest-*.json"):
            shutil.copy2(manifest, baseline / manifest.name)
    for stem in stems:
        for suffix in (".png", ".json"):
            source = run / f"{stem}{suffix}"
            if not source.exists():
                raise SystemExit(f"{source} isn't in the run")
            shutil.copy2(source, baseline / f"{stem}{suffix}")
    return stems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--accept", nargs="*", metavar="SURFACE-TAG",
                        help="copy these (or all) into the baseline")
    args = parser.parse_args(argv)
    if args.accept is not None:
        stems = accept(args.run, args.baseline, args.accept)
        print(f"Accepted {len(stems)} into {args.baseline}")
        return 0
    result = compare(args.run, args.baseline)
    text = report(result)
    (args.run / "compare.md").write_text(text, encoding="utf-8")
    print(text)
    return 1 if result["changed"] or result["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
