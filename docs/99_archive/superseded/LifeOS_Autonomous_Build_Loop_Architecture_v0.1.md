# LifeOS Autonomous Build Loop Architecture

**Version:** v0.1  
**Status:** Draft — For Council Review  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner) + GL (CEO)  
**Intended Placement:** `/LifeOS/docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.1.md`

---

## 1. Purpose & Scope

### 1.1 Purpose

This document defines the architecture for the **Autonomous Build Loop** — the mechanism by which LifeOS builds itself without manual orchestration by the CEO.

The goal is recursive automated construction: LifeOS executes its own backlog, producing improved versions of itself, which then build further improvements. The CEO's role shifts from router (copy-pasting between AI systems) to director (setting intent, reviewing escalations, approving governance changes).

### 1.2 In Scope

- Agent API Layer for model-agnostic LLM invocation (via OpenRouter)
- New operation types for the Tier-2 Orchestration Engine
- Mission types for the design→review→build→review→steward cycle
- OpenCode envelope expansion path (doc steward → builder)
- Governance bindings for autonomous operation

### 1.3 Out of Scope

- External "life" agents (trading, opportunity detection)
- COO Interface (CLI/UI) — covered separately in Tier-3
- Council Protocol changes — this document binds to existing protocol
- Detailed prompt engineering for agent roles — separate artifact

### 1.4 Success Criteria

The architecture is successful when:

1. A task from BACKLOG.md can progress from "TODO" to "DONE" without CEO intervention (except escalation)
2. All state transitions are logged, auditable, and reversible
3. Governance constraints are enforced automatically (envelope violations trigger escalation, not silent failure)
4. The system can operate while the CEO sleeps

---

## 2. Authority & Binding

### 2.1 Subordination

This document is subordinate to:

1. LifeOS Constitution v2.0 (Supreme)
2. Tier Definition Spec v1.1
3. Council Protocol v1.2
4. Governance Protocol v1.0

Conflicts with higher-level documents are resolved in favor of the higher-level document.

### 2.2 CEO Authority Invariant

> [!IMPORTANT]
> All judgment, discretion, and decision-making authority rests with the CEO.
> The Autonomous Build Loop executes tasks; it does not decide what to build or whether governance should change.
> Any ambiguity MUST escalate to CEO.

### 2.3 Governance Surface

Changes to the following require Council review before implementation:

- This architecture document
- Agent role definitions and prompts
- Envelope definitions for any agent
- Operation types added to orchestrator
- Mission type definitions

---

## 3. Design Principles

1. **Use what exists** — Build on Tier-2 orchestration infrastructure, existing packet schemas, existing governance framework. No greenfield rewrites.

2. **Model-agnostic** — LLM calls route through OpenRouter. No vendor lock-in. Model selection is configuration, not code.

3. **Staged handover** — Antigravity remains builder until OpenCode envelope is proven. Expansion requires evidence + council ruling.

4. **Fail-closed** — Envelope violations halt execution and escalate. Silent failures are forbidden.

5. **Evidence-first** — Every LLM call, every file write, every state transition is logged with deterministic identifiers.

6. **Reversibility** — Any mission can be rolled back to pre-execution state. Git is the ledger.

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CEO Interface                           │
│              (Task submission, Escalation review,               │
│               Approval queue, Status dashboard)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Mission Orchestrator                       │
│                 (Tier-2 Engine + New Operations)                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Mission Registry                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ design  │ │ review  │ │  build  │ │ steward │ ...   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Operation Types                        │   │
│  │  llm_call │ tool_invoke │ packet_route │ gate_check     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent API Layer                            │
│            (OpenRouter client, Role→Prompt mapping,             │
│             Deterministic logging, Retry/timeout)               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Tool Layer                                │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ OpenCode  │ │    Git    │ │  Pytest   │ │Filesystem │       │
│  │ (Builder) │ │           │ │           │ │           │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Governance Layer                             │
│         (Envelope checks, Escalation triggers,                  │
│          Audit log, Packet validation)                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Persistence Layer                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                     │
│  │  SQLite   │ │    Git    │ │  Packets  │                     │
│  │  (State)  │ │  (Ledger) │ │ (Artifacts)│                    │
│  └───────────┘ └───────────┘ └───────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Component Specifications

