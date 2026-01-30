> [!NOTE]
> **STATUS**: Non-Canonical (Information Only). This document is provided for context and architectural reference but is not an authoritative specification.

# Council Agent Design v1.0

**Status:** DRAFT — Design In Progress  
**Authority:** Council Protocol v1.3  
**Designer:** Clawd (COO)  
**Approved By:** CEO (2026-01-27)  
**Decision Basis:** CEO Decision Packets #1-3

---

## 1. Purpose

The **Council Agent** implements Council Protocol v1.3, automating multi-seat review processes to eliminate manual "waterboy" orchestration of council reviews.

**Goals:**
1. Execute council reviews autonomously per protocol
2. Support M0/M1/M2 mode selection (start simple, scale as needed)
3. Produce structured Council Run Logs with evidence
4. Enable async CEO approval/override where required

---

## 2. Architecture

### 2.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    COUNCIL AGENT                            │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │  CCP Parser   │→ │ Mode Selector │→ │  Orchestrator│  │
│  └───────────────┘  └───────────────┘  └──────────────┘  │
│         ↓                   ↓                   ↓          │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Seat Executors│  │  Chair/Synth  │  │  Log Writer  │  │
│  └───────────────┘  └───────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
    [Models]          [Evidence Store]      [Audit Trail]
```

### 2.2 Component Specifications

#### **A. CCP Parser**
**Function:** Parse Council Context Pack (YAML header + AUR)  
**Inputs:** CCP file or structured dict  
**Outputs:** Validated CCP object  
**Validation:**
- Required fields per Council Protocol §4
- Enum validation (aur_type, change_class, etc.)
- Mode selection rule validation

#### **B. Mode Selector**
**Function:** Determine M0/M1/M2 mode per protocol rules  
**Logic:** Implements Council Protocol v1.3 §4 mode_selection_rules_v1  
**Outputs:** Selected mode + topology + model plan  
**Override:** Honors CCP override.mode if present

#### **C. Orchestrator**
**Function:** Execute council review workflow  
**Pattern:** Supervisor/Centralized (per external research)  
**Responsibilities:**
- Instantiate Chair + Co-Chair
- Execute reviewer seats per mode/topology
- Coordinate handoffs
- Aggregate results

#### **D. Seat Executors**
**Function:** Execute individual reviewer seats  
**Implementation:** Call agent API with role-specific prompts  
**Outputs:** Structured seat response per Council Protocol §7  
**Validation:** Schema compliance, evidence-by-reference

#### **E. Chair Agent**
**Function:** Central coordinator per Council Protocol §5.1  
**Responsibilities:**
- Validate CCP completeness
- Manage topology execution
- Reject malformed outputs
- Synthesize verdict + Fix Plan
- Generate Contradiction Ledger

#### **F. Co-Chair Agent**
**Function:** Validator + challenger per Council Protocol §5.1  
**Responsibilities:**
- Challenge Chair synthesis
- Hunt hallucinations
- Verify Contradiction Ledger (MONO topology)
- Produce role prompt blocks

#### **G. Log Writer**
**Function:** Generate Council Run Log  
**Outputs:** Structured log per Council Protocol §2.1  
**Contents:**
- AUR identifier + hash
- Selected mode/topology
- Model plan
- All seat outputs
- Chair synthesis
- Verdict + Fix Plan

---

## 3. Modal Implementation

### Mode Definitions

#### **M0_FAST** (Start Here)
**Use Case:** Routine reviews, low-stakes changes  
**Seats:** 1 (L1 Unified Reviewer)  
**Topology:** MONO (single model)  
**Model:** Primary fallback chain  
**Benefits:** Fast, low cost, simple implementation

#### **M1_STANDARD**
**Use Case:** Standard reviews, testable changes  
**Seats:** 5-9 (configurable subset)  
**Topology:** MONO or HYBRID  
**Models:** Single model or Chair+selected external  
**Requirements:** Co-Chair challenge pass, Contradiction Ledger

#### **M2_FULL**
**Use Case:** Critical governance, safety-critical  
**Seats:** All 9 (full protocol)  
**Topology:** DISTRIBUTED (per protocol requirements)  
**Models:** Independent models for Risk/Governance seats (MUST)  
**Requirements:** Independence rule §6.3, full evidence trails

### Mode Selection Algorithm

```python
def select_mode(ccp: CCP) -> Mode:
    # Check override
    if ccp.override.mode:
        return ccp.override.mode
    
    # M2_FULL triggers (§4 mode_selection_rules_v1)
    if (
        "governance_protocol" in ccp.touches
        or "tier_activation" in ccp.touches
        or "runtime_core" in ccp.touches
        or ccp.safety_critical == True
        or (ccp.blast_radius in ["system", "ecosystem"] and ccp.reversibility == "hard")
        or (ccp.uncertainty == "high" and ccp.blast_radius != "local")
    ):
        return Mode.M2_FULL
    
    # M0_FAST triggers
    if (
        ccp.aur_type in ["doc", "plan", "other"]
        and (ccp.touches == ["docs_only"] or all(
            t not in ["runtime_core", "interfaces", "governance_protocol"]
            for t in ccp.touches
        ))
        and ccp.blast_radius == "local"
        and ccp.reversibility == "easy"
        and ccp.safety_critical == False
        and ccp.uncertainty == "low"
    ):
        return Mode.M0_FAST
    
    # Default: M1_STANDARD
    return Mode.M1_STANDARD
