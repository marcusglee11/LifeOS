# Council Review Packet: council-merge-observability

**Branch:** `build/council-merge-observability`
**Base:** `main`
**Commit:** `bdd3c29`
**Date:** 2026-02-09
**Author:** Claude Code (Antigravity-directed)

---

## 1. Diff Summary

```
29 files changed, 6203 insertions(+), 1486 deletions(-)
```

### By Module (additions/deletions)

| Module | Files | +Lines | -Lines | Net |
|--------|-------|--------|--------|-----|
| `runtime/orchestration/council/` | 5 | 1,211 | 0 | +1,211 |
| `runtime/orchestration/missions/` | 4 | 969 | 283 | +686 |
| `runtime/tests/` | 7 | 2,759 | 1,122 | +1,637 |
| `runtime/agents/` | 2 | 314 | 59 | +255 |
| `config/agent_roles/` | 8 | 648 | 0 | +648 |
| `scripts/` | 1 | 171 | 0 | +171 |
| `artifacts/` | 1 | 98 | 0 | +98 |
| `runtime/orchestration/missions/__init__.py` | 1 | 94 | 91 | +3 |

---

## 2. Changed File Inventory

### New Files (22)

**Council Infrastructure (5 files, 1,211 lines)**
- `runtime/orchestration/council/__init__.py` — Package init
- `runtime/orchestration/council/ccp_generator.py` — Council Context Pack generator (290 lines)
- `runtime/orchestration/council/seat_executor.py` — 9-seat review execution framework (249 lines)
- `runtime/orchestration/council/chair.py` — Chair synthesis engine (424 lines)
- `runtime/orchestration/council/cochair.py` — Co-Chair validation (243 lines)

**Reviewer Seat Prompts (8 files, ~648 lines)**
- `config/agent_roles/reviewer_alignment.md`
- `config/agent_roles/reviewer_determinism.md`
- `config/agent_roles/reviewer_governance.md`
- `config/agent_roles/reviewer_risk_adversarial.md`
- `config/agent_roles/reviewer_simplicity.md`
- `config/agent_roles/reviewer_structural_operational.md`
- `config/agent_roles/reviewer_technical.md`
- `config/agent_roles/reviewer_testing.md`

**Test Files (6 files, ~1,638 lines)**
- `runtime/tests/test_ccp_generator.py` — CCP generation tests (278 lines)
- `runtime/tests/test_seat_executor.py` — Seat executor tests (290 lines)
- `runtime/tests/test_chair_synthesis.py` — Chair synthesis tests (281 lines)
- `runtime/tests/test_cochair_validator.py` — Co-Chair validator tests (231 lines)
- `runtime/tests/test_merge_mission.py` — Merge mission tests (262 lines)
- `runtime/tests/test_full_council_review.py` — Full council integration tests (296 lines)

**Other New Files (3)**
- `runtime/orchestration/missions/merge.py` — Autonomous merge mission (479 lines)
- `runtime/agents/timeout_profiler.py` — Timeout diagnostics (176 lines)
- `scripts/rollback_merge.py` — Emergency merge rollback (171 lines)
- `artifacts/council_runs/council_run_log_schema.yaml` — Audit log schema (98 lines)

### Modified Files (7)

- `runtime/orchestration/missions/base.py` — Added MERGE to MissionType enum, mission registry updates (+192/-191)
- `runtime/orchestration/missions/review.py` — Enhanced with full council orchestration (+176/-59)
- `runtime/orchestration/missions/autonomous_build_cycle.py` — Integrated merge step (+60/-1)
- `runtime/orchestration/missions/__init__.py` — Updated exports (+94/-91)
- `runtime/agents/opencode_client.py` — Streaming output capture (+138/-22)
- `runtime/tests/test_missions_phase3.py` — Major test refactoring (+1,122/-1,122)

---

## 3. Architecture Decisions

### Decision 1: Council as Separate Package
**Choice:** Created `runtime/orchestration/council/` as a distinct package rather than extending `missions/review.py`.
**Rationale:** Council Protocol v1.3 has 4 distinct components (CCP, Seats, Chair, Co-Chair) that merit separation. Avoids a 1000+ line review.py.
**Trade-off:** Introduces a new package; increases import surface area.

### Decision 2: Deterministic Mode Selection
**Choice:** CCP generator uses deterministic rules (not LLM) for M0/M1/M2 mode selection based on file paths and change classification.
**Rationale:** Mode selection must be reproducible and auditable. LLM-based mode selection would be non-deterministic.
**Trade-off:** Rules may need manual updates as governance surfaces evolve.

### Decision 3: MergeMission Fail-Closed Design
**Choice:** MergeMission checks PR status, CI, governance guards, and repo state before any merge. Never force-pushes. Emits receipts.
**Rationale:** Git Workflow Protocol v1.1 Stage 4 mandates safety guarantees.
**Trade-off:** More pre-merge checks = slower merges, but safety is non-negotiable.

