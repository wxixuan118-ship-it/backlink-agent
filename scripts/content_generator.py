#!/usr/bin/env python3
"""
Content Generator — uses ZhipuAI (GLM) to produce tailored
submission copy for each directory.
"""

import logging
import os
import json
import hashlib
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Simple disk cache: avoids re-generating the same content on every run
_CACHE_DIR = Path(__file__).parent.parent / "results" / ".content_cache"


def _cache_key(site_url: str, directory_name: str) -> str:
    raw = f"{site_url}|{directory_name}"
    return hashlib.md5(raw.encode()).hexdigest()


def _read_cache(key: str) -> Optional[dict]:
    path = _CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _write_cache(key: str, data: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Public API ──────────────────────────────────────────────────────────────────

def generate_submission_content(site: dict, directory: dict) -> dict:
    """
    Call ZhipuAI to generate tailored submission content for one directory.
    Returns a dict with: title, description, keywords.
    Falls back to config values if the API call fails.
    """
    api_key = os.environ.get("ZHIPUAI_API_KEY", "")
    if not api_key:
        log.warning("ZHIPUAI_API_KEY not set — using config values as-is")
        return _fallback(site)

    key = _cache_key(site["url"], directory["name"])
    cached = _read_cache(key)
    if cached:
        log.debug("Using cached content for %s", directory["name"])
        return cached

    try:
        from zhipuai import ZhipuAI  # type: ignore
        client = ZhipuAI(api_key=api_key)

        prompt = _build_prompt(site, directory)
        response = client.chat.completions.create(
            model="glm-4-flash",   # 便宜快速；换成 glm-4 效果更好
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an SEO copywriter. "
                        "Always reply with a JSON object only — no markdown fences, no extra text. "
                        "Keys: title (≤70 chars), description (≤250 chars), keywords (≤10 comma-separated words). "
                        "Write in English unless instructed otherwise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if the model adds them anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        content = json.loads(raw)

        # Validate keys
        result = {
            "title": str(content.get("title", site["title"]))[:70],
            "description": str(content.get("description", site["description"]))[:250],
            "keywords": str(content.get("keywords", site.get("keywords", "")))[:200],
        }
        _write_cache(key, result)
        log.info("Generated content for %-25s  title=%r", directory["name"], result["title"])
        return result

    except json.JSONDecodeError as exc:
        log.warning("ZhipuAI returned non-JSON for %s: %s", directory["name"], exc)
        return _fallback(site)
    except Exception as exc:
        log.warning("ZhipuAI call failed for %s: %s", directory["name"], exc)
        return _fallback(site)


def _fallback(site: dict) -> dict:
    return {
        "title": site.get("title", ""),
        "description": site.get("description", ""),
        "keywords": site.get("keywords", ""),
    }


def _build_prompt(site: dict, directory: dict) -> str:
    dir_name = directory.get("name", "")
    dir_notes = directory.get("notes", "")
    category = site.get("category", "General")

    return (
        f"Write a directory submission for the following website:\n"
        f"- URL: {site['url']}\n"
        f"- Current title: {site.get('title', '')}\n"
        f"- Current description: {site.get('description', '')}\n"
        f"- Category: {category}\n"
        f"- Target directory: {dir_name}\n"
        f"- Directory notes: {dir_notes}\n\n"
        f"Requirements:\n"
        f"1. Title: compelling, includes the brand name, ≤70 chars\n"
        f"2. Description: natural, benefit-focused, not spammy, ≤250 chars\n"
        f"3. Keywords: 5-8 relevant keywords, comma-separated\n"
        f"4. Do NOT use the phrase 'best' or exclamation marks\n"
        f"Reply with a JSON object only."
    )
