from pathlib import Path
import json
import unittest

from report import render_report, write_report
from scorer import determine_verdict, reconcile_pair


class ReportTests(unittest.TestCase):
    def test_existing_attempt_renders_verdict_and_name(self):
        path = Path("attempts/KV_2_20260826T180319Z/record.json")
        record = json.loads(path.read_text(encoding="utf-8"))
        html = render_report(record)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("KV", html)
        self.assertIn("COMPLETION PASS", html)
        self.assertIn("Stakeholder Discovery", html)
        self.assertIn("Medora Community Health", html)
        self.assertNotIn("<script>", html.lower())

    def test_write_report_next_to_json(self):
        path = Path("attempts/Dummy_Selftest_1_20260826T163757Z/record.json")
        dest = Path("/tmp/cape-dummy-report.html")
        written = write_report(path, dest)
        self.assertTrue(written.exists())
        text = written.read_text(encoding="utf-8")
        self.assertIn("Dummy Selftest", text)
        self.assertIn("FDE Mindset", text)

    def test_html_escapes_markup(self):
        html = render_report(
            {
                "candidate_name": "<script>alert(1)</script>",
                "module_id": 1,
                "module_name": "Test",
                "domain": "retail",
                "tools": ["Claude"],
                "verdict": "FAIL — FULL TRAINING REQUIRED",
                "score_sheet": {
                    "module_score": 10,
                    "vector_score": 10,
                    "final_blended_score": 10,
                    "skill_final": {},
                    "vector_final": {},
                    "pass_a": {"skill_scores": {}, "vector_scores": {}, "evidence": {}},
                    "pass_b": {"skill_scores": {}, "vector_scores": {}, "evidence": {}},
                },
                "submission": {"written": "a < b", "code": ""},
                "defense_qa": [],
            }
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("a &lt; b", html)

    def test_scoring_math_unchanged(self):
        r = reconcile_pair(50, 75, threshold=25)
        self.assertFalse(r["borderline_review"])
        self.assertEqual(r["final"], 62.5)
        self.assertTrue(determine_verdict(80, True, False).startswith("BORDERLINE"))
        self.assertEqual(determine_verdict(40, False, False), "FAIL — FULL TRAINING REQUIRED")


if __name__ == "__main__":
    unittest.main()
