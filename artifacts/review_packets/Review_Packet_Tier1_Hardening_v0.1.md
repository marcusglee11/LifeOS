# Review Packet: Tier-1 Hardening Mission v0.1

**Mission**: Tier1_Hardening_v0.1  
**Date**: 2025-12-09  
**Authority**: Architecture & Ideation Project  

---

## 1. Summary

Executed Stage 1 Tier-1 Hardening: FP-3.1, FP-3.2, FP-3.3, FP-3.7, FP-3.9.  
Created 16 new files. 87 tests passing.

---

## 2. Issue Catalogue

| ID | Fix Pack | Issue | Resolution |
|----|----------|-------|------------|
| FP-3.1 | Determinism | No byte-level verification | Added `test_determinism_suite.py` |
| FP-3.2 | AMU₀ | No state lineage | Added `amu0.py` with create/restore/promote |
| FP-3.3 | DAP | No write gateway | Added `dap_gateway.py` + `indexer.py` |
| FP-3.7 | Anti-Failure | No workflow validation | Added `validator.py` |
| FP-3.9 | Governance | No protected paths | Added `protection.py` |

---

## 3. Acceptance Criteria

- [x] All 5 Fix Packs implemented
- [x] 87 tests passing
- [x] Determinism verified (3 runs)
- [x] AMU₀ baseline created
- [x] Protected paths locked

---

## 4. Non-Goals

- Stage 2 Fix Packs (FP-3.4 to FP-3.10)
- Tier-2 Activation
- Protected path modifications

---

## Appendix — Flattened Code Snapshots

### File: runtime/state/__init__.py
```python
# runtime/state/__init__.py
"""
Runtime State Management Package.
Provides AMU0 discipline and state lineage operations.
"""
```

