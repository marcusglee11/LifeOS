Judiciary Verdict Template v1.0

This is the canonical output format for every Judge in the Judiciary.

All judicial prompts should instruct the model to fill out this template verbatim, with no extra sections or commentary.

1. Header
JUDGE_ID: <short identifier for this judge instance>
TARGET_ARTEFACT: <name or path, e.g. "R6.5 Fix Pack">
REVIEW_SCOPE: <one of: FIX_PACK | IMPLEMENTATION_PLAN | RUNTIME_COMPONENT | GOVERNANCE_CHANGE | OTHER>


Examples:

JUDGE_ID: GPT_5_1_J1
TARGET_ARTEFACT: R6.5 Fix Pack
REVIEW_SCOPE: FIX_PACK

2. VERDICT

Exactly one of:

APPROVE

REJECT

REVISION_REQUIRED

Example:

VERDICT: REVISION_REQUIRED

3. RATIONALE

3–6 short bullets explaining the verdict, focusing on:

Determinism / reproducibility

Governance / constitutional alignment

Safety / risk

Scope adherence (no stealth feature creep)

Example:

RATIONALE:
- Rollback semantics are clarified and align with COO Runtime Spec §5.4.
- Signing boundary remains external; no key material is introduced into Runtime state.
- Test coverage for the new rollback_log limits is described but not yet explicit or property-based.

4. CONSTITUTIONAL REFERENCES

List the specific invariants, sections, or rules you are applying.

These can be informal but must be distinguishable and reusable (e.g. INV-1, AL-§3.2, COO-SPEC-§5.4).

Example:

CONSTITUTIONAL_REFERENCES:
- LifeOS v1.1 — INV-1 Determinism
- Alignment Layer v1.4 — No Silent Inference
- COO Runtime Spec v1.0 — §5.4 Rollback Integrity


If you cannot identify specific references, state that explicitly and treat it as a weakness in your verdict.

5. RISK RATING

Overall risk level if this artefact were adopted as-is.

One of:

LOW

MEDIUM

HIGH

Optional 1–2 bullets to justify.

Example:

RISK_RATING: MEDIUM
RISK_NOTES:
- Changes affect rollback_log behaviour, which is critical for incident response.
- Failure modes appear bounded but rely on correct implementation of log truncation.


If you cannot confidently assess risk, say so and lean conservative.

6. CONDITIONS / RECOMMENDATIONS (Optional)

Use this section only if:

VERDICT: REVISION_REQUIRED, or

VERDICT: APPROVE with explicit conditions you want recorded

Focus on concrete, testable changes rather than vague advice.

Example:

CONDITIONS:
- Add a property test ensuring rollback_log never exceeds the configured entry limit under any deterministic replay path.
- Explicitly document how rollback_log interacts with AMU₀ verification in failure scenarios.


If there are no conditions:

CONDITIONS:
- None.

Complete Example
JUDGE_ID: GPT_5_1_J1
TARGET_ARTEFACT: R6.5 Fix Pack
REVIEW_SCOPE: FIX_PACK

VERDICT: REVISION_REQUIRED

RATIONALE:
- The Fix Pack correctly tightens key-management boundaries in line with LifeOS and Alignment constraints.
- Determinism requirements are preserved; all new flows remain replayable given the described audit log.
- Rollback_log limits are introduced but the enforcement mechanism is underspecified and lacks property-based tests.

CONSTITUTIONAL_REFERENCES:
- LifeOS v1.1 — INV-1 Determinism
- Alignment Layer v1.4 — No Silent Inference
- COO Runtime Spec v1.0 — §5.4 Rollback Integrity

RISK_RATING: MEDIUM
RISK_NOTES:
- Misconfigured or incorrectly enforced rollback limits could impair incident reconstruction.

CONDITIONS:
- Specify the exact maximum number of rollback_log entries and how this interacts with disk space limits.
- Add an automated test that simulates repeated failure/replay cycles and verifies rollback_log truncation behaves deterministically.


Judicial prompts should explicitly say:

“Fill out the template exactly, with these section labels, and do not add or remove sections.”

“If a field is not applicable, write None. rather than omitting it.”
