# Git Workflow Protocol v1.0

**Status:** Active  
**Enforcement:** `scripts/git_workflow.py`  
**Last Updated:** 2026-01-16

---

## 1. Core Principles

1. **Branch-per-build**: Every mission/build gets its own branch
2. **Main is sacred**: Direct commits to `main` are prohibited
3. **Test before merge**: CI must pass before merge to `main`
4. **No orphan work**: All branches must be merged or explicitly archived

---

## 2. Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature/Mission | `build/<topic>` | `build/cso-constitution` |
| Bugfix | `fix/<issue>` | `fix/test-failures` |
| Hotfix | `hotfix/<issue>` | `hotfix/ci-regression` |
| Experiment | `spike/<topic>` | `spike/new-validator` |

**Enforcement:** `scripts/git_workflow.py branch create <name>` validates pattern.

---

## 3. Workflow Stages

### Stage 1: Start Mission

```bash
python scripts/git_workflow.py branch create build/<topic>
```

- Creates branch from latest `main`
- Validates naming convention
- Records branch in `artifacts/active_branches.json`

### Stage 2: Work-in-Progress

- Commit freely to feature branch
- Push to remote for backup: `git push -u origin <branch>`

### Stage 3: Review Ready

```bash
python scripts/git_workflow.py review prepare
```

- Runs all tests
- Generates Review Packet checklist
- Creates PR if tests pass

### Stage 4: Approved

```bash
python scripts/git_workflow.py merge
```

- Verifies CI passed
- Squash-merges to `main`
- Deletes feature branch
- Updates `artifacts/active_branches.json`

---

## 4. Prohibited Operations

The following are **BLOCKED** by the workflow script:

| Operation | Why Blocked |
|-----------|-------------|
| `git checkout main && git commit` | Direct commits to main |
| `git push origin main` | Direct push to main (use PR) |
| `git branch -D` without merge | Orphan work detection |
| `git checkout <branch>` without safety gate | Branch divergence risk |

---

## 5. Emergency Override

For exceptional cases only:

```bash
python scripts/git_workflow.py --emergency <operation>
```

- Logs override to `artifacts/emergency_overrides.log`
- Requires explicit reason
- CEO must approve in retrospective

---

## 6. Integration Points

| System | Integration |
|--------|-------------|
| GitHub Branch Protection | `main` requires PR + CI pass |
| `repo_safety_gate.py` | Preflight before checkout |
| GEMINI.md Article XIX | Constitutional mandate |
| CI Pipeline | Runs on all PRs |

---

## 7. Recovery Procedures

### Orphan Branch Detected

```bash
python scripts/git_workflow.py recover orphan
```

### Divergence Detected

```bash
python scripts/git_workflow.py recover divergence
```

### Missing Critical Files

```bash
python scripts/git_workflow.py recover files
```
