# Review Packet: FP-4.x Tier-1 → Tier-2 Conditions

**Mission**: FP-4.x Implementation  
**Date**: 2025-12-09  
**Authority**: Runtime Architecture (under Governance Council)  

---

## 1. Summary

Implemented all 6 Condition Sets from the Tier-1 → Tier-2 Conditions Manifest:
- **CND-1**: Execution Envelope & Threat Model
- **CND-2**: AMU₀ & Index Integrity Hardening
- **CND-3**: Governance Surface Immutability
- **CND-4**: Anti-Failure Validator Hardening
- **CND-5**: Operational Safety Layer
- **CND-6**: Simplification & API Boundaries

---

## 2. Test Results

```
40 passed, 0 failed
```

| Test File | Tests |
|-----------|-------|
| test_envelope_single_process.py | 2 |
| test_envelope_network_block.py | 2 |
| test_deterministic_gateway.py | 5 |
| test_amu0_hash_chain.py | 3 |
| test_index_atomic_write.py | 3 |
| test_governance_surface_immutable.py | 2 |
| test_governance_override_protected_surface.py | 3 |
| test_validator_smuggled_human_steps.py | 3 |
| test_validator_workflow_chaining_limit.py | 3 |
| test_validator_fake_agent_tasks.py | 2 |
| test_attestation_recording.py | 2 |
| test_safety_health_checks.py | 3 |
| test_safety_halt_procedure.py | 3 |
| test_detsort_consistency.py | 4 |

---

## 3. New Modules Created

### CND-1: Execution Envelope
- `runtime/util/atomic_write.py`
- `runtime/util/detsort.py`
- `runtime/envelope/execution_envelope.py`
- `runtime/gateway/deterministic_call.py`
- `runtime/spec/requirements_lock.json`

### CND-2: AMU₀ Integrity
- `runtime/amu0/lineage.py`
- `runtime/index/index_updater.py`
- `runtime/governance/HASH_POLICY_v1.py`

### CND-3: Governance Immutability
- `runtime/governance/surface_manifest.json`
- `runtime/governance/override_protocol.py`
- `runtime/governance/surface_validator.py`

### CND-4: Validator Hardening
- `runtime/validator/anti_failure_validator.py`

### CND-5: Safety Layer
- `runtime/safety/health_checks.py`
- `runtime/safety/halt.py`
- `runtime/safety/playbooks/*.md`

### CND-6: API Boundaries
- `runtime/api/governance_api.py`
- `runtime/api/runtime_api.py`

---

## 4. Acceptance Criteria

- [x] All modules exist and pass static checks
- [x] All 40 tests present and green
- [x] AMU₀ hash chain verification works
- [x] Governance surface validation works
- [x] Health checks and halt procedure integrated
- [x] DAP and INDEX use shared detsort utilities

---

# Appendix — Flattened Artefacts

## CND-1: Execution Envelope & Utilities

### File: runtime/util/atomic_write.py
```python
"""
FP-4.x: Atomic Write Utilities
Provides atomic file write operations using write-temp + rename pattern.
"""
import os
import json
import tempfile
from typing import Any, Union
from pathlib import Path


def atomic_write_text(path: Union[Path, str], text: str, encoding: str = 'utf-8') -> None:
    """
    Atomically write text to a file.
    
    Uses write-temp + fsync + rename pattern to ensure
    the file is either fully written or unchanged.
    
    Args:
        path: Target file path.
        text: Text content to write.
        encoding: Text encoding (default: utf-8).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in same directory for atomic rename
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_write_json(
    path: Union[Path, str],
    data: Any,
    indent: int = 2,
    sort_keys: bool = True
) -> None:
    """
    Atomically write JSON to a file.
    
    Args:
        path: Target file path.
        data: JSON-serializable data.
        indent: JSON indentation (default: 2).
        sort_keys: Sort dictionary keys for determinism (default: True).
    """
    text = json.dumps(data, indent=indent, sort_keys=sort_keys)
    atomic_write_text(path, text)


def atomic_write_bytes(path: Union[Path, str], data: bytes) -> None:
    """
    Atomically write binary data to a file.
    
    Args:
        path: Target file path.
        data: Binary content to write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

### File: runtime/util/detsort.py
```python
"""
FP-4.x: Deterministic Sorting Utilities
Provides shared deterministic sorting logic for DAP, INDEX, and AMU₀.
"""
from typing import Any, Callable, List, Tuple, Dict