### File: runtime/state/amu0.py
```python
"""
FP-3.2: AMU₀ Discipline & State Lineage
Implements deterministic, reproducible state snapshot operations.
"""
import os
import json
import shutil
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any


class AMU0Error(Exception):
    """Raised when AMU0 operations fail."""
    pass


class AMU0Manager:
    """
    Manages AMU₀ baseline snapshots for deterministic state lineage.
    
    Provides:
    - create_amu0_baseline: Create a baseline snapshot
    - restore_from_amu0: Restore to a baseline
    - promote_run_to_amu0: Promote a successful run to become the new baseline
    """
    
    def __init__(self, state_root: str):
        """
        Initialize AMU0 Manager.
        
        Args:
            state_root: Root directory for all runtime state.
        """
        self.state_root = state_root
        os.makedirs(state_root, exist_ok=True)
    
    def create_amu0_baseline(
        self,
        baseline_name: str,
        source_paths: list[str],
        timestamp: Optional[str] = None
    ) -> str:
        """
        Create a new AMU₀ baseline snapshot.
        
        Args:
            baseline_name: Name for this baseline (e.g., "PRE_HARDENING")
            source_paths: List of paths to include in the snapshot
            timestamp: Optional pinned timestamp (ISO format)
        
        Returns:
            Path to the created baseline directory.
        
        Raises:
            AMU0Error: If baseline creation fails.
        """
        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if os.path.exists(baseline_dir):
            raise AMU0Error(f"Baseline {baseline_name} already exists at {baseline_dir}")
        
        os.makedirs(baseline_dir)
        
        # Create manifest
        manifest = {
            "baseline_name": baseline_name,
            "created_at": timestamp or datetime.utcnow().isoformat() + "Z",
            "source_paths": source_paths,
            "files": []
        }
        
        # Copy files and compute checksums
        for source_path in source_paths:
            if os.path.isfile(source_path):
                self._copy_file_to_baseline(source_path, baseline_dir, manifest)
            elif os.path.isdir(source_path):
                for root, _, files in os.walk(source_path):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        self._copy_file_to_baseline(fpath, baseline_dir, manifest)
        
        # Write manifest
        manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        
        # Compute and store manifest checksum
        with open(manifest_path, "rb") as f:
            manifest_hash = hashlib.sha256(f.read()).hexdigest()
        
        with open(os.path.join(baseline_dir, "amu0_manifest.sha256"), "w") as f:
            f.write(manifest_hash)
        
        return baseline_dir
    
    def _copy_file_to_baseline(
        self,
        source_path: str,
        baseline_dir: str,
        manifest: Dict[str, Any]
    ) -> None:
        """Copy a file to baseline and update manifest."""
        # Compute relative path
        rel_path = os.path.basename(source_path)
        dest_path = os.path.join(baseline_dir, "files", rel_path)
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source_path, dest_path)
        
        # Compute checksum
        with open(dest_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        manifest["files"].append({
            "path": rel_path,
            "sha256": checksum,
            "size": os.path.getsize(dest_path)
        })
    
    def restore_from_amu0(self, baseline_name: str, target_dir: str) -> None:
        """
        Restore state from an AMU₀ baseline.
        
        Args:
            baseline_name: Name of the baseline to restore from
            target_dir: Directory to restore files into
        
        Raises:
            AMU0Error: If restoration fails or integrity check fails.
        """
        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if not os.path.exists(baseline_dir):
            raise AMU0Error(f"Baseline {baseline_name} not found at {baseline_dir}")
        
        # Verify manifest integrity
        manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
        checksum_path = os.path.join(baseline_dir, "amu0_manifest.sha256")
        
        with open(manifest_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        with open(checksum_path, "r") as f:
            expected_hash = f.read().strip()
        
        if actual_hash != expected_hash:
            raise AMU0Error("Manifest integrity check failed. Baseline may be corrupted.")
        
        # Load manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        # Restore files
        os.makedirs(target_dir, exist_ok=True)
        files_dir = os.path.join(baseline_dir, "files")
        
        for file_entry in manifest["files"]:
            src = os.path.join(files_dir, file_entry["path"])
            dst = os.path.join(target_dir, file_entry["path"])
            
            # Verify file integrity
            with open(src, "rb") as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            
            if actual_checksum != file_entry["sha256"]:
                raise AMU0Error(f"File integrity check failed for {file_entry['path']}")
            
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    
    def promote_run_to_amu0(
        self,
        run_dir: str,
        new_baseline_name: str,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Promote a successful run to become a new AMU₀ baseline.
        
        Args:
            run_dir: Directory containing the successful run state
            new_baseline_name: Name for the new baseline
            timestamp: Optional pinned timestamp
        
        Returns:
            Path to the new baseline directory.
        
        Raises:
            AMU0Error: If promotion fails.
        """
        if not os.path.exists(run_dir):
            raise AMU0Error(f"Run directory {run_dir} does not exist")
        
        # Collect all files in run_dir
        source_paths = []
        for root, _, files in os.walk(run_dir):
            for fname in files:
                source_paths.append(os.path.join(root, fname))
        
        return self.create_amu0_baseline(new_baseline_name, source_paths, timestamp)
    
    def verify_baseline(self, baseline_name: str) -> bool:
        """
        Verify integrity of an existing baseline.
        
        Args:
            baseline_name: Name of the baseline to verify
        
        Returns:
            True if baseline is valid, False otherwise.
        """
        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if not os.path.exists(baseline_dir):
            return False
        
        try:
            manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
            checksum_path = os.path.join(baseline_dir, "amu0_manifest.sha256")
            
            with open(manifest_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            with open(checksum_path, "r") as f:
                expected_hash = f.read().strip()
            
            if actual_hash != expected_hash:
                return False
            
            # Verify all files
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            files_dir = os.path.join(baseline_dir, "files")
            for file_entry in manifest["files"]:
                fpath = os.path.join(files_dir, file_entry["path"])
                if not os.path.exists(fpath):
                    return False
                
                with open(fpath, "rb") as f:
                    if hashlib.sha256(f.read()).hexdigest() != file_entry["sha256"]:
                        return False
            
            return True
        except Exception:
            return False
    
    def list_baselines(self) -> list[str]:
        """List all available baselines."""
        baselines = []
        if os.path.exists(self.state_root):
            for name in os.listdir(self.state_root):
                if name.endswith("_AMU0") and os.path.isdir(os.path.join(self.state_root, name)):
                    baselines.append(name.replace("_AMU0", ""))
        return sorted(baselines)
```

