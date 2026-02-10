````markdown
# Council Proposal: Trusted Builder Mode (Rewrite for Council Review)

---
artifact_id: "council-proposal-trusted-builder-v1.1"
artifact_type: "COUNCIL_PROPOSAL"
schema_version: "1.0.0"
created_at: "2026-01-25T00:00:00Z"
author: "ChatGPT (rewrite from v1.0 inputs)"
version: "1.1"
status: "RATIFIED"
tags: ["governance", "autonomous-loop", "plan-gate", "trusted-builder", "article-xviii"]
council_trigger: "CT-2"
supersedes: "council-proposal-trusted-builder-v1.0"
ratified_commit: "54c9f25"
ratified_branch: "trusted-builder-mode-v1.1"
ruling_path: "docs/01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md"
evidence_path: "artifacts/Council_Rereview_Packet__Trusted_Builder_Mode_v1.1__P0_Fixes.md"
ratified_at_local: "2026-01-26 Australia/Sydney"
---

## 0) Decision Request (Council)

**Ruling:** RATIFIED (2026-01-26)
See [Council Ruling](../../docs/01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md).

---

## 1) Executive Summary

This proposal introduces **Trusted Builder Mode**: a narrowly-bounded mechanism that allows the Autonomous Build Loop to perform **certain retry attempts** without **Plan Artefact approval**, while **not waiving Review Packet requirements** and while **preserving fail-closed governance boundaries**.

Core principle: **Plan bypass is only permitted after a concrete proposed patch exists and has been validated as low-risk and bounded** (scope + paths + budget). If the system cannot validate the patch, it must fail closed and require the standard Plan gate.

**Key Updates in v1.1 (P0 Fixes):**
- **Canonical Normalization**: All failure classes normalized to lowercase snake_case (C1).
- **Patch Seam**: Eligibility computed solely from concrete patch diffstat (C2).
- **Protected Paths**: Authoritative `runtime/governance/self_mod_protection.py` is the single source of truth (C3).
- **Audit Schema**: Structured `plan_bypass` block in ledger and review packets (C4/C5).
- **Constitutional Clarity**: Explicitly positioned as a constrained exemption under Art. XVIII, strictly bounded by Art. XIII protected surfaces.

---

## 2) Problem Statement

The current loop can persist state and make deterministic decisions, but repeated retry iterations are operationally constrained by the Plan Artefact gate. For certain low-risk failure classes (e.g., lint, formatting, typos), requiring human Plan approval on every retry adds latency and friction without materially increasing safety—provided that:

- the proposed change is small and mechanically bounded,
- governance-controlled paths are not touched,
- retry budgets prevent “amok loops,” and
- Review Packets remain mandatory for evidence.

---

## 3) Definitions (Normative)

- **Attempt:** One recorded loop iteration producing an entry in the attempt ledger.
- **Retry Attempt:** An attempt whose loop policy output is `RETRY`.
- **Plan Artefact:** The governance-required approval artefact for a proposed code change (per constitution).
- **Plan Bypass:** Skipping the Plan Artefact approval step for a retry attempt **only** when eligibility rules are satisfied.
- **Proposed Patch:** A concrete, reviewable change set produced for a retry attempt (patch file or equivalent), with computed scope metrics and touched-path list. A patch is not “proposed” unless these metrics are computed deterministically from the patch itself.

---

## 4) Non-Goals

1. This proposal does **not** waive Review Packet requirements.
2. This proposal does **not** enable first-run builds to skip Plan approval (applies to **retries** only).
3. This proposal does **not** create a wildcard “anything goes” bypass (explicit allowlist + explicit exclusions).
4. This proposal does **not** change protected/governance path definitions; it requires using the authoritative source.

---

## 5) Proposed Amendment (Constitution / GEMINI.md)

**Amend Article XVIII (Lightweight Stewardship Mode)** by adding a new section:

### Section 5 — Loop Retry Plan Bypass (Trusted Builder Mode)

A retry attempt MAY proceed without Plan Artefact approval **only** if ALL are true:

**(A) Explicit allowlist:** The failure class is in `TRUSTED_RETRY_CLASSES`.

**(B) Concrete Proposed Patch:** One of the following is true:
- **B1 (Patchful retry):** A Proposed Patch exists for the retry, and eligibility checks are computed from that patch; or
- **B2 (No-change retry):** The retry is explicitly defined as a **no-change rerun** (allowed only for `TEST_FLAKE_NO_CHANGE`, see Section 6.3).

