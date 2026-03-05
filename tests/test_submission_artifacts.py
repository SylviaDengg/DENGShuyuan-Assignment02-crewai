"""Submission artifact checks for assignment completeness."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SubmissionArtifactTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = [
            ROOT / "tool.py",
            ROOT / "demo.py",
            ROOT / "README.md",
            ROOT / "prompt-log.md",
        ]
        for path in required:
            with self.subTest(path=str(path)):
                self.assertTrue(path.exists(), f"Missing required file: {path}")

    def test_readme_contains_required_run_instructions(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("python demo.py", readme)

    def test_prompt_log_contains_latest_plan_and_testing_context(self) -> None:
        prompt_log = (ROOT / "prompt-log.md").read_text(encoding="utf-8")
        self.assertIn("Testing Plan: Source Credibility Heuristic Deliverables", prompt_log)
        self.assertIn("snapshot fixtures", prompt_log.lower())
        self.assertIn("unittest", prompt_log)
        self.assertIn("DeepSeek", prompt_log)


if __name__ == "__main__":
    unittest.main()
