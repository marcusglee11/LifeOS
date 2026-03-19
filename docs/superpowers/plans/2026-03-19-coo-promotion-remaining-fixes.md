# COO Promotion Remaining Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all remaining issues from the COO Unsandboxed Prod L3 Council Review session so the promotion can proceed to a re-run → gate-3 seal → soak → handoff.

**Architecture:** Three independent tasks that each produce a standalone commit: (1) fix a pre-existing broken test mock, (2) draft the council ruling from session evidence so gate-3 can accept it, (3) re-run the council review to confirm Accept after the hardening batch.

**Tech Stack:** Python 3.14, pytest, bash, YAML config

---

## File Structure

| File | Responsibility |
|------|---------------|
| `runtime/tests/test_git_workflow_worktree.py:249` | **Modify** — fix `fake_merge_to_main` mock signature |
| `docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md` | **Create** — ratified ruling (CEO approval required before commit) |
| `scripts/workflow/run_council_review_coo_unsandboxed_promotion.py` | **Read-only** — re-run the council review |
| `config/openclaw/profile_approvals/coo_unsandboxed_prod_l3.yaml` | **Read-only** — verify gate-3 dry-run can accept the ruling |

---

### Task 1: Fix pre-existing broken test mock

**Context:** `test_closure_pack_regen_after_merge` has been failing across every test run this session. The real `merge_to_main` function (at `runtime/tools/workflow_pack.py:555`) added an `allow_concurrent_wip` kwarg. The test mock at line 249 doesn't accept it, so `closure_pack.py:311` throws a `TypeError` every time.

**Files:**
- Modify: `runtime/tests/test_git_workflow_worktree.py:249`

- [ ] **Step 1: Read the mock and confirm the fix**

The current mock:
```python
def fake_merge_to_main(repo_root_arg: Path, branch: str) -> dict:
```

The real signature:
```python
def merge_to_main(repo_root: Path, branch: str, allow_concurrent_wip: bool = False) -> dict:
```

- [ ] **Step 2: Fix the mock signature**

```python
def fake_merge_to_main(repo_root_arg: Path, branch: str, **kwargs) -> dict:
```

Using `**kwargs` instead of the explicit kwarg so this mock won't break again if more kwargs are added downstream.

- [ ] **Step 3: Run the failing test to verify it passes**

Run: `pytest runtime/tests/test_git_workflow_worktree.py::test_closure_pack_regen_after_merge -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add runtime/tests/test_git_workflow_worktree.py
git commit -m "fix: update fake_merge_to_main mock to accept kwargs

The real merge_to_main added allow_concurrent_wip kwarg; the test mock
had a fixed signature that rejected it, causing a TypeError on every run."
```

---

### Task 2: Draft council ruling for CEO ratification

**Context:** Gate-3 (`gate3_prepare.py`) now hard-fails if the ruling file doesn't exist under `docs/01_governance/` or doesn't contain `RATIFIED`/`APPROVED`. The draft ruling from the council run needs to be upgraded to a proper ruling document. However, `docs/01_governance/` is a **protected path** — the ruling must be reviewed and approved by the CEO before it is committed.

**Existing template:** `docs/01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md` shows the canonical format:
- `**Decision**: RATIFIED` header field (required for gate-3 validation)
- `**Status**: ACTIVE` header field
- Verdict breakdown table with per-lens verdicts
- Closure statement addressing each finding
- Deferred items / conditions
- Evidence references

**Source evidence:**
- Council run: `artifacts/council_reviews/20260319T021805Z/`
- Live result: `artifacts/council_reviews/20260319T021805Z/live_result.json`
- Draft ruling: `artifacts/council_reviews/20260319T021805Z/draft_ruling_COO_Unsandboxed_Prod_L3_v1.0.md`
- Hardening commit: `cec9cb63` (all Revise findings fixed)
- Classify fix: `48b43b30` (public API cleanup)

**Files:**
- Create: `docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md`

- [ ] **Step 1: Write the ruling document**