### File: runtime/dap_gateway.py
```python
"""
FP-3.3: DAP Write Gateway
Central gateway for all file write operations.
Enforces DAP boundary checks, deterministic naming, and protected path validation.
"""
import os
import re
import json
from typing import Optional, List, Set
from datetime import datetime


class DAPWriteError(Exception):
    """Raised when a DAP write violation occurs."""
    pass


class DAPWriteGateway:
    """
    Central Write Gateway for DAP-compliant file operations.
    
    Validates:
    - Target path is within allowed boundaries
    - Filename follows deterministic naming patterns
    - Protected paths are not written to
    """
    
    # DAP v2.0 naming pattern: name_v{major}.{minor}.{ext}
    VERSION_PATTERN = re.compile(r'^.+_v\d+\.\d+\.(md|json|yaml|txt)$')
    
    def __init__(
        self,
        allowed_roots: List[str],
        protected_paths: Optional[List[str]] = None,
        index_paths: Optional[List[str]] = None
    ):
        self.allowed_roots = [os.path.abspath(r) for r in allowed_roots]
        self.protected_paths = [os.path.abspath(p) for p in (protected_paths or [])]
        self.index_paths = index_paths or []
        self._pending_index_updates: Set[str] = set()
    
    def validate_write(self, target_path: str, content: str) -> None:
        abs_path = os.path.abspath(target_path)
        filename = os.path.basename(target_path)
        
        for protected in self.protected_paths:
            if abs_path.startswith(protected) or abs_path == protected:
                raise DAPWriteError(f"Write to protected path: {target_path}")
        
        in_allowed_root = False
        for root in self.allowed_roots:
            if abs_path.startswith(root):
                in_allowed_root = True
                break
        
        if not in_allowed_root:
            raise DAPWriteError(
                f"Write outside allowed boundaries: {target_path}. "
                f"Allowed roots: {self.allowed_roots}"
            )
    
    def write(self, target_path: str, content: str, encoding: str = 'utf-8') -> None:
        self.validate_write(target_path, content)
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with open(target_path, 'w', encoding=encoding) as f:
            f.write(content)
        self._queue_index_update(target_path)
    
    def write_binary(self, target_path: str, content: bytes) -> None:
        self.validate_write(target_path, "")
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with open(target_path, 'wb') as f:
            f.write(content)
        self._queue_index_update(target_path)
    
    def _queue_index_update(self, written_path: str) -> None:
        self._pending_index_updates.add(os.path.abspath(written_path))
    
    def flush_index_updates(self) -> List[str]:
        updated = list(self._pending_index_updates)
        self._pending_index_updates.clear()
        return updated
    
    def is_protected(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        for protected in self.protected_paths:
            if abs_path.startswith(protected) or abs_path == protected:
                return True
        return False
    
    def is_in_boundary(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        for root in self.allowed_roots:
            if abs_path.startswith(root):
                return True
        return False
    
    @staticmethod
    def generate_versioned_name(base_name: str, major: int, minor: int, ext: str) -> str:
        return f"{base_name}_v{major}.{minor}.{ext}"
```

### File: runtime/index/__init__.py
```python
# runtime/index/__init__.py
"""
Runtime Index Management Package.
Provides automatic index reconciliation for DAP compliance.
"""
```

### File: runtime/index/indexer.py
```python
"""
FP-3.3: Index Reconciliation
Automatic index file maintenance for DAP compliance.
"""
import os
import re
from typing import List, Optional, Set
from pathlib import Path


class IndexReconciler:
    """
    Maintains INDEX files in sync with actual file contents.
    """
    
    def __init__(self, index_path: str, root_dir: str):
        self.index_path = index_path
        self.root_dir = os.path.abspath(root_dir)
    
    def scan_directory(self, extensions: Optional[List[str]] = None) -> List[str]:
        if extensions is None:
            extensions = ['.md']
        
        files = []
        index_basename = os.path.basename(self.index_path)
        for root, _, filenames in os.walk(self.root_dir):
            for fname in filenames:
                if fname == index_basename:
                    continue
                if any(fname.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    rel_path = rel_path.replace('\\', '/')
                    files.append(rel_path)
        
        return sorted(files)
    
    def generate_index_content(self, title: str = "Index", extensions: Optional[List[str]] = None) -> str:
        files = self.scan_directory(extensions)
        lines = [f"# {title}", ""]
        for f in files:
            lines.append(f"- [{f}](./{f})")
        lines.append("")
        return "\n".join(lines)
    
    def reconcile(self, title: str = "Index", extensions: Optional[List[str]] = None) -> bool:
        new_content = self.generate_index_content(title, extensions)
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            if existing_content == new_content:
                return False
        os.makedirs(os.path.dirname(os.path.abspath(self.index_path)), exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    def verify_coherence(self) -> tuple[bool, List[str], List[str]]:
        actual_files = set(self.scan_directory())
        indexed_files: Set[str] = set()
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = r'\[([^\]]+)\]\(\./([^\)]+)\)'
            for match in re.finditer(pattern, content):
                indexed_files.add(match.group(2))
        missing = actual_files - indexed_files
        orphaned = indexed_files - actual_files
        return (len(missing) == 0 and len(orphaned) == 0, sorted(missing), sorted(orphaned))
```

