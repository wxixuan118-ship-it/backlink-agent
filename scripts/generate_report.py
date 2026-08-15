#!/usr/bin/env python3
"""
Generate a Markdown report from results/submission_log.json
Used by the GitHub Actions workflow to post a PR/issue comment.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RESULTS_PATH = ROOT / "results" / "submission_log.json"
REPORT_PATH = ROOT / "results" / "report.md"


def main() -> None:
    if not RESULTS_PATH.exists():
        print("No results file found.")
        sys.exit(0)

    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    submissions = data.get("submissions", [])
    summary = data.get("summary", {})

    lines = [
        "## Backlink Submission Report",
        "",
        f"**Last run:** {summary.get('last_run', 'N/A')}",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| ✅ Success | {summary.get('success', 0)} |",
        f"| ❌ Failed  | {summary.get('failed', 0)} |",
        f"| ⏭ Skipped | {summary.get('skipped', 0)} |",
        f"| 🖐 Manual  | {summary.get('manual', 0)} |",
        "",
        "### Details",
        "",
        "| Directory | Status | HTTP | Timestamp |",
        "|-----------|--------|------|-----------|",
    ]

    status_icon = {
        "success": "✅",
        "failed": "❌",
        "skipped": "⏭",
        "manual": "🖐",
    }

    for rec in sorted(submissions, key=lambda r: r["name"]):
        icon = status_icon.get(rec["status"], "?")
        http = str(rec.get("http_status") or "—")
        ts = (rec.get("timestamp") or "")[:19].replace("T", " ")
        lines.append(f"| {rec['name']} | {icon} {rec['status']} | {http} | {ts} |")

    manual = [r for r in submissions if r["status"] == "manual"]
    if manual:
        lines += [
            "",
            "### Manual Submission Required",
            "",
            "The following directories require human action:",
            "",
        ]
        for r in manual:
            note = r.get("notes", "")
            lines.append(f"- **[{r['name']}]({r['url']})** — {note}")

    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
