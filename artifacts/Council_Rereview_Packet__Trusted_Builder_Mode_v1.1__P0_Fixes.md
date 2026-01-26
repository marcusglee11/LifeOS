# Governance Rereview Packet: Trusted Builder Mode v1.1

**Context**: P0 Fixes for Council Conditions C1–C6
**Mode**: Trusted Builder Acceptance (CT-2)
**Date**: 2026-01-26

## 1. Summary of Changes (C1–C6)

| Condition | Requirement | Implementation Status | Proof Point |
|---|---|---|---|
| **C1** | Normalization | **DONE** | Canonical `lowercase_snake_case` enforced; `normalize_failure_class` helper. |
| **C2** | Patch Seam | **DONE** | Speculative Build → Revert → Diffstat → Evaluate → Conditional Apply. |
| **C3** | Protected Paths | **DONE** | Authoritative `runtime/governance/self_mod_protection.py` wired into evaluator. |
| **C4** | Ledger Plan | **DONE** | Structured `plan_bypass` block added to `AttemptRecord`. |
| **C5** | Packet Plan | **DONE** | `plan_bypass` metadata injected into Review Packets. |
| **C6** | Proposal Text | **DONE** | Redlines applied to align with fail-closed interfaces. |

## 2. Proposal Redlines (Summary)

The proposal text (`Council_Proposal_Trusted_Builder_v1.1.md`) has been updated to:

1. **Strictly Bounded Exemption**: Explicitly cite Article XVIII as the authority for the plan exemption, subservient to Article XIII protected surfaces.
2. **Canonical Normalization**: Mandate `lowercase_snake_case` serialization.
3. **Fail-Closed Patch Lifecycle**: Define the "Speculative Patch" workflow where changes are reverted if bypass is denied.

## 3. Key Code Diffs

### C1 & C3: Policy Normalization & Protected Wiring (`configurable_policy.py`)

```python
# C1: Canonical normalization
def normalize_failure_class(self, failure_class: Any) -> str:
    if isinstance(failure_class, FailureClass):
        return failure_class.value.lower()
    return str(failure_class).strip().lower()

# C3: Authoritative Protected Path Check
bypass_decision = policy.evaluate_plan_bypass(
    failure_class_key=prev_failure,
    proposed_patch=proposed_patch_stats,
    protected_path_registry=PROTECTED_PATHS, # Authoritative Source imported from self_mod_protection
    ledger=ledger
)
```

### C2: Speculative Patch Workflow (`autonomous_build_cycle.py`)

```python
# 1. Run Build (Generates changes in workspace)
b_res = build.run(speculative_context, ...)

# 2. Extract Patch & Diffstat (Speculative)
# ... (git diff HEAD > patch) ...

# 3. REVERT WORKSPACE (Fail-closed State)
run_git_command(["reset", "--hard", "HEAD"], cwd=context.repo_root)
run_git_command(["clean", "-fd"], cwd=context.repo_root)

# 4. Evaluate Bypass (Clean State)
bypass_decision = policy.evaluate_plan_bypass(...)

# 5. Conditional Apply
if bypass_decision["eligible"]:
    run_git_command(["apply", str(patch_path)], cwd=context.repo_root)
```

### C4: Structured Ledger Schema (`ledger.py`)

```python
@dataclass
class AttemptRecord:
    # ...
    # Trusted Builder (C4)
    plan_bypass_info: Optional[Dict[str, Any]] = None
```

## 4. Verification Logs

### Environment

```
$ pwd
c:\Users\cabra\Projects\LifeOS
$ git rev-parse --show-toplevel
C:/Users/cabra/Projects/LifeOS
$ git rev-parse HEAD
1d60e8b87b97a3dc9f050e997b887c779661c711
$ git log -3 --oneline
1d60e8b (HEAD -> build/fix-acceptance-tests) chore: quick wins - gate scripts, tests, and code quality improvements
7b76799 fix: acceptance tests for autonomous build loop (20/24 fixed)
3d79c5f (origin/build/fix-acceptance-tests) fix: acceptance tests for autonomous build loop
$ git status --porcelain=v1
 M scripts/opencode_gate_policy.py
 M scripts/validate_review_packet.py
?? artifacts/Council_Evidence_Flatfile__Trusted_Builder_Mode_v1.1.md
?? artifacts/gap_analyses/Gap_Analysis_CLAUDE_Alignment_v1.0.md
?? config/policy/gate_policy.yaml
?? docs/01_governance/Agent_Capability_Envelopes_v1.0.md
?? docs/01_governance/OptionC_OpenAI.md
?? docs/02_protocols/Agent_Architecture_Claude_vs_Antigravity_v1.0.md
?? docs/02_protocols/templates/review_packet_lightweight.md
?? docs/10_meta/Review_Packet_Complex_Module_Structure_v1.0.md
?? docs/10_meta/Review_Packet_OptionC_Timestamp_Update_v1.0.md
?? docs/10_meta/Review_Packet_Simple_Test_v1.0.md
?? docs/11_admin/Status_Report_Automated_Build_Loops.md
?? docs/99_archive/dogfood_v5.md
?? "docs/Council Proposal Trusted Builder Mode (Rewrite for Council Review).md"
?? docs/Council_Proposal_Trusted_Builder_v1.1.md
?? docs/plans/
?? generate_ccp_manifest.py
?? runtime/tests/test_trusted_builder_c1_c6.py
?? scripts/audit_dogfood_compliance.py
?? scripts/verify_dogfood_gpt5.py
?? tests/complex_test.py
```