```

---

## 4. Execution Flow

### Workflow Sequence

```
1. PARSE CCP
   ├─ Validate YAML header
   ├─ Load AUR artifacts
   └─ Check completeness

2. SELECT MODE
   ├─ Apply mode selection rules
   ├─ Determine topology
   └─ Build model plan

3. INSTANTIATE CHAIR
   ├─ Load Chair prompt
   ├─ Inject CCP context
   └─ Initialize Co-Chair (M1/M2)

4. EXECUTE SEATS
   ├─ M0: Single L1 Unified Reviewer
   ├─ M1: Configurable 5-9 seats (sequential)
   └─ M2: All 9 seats (parallel where possible)

5. VALIDATE OUTPUTS
   ├─ Check schema compliance (§7)
   ├─ Verify evidence-by-reference
   └─ Request corrections if malformed

6. CHAIR SYNTHESIS
   ├─ Aggregate seat findings
   ├─ Generate Contradiction Ledger
   ├─ Produce verdict + Fix Plan
   └─ Co-Chair validation (M1/M2)

7. CEO DECISION (if required)
   ├─ Package decision points
   ├─ Await CEO input
   └─ Apply CEO ruling

8. FINALIZE LOG
   ├─ Write Council Run Log
   ├─ Attach evidence artifacts
   └─ Commit to audit trail
```

---

## 5. Integration Points

### 5.1 Runtime Integration

**Location:** `runtime/agents/council.py` (new file)  
**Dependencies:**
- `runtime/agents/api.py` (call_agent interface)
- `runtime/agents/models.py` (model selection)
- Council Protocol v1.3 (specification)

**API:**
```python
def run_council(
    ccp: Union[Path, Dict],
    mode_override: Optional[Mode] = None,
    model_override: Optional[str] = None,
    async_ceo: bool = True
) -> CouncilRunLog:
    """
    Execute council review per protocol.
    
    Args:
        ccp: Council Context Pack (file path or dict)
        mode_override: Force specific mode (M0/M1/M2)
        model_override: Override model selection
        async_ceo: If True, package CEO decisions for async approval
        
    Returns:
        CouncilRunLog with verdict, Fix Plan, and audit trail
    """
```

### 5.2 CLI Integration

**Command:** `lifeos council <ccp-file>`  
**Options:**
- `--mode [M0|M1|M2]` — Override mode selection
- `--model <model-name>` — Override model
- `--sync` — Block for CEO decisions (default: async)
- `--output <path>` — Log output location

**Example:**
```bash
lifeos council artifacts/ccp_architecture_review_v1.yaml --mode M1
```

### 5.3 Script Integration

**New Script:** `scripts/run_council.py`  
**Purpose:** Invoke council reviews from automation/CI  
**Integration:** Can be called by doc steward, builder, etc.

---

## 6. Configuration

### 6.1 Model Plan (per mode)

**M0_FAST:**
```yaml
models:
  primary: grok-4.1-fast
  seat_unified: grok-4.1-fast
```

**M1_STANDARD:**
```yaml
models:
  primary: claude-sonnet-4-5
  chair: claude-sonnet-4-5
  co_chair: claude-sonnet-4-5
  seats_default: claude-sonnet-4-5
```

**M2_FULL:**
```yaml
models:
  primary: claude-sonnet-4-5
  chair: claude-sonnet-4-5
  co_chair: gpt-5.2  # Independent challenge
  risk_adversarial: deepseek-v3.2  # Independent (MUST per protocol)
  governance: gemini-3-pro  # Independent (MUST per protocol)
  seats_default: claude-sonnet-4-5
