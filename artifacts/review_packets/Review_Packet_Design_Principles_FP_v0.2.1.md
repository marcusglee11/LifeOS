# Review Packet: Fix Pack — Design Principles Protocol v0.2.1

**Packet ID:** Review_Packet_Design_Principles_FP_v0.2.1  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Mission:** Apply Council GO_WITH_FIXES to Design Principles Protocol v0.2

---

## 1. Summary

Applied 12 editorial fixes from Council review to `LifeOS_Design_Principles_Protocol_v0.2.md`. Document is now v0.2.1 with status **Canonical (Council GO_WITH_FIXES applied)**.

---

## 2. Fix Mapping Table

| Priority | Fix # | Section | Change |
|----------|-------|---------|--------|
| **P0** | 1 | §2.4 | Removed "lightweight exception" wording; reframed Spike Declaration as authorized Plan Artefact format, not exception |
| **P0** | 2 | §2.4 | Deterministic path: `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md` required before execution |
| **P0** | 3 | §2.4 | Added CAUTION block: Spike Mode prohibited for governance surfaces |
| **P0** | 4 | §2.3 | Removed `_wip` / `_experimental` suffix pattern rule; kept only explicit roots |
| **P0** | 5 | §2.3 item 3 | Clarified: deletion allowed PROVIDED Spike Declaration + Review Packet preserved |
| **P0** | 6 | §2.5.1 | Added explicit definition: "integration with governance surfaces" = import/call/read/write/stage/promote |
| **P0** | 7 | §4.1 | Added mandatory evidence fields (YAML schema): command_used, output_log, error_log, exit_code, artifact_path |
| **P0** | 8 | §4.2 | Changed "Runs without manual intervention" → single command/script with no interactive input |
| **P0** | 9 | §4.2 | Added: Tests are executable via pytest or equivalent without environment surgery |
| **P0** | 10 | §4.3 | Added TDD gate: At least one failing happy-path test must exist before MVP code is considered started |
| **P1** | 11 | §8.2 | Replaced percentage-only targets with outcome-based coverage gates (% now optional) |
| **P2** | 12 | §5.2 | Added 5th requirement: Governance debt enumeration from §8.3 with risk + closure plan |

---

## 3. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| §2.4 no longer claims "exception" to GEMINI.md | ✅ PASS |
| §2.3 contains no suffix/pattern-based sandbox allowances | ✅ PASS |
| "Integration with governance surfaces" explicitly defined | ✅ PASS |
| §4.1 includes mandatory evidence fields | ✅ PASS |
| §4.2 includes single-command/no-interactive requirement | ✅ PASS |
| §4.2 includes test execution requirement | ✅ PASS |
| Evidence package returned (diff + sha256 + mapping) | ✅ PASS |

---

## 4. Evidence Package

### 4.1 SHA256

```
e79820f31a61fbae60648a8634039b8ec27b4de21c34ccb62001115d5c3cbf76  docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md
```

### 4.2 Unified Diff