### Test Results (C1–C6 Coverage)

```
$ pytest runtime/tests/test_trusted_builder_c1_c6.py -v
===================================================================== test session starts =====================================================================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\cabra\Projects\LifeOS
configfile: pyproject.toml
plugins: anyio-4.7.0, asyncio-1.3.0, cov-6.2.1, mockito-0.0.4
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 7 items                                                                                                                                              

runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c1_normalization_roundtrip PASSED                                        [ 14%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c2_diffstat_logic PASSED                                                 [ 28%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c2_fail_closed_if_no_patch PASSED                                        [ 42%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c3_protected_path_wiring PASSED                                          [ 57%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c3_registry_fail_closed PASSED                                           [ 71%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c4_ledger_schema_completeness PASSED                                     [ 85%]
runtime/tests/test_trusted_builder_c1_c6.py::TestTrustedBuilderCompliance::test_c5_packet_annotation_logic PASSED                                        [100%]

====================================================================== 7 passed in 1.48s ======================================================================
```

## 5. Deferred P1 Items (Non-Goals)

- **Semantic Impact Detection**: No heuristics added to detect "meaningful" changes in small diffs (reliance on diffstat/paths only).
- **Ledger Hash Chain**: Tamper-proofing of the new `plan_bypass` fields is not yet implemented (scheduled for P1/Phase 4).

## 6. DeepSeek Delta (P0 Blockers)

This section documents fixes for DeepSeek's P0 blockers (B1–B3).

### 6.1 Summary of DeepSeek Fixes

| Blocker | Requirement | Implementation Status | Proof Point |
|---|---|---|---|
| **P0.1** | Path Normalization & Evasion | **DONE** | Added traversal checks (`..`), absolute path checks, and case canonicalization before protected path comparison. |
| **P0.2** | Speculative Build Fail-Closed | **DONE** | Bounded timeout (5min) + try/finally workspace cleanup + synthetic denial record on failure. |
| **P0.3** | Budget Atomicity | **DONE** | `FileLock` around budget evaluation to prevent race conditions. |

### 6.2 Key Code Diffs (DeepSeek Fixes)

#### Path Normalization (`configurable_policy.py`)

```python
# P0.1: Path Normalization
for f in touched_files:
    # Reject absolute/traversal immediately
    if os.path.isabs(f) or ".." in f or f.startswith("/") or ":" in f:
            decision["decision_reason"] = f"Absolute or traversal path denied: {f}"
            return decision
    
    # Normalize: forward slashes, lowercase (for case-insensitive match safety)
    f_norm = f.replace("\\", "/").lower()
    
    # Additional Traversal check after replace
    if "/../" in f_norm or f_norm.startswith("../") or f_norm.endswith("/.."):
        decision["decision_reason"] = f"Traversal path denied: {f}"
        return decision
```

#### Speculative Build Timeout & Lock (`autonomous_build_cycle.py`)

```python
# P0.2: Timeout
SPECULATIVE_TIMEOUT = 300 # 5 minutes
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(build.run, ...)
        b_res = future.result(timeout=SPECULATIVE_TIMEOUT)
except concurrent.futures.TimeoutError:
    raise TimeoutError("Speculative build timed out")
# ...
# P0.3: Budget Atomicity
LOCK_PATH = context.repo_root / "artifacts" / "locks" / "plan_bypass.lock"
budget_lock = FileLock(str(LOCK_PATH), timeout=5.0)
with budget_lock.acquire_ctx() as locked:
    # Evaluate and decide
```

### 6.3 DeepSeek Verification Logs

```
$ pytest runtime/tests/test_deepseek_fixes.py -v
===================================================================== test session starts =====================================================================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\cabra\Projects\LifeOS
configfile: pyproject.toml
plugins: anyio-4.7.0, asyncio-1.3.0, cov-6.2.1, mockito-0.0.4
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 5 items

runtime/tests/test_deepseek_fixes.py::TestDeepSeekP0Blockers::test_ds_path_traversal_denied PASSED                                                       [ 20%]
runtime/tests/test_deepseek_fixes.py::TestDeepSeekP0Blockers::test_ds_absolute_path_denied PASSED                                                        [ 40%]
runtime/tests/test_deepseek_fixes.py::TestDeepSeekP0Blockers::test_ds_symlink_evasion_denied PASSED                                                      [ 60%]
runtime/tests/test_deepseek_fixes.py::TestDeepSeekP0Blockers::test_ds_case_canonicalization PASSED                                                       [ 80%]
runtime/tests/test_deepseek_fixes.py::TestDeepSeekP0Blockers::test_ds_budget_lock_mechanism PASSED                                                       [100%]

### 6.4 Git Validation
```

1d60e8b87b97a3dc9f050e997b887c779661c711 (HEAD)
M runtime/orchestration/loop/configurable_policy.py
M runtime/orchestration/missions/autonomous_build_cycle.py
?? runtime/util/file_lock.py
?? runtime/tests/test_deepseek_fixes.py

```
(Note: Only relevant files shown for brevity)

## 7. Final Stewarding Pointers
*   **Ruling**: [Council_Ruling_Trusted_Builder_Mode_v1.1.md](../../docs/01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md)
*   **Proposal**: [Council_Proposal_Trusted_Builder_v1.1.md](../Council_Proposal_Trusted_Builder_v1.1.md)
*   **Verbatim Transcript**: [Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md](../Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md)
