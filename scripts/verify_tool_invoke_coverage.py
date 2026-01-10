#!/usr/bin/env python3
"""
Tool Invoke Coverage Verifier (Phase 2 Hardening).

This script verifies that symlink-defense tests execute (not skip) on non-Windows
platforms. On Windows, skips are expected and allowed.

Usage:
    python scripts/verify_tool_invoke_coverage.py [--strict]

Exit codes:
    0: Pass (all tests passed, and symlink tests ran on non-Windows)
    1: Fail (tests failed or symlink tests skipped on non-Windows)
"""

import subprocess
import sys
import json
import re
from pathlib import Path


# Symlink-related test names (patterns to match)
SYMLINK_TEST_PATTERNS = [
    "test_symlink_escape_blocked",
    "test_symlink_root_raises_governance_unavailable",
]


def run_pytest_with_report():
    """Run pytest and capture output for analysis."""
    cmd = [
        sys.executable, "-m", "pytest",
        "runtime/tests/test_tool_policy.py",
        "runtime/tests/test_tool_filesystem.py",
        "runtime/tests/test_pytest_runner.py",
        "runtime/tests/test_tool_invoke_integration.py",
        "-v", "--tb=short",
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,  # Repo root
    )
    
    return result


def parse_test_results(stdout: str):
    """Parse pytest output to extract pass/fail/skip counts and test names."""
    passed = 0
    failed = 0
    skipped = 0
    
    # Robust parsing: find counts regardless of order
    passed_match = re.search(r"(\d+)\s+passed", stdout)
    if passed_match:
        passed = int(passed_match.group(1))
        
    failed_match = re.search(r"(\d+)\s+failed", stdout)
    if failed_match:
        failed = int(failed_match.group(1))
        
    skipped_match = re.search(r"(\d+)\s+skipped", stdout)
    if skipped_match:
        skipped = int(skipped_match.group(1))
    
    # Find skipped test names
    skipped_tests = []
    for line in stdout.split("\n"):
        if "SKIPPED" in line:
            # Extract test name from line like "test_file.py::TestClass::test_name SKIPPED"
            match = re.search(r"::(\w+)\s+SKIPPED", line)
            if match:
                skipped_tests.append(match.group(1))
    
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "skipped_tests": skipped_tests,
    }


def check_symlink_tests_skipped(skipped_tests: list) -> list:
    """Check if any symlink-related tests were skipped."""
    skipped_symlink_tests = []
    for test_name in skipped_tests:
        for pattern in SYMLINK_TEST_PATTERNS:
            if pattern in test_name:
                skipped_symlink_tests.append(test_name)
                break
    return skipped_symlink_tests


def main():
    platform = sys.platform
    is_windows = platform.startswith("win")
    
    print(f"=== Tool Invoke Coverage Verifier ===")
    print(f"Platform: {platform}")
    print(f"Windows Mode: {is_windows}")
    print()
    
    # Run pytest
    print("Running pytest...")
    result = run_pytest_with_report()
    
    # Parse results
    stats = parse_test_results(result.stdout)
    
    print(f"\n=== Test Results ===")
    print(f"Passed:  {stats['passed']}")
    print(f"Failed:  {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")
    
    if stats['skipped_tests']:
        print(f"\nSkipped tests:")
        for test in stats['skipped_tests']:
            print(f"  - {test}")
    
    # Check for failures
    if stats['failed'] > 0:
        print(f"\n❌ FAIL: {stats['failed']} test(s) failed")
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        return 1
    
    # Check symlink test skips
    skipped_symlink = check_symlink_tests_skipped(stats['skipped_tests'])
    
    if skipped_symlink:
        if is_windows:
            print(f"\n⚠️  Windows: {len(skipped_symlink)} symlink test(s) skipped (expected)")
            for test in skipped_symlink:
                print(f"  - {test}")
            print("\n✅ PASS (Windows mode - symlink skips allowed)")
            return 0
        else:
            print(f"\n❌ FAIL: {len(skipped_symlink)} symlink test(s) skipped on non-Windows!")
            print("Symlink tests MUST run and pass on Linux/macOS.")
            for test in skipped_symlink:
                print(f"  - {test}")
            return 1
    
    print(f"\n✅ PASS: All {stats['passed']} tests passed")
    if not is_windows:
        print("   Symlink tests executed successfully on non-Windows platform.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
