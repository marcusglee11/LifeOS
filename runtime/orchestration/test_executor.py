"""
Test Executor - Pytest execution with timeout and output capture.

Phase 3a capability for autonomous test execution within strict bounds:
- Timeout enforcement (default 300s)
- Output capture and truncation (50KB limit)
- Structured result with exit code, status, and evidence
"""
from __future__ import annotations

import os
import subprocess
import signal
from dataclasses import dataclass
from typing import Optional, Dict, Any, Set
from pathlib import Path


# Maximum output size before truncation (50KB as per Phase 3a spec)
MAX_OUTPUT_SIZE = 50 * 1024  # 50KB

# Default timeout for pytest execution (5 minutes as per Phase 3a spec)
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass
class PytestResult:
    """
    Result of a pytest execution.

    Attributes:
        status: "PASS" | "FAIL" | "TIMEOUT"
        exit_code: pytest exit code (0=success, >0=failure, -N=signal)
        stdout: captured stdout (truncated at MAX_OUTPUT_SIZE)
        stderr: captured stderr (truncated at MAX_OUTPUT_SIZE)
        duration: wall-clock seconds
        evidence: structured evidence dict
        passed_tests: set of test names that passed (if parseable)
        failed_tests: set of test names that failed (if parseable)
        counts: dict with test counts (passed, failed, skipped)
        error_messages: list of error messages from failures
    """
    status: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    evidence: Dict[str, Any]
    passed_tests: Optional[Set[str]] = None
    failed_tests: Optional[Set[str]] = None
    counts: Optional[Dict[str, int]] = None
    error_messages: Optional[list] = None


