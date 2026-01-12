---
artifact_id: "c8433bf9-0587-4533-a591-713520f572fb"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-07T14:25:00+11:00"
author: "Antigravity"
version: "1.1"
status: "PENDING_REVIEW"
mission_ref: "OpenCode-First Doc Stewardship Implementation"
tags: ["governance", "stewardship", "opencode", "gate", "hardened"]
---

# Plan: OpenCode-First Doc Stewardship (Phase 2) v1.1

## Executive Summary
Implement the "OpenCode-First Doc Stewardship" policy to mandate routing of in-envelope documentation changes through the OpenCode steward and its CT-2 gate. This refinement (v1.1) hardens the governance semantics, replaces absolute links with repo-relative paths, and makes authoritative inputs mechanically verifiable via an Implementation Report.

## Problem Statement
The transition to OpenCode-first stewardship requires absolute clarity on envelope applicability and mechanical proof of implementation hygiene. Ambiguities in governance surfaces vs. steward surfaces must be eliminated to prevent unauthorized agentic modification of protected documents.

## Authoritative Inputs (Audit Chain)

Execution must be mechanically faithful to the following specs. SHA-256 hashes are recorded in the **Implementation Report** section of the delivery Review Packet at execution time.

| Artefact | Path | Version | SHA-256 |
| :--- | :--- | :--- | :--- |
| **Gate Runner** | `scripts/opencode_ci_runner.py` | v1.3 | *recorded at exec* |
| **Gate Policy** | `scripts/opencode_gate_policy.py` | v1.3 | *recorded at exec* |
| **CT-2 Ruling** | `docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md` | v1.1 | *recorded at exec* |
| **DAP** | `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md` | v2.0 | *recorded at exec* |

## Envelope Applicability

### Protected Surfaces (Out-of-Envelope)
Edits to the following roots are strictly **out-of-envelope** and MUST NOT use OpenCode stewardship. Adoptions/modifications in these areas must follow the standard governance procedure (Council Ruling + Review Packet):
- `docs/00_foundations/`
- `docs/01_governance/`
- `docs/03_runtime/`
- `scripts/`
- `config/`
- `GEMINI.md`

### Steward Surface (In-Envelope)
Only the demonstration run and future allowed `.md` updates in the steward envelope use OpenCode + CT-2 evidence capture.
- **Demonstration Target**: `docs/08_manuals/Governance_Runtime_Manual_v1.0.md`

## Interfaces + Artefact Schemas

### CLI Entrypoint (Mandatory)
```bash
python scripts/opencode_ci_runner.py --task "<JSON_PAYLOAD>"
```

### Output Artefact Templates
| Report Type | Template Path |
| :--- | :--- |
| **Blocked Report** | `docs/02_protocols/templates/blocked_report_template_v1.0.md` |
| **Gov Request** | `docs/02_protocols/templates/governance_request_template_v1.0.md` |

## Determinism Contract
- **Input Freeze**: All inputs normalized via `scripts/opencode_gate_policy.py`.
- **Hygiene Proof**: Compliance checked via `pytest tests_recursive/test_opencode_gate_policy.py::TestRunnerLogHygiene`.
- **Zero-Ambiguity**: Final evidence bundle must contain unelided logs and a machine-readable footer.

## Proposed Changes

### Governance and Policy (Out-of-Envelope Path)

#### [MODIFY] [OpenCode_First_Stewardship_Policy_v1.1.md](docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md)
- Header: "Status: Active"
- Activated by: `docs/01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md`
- Replace local file-URI links with repo-relative links without including the literal token.

#### [MODIFY] [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](docs/03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md)
- Incorporate Section 7.3 mandate.

#### [NEW] [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](docs/01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md)
- Record sign-off for v1.1.

### Index Updates

#### [MODIFY] [INDEX.md](docs/01_governance/INDEX.md)
- Link Policy v1.1 and Ruling v1.1.


## Verification Plan

### Automated
1. `pytest tests_recursive/test_opencode_gate_policy.py`
2. `python scripts/validate_packet.py` (if applicable)

### Manual (Demonstration)
1. **Demo Task**: Update timestamp in `docs/08_manuals/Governance_Runtime_Manual_v1.0.md`.
2. **Execution**: Run via OpenCode steward + Gate Runner.
3. **Evidence**: Produce full CT-2 bundle with zero ellipses.

## DONE Checklist

- [ ] Policy status/activation consistency verified.
- [ ] F7 Protocol updated with Section 7.3.
- [ ] Demonstration run produced valid evidence bundle.
- [ ] Review Packet v1.1 includes Implementation Report with literal SHAs.
