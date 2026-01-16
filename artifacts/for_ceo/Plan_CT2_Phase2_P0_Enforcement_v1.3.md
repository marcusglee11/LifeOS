---
packet_id: ct2-phase2-p0-enforcement-v1.3
packet_type: PLAN_ARTIFACT
version: 1.3
mission_name: CT-2 Phase 2 P0 Enforcement Final
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Plan: CT-2 Phase 2 (P0) — OpenCode Doc Steward Enforced Gate

## Goal

Final hardening: (1) docs-scoped index discovery with true fail-closed, (2) GitHub Actions-correct CI diff, (3) rename/copy parsing correctness, (4) path traversal defense.

## Binding Constraints

> [!CAUTION]
> - delete/rename/move/copy → ALWAYS BLOCK (git-diff reality)
> - Only `.md` under `docs/` writable; EXTENSION_EXCEPTIONS = []
> - Denylist-first; case-normalized matching
> - NO fallback that weakens fail-closed

---

## P0.1 — Index Discovery (Docs-Scoped, Fail-Closed)

**Problem**: Previous plan had "hardcoded fallback" which weakens fail-closed semantics.

**Solution**: Genuine fail-closed with docs-only scope:

```python
INDEX_DISCOVERY_SCOPE = ["docs/"]  # NOT ALLOWLIST_ROOTS

def discover_writable_index_files(repo_root: str) -> list[str]:
    """Discover index files ONLY under docs/."""
    candidates = []
    for scope_root in INDEX_DISCOVERY_SCOPE:
        for dirpath, _, files in os.walk(os.path.join(repo_root, scope_root)):
            for f in files:
                if f.lower() == "index.md":
                    rel = normalize_path(os.path.relpath(os.path.join(dirpath, f), repo_root))
                    # Exclude if under denylist
                    if not matches_denylist(rel)[0]:
                        candidates.append(rel)
    return sorted(candidates)

# FAIL-CLOSED: no fallback
WRITABLE_INDEX_FILES = discover_writable_index_files(REPO_ROOT)
if not WRITABLE_INDEX_FILES:
    # BLOCK with INDEX_DISCOVERY_EMPTY
    log_block("INDEX_DISCOVERY_EMPTY", f"No index files found under {INDEX_DISCOVERY_SCOPE}")
```

**Governance Surface Decision**:
- `docs/01_governance/` is in DENYLIST_ROOTS → its INDEX.md is **excluded** from WRITABLE_INDEX_FILES
- Final: `WRITABLE_INDEX_FILES = ["docs/index.md"]` (only root index)

---

## P0.2 — CI Diff Detection (GitHub Actions)

**Problem**: `GITHUB_BASE_REF` is a ref name, not a SHA. Direct use fails.

**Solution**: Robust CI detection with merge-base:

```python
def get_diff_command() -> tuple[list[str], str]:
    """Return (diff_command, mode). Fail-closed if refs unavailable."""
    
    # GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        base_ref = os.environ.get("GITHUB_BASE_REF")  # e.g., "main"
        head_sha = os.environ.get("GITHUB_SHA")
        
        if not base_ref or not head_sha:
            return (None, "REFS_UNAVAILABLE")
        
        # Compute merge-base (requires fetch)
        # Assumes: git fetch origin $GITHUB_BASE_REF
        merge_base_cmd = ["git", "merge-base", f"origin/{base_ref}", head_sha]
        result = subprocess.run(merge_base_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return (None, "MERGE_BASE_FAILED")
        
        merge_base = result.stdout.strip()
        return (["git", "diff", "--name-status", "-z", f"{merge_base}..{head_sha}"], "CI")
    
    # GitLab CI
    elif os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_SHA"):
        base_sha = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_SHA")
        head_sha = os.environ.get("CI_COMMIT_SHA", "HEAD")
        return (["git", "diff", "--name-status", "-z", f"{base_sha}..{head_sha}"], "CI")
    
    # Local mode
    else:
        return (["git", "diff", "--cached", "--name-status", "-z"], "LOCAL")

def detect_blocked_ops() -> list[tuple]:
    cmd, mode = get_diff_command()
    
    if cmd is None:
        # FAIL-CLOSED
        return [("UNKNOWN", "ERROR", f"DIFF_COMMAND_FAILED:{mode}")]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return [("UNKNOWN", "ERROR", "DIFF_COMMAND_FAILED:EXEC")]
    
    return parse_blocked_ops(result.stdout)
```

**Requirement**: CI workflow must `git fetch origin $GITHUB_BASE_REF` before running gate.

---

