"""Tests for CND-5: Safety Health Checks"""

import json
import os
import tempfile
import unittest

from runtime.amu0 import AMU0Lineage
from runtime.safety import check_amu0_chain_integrity, check_amu0_readability


class TestSafetyHealthChecks(unittest.TestCase):
    """Test health check functionality."""

    def test_amu0_readability_ok(self):
        """Valid AMU0 file passes readability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "lineage.json")
            with open(path, "w") as f:
                json.dump({"entries": []}, f)

            status = check_amu0_readability(path)
            self.assertTrue(status.ok)

    def test_amu0_readability_missing(self):
        """Missing AMU0 file fails readability check."""
        status = check_amu0_readability("/nonexistent/path.json")
        self.assertFalse(status.ok)

    def test_amu0_chain_integrity_ok(self):
        """Valid chain passes integrity check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "lineage.json")
            lineage = AMU0Lineage(path)
            lineage.append_entry("E1", "2025-01-01T00:00:00Z", "h1", {})

            status = check_amu0_chain_integrity(lineage)
            self.assertTrue(status.ok)


if __name__ == "__main__":
    unittest.main()
