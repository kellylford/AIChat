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
    # A text box's label is its text (wx on Windows), which is content, not
    # identity: keyed by class and name, its text is compared separately.
    if control["class"] == "TextCtrl":
        return control["class"], control["name"], ""
    return control["class"], control["name"], control["label"]


def _name(key) -> str:
    cls, control_name, label = key
    shown = label or control_name
    if len(shown) > 60:
        shown = shown[:57] + "..."
    return f"{cls} {shown!r}"


def layout_changes(old: dict, new: dict) -> list:
    """What changed between two descriptions, in words."""
    changes = []
    if old.get("title") != new.get("title"):
        changes.append(f"title {old.get('title')!r} became {new.get('title')!r}")
    if old.get("size") != new.get("size"):
        changes.append(f"window size {old.get('size')} became {new.get('size')}")
    before, after = {}, {}
    for control in old.get("controls", []):
        before.setdefault(_key(control), []).append(control)
    for control in new.get("controls", []):
        after.setdefault(_key(control), []).append(control)
    for key in list(before) + [k for k in after if k not in before]:
        olds, news = before.get(key, []), after.get(key, [])
        # Controls sharing a key (several unnamed panels) are paired in
        # order; any left over were added or removed.
        for b in news[len(olds):]:
            problems = "; ".join(b.get("problems", []))
            changes.append(f"{_name(key)} is new" + (f" ({problems})" if problems else ""))
        for _a in olds[len(news):]:
            changes.append(f"{_name(key)} is gone")
        for a, b in zip(olds, news):
            changes.extend(_control_changes(_name(key), a, b))
    return changes


def _control_changes(name: str, a: dict, b: dict) -> list:
    changes = []
    ax, ay, aw, ah = a["rect"]
    bx, by, bw, bh = b["rect"]
    if max(abs(ax - bx), abs(ay - by)) > MOVE_TOLERANCE:
        changes.append(f"{name} moved from ({ax}, {ay}) to ({bx}, {by})")
    if max(abs(aw - bw), abs(ah - bh)) > MOVE_TOLERANCE:
        changes.append(f"{name} went from {aw}x{ah} to {bw}x{bh}")
    if a.get("enabled") != b.get("enabled"):
        changes.append(f"{name} is now {'enabled' if b.get('enabled') else 'disabled'}")
    if a["class"] == "TextCtrl":
        if (a.get("label"), a.get("value")) != (b.get("label"), b.get("value")):
            changes.append(f"{name}'s text changed")
    elif a.get("value") != b.get("value"):
        changes.append(f"{name}'s value went from {a.get('value')!r} to {b.get('value')!r}")
    if a.get("items") != b.get("items"):
        changes.append(f"{name}'s items changed")
    if a.get("selection") != b.get("selection"):
        changes.append(f"{name}'s selection moved from {a.get('selection')} to "
                       f"{b.get('selection')}")
    for problem in b.get("problems", []):
        if problem not in a.get("problems", []):
            changes.append(f"{name}: now {problem}")
    return changes


def pixel_change(old_png: Path, new_png: Path, diff_png: Path | None = None) -> float:
    """The share of compared pixels that differ (1.0 if the sizes differ).
    Writes a picture of where, if asked: changed pixels red over a pale copy.
    Rows that match byte for byte are skipped, which is most of them."""
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
    stride = width * 3
    changed_at = []
    # The window's outer border is Windows' drawing over whatever is behind
    # it (a screen copy at 150% and above), not the app's: not compared.
    for y in range(EDGE, height - EDGE):
        row = y * stride
        if a[row:row + stride] == b[row:row + stride]:
            continue
        for x in range(EDGE, width - EDGE):
            i = row + x * 3
            if (abs(a[i] - b[i]) > CHANNEL_TOLERANCE
                    or abs(a[i + 1] - b[i + 1]) > CHANNEL_TOLERANCE
                    or abs(a[i + 2] - b[i + 2]) > CHANNEL_TOLERANCE):
                changed_at.append(i)
    if diff_png is not None and changed_at:
        grey = bytes(new.ConvertToGreyscale().GetData())
        marks = bytearray(200 + v * 55 // 255 for v in grey)
        for i in changed_at:
            marks[i:i + 3] = b"\xff\x00\x00"
        diff_png.parent.mkdir(parents=True, exist_ok=True)
        wx.Image(width, height, bytes(marks)).SaveFile(str(diff_png), wx.BITMAP_TYPE_PNG)
    compared = max(1, (width - 2 * EDGE) * (height - 2 * EDGE))
    return len(changed_at) / compared


def _manifests(folder: Path) -> list:
    """The folder's probe manifests: manifest-<tag>.json, or manifest.json
    from a run without --tag."""
    if not folder.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("manifest*.json"))]


