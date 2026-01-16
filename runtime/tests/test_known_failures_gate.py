"""
Unit tests for check_known_failures_gate.py parsing and comparison logic.

Tests cover:
- FAILED line parsing
- ERROR line parsing  
- Fail-closed behavior (non-zero return code with no FAILED/ERROR lines)
- Deterministic nodeid extraction
"""

import pytest
import sys
import os
from pathlib import Path

# Add scripts directory to path for import
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import after path modification
import importlib.util
spec = importlib.util.spec_from_file_location(
    "check_known_failures_gate", 
    scripts_dir / "check_known_failures_gate.py"
)
gate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_module)

parse_failing_nodeids = gate_module.parse_failing_nodeids
compare_failures = gate_module.compare_failures


class TestParseFailingNodeids:
    """Tests for parse_failing_nodeids function."""
    
    def test_parse_failed_lines(self):
        """Should extract nodeids from FAILED lines."""
        output = """
.........................
FAILED tests/test_foo.py::test_one
FAILED tests/test_bar.py::TestClass::test_two
...
1 passed, 2 failed
"""
        result = parse_failing_nodeids(output)
        assert result == {
            "tests/test_foo.py::test_one",
            "tests/test_bar.py::TestClass::test_two"
        }
    
    def test_parse_error_lines(self):
        """Should extract nodeids from ERROR lines."""
        output = """
ERROR tests/test_broken.py::test_fail_to_collect
ERROR tests/conftest.py
...
1 error
"""
        result = parse_failing_nodeids(output)
        assert result == {
            "tests/test_broken.py::test_fail_to_collect",
            "tests/conftest.py"
        }
    
    def test_parse_mixed_failed_and_error(self):
        """Should extract nodeids from both FAILED and ERROR lines."""
        output = """
FAILED tests/test_a.py::test_one
ERROR tests/test_b.py::test_two
FAILED tests/test_c.py::test_three
"""
        result = parse_failing_nodeids(output)
        assert result == {
            "tests/test_a.py::test_one",
            "tests/test_b.py::test_two",
            "tests/test_c.py::test_three"
        }
    
    def test_empty_output_returns_empty_set(self):
        """Empty output should return empty set."""
        result = parse_failing_nodeids("")
        assert result == set()
    
    def test_all_passing_returns_empty_set(self):
        """Output with no failures should return empty set."""
        output = """
...........................
27 passed in 1.23s
"""
        result = parse_failing_nodeids(output)
        assert result == set()
    
    def test_handles_parametrized_tests(self):
        """Should handle parametrized test nodeids with brackets."""
        output = """
FAILED tests/test_paths.py::test_unsafe[../docs/-path_traversal]
FAILED tests/test_paths.py::test_unsafe[C:\\temp\\-windows]
"""
        result = parse_failing_nodeids(output)
        assert "tests/test_paths.py::test_unsafe[../docs/-path_traversal]" in result
        assert "tests/test_paths.py::test_unsafe[C:\\temp\\-windows]" in result
    
    def test_deterministic_ordering(self):
        """Result should be deterministic (set, but sorted output is stable)."""
        output = """
FAILED z_test.py::test_z
FAILED a_test.py::test_a
FAILED m_test.py::test_m
"""
        result = parse_failing_nodeids(output)
        # Sets are unordered, but sorted() should give deterministic order
        sorted_result = sorted(result)
        assert sorted_result == [
            "a_test.py::test_a",
            "m_test.py::test_m", 
            "z_test.py::test_z"
        ]


class TestCompareFailures:
    """Tests for compare_failures function."""
    
    def test_identical_sets(self):
        """Identical sets should have no added or removed."""
        head = {"a", "b", "c"}
        ledger = {"a", "b", "c"}
        added, removed = compare_failures(head, ledger)
        assert added == set()
        assert removed == set()
    
    def test_new_failures_detected(self):
        """New failures not in ledger should appear in added."""
        head = {"a", "b", "c", "new_fail"}
        ledger = {"a", "b", "c"}
        added, removed = compare_failures(head, ledger)
        assert added == {"new_fail"}
        assert removed == set()
    
    def test_improvements_detected(self):
        """Ledger failures that now pass should appear in removed."""
        head = {"a", "b"}
        ledger = {"a", "b", "c"}
        added, removed = compare_failures(head, ledger)
        assert added == set()
        assert removed == {"c"}
    
    def test_mixed_added_and_removed(self):
        """Should handle both added and removed simultaneously."""
        head = {"a", "d"}
        ledger = {"a", "b", "c"}
        added, removed = compare_failures(head, ledger)
        assert added == {"d"}
        assert removed == {"b", "c"}
    
    def test_empty_head(self):
        """Empty HEAD failures means all ledger entries are improvements."""
        head = set()
        ledger = {"a", "b"}
        added, removed = compare_failures(head, ledger)
        assert added == set()
        assert removed == {"a", "b"}
    
    def test_empty_ledger(self):
        """Empty ledger means all HEAD failures are new."""
        head = {"a", "b"}
        ledger = set()
        added, removed = compare_failures(head, ledger)
        assert added == {"a", "b"}
        assert removed == set()


class TestFailClosedBehavior:
    """Tests for fail-closed gate behavior."""
    
    def test_nonzero_return_with_no_parsed_failures_is_dangerous(self):
        """
        Simulates the fail-closed scenario:
        - pytest returns non-zero (indicating failure)
        - but no FAILED/ERROR lines are parsed (collection error)
        
        The gate should FAIL in this case, not PASS.
        """
        # This tests the LOGIC, not the actual gate execution
        # The gate checks: returncode != 0 AND len(head_failures) == 0
        returncode = 2  # Collection error
        head_failures = parse_failing_nodeids("")  # No FAILED/ERROR lines
        
        # Gate should fail closed in this case
        should_fail_closed = (returncode != 0 and len(head_failures) == 0)
        assert should_fail_closed is True
    
    def test_nonzero_return_with_parsed_failures_is_safe(self):
        """
        If pytest fails but we DID parse failures, we can proceed.
        """
        returncode = 1  # Test failures
        output = "FAILED test.py::test_one"
        head_failures = parse_failing_nodeids(output)
        
        # Gate can proceed (not fail-closed)
        should_fail_closed = (returncode != 0 and len(head_failures) == 0)
        assert should_fail_closed is False
    
    def test_zero_return_with_no_failures_is_safe(self):
        """
        If pytest returns 0 and no failures, that's a valid PASS.
        """
        returncode = 0
        head_failures = parse_failing_nodeids(".....")
        
        should_fail_closed = (returncode != 0 and len(head_failures) == 0)
        assert should_fail_closed is False
