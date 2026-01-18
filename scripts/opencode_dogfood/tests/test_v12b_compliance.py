"""TDD Tests for v1.2b compliance: lint + schema + safety gates."""
import unittest
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.opencode_dogfood import lib

PLAN_PATH = PROJECT_ROOT / "artifacts/for_ceo/Plan_OpenCode_Dogfooding_v1.2b.md"

# Forbidden placeholder tokens (patterns that indicate unsubstituted placeholders)
# These are the actual placeholder syntaxes we want to forbid
FORBIDDEN_TOKENS = [
    r"<run_id>",
    r"<uuid>",
    r"<case_id>",
    r"<file>",
    r"<timestamp>",
    r"\(Logic Error\)",
    r"\(Crash\)",
    r"command / logic",  # Pseudocode indicator from v1.2a
]


class TestPlanLint(unittest.TestCase):
    """P0.1: Plan must have zero placeholder tokens."""

    def test_no_forbidden_tokens_in_plan(self):
        """Assert plan contains no forbidden placeholder tokens (excluding backtick-escaped)."""
        if not PLAN_PATH.exists():
            self.skipTest("Plan v1.2b not yet created")
        content = PLAN_PATH.read_text(encoding="utf-8")
        # Remove backtick-escaped content before checking
        import re
        content_no_backticks = re.sub(r"`[^`]+`", "", content)
        for token in FORBIDDEN_TOKENS:
            matches = list(re.finditer(token, content_no_backticks, re.IGNORECASE))
            self.assertEqual(
                len(matches), 0,
                f"Forbidden token '{token}' found {len(matches)} time(s) in plan"
            )


class TestSchemaCompliance(unittest.TestCase):
    """P0.1: Schema validation tests."""

    def test_case_result_requires_expected_outcome(self):
        """Case result must have expected_outcome field."""
        valid = {
            "schema_id": "opencode_dogfood_case_result",
            "schema_version": "1.0",
            "case_id": "T1C01",
            "stage": "T1",
            "expected_outcome": "SUCCESS",
            "actual_outcome": "SUCCESS",
            "status": "PASS",
            "failure_code": None,
            "run_id": "RUN_0001",
            "duration_ms": 100,
            "model_id": "test",
            "transport": "REST",
            "repo_commit": "a" * 40,
            "evidence": []
        }
        self.assertTrue(lib.validate_schema(valid, "case_result_v1.0.json"))

    def test_case_result_invalid_run_id_format(self):
        """run_id must match RUN_XXXX pattern."""
        invalid = {
            "schema_id": "opencode_dogfood_case_result",
            "schema_version": "1.0",
            "case_id": "T1C01",
            "stage": "T1",
            "expected_outcome": "SUCCESS",
            "actual_outcome": "SUCCESS",
            "status": "PASS",
            "failure_code": None,
            "run_id": "dogfood_20260117_120000",  # Old format
            "duration_ms": 100,
            "model_id": None,
            "transport": None,
            "repo_commit": "a" * 40,
            "evidence": []
        }
        with self.assertRaises(ValueError):
            lib.validate_schema(invalid, "case_result_v1.0.json")


class TestSafetyGates(unittest.TestCase):
    """P0.6: Safety rail tests."""

    def test_deletion_triggers_fail(self):
        """Any deletion with empty allowlist must trigger GITCLEANFAIL."""
        deletions = ["some_file.py"]
        with self.assertRaisesRegex(RuntimeError, "GITCLEANFAIL"):
            lib.enforce_deletion_policy([], deletions)

    def test_modification_allowlist_enforced(self):
        """Modifications outside allowlist must trigger fail."""
        allowlist = ["docs/zz_scratch/opencode_dogfood_probe.md"]
        modified = ["docs/INDEX.md"]  # Not in allowlist
        with self.assertRaisesRegex(RuntimeError, "MODIFICATIONFAIL"):
            lib.enforce_modification_policy(allowlist, modified)

    def test_modification_allowlist_pass(self):
        """Modifications inside allowlist must pass."""
        allowlist = ["docs/zz_scratch/opencode_dogfood_probe.md"]
        modified = ["docs/zz_scratch/opencode_dogfood_probe.md"]
        # Should not raise
        lib.enforce_modification_policy(allowlist, modified)


class TestEvidenceSorting(unittest.TestCase):
    """P0.7: Evidence must be sorted lexicographically."""

    def test_evidence_sorted_by_path(self):
        """Evidence list sorted by path (LC_ALL=C)."""
        unsorted = [
            {"path": "evidence/b.txt", "sha256": "1", "bytes": 10},
            {"path": "evidence/A.txt", "sha256": "2", "bytes": 20},
            {"path": "evidence/a.txt", "sha256": "3", "bytes": 30},
        ]
        sorted_ev = lib.sort_evidence(unsorted)
        # ASCII order: A (65) < a (97) < b (98)
        self.assertEqual(sorted_ev[0]["path"], "evidence/A.txt")
        self.assertEqual(sorted_ev[1]["path"], "evidence/a.txt")
        self.assertEqual(sorted_ev[2]["path"], "evidence/b.txt")


if __name__ == "__main__":
    unittest.main()
