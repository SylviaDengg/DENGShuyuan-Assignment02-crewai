"""Demo workflow for the Source Credibility Heuristic tool."""

from __future__ import annotations

import json
from pathlib import Path

from tool import safe_score_source_credibility


def run_agent_workflow(payload: dict[str, object]) -> dict[str, object]:
    """Minimal agent-like workflow that selects and invokes the credibility tool."""
    return {
        "agent": "credibility_agent_v1",
        "tool_selected": "safe_score_source_credibility",
        "input": payload,
        "tool_result": safe_score_source_credibility(payload),
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
