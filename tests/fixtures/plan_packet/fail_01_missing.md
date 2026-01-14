
- **Goal**: G
- **Non-Goals**: NG
- **In-Scope Paths**: P

# Proposed Changes
## P0.1 Title
- **Description**: D
- **Rationale**: R
- **Touchpoints**:
  - P

# Claims
- **Claim**: C
  - **Type**: output_contract
  - **Statement**: S
  - **Status**: asserted

# Targets
- **Target**: T
  - **Type**: new
  - **Mode**: discover
  - **Intent**: I

# Validator Contract
- **Output Format**: PASS/FAIL
- **Failure Codes**:
  - C: M

# Verification Matrix
| Case ID | Input | Expected | Expected Code | Prefix |
|---------|-------|----------|---------------|--------|
| PASS_01 | pass.md | PASS   |               |        |
| FAIL_01 | fail.md | FAIL   | PPV001        | Missing|
| FAIL_02 | fail.md | FAIL   | PPV002        | Order  |
| FAIL_03 | fail.md | FAIL   | PPV003        | Pointer|
| FAIL_04 | fail.md | FAIL   | PPV004        | Path   |
| FAIL_05 | fail.md | FAIL   | PPV005        | Invalid|

# Migration Plan
- **Backward Compat**: B
- **Rollout Stages**: R
- **Deprecation Rules**: D

# Governance Impact
- **Touches Constitution**: no
- **Gate**: None
- **Rationale**: N/A
