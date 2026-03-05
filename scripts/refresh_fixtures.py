"""Manual utility to refresh test fixtures from selected web pages.

This script is intentionally manual and optional.
It should not run as part of automated tests.

Usage:
    python scripts/refresh_fixtures.py

Notes:
- Requires network access.
- Output is sanitized and truncated for deterministic, low-risk fixtures.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "tests" / "fixtures" / "source_samples.json"

SEED_URLS = [
    "https://www.reuters.com",
    "https://www.npr.org",
    "https://www.cdc.gov",
    "https://www.bbc.com",
]


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title[:180]


def _extract_byline(html: str) -> str:
    patterns = [
        r'name=["\']author["\']\s+content=["\']([^"\']+)["\']',
        r'property=["\']article:author["\']\s+content=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:120]
    return ""


def _extract_text_snippet(html: str) -> str:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
    cleaned: list[str] = []
    for p in paragraphs:
        text = re.sub(r"<[^>]+>", " ", p)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 40:
            cleaned.append(text)
        if len(cleaned) >= 2:
            break
    return " ".join(cleaned)[:300]


def _fetch_url(url: str) -> dict[str, str]:
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    return {
        "url": url,
        "title": _extract_title(html) or "Untitled page",
        "byline": _extract_byline(html),
        "text": _extract_text_snippet(html),
    }


def main() -> None:
    refreshed: list[dict[str, object]] = []

    for i, url in enumerate(SEED_URLS, start=1):
        try:
            record = _fetch_url(url)
            refreshed.append(
                {
                    "id": f"refreshed_{i}",
                    "record": record,
                    "expectations": {
                        "score_min": 0,
                        "score_max": 100,
                        "label_one_of": [
                            "higher_credibility",
                            "mixed_credibility",
                            "lower_credibility",
                        ],
                        "should_error": False,
                    },
                }
            )
            print(f"Fetched: {url}")
        except Exception as exc:
            print(f"Skipped {url}: {exc}")

    if not refreshed:
        raise SystemExit("No fixtures refreshed. Check network access and target URLs.")

    OUT_PATH.write_text(json.dumps(refreshed, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(refreshed)} fixtures to {OUT_PATH}")


if __name__ == "__main__":
    main()