**(C) Scope is bounded:** Patch scope is within configured limits:
- `max_files <= 3`
- `max_total_line_delta <= 50`  
  where `total_line_delta = sum(added_lines + deleted_lines)` across files (diff numstat).

**(D) Governance boundary preserved:** The proposed change does **not** touch any governance-controlled/protected paths (per the authoritative protected path registry referenced by the constitution).

**(E) Budgeted:** The attempt is within:
- per-class bypass retry budget; AND
- global per-run plan-bypass budget.

**(F) Evidence not waived:** Review Packet remains REQUIRED for the attempt (no change to evidence standards).

#### §5.1 Fail-Closed Requirements
If the system cannot:
- compute scope deterministically from the Proposed Patch,
- determine whether protected paths are touched using the authoritative registry, or
- determine budgets from the ledger,
then Plan Bypass MUST be denied and the standard Plan gate MUST apply.

#### §5.2 Audit Requirements
When Plan Bypass eligibility is evaluated, the attempt record MUST contain:
- eligibility result (eligible/denied) and reason,
- rule identifier used (if any),
- scope metrics (files count, total line delta),
- protected-path hit list (empty if none),
- budgets remaining/consumed,
- and whether bypass was applied.

When bypass is applied, the Review Packet summary MUST explicitly note:
- “Plan Bypass Applied: Yes”
- and include the above fields in a structured form.

---

## 6) Policy & Implementation Specification (Execution-Grade)

### 6.1 TRUSTED_RETRY_CLASSES (Allowlist)

Trusted Builder Mode is limited to the following failure classes:

| Failure Class | Mode | Notes |
|---|---|---|
| `lint_error` | patchful | Mechanical fixes only; must satisfy scope + path checks |
| `formatting_error` | patchful | Mechanical fixes only; must satisfy scope + path checks |
| `typo` | patchful | Small text corrections; must satisfy scope + path checks |
| `test_flake_no_change` | no-change rerun | **Must not modify files**; rerun-only |

**Explicit Exclusions (always Plan-gated):**
- `syntax_error`
- `validation_error`
- `test_failure` (distinct from flake)
- `review_rejection`
- `unknown`
- any class not in allowlist

### 6.2 Deterministic Scope Metric

For patchful retries, the scope metric MUST be computed from the Proposed Patch diffstat:

- `files_touched = count(unique_paths_in_patch)`
- `added_lines, deleted_lines = sum(diff_numstat)`
- `total_line_delta = added_lines + deleted_lines`

**Eligibility check uses `total_line_delta` (not net lines, not feedback length, not prior attempt metadata).**

### 6.3 TEST_FLAKE Handling (Tightened)

The only bypass-eligible test flake mode is **no-change rerun**:

- Failure class must be `test_flake_no_change`.
- The retry MUST have `files_touched = 0` and `total_line_delta = 0`.
- If any code/test modification is proposed, the failure MUST be treated as `test_failure` (Plan required), unless separately approved by Council in a future amendment.

This prevents “flake” from becoming a label that permits substantive edits without Plan approval.

### 6.4 Protected / Governance-Controlled Paths (Authoritative)

Implementation MUST NOT hardcode protected path lists in the loop mission.

Instead, the bypass eligibility check MUST consult an authoritative protected-path registry that is already governed by the constitution (e.g., “Article XIII §4 protected paths” source of truth).

Fail-closed rule:
- If the registry cannot be loaded/read, Plan Bypass MUST be disabled (denied).

### 6.5 Normalization and Matching Rules

To avoid silent mismatch between YAML rules, taxonomy, and runtime strings:

- Canonical representation of failure class keys in config and ledger MUST be **lowercase snake_case**.
- Internal enums MAY exist, but serialization boundaries MUST be the canonical string.
- Rule matching MUST be tested for case/format normalization (strictly enforced).

### 6.6 Budgets (Two-Tier)

Budgets are required to prevent “death by a thousand bypasses.”

1) **Per-class bypass budget** (configured per rule; default 3 unless specified)
2) **Per-run global bypass budget** (single cap; recommended default 5)

When budgets are exhausted:
- bypass MUST be denied,
- standard Plan gate MUST apply (or escalation per existing governance policy, if that is the current behavior).

### 6.7 Ledger and Packet Wiring (Audit Completeness)

