#!/usr/bin/env python3
"""
Auto-update directory types in submission_config.yaml based on last run results.

Strategy:
  401 / 404  →  manual     (needs auth or URL is dead)
  403        →  playwright  (bot-detection that a real browser may bypass)
  405        →  playwright  (JS form, POST endpoint wrong)
  200 failed →  playwright  (form validation needs JS)
  playwright failed → manual (nothing works automatically)

Uses text-level replacement so the YAML file's indentation and formatting
are 100% preserved — no ruamel.yaml dump() involved.
"""

import json
import re
import sys
from pathlib import Path

ROOT         = Path(__file__).parent.parent
RESULTS_PATH = ROOT / "results" / "submission_log.json"
CONFIG_PATH  = ROOT / "config" / "submission_config.yaml"

UPGRADE_TO_PLAYWRIGHT = {403, 405}
DOWNGRADE_TO_MANUAL   = {401, 404}


def _find_entry_bounds(raw: str, name: str) -> tuple[int, int] | None:
    """Return (start, end) byte offsets for the entry block named `name`."""
    escaped = re.escape(name)
    m = re.search(rf'\n\s*- name: "{escaped}"', raw)
    if not m:
        return None
    entry_start = m.start()
    rest = raw[m.end():]
    next_entry = re.search(r'\n\s*- name:', rest)
    entry_end = m.end() + (next_entry.start() if next_entry else len(rest))
    return entry_start, entry_end


def _apply_change(raw: str, name: str, new_type: str, new_notes: str | None) -> str:
    """Update type (and optionally add notes) for one entry, preserving all formatting."""
    bounds = _find_entry_bounds(raw, name)
    if bounds is None:
        print(f"  Warning: '{name}' not found in config — skipping")
        return raw

    start, end = bounds
    block = raw[start:end]

    # Detect field indentation from the dash line  ("  - name:" → field = "    ")
    indent_m = re.match(r'\n(\s*)- name:', block)
    dash_indent  = indent_m.group(1) if indent_m else '  '
    field_indent = dash_indent + '  '
    fi = re.escape(field_indent)

    # Replace the type value
    block = re.sub(rf'(\n{fi}type: )\S+', rf'\g<1>{new_type}', block)

    # Add notes line if requested and not already present
    if new_notes is not None and not re.search(rf'\n{fi}notes:', block):
        block = re.sub(
            rf'(\n{fi}type: \S+)',
            rf'\g<1>\n{field_indent}notes: "{new_notes}"',
            block,
        )

    return raw[:start] + block + raw[end:]


def main() -> None:
    # ── Collect submissions from all per-site result files ──────────────
    all_submissions: list[dict] = []
    for path in (ROOT / "results").glob("*/submission_log.json"):
        try:
            with open(path, encoding="utf-8") as f:
                all_submissions.extend(json.load(f).get("submissions", []))
        except Exception as e:
            print(f"  Warning: could not read {path}: {e}")

    if not all_submissions and RESULTS_PATH.exists():
        with open(RESULTS_PATH, encoding="utf-8") as f:
            all_submissions.extend(json.load(f).get("submissions", []))

    if not all_submissions:
        print("No results file — nothing to update.")
        return

    # ── Best result per directory across all sites ──────────────────────
    last: dict[str, dict] = {}
    for rec in all_submissions:
        name = rec["name"]
        existing = last.get(name)
        if not existing:
            last[name] = rec
        elif rec["status"] == "success" and existing["status"] != "success":
            last[name] = rec

    # ── Read config (raw text + simple YAML parse for current types) ────
    raw = CONFIG_PATH.read_text(encoding="utf-8")

    # Parse current name→type mapping from raw text (no yaml.load needed)
    current_types: dict[str, str] = {}
    for m in re.finditer(r'- name: "([^"]+)".*?\n\s+type: (\S+)', raw, re.DOTALL):
        current_types[m.group(1)] = m.group(2)

    current_notes: set[str] = set()
    for m in re.finditer(r'- name: "([^"]+)".*?\n\s+notes:', raw, re.DOTALL):
        current_notes.add(m.group(1))

    # ── Compute changes ─────────────────────────────────────────────────
    changes: list[tuple[str, str, str | None]] = []  # (name, new_type, new_notes)

    for name, current_type in current_types.items():
        if current_type == "manual":
            continue  # already lowest tier

        rec = last.get(name)
        if not rec or rec["status"] == "success":
            continue

        http = rec.get("http_status")
        new_type = None
        reason   = ""

        if http in DOWNGRADE_TO_MANUAL:
            new_type = "manual"
            reason   = f"HTTP {http}"
        elif http in UPGRADE_TO_PLAYWRIGHT or (rec["status"] == "failed" and current_type == "form"):
            new_type = "playwright"
            reason   = f"HTTP {http or 'error'}"
        elif rec["status"] == "failed" and current_type == "playwright":
            new_type = "manual"
            reason   = "Playwright also failed"

        if new_type and new_type != current_type:
            print(f"  {name:<35} {current_type} → {new_type}  ({reason})")
            new_notes = None
            if new_type == "manual" and name not in current_notes:
                new_notes = f"Auto-downgraded ({reason})"
            changes.append((name, new_type, new_notes))

    # ── Apply changes directly to raw text (preserves formatting 100%) ──
    if changes:
        for name, new_type, new_notes in changes:
            raw = _apply_change(raw, name, new_type, new_notes)

        CONFIG_PATH.write_text(raw, encoding="utf-8")
        n = len(changes)
        print(f"\nUpdated {n} director{'y' if n == 1 else 'ies'} in config.")
    else:
        print("No type changes needed.")


if __name__ == "__main__":
    main()
