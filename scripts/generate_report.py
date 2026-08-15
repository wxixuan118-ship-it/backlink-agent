#!/usr/bin/env python3
"""
Generate submission reports.
  --site {slug}  → report for one site  (results/{slug}/report.md)
  (no flag)      → report for all sites (results/{slug}/report.md each + combined results/report.md)
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def build_report(submissions: list, site_slug: str, last_run: str) -> str:
    manually_done  = sum(1 for r in submissions if r.get("manually_submitted"))
    auto_success   = sum(1 for r in submissions if r["status"] == "success")
    confirmed      = auto_success + manually_done
    pending_manual = sum(1 for r in submissions if r["status"] == "manual" and not r.get("manually_submitted"))
    auto_failed    = sum(1 for r in submissions if r["status"] == "failed" and not r.get("manually_submitted"))

    lines = [
        f"## Backlink Report — {site_slug}",
        "",
        f"**Last run:** {last_run}",
        "",
        "| Status | Count |",
        "|--------|-------|",
        f"| ✅ Confirmed (auto + manual) | {confirmed} |",
        f"| ⚡ Auto-submitted            | {auto_success} |",
        f"| 📝 Manually confirmed        | {manually_done} |",
        f"| 🖐 Pending manual            | {pending_manual} |",
        f"| ❌ Auto-failed               | {auto_failed} |",
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
        icon  = _icon(rec)
        http  = str(rec.get("http_status") or "—")
        ts    = (rec.get("manually_submitted_at") or rec.get("timestamp") or "")[:10]
        label = rec["status"] + (" ✓" if rec.get("manually_submitted") else "")
        lines.append(f"| {rec['name']} | {icon} {label} | {http} | {ts} |")

    pending = [r for r in submissions if r["status"] == "manual" and not r.get("manually_submitted")]
    if pending:
        lines += [
            "",
            "### Pending Manual Submissions",
            "",
            "Open these URLs and submit manually:",
            "",
        ]
        for r in pending:
            note = r.get("notes", "")
            lines.append(f"- **[{r['name']}]({r['url']})** — {note}")

    return "\n".join(lines)


def process_site(slug: str, results_path: Path) -> str | None:
    if not results_path.exists():
        return None
    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)
    submissions = data.get("submissions", [])
    last_run    = data.get("summary", {}).get("last_run", "N/A")
    report      = build_report(submissions, slug, last_run)
    report_path = results_path.parent / "report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written: {report_path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", help="Site slug (default: all sites)")
    args = parser.parse_args()

    results_root = ROOT / "results"

    if args.site:
        rp = results_root / args.site / "submission_log.json"
        report = process_site(args.site, rp)
        if report:
            print(report)
        else:
            print(f"No results for site '{args.site}'")
        return

    # All sites
    reports = []
    for rp in sorted(results_root.glob("*/submission_log.json")):
        slug   = rp.parent.name
        report = process_site(slug, rp)
        if report:
            reports.append(report)

    if not reports:
        # Legacy flat path fallback
        legacy = results_root / "submission_log.json"
        if legacy.exists():
            with open(legacy, encoding="utf-8") as f:
                data = json.load(f)
            report = build_report(data.get("submissions", []), "default",
                                  data.get("summary", {}).get("last_run", "N/A"))
            (results_root / "report.md").write_text(report, encoding="utf-8")
            print(report)
            return
        print("No results found.")
        return

    # Combined report at results/report.md
    combined = "\n\n---\n\n".join(reports)
    (results_root / "report.md").write_text(combined, encoding="utf-8")
    print(combined)


if __name__ == "__main__":
    main()
