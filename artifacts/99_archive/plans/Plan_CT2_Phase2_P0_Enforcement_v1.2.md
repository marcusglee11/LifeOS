---
packet_id: ct2-phase2-p0-enforcement-v1.2
packet_type: PLAN_ARTIFACT
version: 1.2
mission_name: CT-2 Phase 2 P0 Enforcement Hardening
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Plan: CT-2 Phase 2 (P0) — OpenCode Doc Steward Enforced Gate

## Goal

Harden the OpenCode doc-steward gate with: (1) correct index enumeration with fail-closed discovery, (2) CI-safe blocked-op detection, (3) evidence-tampering prevention, (4) bypass-resistant path normalization.

## Binding Constraints

> [!CAUTION]
> - delete/rename/move/copy → ALWAYS BLOCK (git-diff reality, not JSON)
> - Only `.md` under `docs/` writable; extension_exceptions = []
> - Packet discovery = explicit `packet_paths` only
> - Denylist-first; case-normalized matching

---

## P0.1 — WRITABLE_INDEX_FILES (Fail-Closed Discovery)

**Problem**: Previous plan listed `config/index.md` which is under denylisted `config/` root.

**Solution**: Deterministic discovery from allowed roots only:

```python
def discover_writable_index_files(repo_root: str) -> list[str]:
    """Discover index files ONLY under allowed roots."""
    candidates = []
    for root in ALLOWLIST_ROOTS:  # ["artifacts/review_packets/", "docs/"]
        for dirpath, _, files in os.walk(os.path.join(repo_root, root)):
            for f in files:
                if f.lower() == "index.md":
                    rel = os.path.relpath(os.path.join(dirpath, f), repo_root)
                    norm = normalize_path(rel)
                    # Exclude if under denylist
                    if not matches_denylist(norm)[0]:
                        candidates.append(norm)
    return sorted(candidates)

# Fail-closed: if empty or >10, treat as ambiguous
WRITABLE_INDEX_FILES = discover_writable_index_files(REPO_ROOT)
if not WRITABLE_INDEX_FILES or len(WRITABLE_INDEX_FILES) > 10:
    # BLOCK with reason code INDEX_DISCOVERY_AMBIGUOUS
    # Print sorted candidates for human resolution
```

**Corrected Hardcoded Fallback** (Phase 2):
```python
WRITABLE_INDEX_FILES = [
    "docs/index.md",
    "docs/01_governance/index.md",
]
# Note: config/index.md REMOVED (under denylist root)
# Note: artifacts/index.md REMOVED (not under review_packets/)
```

---

## P0.2 — CI-Safe Blocked-Op Detection

**Problem**: `git diff --cached` only works for local staged changes, not CI PRs.

**Solution**: Parameterized diff detection:

```python
def get_diff_command() -> list[str]:
    """Return appropriate diff command for execution context."""
    # CI environment detection
    base_ref = os.environ.get("GITHUB_BASE_REF") or os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_SHA")
    head_ref = os.environ.get("GITHUB_SHA") or os.environ.get("CI_COMMIT_SHA") or "HEAD"
    
    if base_ref:
        # CI mode: compare base..HEAD
        return ["git", "diff", "--name-status", "-z", f"{base_ref}...{head_ref}"]
    else:
        # Local mode: staged changes
        return ["git", "diff", "--cached", "--name-status", "-z"]

def detect_blocked_ops() -> list[tuple[str, str, str]]:
    """Detect D/R/C operations. Returns [(path, op, reason_code)]."""
    cmd = get_diff_command()
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        # Fail-closed: cannot determine diff
        return [("UNKNOWN", "ERROR", "DIFF_COMMAND_FAILED")]
    
    if not result.stdout.strip():
        # No changes detected — NOT a silent pass, but valid empty
        return []
    
    blocked = []
    for entry in parse_git_status_z(result.stdout):
        status, path = entry
        if status == "D":
            blocked.append((path, "delete", "PH2_DELETE_BLOCKED"))
        elif status.startswith("R"):
            blocked.append((path, "rename", "PH2_RENAME_BLOCKED"))
        elif status.startswith("C"):
            blocked.append((path, "copy", "PH2_COPY_BLOCKED"))
    return blocked
```

