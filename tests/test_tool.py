"""Unit tests for tool.py."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import tool
from tool import ToolValidationError, safe_score_source_credibility, score_source_credibility


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "source_samples.json"


class ToolBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_success_samples_follow_expected_score_ranges(self) -> None:
        for sample in self.samples:
            expectations = sample["expectations"]
            if expectations.get("should_error"):
                continue

            with self.subTest(sample_id=sample["id"]):
                result = score_source_credibility(sample["record"])
                self.assertTrue(result["ok"])
                self.assertIn("score", result)
                self.assertIn("label", result)
                self.assertIn("signals", result)
                self.assertIn("reasons", result)
                self.assertGreaterEqual(result["score"], 0)
                self.assertLessEqual(result["score"], 100)
                self.assertGreaterEqual(result["score"], expectations["score_min"])
                self.assertLessEqual(result["score"], expectations["score_max"])
                self.assertIn(result["label"], expectations["label_one_of"])
                self.assertIsInstance(result["reasons"], list)
                self.assertGreater(len(result["reasons"]), 0)

    def test_score_label_band_mapping(self) -> None:
        self.assertEqual(tool._label_for_score(100), "higher_credibility")
        self.assertEqual(tool._label_for_score(75), "higher_credibility")
        self.assertEqual(tool._label_for_score(74), "mixed_credibility")
        self.assertEqual(tool._label_for_score(40), "mixed_credibility")
        self.assertEqual(tool._label_for_score(39), "lower_credibility")
        self.assertEqual(tool._label_for_score(0), "lower_credibility")

    def test_domain_scoring_covers_trusted_neutral_suspicious(self) -> None:
        trusted_suffix = tool._score_domain("https://agency.gov/report")
        trusted_keyword = tool._score_domain("https://www.reuters.com/world")
        neutral = tool._score_domain("https://www.some-unknown-domain.xyz/a")
        suspicious = tool._score_domain("https://fast-viral-click-news.example/a")

        self.assertGreater(trusted_suffix[0], 0)
        self.assertGreater(trusted_keyword[0], 0)
        self.assertEqual(neutral[0], 0)
        self.assertLess(suspicious[0], 0)

    def test_byline_signal_present_and_missing(self) -> None:
        self.assertGreater(tool._score_byline("Reporter Name")[0], 0)
        self.assertLess(tool._score_byline("")[0], 0)

    def test_clickbait_and_caps_penalties_detected(self) -> None:
        penalty, reason, detail = tool._score_clickbait_and_caps(
            "SHOCKING ONE TRICK YOU WONT BELIEVE",
            "You won't believe this shocking event.",
        )
        self.assertLess(penalty, 0)
        self.assertIn("Clickbait", reason)
        self.assertGreater(detail["uppercase_ratio"], 0.4)

    def test_clickbait_and_caps_baseline_has_no_penalty(self) -> None:
        penalty, reason, detail = tool._score_clickbait_and_caps(
            "City releases transportation report",
            "Officials provided the methodology and references.",
        )
        self.assertEqual(penalty, 0)
        self.assertIn("No common clickbait", reason)
        self.assertEqual(detail["caps_reason"], "No excessive capitalization detected")

    def test_core_validation_errors_from_fixtures(self) -> None:
        for sample in self.samples:
            if not sample["expectations"].get("should_error"):
                continue
            with self.subTest(sample_id=sample["id"]):
                with self.assertRaises(ToolValidationError):
                    score_source_credibility(sample["record"])

    def test_core_validation_non_dict_input(self) -> None:
        with self.assertRaises(ToolValidationError):
            score_source_credibility("not-a-dict")  # type: ignore[arg-type]

    def test_wrapper_normalizes_validation_error(self) -> None:
        result = safe_score_source_credibility({"url": "bad", "title": 123})  # type: ignore[dict-item]
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "ToolValidationError")
        self.assertIn("message", result["error"])
        self.assertIn("details", result["error"])

    def test_wrapper_normalizes_unexpected_exception(self) -> None:
        with patch("tool.score_source_credibility", side_effect=RuntimeError("boom")):
            result = safe_score_source_credibility({"url": "https://x.com", "title": "x"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["type"], "RuntimeError")
        self.assertEqual(result["error"]["message"], "Unexpected tool failure")


if __name__ == "__main__":
    unittest.main()
