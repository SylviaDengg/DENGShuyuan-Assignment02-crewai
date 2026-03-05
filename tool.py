"""Source Credibility Heuristic tool.

This module exposes a lightweight heuristic scorer for article/source credibility.
It is intentionally simple and interpretable, and is not a factual verification
engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


TRUSTED_DOMAIN_SUFFIXES = (
    ".gov",
    ".edu",
)

TRUSTED_DOMAIN_KEYWORDS = (
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "npr.org",
    "nature.com",
    "who.int",
)

SUSPICIOUS_DOMAIN_KEYWORDS = (
    "viral",
    "click",
    "buzz",
    "shocking",
    "truth-now",
    "breaking-now",
    "free-money",
)

CLICKBAIT_PHRASES = (
    "you won't believe",
    "you wont believe",
    "shocking",
    "must see",
    "what happened next",
    "doctors hate",
    "this one trick",
    "gone wrong",
    "secret they don't want",
)


@dataclass
class ToolValidationError(Exception):
    """Raised when input to the credibility tool is invalid."""

    message: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.message


def _require_non_empty_string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            message=f"'{key}' must be a non-empty string",
            details={"field": key, "value": value},
        )
    return value.strip()


def _optional_string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ToolValidationError(
            message=f"'{key}' must be a string when provided",
            details={"field": key, "value": value},
        )
    return value.strip()


def _validate_record(record: dict[str, object]) -> tuple[str, str, str, str]:
    if not isinstance(record, dict):
        raise ToolValidationError(
            message="Input must be a dictionary",
            details={"expected": "dict[str, object]", "received_type": type(record).__name__},
        )

    url = _require_non_empty_string(record, "url")
    title = _require_non_empty_string(record, "title")
    byline = _optional_string(record, "byline")
    text = _optional_string(record, "text")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ToolValidationError(
            message="'url' must be a valid http/https URL",
            details={"field": "url", "value": url},
        )

    return url, title, byline, text


def _score_domain(url: str) -> tuple[int, str, str]:
    domain = urlparse(url).netloc.lower()

    if domain.endswith(TRUSTED_DOMAIN_SUFFIXES):
        return 18, domain, "Government or education domain suffix detected"

    if any(keyword in domain for keyword in TRUSTED_DOMAIN_KEYWORDS):
        return 12, domain, "Domain matches known mainstream/scientific outlet patterns"

    if any(keyword in domain for keyword in SUSPICIOUS_DOMAIN_KEYWORDS):
        return -20, domain, "Domain contains suspicious/click-optimized pattern"

    return 0, domain, "Domain has no strong trust or distrust pattern"


def _score_byline(byline: str) -> tuple[int, str]:
    if byline:
        return 10, "Byline/author metadata present"
    return -6, "No byline/author metadata present"


def _score_clickbait_and_caps(title: str, text: str) -> tuple[int, str, dict[str, Any]]:
    combined = f"{title} {text}".strip().lower()
    matched_phrases = [phrase for phrase in CLICKBAIT_PHRASES if phrase in combined]

    clickbait_penalty = -8 * len(matched_phrases)

    alpha_chars = [c for c in title if c.isalpha()]
    uppercase_chars = [c for c in alpha_chars if c.isupper()]
    uppercase_ratio = (len(uppercase_chars) / len(alpha_chars)) if alpha_chars else 0.0

    caps_penalty = 0
    caps_reason = "No excessive capitalization detected"
    if uppercase_ratio >= 0.6 and len(alpha_chars) >= 8:
        caps_penalty = -12
        caps_reason = "Excessive capitalization in title"
    elif uppercase_ratio >= 0.4 and len(alpha_chars) >= 8:
        caps_penalty = -6
        caps_reason = "Moderate capitalization signal in title"

    total = clickbait_penalty + caps_penalty

    if matched_phrases:
        reason = f"Clickbait phrases detected: {', '.join(matched_phrases)}"
    else:
        reason = "No common clickbait phrases detected"

    detail = {
        "matched_clickbait_phrases": matched_phrases,
        "uppercase_ratio": round(uppercase_ratio, 3),
        "caps_reason": caps_reason,
    }
    return total, reason, detail


def _label_for_score(score: int) -> str:
    if score >= 75:
        return "higher_credibility"
    if score >= 40:
        return "mixed_credibility"
    return "lower_credibility"


def score_source_credibility(record: dict[str, object]) -> dict[str, object]:
    """Compute a lightweight source credibility score from metadata/text heuristics.

    The tool scores one record using simple, interpretable signals:
    - Domain pattern heuristics (trusted/suspicious indicators)
    - Presence of byline/author metadata
    - Clickbait phrase detection and excessive capitalization in title

    The score is *not* a truth detector and should only be used as a rough,
    first-pass ranking signal.

    Args:
        record: Input dictionary with the following schema:
            - url (required): non-empty http/https URL string
            - title (required): non-empty title string
            - byline (optional): author/byline string
            - text (optional): snippet/body string

    Returns:
        JSON-serializable dictionary with this shape:
            {
              "ok": True,
              "score": int,  # 0..100
              "label": str,  # higher_credibility|mixed_credibility|lower_credibility
              "signals": {
                "domain": int,
                "byline": int,
                "clickbait_caps": int,
                "baseline": int,
              },
              "reasons": list[str],
              "input_echo": {
                "url": str,
                "title": str,
                "byline": str,
                "text": str,
              },
              "debug": {
                "domain": str,
                "clickbait": {
                  "matched_clickbait_phrases": list[str],
                  "uppercase_ratio": float,
                  "caps_reason": str,
                }
              }
            }

    Raises:
        ToolValidationError: If input is missing required fields, has invalid
            types, or has an invalid URL format.
    """

    url, title, byline, text = _validate_record(record)

    baseline = 50

    domain_score, domain, domain_reason = _score_domain(url)
    byline_score, byline_reason = _score_byline(byline)
    clickbait_caps_score, clickbait_reason, clickbait_detail = _score_clickbait_and_caps(
        title=title,
        text=text,
    )

    raw_score = baseline + domain_score + byline_score + clickbait_caps_score
    score = max(0, min(100, raw_score))

    reasons = [domain_reason, byline_reason, clickbait_reason, clickbait_detail["caps_reason"]]

    return {
        "ok": True,
        "score": score,
        "label": _label_for_score(score),
        "signals": {
            "baseline": baseline,
            "domain": domain_score,
            "byline": byline_score,
            "clickbait_caps": clickbait_caps_score,
        },
        "reasons": reasons,
        "input_echo": {
            "url": url,
            "title": title,
            "byline": byline,
            "text": text,
        },
        "debug": {
            "domain": domain,
            "clickbait": clickbait_detail,
        },
    }


def safe_score_source_credibility(record: dict[str, object]) -> dict[str, object]:
    """Safely invoke `score_source_credibility` and normalize failures.

    Args:
        record: Input dictionary expected by `score_source_credibility`.

    Returns:
        On success, the same success payload as `score_source_credibility`.
        On failure, a structured JSON-serializable error payload:
            {
              "ok": False,
              "error": {
                "type": str,
                "message": str,
                "details": dict
              }
            }
    """

    try:
        return score_source_credibility(record)
    except ToolValidationError as exc:
        return {
            "ok": False,
            "error": {
                "type": "ToolValidationError",
                "message": str(exc),
                "details": exc.details,
            },
        }
    except Exception as exc:  # Defensive boundary for agent workflows.
        return {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "message": "Unexpected tool failure",
                "details": {"raw_message": str(exc)},
            },
        }


if __name__ == "__main__":
    import json

    example = {
        "url": "https://www.reuters.com/world/example-story",
        "title": "Global health agency publishes annual report",
        "byline": "Alex Smith",
        "text": "Officials shared methodology and reviewed findings.",
    }
    print(json.dumps(safe_score_source_credibility(example), indent=2))