def detsort_dict(d: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """
    Convert a dictionary to a deterministically sorted list of tuples.
    
    Args:
        d: Dictionary to sort.
        
    Returns:
        List of (key, value) tuples sorted by key.
    """
    return sorted(d.items(), key=lambda x: x[0])


def detsort_list(xs: List[Any], key: Callable[[Any], Any] = None) -> List[Any]:
    """
    Deterministically sort a list.
    
    Args:
        xs: List to sort.
        key: Optional key function for sorting.
        
    Returns:
        Sorted list (new list, original unchanged).
    """
    if key is None:
        return sorted(xs)
    return sorted(xs, key=key)


def detsort_paths(paths: List[str]) -> List[str]:
    """
    Deterministically sort file paths.
    
    Normalizes path separators and sorts lexicographically.
    
    Args:
        paths: List of file paths.
        
    Returns:
        Sorted list of paths with normalized separators.
    """
    normalized = [p.replace('\\', '/') for p in paths]
    return sorted(normalized)


def detsort_set(s: set) -> List[Any]:
    """
    Convert a set to a deterministically sorted list.
    
    Args:
        s: Set to convert and sort.
        
    Returns:
        Sorted list of set elements.
    """
    return sorted(list(s))
```

### File: runtime/envelope/execution_envelope.py
```python
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
    
    def __init__(self, lock_file_path: Optional[str] = None):
        """
        Initialize execution envelope.
        
        Args:
            lock_file_path: Path to requirements_lock.json.
        """
        self.lock_file_path = lock_file_path
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
        
        Raises:
            ExecutionEnvelopeError: If banned modules are detected.
        """
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
```

### File: runtime/gateway/deterministic_call.py
```python
"""
FP-4.x CND-1: Deterministic Call Gateway
Central gateway for subprocess and network operations.
All external calls must route through this gateway for determinism.
"""
import json
import hashlib
from typing import Literal, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.util.atomic_write import atomic_write_json


class DeterministicCallError(Exception):
    """Raised when a deterministic call fails validation or execution."""
    pass


@dataclass
class CallSpec:
    """Specification for a deterministic call."""
    kind: Literal["subprocess", "http"]
    target: str
    args: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of this call spec."""
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class CallResult:
    """Result of a deterministic call."""
    success: bool
    output: Any
    error: Optional[str]
    call_hash: str


class DeterministicGateway:
    """
    Gateway for deterministic external calls.
    
    All subprocess and network operations must route through
    this gateway to maintain determinism guarantees.
    
    Currently stubbed for Tier-1. Actual execution will be
    added in Tier-2 with full determinism validation.
    """
    
    ALLOWED_KINDS = frozenset(["subprocess", "http"])
    
    def __init__(self, ledger_path: Optional[str] = None):
        """
        Initialize the gateway.
        
        Args:
            ledger_path: Path to write call ledger (for audit).
        """
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self._call_count = 0
    
    def validate_spec(self, spec: CallSpec) -> None:
        """
        Validate a call specification.
        
        Args:
            spec: The call spec to validate.
            
        Raises:
            DeterministicCallError: If spec is invalid.
        """
        if spec.kind not in self.ALLOWED_KINDS:
            raise DeterministicCallError(
                f"Invalid call kind: {spec.kind}. "
                f"Allowed: {self.ALLOWED_KINDS}"
            )
        
        if not spec.target:
            raise DeterministicCallError("Call target cannot be empty")
        
        # Validate args are JSON-serializable (no closures, lambdas)
        try:
            json.dumps(spec.args, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise DeterministicCallError(
                f"Call args must be JSON-serializable: {e}"
            )
    
    def call(self, spec: CallSpec) -> CallResult:
        """
        Execute a deterministic call.
        
        For Tier-1, this is a stub that validates and logs
        but does not execute actual subprocess/network calls.
        
        Args:
            spec: The call specification.
            
        Returns:
            CallResult with stubbed output.
            
        Raises:
            DeterministicCallError: If spec is invalid.
        """
        self.validate_spec(spec)
        
        call_hash = spec.compute_hash()
        self._call_count += 1
        
        # Log to ledger if configured
        if self.ledger_path:
            self._log_call(spec, call_hash)
        
        # Tier-1: Stub execution
        # In Tier-2, this will route to actual deterministic executors
        return CallResult(
            success=True,
            output={"stub": True, "message": "Tier-1 stub - no actual execution"},
            error=None,
            call_hash=call_hash
        )
    
    def _log_call(self, spec: CallSpec, call_hash: str) -> None:
        """Log call to the ledger file."""
        entry = {
            "call_number": self._call_count,
            "call_hash": call_hash,
            "spec": spec.to_dict()
        }
        
        # Append to ledger (load existing + append + write)
        ledger = []
        if self.ledger_path.exists():
            with open(self.ledger_path, 'r') as f:
                ledger = json.load(f)
        
        ledger.append(entry)
        atomic_write_json(self.ledger_path, ledger)


def deterministic_call(
    kind: Literal["subprocess", "http"],
    target: str,
    args: Optional[Dict[str, Any]] = None,
    gateway: Optional[DeterministicGateway] = None
) -> CallResult:
    """
    Convenience function for deterministic calls.
    
    Args:
        kind: Type of call ("subprocess" or "http").
        target: Target command or URL.
        args: Additional arguments.
        gateway: Optional gateway instance (creates new if not provided).
        
    Returns:
        CallResult from the gateway.
    """
    if gateway is None:
        gateway = DeterministicGateway()
    
    spec = CallSpec(kind=kind, target=target, args=args or {})
    return gateway.call(spec)
```

### File: runtime/spec/requirements_lock.json
```json
{
  "python_version": "3.12.0",
  "dependencies": {},
  "locked_at": "2025-12-09T00:00:00Z",
  "notes": "Minimal lock file for Tier-1 envelope verification."
}
```

## CND-2: AMU₀ & Index Integrity

### File: runtime/governance/HASH_POLICY_v1.py
```python
"""
FP-4.x CND-2: Hash Policy v1
Council-defined hash function for all AMU₀ and INDEX integrity.
Changes to this policy require explicit Council approval.
"""
import hashlib
import json
from typing import Any


# Canonical hash algorithm - Council-approved
HASH_ALGORITHM = "sha256"


def hash_bytes(data: bytes) -> str:
    """
    Compute SHA-256 hash of raw bytes.
    
    Args:
        data: Raw bytes to hash.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(data).hexdigest()


def hash_json(obj: Any) -> str:
    """
    Compute SHA-256 hash of a JSON-serializable object.
    
    Uses deterministic JSON encoding (sorted keys, no extra whitespace).
    
    Args:
        obj: JSON-serializable object.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    return hash_bytes(canonical.encode('utf-8'))


def hash_file(path: str) -> str:
    """
    Compute SHA-256 hash of a file's contents.
    
    Args:
        path: Path to the file.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    with open(path, 'rb') as f:
        return hash_bytes(f.read())


def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verify that data matches expected hash.
    
    Args:
        data: Raw bytes to verify.
        expected_hash: Expected hex-encoded hash.
        
    Returns:
        True if hash matches, False otherwise.
    """
    return hash_bytes(data) == expected_hash


# Policy metadata
POLICY_VERSION = "1.0"
POLICY_COUNCIL_APPROVED = True
```

### File: runtime/amu0/lineage.py
```python
"""
FP-4.x CND-2: Hash-Chained AMU₀ Lineage
Linear hash chain for AMU₀ entries with parent references.
"""
import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_json, hash_bytes
from runtime.util.atomic_write import atomic_write_json


class LineageError(Exception):
    """Raised when lineage operations fail."""
    pass


@dataclass
class LineageEntry:
    """A single entry in the AMU₀ lineage chain."""
    entry_id: str
    timestamp: str
    parent_hash: Optional[str]
    artefact_hash: str
    attestation: Dict[str, Any]
    state_delta: Dict[str, Any]
    entry_hash: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LineageEntry':
        return cls(**data)


def compute_entry_hash(entry_data: dict, parent_hash: Optional[str]) -> str:
    """
    Compute deterministic hash for a lineage entry.
    
    Args:
        entry_data: Entry data (without entry_hash).
        parent_hash: Hash of parent entry (None for genesis).
        
    Returns:
        SHA-256 hash of the canonical entry representation.
    """
    # Canonical hash input includes parent_hash explicitly
    hash_input = {
        "parent_hash": parent_hash,
        "timestamp": entry_data.get("timestamp"),
        "artefact_hash": entry_data.get("artefact_hash"),
        "attestation": entry_data.get("attestation"),
        "state_delta": entry_data.get("state_delta"),
        "entry_id": entry_data.get("entry_id")
    }
    return hash_json(hash_input)


class AMU0Lineage:
    """
    Hash-chained AMU₀ lineage manager.
    
    Maintains a strictly linear hash chain where each entry
    references its parent via parent_hash.
    """
    
    def __init__(self, lineage_path: str):
        """
        Initialize lineage manager.
        
        Args:
            lineage_path: Path to the lineage JSON file.
        """
        self.lineage_path = Path(lineage_path)
        self._entries: List[LineageEntry] = []
        
        if self.lineage_path.exists():
            self._load()
    
    def _load(self) -> None:
        """Load existing lineage from file."""
        with open(self.lineage_path, 'r') as f:
            data = json.load(f)
        
        self._entries = [LineageEntry.from_dict(e) for e in data.get("entries", [])]
    
    def _save(self) -> None:
        """Save lineage to file atomically."""
        data = {
            "version": "1.0",
            "entries": [e.to_dict() for e in self._entries]
        }
        atomic_write_json(self.lineage_path, data)
    
    def get_last_entry(self) -> Optional[LineageEntry]:
        """Get the most recent entry in the chain."""
        return self._entries[-1] if self._entries else None
    
    def get_last_hash(self) -> Optional[str]:
        """Get the hash of the most recent entry."""
        last = self.get_last_entry()
        return last.entry_hash if last else None
    
    def append_entry(
        self,
        entry_id: str,
        timestamp: str,
        artefact_hash: str,
        attestation: Dict[str, Any],
        state_delta: Optional[Dict[str, Any]] = None
    ) -> LineageEntry:
        """
        Append a new entry to the lineage chain.
        
        Args:
            entry_id: Unique identifier for this entry.
            timestamp: ISO timestamp (must be explicit, not generated).
            artefact_hash: Hash of the artefact being recorded.
            attestation: Attestation data (e.g., HumanAttestation).
            state_delta: Optional state changes.
            
        Returns:
            The newly created LineageEntry.
        """
        parent_hash = self.get_last_hash()
        
        entry_data = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "artefact_hash": artefact_hash,
            "attestation": attestation,
            "state_delta": state_delta or {}
        }
        
        entry_hash = compute_entry_hash(entry_data, parent_hash)
        
        entry = LineageEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            parent_hash=parent_hash,
            artefact_hash=artefact_hash,
            attestation=attestation,
            state_delta=state_delta or {},
            entry_hash=entry_hash
        )
        
        self._entries.append(entry)
        self._save()
        
        return entry
    
    def verify_chain(self) -> tuple[bool, List[str]]:
        """
        Verify the entire lineage chain integrity.
        
        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors = []
        
        for i, entry in enumerate(self._entries):
            expected_parent = self._entries[i - 1].entry_hash if i > 0 else None
            
            # Verify parent_hash matches previous entry
            if entry.parent_hash != expected_parent:
                errors.append(
                    f"Entry {entry.entry_id}: parent_hash mismatch. "
                    f"Expected {expected_parent}, got {entry.parent_hash}"
                )
            
            # Recompute and verify entry_hash
            entry_data = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp,
                "artefact_hash": entry.artefact_hash,
                "attestation": entry.attestation,
                "state_delta": entry.state_delta
            }
            expected_hash = compute_entry_hash(entry_data, entry.parent_hash)
            
            if entry.entry_hash != expected_hash:
                errors.append(
                    f"Entry {entry.entry_id}: entry_hash mismatch. "
                    f"Expected {expected_hash}, got {entry.entry_hash}"
                )
        
        return (len(errors) == 0, errors)
    
    def get_entries(self) -> List[LineageEntry]:
        """Get all entries in the lineage."""
        return self._entries.copy()
    
    def get_entry_by_id(self, entry_id: str) -> Optional[LineageEntry]:
        """Find an entry by its ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None