The attempt ledger record MUST include structured fields (names illustrative; exact schema may align to existing ledger schema):

```yaml
plan_bypass:
  evaluated: true
  eligible: true|false
  applied: true|false
  rule_id: "loop.lint-error" | null
  decision_reason: "..."           # deterministic string
  scope:
    files_touched: 2
    total_line_delta: 17
    added_lines: 10
    deleted_lines: 7
    files: ["path/a.py", "path/b.py"]
  protected_paths_hit: []          # list of matching patterns/paths
  budget:
    per_class_remaining: 2
    global_remaining: 4
  mode: "patchful" | "no_change_rerun"
proposed_patch:
  present: true|false
  patch_path: "..." | null         # if present
  diffstat_source: "git_numstat"   # or equivalent deterministic method
````

Terminal packet MUST include a bypass summary:

* total bypass evaluations, approvals, denials,
* bypasses applied by class,
* denials by reason (top-level categories),
* and whether any bypass attempt was blocked due to inability to validate (fail-closed events).

Review Packet MUST include:

* the above plan_bypass block in the summary (or a structured section).

---

## 7) Configuration Changes (loop_rules.yaml)

This proposal adds a `plan_bypass` block to rules that are bypass-eligible.

Example (illustrative):

```yaml
- rule_id: loop.lint-error
  decision: RETRY
  priority: 110
  match:
    failure_class: lint_error
  max_retries: 3
  plan_bypass:
    eligible: true
    mode: patchful
    scope_limit:
      max_total_line_delta: 50
      max_files: 3
    budget:
      per_class_max_bypasses: 3
- rule_id: loop.test-flake-no-change
  decision: RETRY
  priority: 110
  match:
    failure_class: test_flake_no_change
  max_retries: 2
  plan_bypass:
    eligible: true
    mode: no_change_rerun
    scope_limit:
      max_total_line_delta: 0
      max_files: 0
    budget:
      per_class_max_bypasses: 2

# Global cap (location may be a top-level policy stanza depending on existing schema)
plan_bypass_global_budget:
  max_bypasses_per_run: 5
```

**Fail-closed default:** if `plan_bypass` is absent for a rule, bypass eligibility is false.

---

## 8) Runtime Changes (Minimal Interface Spec)

### 8.1 ConfigurableLoopPolicy (Eligibility API)

Add a deterministic API that takes **Proposed Patch Stats** (not feedback length, not prior attempt estimates):

```python
def evaluate_plan_bypass(
    self,
    *,
    failure_class_key: str,             # canonical lower snake_case
    proposed_patch: ProposedPatch | None,
    protected_path_registry: ProtectedPathRegistry,
    ledger: AttemptLedger
) -> PlanBypassDecision:
    """
    Returns a structured decision containing:
    - evaluated/eligible/applied flags
    - rule_id and reason
    - scope metrics and protected path hits
    - budget accounting
    Must be deterministic and fail-closed.
    """
