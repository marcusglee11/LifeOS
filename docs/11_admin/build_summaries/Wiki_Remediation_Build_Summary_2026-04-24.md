# Wiki Remediation Build Summary — 2026-04-24

**Branch:** `build/wiki-remediation`
**Executed by:** Claude Code (sprint agent)
**Instruction block:** `AGENT INSTRUCTION BLOCK — WIKI REMEDIATION: TRUE, SIMPLE, USABLE`

---

## Files Changed

### Schema

- `.context/wiki/SCHEMA.md` — upgraded to v2.0; new contract (docs/** restriction,
  source_commit_max, 5-section requirement, evergreen/volatile rules)

### Tooling

- `doc_steward/wiki_lint_validator.py` — added source path validation, source_commit_max
  validation, required-section check; replaced last_updated/mtime staleness logic; added
  subprocess exception handling
- `scripts/wiki/refresh_wiki.py` — patched `_call_ea()` prompt to new schema contract;
  added pre-flight source validation (runs before `--dry-run` return); added in-loop source
  gate; compute source_commit_max per page instead of HEAD SHA
- `runtime/tests/test_wiki_lint_validator.py` — added 6 new test cases covering new contract
  invariants; updated _VALID_PAGE and test_missing_frontmatter_field for v2.0 schema

### New Canonical Docs

- `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md` — eliminates wiki dependence on
  runtime/ and config/ sources for OpenClaw facts
- `docs/00_foundations/Agent_Roles_Reference_v1.0.md` — eliminates wiki dependence on
  config/agent_roles/coo.md for COO autonomy model

### docs/INDEX.md

- Fixed stale reference: `Document_Steward_Protocol_v1.0.md` → `v1.1.md`
- Fixed stale reference: `Build_Handoff_Protocol_v1.0.md` → `v1.1.md`
- Added `LifeOS Target Architecture v2.3c.md` to 00_foundations section
- Added `OpenClaw_COO_Integration_v1.0.md` and `Agent_Roles_Reference_v1.0.md`

### New Wiki Pages

- `.context/wiki/home.md` — agent navigation landing page (new)
- `.context/wiki/target-architecture.md` — CEO→COO→EA architecture reference (new)

### Rewritten Wiki Pages

- `.context/wiki/governance-model.md` — removed volatile phase claims; added Authority Note; fixed frontmatter
- `.context/wiki/agent-roles.md` — replaced config/ source with new docs/ source
- `.context/wiki/coo-runtime.md` — removed runtime/ source; surfaced spec vs target-arch conflict
- `.context/wiki/openclaw-integration.md` — replaced all non-docs sources with canonical docs
- `.context/wiki/doc-stewardship.md` — removed cli.py source; surfaced Drive sync conflict
- `.context/wiki/mission-orchestration.md` — removed directory sources; surfaced tier-model vs target-arch conflict
- `.context/wiki/protocols-index.md` — replaced directory source with docs/INDEX.md; fixed sections
- `.context/wiki/backlog-task-system.md` — replaced config/ sources with docs/ equivalents
- `.context/wiki/build-workflow.md` — replaced CLAUDE.md/.claude/ sources with protocol docs

---

## Contract Changes (SCHEMA.md v1.0 → v2.0)

| Change | v1.0 | v2.0 |
| ------ | ---- | ---- |
| Source restriction | Sources from docs/ implied but not enforced | `source_docs` MUST be files under `docs/**` only |
| Directory sources | Not explicitly forbidden | Explicitly forbidden; tooling rejects |
| Freshness field | `last_updated` (git SHA of any change) | `source_commit_max` (newest commit among source files) |
| Required fields | `source_docs`, `last_updated`, `concepts` | `source_docs`, `source_commit_max`, `authority`, `page_class`, `concepts` |
| Required sections | Summary, Key Relationships, Current State, Open Questions | Summary, Key Relationships, **Authority Note**, **Current Truth**, Open Questions |
| Volatile content | Not restricted | `page_class: evergreen` pages MUST NOT carry volatile phase/status claims |
| Conflict handling | Not specified | MUST use `> [!CONFLICT]` and cite both sources |

---

## Pages Added

1. `home.md` — agent navigation landing page; authority chain map
2. `target-architecture.md` — LifeOS target control-plane architecture (v2.3c)

---

## Pages Rewritten

9 pages rewritten (see Files Changed above). Zero pages deleted.

---

## Conflicts Surfaced

| Page | Conflict |
| ---- | -------- |
| `coo-runtime.md` | `COO_Runtime_Core_Spec_v1.0.md` (SQLite/FSM/Engineer-QA model) vs `LifeOS Target Architecture v2.3c.md` (CEO→COO→EA/GitHub model) |
| `mission-orchestration.md` | Tier-1/2/3 model (runtime spec) vs phased CEO→COO→EA model (target architecture) |
| `doc-stewardship.md` | `Document_Steward_Protocol_v1.1.md` claims bidirectional Drive sync; `LifeOS Target Architecture v2.3c` (canonical) says Drive is read-only, GitHub→Drive one-directional — protocol needs updating to align with v2.3c |
| `target-architecture.md` | Multiple earlier ARCH_* proposals in `docs/00_foundations/` vs v2.3c (v2.3c is canonical; older docs remain) |

---

## Pass/Fail Results

| Check | Result |
| ----- | ------ |
| `wiki-lint .` | PASS |
| No non-docs sources | PASS |
| No directory sources | PASS |
| source_commit_max on all pages | PASS |
| home.md and target-architecture.md exist | PASS |
| refresh_wiki.py --dry-run --full | PASS |
| pytest runtime/tests -q | PASS (3166 passed, 5 pre-existing failures) |
| dap-validate . | PASS |
