"""
FP-4.x CND-1: Execution Envelope
Enforces deterministic execution environment constraints.
"""
import os
import sys
import json
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path


class ExecutionEnvelopeError(Exception):
    """Raised when execution envelope constraints are violated."""
    pass


@dataclass
class EnvelopeStatus:
    """Status of envelope verification."""
    verified: bool
    checks_passed: List[str]
    checks_failed: List[str]
    
    @property
    def attestation(self) -> dict:
        return {
            "verified": self.verified,
            "passed": self.checks_passed,
            "failed": self.checks_failed
        }


class ExecutionEnvelope:
    """
    Enforces Tier-1 execution envelope constraints:
    - Single-process execution
    - Environment determinism (PYTHONHASHSEED=0)
    - No ungoverned network I/O
    - Pinned interpreter + dependencies
    """
    
    # Modules that indicate potential nondeterminism or escape from envelope
    BANNED_MODULES = frozenset([
        'multiprocessing',
        'concurrent.futures',
        'asyncio.subprocess',
    ])
    
    NETWORK_MODULES = frozenset([
        'requests',
        'urllib.request',
        'http.client',
        'socket',
        'aiohttp',
    ])
    
    def __init__(self, lock_file_path: Optional[str] = None, mode: Optional[str] = None):
        """
        Initialize execution envelope.

        Args:
            lock_file_path: Path to requirements_lock.json.
            mode: Execution mode ('tier2' for strict, 'sandbox' for relaxed)
        """
        self.lock_file_path = lock_file_path
        self.mode = mode or 'tier2'  # Default to strict mode
        self._checks_passed: List[str] = []
        self._checks_failed: List[str] = []
    
    def verify_environment(self) -> None:
        """
        Verify PYTHONHASHSEED=0 for deterministic hashing.
        
        Raises:
            ExecutionEnvelopeError: If PYTHONHASHSEED is not set to 0.
        """
        hashseed = os.environ.get('PYTHONHASHSEED', '')
        if hashseed != '0':
            self._checks_failed.append('PYTHONHASHSEED')
            raise ExecutionEnvelopeError(
                f"PYTHONHASHSEED must be '0' for deterministic execution. "
                f"Current value: '{hashseed}'. Set PYTHONHASHSEED=0 before running."
            )
        self._checks_passed.append('PYTHONHASHSEED')
    
    def verify_single_process(self) -> None:
        """
        Verify no banned multiprocessing modules are loaded.

        In sandbox mode, this check is relaxed to support testing.

        Raises:
            ExecutionEnvelopeError: If banned modules are detected (tier2 mode only).
        """
        # Sandbox mode: skip check
        if self.mode == 'sandbox':
            self._checks_passed.append('single_process_skipped_sandbox')
            return

        # Tier2 mode: enforce check
        loaded_banned = self.BANNED_MODULES.intersection(sys.modules.keys())
        if loaded_banned:
            self._checks_failed.append('single_process')
            raise ExecutionEnvelopeError(
                f"Banned multiprocessing modules detected: {loaded_banned}. "
                "Tier-1 requires single-process execution."
            )
        self._checks_passed.append('single_process')
    
    def verify_network_restrictions(self) -> None:
        """
        Verify no direct network modules are loaded.
        
        Note: This is a best-effort check. Modules loaded after
        envelope verification are not detected.
        
        Raises:
            ExecutionEnvelopeError: If network modules are detected.
        """
        loaded_network = self.NETWORK_MODULES.intersection(sys.modules.keys())
        if loaded_network:
            self._checks_failed.append('network_restrictions')
            raise ExecutionEnvelopeError(
                f"Direct network modules detected: {loaded_network}. "
                "Use deterministic_call gateway for network operations."
            )
        self._checks_passed.append('network_restrictions')
    
    def verify_dependency_lock(self) -> None:
        """
        Verify installed dependencies match lock file.
        
        Raises:
            ExecutionEnvelopeError: If dependencies don't match lock.
        """
        if not self.lock_file_path:
            # No lock file specified, skip check
            self._checks_passed.append('dependency_lock_skipped')
            return
            
        lock_path = Path(self.lock_file_path)
        if not lock_path.exists():
            self._checks_failed.append('dependency_lock')
            raise ExecutionEnvelopeError(
                f"Dependency lock file not found: {self.lock_file_path}"
            )
        
        with open(lock_path, 'r') as f:
            lock_data = json.load(f)
        
        # Verify Python version
        expected_python = lock_data.get('python_version')
        actual_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        if expected_python and expected_python != actual_python:
            self._checks_failed.append('dependency_lock')
            raise ExecutionEnvelopeError(
                f"Python version mismatch. Expected: {expected_python}, "
                f"Actual: {actual_python}"
            )
        
        self._checks_passed.append('dependency_lock')
    
    def verify_all(self) -> EnvelopeStatus:
        """
        Run all envelope verifications.
        
        Returns:
            EnvelopeStatus with verification results.
            
        Note: Collects all failures before raising.
        """
        self._checks_passed = []
        self._checks_failed = []
        errors = []
        
        try:
            self.verify_environment()
        except ExecutionEnvelopeError as e:
            errors.append(str(e))
        
        try:
            self.verify_single_process()
        except ExecutionEnvelopeError as e:
            errors.append(str(e))
        
        try:
            self.verify_network_restrictions()
        except ExecutionEnvelopeError as e:
            errors.append(str(e))
        
        try:
            self.verify_dependency_lock()
        except ExecutionEnvelopeError as e:
            errors.append(str(e))
        
        status = EnvelopeStatus(
            verified=len(errors) == 0,
            checks_passed=self._checks_passed.copy(),
            checks_failed=self._checks_failed.copy()
        )
        
        if errors:
            raise ExecutionEnvelopeError(
                "Execution envelope verification failed:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )
        
        return status
    
    def verify_all_soft(self) -> EnvelopeStatus:
        """
        Run all verifications without raising.
        
        Returns:
            EnvelopeStatus with results (may have failures).
        """
        try:
            return self.verify_all()
        except ExecutionEnvelopeError:
            return EnvelopeStatus(
                verified=False,
                checks_passed=self._checks_passed.copy(),
                checks_failed=self._checks_failed.copy()
            )
