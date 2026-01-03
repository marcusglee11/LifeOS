# FP-4.x Implementation Packet v0.1
(derived from FP-4.x Fix Pack Specification v0.1)

## 0. METADATA

- **Name**: FP-4.x Implementation Packet  
- **Version**: v0.1  
- **Upstream Specs**: Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md, FP-4x_Fix_Pack_Specification_v0.1.md  
- **Authority**: Runtime Architecture (under Governance Council)  
- **Execution Agent**: Antigrav (Runtime Builder / Doc Steward)  
- **Status**: Ready for implementation (no placeholders)  

**Objective**: Provide a concrete, module-level implementation plan for FP-4.x.

**Scope**: `runtime/` package, `runtime/tests/` test suite, related docs.

---

## 1. IMPLEMENTATION PRINCIPLES

1. **Determinism preserved**: No new nondeterministic sources.
2. **Minimal surface change**: Prefer additive, modular utilities.
3. **Governance surfaces sealed**: Runtime cannot self-modify governance.
4. **Anti-Failure compliance**: ≤2 human governance primitives per workflow.
5. **Tier-1 → Tier-2 compatibility**: All work supports Tier-2 activation.

---

## 2. DIRECTORY AND MODULE PLAN

### 2.1 New Utility Modules
- `runtime/util/atomic_write.py`
- `runtime/util/detsort.py`

### 2.2 Envelope / Gateway
- `runtime/envelope/execution_envelope.py`
- `runtime/gateway/deterministic_call.py`

### 2.3 AMU₀ & Index Lineage
- `runtime/amu0/lineage.py`
- `runtime/index/index_updater.py`

### 2.4 Governance Surfaces
- `runtime/governance/HASH_POLICY_v1.py`
- `runtime/governance/surface_manifest.json`
- `runtime/governance/surface_manifest.sig`
- `runtime/governance/override_protocol.py`

### 2.5 Validator & Safety
- `runtime/validator/anti_failure_validator.py`
- `runtime/safety/health_checks.py`
- `runtime/safety/halt.py`
- `runtime/safety/playbooks/*.md`

### 2.6 API Boundaries
- `runtime/api/governance_api.py`
- `runtime/api/runtime_api.py`

### 2.7 Tests
- `test_envelope_single_process.py`
- `test_envelope_network_block.py`
- `test_deterministic_gateway.py`
- `test_amu0_hash_chain.py`
- `test_index_atomic_write.py`
- `test_governance_surface_immutable.py`
- `test_governance_override_protected_surface.py`
- `test_validator_smuggled_human_steps.py`
- `test_validator_workflow_chaining_limit.py`
- `test_validator_fake_agent_tasks.py`
- `test_attestation_recording.py`
- `test_safety_health_checks.py`
- `test_safety_halt_procedure.py`
- `test_detsort_consistency.py`

### 2.8 Orchestration Adapters
- `runtime/orchestration/config_adapter.py`
- `runtime/orchestration/config_test_run.py`


---

## 3. IMPLEMENTATION BY CONDITION SET

### 3.1 CND-1 — Execution Envelope & Threat Model
- ExecutionEnvelope class with verify_* methods
- PYTHONHASHSEED=0 enforcement
- Single-process guarantee
- No ungoverned network I/O
- Pinned dependencies via requirements_lock.json
- Deterministic gateway for subprocess/network

### 3.2 CND-2 — AMU₀ & Index Integrity Hardening
- Hash-chained lineage (parent_hash, entry_hash, SHA-256)
- Atomic writes (write-temp + rename)
- Council-defined hash function (HASH_POLICY_v1)

### 3.3 CND-3 — Governance Surface Immutability
- Read-only governance surfaces via manifest + signature
- Council-only override protocol with AMU₀ logging

### 3.4 CND-4 — Anti-Failure Validator Hardening
- Adversarial tests (smuggled steps, chaining, fake agents)
- Attestation logging (HumanAttestation dataclass)

### 3.5 CND-5 — Operational Safety Layer
- Failure-mode playbooks (markdown)
- Health checks (DAP, INDEX, AMU₀)
- Tier-1 halt procedure

### 3.6 CND-6 — Simplification Requirements
- Deduplicate detsort logic
- Simplify AMU₀ to linear hash chain
- Clarify API boundaries (governance_api, runtime_api)

---

## 4. COMPLETION CHECKLIST

- [ ] All modules in Section 2 exist
- [ ] All tasks in Sections 3.1–3.6 implemented
- [ ] All tests present and green
- [ ] AMU₀ hash chain verification works
- [ ] Governance surface validation works
- [ ] Health checks and halt procedure integrated
- [ ] DAP and INDEX use shared detsort utilities

