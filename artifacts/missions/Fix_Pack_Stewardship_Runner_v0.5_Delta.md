# Fix_Pack_Stewardship_Runner_v0.5_Delta

**Mission**: Address REMAINING Council P1 conditions (not covered by v1.0)  
**Date**: 2026-01-02  
**Author**: Council Chair  
**Status**: READY FOR BUILDER  
**Blocking**: Agent-triggered runs require these fixes.

---

## 1. Context

Review_Packet_Stewardship_Hardening_Combined_v1.0 delivered:
- ✅ Canonical Surface Scope across all validators
- ✅ Governance structural fixes
- ✅ SyntaxWarning fix
- ✅ Smoke test passing

**However**, the 5 Council P1 conditions from the formal review remain unaddressed. This delta pack contains ONLY those remaining items.

---

## 2. Remaining P1 Fixes (Required)

### P1-A: Re-check dirty state before commit

**Problem**: Race condition — if repo becomes dirty during run (external process), commit stage could include unintended changes.

**Location**: `scripts/steward_runner.py` — commit stage, before `git add`

**Implementation**:
```python
def _execute_commit_stage(self, changed_files: list[str], staging_roots: list[str]) -> StageResult:
    # ... existing change detection complete ...
    
    # P1-A: Re-check for unexpected changes before staging
    pre_stage_result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=self.repo_root
    )
    current_dirty = {
        line[3:] for line in pre_stage_result.stdout.strip().split('\n') 
        if line.strip()
    }
    expected_set = set(changed_files)
    unexpected = current_dirty - expected_set
    
    if unexpected:
        self._log_event("commit_blocked", {
            "reason": "repo_dirty_during_run",
            "unexpected_files": sorted(unexpected)
        })
        return StageResult.fail(
            reason="repo_dirty_during_run",
            detail=f"Unexpected changes before staging: {sorted(unexpected)}"
        )
    
    # ... proceed to git add -A -- <roots> ...
```

**Acceptance Test** (AT-14):
```python
@pytest.mark.parametrize("inject_file", ["injected.txt", "docs/injected.md"])
def test_dirty_during_run_rejected(mock_repo, runner, inject_file):
    """AT-14: Changes appearing mid-run are rejected."""
    # Patch change_detect to inject a file after detection but before commit
    original_detect = runner._detect_changes
    
    def detect_then_inject():
        result = original_detect()
        # Simulate external process creating file
        (mock_repo / inject_file).write_text("injected content")
        return result
    
    runner._detect_changes = detect_then_inject
    result = runner.run()
    
    assert result.failed
    assert result.reason == "repo_dirty_during_run"
    assert inject_file in str(result.detail)
```

---

### P1-B: Log determinism guarantees

**Problem**: AT-10 exists but specifics of determinism contract undocumented.

**Location**: `scripts/steward_runner.py` — top of file + logging functions

**Implementation** (docstring contract):
```python
"""
Stewardship Runner

Log Determinism Contract
------------------------
- Timestamps: ISO 8601 UTC with Z suffix (e.g., "2026-01-02T14:30:00Z")
- File lists: Always sorted lexicographically before logging
- Git hashes: Logged for audit trail, never used in control flow
- Run-id: Externally provided, deterministic input
- No locale/timezone/ordering dependencies in decision logic
"""
```

**Implementation** (enforce sorting):
```python
def _log_event(self, event_type: str, data: dict) -> None:
    """Append structured event to JSONL log."""
    entry = {
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": self.run_id,
        "event": event_type,
    }
    entry.update(data)
    
    # P1-B: Enforce sorted file lists for determinism
    for key in ("files", "changed_files", "staged_files", "validated_files", "unexpected_files"):
        if key in entry and isinstance(entry[key], list):
            entry[key] = sorted(entry[key])
    
    with open(self.log_path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
```

**Acceptance Test** (AT-15):
```python
def test_log_file_lists_sorted(mock_repo, runner, tmp_path):
    """AT-15: File lists in logs are always lexicographically sorted."""
    # Create files in non-sorted order
    for name in ["z_file.md", "a_file.md", "m_file.md"]:
        (mock_repo / "docs" / name).write_text(f"# {name}")
    
    runner.run(dry_run=True)
    
    log_entries = [json.loads(line) for line in runner.log_path.read_text().splitlines()]
    
    for entry in log_entries:
        for key in ("files", "changed_files", "staged_files"):
            if key in entry and isinstance(entry[key], list):
                assert entry[key] == sorted(entry[key]), f"{key} not sorted in {entry}"
```