def _stem(surface: str, tag: str) -> str:
    return f"{surface}-{tag}" if tag else surface


def _stems(folder: Path, tags=None) -> set:
    """The screens a run (or the baseline) has, by its manifests' own surface
    names and tags, so no tag is matched by how a name ends. Only ``tags``,
    if given. A folder without manifests: its JSON files."""
    manifests = _manifests(folder)
    if not manifests:
        # No manifests to say which variant each picture is: go by the name.
        stems = {p.stem for p in folder.glob("*.json")} if folder.is_dir() else set()
        return {s for s in stems if tags is None or any(s.endswith(f"-{t}") for t in tags)}
    return {_stem(surface, m.get("tag", "")) for m in manifests
            if tags is None or m.get("tag", "") in tags for surface in m.get("surfaces", {})}


def _failed(run: Path) -> dict:
    """stem -> the error the probe reported for it (a page that never drew,
    the wrong dialog, an exception): never compared, never accepted."""
    failed = {}
    for data in _manifests(run):
        for surface, entry in data.get("surfaces", {}).items():
            if entry.get("error"):
                failed[_stem(surface, data.get("tag", ""))] = \
                    entry["error"].strip().splitlines()[-1]
    return failed


def compare(run: Path, baseline: Path) -> dict:
    tags = {m.get("tag", "") for m in _manifests(run)} or None
    run_stems = _stems(run)
    # Only the variants this run took: a run of light-100 alone isn't missing
    # the other variants' pictures.
    base_stems = _stems(baseline, tags)
    # And only the surfaces a partial run (--surface) set out to take. A
    # complete run that lacks one is missing it: it's gone from the probe.
    if any(m.get("complete") is False for m in _manifests(run)):
        base_stems &= run_stems
    failed = _failed(run)
    shutil.rmtree(run / "diff", ignore_errors=True)  # an earlier comparison's
    result = {"failed": {s: failed[s] for s in sorted(failed)},
              "new": sorted(run_stems - base_stems - set(failed)),
              "missing": sorted(base_stems - run_stems), "unchanged": [], "changed": {}}
    for stem in sorted((run_stems & base_stems) - set(failed)):
        if not (run / f"{stem}.json").exists():
            result["failed"][stem] = "no description in the run"
            continue
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
             f"{len(result['new'])} new, {len(result['missing'])} missing, "
             f"{len(result['failed'])} failed.", ""]
    if result["failed"]:
        lines.append("## Failed in this run (not compared: run them again)")
        lines.extend(f"- **{stem}**: {why}" for stem, why in result["failed"].items())
        lines.append("")
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
    failed = _failed(run)
    stems = names or sorted(_stems(run))
    refused = {stem: failed[stem] for stem in stems if stem in failed}
    if refused:
        raise SystemExit("Not accepted: the probe reported these as failed. Run them again.\n" +
                         "\n".join(f"  {stem}: {why}" for stem, why in refused.items()))
    # Everything is checked before anything is copied, so a name that isn't
    # in the run leaves the baseline as it was.
    sources = [run / f"{stem}{suffix}" for stem in stems for suffix in (".png", ".json")]
    absent = [str(s) for s in sources if not s.exists()]
    if absent:
        raise SystemExit("Not accepted: not in the run:\n" + "\n".join(f"  {s}" for s in absent))
    baseline.mkdir(parents=True, exist_ok=True)
    if not names:
        # Accepting a whole run keeps its manifests: which Windows, scaling
        # and theme the baseline was taken in.
        for manifest in run.glob("manifest*.json"):
            shutil.copy2(manifest, baseline / manifest.name)
    for source in sources:
        shutil.copy2(source, baseline / source.name)
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
    # New screens alone pass: they have no baseline to differ from yet.
    return 1 if result["changed"] or result["missing"] or result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
