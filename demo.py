"""Demo workflow for the Source Credibility Heuristic tool."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from tool import safe_score_source_credibility


def _call_deepseek_router(payload: dict[str, object], api_key: str) -> dict[str, Any]:
    """Route tool selection through a real DeepSeek call when enabled."""
    prompt = (
        "You are an agent router. Return strict JSON with keys "
        "'tool_selected' and 'reason'. "
        "For this workflow choose the tool for source credibility scoring. "
        f"Payload: {json.dumps(payload, ensure_ascii=True)}"
    )
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Return compact JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    req = request.Request(
        url="https://api.deepseek.com/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    with request.urlopen(req, timeout=20) as resp:
        parsed = json.loads(resp.read().decode("utf-8"))

    content = (
        parsed.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    try:
        decision = json.loads(content)
    except json.JSONDecodeError:
        decision = {}

    selected = decision.get("tool_selected")
    reason = decision.get("reason")
    if not isinstance(selected, str) or not selected.strip():
        selected = "safe_score_source_credibility"
    if not isinstance(reason, str) or not reason.strip():
        reason = "Defaulted to the known credibility tool."

    return {
        "mode": "real_llm",
        "provider": "deepseek",
        "tool_selected": selected,
        "reason": reason,
    }


def select_tool_for_payload(payload: dict[str, object]) -> dict[str, Any]:
    """Select the tool via simulated routing or optional real LLM routing."""
    use_real_llm = os.getenv("USE_REAL_LLM_AGENT", "0") == "1"
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if use_real_llm and api_key:
        try:
            return _call_deepseek_router(payload, api_key)
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            return {
                "mode": "simulated",
                "provider": "fallback_after_api_error",
                "tool_selected": "safe_score_source_credibility",
                "reason": f"Fell back to simulated router: {type(exc).__name__}",
            }
        except Exception as exc:
            return {
                "mode": "simulated",
                "provider": "fallback_after_unexpected_error",
                "tool_selected": "safe_score_source_credibility",
                "reason": f"Fell back to simulated router: {type(exc).__name__}",
            }

    if use_real_llm and not api_key:
        return {
            "mode": "simulated",
            "provider": "missing_api_key",
            "tool_selected": "safe_score_source_credibility",
            "reason": "USE_REAL_LLM_AGENT=1 but DEEPSEEK_API_KEY is missing.",
        }

    return {
        "mode": "simulated",
        "provider": "local_rules",
        "tool_selected": "safe_score_source_credibility",
        "reason": "Default local simulation mode.",
    }


def run_agent_workflow(payload: dict[str, object]) -> dict[str, object]:
    """Agent-like workflow with optional real-LLM routing."""
    routing = select_tool_for_payload(payload)
    selected_tool = routing["tool_selected"]
    if selected_tool != "safe_score_source_credibility":
        tool_result: dict[str, object] = {
            "ok": False,
            "error": {
                "type": "UnsupportedToolSelection",
                "message": f"Unsupported tool selected by router: {selected_tool}",
                "details": {"selected_tool": selected_tool},
            },
        }
    else:
        tool_result = safe_score_source_credibility(payload)

    return {
        "agent": "credibility_agent_v1",
        "agent_mode": routing["mode"],
        "routing": routing,
        "tool_selected": selected_tool,
        "input": payload,
        "tool_result": tool_result,
    }


def load_real_scraped_payload() -> dict[str, object]:
    """Load a demo payload.

    Preferred source is the local fixture snapshot. If the fixture file is absent
    (for example, in a minimal submission package), fall back to a built-in valid
    record so the demo remains runnable.
    """
    fixture_path = Path(__file__).resolve().parent / "tests" / "fixtures" / "source_samples.json"
    if fixture_path.exists():
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Fixture file must contain a list of samples")

        for sample in data:
            record = sample.get("record")
            if not isinstance(record, dict):
                continue
            if isinstance(record.get("url"), str) and record.get("url", "").startswith(("http://", "https://")):
                if isinstance(record.get("title"), str) and record.get("title", "").strip():
                    return record

        raise ValueError("No valid scraped record found in fixture file")

    return {
        "url": "https://www.npr.org",
        "title": "NPR - Breaking News, Analysis, Music, Arts & Podcasts",
        "byline": "NPR Staff",
        "text": "Public media reporting and analysis on U.S. and world events.",
    }


def main() -> None:
    valid_payload = load_real_scraped_payload()

    invalid_payload = {
        "url": "not-a-url",
        "title": 999,
        "byline": None,
    }

    print("=== Demo 1: Agent/workflow calls the tool with real scraped data ===")
    success_run = run_agent_workflow(valid_payload)
    print(json.dumps(success_run, indent=2, ensure_ascii=True))

    print("\n=== Demo 1a: Successful execution result ===")
    print(json.dumps(success_run["tool_result"], indent=2, ensure_ascii=True))

    print("\n=== Demo 2: Error handling with bad input ===")
    error_run = run_agent_workflow(invalid_payload)
    print(json.dumps(error_run, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