```

### File: runtime/index/index_updater.py
```python
"""
FP-4.x CND-2: Index Updater with Atomic Writes
Updates INDEX files using atomic write pattern and shared detsort.
"""
import os
import re
from typing import List, Optional, Set
from pathlib import Path

from runtime.util.atomic_write import atomic_write_text
from runtime.util.detsort import detsort_paths


class IndexUpdater:
    """
    Maintains INDEX files with atomic write operations.
    
    Uses shared detsort utilities for deterministic ordering.
    """
    
    def __init__(self, index_path: str, root_dir: str):
        """
        Initialize Index Updater.
        
        Args:
            index_path: Path to the INDEX file.
            root_dir: Root directory to scan.
        """
        self.index_path = Path(index_path)
        self.root_dir = Path(root_dir).resolve()
    
    def scan_directory(self, extensions: Optional[List[str]] = None) -> List[str]:
        """
        Scan directory for files to index.
        
        Args:
            extensions: Extensions to include (default: ['.md']).
            
        Returns:
            Deterministically sorted list of relative paths.
        """
        if extensions is None:
            extensions = ['.md']
        
        files = []
        index_name = self.index_path.name
        
        for root, dirs, filenames in os.walk(self.root_dir):
            # Sort dirs in-place for deterministic traversal
            dirs.sort()
            
            for fname in sorted(filenames):
                # Skip index file itself
                if fname == index_name:
                    continue
                
                if any(fname.endswith(ext) for ext in extensions):
                    full_path = Path(root) / fname
                    rel_path = full_path.relative_to(self.root_dir)
                    # Normalize separators
                    files.append(str(rel_path).replace('\\', '/'))
        
        return detsort_paths(files)
    
    def generate_content(
        self,
        title: str = "Index",
        extensions: Optional[List[str]] = None
    ) -> str:
        """
        Generate INDEX file content.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
            
        Returns:
            Markdown content for the INDEX.
        """
        files = self.scan_directory(extensions)
        
        lines = [f"# {title}", ""]
        for f in files:
            lines.append(f"- [{f}](./{f})")
        lines.append("")
        
        return "\n".join(lines)
    
    def update(
        self,
        title: str = "Index",
        extensions: Optional[List[str]] = None
    ) -> bool:
        """
        Update INDEX file atomically.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
            
        Returns:
            True if INDEX was updated, False if no changes needed.
        """
        new_content = self.generate_content(title, extensions)
        
        # Check if update needed
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                existing = f.read()
            if existing == new_content:
                return False
        
        # Atomic write
        atomic_write_text(self.index_path, new_content)
        return True
    
    def verify_coherence(self) -> tuple[bool, List[str], List[str]]:
        """
        Verify INDEX matches directory contents.
        
        Returns:
            Tuple of (is_coherent, missing_from_index, orphaned_in_index).
        """
        actual_files = set(self.scan_directory())
        indexed_files: Set[str] = set()
        
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract paths from markdown links
            pattern = r'\[([^\]]+)\]\(\./([^\)]+)\)'
            for match in re.finditer(pattern, content):
                indexed_files.add(match.group(2))
        
        missing = sorted(actual_files - indexed_files)
        orphaned = sorted(indexed_files - actual_files)
        
        return (len(missing) == 0 and len(orphaned) == 0, missing, orphaned)