---

## P1.1 — Review Packets Add-Only

**Policy**: `artifacts/review_packets/` allows ONLY add-new `.md` files.

```python
def check_review_packets_addonly(path: str, git_status: str) -> bool:
    """Return True if allowed, False if blocked."""
    norm = normalize_path(path)
    if not norm.startswith("artifacts/review_packets/"):
        return True  # Not in scope
    
    # Must be .md
    if not norm.endswith(".md"):
        return False  # NON_MD_IN_REVIEW_PACKETS
    
    # Must be Add only
    if git_status != "A":
        return False  # REVIEW_PACKET_NOT_ADD_ONLY
    
    return True
```

---

## P1.2 — normalize_path() Specification

```python
def normalize_path(path: str) -> str:
    """Normalize path for policy matching.
    
    - Backslashes → forward slashes
    - Strip leading './'
    - Collapse repeated slashes
    - Lowercase (for matching only; preserve original for reporting)
    """
    norm = path.replace("\\", "/")
    while "//" in norm:
        norm = norm.replace("//", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm.lower()
```

**Test Cases**:
| Input | Expected |
|-------|----------|
| `docs\\INDEX.md` | `docs/index.md` |
| `./docs/test.md` | `docs/test.md` |
| `docs//sub//file.md` | `docs/sub/file.md` |
| `DOCS/00_Foundations/x.md` | `docs/00_foundations/x.md` |
| `Gemini.MD` | `gemini.md` |

---

## P1.3 — Evidence Contract

**Hash Object Schema**:
```json
{"algorithm": "sha256", "hex": "a1b2c3..."}
```

**Truncation Constants**:
```python
LOG_MAX_LINES = 500
LOG_MAX_BYTES = 100000  # 100KB
TRUNCATION_FOOTER = "[TRUNCATED] cap_lines={}, cap_bytes={}, observed_lines={}, observed_bytes={}"
```

**Canonical Artefact Root** (from repo evidence):
```python
EVIDENCE_ROOT = "artifacts/evidence/opencode_steward_certification/"
```

---

## Explicit Enumerations (Final)

```python
ALLOWLIST_ROOTS = ["artifacts/review_packets/", "docs/"]
DENYLIST_ROOTS = ["config/", "docs/00_foundations/", "scripts/"]
DENYLIST_EXACT_FILES = ["gemini.md"]
DENYLIST_EXTENSIONS = [".py"]
ALLOWED_EXTENSIONS_DOCS = [".md"]
EXTENSION_EXCEPTIONS = []
WRITABLE_INDEX_FILES = ["docs/index.md", "docs/01_governance/index.md"]
```

---

## Tests

### Bypass-Resistance
| Test | Attack | Assertion |
|------|--------|-----------|
| `test_git_diff_mislabel_delete` | JSON=modify, git=D | BLOCK |
| `test_git_diff_mislabel_rename` | JSON=modify, git=R | BLOCK |
| `test_case_bypass_gemini` | `Gemini.MD` | BLOCK |
| `test_review_packet_modify_blocked` | Modify existing packet | BLOCK |
| `test_normalize_backslash` | `docs\\x.md` | Match allowed |

### Functional
| Test | Expected |
|------|----------|
| `test_allowed_md_pass` | PASS |
| `test_non_md_blocked` | BLOCK |
| `test_review_packet_add_pass` | PASS |
| `test_ci_diff_detection` | Correct base..HEAD |

---

## DONE Definition

- [ ] WRITABLE_INDEX_FILES excludes denylist roots; fail-closed if ambiguous
- [ ] Blocked ops detected via CI-safe diff (base..HEAD or --cached)
- [ ] `artifacts/review_packets/` is add-only `.md`
- [ ] `normalize_path()` handles backslash, leading `./`, repeated `/`, case
- [ ] Evidence: hash objects, truncation caps, canonical root constant
- [ ] Evidence bundles: PASS + BLOCK with hashes

---

## CHANGELOG

- **v1.2**: Fixed WRITABLE_INDEX_FILES contradiction, CI-safe diff, add-only packets, normalize_path spec
- **v1.1**: Git-diff-based op detection, bypass-resistance tests
- **v1.0**: Initial plan
