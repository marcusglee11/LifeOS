# TODO Standard v1.0

**Version:** 1.0
**Date:** 2026-01-13
**Author:** Antigravity
**Status:** ACTIVE

---

## 1. Purpose

Define a structured TODO tagging system for LifeOS that makes the codebase the single source of truth for backlog management. TODOs live where work happens, with fail-loud enforcement for P0 items.

---

## 2. Canonical Tag Format

### Basic Format

```
LIFEOS_TODO[P0|P1|P2][area: <path>:<symbol>][exit: <exact command>] <what>
```

### Fail-Loud Format (P0 Only)

```
LIFEOS_TODO![P0][area: <path>:<symbol>][exit: <exact command>] <what>
```

### Components

| Component | Required | Description | Example |
|-----------|----------|-------------|---------|
| `LIFEOS_TODO` | ✅ | Tag identifier (never use generic `TODO`) | `LIFEOS_TODO` |
| `!` | Optional | Fail-loud marker (P0 only; must raise exception) | `LIFEOS_TODO!` |
| `[P0\|P1\|P2]` | ✅ | Priority level | `[P0]` |
| `[area: ...]` | Recommended | Code location (path:symbol) | `[area: runtime/cli.py:cmd_status]` |
| `[exit: ...]` | ✅ | Verification command | `[exit: pytest runtime/tests/test_cli.py]` |
| Description | ✅ | What needs to be done | `Implement config validation` |

---

## 3. Priority Levels

### P0: Critical

**Definition:** Correctness or safety risk if incomplete or silently bypassed

**Characteristics:**
- Blocking production use
- Could cause data loss, security issues, or silent failures
- Must be addressed before claiming "done" on related feature

**Fail-Loud Requirement:**
- If code path can be reached, MUST raise exception
- Pattern: `raise NotImplementedError("LIFEOS_TODO![P0][area: ...][exit: ...] ...")`
- Exception message MUST include the full TODO header

**Example:**
```python
def process_sensitive_data(data):
    # LIFEOS_TODO![P0][area: runtime/data.py:process_sensitive_data][exit: pytest runtime/tests/test_data.py] Implement encryption
    raise NotImplementedError(
        "LIFEOS_TODO![P0][area: runtime/data.py:process_sensitive_data]"
        "[exit: pytest runtime/tests/test_data.py] Implement encryption"
    )
```

### P1: High Priority

**Definition:** Important but not safety-critical

**Characteristics:**
- Degrades user experience or maintainability
- Should be addressed soon
- Can ship without completing if documented

**Example:**
```python
# LIFEOS_TODO[P1][area: runtime/config.py:load_config][exit: pytest runtime/tests/test_config.py] Add schema validation for nested objects
def load_config(path):
    # ... basic validation only
    pass
```

### P2: Polish

**Definition:** Cleanup, documentation, or minor improvements

**Characteristics:**
- Nice to have
- Low impact if deferred
- Technical debt reduction

**Example:**
```python
# LIFEOS_TODO[P2][area: runtime/utils.py][exit: pytest runtime/tests/test_utils.py] Refactor shared validation logic into helper
def validate_input_a(data):
    # ... duplicated validation logic
    pass
```

---

## 4. Optional Body Format

Keep bodies tight (2-6 lines max). Use only when context is needed.

```python
# LIFEOS_TODO[P1][area: runtime/missions/build.py:run][exit: pytest runtime/tests/test_build_mission.py] Add incremental build support
# Why: Full rebuilds are slow for large projects
# Done when:
#   - Cache previous compilation outputs
#   - Detect changed files and rebuild only those
#   - Tests pass with incremental builds
```

**Sections:**
- **Why:** One sentence explaining rationale
- **Done when:** 1-3 bullets defining completion criteria
- **Notes:** (Optional) Additional context or constraints

---

## 5. Fail-Loud Stub Requirements

### When Required

Fail-loud stubs (using `LIFEOS_TODO!`) are REQUIRED for P0 TODOs where:
1. The incomplete code path can be reached during normal operation
2. Silent bypass could cause correctness or safety issues
3. The function/method is part of a public API or called by other modules

### When NOT Required

Fail-loud stubs are NOT required when:
- Code path is unreachable (dead code, commented out, etc.)
- P1 or P2 priority
- Function is clearly marked as a placeholder in documentation

### Implementation Pattern

```python
def incomplete_function(params):
    """
    Function description.

    LIFEOS_TODO![P0][area: module.py:incomplete_function][exit: pytest tests/test_module.py] Complete implementation
    """
    raise NotImplementedError(
        "LIFEOS_TODO![P0][area: module.py:incomplete_function]"
        "[exit: pytest tests/test_module.py] Complete implementation"
    )
```

---

## 6. Inventory and Discovery

### Canonical Tool

Use `scripts/todo_inventory.py` for ALL TODO searching:

```bash
# View all TODOs (Markdown)
python scripts/todo_inventory.py

# View as JSON
python scripts/todo_inventory.py --json

# Filter by priority
python scripts/todo_inventory.py --priority P0
```

### Never Use Generic Grep

❌ **WRONG:**
```bash
grep -r "TODO" .
```

✅ **CORRECT:**
```bash
python scripts/todo_inventory.py
```

**Rationale:** Generic `grep` finds comments in third-party code, doesn't parse the structured format, and lacks filtering.

---

## 7. Migration Rules

