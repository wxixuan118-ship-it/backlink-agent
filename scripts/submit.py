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
import playwright_submit as pw_submit

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
    """Heuristic: look for success/failure signals in the response body.

    Uses specific multi-word phrases only — single generic words like 'error'
    or 'invalid' appear on almost every page and produce too many false negatives.
    A 2xx/3xx with no explicit failure phrase is treated as likely success.
    """
    text = response.text.lower()
    success_phrases = [
        "thank you", "thanks for submitting", "successfully submitted",
        "submission received", "added successfully", "url has been added",
        "your site has been", "submission complete", "received your submission",
        "we'll review", "we will review", "under review", "pending review",
        "site submitted", "listing submitted", "tool submitted",
    ]
    # Specific failure phrases — avoid single words that appear in normal pages
    failure_phrases = [
        "your submission could not", "submission failed", "submission error",
        "invalid url", "invalid website", "url is not valid",
        "already submitted", "already listed", "already in our",
        "captcha", "spam detected", "bot detected",
        "please fill in", "this field is required",
        "invalid email address",
    ]
    if response.status_code >= 400:
        return False
    for phrase in success_phrases:
        if phrase in text:
            return True
    for phrase in failure_phrases:
        if phrase in text:
            return False
    # 2xx with no explicit failure signal → treat as success
    return response.status_code < 400


# ── Form field auto-detection ──────────────────────────────────────────────────

# Keyword groups that hint at a field's semantic meaning
_URL_HINTS   = {"url", "site", "website", "link", "web", "homepage", "siteurl", "site_url"}
_TITLE_HINTS = {"title", "name", "sitename", "site_name", "toolname", "tool_name",
                "appname", "app_name", "productname", "product_name"}
_DESC_HINTS  = {"desc", "description", "about", "summary", "detail",
                "message", "content", "overview", "blurb", "info"}
_EMAIL_HINTS = {"email", "mail", "contact", "e_mail"}
_KW_HINTS    = {"keyword", "keywords", "tag", "tags", "category", "categories"}


def _hint_match(text: str, hint_set: set) -> bool:
    lower = text.lower().replace("-", "_")
    return any(h in lower for h in hint_set)


def smart_fill_fields(soup: BeautifulSoup, base_fields: dict,
                      site: dict, generated: dict) -> dict:
    """
    Walk every visible <input>/<textarea> on the page and map our values
    to whatever field names the form actually uses.
    base_fields (from config) take priority; detected fields fill the rest.
    """
    val = {
        "url":         site["url"],
        "title":       generated.get("title",       site.get("title", "")),
        "description": generated.get("description", site.get("description", "")),
        "email":       site.get("email", ""),
        "keywords":    generated.get("keywords",    site.get("keywords", "")),
        "owner_name":  site.get("owner_name", ""),
    }

    result = dict(base_fields)

    form = soup.find("form")
    inputs = (form or soup).find_all(["input", "textarea", "select"])

    for inp in inputs:
        field_name = (inp.get("name") or "").strip()
        if not field_name:
            continue
        ftype = (inp.get("type") or "text").lower()
        if ftype in ("hidden", "submit", "button", "image", "reset"):
            # Keep hidden values from the page (CSRF etc.) but don't overwrite config
            if ftype == "hidden" and field_name not in result:
                result[field_name] = inp.get("value", "")
            continue
        if field_name in result:
            continue  # config already specified this field

        # Build hint string from name + id + placeholder + label text
        hint = " ".join(filter(None, [
            field_name,
            inp.get("id", ""),
            inp.get("placeholder", ""),
        ]))

        if   _hint_match(hint, _URL_HINTS):   result[field_name] = val["url"]
        elif _hint_match(hint, _EMAIL_HINTS):  result[field_name] = val["email"]
        elif _hint_match(hint, _TITLE_HINTS):  result[field_name] = val["title"]
        elif _hint_match(hint, _DESC_HINTS):   result[field_name] = val["description"]
        elif _hint_match(hint, _KW_HINTS):     result[field_name] = val["keywords"]

    return result


# ── Core submission logic ──────────────────────────────────────────────────────

def submit_form(client: httpx.Client, directory: dict, site: dict, settings: dict) -> dict:
    name = directory["name"]
    url = directory["url"]
    method = directory.get("method", "POST").upper()
    raw_fields = directory.get("fields", {})

    generated = generate_submission_content(site, directory)
    base_fields = resolve_fields(raw_fields, site, generated)

    retries = settings.get("max_retries", 2)
    timeout = settings.get("request_timeout_seconds", 20)

    for attempt in range(1, retries + 2):
        try:
            page_resp = client.get(url, timeout=timeout)
            soup = BeautifulSoup(page_resp.text, "html.parser")

            # Detect actual form fields + merge CSRF hidden inputs
            fields = smart_fill_fields(soup, base_fields, site, generated)

            # Find the form's action URL (may differ from the page URL)
            form_tag = soup.find("form")
            action = url
            if form_tag and form_tag.get("action"):
                from urllib.parse import urljoin
                action = urljoin(url, form_tag["action"])
                method = (form_tag.get("method") or method).upper()

            if method == "POST":
                resp = client.post(action, data=fields, timeout=timeout)
            else:
                resp = client.get(action, params=fields, timeout=timeout)

            status = "success" if detect_success(resp) else "failed"
            log.debug("%s fields sent: %s", name, list(fields.keys()))
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
                if not any(r["name"] == name for r in results["submissions"]):
                    results["submissions"].append({
                        "name": name,
                        "url": directory["url"],
                        "status": "manual",
                        "http_status": None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "notes": directory.get("notes", ""),
                    })
                continue

            # Skip already-submitted directories
            if not args.force and skip_done and already_submitted(results, name):
                log.info("[ SKIP   ] %s  (already submitted)", name)
                continue

            if args.dry_run:
                log.info("[ DRY    ] Would submit to: %s  (%s, type=%s)", name, directory["url"], dtype)
                continue

            # ── Playwright submission ──────────────────────────────────────
            if dtype == "playwright":
                log.info("[ BROWSER] %s  →  %s", name, directory["url"])
                generated = generate_submission_content(site, directory)
                record = pw_submit.submit(directory, site, generated,
                                          timeout_ms=settings.get("request_timeout_seconds", 40) * 1000)

            # ── HTTP form submission ───────────────────────────────────────
            else:
                log.info("[ SUBMIT ] %s  →  %s", name, directory["url"])
                record = submit_form(client, directory, site, settings)

            results["submissions"] = [r for r in results["submissions"] if r["name"] != name]
            results["submissions"].append(record)
            save_results(results)

            emoji = "✓" if record["status"] == "success" else "✗"
            log.info("           %s %s  (HTTP %s)", emoji, record["status"].upper(), record.get("http_status"))

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

    # Only fail CI when the script itself had an unrecoverable error.
    # Individual submission failures are normal (sites change forms, add CAPTCHAs, etc.)
    # and are recorded in the JSON for review — they should not block email/commit steps.
    failed = s.get("failed", 0)
    success = s.get("success", 0)
    if failed > 0:
        log.warning("%d submission(s) failed — see results/submission_log.json", failed)
    if success == 0 and failed > 0:
        log.warning("No submissions succeeded this run.")
    # Always exit 0 so downstream steps (email, commit) still run


if __name__ == "__main__":
    main()