```

### 6.2 Seat Selection (M1_STANDARD configurable)

**Default 5-seat subset (M1):**
1. Architect
2. Technical
3. Risk/Adversarial
4. Governance
5. Simplicity

**Optional seats:**
- Alignment
- Structural & Operational
- Testing
- Determinism

---

## 7. Evidence Management

### 7.1 Evidence-by-Reference

**Requirement:** All material claims must cite AUR  
**Format:** `REF: <AUR_ID>:<file>:§<section>` or `#Lx-Ly`

**Validation:**
- Chair validates citations exist
- Rejects seat outputs without evidence
- Logs ASSUMPTION markers

### 7.2 Complexity Budget

**Requirement:** Per Council Protocol §7.3  
**Enforcement:**
- Chair validates complexity_budget in seat outputs
- Rejects seats missing budget
- Tracks net_human_steps across recommendations

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Test Suite:** `tests/test_council_agent.py`

**Coverage:**
- CCP parsing + validation
- Mode selection logic
- Seat execution + validation
- Chair synthesis
- Log generation

### 8.2 Integration Tests

**Test Suite:** `tests/integration/test_council_workflows.py`

**Scenarios:**
- M0_FAST: Simple doc review
- M1_STANDARD: Code change review
- M2_FULL: Governance protocol change
- Error handling: Malformed seat output
- CEO decision flow

### 8.3 Validation

**Checklist:**
- ✅ Produces valid Council Run Log
- ✅ Respects mode selection rules
- ✅ Enforces evidence-by-reference
- ✅ Handles CEO async approval
- ✅ Logs to audit trail

---

## 9. Deployment Plan

### Phase 1: M0_FAST Only (Week 1)
**Scope:** Implement basic workflow with single unified reviewer  
**Goal:** Prove end-to-end automation  
**Use Case:** Doc reviews, low-stakes changes

### Phase 2: M1_STANDARD (Week 2)
**Scope:** Add multi-seat execution, Chair/Co-Chair  
**Goal:** Handle standard code reviews  
**Use Case:** Feature changes, refactoring

### Phase 3: M2_FULL (Week 3)
**Scope:** Add independent model execution, full 9 seats  
**Goal:** Critical governance reviews  
**Use Case:** Governance protocol changes, tier activation

### Phase 4: Production (Week 4)
**Scope:** CLI integration, automation hooks  
**Goal:** Replace manual council orchestration  
**Success Criteria:** CEO exits waterboy mode for reviews

---

## 10. Open Questions

**Q1:** Where should Council Run Logs be stored?  
**Options:**
- `artifacts/council_logs/`
- `docs/council_logs/`
- Git-tracked or .gitignore?

**Q2:** How should CEO async approval be surfaced?  
**Options:**
- WhatsApp notification with decision packet
- CLI command to list pending approvals
- Web dashboard view

**Q3:** Should council agent auto-commit logs to git?  
**Options:**
- Yes (automated audit trail)
- No (manual review before commit)

**Q4:** What's the failure/retry strategy?  
**Options:**
- Retry on model API failure (up to 3x)
- Fail-closed on validation errors
- CEO escalation on persistent failures

---

## 11. Success Criteria

**MVP (M0_FAST working):**
- ✅ Accepts CCP input
- ✅ Executes single unified reviewer
- ✅ Produces valid Council Run Log
- ✅ Chair synthesis with verdict

**Production Ready (All modes):**
- ✅ M0/M1/M2 mode selection automated
- ✅ Multi-seat execution (M1/M2)
- ✅ Independent model execution (M2)
- ✅ Evidence validation enforced
- ✅ CEO async approval workflow
- ✅ CLI integration complete
- ✅ Audit trail automated

**Success Metric:**
CEO no longer manually orchestrates council reviews (measured by time saved + review throughput)

---

## 12. Next Steps

1. ✅ Design document (this file) — IN PROGRESS
2. ⏳ CEO review of open questions (Q1-Q4)
3. ⏳ Implement CCP parser + mode selector
4. ⏳ Implement M0_FAST (MVP)
5. ⏳ Test + validate M0_FAST
6. ⏳ Extend to M1_STANDARD
7. ⏳ Extend to M2_FULL
8. ⏳ CLI integration
9. ⏳ Production deployment

**Estimated Timeline:** 3-5 days for full implementation

---

**END OF DESIGN DOCUMENT**  
**Status:** Draft v1.0 — Awaiting CEO review of open questions