### Opportunistic Migration

When touching a file with legacy TODOs:
1. Convert legacy `TODO` comments to `LIFEOS_TODO` format
2. Add priority, area, and exit command
3. For P0 items, add fail-loud stub if needed

### Controlled Migration Batches

For large-scale migration:
1. Create explicit migration mission/task
2. Migrate in small batches (5-10 TODOs per batch)
3. Verify each batch with `scripts/todo_inventory.py`
4. Commit after each batch

### No Mechanical Rewrites

❌ **Never** do repo-wide find/replace without approval
✅ **Always** consider context and add proper metadata

---

## 8. Governance Integration

### Forbidden Tokens

The closure bundle validator MUST:
- ✅ **ALLOW** structured `LIFEOS_TODO` and `LIFEOS_TODO!` tags
- ❌ **FORBID** raw `TODO`, `TBD`, `FIXME`, `XXX`, `HACK`, `[PENDING]`

**Rationale:** Structured TODOs are tracked and have exit criteria; unstructured TODOs are technical debt.

### Constitutional Alignment

This protocol follows:
- **Deterministic Artefact Protocol v2.0** - TODOs are discoverable and verifiable
- **Test Protocol v2.0** - Exit commands define done criteria
- **LifeOS Constitution v2.0** - Audit completeness (all work is visible)

---

## 9. Examples

### Example 1: P0 Fail-Loud with Body

```python
def authenticate_user(credentials):
    """
    Authenticate user and return session token.

    LIFEOS_TODO![P0][area: runtime/auth.py:authenticate_user][exit: pytest runtime/tests/test_auth.py] Implement secure authentication
    Why: Current implementation has no auth; anyone can access
    Done when:
      - Validate credentials against user database
      - Generate secure session token (JWT with expiration)
      - Tests cover valid/invalid credentials and token expiration
    """
    raise NotImplementedError(
        "LIFEOS_TODO![P0][area: runtime/auth.py:authenticate_user]"
        "[exit: pytest runtime/tests/test_auth.py] Implement secure authentication"
    )
```

### Example 2: P1 In-Code Comment

```python
# LIFEOS_TODO[P1][area: runtime/config.py:load_config][exit: pytest runtime/tests/test_config.py] Add environment variable override support
def load_config(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config  # No env var support yet
```

### Example 3: P2 Documentation TODO

```markdown
# Mission Orchestrator

The mission orchestrator coordinates execution of mission types.

<!-- LIFEOS_TODO[P2][area: docs/03_runtime/orchestration.md][exit: doc_steward.cli dap-validate docs/03_runtime/orchestration.md] Add sequence diagrams for mission lifecycle -->

## Architecture
...
```

---

## 10. Verification Commands

### Verify Script Works

```bash
python scripts/todo_inventory.py --json | jq '.todos | length'
```

**Expected:** Count of TODOs in codebase

### Verify P0 Fail-Loud Stubs

```bash
# Run tests; P0 stubs should raise NotImplementedError
pytest runtime/tests -v
```

**Expected:** Tests fail with clear NotImplementedError messages showing TODO context

### Verify Protocol Compliance

```bash
python -m doc_steward.cli dap-validate docs/02_protocols/TODO_Standard_v1.0.md
```

**Expected:** `[PASSED] DAP validation passed.`

---

## 11. Anti-Patterns

### ❌ Vague TODOs

```python
# TODO: fix this
```

**Problem:** No priority, area, or exit criteria. Unmaintainable.

### ❌ Generic TODO in Closure Bundle

```python
# TODO: implement later
```

**Problem:** Forbidden token in governance artefacts. Fails closure validation.

### ❌ P0 Without Fail-Loud

```python
# LIFEOS_TODO[P0][area: ...][exit: ...] Critical security implementation needed
def process_payment(amount):
    pass  # Silent failure risk
```

**Problem:** P0 code path can be reached without raising exception.

### ❌ No Exit Command

```python
# LIFEOS_TODO[P1][area: runtime/utils.py] Refactor this
```

**Problem:** No verification criteria. How do we know when it's done?

---

## 12. Lifecycle

### Adding a TODO

1. Determine priority (P0/P1/P2)
2. Place in relevant file at exact location
3. Include area, exit command, and description
4. For P0: add fail-loud stub if code path is reachable
5. Verify with `python scripts/todo_inventory.py`

### Completing a TODO

1. Implement the work
2. Run the exit command to verify completion
3. Remove the TODO tag
4. Verify with `python scripts/todo_inventory.py` (count should decrease)

### Deferring a TODO

1. If priority changes, update the tag (e.g., P0 → P1)
2. Add context in body explaining why deferred
3. Never delete TODOs without completing or explicitly deciding to reject

---

## 13. Scope Boundaries

### In Scope

- `runtime/` - All runtime code
- `docs/` - Documentation markdown files
- `config/` - Configuration YAML/JSON files
- `scripts/` - Utility scripts
- Root-level files (README.md, CLAUDE.md, etc.)

### Out of Scope

- `.git/` - Version control internals
- `__pycache__/`, `*.pyc` - Build artifacts
- `.claude/skills/*/` - Third-party submodules
- `.venv/`, `venv/`, `node_modules/` - Dependencies

**Enforcement:** `scripts/todo_inventory.py` excludes out-of-scope paths.

---

*This protocol ensures all work is visible, verifiable, and tracked at the point of need.*
