#!/usr/bin/env python3
"""
Auto-update directory types in submission_config.yaml based on last run results.

Strategy:
  401 / 404  →  manual     (needs auth or URL is dead)
  403        →  playwright  (bot-detection that a real browser may bypass)
  405        →  playwright  (JS form, POST endpoint wrong)
  200 failed →  playwright  (form validation needs JS)
  playwright failed → manual (nothing works automatically)
"""

import json
import sys
from pathlib import Path
from ruamel.yaml import YAML

ROOT        = Path(__file__).parent.parent
RESULTS_PATH = ROOT / "results" / "submission_log.json"
CONFIG_PATH  = ROOT / "config" / "submission_config.yaml"

# These HTTP codes mean we should try a real browser next time
UPGRADE_TO_PLAYWRIGHT = {403, 405}

# These mean the site cannot be automated at all
DOWNGRADE_TO_MANUAL = {401, 404}


def main() -> None:
    # Collect submissions from all per-site result files + legacy path
    all_submissions: list[dict] = []

    results_root = ROOT / "results"
    for path in results_root.glob("*/submission_log.json"):
        try:
            with open(path, encoding="utf-8") as f:
                all_submissions.extend(json.load(f).get("submissions", []))
        except Exception as e:
            print(f"  Warning: could not read {path}: {e}")

    if not all_submissions:
        # Also try legacy flat path
        if RESULTS_PATH.exists():
            with open(RESULTS_PATH, encoding="utf-8") as f:
                all_submissions.extend(json.load(f).get("submissions", []))

    if not all_submissions:
        print("No results file — nothing to update.")
        return

    # For each directory: keep best result across all sites
    # (success from any site beats failure from all others)
    last: dict[str, dict] = {}
    for rec in all_submissions:
        name = rec["name"]
        existing = last.get(name)
        if not existing:
            last[name] = rec
        elif rec["status"] == "success" and existing["status"] != "success":
            last[name] = rec  # promote to success

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.load(f)

    changed = 0
    for directory in cfg.get("directories", []):
        name         = directory.get("name", "")
        current_type = directory.get("type", "form")

        if current_type == "manual":
            continue  # already at the lowest tier, never promote automatically

        rec = last.get(name)
        if not rec:
            continue
        if rec["status"] == "success":
            continue  # working fine

        http = rec.get("http_status")
        new_type = None

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
            directory["type"] = new_type
            if new_type == "manual" and not directory.get("notes"):
                directory["notes"] = f"Auto-downgraded ({reason})"
            changed += 1

    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)
        print(f"\nUpdated {changed} director{'y' if changed == 1 else 'ies'} in config.")
    else:
        print("No type changes needed.")


if __name__ == "__main__":
    main()