---

### P1-C: Platform policy documentation

**Problem**: Windows path rejection exists but platform scope undocumented.

**Location**: NEW FILE `docs/01_governance/PLATFORM_POLICY.md`

**Implementation**:
```markdown
# Platform Policy

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | ✅ Primary | CI target, production |
| macOS | ✅ Supported | Development |
| Windows (native) | ❌ Unsupported | Use WSL2 |

## Path Handling

The Stewardship Runner rejects Windows-style paths at config validation:
- `C:\path` → rejected (`absolute_path_windows`)
- `\\server\share` → rejected (`absolute_path_unc`)

This is a **safety net**, not runtime support. The runner is not tested on Windows.

## Contributors on Windows

Use WSL2 with Ubuntu. The LifeOS toolchain assumes POSIX semantics.

## Rationale

Maintaining cross-platform compatibility adds complexity without benefit.
LifeOS targets server/CI environments (Linux) and developer machines (Linux/macOS).
```

**Also add to** `config/steward_runner.yaml`:
```yaml
# Platform: Linux/macOS only. Windows paths rejected as safety net.
# Windows users: use WSL2. See docs/01_governance/PLATFORM_POLICY.md
```

---

### P1-D: Explicit --dry-run / --commit flags

**Problem**: CI safety requires explicit commit opt-in. Default should be safe (no commit).

**Location**: `scripts/steward_runner.py` — CLI parsing + main

**Implementation**:
```python
import argparse
import sys

def parse_args(argv: list[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stewardship Runner — deterministic doc maintenance pipeline"
    )
    parser.add_argument(
        "--run-id", 
        required=True, 
        help="Unique identifier for this run (for audit trail)"
    )
    parser.add_argument(
        "--config", 
        default="config/steward_runner.yaml",
        help="Path to runner config"
    )
    
    # P1-D: Mutually exclusive commit control
    commit_group = parser.add_mutually_exclusive_group()
    commit_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all stages but skip git commit (default behavior)"
    )
    commit_group.add_argument(
        "--commit",
        action="store_true",
        help="Actually commit changes (explicit opt-in required)"
    )
    
    return parser.parse_args(argv)


def main(argv: list[str] = None) -> int:
    args = parse_args(argv)
    
    # Default is dry-run (safe). Commit requires explicit --commit flag.
    actually_commit = args.commit  # True only if --commit passed
    
    runner = StewardshipRunner(
        run_id=args.run_id,
        config_path=args.config,
        dry_run=not actually_commit
    )
    
    result = runner.run()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Acceptance Tests** (AT-16, AT-17):
```python
def test_default_is_dry_run(mock_repo, cli_runner):
    """AT-16: Without flags, runner does not commit."""
    # Make a change
    (mock_repo / "docs" / "test.md").write_text("# Test")
    
    result = cli_runner(["--run-id", "test-16"])
    
    assert result.exit_code == 0
    # Verify no new commits
    commits_after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, cwd=mock_repo
    )
    assert commits_after.stdout.strip() == "1"  # Only initial commit


def test_commit_flag_enables_commit(mock_repo, cli_runner):
    """AT-17: --commit flag enables actual commit."""
    (mock_repo / "docs" / "test.md").write_text("# Test")
    
    result = cli_runner(["--run-id", "test-17", "--commit"])
    
    assert result.exit_code == 0
    commits_after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, cwd=mock_repo
    )
    assert commits_after.stdout.strip() == "2"  # Initial + steward commit


def test_dry_run_explicit(mock_repo, cli_runner):
    """AT-18: Explicit --dry-run also prevents commit."""
    (mock_repo / "docs" / "test.md").write_text("# Test")
    
    result = cli_runner(["--run-id", "test-18", "--dry-run"])
    
    assert result.exit_code == 0
    assert "dry_run" in result.log_content or "skipped" in result.log_content.lower()
```

---

### P1-E: Log retention policy documentation

**Problem**: No specification for log lifecycle (retention, cleanup, archival).

**Location**: NEW FILE `docs/01_governance/LOG_RETENTION.md`

**Implementation**:
```markdown
# Log Retention Policy