## P0.3 — Rename/Copy Parsing

**Problem**: `-z` format for R*/C* has two paths separated by NUL.

**Solution**:

```python
def parse_git_status_z(output: str) -> list[tuple]:
    """Parse git diff --name-status -z output.
    
    Returns:
      A/M/D       -> (status, path)
      R100/C100   -> (status, old_path, new_path)
    """
    entries = output.split('\0')
    result = []
    i = 0
    while i < len(entries):
        if not entries[i]:
            i += 1
            continue
        status = entries[i][0]
        if status in ('R', 'C'):
            # Rename/Copy: status\0old_path\0new_path
            old_path = entries[i].split('\t')[1] if '\t' in entries[i] else entries[i+1] if i+1 < len(entries) else ""
            new_path = entries[i+2] if i+2 < len(entries) else ""
            result.append((status, old_path, new_path))
            i += 3
        else:
            # A/M/D: status\tpath (in -z, split by \t within record)
            parts = entries[i].split('\t')
            if len(parts) == 2:
                result.append((parts[0], parts[1]))
            i += 1
    return result

def check_blocked_ops(parsed: list[tuple]) -> list[tuple]:
    """Check for blocked operations. Handle R/C with both paths."""
    blocked = []
    for entry in parsed:
        status = entry[0][0]  # First char
        if status == "D":
            blocked.append((entry[1], "delete", "PH2_DELETE_BLOCKED"))
        elif status == "R":
            old_path, new_path = entry[1], entry[2]
            blocked.append((f"{old_path}->{new_path}", "rename", "PH2_RENAME_BLOCKED"))
        elif status == "C":
            old_path, new_path = entry[1], entry[2]
            blocked.append((f"{old_path}->{new_path}", "copy", "PH2_COPY_BLOCKED"))
    return blocked
```

---

## P1.1 — Path Traversal Defense

```python
def check_path_security(path: str) -> tuple[bool, str]:
    """Check path for traversal/absolute attacks. Returns (safe, reason)."""
    norm = normalize_path(path)
    
    # Absolute path check (Unix or Windows)
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
        return (False, "PATH_ABSOLUTE_BLOCKED")
    
    # Traversal check (after normalization)
    if ".." in norm.split("/"):
        return (False, "PATH_TRAVERSAL_BLOCKED")
    
    # Realpath containment (if file exists)
    if os.path.exists(path):
        real = os.path.realpath(path)
        repo_real = os.path.realpath(REPO_ROOT)
        if not real.startswith(repo_real):
            return (False, "PATH_ESCAPE_BLOCKED")
    
    return (True, None)
```

---

## Explicit Enumerations (Final)

```python
# Scopes
INDEX_DISCOVERY_SCOPE = ["docs/"]
ALLOWLIST_ROOTS = ["artifacts/review_packets/", "docs/"]
DENYLIST_ROOTS = ["config/", "docs/00_foundations/", "docs/01_governance/", "scripts/"]
DENYLIST_EXACT_FILES = ["gemini.md"]
DENYLIST_EXTENSIONS = [".py"]

# Extensions
ALLOWED_EXTENSIONS_DOCS = [".md"]
EXTENSION_EXCEPTIONS = []

# Index (discovered, fail-closed)
WRITABLE_INDEX_FILES = ["docs/index.md"]  # governance index excluded
```

---

## Tests

| Test | Assertion |
|------|-----------|
| `test_rename_parsing_z` | R100\0old\0new → (R, old, new) |
| `test_ci_diff_refs_missing` | BLOCK DIFF_COMMAND_FAILED |
| `test_traversal_blocked` | `../etc/passwd` → BLOCK |
| `test_index_discovery_docs_only` | review_packets index NOT in list |
| `test_governance_index_excluded` | `docs/01_governance/index.md` excluded |

---

## DONE Definition

- [ ] Index discovery docs-scoped; fail-closed; no fallback
- [ ] `docs/01_governance/` in denylist → its index excluded
- [ ] CI diff uses merge-base; fail-closed on missing refs
- [ ] Rename/copy parsed correctly (old+new paths)
- [ ] Traversal/absolute path defense + tests
- [ ] Evidence: PASS + BLOCK(rename) + BLOCK(diff_failed)

---

## CHANGELOG

- **v1.3**: Docs-scoped index, CI merge-base, rename parsing, traversal defense, governance index excluded
- **v1.2**: Fixed WRITABLE_INDEX_FILES contradiction, CI-safe diff, add-only packets, normalize_path spec
- **v1.1**: Git-diff-based op detection, bypass-resistance tests
- **v1.0**: Initial plan