```diff
--- a/docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md
+++ b/docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md
@@ -1,7 +1,7 @@
 # LifeOS Design Principles Protocol

-**Version:** v0.2  
-**Status:** Draft — For Council Review  
+**Version:** v0.2.1  
+**Status:** Canonical (Council GO_WITH_FIXES applied)  
 **Date:** 2026-01-08  
 **Author:** Claude (Execution Partner)  
 **Canonical Path:** `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md`
@@ -56,12 +56,11 @@
 MVP and spike work MUST occur in locations that:

 1. **Are not under governance control** — Not in `docs/00_foundations/`, `docs/01_governance/`, `runtime/governance/`, or any path matching `*Constitution*.md` or `*Protocol*.md`
-2. **Are explicitly marked as experimental** — Permitted locations:
+2. **Are explicitly marked as experimental** — Permitted locations (exhaustive list):
    - `runtime/experimental/`
    - `spikes/`
    - `sandbox/`
-   - Any directory containing `_wip` or `_experimental` suffix
-3. **Can be deleted without triggering governance alerts**
+3. **Can be deleted without triggering governance alerts** — Sandbox code/assets may be deleted without governance alerts, PROVIDED Spike Declaration + Lightweight Review Packet are preserved under `artifacts/spikes/<YYYYMMDD>_<short_slug>/`
 4. **Do NOT trigger Document Steward Protocol** — Files in sandbox locations are exempt from `INDEX.md` updates and corpus regeneration until promoted

@@ -68,11 +67,11 @@

 ### 2.4 GEMINI.md Reconciliation (Plan Artefact Gate)

-GEMINI.md Article XIII requires a Plan Artefact before substantive work. This protocol provides a lightweight exception:
+This protocol establishes the **Spike Declaration** as the authorized Plan Artefact format for Spike Mode, consistent with GEMINI.md Article XVIII (Lightweight Stewardship). It is not an exception for governance-surface work.

 **Spike Mode:**

-For time-boxed explorations (≤3 days), agents may use a **Spike Declaration** instead of a full `implementation_plan.md`:
+For time-boxed explorations (≤3 days), agents MUST use a **Spike Declaration** as the Plan Artefact:

 ```markdown
 ## Spike Declaration
@@ -79,14 +78,17 @@
 **Time Box:** [Duration: 2 hours / 1 day / 3 days]
 **Success Criteria:** [Observable result]
