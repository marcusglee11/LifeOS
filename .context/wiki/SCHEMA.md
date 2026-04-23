---
type: schema
version: "2.0"
---

# Wiki Layer Schema v2.0

## Purpose

The wiki layer provides compact, cross-referenced entity pages for agent context injection.
It is a **derived, non-authoritative layer**. When wiki content conflicts with a canonical
doc under `docs/**`, the canonical doc wins. Never treat wiki pages as source of truth.

## Invariants

1. `source_docs` entries MUST be files under `docs/**` (repo-relative). No exceptions.
2. `source_docs` entries MUST NOT be directories.
3. `source_docs` entries MUST NOT reference `config/**`, `runtime/**`, root agent files
   (CLAUDE.md, .claude/), or any path outside `docs/**`.
4. `source_commit_max` MUST equal the git SHA of the newest commit that touched any
   of the page's declared `source_docs` files.
5. Tooling (refresh and lint) MUST fail closed on invalid source declarations — no
   silent fallback, no partial refresh.
6. Pages with `page_class: evergreen` MUST NOT contain volatile phase/progress/status
   claims. Current operational state belongs in `docs/11_admin/LIFEOS_STATE.md`.
7. Where source docs conflict, the wiki MUST surface the conflict explicitly in
   `Open Questions` using `> [!CONFLICT]` prefix, citing both sources.
8. Operational reality not yet canonized under `docs/**` MUST NOT be added to wiki
   pages. Canonize it under `docs/**` first, then source from there.

## Guarantee Tiers

Wiki-lint enforces three classes of guarantee with different enforcement mechanisms:

### Structural (mechanically enforced by tooling)

- All required frontmatter fields present (`source_docs`, `source_commit_max`, `authority`, `page_class`, `concepts`)
- Field VALUES: `authority` must equal `"derived"`; `page_class` must be `"evergreen"` or `"status"`; `concepts` must be non-empty; `source_docs` must be non-empty
- All required body sections present **in order**: `## Summary`, `## Key Relationships`, `## Authority Note`, `## Current Truth`, `## Open Questions`
- All pages listed in the Page Index exist on disk; no orphaned pages outside the index
- All `source_docs` paths resolve to files under `docs/**` (not directories, not other roots)

### Freshness (mechanically enforced by tooling)

- `source_commit_max` MUST equal `git log -1 --format=%H -- <all source_docs files>`
- Tooling rejects any page whose stored SHA does not match the computed newest-commit SHA across ALL declared source docs

### Semantic (not mechanically enforced — requires human or Council review)

- `page_class: evergreen` pages must not contain volatile phase/progress claims (Invariant 6)
- Conflicts between source docs must be surfaced with `> [!CONFLICT]` (Invariant 7)
- Operational reality not yet canonized under `docs/**` must not be added to wiki pages (Invariant 8)

**Passing wiki-lint proves structural integrity and source freshness only. It does NOT prove
semantic correctness or that the wiki accurately reflects current system state. Semantic
accuracy requires human review of page content.**

## Required Frontmatter (every page)

```yaml
---
source_docs:
  - docs/path/to/source.md     # files under docs/** only
source_commit_max: <sha>        # git SHA: newest commit among source_docs files
authority: derived              # always "derived" for wiki pages
page_class: evergreen | status  # evergreen = stable concepts; status = volatile state
concepts:
  - keyword
---
```

- `source_docs`: one or more **file** paths under `docs/**`
- `source_commit_max`: run `git log -1 --format="%H" -- <source_docs_files>` to compute
- `authority`: must be `derived` — wiki pages are never authoritative
- `page_class`: `evergreen` for stable concept pages; `status` for volatile operational state
- `concepts`: non-empty list of indexable keywords

## Required Body Sections (every page)

Every page MUST have these five headings (in order):

```
## Summary
## Key Relationships
## Authority Note
## Current Truth
## Open Questions
```

- **Summary**: 2–4 sentences. What is this thing? What problem does it solve?
- **Key Relationships**: Bulleted links to related wiki pages and source docs.
- **Authority Note**: Must state that canonical source docs win over this page.
  Standard text: "Canonical source: `<source_doc_path>`. That document wins on any conflict with this page."
- **Current Truth**: Concise summary of current canon state only. No phase progress,
  no programme narration. For `page_class: evergreen` pages, omit volatile claims entirely.
- **Open Questions**: Contradictions, gaps, or unresolved conflicts. Empty section is valid.
  Use `> [!CONFLICT]` prefix for explicit contradictions between sources.

## Compact Size

Target 200–400 tokens per page. Split if >600 tokens.

## Page Index

The following pages are part of the wiki layer:

| Page | Description |
|------|-------------|
| `home.md` | Agent navigation landing page; authority chain map |
| `target-architecture.md` | LifeOS target control-plane architecture (v2.3c) |
| `governance-model.md` | Constitution, hard invariants, Council |
| `agent-roles.md` | CEO, COO, EA, Antigravity role definitions and autonomy model |
| `coo-runtime.md` | COO runtime FSM, orchestration specs |
| `openclaw-integration.md` | OpenClaw gateway, COO invocation |
| `doc-stewardship.md` | Document steward protocol, DAP, sync |
| `mission-orchestration.md` | Mission lifecycle, tier model, executor types |
| `protocols-index.md` | Navigation index of active protocols |
| `backlog-task-system.md` | Backlog, task proposals, COO proposal flow |
| `build-workflow.md` | Worktree isolation, branch naming, build lifecycle |