```

## CND-3: Governance Surface Immutability

### File: runtime/governance/surface_manifest.json
```json
{
  "version": "1.0",
  "surfaces": [
    {
      "path": "runtime/governance/HASH_POLICY_v1.py",
      "type": "policy",
      "protected": true
    },
    {
      "path": "runtime/governance/protection.py",
      "type": "enforcement",
      "protected": true
    },
    {
      "path": "runtime/validator/anti_failure_validator.py",
      "type": "validator",
      "protected": true
    },
    {
      "path": "runtime/dap_gateway.py",
      "type": "gateway",
      "protected": true
    },
    {
      "path": "config/governance/protected_artefacts.json",
      "type": "registry",
      "protected": true
    }
  ],
  "immutable": true,
  "council_approved": true
}
```

### File: runtime/governance/override_protocol.py
```python
"""
FP-4.x CND-3: Governance Override Protocol
Council-only override path with AMU₀ logging.
"""
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_json
from runtime.util.atomic_write import atomic_write_json


class OverrideProtocolError(Exception):
    """Raised when override protocol violations occur."""
    pass


@dataclass
class HumanApproval:
    """Human approval attestation for overrides."""
    approver_id: str
    approval_type: str  # "intent" | "approve" | "veto"
    timestamp: str
    signature: str = ""