-**Sandbox Location:** [Path within permitted sandbox]
+**Sandbox Location:** [Path within permitted sandbox — see §2.3]
 ```

 **Conditions:**
-- Spike Declaration must be recorded in `artifacts/spikes/` or task.md
-- Work must remain within declared sandbox location
+- Spike Declaration MUST be recorded **before execution** at: `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md`
+- Work must remain within declared sandbox location (§2.3 permitted roots only)
 - CEO retains authority to cancel at any time
 - Upon spike completion, a Lightweight Review Packet is required (see §4.1)

+> [!CAUTION]
+> **Spike Mode is prohibited for governance surfaces.** If work touches any path listed in §5.5, full Plan Artefact (implementation_plan.md) and Council review are required. No spike exception applies.
+
 ### 2.5 Council Protocol Reconciliation (CT-1 Trigger)

 Council Protocol v1.2 CT-1 triggers on "new capability introduction." This protocol clarifies:
@@ -93,7 +95,18 @@
 1. **MVP work in sandbox locations does NOT trigger CT-1** — Exploratory work is not a capability until it seeks production status
-2. **Integration with governance surfaces triggers CT-1** — When MVP work touches governance-controlled paths or seeks promotion to `runtime/` or `docs/`, CT-1 applies
+2. **Integration with governance surfaces triggers CT-1** — See §2.5.1 for definition
 3. **Council reviews working systems** — Hardening reviews evaluate running code with test evidence, not theoretical architectures

+#### 2.5.1 Definition: Integration with Governance Surfaces
+
+"Integration with governance surfaces" means ANY of the following:
+
+- **Importing/calling** governance-controlled modules or functions
+- **Reading/writing** governance-controlled files or paths at runtime
+- **Staging/merging** changes that touch governance surfaces (per §5.5)
+- **Promoting** capability into `runtime/` or `docs/` paths outside sandbox roots (§2.3)
+
+This definition is consistent with §5.5 (Governance Surface Definition).
+
 ---

@@ -172,8 +185,17 @@
 1. **Question answered** — The original spike question
 2. **Outcome** — proceed / pivot / abandon
 3. **Key learnings** — What was discovered
-4. **Evidence** — Test output, execution logs, or demo results
-5. **Next steps** — If proceeding, what MVP scope is proposed
+4. **Next steps** — If proceeding, what MVP scope is proposed
+5. **Evidence (mandatory fields):**
+
+```yaml
+evidence:
+  command_used: "<exact command to run spike>"
+  output_log: "<path to output log OR inline excerpt>"
+  error_log: "<path to error log OR 'none'>"
+  exit_code: <integer>
+  artifact_path: "<path where runnable code/demo lives>"
+```

@@ -189,9 +211,10 @@
 **Definition:** The smallest implementation that delivers end-to-end value.

 **MVP Checklist:**
-- [ ] Runs without manual intervention (for its scope)
+- [ ] Runs end-to-end via a single command/script with no interactive input (for its scope)
 - [ ] Produces observable output
 - [ ] Has at least one happy-path test
+- [ ] Tests are executable via `pytest` or equivalent without environment surgery
 - [ ] Has basic error handling (fails loudly, not silently)
 - [ ] Is documented in a README or inline comments
 - [ ] Remains within sandbox until hardening
@@ -211,6 +234,9 @@
 3. **Refactor** — Clean up without changing behavior
 4. **Repeat** — Next test, next increment

+> [!IMPORTANT]
+> At least one failing happy-path test must exist before MVP code is considered started.
+
 **Test Priorities:**

@@ -262,6 +288,7 @@
 2. **Gap analysis** — What MVP lacks vs. production requirements
 3. **Proposed hardening** — Specific additions for each gap
 4. **Risk assessment** — What could go wrong, likelihood, mitigation
+5. **Governance debt enumeration** — From §8.3, with risk assessment and proposed closure plan

 Council reviews what exists and what should be added, not theoretical architecture.

@@ -400,12 +427,12 @@

 ### 8.2 Test Coverage Progression

-| Stage | Coverage Target |
-|-------|-----------------|
-| Spike | 0% (disposable code) |
-| MVP | >50% of happy paths |
-| Stabilize | >80% of exercised paths |
-| Harden | >90% including edge cases |
+| Stage | Coverage Gate | Optional % Target |
+|-------|---------------|-------------------|
+| Spike | No tests required (disposable code) | 0% |
+| MVP | Covers all user-visible outcomes (happy path) with runnable test(s) | >50% |
+| Stabilize | Covers all exercised paths observed in supervised runs | >80% |
+| Harden | Adds edge/adversarial cases relevant to real failures | >90% |

@@ -425,7 +452,8 @@
 ## 9. Version History

 | Version | Date | Author | Changes |
-|---------|------|--------|---------|
+|---------|------|--------|--------|
+| 0.2.1 | 2026-01-08 | Claude | **Council GO_WITH_FIXES applied**: §2.3 sandbox loophole closed (removed pattern rule); §2.4 reframed as compliant format (not exception) + governance prohibition + deterministic path; §2.5.1 added integration definition; §4.1 mandatory evidence fields; §4.2 single-command + test execution requirements; §4.3 TDD gate; §5.2 governance debt requirement; §8.2 outcome-based coverage gates. |
 | 0.2 | 2026-01-08 | Claude | Added: §2.3 Development Sandbox, §2.4 GEMINI.md Reconciliation, §2.5 Council Protocol Reconciliation, §4.1 Review Packet requirements, §5.4 CEO Override Authority, §5.5 Governance Surface Definition, §6.6 Sandbox Escape anti-pattern. Updated subordination chain. |
 | 0.1 | 2026-01-08 | Claude | Initial draft |
```

---

## 5. Non-Goals

- Amendments to Constitution v2.0, Council Protocol v1.2, Tier Spec v1.1, or GEMINI.md
- Introducing new governance surfaces
- Structural operations (renames/moves/deletes)

---

## 6. Files Modified

| Action | Path |
|--------|------|
| MODIFY | `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md` → v0.2.1 |

---

## 7. Document Steward Protocol

- ✅ INDEX.md already contains entry for v0.2 (status tag updated in document itself)
- ✅ LifeOS_Strategic_Corpus.md regenerated

---

**END OF REVIEW PACKET**
