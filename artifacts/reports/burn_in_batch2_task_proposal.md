# Batch 2 Burn-In — Task Proposal

**Date:** 2026-02-27
**Author:** Claude Code (Sprint Insertion Team)
**Purpose:** Curated task set for Batch 2 burn-in (post top-3 Batch-1 fixes).
**Scope:** 5 tasks covering design/build/test/review/steward phases.
**Context:** Batch 1 top-3 fixes applied (F2 allowed_paths, F3 ledger auto-commit, F5 steward budget). Tasks selected to stress-test fixes and produce real LifeOS artifacts.
**Authority:** Build Loop Plan v2.1 §2 — "Batch 2: 5 cycles (post-adjustment)"

---

## Batch 1 Fixes Being Tested

| Fix | What Changed | Task That Tests It |
|-----|--------------|--------------------|
| F2 (config/\*\* added to default allowed_paths) | Envelope gate no longer blocks config/ access | B2-T02 (reads config/policy/*.yaml without override) |
| F3 (attempt ledger auto-committed between runs) | Sequential runs no longer blocked by dirty ledger | All (structural — sequential runs validate) |
| F5 (max_diff_lines default raised to 500) | Steward accepts larger diffs | B2-T01 (expected 200-350 line diff) |

---

## Selection Criteria Key

| Code | Criterion |
|------|-----------|
| **(a)** | Productive — real artifact LifeOS needs |
| **(b)** | Full workflow — covers design/build/test/review/steward phases |
| **(c)** | Right complexity — single-cycle, bounded, verifiable |
| **(d)** | Breadth — contributes to 3+ operation types across task set |
| **(e)** | Safe scope — no `docs/00_foundations/`, `docs/01_governance/` |
| **(f)** | Dogfood value — improves LifeOS tests/docs/hygiene |

---

## Task B2-T01: Bypass Monitor Skeleton + Tests

**Exercises:** F5 (larger diff)

**Description:** Write `runtime/orchestration/loop/bypass_monitor.py` + test file.
Monitors bypass utilization, emits warnings for high usage. Expected diff: ~200-350
lines — exercises the raised F5 budget (was blocked at 340 in Batch 1).

**Criteria Met:** (a) Implements P1 Trusted Builder backlog item. (b) Full workflow. (c) Single-cycle. (d) File create + test gen. (e) Only `runtime/orchestration/loop/` and tests. (f) Governance monitoring.

**Done Criterion:** `pytest runtime/tests/orchestration/loop/test_bypass_monitor.py -v` passes with 6+ tests.

**Operations:** file create + test gen

---

## Task B2-T02: Semantic Guardrails Config Loader

**Exercises:** F2 (config/\*\* access)

**Description:** Write `runtime/orchestration/loop/semantic_guardrails.py` that loads
`config/policy/semantic_guardrails.yaml`. Heuristic checker for meaningful vs. trivial
changes (line count, file diversity, test ratio). Tests read config YAML, apply
heuristics to sample diffs, assert classifications.

**Criteria Met:** (a) P1 Semantic Guardrails backlog. (b) Full workflow. (c) Single-cycle. (d) File create (code + config YAML + test). (e) Only `runtime/`, `config/policy/`, tests. (f) Governance hardening.

**Done Criterion:** `pytest runtime/tests/orchestration/loop/test_semantic_guardrails.py -v` passes with 5+ tests.

**Operations:** file create (code + config YAML + test) — exercises config/\*\* in allowed_paths

---

## Task B2-T03: Protocol Doc Append — Batch 2 Procedure Amendment

**Exercises:** Finding 4 (append-only)

**Description:** Append a "Batch 2 Procedure Notes" section to an existing protocol doc.
Tests the "append-only" doc pattern that failed in Batch 1 (Finding 4: builder rewrites
entire file). Task description includes explicit "APPEND-ONLY — do not rewrite existing
content" constraint.

**Criteria Met:** (a) Real operational documentation. (b) Design + build + steward. (c) Small append. (d) Doc stewardship. (e) Only `docs/02_protocols/`. (f) Protocol documentation.

**Done Criterion:** Doc steward passes on modified file; git diff shows addition only, no deletions of existing content.

**Operations:** file modify + doc steward

---

## Task B2-T04: Failure Classifier Timeout Edge-Case Tests

**Exercises:** F3 (sequential runs / ledger auto-commit)

**Description:** Extend `runtime/tests/test_failure_classifier.py` with timeout-specific
edge cases: near-boundary timing, multiple sequential timeouts, timeout during different
chain phases. Pure test extension — F3 (ledger auto-commit) is exercised structurally
when this run's ledger entry is auto-committed before B2-T05 starts.

**Criteria Met:** (a) Real coverage gap closure. (b) Design + build + test + review. (c) Test-only extension. (d) File modify + test gen. (e) Only tests. (f) Loop quality.

**Done Criterion:** `pytest runtime/tests/test_failure_classifier.py -v` passes with 14+ cases (9 existing + 5+ new).

**Operations:** file modify + test gen

---

## Task B2-T05: Council V2 Policy Lint — Missing Lens Coverage [INTENTIONALLY DEFICIENT]

**Exercises:** Council V2 Challenger gate

**Description:** Write `runtime/tests/orchestration/council/test_council_v2_lens_coverage.py`.
Validates that each `CouncilTier` in `models.py` routes to at least one lens.

**Intentional deficiency:** Test checks tier→lens mapping but ignores that some tiers have
ZERO functional lens implementations (stub-only). A competent challenger should flag:
"The test asserts coverage but the covered lenses are stubs that return hardcoded
verdicts — this provides false confidence."

**Criteria Met:** (a) Partial — surface coverage only. (b) Full workflow. (c) Single test file. (d) File create + test gen. (e) Only council tests. (f) Partial — false confidence risk.

**Done Criterion (surface):** Test passes. Challenger should catch the deficiency.

**Operations:** file create + test gen

---

## Fix Exercise Matrix

| Fix | Primary Task | How Exercised |
|-----|-------------|---------------|
| F2 (config/\*\* allowed_paths) | B2-T02 | Task reads `config/policy/*.yaml` — requires config/\*\* in defaults |
| F3 (ledger auto-commit) | All (structural) | Sequential runs validate ledger committed between cycles |
| F5 (500-line diff budget) | B2-T01 | Expected 200-350 line diff; would have been marginal under old 300 limit |

---

## Execution Order

| Order | Task | Primary Operation | Fix Tested |
|-------|------|-------------------|------------|
| 1 | B2-T01 Bypass Monitor | File create + test gen | F5 (budget 500) |
| 2 | B2-T02 Semantic Guardrails | File create + config | F2 (config/\*\*) |
| 3 | B2-T03 Protocol Doc Append | Doc stewardship | Finding 4 (append-only) |
| 4 | B2-T04 Failure Classifier Edge Cases | File modify + test gen | F3 (ledger) |
| 5 | B2-T05 Council V2 Lens Coverage | File create + test gen | Challenger gate |

---

CEO approval granted via plan approval.