## Stewardship Runner Logs

Location: `logs/steward_runner/<run-id>.jsonl`

### Retention by Context

| Context | Location | Retention | Owner |
|---------|----------|-----------|-------|
| Local development | `logs/steward_runner/` | 30 days | Developer |
| CI pipeline | Build artifacts | 90 days | CI system |
| Governance audit | `archive/logs/` | Indefinite | Doc Steward |

### Cleanup Rules

1. **Local**: Logs older than 30 days may be deleted unless referenced by open issue
2. **CI**: Artifacts auto-expire per platform default (GitHub: 90 days)
3. **Pre-deletion check**: Before deleting logs related to governance decisions, export to `archive/logs/`

### Log Content

Each JSONL entry contains:
- `timestamp`: ISO 8601 UTC
- `run_id`: Unique run identifier
- `event`: Event type (preflight, test, validate, commit, etc.)
- Event-specific data (files, results, errors)

### Audit Trail

Logs are append-only during a run. The `run_id` ties all entries together.
For governance audits, the complete log for a run provides deterministic replay evidence.
```

**Also add to** `config/steward_runner.yaml`:
```yaml
logging:
  output_dir: "logs/steward_runner"
  format: "jsonl"
  # Retention: 30 days local, 90 days CI. See docs/01_governance/LOG_RETENTION.md
```

---

## 3. P2 Hardenings (Optional, Recommended)

### P2-A: Empty commit_paths validation

```python
# In config validation
if "commit_paths" not in config:
    errors.append("commit_paths: required field missing")
elif not config["commit_paths"]:
    errors.append("commit_paths: empty list not allowed")
```

### P2-B: URL-encoded path rejection

```python
# In normalize_commit_path(), after glob check
if "%" in normalized:
    return path, "url_encoded_chars"
```

Add to AT-13 parametrization:
```python
("docs%2F..%2Fother", "url_encoded_chars"),
```

### P2-C: Return original path on error

```python
def normalize_commit_path(path: str) -> tuple[str, str | None]:
    original = path  # Keep original for error returns
    normalized = path.replace("\\", "/")
    
    if normalized.startswith("//"):
        return original, "absolute_path_unc"  # Return original, not normalized
    # ... same pattern for all error cases ...
```

---

## 4. Files to Create/Modify

| File | Action | P1 |
|------|--------|-----|
| `scripts/steward_runner.py` | Modify | A, B, D |
| `docs/01_governance/PLATFORM_POLICY.md` | Create | C |
| `docs/01_governance/LOG_RETENTION.md` | Create | E |
| `config/steward_runner.yaml` | Modify (comments) | C, E |
| `tests_recursive/test_steward_runner.py` | Add AT-14 through AT-18 | A, B, D |

---

## 5. Verification

```bash
# Run new acceptance tests
python -m pytest -v tests_recursive/test_steward_runner.py -k "AT-14 or AT-15 or AT-16 or AT-17 or AT-18"

# Verify docs exist
ls docs/01_governance/PLATFORM_POLICY.md docs/01_governance/LOG_RETENTION.md

# Full suite
python -m pytest -q -c pytest.ini runtime/tests tests_doc tests_recursive
```

---

## 6. Completion Checklist

Builder returns this completed:

- [ ] P1-A: Dirty-during-run check — AT-14 passes
- [ ] P1-B: Log determinism contract — docstring added, sorting enforced, AT-15 passes
- [ ] P1-C: PLATFORM_POLICY.md created, config commented
- [ ] P1-D: CLI flags added — AT-16, AT-17, AT-18 pass
- [ ] P1-E: LOG_RETENTION.md created, config commented
- [ ] (Optional) P2-A: Empty commit_paths validation
- [ ] (Optional) P2-B: URL-encoded rejection
- [ ] (Optional) P2-C: Original path on error
- [ ] Full test suite passes

---

## 7. Post-Completion

Once this pack is complete, Council conditions are satisfied:
- **D1 (Operational readiness)**: APPROVED for agent-triggered runs
- **D2 (Canonical surface)**: Already approved (v1.0 enforced it)
- **D3 (Fail-closed)**: APPROVED

---

## End of Delta Fix Pack