```

### 8.2 AutonomousBuildCycleMission (Control Flow Change)

For `RETRY` decisions:

1. Determine if the matched rule permits `plan_bypass`.
2. If bypass mode is `no_change_rerun`, enforce `proposed_patch is None` and rerun-only semantics.
3. If bypass mode is `patchful`:

   * Generate Proposed Patch in a **non-applied** form (patch file or equivalent),
   * Compute diffstat from the patch deterministically,
   * Evaluate plan bypass eligibility from those computed stats,
   * If eligible: apply patch and proceed,
   * If denied: invoke standard Plan gate behavior (blocked awaiting Plan Artefact approval), preserving Proposed Patch as evidence if allowed by existing evidence rules; otherwise discard.

**Critical invariant:** the loop MUST NOT apply a patch unless bypass is eligible OR a Plan Artefact has been approved.

---

## 9) Verification Plan (Council Acceptance Criteria)

### 9.1 Automated Tests (Required)

**Unit tests**

1. Patch diffstat computation produces correct `files_touched`, `added`, `deleted`, `total_line_delta`.
2. Eligibility returns **denied** if Proposed Patch is missing for patchful mode.
3. Eligibility returns **denied** if protected path registry cannot be loaded (fail-closed).
4. Eligibility returns **denied** if any protected path is touched.
5. Eligibility returns **denied** if over scope limits (files or total_line_delta).
6. Eligibility returns **denied** if budgets exhausted.
7. `test_flake_no_change` bypass returns **denied** if any file changes exist.

**Integration tests**
8. For a lint error retry with a small patch:

* bypass is applied,
* patch is applied only after eligibility passes,
* attempt ledger records the structured plan_bypass block,
* Review Packet includes “Plan Bypass Applied”.

1. For a retry that touches a protected path:

   * bypass denied,
   * standard Plan gate engaged (blocked),
   * ledger includes denial reason and protected hit.
2. For repeated bypass attempts exceeding global budget:

* bypass denied,
* standard Plan gate engaged (blocked),
* ledger shows budget exhaustion as reason.

### 9.2 Manual Verification (Optional)

* Trigger a controlled lint failure and confirm the system:

  * produces Proposed Patch,
  * computes diffstat,
  * applies bypass,
  * produces Review Packet,
  * records bypass statistics in terminal packet.

---

## 10) Risk Analysis (Updated)

| Risk | Failure Mode | Mitigation (This Proposal) |
| --- | --- | --- |
| Incorrect bypass grant | Uses non-authoritative estimates | Eligibility computed from Proposed Patch diffstat only |
| Protected path drift | Hardcoded lists go stale | Must consult authoritative registry; fail-closed on read/load failure |
| “Flake” masks real failure | Substantive changes under flake label | Only `test_flake_no_change` is bypass-eligible |
| Slow scope creep | Many small bypasses accumulate | Per-class and global bypass budgets |
| Audit gaps | Bypass not recorded consistently | Mandatory structured ledger fields + packet requirements |

---

## 11) Governance Path / Process

1. Council reviews this proposal (CT-2).
2. Council issues ruling:

   * APPROVE / APPROVE_WITH_CONDITIONS / REJECT
3. If approved:

   * Constitution amended per Section 5
   * Code changes implemented per Sections 6–8
   * Tests executed per Section 9
4. Adoption complete only when all acceptance tests pass and the evidence packets are produced per existing standards.

---

## 12) Council Questions (Targeted)

1. Is the allowlist appropriate and sufficiently narrow (especially the `test_flake_no_change` framing)?
2. Are the scope limits (`max_files=3`, `max_total_line_delta=50`) acceptable, or should they be tighter for Phase 4 entry?
3. Is the global bypass budget (recommended 5) appropriate, or should it be lower?
4. Should we require that bypass-eligible patches are restricted to certain non-governance subsystems (optional tightening), or is “protected paths only” sufficient for now?

---

## Appendix A — Proposed Text Diff for GEMINI.md (Illustrative)

This appendix is illustrative; exact insertion location is “Article XVIII”.

```diff
+## Section 5 — Loop Retry Plan Bypass (Trusted Builder Mode)
+
+A retry attempt MAY proceed without Plan Artefact approval ONLY if ALL are true:
+1) Failure class is explicitly allowlisted (TRUSTED_RETRY_CLASSES).
+2) A concrete Proposed Patch exists and scope is computed from the patch itself
+   (or the retry is an allowlisted no-change rerun).
+3) Scope is bounded: max_files <= 3 and max_total_line_delta <= 50.
+4) No governance-controlled/protected paths are touched (authoritative registry).
+5) Budgets permit bypass (per-class and global per-run).
+6) Review Packet is STILL REQUIRED (not waived).
+
+### §5.1 Fail-Closed Requirements
+If scope cannot be computed, protected paths cannot be checked, or budgets cannot be determined,
+Plan Bypass MUST be denied and the standard Plan gate MUST apply.
+
+### §5.2 Audit Requirements
+Attempt ledger MUST record evaluation outcome, reasons, scope metrics, protected path hits,
+budget accounting, and whether bypass was applied. Review Packet MUST note bypass when applied.
```

---

## Appendix B — Change Log vs v1.0 (What Was Fixed)

1. Replaced “estimated scope” heuristics with **Proposed Patch diffstat** as the sole patchful eligibility input.
2. Tightened `TEST_FLAKE` to `test_flake_no_change` only (no file modifications).
3. Required authoritative protected-path registry usage; removed hardcoded path lists as a dependency.
4. Added global bypass budget to prevent many small bypasses.
5. Made normalization requirements explicit (canonical lowercase snake_case).
6. Upgraded audit wiring to a structured ledger + packet requirements (not ad-hoc strings).
7. Added fail-closed clauses for any validation/registry/metrics uncertainty.

---

END

````