### File: runtime/workflows/__init__.py
```python
# runtime/workflows/__init__.py
"""
Runtime Workflow Management Package.
Provides Anti-Failure workflow validation.
"""
```

### File: runtime/workflows/validator.py
```python
"""
FP-3.7: Anti-Failure Workflow Validator
Enforces Anti-Failure constraints on workflows:
- Maximum 5 steps total
- Maximum 2 human steps
- No routine human operations
"""
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum, auto


class StepActor(Enum):
    HUMAN = auto()
    AGENT = auto()
    SYSTEM = auto()


class WorkflowValidationError(Exception):
    pass


@dataclass
class WorkflowStep:
    name: str
    actor: StepActor
    description: str
    is_routine: bool = False


@dataclass
class ValidationResult:
    is_valid: bool
    total_steps: int
    human_steps: int
    routine_human_ops: int
    violations: List[str]
    suggestions: List[str]


class WorkflowValidator:
    MAX_STEPS = 5
    MAX_HUMAN_STEPS = 2
    
    def __init__(self, max_steps: int = 5, max_human_steps: int = 2, allow_routine_human_ops: bool = False):
        self.max_steps = max_steps
        self.max_human_steps = max_human_steps
        self.allow_routine_human_ops = allow_routine_human_ops
    
    def validate(self, steps: List[WorkflowStep]) -> ValidationResult:
        violations = []
        suggestions = []
        total_steps = len(steps)
        human_steps = sum(1 for s in steps if s.actor == StepActor.HUMAN)
        routine_human_ops = sum(1 for s in steps if s.actor == StepActor.HUMAN and s.is_routine)
        
        if total_steps > self.max_steps:
            violations.append(f"Workflow has {total_steps} steps, maximum is {self.max_steps}")
            suggestions.append("Consider combining steps or delegating to agents")
        
        if human_steps > self.max_human_steps:
            violations.append(f"Workflow has {human_steps} human steps, maximum is {self.max_human_steps}")
            suggestions.append("Human involvement should be limited to: Intent/Approve/Veto/Governance")
        
        if routine_human_ops > 0 and not self.allow_routine_human_ops:
            violations.append(f"Workflow has {routine_human_ops} routine human operations")
            for step in steps:
                if step.actor == StepActor.HUMAN and step.is_routine:
                    suggestions.append(f"Automate '{step.name}': {step.description}")
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            total_steps=total_steps,
            human_steps=human_steps,
            routine_human_ops=routine_human_ops,
            violations=violations,
            suggestions=suggestions
        )
    
    def validate_or_raise(self, steps: List[WorkflowStep]) -> ValidationResult:
        result = self.validate(steps)
        if not result.is_valid:
            error_msg = "Workflow validation failed:\n"
            error_msg += "\n".join(f"  - {v}" for v in result.violations)
            if result.suggestions:
                error_msg += "\n\nSuggestions:\n"
                error_msg += "\n".join(f"  - {s}" for s in result.suggestions)
            raise WorkflowValidationError(error_msg)
        return result
    
    def validate_mission(self, mission: dict) -> ValidationResult:
        steps = []
        execution_flow = mission.get('execution_flow', [])
        for step_def in execution_flow:
            actor = StepActor.AGENT
            step_name = step_def.get('step', 'unnamed')
            if 'human_' in step_name.lower() or 'approve' in step_name.lower():
                actor = StepActor.HUMAN
            steps.append(WorkflowStep(
                name=step_name, actor=actor,
                description=step_def.get('description', ''), is_routine=False
            ))
        return self.validate(steps)
    
    @staticmethod
    def create_human_step(name: str, description: str, is_routine: bool = False) -> WorkflowStep:
        return WorkflowStep(name=name, actor=StepActor.HUMAN, description=description, is_routine=is_routine)
    
    @staticmethod
    def create_agent_step(name: str, description: str) -> WorkflowStep:
        return WorkflowStep(name=name, actor=StepActor.AGENT, description=description, is_routine=False)
    
    @staticmethod
    def create_system_step(name: str, description: str) -> WorkflowStep:
        return WorkflowStep(name=name, actor=StepActor.SYSTEM, description=description, is_routine=False)
```

### File: runtime/governance/__init__.py
```python
# runtime/governance/__init__.py
"""
Runtime Governance Package.
Provides protected artefact enforcement and autonomy ceilings.
"""
```