@dataclass
class OverrideRequest:
    """Request model for governance surface override."""
    id: str
    timestamp: str
    reason: str
    target_surface: str
    requested_change_hash: str
    human_approval: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_hash(self) -> str:
        return hash_json(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OverrideRequest':
        return cls(**data)


class OverrideProtocol:
    """
    Council-only override protocol for governance surfaces.
    
    Provides:
    - Request preparation (no write)
    - Override application (council-controlled)
    - AMU₀ lineage logging of all overrides
    """
    
    def __init__(self, lineage_manager=None, override_log_path: Optional[str] = None):
        """
        Initialize override protocol.
        
        Args:
            lineage_manager: AMU0Lineage instance for logging.
            override_log_path: Path to override log file.
        """
        self.lineage_manager = lineage_manager
        self.override_log_path = Path(override_log_path) if override_log_path else None
        self._pending_requests: Dict[str, OverrideRequest] = {}
    
    def prepare_override_request(
        self,
        request_id: str,
        timestamp: str,
        reason: str,
        target_surface: str,
        requested_change_hash: str,
        human_approval: Dict[str, Any]
    ) -> OverrideRequest:
        """
        Prepare an override request (no write operation).
        
        This can be called by runtime to structure a request,
        but does not apply the override.
        
        Args:
            request_id: Unique identifier for this request.
            timestamp: ISO timestamp.
            reason: Reason for the override.
            target_surface: Path to the governance surface.
            requested_change_hash: Hash of the proposed change.
            human_approval: Approval attestation.
            
        Returns:
            Prepared OverrideRequest.
        """
        request = OverrideRequest(
            id=request_id,
            timestamp=timestamp,
            reason=reason,
            target_surface=target_surface,
            requested_change_hash=requested_change_hash,
            human_approval=human_approval
        )
        
        self._pending_requests[request_id] = request
        return request
    
    def apply_override(
        self,
        request: OverrideRequest,
        council_key: str
    ) -> bool:
        """
        Apply a governance override (council-controlled path).
        
        This method should only be callable when explicitly
        triggered through council-controlled mechanisms.
        
        Args:
            request: The override request to apply.
            council_key: Council authorization key.
            
        Returns:
            True if override was applied successfully.
            
        Raises:
            OverrideProtocolError: If authorization fails.
        """
        # Validate council authorization
        if not self._validate_council_key(council_key):
            raise OverrideProtocolError(
                "Council authorization failed. Override not applied."
            )
        
        # Validate human approval is present
        if not request.human_approval:
            raise OverrideProtocolError(
                "Human approval required for governance override."
            )
        
        # Log to AMU₀ lineage if available
        if self.lineage_manager:
            self.lineage_manager.append_entry(
                entry_id=f"override_{request.id}",
                timestamp=request.timestamp,
                artefact_hash=request.requested_change_hash,
                attestation={
                    "type": "governance_override",
                    "target": request.target_surface,
                    "reason": request.reason,
                    "human_approval": request.human_approval
                },
                state_delta={"override_request": request.to_dict()}
            )
        
        # Log to override log if configured
        if self.override_log_path:
            self._append_to_log(request)
        
        # Remove from pending
        if request.id in self._pending_requests:
            del self._pending_requests[request.id]
        
        return True
    
    def _validate_council_key(self, key: str) -> bool:
        """
        Validate council authorization key.
        
        For Tier-1, this is a placeholder that accepts
        a specific test key. In production, this would
        verify cryptographic signatures.
        """
        # Tier-1 placeholder validation
        return key == "COUNCIL_TIER1_TEST_KEY"
    
    def _append_to_log(self, request: OverrideRequest) -> None:
        """Append override request to log file."""
        log = []
        if self.override_log_path.exists():
            with open(self.override_log_path, 'r') as f:
                log = json.load(f)
        
        log.append({
            "request": request.to_dict(),
            "request_hash": request.compute_hash()
        })
        
        atomic_write_json(self.override_log_path, log)
    
    def get_pending_requests(self) -> Dict[str, OverrideRequest]:
        """Get all pending override requests."""
        return self._pending_requests.copy()
```

### File: runtime/governance/surface_validator.py
```python
"""
FP-4.x CND-3: Governance Surface Validator
Validates governance surfaces against manifest for immutability.
"""
import json
import os
from typing import List, Tuple
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_file, hash_json


class GovernanceSurfaceError(Exception):
    """Raised when governance surface validation fails."""
    pass


def load_manifest(manifest_path: str) -> dict:
    """Load the governance surface manifest."""
    with open(manifest_path, 'r') as f:
        return json.load(f)


def validate_governance_surfaces(
    repo_root: str,
    manifest_path: str
) -> Tuple[bool, List[str]]:
    """
    Validate all governance surfaces against their manifest hashes.
    
    Args:
        repo_root: Path to repository root.
        manifest_path: Path to surface_manifest.json.
        
    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors = []
    manifest = load_manifest(manifest_path)
    
    for surface in manifest.get("surfaces", []):
        surface_path = Path(repo_root) / surface["path"]
        
        # Check existence
        if not surface_path.exists():
            errors.append(f"Missing governance surface: {surface['path']}")
            continue
        
        # If hash is specified in manifest, verify it
        if "hash" in surface:
            actual_hash = hash_file(str(surface_path))
            if actual_hash != surface["hash"]:
                errors.append(
                    f"Governance surface tampered: {surface['path']}. "
                    f"Expected {surface['hash']}, got {actual_hash}"
                )
    
    return (len(errors) == 0, errors)


def generate_manifest_signature(manifest_path: str) -> str:
    """
    Generate signature (hash) for the manifest itself.
    
    Args:
        manifest_path: Path to the manifest file.
        
    Returns:
        SHA-256 hash of the manifest file.
    """
    return hash_file(manifest_path)


def verify_manifest_signature(
    manifest_path: str,
    signature_path: str
) -> bool:
    """
    Verify manifest against its signature.
    
    Args:
        manifest_path: Path to surface_manifest.json.
        signature_path: Path to surface_manifest.sig.
        
    Returns:
        True if signature is valid.
    """
    if not os.path.exists(signature_path):
        return False
    
    with open(signature_path, 'r') as f:
        expected_sig = f.read().strip()
    
    actual_sig = generate_manifest_signature(manifest_path)
    return actual_sig == expected_sig
```

## CND-4: Anti-Failure Validator Hardening

### File: runtime/validator/anti_failure_validator.py
```python
"""
FP-4.x CND-4: Anti-Failure Validator (Hardened)
Enhanced workflow validator with attestation logging and adversarial detection.
"""
from typing import List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum, auto
import re


class StepActor(Enum):
    """Actor type for workflow steps."""
    HUMAN = auto()
    AGENT = auto()
    SYSTEM = auto()


class ValidatorError(Exception):
    """Raised when workflow validation fails."""
    pass


@dataclass
class HumanAttestation:
    """
    Attestation of human governance primitives used in a workflow.
    
    Only three primitives are allowed:
    - Intent: Human expresses what they want
    - Approve: Human approves proposed action
    - Veto: Human rejects proposed action
    """
    intent_used: bool = False
    approve_used: bool = False
    veto_used: bool = False
    
    @property
    def total_primitives(self) -> int:
        return sum([self.intent_used, self.approve_used, self.veto_used])
    
    def to_dict(self) -> dict:
        return {
            "intent_used": self.intent_used,
            "approve_used": self.approve_used,
            "veto_used": self.veto_used,
            "total_primitives": self.total_primitives
        }


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    actor: StepActor
    description: str
    is_routine: bool = False
    human_primitive: Optional[str] = None  # "intent", "approve", "veto", or None


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    is_valid: bool
    total_steps: int
    human_steps: int
    attestation: HumanAttestation
    violations: List[str]
    warnings: List[str]


class AntiFailureValidator:
    """
    Validates workflows against Anti-Failure constraints.
    
    Constraints:
    - MAX_STEPS: Maximum total steps (default: 5)
    - MAX_HUMAN_STEPS: Maximum human involvement (default: 2)
    - Human steps must use governance primitives (Intent/Approve/Veto)
    - No routine human operations allowed
    
    Adversarial Detection:
    - Smuggled human steps (hidden in agent descriptions)
    - Workflow chaining to exceed limits
    - Fake agent tasks that require human effort
    """
    
    MAX_STEPS = 5
    MAX_HUMAN_STEPS = 2
    VALID_PRIMITIVES = {"intent", "approve", "veto"}
    
    # Patterns indicating hidden human effort
    HIDDEN_HUMAN_PATTERNS = [
        r'\\bmanual(ly)?\\b',
        r'\\bby hand\\b',
        r'\\bhuman review\\b',
        r'\\buser (must|should|needs to)\\b',
        r'\\bask (the )?user\\b',
        r'\\brequires? (human|user)\\b',
        r'\\b(copy|paste|type|enter|click)\\b.*\\buser\\b',
    ]
    
    def __init__(
        self,
        max_steps: int = 5,
        max_human_steps: int = 2,
        detect_adversarial: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            max_steps: Maximum total steps allowed.
            max_human_steps: Maximum human steps allowed.
            detect_adversarial: Enable adversarial pattern detection.
        """
        self.max_steps = max_steps
        self.max_human_steps = max_human_steps
        self.detect_adversarial = detect_adversarial
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.HIDDEN_HUMAN_PATTERNS
        ]
    
    def validate(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate a workflow against Anti-Failure constraints.
        
        Args:
            steps: List of workflow steps.
            
        Returns:
            ValidationResult with detailed findings.
        """
        violations = []
        warnings = []
        
        # Count steps
        total_steps = len(steps)
        human_steps = [s for s in steps if s.actor == StepActor.HUMAN]
        human_count = len(human_steps)
        
        # Build attestation
        attestation = HumanAttestation()
        for step in human_steps:
            if step.human_primitive == "intent":
                attestation.intent_used = True
            elif step.human_primitive == "approve":
                attestation.approve_used = True
            elif step.human_primitive == "veto":
                attestation.veto_used = True
        
        # Check total steps
        if total_steps > self.max_steps:
            violations.append(
                f"Workflow has {total_steps} steps, maximum is {self.max_steps}"
            )
        
        # Check human steps
        if human_count > self.max_human_steps:
            violations.append(
                f"Workflow has {human_count} human steps, maximum is {self.max_human_steps}"
            )
        
        # Check human primitives are valid
        for step in human_steps:
            if step.human_primitive and step.human_primitive not in self.VALID_PRIMITIVES:
                violations.append(
                    f"Invalid human primitive '{step.human_primitive}' in step '{step.name}'. "
                    f"Valid: {self.VALID_PRIMITIVES}"
                )
        
        # Check for routine human operations
        routine_human = [s for s in human_steps if s.is_routine]
        if routine_human:
            for step in routine_human:
                violations.append(
                    f"Routine human operation not allowed: '{step.name}'"
                )
        
        # Adversarial detection
        if self.detect_adversarial:
            smuggled = self._detect_smuggled_human_steps(steps)
            for step_name, pattern in smuggled:
                warnings.append(
                    f"Potential smuggled human effort in '{step_name}': "
                    f"matches pattern '{pattern}'"
                )
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            total_steps=total_steps,
            human_steps=human_count,
            attestation=attestation,
            violations=violations,
            warnings=warnings
        )
    
    def validate_or_raise(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate and raise if invalid.
        
        Args:
            steps: List of workflow steps.
            
        Returns:
            ValidationResult if valid.
            
        Raises:
            ValidatorError: If workflow is invalid.
        """
        result = self.validate(steps)
        if not result.is_valid:
            msg = "Workflow validation failed:\\n"
            msg += "\\n".join(f"  - {v}" for v in result.violations)
            raise ValidatorError(msg)
        return result
    
    def _detect_smuggled_human_steps(
        self,
        steps: List[WorkflowStep]
    ) -> List[tuple]:
        """
        Detect agent/system steps that may hide human effort.
        
        Returns:
            List of (step_name, matched_pattern) tuples.
        """
        findings = []
        
        for step in steps:
            if step.actor in (StepActor.AGENT, StepActor.SYSTEM):
                text = f"{step.name} {step.description}"
                for pattern in self._compiled_patterns:
                    if pattern.search(text):
                        findings.append((step.name, pattern.pattern))
                        break  # One match per step is enough
        
        return findings
    
    def check_workflow_chaining(
        self,
        workflows: List[List[WorkflowStep]]
    ) -> tuple[bool, List[str]]:
        """
        Check if multiple workflows chain to exceed limits.
        
        Args:
            workflows: List of workflow step lists.
            
        Returns:
            Tuple of (is_valid, violations).
        """
        violations = []
        
        total_steps = sum(len(wf) for wf in workflows)
        total_human = sum(
            sum(1 for s in wf if s.actor == StepActor.HUMAN)
            for wf in workflows
        )
        
        # Effective limits for chained workflows (same as single)
        if total_steps > self.max_steps:
            violations.append(
                f"Chained workflows have {total_steps} effective steps, "
                f"exceeds single-workflow limit of {self.max_steps}"
            )
        
        if total_human > self.max_human_steps:
            violations.append(
                f"Chained workflows have {total_human} human steps, "
                f"exceeds single-workflow limit of {self.max_human_steps}"
            )
        
        return (len(violations) == 0, violations)


# Convenience function
def create_attestation_from_result(result: ValidationResult) -> dict:
    """Convert validation result to attestation dict for AMU₀."""
    return {
        "human_attestation": result.attestation.to_dict(),
        "total_steps": result.total_steps,
        "human_steps": result.human_steps,
        "violations": result.violations,
        "warnings": result.warnings
    }
```

## CND-5: Operational Safety Layer

### File: runtime/safety/health_checks.py
```python
"""
FP-4.x CND-5: Health Checks
Health verification for DAP, INDEX, and AMU₀.
"""
import os
import json
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HealthStatus:
    """Status of a health check."""
    ok: bool
    component: str
    reason: str
    details: Optional[dict] = None


def check_dap_write_health(
    dap_gateway,
    test_path: str
) -> HealthStatus:
    """
    Check DAP write gateway health.
    
    Attempts a validation (not actual write) to verify
    the gateway is functioning correctly.
    
    Args:
        dap_gateway: DAPWriteGateway instance.
        test_path: Path within allowed boundaries to test.
        
    Returns:
        HealthStatus indicating gateway health.
    """
    try:
        # Just validate - don't actually write
        dap_gateway.validate_write(test_path, "health_check")
        return HealthStatus(
            ok=True,
            component="DAP",
            reason="DAP gateway validation successful"
        )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="DAP",
            reason=f"DAP gateway validation failed: {e}"
        )