### 5.1 Agent API Layer

**Purpose:** Provide a model-agnostic interface for invoking LLMs with role-specific prompts.

**Location:** `runtime/agents/api.py`

**Interface:**

```python
@dataclass
class AgentCall:
    role: str                    # e.g., "designer", "reviewer", "builder"
    packet: dict                 # Input packet (validated against schema)
    model: str = "auto"          # Model identifier or "auto" for default
    temperature: float = 0.0     # Determinism by default
    max_tokens: int = 8192

@dataclass  
class AgentResponse:
    call_id: str                 # UUID for tracing
    role: str
    model_used: str              # Actual model that responded
    content: str                 # Raw response
    packet: Optional[dict]       # Parsed output packet (if valid)
    usage: dict                  # Token counts
    latency_ms: int
    timestamp: str               # ISO8601

def call_agent(call: AgentCall) -> AgentResponse:
    """
    Invoke an LLM via OpenRouter with role-specific system prompt.
    
    Raises:
        EnvelopeViolation: If role is not in allowed set
        AgentTimeoutError: If call exceeds timeout
        AgentResponseInvalid: If response fails packet schema validation
    """
```

**OpenRouter Integration:**

- Base URL: `https://openrouter.ai/api/v1`
- Authentication: `OPENROUTER_API_KEY` environment variable
- Model selection: Configuration file maps roles to preferred models
- Fallback: If preferred model unavailable, use fallback chain

**Role→Prompt Mapping:**

System prompts for each role are stored in `config/agent_roles/`:

```
config/agent_roles/
├── designer.md
├── reviewer_architect.md
├── reviewer_alignment.md
├── reviewer_risk.md
├── reviewer_governance.md
├── builder.md
├── steward.md
└── cso.md
```

Each file contains the system prompt for that role. The Agent API Layer reads these at startup and caches them.

**Logging Contract:**

Every call produces a log entry in `logs/agent_calls/`:

```yaml
call_id: "abc123"
timestamp: "2026-01-08T10:30:00Z"
role: "designer"
model_requested: "auto"
model_used: "anthropic/claude-3-sonnet"
input_packet_hash: "sha256:..."
input_tokens: 1234
output_tokens: 567
latency_ms: 2340
output_packet_hash: "sha256:..."
status: "success"  # or "error", "timeout", "invalid_response"
```

### 5.2 Operation Types

**Purpose:** Extend the Tier-2 Orchestration Engine with operations that can call agents and tools.

**Location:** `runtime/orchestration/operations.py`

**New Operation Types:**

| Operation | Description | Envelope Constraints |
|-----------|-------------|---------------------|
| `llm_call` | Invoke Agent API Layer | Role must be in allowed set; budget check |
| `tool_invoke` | Call external tool (git, pytest, OpenCode) | Tool must be in allowed set; path constraints |
| `packet_route` | Transform output packet to input packet for next step | Schema validation required |
| `gate_check` | Validate precondition before proceeding | Fail-closed on violation |
| `escalate` | Halt workflow and notify CEO | Always allowed |

**Operation Execution Model:**

```python
@dataclass
class OperationSpec:
    type: str                    # llm_call, tool_invoke, etc.
    params: dict                 # Operation-specific parameters
    envelope: dict               # Constraints for this operation

@dataclass
class OperationResult:
    operation_id: str
    type: str
    status: str                  # "success", "failed", "escalated"
    output: Any                  # Operation-specific output
    evidence: dict               # Hashes, logs, timing

def execute_operation(spec: OperationSpec, ctx: ExecutionContext) -> OperationResult:
    """
    Execute a single operation within the orchestrator.
    
    Raises:
        EnvelopeViolation: If operation exceeds its envelope
        OperationFailed: If operation fails (will trigger rollback consideration)
    """
```

**Integration with Existing Engine:**

The existing `engine.py` dispatches based on `step.kind`. Currently supports:
- `runtime` → executes `noop` or `fail`
- `human` → pass-through marker

Extended to support:
- `runtime` → dispatches to operation executor based on `payload.operation`

### 5.3 Mission Types

**Purpose:** Define the workflow templates for the autonomous build loop.