class PytestExecutor:
    """
    Executor for pytest with timeout and output capture.

    Usage:
        executor = PytestExecutor(timeout=300)
        result = executor.run("runtime/tests/test_example.py")
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        """
        Initialize test executor.

        Args:
            timeout: Maximum seconds to allow for test execution
        """
        self.timeout = timeout

    def run(self, target: str, extra_args: Optional[list] = None) -> PytestResult:
        """
        Execute pytest on target path with timeout enforcement.

        P0-2 Hardening: Process group termination with SIGTERM → SIGKILL cascade
        to prevent orphaned child processes.

        Args:
            target: Path to test file or directory
            extra_args: Optional additional pytest arguments

        Returns:
            PytestResult with captured output and status
        """
        import time
        import os

        start_time = time.time()

        # Build pytest command
        cmd = ["pytest", target, "-v"]
        if extra_args:
            cmd.extend(extra_args)

        # Start pytest in new process group (session)
        # This allows us to kill the entire process tree
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path.cwd(),
            start_new_session=True,  # Create new process group
        )

        timeout_triggered = False
        exit_code = 0

        try:
            # Wait for process with timeout
            stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
            exit_code = process.returncode

        except subprocess.TimeoutExpired:
            # Timeout occurred - kill entire process group
            timeout_triggered = True

            # Step 1: Send SIGTERM to process group (graceful shutdown)
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass  # Process group already dead or no longer exists

            # Step 2: Wait grace period (1.5 seconds)
            time.sleep(1.5)

            # Step 3: Send SIGKILL to process group (forceful kill)
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass  # Process group already dead or no longer exists

            # Collect any partial output
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                # Process still hung, force kill
                process.kill()
                stdout_bytes, stderr_bytes = process.communicate()

            exit_code = -signal.SIGTERM

        # Decode output (handle both bytes and str)
        if isinstance(stdout_bytes, bytes):
            stdout_raw = stdout_bytes.decode("utf-8", errors="replace")
        else:
            stdout_raw = stdout_bytes or ""

        if isinstance(stderr_bytes, bytes):
            stderr_raw = stderr_bytes.decode("utf-8", errors="replace")
        else:
            stderr_raw = stderr_bytes or ""

        duration = time.time() - start_time

        # Determine status
        if timeout_triggered:
            status = "TIMEOUT"
        elif exit_code == 0:
            status = "PASS"
        else:
            status = "FAIL"

        # Truncate output if needed
        stdout = self._truncate_output(stdout_raw)
        stderr = self._truncate_output(stderr_raw)

        if not timeout_triggered:
            # Parse test results (only for non-timeout cases)
            counts, passed_tests, failed_tests, error_messages = self._parse_pytest_output(
                stdout_raw
            )

            # Build evidence
            evidence = self._build_evidence(
                target=target,
                exit_code=exit_code,
                status=status,
                duration=duration,
                stdout=stdout,
                stderr=stderr,
                counts=counts,
                truncated=len(stdout_raw) > MAX_OUTPUT_SIZE or len(stderr_raw) > MAX_OUTPUT_SIZE,
                timeout_triggered=False,
            )

            return PytestResult(
                status=status,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                evidence=evidence,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                counts=counts,
                error_messages=error_messages,
            )
        else:
            # Timeout case
            evidence = self._build_evidence(
                target=target,
                exit_code=exit_code,
                status="TIMEOUT",
                duration=duration,
                stdout=stdout,
                stderr=stderr,
                counts=None,
                truncated=False,
                timeout_triggered=True,
            )

            return PytestResult(
                status="TIMEOUT",
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                evidence=evidence,
            )

    def _truncate_output(self, output: str) -> str:
        """
        Truncate output at MAX_OUTPUT_SIZE boundary.

        Args:
            output: Raw output string

        Returns:
            Truncated output with marker if truncated
        """
        if len(output) <= MAX_OUTPUT_SIZE:
            return output

        return output[:MAX_OUTPUT_SIZE] + "\n\n[OUTPUT TRUNCATED AT 50KB LIMIT]"

    def _parse_pytest_output(self, stdout: str) -> tuple:
        """
        Parse pytest output to extract test counts and results.

        Args:
            stdout: pytest stdout output

        Returns:
            (counts dict, passed_tests set, failed_tests set, error_messages list)
        """
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        passed_tests = set()
        failed_tests = set()
        error_messages = []

        # Parse summary line like "1134 passed, 1 failed, 1 skipped"
        for line in stdout.splitlines():
            if "passed" in line or "failed" in line or "skipped" in line:
                # Try to extract counts
                import re
                passed_match = re.search(r"(\d+) passed", line)
                failed_match = re.search(r"(\d+) failed", line)
                skipped_match = re.search(r"(\d+) skipped", line)

                if passed_match:
                    counts["passed"] = int(passed_match.group(1))
                if failed_match:
                    counts["failed"] = int(failed_match.group(1))
                if skipped_match:
                    counts["skipped"] = int(skipped_match.group(1))

            # Capture FAILED lines
            if "FAILED" in line:
                # Extract test name from lines like "FAILED test_file.py::test_name"
                import re
                match = re.search(r"FAILED\s+(\S+)", line)
                if match:
                    failed_tests.add(match.group(1))

            # Capture PASSED lines
            if "PASSED" in line:
                import re
                match = re.search(r"PASSED\s+(\S+)", line)
                if match:
                    passed_tests.add(match.group(1))

        # Extract error messages from failure sections
        in_failure_section = False
        for line in stdout.splitlines():
            if "FAILED" in line or "ERROR" in line:
                in_failure_section = True
            if in_failure_section and ("AssertionError" in line or "Error:" in line):
                error_messages.append(line.strip())
                if len(error_messages) >= 10:  # Cap at 10 error messages
                    break

        return counts, passed_tests, failed_tests, error_messages

    def _build_evidence(
        self,
        target: str,
        exit_code: int,
        status: str,
        duration: float,
        stdout: str,
        stderr: str,
        counts: Optional[Dict[str, int]],
        truncated: bool,
        timeout_triggered: bool,
    ) -> Dict[str, Any]:
        """
        Build structured evidence dict for pytest execution.

        Args:
            target: Test target path
            exit_code: Process exit code
            status: Test status (PASS/FAIL/TIMEOUT)
            duration: Wall-clock seconds
            stdout: Captured stdout
            stderr: Captured stderr
            counts: Test counts dict
            truncated: Whether output was truncated
            timeout_triggered: Whether timeout occurred

        Returns:
            Evidence dict matching Phase 3a spec
        """
        return {
            "target": target,
            "exit_code": exit_code,
            "status": status,
            "duration_seconds": round(duration, 2),
            "test_counts": counts or {},
            "pytest_stdout": stdout,
            "pytest_stderr": stderr,
            "truncated": truncated,
            "timeout_triggered": timeout_triggered,
        }
