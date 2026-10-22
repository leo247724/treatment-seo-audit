#!/usr/bin/env python3
"""Compare the two most recent audit snapshots for one site.

    python diff_runs.py <host>

Reads out/<host>/history/<YYYY-MM-DD>/findings.json. With two or more
snapshots it compares the latest with the one before it; with only one it
compares that snapshot with the current out/<host>/findings.json. Prints new,
resolved and impact-changed findings plus the top-5 before/after, writes
out/<host>/history/<latest>/diff.md and ends with a one-line summary:

    <host>: +N new, -M resolved, K changed

Standard library only. Always exits 0.
"""
import json
import os
import re
import sys

CHANGE_THRESHOLD = 0.20  # relative impact change that counts as "changed"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def norm_host(arg):
    h = arg.strip().lower()
    if "://" in h:
        h = h.split("://", 1)[1]
    h = h.split("/", 1)[0].split(":", 1)[0]
    return h[4:] if h.startswith("www.") else h


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"warning: cannot read {path}: {e}", file=sys.stderr)
        return None
    if isinstance(data, dict):
        data = data.get("findings", [])
    return [x for x in data if isinstance(x, dict) and x.get("id")] if isinstance(data, list) else None


def impact(f):
    try:
        return float(f.get("impact") or 0)
    except (TypeError, ValueError):
        return 0.0


def top5(findings):
    return sorted(findings, key=impact, reverse=True)[:5]


def short(text, n=90):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def main(argv):
    if len(argv) < 2:
        print("usage: diff_runs.py <host>")
        print("?: +0 new, -0 resolved, 0 changed (no host given)")
        return 0
    host = norm_host(argv[1])
    base = os.path.join("out", host)
    hist = os.path.join(base, "history")

    snaps = []
    if os.path.isdir(hist):
        snaps = sorted(d for d in os.listdir(hist)
                       if DATE_RE.match(d) and os.path.isfile(os.path.join(hist, d, "findings.json")))

    if len(snaps) >= 2:
        old_label, new_label = snaps[-2], snaps[-1]
        old_path = os.path.join(hist, old_label, "findings.json")
        new_path = os.path.join(hist, new_label, "findings.json")
    elif len(snaps) == 1:
        old_label, new_label = snaps[0], "current"
        old_path = os.path.join(hist, snaps[0], "findings.json")
        new_path = os.path.join(base, "findings.json")
    else:
        print(f"{host}: +0 new, -0 resolved, 0 changed (no snapshots in {hist})")
        return 0

    old, new = load(old_path), load(new_path)
    if old is None or new is None:
        print(f"{host}: +0 new, -0 resolved, 0 changed (missing or unreadable findings.json)")
        return 0

    old_by = {f["id"]: f for f in old}
    new_by = {f["id"]: f for f in new}
    added = sorted((new_by[i] for i in new_by.keys() - old_by.keys()), key=impact, reverse=True)
    resolved = sorted((old_by[i] for i in old_by.keys() - new_by.keys()), key=impact, reverse=True)
    changed = []
    for i in new_by.keys() & old_by.keys():
        a, b = impact(old_by[i]), impact(new_by[i])
        if a == b:
            continue
        rel = abs(b - a) / abs(a) if a else float("inf")
        if rel >= CHANGE_THRESHOLD:
            changed.append((new_by[i], a, b, rel))
    changed.sort(key=lambda t: abs(t[2] - t[1]), reverse=True)

    lines = [f"# Audit diff: {host}", "",
             f"Compared `{old_label}` (before) with `{new_label}` (after).", ""]

    def section(title, rows):
        lines.extend([f"## {title} ({len(rows)})", ""])
        lines.extend(rows or ["None."])
        lines.append("")

    section("New findings", [f"- **{f['id']}** (impact {impact(f):g}, severity {f.get('severity', '?')}, "
                             f"{f.get('page_count', '?')} pages): {short(f.get('title'))}" for f in added])
    section("Resolved findings", [f"- **{f['id']}** (was impact {impact(f):g}): {short(f.get('title'))}"
                                  for f in resolved])
    section(f"Impact changed by {int(CHANGE_THRESHOLD * 100)}% or more",
            [f"- **{f['id']}**: {a:g} -> {b:g} ("
             + ("new non-zero" if rel == float("inf") else f"{(b - a) / a * 100:+.0f}%")
             + f"): {short(f.get('title'))}" for f, a, b, rel in changed])

    before, after = top5(old), top5(new)
    lines.extend(["## Top 5 before / after", "", "| # | Before | After |", "|---|---|---|"])
    for n in range(5):
        cell = lambda lst: (f"{lst[n]['id']} ({impact(lst[n]):g})" if n < len(lst) else "")
        lines.append(f"| {n + 1} | {cell(before)} | {cell(after)} |")
    lines.append("")

    summary = f"{host}: +{len(added)} new, -{len(resolved)} resolved, {len(changed)} changed"
    lines.extend([f"Summary: {summary}", ""])
    report = "\n".join(lines)

    target_dir = os.path.join(hist, snaps[-1])
    try:
        with open(os.path.join(target_dir, "diff.md"), "w", encoding="utf-8") as f:
            f.write(report)
    except OSError as e:
        print(f"warning: cannot write diff.md: {e}", file=sys.stderr)

    print(report)
    print(summary)
    return 0


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception as e:  # never fail the scheduler
        print(f"diff_runs.py error: {e}", file=sys.stderr)
        host = norm_host(sys.argv[1]) if len(sys.argv) > 1 else "?"
        print(f"{host}: +0 new, -0 resolved, 0 changed (diff error)")
    sys.exit(0)
