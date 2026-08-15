#!/usr/bin/env python3
"""
Backlink Directory Auto-Submitter
Reads config/submission_config.yaml and submits your site to each directory.
Uses ZhipuAI to generate tailored submission content when ZHIPUAI_API_KEY is set.
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from bs4 import BeautifulSoup

from content_generator import generate_submission_content

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "submission_config.yaml"
RESULTS_PATH = ROOT / "results" / "submission_log.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_results() -> dict:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"submissions": [], "summary": {}}


def save_results(results: dict) -> None:
    submitted = results["submissions"]
    results["summary"] = {
        "total": len(submitted),
        "success": sum(1 for r in submitted if r["status"] == "success"),
        "failed": sum(1 for r in submitted if r["status"] == "failed"),
        "skipped": sum(1 for r in submitted if r["status"] == "skipped"),
        "manual": sum(1 for r in submitted if r["status"] == "manual"),
        "last_run": datetime.now(timezone.utc).isoformat(),
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def resolve_fields(fields: dict, site: dict, generated: dict) -> dict:
    """Replace {site.xxx} and {gen.xxx} placeholders with actual values.

    {gen.title}, {gen.description}, {gen.keywords} use AI-generated content
    when available, otherwise fall back to config values.
    """
    merged = {**site, **{f"gen_{k}": v for k, v in generated.items()}}
    resolved = {}
    for key, tpl in fields.items():
        val = tpl
        for attr, v in site.items():
            val = val.replace(f"{{site.{attr}}}", str(v))
        for attr, v in generated.items():
            val = val.replace(f"{{gen.{attr}}}", str(v))
        resolved[key] = val
    return resolved


def already_submitted(results: dict, directory_name: str) -> bool:
    for rec in results["submissions"]:
        if rec["name"] == directory_name and rec["status"] == "success":
            return True
    return False


def detect_success(response: httpx.Response) -> bool:
    """Heuristic: look for common success signals in the response body."""
    text = response.text.lower()
    success_phrases = [
        "thank you", "thanks for submitting", "successfully submitted",
        "submission received", "added successfully", "url has been added",
        "your site has been", "submission complete", "received your submission",
    ]
    failure_phrases = [
        "error", "invalid", "already submitted", "captcha", "spam",
        "bad request",
    ]
    if response.status_code >= 400:
        return False
    for phrase in success_phrases:
        if phrase in text:
            return True
    # If no obvious error and status is 2xx/3xx, treat as likely success
    for phrase in failure_phrases:
        if phrase in text:
            return False
    return response.status_code < 400


# ── Core submission logic ──────────────────────────────────────────────────────

def submit_form(client: httpx.Client, directory: dict, site: dict, settings: dict) -> dict:
    name = directory["name"]
    url = directory["url"]
    method = directory.get("method", "POST").upper()
    raw_fields = directory.get("fields", {})

    # Generate AI content, then resolve field placeholders
    generated = generate_submission_content(site, directory)
    fields = resolve_fields(raw_fields, site, generated)

    retries = settings.get("max_retries", 2)
    timeout = settings.get("request_timeout_seconds", 20)

    for attempt in range(1, retries + 2):
        try:
            # First GET the page to grab any hidden CSRF tokens
            page_resp = client.get(url, timeout=timeout)
            soup = BeautifulSoup(page_resp.text, "html.parser")

            # Merge hidden inputs from the form
            form = soup.find("form")
            if form:
                for hidden in form.find_all("input", type="hidden"):
                    n = hidden.get("name")
                    v = hidden.get("value", "")
                    if n and n not in fields:
                        fields[n] = v

            # Submit
            if method == "POST":
                resp = client.post(url, data=fields, timeout=timeout)
            else:
                resp = client.get(url, params=fields, timeout=timeout)

            status = "success" if detect_success(resp) else "failed"
            return {
                "name": name,
                "url": url,
                "status": status,
                "http_status": resp.status_code,
                "attempt": attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": directory.get("notes", ""),
            }

        except httpx.TimeoutException:
            log.warning("%s — timeout (attempt %d)", name, attempt)
            if attempt > retries:
                break
            time.sleep(2)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s — error: %s (attempt %d)", name, exc, attempt)
            if attempt > retries:
                break
            time.sleep(2)

    return {
        "name": name,
        "url": url,
        "status": "failed",
        "http_status": None,
        "attempt": retries + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": "Exceeded retries",
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Submit your site to backlink directories")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without submitting")
    parser.add_argument("--only", help="Comma-separated list of directory names to run")
    parser.add_argument("--force", action="store_true", help="Re-submit even if already submitted")
    args = parser.parse_args()

    cfg = load_config()
    site = cfg["site"]
    directories = cfg["directories"]
    settings = cfg.get("settings", {})
    delay = settings.get("request_delay_seconds", 3)
    skip_done = settings.get("skip_already_submitted", True)

    results = load_results()

    # Filter by --only flag
    if args.only:
        wanted = {n.strip().lower() for n in args.only.split(",")}
        directories = [d for d in directories if d["name"].lower() in wanted]

    ai_enabled = bool(os.environ.get("ZHIPUAI_API_KEY"))
    log.info("=" * 60)
    log.info("Target site : %s", site["url"])
    log.info("Directories : %d", len(directories))
    log.info("AI content  : %s", "enabled (ZhipuAI)" if ai_enabled else "disabled (using config values)")
    log.info("Dry run     : %s", args.dry_run)
    log.info("=" * 60)

    manual_list = []

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for directory in directories:
            name = directory["name"]
            dtype = directory.get("type", "form")

            # Manual directories — queue for human action
            if dtype == "manual":
                log.info("[ MANUAL ] %s  →  %s", name, directory["url"])
                manual_list.append(directory)
                record = {
                    "name": name,
                    "url": directory["url"],
                    "status": "manual",
                    "http_status": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": directory.get("notes", ""),
                }
                # Only add if not already in results
                if not any(r["name"] == name for r in results["submissions"]):
                    results["submissions"].append(record)
                continue

            # Skip already-submitted directories
            if not args.force and skip_done and already_submitted(results, name):
                log.info("[ SKIP   ] %s  (already submitted)", name)
                continue

            if args.dry_run:
                log.info("[ DRY    ] Would submit to: %s  (%s)", name, directory["url"])
                continue

            log.info("[ SUBMIT ] %s  →  %s", name, directory["url"])
            record = submit_form(client, directory, site, settings)

            # Remove previous record for this directory, then append new one
            results["submissions"] = [
                r for r in results["submissions"] if r["name"] != name
            ]
            results["submissions"].append(record)
            save_results(results)

            emoji = "✓" if record["status"] == "success" else "✗"
            log.info("           %s %s  (HTTP %s)", emoji, record["status"].upper(), record["http_status"])

            time.sleep(delay)

    save_results(results)

    # ── Summary ────────────────────────────────────────────────────────────────
    s = results["summary"]
    log.info("")
    log.info("=" * 60)
    log.info("DONE — Success: %d  Failed: %d  Skipped: %d  Manual: %d",
             s.get("success", 0), s.get("failed", 0),
             s.get("skipped", 0), s.get("manual", 0))

    if manual_list:
        log.info("")
        log.info("── Manual submission required ──")
        for d in manual_list:
            log.info("  • %-30s %s", d["name"], d["url"])
            if d.get("notes"):
                log.info("    Note: %s", d["notes"])

    log.info("Results saved to: %s", RESULTS_PATH)

    # Exit with error code if any submissions failed (useful for CI)
    failed = s.get("failed", 0)
    if failed > 0:
        log.warning("%d submission(s) failed — check results/submission_log.json", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
