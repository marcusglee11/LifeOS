---
source_docs:
  - docs/02_protocols/Document_Steward_Protocol_v1.1.md
  - docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md
  - doc_steward/cli.py
last_updated: bf4d9ecd
concepts:
  - DAP
  - doc_steward
  - freshness
  - index consistency
  - Google Drive sync
  - document stewardship
---

# Doc Stewardship

## Summary

Document stewardship is agent-owned, not human-operated. The doc_steward CLI
validates naming, link integrity, index consistency, and freshness. The CEO
never manually shuffles docs or updates indices. Source of truth is always
the local `docs/` directory; GitHub and Google Drive are sync targets.

## Key Relationships

- **[governance-model](governance-model.md)** — Constitution defines protected paths.
- **[build-workflow](build-workflow.md)** — doc changes go through the same worktree/PR flow.
- **CLI**: `python -m doc_steward.cli <command> <repo_root>`
- **Protocol**: `docs/02_protocols/Document_Steward_Protocol_v1.1.md`
- **DAP spec**: `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md`

## doc_steward CLI Commands

| Command | Purpose |
|---------|---------|
| `dap-validate .` | DAP naming compliance |
| `index-check . docs/INDEX.md` | Index vs actual file consistency |
| `link-check .` | Broken internal links |
| `freshness-check .` | Stale doc detection (mode-gated: off/warn/fail) |
| `admin-structure-check .` | `docs/11_admin/` structure validation |
| `protocols-structure-check .` | `docs/02_protocols/` structure |
| `wiki-lint .` | *(new)* Wiki layer validation |

## Sync Targets

| Target | Trigger | Purpose |
|--------|---------|---------|
| GitHub | Every commit | Primary backup |
| Google Drive | Same session as changes | External access, NotebookLM feed |

Auto-generated corpus files: `docs/LifeOS_Universal_Corpus.md` (all docs),
`docs/LifeOS_Strategic_Corpus.md` (filtered for AI).

## Stewardship Ledger

All stewardship runs recorded as YAML at `artifacts/ledger/dl_doc/YYYY-MM-DD_<trial_type>_<case_id>.yaml`.

## Protected Paths

`docs/00_foundations/` and `docs/01_governance/` require Council approval.
The pre-commit hook (`scripts/claude_doc_stewardship_gate.py`) enforces this.

## CEO Constraint

Maximum 2 human steps per stewardship operation; anything more must be automated.
CEO approves only; agent performs all file creation, indexing, syncing.

## Current State

Protocol at v1.1 (adopted canonical packet envelope). Google Drive auto-sync
active (bidirectional via Drive Desktop). Freshness check mode: configurable.

## Open Questions

None currently flagged.