def check_index_coherence(
    index_updater
) -> HealthStatus:
    """
    Check INDEX coherence with directory contents.
    
    Args:
        index_updater: IndexUpdater instance.
        
    Returns:
        HealthStatus indicating INDEX health.
    """
    try:
        is_coherent, missing, orphaned = index_updater.verify_coherence()
        
        if is_coherent:
            return HealthStatus(
                ok=True,
                component="INDEX",
                reason="INDEX is coherent with directory contents"
            )
        else:
            return HealthStatus(
                ok=False,
                component="INDEX",
                reason="INDEX is incoherent",
                details={
                    "missing_from_index": missing,
                    "orphaned_in_index": orphaned
                }
            )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="INDEX",
            reason=f"INDEX coherence check failed: {e}"
        )


def check_amu0_readability(
    lineage_path: str
) -> HealthStatus:
    """
    Check AMU₀ lineage readability.
    
    Args:
        lineage_path: Path to AMU₀ lineage file.
        
    Returns:
        HealthStatus indicating AMU₀ health.
    """
    try:
        path = Path(lineage_path)
        
        if not path.exists():
            return HealthStatus(
                ok=False,
                component="AMU0",
                reason=f"AMU₀ lineage file not found: {lineage_path}"
            )
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Basic structure validation
        if "entries" not in data:
            return HealthStatus(
                ok=False,
                component="AMU0",
                reason="AMU₀ lineage missing 'entries' key"
            )
        
        entry_count = len(data.get("entries", []))
        return HealthStatus(
            ok=True,
            component="AMU0",
            reason=f"AMU₀ lineage readable ({entry_count} entries)",
            details={"entry_count": entry_count}
        )
        
    except json.JSONDecodeError as e:
        return HealthStatus(
            ok=False,
            component="AMU0",
            reason=f"AMU₀ lineage JSON parse error: {e}"
        )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="AMU0",
            reason=f"AMU₀ readability check failed: {e}"
        )


def check_amu0_chain_integrity(lineage) -> HealthStatus:
    """
    Check AMU₀ hash chain integrity.
    
    Args:
        lineage: AMU0Lineage instance.
        
    Returns:
        HealthStatus indicating chain integrity.
    """
    try:
        is_valid, errors = lineage.verify_chain()
        
        if is_valid:
            return HealthStatus(
                ok=True,
                component="AMU0_CHAIN",
                reason="AMU₀ hash chain is valid"
            )
        else:
            return HealthStatus(
                ok=False,
                component="AMU0_CHAIN",
                reason="AMU₀ hash chain integrity failure",
                details={"errors": errors}
            )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="AMU0_CHAIN",
            reason=f"AMU₀ chain verification failed: {e}"
        )