**Location:** `runtime/orchestration/missions/`

**Mission: `design`**

Transforms a task specification into a BUILD_PACKET.

```yaml
mission: design
inputs:
  - task_spec: str              # Task description from backlog
  - context_refs: list[str]     # Relevant documents to include
outputs:
  - build_packet: BUILD_PACKET
steps:
  - id: gather_context
    kind: runtime
    operation: tool_invoke
    params:
      tool: filesystem
      action: read_files
      paths: "{{context_refs}}"
  - id: design
    kind: runtime
    operation: llm_call
    params:
      role: designer
      input_packet:
        type: CONTEXT_RESPONSE_PACKET
        task: "{{task_spec}}"
        context: "{{steps.gather_context.output}}"
  - id: validate_output
    kind: runtime
    operation: gate_check
    params:
      schema: BUILD_PACKET
      data: "{{steps.design.output.packet}}"
```

**Mission: `review`**

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).

```yaml
mission: review
inputs:
  - subject_packet: dict        # The packet to review
  - review_type: str            # "build_review" or "output_review"
outputs:
  - verdict: str                # "approved", "fix_required", "rejected"
  - council_decision: dict
steps:
  - id: prepare_ccp
    kind: runtime
    operation: packet_route
    params:
      transform: to_council_context_pack
      input: "{{subject_packet}}"
  - id: run_seats
    kind: runtime
    operation: llm_call
    params:
      role: reviewer_{{seat}}
      input_packet: "{{steps.prepare_ccp.output}}"
    for_each:
      seat: [architect, alignment, risk, governance]
  - id: synthesize
    kind: runtime
    operation: llm_call
    params:
      role: council_chair
      input_packet:
        seat_outputs: "{{steps.run_seats.outputs}}"
  - id: validate_decision
    kind: runtime
    operation: gate_check
    params:
      schema: COUNCIL_APPROVAL_PACKET
      data: "{{steps.synthesize.output.packet}}"
```

**Mission: `build`**

Invokes builder (OpenCode) with approved BUILD_PACKET.

```yaml
mission: build
inputs:
  - build_packet: BUILD_PACKET
  - approval: COUNCIL_APPROVAL_PACKET
outputs:
  - review_packet: REVIEW_PACKET
preconditions:
  - approval.verdict == "approved"
steps:
  - id: check_envelope
    kind: runtime
    operation: gate_check
    params:
      check: builder_envelope
      scope: "{{build_packet.payload.scope}}"
  - id: invoke_builder
    kind: runtime
    operation: tool_invoke
    params:
      tool: opencode
      action: execute_build
      instruction: "{{build_packet}}"
  - id: collect_evidence
    kind: runtime
    operation: tool_invoke
    params:
      tool: git
      action: diff_stat
  - id: package_output
    kind: runtime
    operation: packet_route
    params:
      transform: to_review_packet
      build_output: "{{steps.invoke_builder.output}}"
      evidence: "{{steps.collect_evidence.output}}"
```

**Mission: `steward`**

Commits approved changes to repository.

```yaml
mission: steward
inputs:
  - review_packet: REVIEW_PACKET
  - approval: COUNCIL_APPROVAL_PACKET
outputs:
  - commit_hash: str
preconditions:
  - approval.verdict == "approved"
steps:
  - id: check_envelope
    kind: runtime
    operation: gate_check
    params:
      check: steward_envelope
      paths: "{{review_packet.payload.artifacts_produced}}"
  - id: stage_changes
    kind: runtime
    operation: tool_invoke
    params:
      tool: git
      action: add
      paths: "{{review_packet.payload.artifacts_produced}}"
  - id: commit
    kind: runtime
    operation: tool_invoke
    params:
      tool: git
      action: commit
      message: "{{review_packet.mission_name}}: {{review_packet.summary}}"
  - id: record_completion
    kind: runtime
    operation: tool_invoke
    params:
      tool: filesystem
      action: update_state
      file: LIFEOS_STATE.md
      mark_done: "{{review_packet.mission_name}}"
```

**Mission: `autonomous_build_cycle`**

Composes the above into a single end-to-end workflow.