### Decision 4: Streaming Output via Popen
**Choice:** Replaced `subprocess.run(capture_output=True)` with `subprocess.Popen` for OpenCode CLI calls, enabling line-by-line output capture.
**Rationale:** Diagnose timeout root causes — need to distinguish "model queued" from "model producing output" from "network timeout".
**Trade-off:** More complex process management; Unix-specific (WSL compatible).

### Decision 5: All Tests Are Unit/Mock-Based
**Choice:** All 111 new tests use mocking — no live LLM calls, no live git operations.
**Rationale:** Tests must be fast, deterministic, and runnable in CI without credentials.
**Trade-off:** No actual integration validation. The infrastructure has never been exercised against real models.

---

## 4. Known Risks and Weaknesses

### R1: Zero Dogfooding (CRITICAL)
The build plan was titled "Dogfooded Autonomous Merges & Council Protocol v1.3 Reviews" but **no council review was actually executed** against any change. The infrastructure exists but has never produced a real Council Context Pack or executed a real seat review.

### R2: No CCP Generation Exercised
`ccp_generator.py` was built and tested with mocks, but no actual CCP document has been produced for any merge in the project's history.

### R3: Chair/Co-Chair Never Synthesized Real Data
The Chair synthesis engine and Co-Chair validator have comprehensive mock-based tests but have never processed real seat outputs from real LLM calls.

### R4: MergeMission Untested Against Real GitHub
MergeMission was tested with subprocess mocks. It has never executed `gh pr view`, `git merge`, or `git push` against the actual repository.

### R5: Reviewer Prompts Untested
8 new reviewer seat prompt files exist in `config/agent_roles/` but have never been sent to an LLM. Prompt quality is unvalidated.

### R6: test_missions_phase3.py Churn
The largest change (+1,122/-1,122 lines) is a full rewrite of `test_missions_phase3.py`. This is a high-risk refactor of an existing test file.

### R7: Pre-existing Test Failures
11 tests are failing in the baseline (4 in the diff output). These are pre-existing and not caused by this branch, but they cloud signal quality.

---

## 5. Council Seat Assessments

### Architect Seat
**Verdict:** PASS_WITH_NOTES
- Clean separation of concerns across council package
- Appropriate use of BaseMission pattern for MergeMission
- Concern: 29 files in a single commit is large blast radius

### Alignment Seat
**Verdict:** PASS_WITH_NOTES
- Implements Council Protocol v1.3 structure as specified
- Concern: Commit message claims "dogfooded" but no dogfooding occurred — misalignment between claim and reality

### Structural/Operational Seat
**Verdict:** PASS_WITH_NOTES
- File organization follows existing conventions
- Config files in `config/agent_roles/`, tests co-located in `runtime/tests/`
- Concern: No `__init__.py` exports for council submodules

### Technical Seat
**Verdict:** PASS_WITH_NOTES
- Streaming Popen implementation is correct for WSL
- Timeout profiler captures useful diagnostics
- Concern: Error handling in merge.py relies on subprocess return codes without stderr parsing

### Testing Seat
**Verdict:** CONDITIONAL_PASS
- 111 new tests, all passing
- Good coverage of happy paths and error cases
- **Condition:** All tests are mock-based. Zero integration testing against real infrastructure. The "full council review" test mocks every LLM call.

### Risk/Adversarial Seat
**Verdict:** CONDITIONAL_PASS
- MergeMission is fail-closed (good)
- Rollback script exists (good)
- **Risk:** No real-world exercise means unknown failure modes in production
- **Risk:** Reviewer prompts could produce unexpected output formats that break seat_executor parsing

### Simplicity Seat
**Verdict:** PASS_WITH_NOTES
- Design is appropriately modular
- Concern: 6,203 lines added in one commit is not "simplest thing that works"
- Council infrastructure may be over-engineered given it has never been used

### Determinism Seat
**Verdict:** PASS
- Mode selection is deterministic (rule-based, not LLM)
- Council run log schema supports reproducibility
- Test outcomes are deterministic (all mock-based)

### Governance Seat
**Verdict:** CONDITIONAL_PASS
- No protected paths modified (docs/00, docs/01 untouched)
- Self-mod protector integration in MergeMission
- **Condition:** The commit message "dogfooded autonomous merges" is governance-misleading. No autonomous merge was dogfooded. This should be corrected before merge to main.

---

## 6. Recommendation

**Overall Verdict:** CONDITIONAL_PASS

**Conditions for merge to main:**
1. Execute at least one real council review cycle using this infrastructure
2. Produce at least one actual CCP document
3. Correct the commit message to accurately reflect what was done
4. Validate reviewer prompts produce parseable output with at least one LLM

**Without these conditions met, the infrastructure is speculative — well-structured, well-tested against mocks, but unproven.**
