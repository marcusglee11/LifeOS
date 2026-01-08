# Policy: OpenCode-First Doc Stewardship (Phase 2 Envelope) v1.0

**Status**: Active  
**Authority**: LifeOS Governance Council  
**Date**: 2026-01-07  

---

## 1. Purpose
This policy reduces drift and eliminates ambiguity in the LifeOS documentation lifecycle by making OpenCode the mandatory default steward for all changes within its authorized Phase 2 envelope. By enforcing this routing, the repository ensures that all eligible documentation updates are processed through the CT-2 gate, producing deterministic evidence bundles for audit.

## 2. Definitions
- **"Phase 2 Doc-Steward Envelope"**: The set of patterns and constraints currently authorized for the OpenCode Document Steward, as defined in the following canonical sources:
  - **Runner**: [scripts/opencode_ci_runner.py](scripts/opencode_ci_runner.py)
  - **Policy**: [scripts/opencode_gate_policy.py](scripts/opencode_gate_policy.py)
  - **Ruling**: [docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md)
- **"In-envelope doc change"**: Any modification that the CT-2 gate would classify as ALLOWED. Specifically:
  - Targets the `docs/` subtree (excluding protected roots).
  - Uses only `.md` extensions.
  - Does not involve structural operations (delete, rename, move, copy).
  - Does not touch denylisted roots (`docs/00_foundations/`, `docs/01_governance/`, `scripts/`, `config/`).

## 3. Default Routing Rule (MUST)
For any in-envelope documentation change (including index updates and doc propagation tasks), Antigravity **MUST**:
1. **Invoke OpenCode** to perform the stewardship edit(s).
2. **Run the CT-2 gate runner** (`scripts/opencode_ci_runner.py`) to validate the change.
3. **Produce and retain** the full CT-2 evidence bundle outputs (including `exit_report.json`, `changed_files.json`, `classification.json`, `runner.log`, and `hashes.json`).

## 4. Explicit Exceptions (MUST, fail-closed)
- **Out-of-envelope changes**: If a change involves denylisted/protected surfaces, non-`.md` files, or structural operations, Antigravity **MUST NOT** attempt OpenCode stewardship. It **MUST BLOCK** the operation, emit a minimal "blocked report", and generate a governance packet request per repository convention.
- **Structural operations**: Deletions, renames, moves, and copies are strictly blocked in Phase 2. Antigravity **MUST BLOCK** and report these attempts.
- **System unavailability**: If OpenCode, the gate runner, or critical CI references are unavailable, Antigravity **MUST BLOCK** and return detailed diagnostics and next-action instructions. Bypassing the gate is forbidden.

## 5. Mixed Changes Rule (docs + code)
In mission blocks containing both documentation and code edits:
- Documentation edits that fall within the Phase 2 envelope **MUST** be executed via OpenCode stewardship and satisfy CT-2 evidence requirements.
- Code changes must follow standard build/test/verification gates as defined in their respective protocols.

## 6. Evidence and Audit Requirements (MUST)
All mandated stewardship runs must provide deterministic capture of:
- Full file list of modified artifacts.
- Explicit classification decisions (A/M/D).
- Precise reason codes for any BLOCK decisions.
- SHA-256 hashes of all inputs and outputs.
- No-ellipsis outputs as enforced by the CT-2 passage fixes (v2.4).

## 7. Adoption and Enforcement
Antigravity’s own operating protocols (including F7) are binding to this policy. Any documentation update performed outside this routing without explicit Council waiver is treated as a process failure and requires immediate remediation and audit.

---

**Signed**,  
LifeOS Governance Council
