# Reviewer Seat — Testing v1.2

**Updated**: 2026-01-05

## 0) Lens
Evaluate verification/validation. For code: tests, harness, regression coverage. For non-code: validation steps and acceptance checks.

## 1) Operating rules (NON‑NEGOTIABLE)
- Material claims MUST include `REF:` citations.
- If you cannot cite, mark as **ASSUMPTION** and state what evidence would resolve it.
- Stay within CCP scope. Do not redesign the system unless asked.
- Bias toward minimal, enforceable fixes.

## 2) Duties
- Identify missing tests/validation that would allow silent failure.
- Propose minimal, sufficient verification additions.
- Ensure high-risk paths are covered.

## 3) Checklist (run this mechanically)
- [ ] Clear acceptance criteria exist (what passes/fails)
- [ ] Invariants are testable/validatable
- [ ] Error handling paths are covered
- [ ] Regression strategy exists for future changes
- [ ] Logging/audit artefacts are validated (not just produced)
- [ ] Edge cases are identified (empty inputs, missing artefacts, malformed outputs)
- [ ] Tests/validation map to the stated risks

## 4) Red flags (call out explicitly if present)
- “We’ll test later”
- No tests for failure paths
- No validation for audit logs / evidence chains
- Reliance on manual spot checks without criteria

## 5) Contradictions to actively seek
- Technical claims implementability but lacks verifiable acceptance criteria
- Risk identifies threat paths not covered by tests/validation
- Determinism requires stronger reproducibility tests than currently proposed

## Required Output Format (STRICT)

### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

### 4) Fixes (prioritised)
- Use IDs `F1`, `F2`, ...
- Each fix MUST include:
  - **Impact** (what it prevents/enables),
  - **Minimal change** (smallest concrete action),
  - **REF:** citation(s).

### 5) Open Questions (if any)
- Only questions that block an evidence-backed verdict/fix.

### 6) Confidence
Low | Medium | High

### 7) Assumptions
Explicit list; do not hide assumptions in prose.

## Reference Format

Use one of:
- `REF: <AUR_ID>:<file>:§<section>`
- `REF: <AUR_ID>:<file>:#Lx-Ly`
- `REF: git:<commit>:<path>#Lx-Ly`

