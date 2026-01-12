---
packet_id: ct2-phase2-p0-enforcement-v1.1
packet_type: PLAN_ARTIFACT
version: 1.1
mission_name: CT-2 Phase 2 P0 Enforcement Hardening
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Plan: CT-2 Phase 2 (P0) — OpenCode Doc Steward Enforced Gate Implementation

## Goal

Harden the OpenCode doc-steward gate with: (1) git-diff-based blocked operation detection, (2) explicit matching semantics (no globs), (3) bypass-resistant policy enforcement.

## User Review Required

> [!CAUTION]
> **Binding Constraints (No Override, No Exceptions)**:
> - delete/rename/move → ALWAYS BLOCK (detected from git diff, not JSON action)
> - Only `.md` under `docs/` writable; extension_exceptions = []
> - Packet discovery = explicit `packet_paths` only
> - Denylist-first evaluation; any match = terminal BLOCK
> - Case-normalized matching on all platforms

---

## P0.1 — Git-Diff-Based Operation Detection

The runner MUST detect blocked operations from `git diff --cached --name-status -z`, NOT from JSON `action` field:

| Git Status | Operation | Phase 2 |  Reason Code |
|------------|-----------|---------|---------------|
| D | delete | BLOCK | `PH2_DELETE_BLOCKED` |
| R* | rename/move | BLOCK | `PH2_RENAME_BLOCKED` |
| C* | copy | BLOCK | `PH2_COPY_BLOCKED` |

This prevents bypass via mislabeled JSON (e.g., `action:"modify"` but git sees rename).

---

## P0.2 — Explicit Matching Semantics (No Globs)

### Matching Algorithm
```python
def matches_allowlist(path: str) -> bool:
    norm = normalize_path(path)  # lowercase, forward slashes
    return any(norm.startswith(root) for root in ALLOWLIST_ROOTS)

def matches_denylist(path: str) -> Tuple[bool, str]:
    norm = normalize_path(path)
    # Check exact files first
    if norm in DENYLIST_EXACT_FILES:
        return (True, "exact_file")
    # Check roots
    for root in DENYLIST_ROOTS:
        if norm.startswith(root):
            return (True, "denylist_root")
    # Check extensions
    ext = os.path.splitext(norm)[1].lower()
    if ext in DENYLIST_EXTENSIONS:
        return (True, "denylist_extension")
    return (False, None)
```

### Evaluation Order (Invariant)
1. **Denylist FIRST** — any match → terminal BLOCK (no fallthrough)
2. **Allowlist SECOND** — path must match an allowed root
3. **Extension check** — if under `docs/`, must be `.md`

---

## Proposed Changes

### [MODIFY] opencode_ci_runner.py

**Constants (Explicit Enumerations):**
```python
# Allowlist (sorted)
ALLOWLIST_ROOTS = [
    "artifacts/review_packets/",
    "docs/",
]

# Denylist (explicit, no globs)
DENYLIST_ROOTS = [
    "config/",
    "docs/00_foundations/",
    "scripts/",
]
DENYLIST_EXACT_FILES = ["gemini.md"]  # lowercase for matching
DENYLIST_EXTENSIONS = [".py"]

# Extension restrictions under docs/
ALLOWED_EXTENSIONS_DOCS = [".md"]
EXTENSION_EXCEPTIONS = []  # Must remain empty in Phase 2

# Writable index files (discovered from repo)
WRITABLE_INDEX_FILES = [
    "artifacts/index.md",
    "config/index.md",
    "docs/01_governance/index.md",
    "docs/index.md",
]
```

**New Function: `detect_blocked_ops_from_git()`**
- Parse `git diff --cached --name-status -z`
- Return list of `(path, op_type)` where op_type in {D, R, C}
- If any blocked op detected → BLOCK before mission execution

---

### [NEW] opencode_gate_policy.py

Separate policy constants into dedicated module for maintainability.

---

### Test Coverage

#### Bypass-Resistance Tests (P0.3)

| Test Case | Attack Vector | Assertion |
|-----------|---------------|-----------|
| `test_git_diff_mislabel_delete_blocked` | JSON=modify, git=D | BLOCK |
| `test_git_diff_mislabel_rename_blocked` | JSON=modify, git=R | BLOCK |
| `test_case_bypass_docs_foundations` | `DOCS/00_Foundations/x.md` | Normalize → BLOCK |
| `test_case_bypass_gemini` | `Gemini.MD` | Normalize → BLOCK |
| `test_extension_bypass_double_ext` | `docs/file.md.py` | BLOCK |

#### Functional Tests

| Test Case | Expected |
|-----------|----------|
| `test_allowed_md_modify_under_docs_pass` | PASS |
| `test_non_md_under_docs_blocked` | BLOCK |
| `test_delete_blocked_phase2_gitdiff` | BLOCK |
| `test_rename_blocked_phase2_gitdiff` | BLOCK |
| `test_denied_path_blocked` | BLOCK |

---

## DONE Definition

- [ ] Blocked ops (D/R/C) detected from `git diff --cached`, not JSON action
- [ ] No globs in policy matching; explicit prefix/exact matching only
- [ ] delete/rename/move ALWAYS BLOCK in Phase 2 (git-diff enforced)
- [ ] Only `.md` writable under `docs/`; extension_exceptions=[]
- [ ] Denylist-first evaluation; case-normalized matching
- [ ] Bypass-resistance tests pass (mislabel, case, extension attacks)
- [ ] Evidence bundles (PASS + BLOCK×2) with hashes delivered
