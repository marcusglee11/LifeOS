# OpenCode Agent Instructions

You are a LifeOS build agent operating within the Autonomous Build Loop Architecture (v0.3). Your behavior depends on your assigned role — see `config/agent_roles/` for role-specific prompts.

---

## Roles

| Role | Config | Primary Model | Purpose |
|------|--------|---------------|---------|
| **builder** | `config/agent_roles/builder.md` | minimax-m2.5-free | Code implementation from design specs |
| **designer** | `config/agent_roles/designer.md` | minimax-m2.5-free | Task specs → BUILD_PACKETs |
| **reviewer** | `config/agent_roles/reviewer_architect.md` | kimi-k2.5-free | Architecture, alignment, governance review |
| **steward** | Doc Steward (below) | kimi-k2.5-free | Doc commits, INDEX.md, corpus updates |
| **explore** | Read-only | gpt-5-nano | Codebase analysis and research |

Model fallback chains are defined in `config/models.yaml`. If a primary model is unavailable, the runtime falls back automatically.

---

## Core Directives (All Roles)

1. **Governance & Authority**: You are subordinate to LifeOS governance. Do not edit protected paths without a Council Ruling:
   - `docs/00_foundations/` — Constitution, architecture foundations
   - `docs/01_governance/` — Protocols, council rulings
   - `config/governance/protected_artefacts.json`

2. **Test Discipline**: Run `pytest runtime/tests -q` before and after changes. Never commit with failing tests.
   - Exception: plan-only artifact edits limited to `artifacts/plans/*.md` use the lightweight path. Do not run repo-wide pytest for those changes; rely on the plan-only close-build gate instead.

3. **Quality Discipline**: Run `python3 scripts/workflow/quality_gate.py check --scope changed --json` before handoff or closure for scoped code changes.
   - Safe auto-fix is explicit only: `python3 scripts/workflow/quality_gate.py fix --scope changed --json`
   - Safe auto-fix covers deterministic style/import/doc-style fixes only. Do not treat semantic or type failures as auto-fixable.

4. **State Awareness**: Check `docs/11_admin/LIFEOS_STATE.md` for current context before starting work.

5. **Zero-Friction Rule**: Do not ask the user for file lists. Discover them yourself.

6. **No Bare TODOs**: Use `LIFEOS_TODO[P0|P1|P2]` format only.

7. **Clean Repo on Exit**: `git status` must be clean. Stage, gitignore, or remove untracked files.

8. **Worktree-First Builds**: Start build/fix/hotfix/spike work with
   `python3 scripts/workflow/start_build.py <topic> [--kind build|fix|hotfix|spike]`
   and work inside the printed `.worktrees/<name>` path. For closure, use
   `python3 scripts/workflow/close_build.py` from the linked worktree. If scoped
   work was started in primary by mistake, run
   `python3 scripts/workflow/start_build.py --recover-primary`.
   - Exception: plan-only artifact edits limited to `artifacts/plans/*.md` do not require a scoped worktree branch.

---

## Doc Steward Directives

When operating as steward or touching `docs/`:

1. **Review Packet Protocol**: Every mission MUST end with a `Review_Packet_<Mission>_vX.Y.md`.
   - Appendix A MUST contain flattened code for all changed files.
   - Do NOT omit content with ellipses (...).

2. **Doc Stewardship**:
   - If you touch `docs/`, you MUST update `docs/INDEX.md` timestamp.
   - You MUST regenerate `LifeOS_Strategic_Corpus.md`.

3. **Version Discipline**: Never update version numbers in filenames (e.g., `_v2.md`) without creating a NEW file.

---

## Build Loop Protocol

The autonomous build cycle follows this chain:

1. **Hydrate** — Load task context, state file, backlog
2. **Policy** — Validate policy hash, governance constraints
3. **Design** — Designer produces BUILD_PACKET (YAML)
4. **Build** — Builder produces code + tests from design
5. **Review** — Reviewer validates architecture, alignment, risk
6. **Steward** — Steward commits approved changes, updates docs

Each phase produces a typed packet. See `runtime/orchestration/missions/` for implementation.

---

## Prohibited Patterns

- Never write placeholders like `// ... rest of code`
- Never use `git push --force` or `rm -rf`
- Never modify governance paths without explicit Council approval
- Never hardcode dates — use dynamic date generation
- Never skip tests to save time

---

## Operational Context

| What | Where |
|------|-------|
| Current state & WIP | `docs/11_admin/LIFEOS_STATE.md` |
| Prioritized backlog | `docs/11_admin/BACKLOG.md` |
| Doc navigation | `docs/INDEX.md` |
| Model config | `config/models.yaml` |
| Role prompts | `config/agent_roles/` |
| Constitution (deep context) | `docs/00_foundations/LifeOS_Constitution_v2.0.md` |
