# Council Seat Outputs: Phase 9 Ops Ratification

## Risk / Adversarial Reviewer Seat

**Verdict:** Accept

**Key findings:**
- The certification runner properly checks if an approval reference exists and contains a valid decision marker `_DECISION_MARKER_RE.search(text)` (REF: `scripts/run_ops_certification.py`:#L134-138).
- Only paths under `docs/01_governance/` are considered valid for `approval_ref` validation, protecting against tricking the validator with non-governance documents (REF: `scripts/run_ops_certification.py`:#L128-130).
- The `current_worktree_clean()` check correctly blocks certification if there are uncommitted changes, including unauthorized edits to `lanes.yaml` (REF: `scripts/run_ops_certification.py`:#L75-83).
- The action validation ensures that allowed actions are recognized and require approval. However, the overlap check uses set intersection between `allowed_actions` and `excluded_actions` to block misconfigurations (REF: `scripts/run_ops_certification.py`:#L198-207).

**Risks / failure modes:**
- *Risk 1:* Bypassing the ratification gate is difficult via standard CI, but local runs could theoretically bypass it if the user manually changes `ops_readiness.json` status to `prod_local` or similar, as the artifact is not signed (ASSUMPTION: The artifact is trusted once generated locally).
- *Risk 2:* If the governance directory is corrupted or deleted, the `_validate_approval_ref` will fail because `ruling_path.is_file()` returns false, safely failing closed (REF: `scripts/run_ops_certification.py`:#L131).
- *Risk 3:* The excluded_actions list could be bypassed if a new action is introduced that provides equivalent capabilities but is not listed in `excluded_actions`.

**Fixes:**
- F1 (Low Impact): Consider cryptographic signing or hashing of `lanes.yaml` state in the `ops_readiness.json` artifact to prevent manual tampering post-certification (REF: `scripts/run_ops_certification.py`).

**Open questions:**
- How will the system respond if the `approval_ref` document is modified after ratification to remove the approval marker? The certification runs at a point in time, so it might use stale readiness if not re-run.

**Confidence:** High

**Assumptions:**
- Users do not manually alter `ops_readiness.json` after running `lifeos certify ops`.
- Git status output reliably detects changes to `lanes.yaml`.

**Complexity Budget:**
```yaml
complexity_budget:
  net_human_steps: "0"
  new_surfaces_introduced: 0
  surfaces_removed: 0
  mechanized: "yes"
  trade_statement: "none"
```

**Common-Sense Operator View:**
- "Would a pragmatic operator implement this?": Yes, the checks are straightforward and rely on existing files.
- "Does this create more work than it prevents?": No, it automates a critical compliance check.
- "Is there a simpler alternative?": No simpler alternative exists that still provides automated governance gating.

---

## Determinism Reviewer Seat

**Verdict:** Accept

**Key findings:**
- The certification process relies on static configuration (`lanes.yaml`), test suite outcomes (pytest junit XML), and git status. Given the same repository state, it is highly deterministic (REF: `scripts/run_ops_certification.py`).
- The `ops_readiness.json` artifact captures a summary of the environment, test outcomes, lane manifest at the time of run, and timestamps. It provides a decent audit trail, though it lacks a git commit hash (REF: `scripts/run_ops_certification.py`:#L318-328).
- The only non-deterministic elements are the execution time `elapsed_s` and the `timestamp` field containing `_now_iso()` (REF: `scripts/run_ops_certification.py`:#L42, #L244).
- A certification run can mostly be reproduced from the readiness artifact as it contains the embedded `lane_manifest` and test summaries, though without the exact git SHA, perfect reproduction of the repository state isn't guaranteed.

**Risks / failure modes:**
- *Risk 1:* Missing git commit hash in the `ops_readiness.json` artifact makes it harder to map a certification back to a precise codebase state.

**Fixes:**
- F1 (Medium Impact): Inject the current git commit SHA into the `ops_readiness.json` payload to improve reproducibility and auditability (REF: `scripts/run_ops_certification.py`:#L318-328).

**Open questions:**
- Should the `ops_readiness.json` include the git branch name as well?

**Confidence:** High

**Assumptions:**
- The git tree is clean at the time of certification, as enforced by the script.

**Complexity Budget:**
```yaml
complexity_budget:
  net_human_steps: "0"
  new_surfaces_introduced: 0
  surfaces_removed: 0
  mechanized: "partial"
  trade_statement: "none"
```

**Common-Sense Operator View:**
- "Would a pragmatic operator implement this?": Yes, the artifact structure is standard for CI/CD outputs.
- "Does this create more work than it prevents?": No, the artifact generation is fully automated.
- "Is there a simpler alternative?": Just relying on stdout, but that fails the auditability requirement.

---

## Governance Reviewer Seat

**Verdict:** Accept

**Key findings:**
- Phase 9 stays strictly within the granted authority. The spec explicitly states "No new executor actions are introduced in this phase" (REF: `artifacts/plans/2026-04-02-phase9-ops-autonomy-spec.md`:§Summary).
- The approval reference chain validation is strong. It checks that the reference points to a file within `docs/01_governance/` and contains a specific decision marker (`**Decision**: RATIFIED` or `APPROVED`) (REF: `scripts/run_ops_certification.py`:#L128-138).
- The spec explicitly defers Phase 10 without pre-authorizing it: "no Phase 10 expansion is pre-authorized" (REF: `artifacts/plans/2026-04-02-phase9-ops-autonomy-spec.md`:§Default Approval Outcome).
- Excluded operational classes are bounded clearly in the text of the Review Packet and Spec, even if not fully implemented in code (REF: `artifacts/review_packets/Phase9_Ops_Autonomy_Review_Packet.md`:§Reserved Excluded Classes).
- There is no apparent governance drift; the protocol aligns with the human-in-the-loop requirements of the Constitution (`explicit_human_approval` is enforced) (REF: `scripts/run_ops_certification.py`:#L189-195).

**Risks / failure modes:**
- *Risk 1:* If a new action is added to the system but not explicitly excluded in `lanes.yaml`, it might inadvertently become available if someone adds it to `allowed_actions` and local ratification passes.

**Fixes:**
- F1 (Low Impact): Ensure any new actions added to the registry default to requiring explicit approval.

**Open questions:**
- None.

**Confidence:** High

**Assumptions:**
- `docs/01_governance/` is protected by other mechanisms from unauthorized edits.

**Complexity Budget:**
```yaml
complexity_budget:
  net_human_steps: "0"
  new_surfaces_introduced: 0
  surfaces_removed: 0
  mechanized: "yes"
  trade_statement: "none"
```

**Common-Sense Operator View:**
- "Would a pragmatic operator implement this?": Yes, it closely follows the established governance framework without adding bloat.
- "Does this create more work than it prevents?": No, the bounds are clear and automated.
- "Is there a simpler alternative?": No simpler alternative exists that respects the strict governance requirements.