```markdown
# Council Ruling: COO Unsandboxed Prod L3

**Decision**: RATIFIED
**Date**: 2026-03-19
**Scope**: COO Unsandboxed Production Profile Promotion (L3)
**Status**: ACTIVE

## 1. Verdict Breakdown

| Lens | Provider | Initial Verdict | Post-Fix Status |
|------|----------|----------------|-----------------|
| **Risk** | gemini | Accept (high) | No changes required |
| **Implementation** | gemini | Accept (high) | No changes required |
| **Architecture** | claude_code | Revise (medium) | All findings resolved (cec9cb63) |
| **Governance** | codex | Revise (high) | All findings resolved (cec9cb63, 48b43b30) |

**Final Ruling**: The Council APPROVES COO Unsandboxed Prod L3 promotion, subject to the following conditions being satisfied prior to activation:

1. All Revise findings from run `20260319T021805Z` have been resolved (verified in commits cec9cb63, 48b43b30)
2. Re-run of council review produces Accept verdict (Task 3 below)
3. Gate-5 soak window completed (16 clean runs, 4 sessions, 2 calendar days)
4. CEO completes gate-6 UAT handoff

## 2. Closure Statement

### Governance Findings (Resolved)
- **Gate-3 ruling verification**: `gate3_prepare.py` now validates ruling file exists under `docs/01_governance/` and contains RATIFIED/APPROVED marker before sealing (fail-closed).
- **Promotion guard hardening**: `promotion_guard.py` now validates ruling_ref file existence, path normalization, and delegation_envelope_sha256 integrity.
- **Shell injection (CWE-78)**: `openclaw_verify_surface.sh` replaced `python3 -c` interpolation with heredoc+argv; PROFILE_NAME validated against safe character set.
- **Path traversal (CWE-22)**: `LIFEOS_COO_CAPTURE_LABEL` sanitized to `[A-Za-z0-9._-]+`; output path boundary-checked.

### Architecture Findings (Resolved)
- **Soak runner fallthrough**: `apply_reset()` raises `ValueError` on unrecognized reason values.
- **Gate-3 idempotency**: Raises `RuntimeError` if manifest already sealed.
- **Gate-6 hardcoded ruling ref**: Reads from sealed manifest instead of literal path.
- **Missing capture dump**: `_maybe_capture_dump` now called in `--execute` auto-dispatch branch.
- **Private symbol coupling**: `classify_coo_response()` exposed as public API; controller updated.

### Least-Privilege Acknowledgment
The candidate profile (`coo_unsandboxed_prod_l3.json`) deliberately sets `unsandboxed: true`, session sandbox not required, and elevated disable not required. This is an accepted design trade-off to enable production COO autonomy at L3. Blast radius is bounded by:
- Delegation envelope ceiling: `[L0, L3, L4]`
- Approval manifest hash-binding (profile + envelope + ruling)
- Deterministic rollback to `coo_shared_ingress_burnin.json`
- `verify_surface.sh` runtime enforcement on every invocation

## 3. Conditions

| ID | Condition | Status |
|----|-----------|--------|
| C1 | Revise findings resolved | RESOLVED (cec9cb63, 48b43b30) |
| C2 | Council re-run Accept | PENDING (Task 3) |
| C3 | Gate-5 soak complete | PENDING |
| C4 | Gate-6 CEO UAT | PENDING |

## 4. Evidence References

- **Council Run**: `artifacts/council_reviews/20260319T021805Z/`
- **Live Result**: `artifacts/council_reviews/20260319T021805Z/live_result.json`
- **Review Packet**: `artifacts/review_packets/Review_Packet_COO_Unsandboxed_Prod_L3_Council_Dogfood_v1.0.md`
- **Hardening Commit**: `cec9cb63` (10 findings fixed, 5 regression tests added)
- **API Cleanup Commit**: `48b43b30` (classify_coo_response public API)
```

- [ ] **Step 2: CEO review gate — STOP AND ASK**

**CRITICAL:** `docs/01_governance/` is a protected path. Before committing this file:
1. Present the ruling text to the CEO (user)
2. Ask: "Do you approve this ruling for ratification?"
3. Only proceed to commit after explicit `RATIFIED` or `APPROVED` response

If the CEO requests changes, edit the ruling and re-present.

- [ ] **Step 3: Commit the ratified ruling**

```bash
git add docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md
git commit -m "governance: ratify Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0

Council V2 review (run 20260319T021805Z) initially returned Revise.
All findings resolved in cec9cb63 and 48b43b30.
Ruling ratified with conditions: re-run Accept, soak, CEO UAT."
```

- [ ] **Step 4: Verify gate-3 dry-run accepts the ruling**

```bash
python3 scripts/campaign/gate3_prepare.py \
  --repo-root . \
  --ruling-ref docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md \
  --dry-run
```