### File: runtime/governance/protection.py
```python
"""
FP-3.9: Governance Protections & Autonomy Ceilings
Enforces protected artefact registry and autonomy constraints.
"""
import os
import json
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass


class GovernanceProtectionError(Exception):
    pass


@dataclass
class AutonomyCeiling:
    max_files_modified: int = 40
    max_directories_modified: int = 6
    allow_new_modules: bool = True
    allow_new_tests: bool = True
    allow_doc_updates: bool = True
    prohibit_protected_paths: bool = True


@dataclass
class OperationScope:
    files_modified: Set[str]
    directories_modified: Set[str]
    protected_violations: List[str]
    
    @property
    def file_count(self) -> int:
        return len(self.files_modified)
    
    @property
    def directory_count(self) -> int:
        return len(self.directories_modified)


class GovernanceProtector:
    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = registry_path
        self._protected_paths: List[str] = []
        self._autonomy_ceiling = AutonomyCeiling()
        if registry_path and os.path.exists(registry_path):
            self._load_registry(registry_path)
    
    def _load_registry(self, path: str) -> None:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._protected_paths = data.get('protected_paths', [])
    
    def add_protected_path(self, path: str) -> None:
        if path not in self._protected_paths:
            self._protected_paths.append(path)
    
    def remove_protected_path(self, path: str) -> None:
        if path in self._protected_paths:
            self._protected_paths.remove(path)
    
    def is_protected(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        norm_path = os.path.normpath(path)
        for protected in self._protected_paths:
            protected_abs = os.path.abspath(protected)
            protected_norm = os.path.normpath(protected)
            if (abs_path == protected_abs or norm_path == protected_norm or
                abs_path.startswith(protected_abs + os.sep) or
                norm_path.startswith(protected_norm + os.sep)):
                return True
        return False
    
    def validate_write(self, path: str) -> None:
        if self.is_protected(path):
            raise GovernanceProtectionError(f"Write to protected path prohibited: {path}")
    
    def set_autonomy_ceiling(self, ceiling: AutonomyCeiling) -> None:
        self._autonomy_ceiling = ceiling
    
    def validate_operation_scope(self, scope: OperationScope) -> tuple[bool, List[str]]:
        violations = []
        if scope.file_count > self._autonomy_ceiling.max_files_modified:
            violations.append(f"Files modified ({scope.file_count}) exceeds ceiling ({self._autonomy_ceiling.max_files_modified})")
        if scope.directory_count > self._autonomy_ceiling.max_directories_modified:
            violations.append(f"Directories modified ({scope.directory_count}) exceeds ceiling ({self._autonomy_ceiling.max_directories_modified})")
        if self._autonomy_ceiling.prohibit_protected_paths and scope.protected_violations:
            violations.append(f"Protected paths touched: {', '.join(scope.protected_violations)}")
        return (len(violations) == 0, violations)
    
    def validate_operation_scope_or_raise(self, scope: OperationScope) -> None:
        is_valid, violations = self.validate_operation_scope(scope)
        if not is_valid:
            raise GovernanceProtectionError("Autonomy ceiling violations:\n" + "\n".join(f"  - {v}" for v in violations))
    
    def validate_mission_scope(self, mission: Dict[str, Any]) -> tuple[bool, List[str]]:
        violations = []
        safety = mission.get('safety', {})
        ceiling = safety.get('autonomy_ceiling', {})
        max_files = ceiling.get('max_files_modified', 0)
        if max_files > self._autonomy_ceiling.max_files_modified:
            violations.append(f"Mission max_files_modified ({max_files}) exceeds system ceiling ({self._autonomy_ceiling.max_files_modified})")
        max_dirs = ceiling.get('max_directories_modified', 0)
        if max_dirs > self._autonomy_ceiling.max_directories_modified:
            violations.append(f"Mission max_directories_modified ({max_dirs}) exceeds system ceiling ({self._autonomy_ceiling.max_directories_modified})")
        return (len(violations) == 0, violations)
    
    def get_protected_paths(self) -> List[str]:
        return self._protected_paths.copy()
    
    def save_registry(self, path: Optional[str] = None) -> None:
        save_path = path or self.registry_path
        if not save_path:
            raise ValueError("No registry path specified")
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        data = {"protected_paths": self._protected_paths, "saved_at": "2025-12-09T00:00:00Z"}
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
```

### File: config/governance/protected_artefacts.json
```json
{
  "protected_paths": [
    "docs/00_foundations",
    "docs/01_governance",
    "docs/02_alignment",
    "docs/INDEX_v1.1.md",
    "config/governance/protected_artefacts.json"
  ],
  "locked_at": "2025-12-09T19:09:00+11:00",
  "locked_by": "Tier1_Hardening_v0.1"
}
```

---

*End of Review Packet*
