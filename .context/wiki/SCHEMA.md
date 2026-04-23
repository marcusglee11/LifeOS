---
type: schema
version: "1.0"
---

# LifeOS Wiki — Maintenance Schema

This file is the contract that governs how an LLM maintains the wiki layer.
Do not hand-edit wiki pages; run `scripts/wiki/refresh_wiki.py` instead.

## Purpose

The wiki layer provides compact, cross-referenced entity pages for agent context
injection. Sources are `docs/00_foundations/` through `docs/08_manuals/`. Wiki
pages synthesize those sources — they do not duplicate verbatim text.

## Page Index

| File | Topic |
|------|-------|
| `governance-model.md` | Constitution, CEO supremacy, hard invariants, Council |
| `agent-roles.md` | COO, CEO, doc_steward, Antigravity, sprint agents |
| `coo-runtime.md` | FSM, engine lifecycle, orchestration layers, budget |
| `openclaw-integration.md` | Gateway, invoke pattern, COO adapter, invocation quirks |
| `build-workflow.md` | Worktree isolation, branch naming, close-build gates |
| `doc-stewardship.md` | DAP naming, freshness, index consistency, sync targets |
| `backlog-task-system.md` | backlog.yaml, LIFEOS_STATE, task proposal flow |
| `mission-orchestration.md` | Tier-2/3 layers, mission registry, executor types |
| `protocols-index.md` | Cross-reference of all active protocols |

## Required Frontmatter (every page)

```yaml
---
source_docs:
  - docs/path/to/source1.md
  - docs/path/to/source2.md
last_updated: <git commit SHA>
concepts:
  - keyword1
  - keyword2
---
```

## Required Sections (every page)

1. **Summary** — 2–4 sentences. What is this thing? What problem does it solve?
2. **Key Relationships** — Bulleted links to other wiki pages and source docs.
3. **Current State** — Operational status, active version, known blockers.
4. **Open Questions** — Contradictions or gaps (use `> [!CONFLICT]` prefix for contradictions).

## Maintenance Rules

1. **Incremental only** — When a source doc changes, update only pages whose
   `source_docs` frontmatter includes that path. Do not regenerate unaffected pages.
2. **Synthesize, don't copy** — Extract concepts and relationships; don't paste verbatim text.
3. **Stay compact** — Each page targets 200–400 tokens. If a page grows past 600 tokens,
   split it or move detail back to source docs.
4. **Flag contradictions** — If two source docs conflict, note it under Open Questions
   with `> [!CONFLICT]` and cite both sources.
5. **Update last_updated** — Set to the git SHA of the commit that changed the source doc.
6. **Cross-link** — Use relative wiki links (`[governance-model](governance-model.md)`)
   for inter-page links. Use repo-relative paths for source doc links.

## Refresh Trigger

`scripts/wiki/refresh_wiki.py` is called by the post-commit hook when files
under `docs/` change. It writes a diff to `.context/wiki/_pending_diff.patch`
for human review. Only after review should `scripts/wiki/commit_wiki_update.py`
be run to stage and commit the changes.

## Lint Gate

`python -m doc_steward.cli wiki-lint .` validates:
- Required frontmatter fields present on all pages
- All `source_docs` paths resolve to real files
- No page is stale (source doc newer than `last_updated` commit)
- All pages in this index exist; no orphaned pages
