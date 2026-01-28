# CLAUDE.md

LifeOS is a multi-agent orchestrator for AI governance and personal productivity. **Antigravity is the primary builder**; Claude Code operates as a sprint insertion team for focused, bounded work.

**Expectation**: Deliver focused value within scope. Don't over-scope or add unrequested improvements.

---

## Before You Touch Anything

**Mandatory pre-flight checklist** (do these in order):

1. **Check current state** - Understand what's in flight
   ```bash
   cat docs/11_admin/LIFEOS_STATE.md
   ```

2. **Check git status** - See uncommitted work
   ```bash
   git status
   ```

3. **Verify tests pass** - Confirm baseline is green
   ```bash
   pytest runtime/tests -q
   ```

4. **Confirm scope** - Ask what files/areas are in scope for this sprint

---

## Protected Areas (Hands Off)

These paths require Council approval to modify. **Do not touch unless explicitly asked**:

- `docs/00_foundations/` - Constitution, architecture foundations
- `docs/01_governance/` - Protocols, council rulings
- `config/governance/protected_artefacts.json`

If you need to modify these, stop and ask the user first.

---

## Project Structure

```
lifeos/
├── runtime/           # COO Runtime (main codebase)
│   ├── engine.py      # FSM orchestrating system lifecycle
│   ├── mission/       # Mission registry (Tier-3)
│   ├── orchestration/ # Execution orchestration (Tier-2)
│   ├── governance/    # Protection layers, validators
│   ├── api/           # Public API surfaces
│   └── tests/         # Primary test suite (415+ tests)
│
├── docs/              # Source of truth for governance & specs
│   ├── 00_foundations/  # Constitution, architecture (protected)
│   ├── 01_governance/   # Protocols, rulings (protected)
│   ├── 02_protocols/    # Operational protocols
│   ├── 11_admin/        # LIFEOS_STATE, BACKLOG, DECISIONS
│   └── INDEX.md         # Navigation index
│
├── project_builder/   # Multi-agent orchestration
├── recursive_kernel/  # Self-improvement loop
├── doc_steward/       # Document governance CLI
├── config/            # Configuration files
├── artifacts/         # Agent-generated outputs
└── scripts/           # Utility scripts
```

---

## Essential Commands

```bash
# Run tests (do this before AND after changes)
pytest runtime/tests -q

# TDD compliance check
pytest tests_doc/test_tdd_compliance.py

# Full test suite
pytest

# Check current project state
cat docs/11_admin/LIFEOS_STATE.md

# View backlog
cat docs/11_admin/BACKLOG.md

# Validate docs if you modified them
python -m doc_steward.cli dap-validate .
```

---

## How to Work

### Sprint Team Rules

1. **Do what was asked, nothing more** - No unrequested refactoring or improvements
2. **Follow existing patterns** - Look at similar files before creating new ones
3. **Small batches** - Make incremental changes, verify each step
4. **Tests matter** - Run tests before and after. If tests break, fix before moving on
5. **Match code style** - Follow conventions in the existing codebase

### TDD When Practical

- Write test first when adding new functionality
- For bug fixes, add a regression test
- For refactoring, ensure existing tests still pass
- Results are priority - don't over-engineer test infrastructure

### Pattern Discovery

Before writing new code:
1. Search for similar functionality in the codebase
2. Check how existing modules handle the same concerns
3. Reuse existing utilities rather than creating new ones

---

## Mistakes to Avoid

### 1. Over-Scoping
- Don't refactor code that wasn't asked to be refactored
- Don't add features not explicitly requested
- Don't "improve" adjacent code while fixing something else
- Don't add documentation, comments, or type hints to unchanged code

### 2. Ignoring Patterns
- Check how the codebase already does things before inventing new approaches
- Match existing error handling, logging, and validation patterns
- Use existing utilities rather than creating duplicates

### 3. Conflicting with Work-in-Progress
- Check `LIFEOS_STATE.md` for what's currently being worked on
- Ask before modifying files that might be in active development
- If unsure, ask about scope boundaries

### 4. Breaking Tests
- Run `pytest runtime/tests -q` after every significant change
- Never commit with failing tests
- Fix test failures before moving on to new work

### 5. Governance Trampling
- Leave `docs/00_foundations/` and `docs/01_governance/` alone
- Don't modify protected paths without explicit permission
- When in doubt, ask

---

## Key References

| What | Where |
|------|-------|
| Current state & WIP | `docs/11_admin/LIFEOS_STATE.md` |
| Prioritized backlog | `docs/11_admin/BACKLOG.md` |
| Doc navigation | `docs/INDEX.md` |
| Constitution (deep context) | `docs/00_foundations/LifeOS_Constitution_v2.0.md` |
| Strategic corpus | `docs/LifeOS_Strategic_Corpus.md` |

---

## Handoff Protocol

When finishing a sprint:

1. **Run full test suite**
   ```bash
   pytest runtime/tests -q
   ```

2. **Verify git status is clean**
   ```bash
   git status --porcelain=v1  # Should be empty or only expected changes
   ```

3. **Commit evidence** (if committing)
   ```bash
   git rev-parse HEAD
   git log -1 --oneline
   ```

4. **Update state if scope changed** - If you discovered new work or changed scope, note it

5. **Document discoveries** - If you learned something about the codebase that would help future sprints, mention it

---

## WSL Notes

This repo runs on WSL with Windows-mounted working copy (`/mnt/c/...`).

- Only one Git "reality" should touch the working tree during agent runs
- Avoid Windows Git/IDEs doing Git operations mid-run
- Line endings are enforced LF via `.gitattributes`

---

## Quick Reference

```bash
# Pre-flight
cat docs/11_admin/LIFEOS_STATE.md && git status && pytest runtime/tests -q

# After changes
pytest runtime/tests -q && git status

# Handoff
pytest && git status --porcelain=v1
```
