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

    manually_done  = sum(1 for r in submissions if r.get("manually_submitted"))
    auto_success   = summary.get("success", 0)
    confirmed      = auto_success + manually_done
    pending_manual = sum(1 for r in submissions if r["status"] == "manual" and not r.get("manually_submitted"))
    auto_failed    = sum(1 for r in submissions if r["status"] == "failed" and not r.get("manually_submitted"))

    lines = [
        "## Backlink Submission Report",
        "",
        f"**Last run:** {summary.get('last_run', 'N/A')}",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| ✅ Confirmed (auto + manual) | {confirmed} |",
        f"| 📝 Manually confirmed | {manually_done} |",
        f"| ⚡ Auto-submitted | {auto_success} |",
        f"| 🖐 Pending manual | {pending_manual} |",
        f"| ❌ Auto-failed | {auto_failed} |",
        f"| ⏭ Skipped | {summary.get('skipped', 0)} |",
        "",
        "### All Submissions",
        "",
        "| Directory | Status | HTTP | Date |",
        "|-----------|--------|------|------|",
    ]

    def _icon(rec):
        if rec.get("manually_submitted"):
            return "📝"
        return {"success": "✅", "failed": "❌", "skipped": "⏭", "manual": "🖐"}.get(rec["status"], "?")

    for rec in sorted(submissions, key=lambda r: r["name"]):
        icon = _icon(rec)
        http = str(rec.get("http_status") or "—")
        ts = (rec.get("manually_submitted_at") or rec.get("timestamp") or "")[:10]
        label = rec["status"] + (" ✓" if rec.get("manually_submitted") else "")
        lines.append(f"| {rec['name']} | {icon} {label} | {http} | {ts} |")

    # Pending manual actions
    pending = [r for r in submissions if r["status"] == "manual" and not r.get("manually_submitted")]
    if pending:
        lines += [
            "",
            "### Pending Manual Submissions",
            "",
            "Open these URLs in a browser and submit your site manually:",
            "",
        ]
        for r in pending:
            note = r.get("notes", "")
            lines.append(f"- **[{r['name']}]({r['url']})** — {note}")

    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