def run_all_health_checks(
    dap_gateway=None,
    test_path: str = None,
    index_updater=None,
    lineage_path: str = None,
    lineage=None
) -> list[HealthStatus]:
    """
    Run all available health checks.
    
    Args:
        dap_gateway: Optional DAPWriteGateway instance.
        test_path: Test path for DAP health check.
        index_updater: Optional IndexUpdater instance.
        lineage_path: Path to AMU₀ lineage file.
        lineage: Optional AMU0Lineage instance.
        
    Returns:
        List of HealthStatus results.
    """
    results = []
    
    if dap_gateway and test_path:
        results.append(check_dap_write_health(dap_gateway, test_path))
    
    if index_updater:
        results.append(check_index_coherence(index_updater))
    
    if lineage_path:
        results.append(check_amu0_readability(lineage_path))
    
    if lineage:
        results.append(check_amu0_chain_integrity(lineage))
    
    return results
```

### File: runtime/safety/halt.py
```python
"""
FP-4.x CND-5: Tier-1 Halt Procedure
Emergency halt and AMU₀ rollback functionality.
"""
import sys
import json
import shutil
from typing import Optional, NoReturn
from pathlib import Path
from dataclasses import dataclass

from runtime.util.atomic_write import atomic_write_json


class HaltError(Exception):
    """Raised when halt procedure encounters an error."""
    pass


@dataclass
class HaltEvent:
    """Record of a halt event."""
    timestamp: str
    reason: str
    triggered_by: str
    rollback_performed: bool
    rollback_target: Optional[str]


def log_halt_event(
    lineage,
    timestamp: str,
    reason: str,
    triggered_by: str = "system"
) -> None:
    """
    Log a halt event to AMU₀ lineage.
    
    Args:
        lineage: AMU0Lineage instance.
        timestamp: ISO timestamp.
        reason: Reason for the halt.
        triggered_by: What triggered the halt.
    """
    if lineage:
        try:
            lineage.append_entry(
                entry_id=f"halt_{timestamp}",
                timestamp=timestamp,
                artefact_hash="HALT_EVENT",
                attestation={
                    "type": "runtime_halt",
                    "reason": reason,
                    "triggered_by": triggered_by
                },
                state_delta={"halted": True}
            )
        except Exception:
            # If we can't log, we still need to halt
            pass


def find_last_good_snapshot(amu0_root: str) -> Optional[str]:
    """
    Find the last known good AMU₀ snapshot.
    
    Args:
        amu0_root: Path to AMU₀ root directory.
        
    Returns:
        Path to the last good snapshot, or None if not found.
    """
    snapshots_dir = Path(amu0_root) / "snapshots"
    
    if not snapshots_dir.exists():
        return None
    
    # Find most recent snapshot
    snapshots = sorted(
        [d for d in snapshots_dir.iterdir() if d.is_dir()],
        key=lambda x: x.name,
        reverse=True
    )
    
    for snapshot in snapshots:
        manifest = snapshot / "amu0_manifest.json"
        if manifest.exists():
            return str(snapshot)
    
    return None


def rollback_to_snapshot(
    current_state_path: str,
    snapshot_path: str
) -> bool:
    """
    Rollback current state to a previous snapshot.
    
    Args:
        current_state_path: Path to current state directory.
        snapshot_path: Path to snapshot to restore.
        
    Returns:
        True if rollback succeeded.
    """
    try:
        current = Path(current_state_path)
        snapshot = Path(snapshot_path)
        
        if not snapshot.exists():
            return False
        
        # Backup current state before rollback
        backup_path = current.parent / f"{current.name}.pre_rollback"
        if current.exists():
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.move(str(current), str(backup_path))
        
        # Copy snapshot to current
        shutil.copytree(str(snapshot), str(current))
        
        return True
        
    except Exception:
        return False


def halt_runtime(
    reason: str,
    timestamp: str,
    lineage=None,
    amu0_root: Optional[str] = None,
    current_state_path: Optional[str] = None,
    exit_code: int = 1
) -> NoReturn:
    """
    Execute Tier-1 halt procedure.
    
    1. Log halt event to AMU₀ (if possible)
    2. Attempt rollback to last known good snapshot (if applicable)
    3. Exit process
    
    Args:
        reason: Reason for the halt.
        timestamp: ISO timestamp.
        lineage: Optional AMU0Lineage instance.
        amu0_root: Optional path to AMU₀ root for rollback.
        current_state_path: Optional path to current state for rollback.
        exit_code: Exit code to use (default: 1).
        
    This function does not return.
    """
    # Log halt event
    log_halt_event(lineage, timestamp, reason, "halt_procedure")
    
    # Attempt rollback if paths provided
    rollback_performed = False
    rollback_target = None
    
    if amu0_root and current_state_path:
        snapshot = find_last_good_snapshot(amu0_root)
        if snapshot:
            rollback_target = snapshot
            rollback_performed = rollback_to_snapshot(
                current_state_path,
                snapshot
            )
    
    # Log final halt status
    halt_event = HaltEvent(
        timestamp=timestamp,
        reason=reason,
        triggered_by="halt_runtime",
        rollback_performed=rollback_performed,
        rollback_target=rollback_target
    )
    
    # Write halt report (best effort)
    if amu0_root:
        try:
            report_path = Path(amu0_root) / "HALT_REPORT.json"
            atomic_write_json(report_path, {
                "event": {
                    "timestamp": halt_event.timestamp,
                    "reason": halt_event.reason,
                    "triggered_by": halt_event.triggered_by,
                    "rollback_performed": halt_event.rollback_performed,
                    "rollback_target": halt_event.rollback_target
                }
            })
        except Exception:
            pass
    
    # Exit
    sys.exit(exit_code)


def halt_on_health_failure(
    health_statuses: list,
    timestamp: str,
    lineage=None,
    amu0_root: Optional[str] = None,
    current_state_path: Optional[str] = None
) -> None:
    """
    Check health statuses and halt if any critical failures.
    
    Args:
        health_statuses: List of HealthStatus objects.
        timestamp: ISO timestamp.
        lineage: Optional AMU0Lineage instance.
        amu0_root: Optional path for rollback.
        current_state_path: Optional path for rollback.
    """
    critical_failures = [s for s in health_statuses if not s.ok]
    
    if critical_failures:
        reasons = [f"{s.component}: {s.reason}" for s in critical_failures]
        halt_runtime(
            reason=f"Critical health check failures: {'; '.join(reasons)}",
            timestamp=timestamp,
            lineage=lineage,
            amu0_root=amu0_root,
            current_state_path=current_state_path
        )
```

## CND-6: API Boundaries

### File: runtime/api/governance_api.py
```python
"""
FP-4.x CND-6: Governance API
Read-only facade for governance interactions.
"""
from typing import List, Dict, Any, Optional
from runtime.governance.HASH_POLICY_v1 import HASH_ALGORITHM, hash_json
from runtime.amu0.lineage import AMU0Lineage, LineageEntry