```yaml
mission: autonomous_build_cycle
inputs:
  - task_spec: str
  - context_refs: list[str]
outputs:
  - commit_hash: str
  - cycle_report: dict
steps:
  - id: design
    kind: mission
    mission: design
    params:
      task_spec: "{{task_spec}}"
      context_refs: "{{context_refs}}"
  - id: review_design
    kind: mission
    mission: review
    params:
      subject_packet: "{{steps.design.output.build_packet}}"
      review_type: build_review
  - id: gate_design_approval
    kind: runtime
    operation: gate_check
    params:
      condition: "{{steps.review_design.output.verdict}} == 'approved'"
      on_fail: escalate
  - id: build
    kind: mission
    mission: build
    params:
      build_packet: "{{steps.design.output.build_packet}}"
      approval: "{{steps.review_design.output.council_decision}}"
  - id: review_output
    kind: mission
    mission: review
    params:
      subject_packet: "{{steps.build.output.review_packet}}"
      review_type: output_review
  - id: gate_output_approval
    kind: runtime
    operation: gate_check
    params:
      condition: "{{steps.review_output.output.verdict}} == 'approved'"
      on_fail: escalate
  - id: steward
    kind: mission
    mission: steward
    params:
      review_packet: "{{steps.build.output.review_packet}}"
      approval: "{{steps.review_output.output.council_decision}}"
```

### 5.4 OpenCode Envelope Expansion

**Current Envelope (Phase 2 Doc Steward):**

Per `OpenCode_First_Stewardship_Policy_v1.1.md`:

- CAN: Modify `.md` files in `docs/` (excluding protected roots)
- CAN: Add `.md` files to `artifacts/review_packets/`
- CANNOT: Modify `docs/00_foundations/`, `docs/01_governance/`, `scripts/`, `config/`
- CANNOT: Delete, rename, move, copy files
- CANNOT: Modify non-`.md` files

**Target Envelope (Builder):**

To enable autonomous build loop, OpenCode needs:

- CAN: Create/modify `.py` files in `coo/`, `runtime/`, `tests/`
- CAN: Create/modify `.yaml` and `.json` config files in `config/`
- CAN: Run `pytest`
- CANNOT: Modify governance surfaces (`docs/00_foundations/`, `docs/01_governance/`)
- CANNOT: Modify its own envelope definition
- CANNOT: Modify `scripts/opencode_gate_policy.py` (self-modification protection)

**Expansion Path:**

| Phase | Envelope Addition | Prerequisite |
|-------|-------------------|--------------|
| Current | Doc steward (`.md` in `docs/`) | Active |
| Phase 3a | Test execution (`pytest`) | Council ruling |
| Phase 3b | Code creation (`coo/`, `runtime/`, `tests/`) | Phase 3a stable + Council ruling |
| Phase 3c | Config modification (`config/`) | Phase 3b stable + Council ruling |

Each expansion requires:
1. Evidence of stable operation at current phase
2. Council review with full seat coverage (M2_FULL)
3. CEO sign-off
4. 48-hour observation period before next expansion

### 5.5 Governance Bindings

**Escalation Triggers (Automatic):**

| Condition | Action |
|-----------|--------|
| Envelope violation detected | HALT + escalate to CEO |
| Council verdict is "rejected" | HALT + escalate to CEO |
| Council verdict is "fix_required" after 2 cycles | HALT + escalate to CEO |
| Budget threshold exceeded | HALT + escalate to CEO |
| Test failure after retry | HALT + escalate to CEO |
| Any modification to governance surface | HALT + escalate to CEO |

**Approval Queue:**

Escalated items enter the CEO approval queue. The queue is:
- Persistent (SQLite)
- Ordered by escalation timestamp
- Viewable via CLI (`coo queue list`)
- Actionable via CLI (`coo queue approve <id>`, `coo queue reject <id>`)

**Audit Trail:**

Every mission execution produces:
- Mission log (SQLite: `mission_runs` table)
- Agent call logs (`logs/agent_calls/`)
- Git commits (feature branch per mission)
- Packets (artifacts directory)

Retention: Indefinite for mission logs and git history. 30 days for agent call logs (configurable).

---

## 6. Implementation Phases

### Phase 1: Agent API Layer (Est. 3-5 days)