Expected: exits 0, prints the manifest dict with hashes filled in and ruling_ref pointing to the committed file. **Note:** `--dry-run` only validates — it does NOT write the sealed manifest. Actual sealing happens downstream (not in this plan's scope).

If it fails: the `_validate_ruling_ref` check in `gate3_prepare.py` will say exactly why (file missing, wrong directory, no RATIFIED marker). Fix accordingly.

---

### Task 3: Re-run council review for Accept verdict

**Context:** The hardening batch (cec9cb63) and API cleanup (48b43b30) resolved all 10 Revise findings. A re-run should produce Accept from all lenses. This task cannot run until Task 2 is complete (the ruling file must exist for the full promotion guard to pass, though the council review itself doesn't check for it — it checks the CCP and runs the lenses).

**Important timing note:** This task takes 10-20 minutes due to real CLI provider invocations (codex, gemini, claude_code). Plan accordingly.

**Important:** This task must run from the primary repo (`/mnt/c/Users/cabra/Projects/LifeOS`), not a worktree, because the runner writes artifacts to the repo root and reads the CCP from `artifacts/council_reviews/`.

**Files:**
- Read-only: `scripts/workflow/run_council_review_coo_unsandboxed_promotion.py`
- Output: `artifacts/council_reviews/<timestamp>/` (new run directory)

- [ ] **Step 1: Dry-run to confirm CCP still compiles cleanly**

```bash
python3 scripts/workflow/run_council_review_coo_unsandboxed_promotion.py --dry-run
```

Expected: T3 tier, Risk + Governance in required_lenses, no preflight issues, exit 0.

- [ ] **Step 2: Run the live council review**

```bash
python3 scripts/workflow/run_council_review_coo_unsandboxed_promotion.py
```

This will:
1. Run mock gate (pytest subprocess) — should pass
2. Run live gate (dispatch lenses to CLI providers) — wait for completion
3. Generate draft ruling, summary.json, live_result.json in `artifacts/council_reviews/<timestamp>/`
4. If Accept: queue escalation to CEO as PENDING

- [ ] **Step 3: Verify the results**

```bash
# Find the latest run
LATEST=$(ls -t artifacts/council_reviews/ | grep '^2026' | head -1)

# Check verdict
python3 -c "
import json
d = json.load(open('artifacts/council_reviews/$LATEST/live_result.json'))
dp = d['decision_payload']
print('status:', dp['status'])
print('verdict:', dp['verdict'])
print('decision_status:', dp['decision_status'])
# Per-lens
for lens, res in d['run_log']['lens_results'].items():
    print(f'  {lens}: {res.get(\"verdict_recommendation\")} ({res.get(\"confidence\")})')
"
```

**Expected outcome:**
| Field | Value |
|-------|-------|
| `summary.json → terminal_outcome` | `"PASS"` |
| `summary.json → queue_status` | `"PENDING"` |
| `live_result.json → decision_payload.verdict` | `"Accept"` |
| `live_result.json → decision_payload.decision_status` | `"NORMAL"` |

**If verdict is still Revise:**
- Read the new `live_result.json` to see which lens(es) still block
- Check if new findings emerged that weren't in the hardening batch
- Fix any new findings and re-run (this is iterative by design)
- Note: LLM council verdicts are non-deterministic. The same codebase can get Accept on one run and Revise on another. If findings are spurious (already addressed), a second re-run may produce Accept.

**If verdict is Accept:**
- `summary.json` will show `queue_status: PENDING`
- An escalation entry is queued in `artifacts/queue/escalations.db`
- The draft ruling in the run directory reflects Accept
- Proceed to gate-3 seal (next downstream step, not in this plan)

- [ ] **Step 4: Commit any new artifacts**

```bash
git add artifacts/council_reviews/<timestamp>/ artifacts/review_packets/
git commit -m "evidence: council re-run <timestamp> — <verdict>"
```

---

## Downstream (Not In This Plan)

After all three tasks above are complete and the council returns Accept:

1. **Gate-3 seal** — `python3 scripts/campaign/gate3_prepare.py --ruling-ref docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md` — seals the approval manifest with profile hash, envelope hash, and ruling ref.

2. **Gate-4 host probes** — `python3 scripts/campaign/gate4_runner.py` — validates runtime surface.

3. **Gate-5 soak** — 16 clean runs across 4 sessions over 2 calendar days. Uses `coo_promotion_controller.py` to run scenario manifests and `gate5_soak_runner.py` to track clean/reset counts. Validated by `gate5_soak_validator.py`.

4. **Gate-6 handoff** — `python3 scripts/campaign/gate6_handoff.py --repo-root .` — assembles the UAT pack for CEO review (profile hashes, ruling ref from manifest, UAT prompts, rollback procedure, cutover checklist).

5. **CEO UAT** — CEO executes the 5 UAT prompts from the handoff pack, verifies behavior, approves cutover.

6. **Activation** — Copy approved profile over `coo.json`, verify surface, confirm `models status` reflects new autonomy level.

---

## Risk Notes

- **Council non-determinism:** LLM-based council verdicts can vary between runs on unchanged code. If Task 3 returns Revise on findings already addressed, evaluate whether the findings are genuinely new or re-raised. A second run is acceptable; more than two suggests a real gap.

- **Protected path governance:** The ruling in Task 2 touches `docs/01_governance/`. CEO approval is a hard gate. Do not automate or skip this step.

- **Provider availability:** Task 3 depends on all three CLI providers (codex, gemini, claude_code) being healthy. If a provider times out, the run may block. The gemini provider specifically needed no `-m` flag in testing (default model worked; `gemini-2.5-flash` caused a timeout).
