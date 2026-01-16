---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"
---

# Scope Envelope

- **Goal**: [String]
- **Non-Goals**: [List]
- **In-Scope Paths**: [List]

---

# Proposed Changes

## P0.1 [Title]

- **Description**: [String]
- **Rationale**: [String]
- **Touchpoints**:
  - [Fixed Path or Discovery Query]

---

# Claims

- **Claim**: [Statement]
  - **Type**: [policy_mandate | canonical_path | output_contract | semantic_token_set]
  - **Evidence Pointer**: [path:Lx-Ly | path#sha256:HEX | N/A(Reason)]
  - **Status**: [asserted | proven | proposal]

---

# Targets

- **Target**: [Fixed Path or Query]
  - **Type**: [modify | new]
  - **Mode**: [fixed_path | discover]
  - **Intent**: [String]

---

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Codes**:
  - [Code]: [Message Template]

---

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| PASS_01 | ...           | PASS     |               |        |
| FAIL_01 | ...           | FAIL     | ...           | ...    |

---

# Migration Plan

- **Backward Compat**: [String]
- **Rollout Stages**: [List]
- **Deprecation Rules**: [List]

---

# Governance Impact

- **Touches Constitution**: [yes/no]
- **Gate**: [String]
- **Rationale**: [String]
