# LifeOS Operator Onboarding

<!-- markdownlint-disable MD013 -->

## Purpose

This guide is the first human-readable onboarding path for a new LifeOS operator or AI assistant. It does not create new architecture. It explains how to enter the existing system without treating chat memory, wiki pages, or generated corpora as canon.

## One-sentence model

LifeOS turns CEO intent into COO-managed operations, then into bounded executing-agent work, with GitHub issues and repo evidence as the durable control plane.

## Surfaces

| Surface | Use it for | Do not use it for |
| --- | --- | --- |
| `LifeOS` | Canonical doctrine, current state, runtime code, documentation authority, doc stewardship | Cross-repo dispatch truth when a bus issue owns the workstream |
| `lifeos-operational-bus` | Operational work orders, evidence receipts, continuation batons, cross-repo runtime/agent trackers | Canonical architecture doctrine unless explicitly promoted back into `LifeOS` |
| `lifeos-common-hub` | Shared schemas, common skills, extracted reusable standards | First-draft operational work that has not stabilised |

## Roles and boundaries

| Actor | Plain-English role | Boundary |
| --- | --- | --- |
| CEO | Decides strategic intent and high-risk trade-offs | Does not need to be middleware for routine reversible execution |
| COO | Converts intent into scoped work, chooses lanes, maintains evidence, escalates real gates | Does not invent strategic intent or override explicit CEO decisions |
| Executing agents / workers | Implement, test, inspect, or review a bounded slice | Do not own truth; their claims require conductor readback |
| Advisory agents | Provide architecture/security/assurance review | Advisory evidence, not automatic approval unless a protocol says so |

## Authority order

When two surfaces disagree, resolve in this order:

1. Canonical `LifeOS` repo docs, governance records, and authority registry.
2. Live GitHub issue/PR state, exact commits, CI/checks, and read-back receipts.
3. Derived navigation surfaces such as `docs/LifeOS_Strategic_Corpus.md` and `.context/wiki/`.
4. Agent memory, chat summaries, local scratch notes, and unverified worker claims.

If a derived surface contradicts canon, treat the derived surface as stale and file or update a documentation-drift tracker. Do not auto-edit canonical docs from a sweep.

## First read chain

Read these in order:

1. `README.md` — current high-level map and authority warning.
2. `docs/INDEX.md` — authoritative documentation index.
3. `docs/LifeOS_Strategic_Corpus.md` — derived high-context snapshot.
4. `docs/11_admin/LIFEOS_STATE.md` — current focus, WIP, blockers, and latest baseline state.
5. `docs/00_foundations/LifeOS Target Architecture v2.3c.md` — current canonical target architecture.
6. `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` — agent-specific operating instructions.
7. `.context/REPO_MAP.md` — repository layout and navigation aid, if present.

## How to start work safely

1. Read the live GitHub issue before editing.
2. Confirm whether the issue is a LifeOS repo issue, an operational-bus issue, or a shared-hub issue.
3. Use a clean build worktree for implementation.
4. Keep scope to the issue's acceptance criteria.
5. For docs changes, update `docs/INDEX.md`, regenerate `docs/LifeOS_Strategic_Corpus.md`, and run the doc/quality gates.
6. For new risks or drift discovered during work, search for an existing tracker before creating a new one.
7. Post evidence back to the controlling issue when the slice is complete or blocked.

## Documentation stewardship rules

- `config/docs/authority_registry.yaml` is the machine-readable authority registry.
- Proposal-only and archived docs are not canonical just because they are persuasive.
- `docs/LifeOS_Strategic_Corpus.md` is generated/derived; do not edit it by hand.
- `.context/wiki/` is derived and human-readable; it must not outrank repo canon.
- Entry docs should orient and route. They should not smuggle new architecture decisions.

## Stop and escalate when

- A change would alter CEO/COO authority, execution tiers, merge authority, credential handling, public/upstream behaviour, billing, or irreversible/destructive state.
- Canonical docs and live issue/PR evidence materially contradict each other.
- The next safe action requires missing credentials or external account changes.
- A proposed doc change would promote proposal-only material into canon without review evidence.