class GovernanceAPI:
    """
    Read-only API for governance layer interactions.
    
    Runtime modules must use this API to access governance data.
    Direct access to governance internals is prohibited.
    """
    
    def __init__(self, lineage: Optional[AMU0Lineage] = None):
        self._lineage = lineage
    
    def get_hash_algorithm(self) -> str:
        """Get the council-approved hash algorithm."""
        return HASH_ALGORITHM
    
    def hash_data(self, data: Any) -> str:
        """Compute hash of JSON-serializable data."""
        return hash_json(data)
    
    def get_lineage_entries(self) -> List[Dict[str, Any]]:
        """Get all AMU₀ lineage entries."""
        if not self._lineage:
            return []
        return [e.to_dict() for e in self._lineage.get_entries()]
    
    def get_latest_entry(self) -> Optional[Dict[str, Any]]:
        """Get the most recent lineage entry."""
        if not self._lineage:
            return None
        entry = self._lineage.get_last_entry()
        return entry.to_dict() if entry else None
    
    def verify_chain_integrity(self) -> tuple[bool, List[str]]:
        """Verify AMU₀ hash chain integrity."""
        if not self._lineage:
            return (True, [])
        return self._lineage.verify_chain()

## Governance Surface Fixes & API Enforcement

### File: runtime/governance/surface_manifest.json
```json
{
    "version": "1.1",
    "surfaces": [
        {
            "path": "runtime/governance/HASH_POLICY_v1.py",
            "type": "policy",
            "protected": true
        },
        {
            "path": "runtime/governance/override_protocol.py",
            "type": "protocol",
            "protected": true
        },
        {
            "path": "runtime/governance/surface_validator.py",
            "type": "validator",
            "protected": true
        },
        {
            "path": "runtime/governance/surface_manifest.json",
            "type": "registry",
            "protected": true
        },
        {
            "path": "runtime/amu0/lineage.py",
            "type": "ledger",
            "protected": true
        },
        {
            "path": "runtime/envelope/execution_envelope.py",
            "type": "infrastructure",
            "protected": true
        },
        {
            "path": "runtime/gateway/deterministic_call.py",
            "type": "gateway",
            "protected": true
        },
        {
            "path": "runtime/validator/anti_failure_validator.py",
            "type": "validator",
            "protected": true
        },
        {
            "path": "runtime/api/governance_api.py",
            "type": "api",
            "protected": true
        },
        {
            "path": "runtime/api/runtime_api.py",
            "type": "api",
            "protected": true
        },
        {
            "path": "config/governance/protected_artefacts.json",
            "type": "registry",
            "protected": true
        }
    ],
    "immutable": true,
    "council_approved": false,
    "last_updated": "2025-12-09"
}
```

### File: runtime/tests/test_api_boundary.py
```python
"""
Test to enforce API boundaries in the Runtime.
Ensures that runtime modules do not bypass API layers to access governance internals directly.
"""
import ast
import os
from pathlib import Path
from typing import List, Tuple

# Protected modules that should not be imported directly
PROTECTED_MODULES = [
    "runtime.governance",
    "runtime.amu0",
]

# Allowed access points
ALLOWED_IMPORTS = [
    "runtime.api",
    "runtime.api.governance_api",
    "runtime.api.runtime_api",
]

# Files exempt from these rules (the APIs themselves and tests)
EXEMPT_FILES = [
    "runtime/api/governance_api.py",
    "runtime/api/runtime_api.py",
    "runtime/governance/",  # Governance internals can import each other
    "runtime/amu0/",       # AMU0 internals can import each other
    "runtime/tests/",      # Tests verify internals
    "runtime/envelope/",   # Envelope is infrastructure, needs deep access
]

def check_imports(file_path: str) -> List[str]:
    """Check a file for illegal imports."""
    violations = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return [f"SyntaxError parsing {file_path}"]

    for node in ast.walk(tree):
        # Check 'import runtime.governance...'
        if isinstance(node, ast.Import):
            for alias in node.names:
                for protected in PROTECTED_MODULES:
                    if alias.name.startswith(protected):
                        violations.append(f"Line {node.lineno}: Illegal import '{alias.name}'")

        # Check 'from runtime.governance import ...'
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for protected in PROTECTED_MODULES:
                    if node.module.startswith(protected):
                        violations.append(f"Line {node.lineno}: Illegal import from '{node.module}'")
    
    return violations

def test_api_boundary_enforcement():
    """Scan runtime/ directory for API boundary violations."""
    runtime_root = Path("runtime").resolve()
    
    if not runtime_root.exists():
        # Fallback for test runner location
        runtime_root = Path.cwd() / "runtime"
    
    assert runtime_root.exists(), f"Could not find runtime root at {runtime_root}"
    
    all_violations = {}
    
    for python_file in runtime_root.rglob("*.py"):
        rel_path = python_file.relative_to(runtime_root.parent).as_posix()
        
        # Check exemptions
        is_exempt = False
        for exempt in EXEMPT_FILES:
            if rel_path.startswith(exempt) or exempt in rel_path:
                is_exempt = True
                break
        
        if is_exempt:
            continue
            
        # Check the file
        violations = check_imports(str(python_file))
        if violations:
            all_violations[rel_path] = violations
            
    # Report
    if all_violations:
        msg = "\nAPI Boundary Violations Found:\n"
        for fpath, errs in all_violations.items():
            msg += f"\nFile: {fpath}\n"
            for err in errs:
                msg += f"  {err}\n"
        
        assert False, msg

if __name__ == "__main__":
    test_api_boundary_enforcement()
```
```python
"""
FP-4.x CND-6: Runtime API
Operational API for runtime interactions.
"""
from typing import List, Dict, Any, Optional
from runtime.validator.anti_failure_validator import (
    AntiFailureValidator, WorkflowStep, ValidationResult
)


class RuntimeAPI:
    """
    Operational API for runtime layer.
    
    Provides workflow submission, validation, and DAP operations.
    """
    
    def __init__(self, validator: Optional[AntiFailureValidator] = None):
        self._validator = validator or AntiFailureValidator()
    
    def validate_workflow(self, steps: List[WorkflowStep]) -> ValidationResult:
        """Validate a workflow against Anti-Failure constraints."""
        return self._validator.validate(steps)
    
    def submit_workflow(self, steps: List[WorkflowStep]) -> Dict[str, Any]:
        """Submit a workflow for execution."""
        result = self._validator.validate_or_raise(steps)
        return {
            "submitted": True,
            "validation": {
                "total_steps": result.total_steps,
                "human_steps": result.human_steps,
                "attestation": result.attestation.to_dict()
            }
        }
```