**Deliverables:**
- `runtime/agents/api.py` — OpenRouter client with role dispatch
- `runtime/agents/logging.py` — Deterministic call logging
- `config/agent_roles/*.md` — Initial role prompts (designer, reviewer seats, builder)
- `config/models.yaml` — Role→model mapping
- Unit tests for API layer
- Integration test with live OpenRouter call

**Exit Criteria:**
- `call_agent()` successfully invokes OpenRouter
- Response is logged deterministically
- Role prompts load correctly
- Tests pass

### Phase 2: Operations (Est. 3-5 days)

**Deliverables:**
- `runtime/orchestration/operations.py` — Operation executor
- Extensions to `engine.py` for new operation dispatch
- `llm_call`, `tool_invoke`, `packet_route`, `gate_check` implementations
- Unit tests for each operation type
- Integration tests with mock tools

**Exit Criteria:**
- Engine executes workflows with new operation types
- Envelope checks trigger violations correctly
- Operations log evidence
- Tests pass

### Phase 3: Mission Types (Est. 5-7 days)

**Deliverables:**
- `runtime/orchestration/missions/design.py`
- `runtime/orchestration/missions/review.py`
- `runtime/orchestration/missions/build.py`
- `runtime/orchestration/missions/steward.py`
- `runtime/orchestration/missions/autonomous_build_cycle.py`
- Mission registry updates
- End-to-end test with mock builder

**Exit Criteria:**
- Each mission executes in isolation
- `autonomous_build_cycle` composes correctly
- Escalation triggers work
- Tests pass

### Phase 4: OpenCode Builder Integration (Est. 3-5 days)

**Deliverables:**
- `tool_invoke` implementation for OpenCode
- Envelope expansion proposal (Council review packet)
- Integration tests with real OpenCode execution
- Observation period results

**Exit Criteria:**
- OpenCode executes BUILD_PACKETs
- Output matches expected REVIEW_PACKET structure
- Envelope violations are caught
- Council ruling obtained for Phase 3a envelope

### Phase 5: End-to-End Validation (Est. 3-5 days)

**Deliverables:**
- Execute real backlog item through full cycle
- Document friction points and failures
- Fix critical issues
- Produce Milestone Report

**Exit Criteria:**
- One task completes TODO→DONE without CEO routing
- Escalation works (test by injecting failure)
- Audit trail is complete and useful
- CEO can review and approve via queue

---

## 7. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenRouter API instability | Medium | High | Implement retry with backoff; fallback model chain |
| LLM produces invalid packets | High | Medium | Strict schema validation; retry once; escalate on second failure |
| Runaway token spend | Medium | High | Budget caps per mission; daily ceiling; alerts |
| OpenCode envelope too restrictive | Medium | Medium | Staged expansion; measure what's blocked |
| Council automation reduces quality | Medium | High | Compare automated vs manual council verdicts; tune prompts |
| Self-modification escape | Low | Critical | Hardcoded protection for envelope definitions; no self-modification path |

---

## 8. Open Questions (For CEO Decision)

1. **Model selection:** Default model for each role? (Recommendation: Claude Sonnet for speed, Opus for design/architecture seats)

2. **Budget ceiling:** Daily token/cost limit before automatic halt? (Recommendation: $10/day initial ceiling)

3. **Council seat reduction:** Full 9-seat council for every review, or reduced set for low-risk changes? (Recommendation: Start with 4-seat for build reviews: Architect, Alignment, Risk, Governance)

4. **Observation period:** 48 hours between envelope expansions, or different cadence? (Recommendation: 48 hours minimum, extend if issues found)

5. **First workload:** Which backlog item to use for Phase 5 validation? (Recommendation: A bounded, low-governance-risk item like "Register `run_tests` in registry.py")

---

## 9. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| OpenRouter API access | Required | Need API key configured |
| OpenCode doc steward | Active | Current envelope sufficient for Phase 1-3 |
| Council Protocol v1.2 | Active | Binds council automation |
| Tier-2 Orchestration Engine | Active | Foundation for operations |
| Packet schemas v1.2 | Active | Contract layer |

---

## 10. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-08 | Claude + GL | Initial draft for council review |

---

**END OF DOCUMENT**
