#!/usr/bin/env python3
"""
Playwright-based form submitter for JS-rendered sites.
Falls back gracefully if playwright is not installed.
"""

import asyncio
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# ── Field hint sets ────────────────────────────────────────────────────────────
_URL_HINTS   = {"url", "site", "website", "link", "web", "homepage", "siteurl", "site_url"}
_TITLE_HINTS = {"title", "name", "sitename", "site_name", "toolname", "tool_name",
                "appname", "app_name", "productname", "product_name"}
_DESC_HINTS  = {"desc", "description", "about", "summary", "detail",
                "message", "content", "overview", "blurb"}
_EMAIL_HINTS = {"email", "mail", "contact", "e_mail"}
_KW_HINTS    = {"keyword", "keywords", "tag", "tags"}

_SUCCESS_PHRASES = [
    "thank you", "thanks for submitting", "successfully submitted",
    "submission received", "added successfully", "url has been added",
    "your site has been", "submission complete", "received your submission",
    "we'll review", "we will review", "under review",
]
_FAILURE_PHRASES = [
    "captcha required", "spam detected", "invalid url",
    "access denied", "forbidden",
]


def _hint_match(text: str, hints: set) -> bool:
    lower = text.lower().replace("-", "_")
    return any(h in lower for h in hints)


def _check_success(html: str) -> bool | None:
    text = html.lower()
    if any(p in text for p in _SUCCESS_PHRASES):
        return True
    if any(p in text for p in _FAILURE_PHRASES):
        return False
    return None  # ambiguous — assume optimistic


async def _fill_form(page, values: dict) -> int:
    """Fill every visible text input/textarea. Returns number of fields filled."""
    filled = 0
    for selector in ["input:visible", "textarea:visible"]:
        try:
            elements = await page.locator(selector).all()
        except Exception:
            continue

        for el in elements:
            try:
                itype = (await el.get_attribute("type") or "text").lower()
                if itype in ("hidden", "submit", "button", "checkbox", "radio", "file", "search"):
                    continue

                name = await el.get_attribute("name") or ""
                eid  = await el.get_attribute("id")   or ""
                ph   = await el.get_attribute("placeholder") or ""
                hint = f"{name} {eid} {ph}"

                value = None
                if   _hint_match(hint, _URL_HINTS):   value = values["url"]
                elif _hint_match(hint, _EMAIL_HINTS):  value = values["email"]
                elif _hint_match(hint, _TITLE_HINTS):  value = values["title"]
                elif _hint_match(hint, _DESC_HINTS):   value = values["description"]
                elif _hint_match(hint, _KW_HINTS):     value = values["keywords"]

                if value:
                    await el.fill(str(value))
                    filled += 1
            except Exception:
                continue

    return filled


async def _click_submit(page) -> bool:
    """Try common submit button selectors. Returns True if clicked."""
    selectors = [
        "button[type=submit]",
        "input[type=submit]",
        "button:has-text('Submit')",
        "button:has-text('Add')",
        "button:has-text('Send')",
        "button:has-text('List')",
        "button:has-text('Register')",
        "[data-testid*='submit']",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


async def _submit_async(directory: dict, site: dict, generated: dict,
                         timeout_ms: int = 40_000) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    url  = directory["url"]
    name = directory["name"]

    values = {
        "url":         site["url"],
        "title":       generated.get("title",       site.get("title", "")),
        "description": generated.get("description", site.get("description", "")),
        "email":       site.get("email", ""),
        "keywords":    generated.get("keywords",    site.get("keywords", "")),
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        def _result(status, notes=""):
            return {
                "name": name, "url": url,
                "status": status, "http_status": 200 if status == "success" else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": notes or "Submitted via Playwright",
            }

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for form fields to render (handles React/Vue SPAs)
            try:
                await page.wait_for_selector("input:visible, textarea:visible", timeout=8_000)
            except Exception:
                pass

            filled = await _fill_form(page, values)
            if filled == 0:
                log.warning("%s — Playwright: no fields found", name)
                return _result("failed", "No fillable fields found")

            log.debug("%s — Playwright filled %d field(s)", name, filled)
            submitted = await _click_submit(page)

            if not submitted:
                return _result("failed", "No submit button found")

            # Wait for navigation or response
            try:
                await page.wait_for_load_state("load", timeout=5_000)
            except Exception:
                pass

            html = await page.content()
            ok = _check_success(html)
            return _result("success" if ok is not False else "failed")

        except PWTimeout:
            return _result("failed", "Playwright timeout")
        except Exception as exc:
            return _result("failed", f"Playwright error: {exc}")
        finally:
            await browser.close()


def submit(directory: dict, site: dict, generated: dict,
           timeout_ms: int = 40_000) -> dict:
    """Sync entry point."""
    try:
        return asyncio.run(_submit_async(directory, site, generated, timeout_ms))
    except ImportError:
        return {
            "name": directory["name"], "url": directory["url"],
            "status": "failed", "http_status": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": "playwright not installed",
        }
