import unittest
import json
import tempfile
import os
import shutil
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

# Fix path to allow importing scripts.opencode_dogfood
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.opencode_dogfood import lib

class TestRunnerValidators(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.schemas_dir = Path("scripts/opencode_dogfood/schemas").resolve()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_lib_importable(self):
        """P0.1: Assert lib module exists"""
        self.assertIsNotNone(lib, "scripts.opencode_dogfood.lib module missing")

    def test_evidence_sorting(self):
        """P0.1: Assert evidence sorted by path (LC_ALL=C equivalent)"""
        evidence = [
            {"path": "b.txt", "sha256": "1", "bytes": 10},
            {"path": "a.txt", "sha256": "2", "bytes": 20},
            {"path": "A.txt", "sha256": "3", "bytes": 30}
        ]
        if lib:
            sorted_evidence = lib.sort_evidence(evidence)
            # In C locale, 'A' < 'a' < 'b' usually, but python default sort is ascii/unicode code point.
            # 'A' (65) < 'a' (97).
            self.assertEqual(sorted_evidence[0]["path"], "A.txt")
            self.assertEqual(sorted_evidence[1]["path"], "a.txt")
            self.assertEqual(sorted_evidence[2]["path"], "b.txt")

    def test_schema_validation_valid(self):
        """P0.1: Valid result passes schema validation"""
        valid_result = {
            "schema_id": "opencode_dogfood_case_result",
            "schema_version": "1.0",
            "case_id": "T1C01",
            "stage": "T1",
            "status": "PASS",
            "run_id": "dogfood_20260101_120000",
            "duration_ms": 100,
            "model_id": "test",
            "transport": "test",
            "repo_commit": "a" * 40,
            "evidence": []
        }
        if lib:
            self.assertTrue(lib.validate_schema(valid_result, "case_result_v1.0.json"))

    def test_schema_validation_invalid_enum(self):
        """P0.1: Invalid status enum fails validation"""
        invalid_result = {
            "schema_id": "opencode_dogfood_case_result",
            "schema_version": "1.0",
            "case_id": "T1C01",
            "stage": "T1",
            "status": "MAYBE", # Invalid
            "run_id": "dogfood_20260101_120000",
            "duration_ms": 100,
            "model_id": "test",
            "transport": "test",
            "repo_commit": "a" * 40,
            "evidence": []
        }
        if lib:
            with self.assertRaises(ValueError):
                lib.validate_schema(invalid_result, "case_result_v1.0.json")

    def test_deletion_allowlist_fail(self):
        """P0.1: Deletion of non-allowed file triggers fail"""
        if lib:
            actual_deletions = ["deleted_file.txt"]
            # Empty allowlist
            with self.assertRaisesRegex(RuntimeError, "GITCLEANFAIL"):
                lib.enforce_deletion_policy([], actual_deletions)

    def test_delta_computation_deterministic(self):
        """P0.1: Delta files are renamed deterministically"""
        # delta list
        delta_files = ["log_b.json", "log_a.json"] # Unsorted
        if lib:
            renamed = lib.compute_deterministic_names(delta_files, prefix="item")
            # Should be sorted first: log_a, log_b
            # Then renamed: item_01, item_02
            self.assertEqual(renamed, {
                "log_a.json": "item_01.json",
                "log_b.json": "item_02.json"
            })

if __name__ == "__main__":
    unittest.main()
