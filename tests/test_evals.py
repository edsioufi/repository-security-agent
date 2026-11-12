import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from google.adk.tools import FunctionTool

from evals.run import Budget
from tools import RepositoryTools
from tools.report import ReportTool


class EvalTests(unittest.TestCase):
    def test_report_schema_and_validation(self):
        tool = ReportTool(RepositoryTools("sample"))
        schema = FunctionTool(tool.submit_report)._get_declaration()
        self.assertIn("findings", schema.parameters_json_schema["properties"])
        context = SimpleNamespace(actions=SimpleNamespace(skip_summarization=False))
        result = tool.submit_report([], ["../outside"], "Limited review", context)
        self.assertFalse(result["accepted"])
        result = tool.submit_report([], ["app.py"], "Limited review", context)
        self.assertTrue(result["accepted"])
        self.assertTrue(context.actions.skip_summarization)

    def test_report_requires_real_evidence(self):
        tool = ReportTool(RepositoryTools("sample"))
        context = SimpleNamespace(actions=SimpleNamespace(skip_summarization=False))
        finding = dict(cwe="CWE-89", path="app.py", start_line=1, end_line=2,
                       evidence="invented", explanation="issue", fix="fix")
        self.assertFalse(tool.submit_report(
            [finding], ["app.py"], "Limited review", context
        )["accepted"])
        self.assertIsNone(tool.accepted)

    def test_budget_retains_unknown_usage_and_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            budget = Budget(Path(folder) / "ledger.json", .1)
            budget.reserve()
            budget.settle(None)
            budget.reserve()
            with self.assertRaises(RuntimeError):
                budget.reserve()
            self.assertEqual(budget.data["calls_reserved"], 2)


if __name__ == "__main__":
    unittest.main()


class ScoringTests(unittest.TestCase):
    def test_failure_and_missing_are_not_clean(self):
        from evals.score import classify
        case = {"category": "CWE-89", "vulnerable": False}
        self.assertEqual(classify(case, None, None), "incomplete")
        self.assertEqual(classify(case, {"status": "incomplete"}, None),
                         "incomplete")

    def test_positives_require_audit_and_empty_is_label_dependent(self):
        from evals.score import classify
        case = {"category": "CWE-89", "vulnerable": True}
        empty = {"status": "accepted", "report": {"findings": []}}
        self.assertEqual(classify(case, empty, None), "FN")
        hit = {"status": "accepted", "report": {"findings": [
            {"cwe": "CWE-89", "path": "app.py"}]}}
        self.assertEqual(classify(case, hit, None), "pending_audit")
        self.assertEqual(classify(
            case, hit, {"valid_target_finding": True}), "TP")
        self.assertEqual(classify(
            case, hit, {"valid_target_finding": False}), "FN")
