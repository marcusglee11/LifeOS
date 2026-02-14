# docs/11_admin — Admin Documentation

**Purpose:** Lightweight control plane for project state, backlog, and decisions.

**Last Updated:** 2026-02-14 (consolidation v1.0)

---

## Authority Hierarchy

When statements conflict, resolve by this precedence (highest → lowest):

1. **`LIFEOS_STATE.md` + `BACKLOG.md`** (canonical, auto-updated)
2. **`DECISIONS.md`** (append-only; decisions override intent/spec drift)
3. **`Plan_Supersession_Register.md` + referenced plan** (plan authority)
4. **Specs in `docs/11_admin/`** (e.g., `Doc_Freshness_Gate_Spec_v1.0.md`)
5. **Derived views** (e.g., `AUTONOMY_STATUS.md`) — must cite sources + derived-from timestamp
6. **Strategic context** (e.g., `lifeos-master-operating-manual-v2.1.md`)
7. **Archive** (historical reference only; no inbound links; immutable)

---

## Canonical Allowlist

### Required Files (Root)

These files **MUST** exist at `docs/11_admin/` root:

- `LIFEOS_STATE.md` — Single source of truth for current focus, WIP, blockers (auto-updated)
- `BACKLOG.md` — Actionable backlog (Now/Next/Later), target ≤40 items (auto-updated)
- `INBOX.md` — Raw capture scratchpad for triage
- `DECISIONS.md` — Append-only decision log

### Canonical Optional Files (Root)

These files are allowed at `docs/11_admin/` root:

- `LifeOS_Master_Execution_Plan_v1.1.md` — Current master execution plan (per supersession register)
- `Plan_Supersession_Register.md` — Canonical register of superseded and active plans
- `Doc_Freshness_Gate_Spec_v1.0.md` — Runtime-backed doc freshness gate spec
- `AUTONOMY_STATUS.md` — Derived view of autonomy capabilities
- `WIP_LOG.md` — Work-in-progress tracker with controlled status enum
- `lifeos-master-operating-manual-v2.1.md` — Strategic operating context

### Allowed Subdirectories

Only these subdirectories are permitted under `docs/11_admin/`:

- **`build_summaries/`** — Timestamped build evidence summaries
  - **Naming rule:** `*_Build_Summary_YYYY-MM-DD.md`
  - Example: `E2E_Spine_Proof_Build_Summary_2026-02-14.md`

- **`archive/`** — Historical documents (reference only; immutable)
  - **Subdir naming rule:** `YYYY-MM-DD_<topic>/`
  - Example: `2026-02-14_consolidation/`
  - **Required:** Each archive subdir MUST contain a `README.md` with disposition table
  - **Link policy:** See Archive Policy below

---

## Archive Policy

**Archived files are immutable.** Only allowed modifications:
- Typo fixes in the archive README itself
- Mechanical path corrections if repo structure changes (rare)

**Link hygiene:**
- Active docs MUST NOT link to archived files
- Exception: `docs/11_admin/README.md` (this file) may link to archive subdir READMEs only
- Archive subdirectory READMEs may link to archived files within their own subdir

See [archive/2026-02-14_consolidation/README.md](./archive/2026-02-14_consolidation/README.md) for the consolidation disposition table.

---

## Validation Commands

Run these to validate admin doc structure and hygiene:

```bash
# Structure enforcement (fail-closed; always blocking)
python3 -m doc_steward.cli admin-structure-check .

# Archive link ban (fail-closed; always blocking)
python3 -m doc_steward.cli admin-archive-link-ban-check .

# Freshness check (mode-gated: off/warn/block)
LIFEOS_DOC_FRESHNESS_MODE=warn python3 -m doc_steward.cli freshness-check .

# Full doc stewardship suite
python3 -m doc_steward.cli index-check . docs/INDEX.md
python3 -m doc_steward.cli link-check .
```

**Freshness mode:**
- `off` (default): No freshness checking
- `warn`: Emit warnings but do not fail
- `block`: Fail on violations

Freshness checks:
- `artifacts/status/runtime_status.json` must be <24h old
- Structured contradictions field must be empty (or only "warn" severity in warn mode)

---

## Adding a New Admin Doc

If you need to add a new admin doc (rare):

1. **Add a `DECISIONS.md` entry** explaining why the doc exists
2. **Update the allowlist validator** (`doc_steward/admin_structure_validator.py`)
   - Add to `REQUIRED_FILES` (if mandatory) or `CANONICAL_OPTIONAL_FILES` (if optional)
3. **Update `docs/INDEX.md`** with the new doc reference
4. **Run validation** to confirm structure is still valid

**Default answer: Don't add new docs.** The admin directory is intentionally thin. Most content belongs in:
- `docs/00_foundations/` (core principles)
- `docs/01_governance/` (governance & contracts)
- `docs/02_protocols/` (protocols & procedures)
- `docs/03_runtime/` (runtime specs & plans)
- `docs/08_manuals/` (operational manuals)

---

## Maintenance Workflow

### When modifying admin docs:

1. **Pre-flight:**
   ```bash
   git status
   python3 -m doc_steward.cli admin-structure-check .
   ```

2. **Make changes** (following authority hierarchy)

3. **Post-flight:**
   ```bash
   python3 -m doc_steward.cli admin-structure-check .
   python3 -m doc_steward.cli admin-archive-link-ban-check .
   python3 -m doc_steward.cli index-check . docs/INDEX.md
   python3 -m doc_steward.cli link-check .
   git status --porcelain=v1
   ```

### When auto-update fails:

If `LIFEOS_STATE.md` or `BACKLOG.md` auto-update fails, investigate:
- Check `runtime/tools/workflow_pack.py` (`update_state_and_backlog()`)
- Review recent commits for conflicts
- Manually sync if needed, but preserve auto-update capability

---

## Status Enum (WIP_LOG.md)

**Allowed status values:** `WIP | FINALIZED | CANONICAL | DEFERRED`

- **WIP**: Active work in progress, not yet complete
- **FINALIZED**: Complete but awaiting formal ratification/activation
- **CANONICAL**: Ratified and active (binding)
- **DEFERRED**: Work paused or postponed

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) — Claude Code agent guidance (references admin docs)
- [docs/INDEX.md](../INDEX.md) — Full documentation index
- [COO_Doc_Management_Manual_v1.0.md](../08_manuals/COO_Doc_Management_Manual_v1.0.md) — Operational runbook for doc maintenance
