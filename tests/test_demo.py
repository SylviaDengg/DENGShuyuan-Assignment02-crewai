"""Unit tests for demo.py workflows."""

from __future__ import annotations

import unittest

import demo


class DemoBehaviorTests(unittest.TestCase):
    def test_run_agent_workflow_envelope(self) -> None:
        payload = {
            "url": "https://www.reuters.com/world/example",
            "title": "Agency releases annual report",
            "byline": "Jordan Lee",
            "text": "Report includes methodology and references.",
        }
        result = demo.run_agent_workflow(payload)
        self.assertEqual(result["agent"], "credibility_agent_v1")
        self.assertEqual(result["tool_selected"], "safe_score_source_credibility")
        self.assertEqual(result["input"], payload)
        self.assertIn("tool_result", result)


if __name__ == "__main__":
    unittest.main()
