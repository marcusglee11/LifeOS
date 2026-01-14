# LifeOS Autonomous Build Loop Architecture

**Version:** v0.3  
**Status:** Draft — Council Re-Review Fixes Integrated  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner) + GL (CEO)  
**Intended Placement:** `/LifeOS/docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md`

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
- **[v0.2]** Governance surface protection and self-modification locks
- **[v0.2]** Envelope enforcement mechanisms
- **[v0.2]** Determinism, replay, and atomicity semantics
- **[v0.2]** Run control, crash recovery, and kill switch
- **[v0.3]** Governance baseline creation/update ceremony
- **[v0.3]** Compensation verification and post-state checks
- **[v0.3]** Canonical JSON specification and replay equivalence
- **[v0.3]** Kill-switch/lock ordering and mid-run behavior

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
5. **[v0.2]** Governance surfaces are tamper-evident and runtime-verified
6. **[v0.2]** Missions are atomic with deterministic rollback

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

### 2.3 Governance Surface Classification

**[v0.2 — P0.1]** The following artifacts are classified as **governance-controlled surfaces**:

| Category | Artifacts | Modification Authority |
|----------|-----------|----------------------|
| **Role Prompts** | `config/agent_roles/*.md` | Council ruling required |
| **Model Mapping** | `config/models.yaml` | Council ruling required |
| **Envelope Policy** | `scripts/opencode_gate_policy.py` | Council ruling required |
| **Packet Transforms** | `runtime/orchestration/transforms/*.py` | Council ruling required |
| **This Document** | `docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_*.md` | Council ruling required |
| **Agent Constitutions** | `GEMINI.md`, `CLAUDE.md`, agent constitutions | Council ruling required |
| **Protected Doc Roots** | `docs/00_foundations/`, `docs/01_governance/` | Per existing policy |

**Runtime Integrity Requirement (P0.1):**

At mission start, the orchestrator MUST:

1. Compute SHA-256 hashes for all governance-controlled artifacts listed above.
2. Compare against the **approved baseline manifest** stored at `config/governance_baseline.yaml`.
3. If ANY mismatch is detected: **HALT immediately** and escalate to CEO with:
   - List of mismatched files
   - Expected vs actual hashes
   - Timestamp of detection
4. The mission MUST NOT proceed until integrity is verified.

```yaml
# config/governance_baseline.yaml (example structure)
baseline_version: "2026-01-08T10:00:00Z"
approved_by: "CEO"
council_ruling_ref: "Council_Ruling_<ID>"
artifacts:
  - path: "config/agent_roles/designer.md"
    sha256: "abc123..."
  - path: "config/agent_roles/builder.md"
    sha256: "def456..."
  - path: "scripts/opencode_gate_policy.py"
    sha256: "789abc..."
  # ... all governance surfaces
```

### 2.4 Self-Modification Protection

**[v0.2 — P0.1]** The following self-modification protections are **hardcoded and cannot be overridden**:

1. **Builder/Steward agents CANNOT modify** any artifact in §2.3 regardless of mission instructions.
2. **No agent may modify its own envelope definition** — this is enforced at the `tool_invoke` operation level.
3. **No agent may modify `scripts/opencode_gate_policy.py`** — this file enforces envelope boundaries.
4. **No agent may modify `config/governance_baseline.yaml`** — this file validates integrity.

These protections are implemented as a hardcoded denylist in `runtime/governance/self_mod_protection.py` (to be created), which is checked BEFORE any filesystem or git operation is permitted.

**Escalation Note:** If a future mission requires modification of governance surfaces, a new role with higher clearance must be defined via Council ruling. This architecture does not grant such authority.

### 2.5 Governance Baseline Ceremony [v0.3 — P0.1]

**[v0.3 — P0.1]** The governance baseline (`config/governance_baseline.yaml`) is the single source of truth for approved governance surface hashes. This section defines the operable, auditable, fail-closed creation and update procedures.

#### 2.5.1 Initial Baseline Creation

The governance baseline is created exactly once per system initialization:

**Prerequisites:**
1. CEO explicitly authorizes baseline creation
2. All governance surface files exist and are reviewed
3. No autonomous operations are running

**Procedure:**

```python
def create_initial_baseline(
    governance_surfaces: List[str],
    approver: str,  # Must be "CEO"
    council_ruling_ref: Optional[str]
) -> BaselineResult:
    """
    Create initial governance baseline.
    
    Steps:
    1. Verify approver == "CEO" (fail if not)
    2. For each path in governance_surfaces:
       a. Verify file exists
       b. Normalize path: os.path.normpath(os.path.relpath(path, repo_root))
       c. Compute SHA-256 of file contents (UTF-8, no BOM normalization)
    3. Construct baseline document:
       - baseline_version: ISO8601 timestamp
       - approved_by: approver
       - council_ruling_ref: (if provided)
       - hash_algorithm: "SHA-256"
       - path_normalization: "relpath_from_repo_root"
       - artifacts: list of {path, sha256}
    4. Write to config/governance_baseline.yaml
    5. Compute SHA-256 of baseline file itself
    6. Create Review Packet with:
       - Full baseline content
       - All input file hashes
       - Baseline file hash
    7. Require CEO sign-off on Review Packet
    8. Git commit with message: "GOVERNANCE: Initial baseline created"
    """
```

**Required Evidence:**
- List of all governance surfaces with hashes
- CEO signature/approval record
- Git commit hash of baseline creation
- Review Packet path

**Fail-Closed Behavior:**
- If CEO approval not obtained: HALT, baseline not created
- If any governance surface file missing: HALT, escalate
- If write to baseline file fails: HALT, escalate

#### 2.5.2 Baseline Update Procedure

The governance baseline is updated ONLY when Council approves modifications to governance surfaces:

**Trigger:** Council ruling approves change to one or more governance surfaces

**Procedure:**

```python
def update_governance_baseline(
    council_ruling_ref: str,
    modified_surfaces: List[str],
    baseline_commit: str  # Git commit before modification
) -> UpdateResult:
    """
    Update governance baseline after council-approved change.
    
    Inputs:
    - council_ruling_ref: Reference to Council ruling authorizing change
    - modified_surfaces: List of governance surface paths modified
    - baseline_commit: Git HEAD at time change was approved
    
    Steps:
    1. Load current baseline from config/governance_baseline.yaml
    2. Verify baseline_commit matches current HEAD (abort if drift detected)
    3. For each path in modified_surfaces:
       a. Verify path is listed in §2.3 governance surfaces
       b. Verify file exists
       c. Normalize path per §2.5.1
       d. Compute new SHA-256 hash
    4. Create updated baseline:
       - Increment baseline_version timestamp
       - Update approved_by: "CEO" (still required)
       - Add council_ruling_ref
       - Update artifacts list with new hashes
       - Preserve hashes for unmodified surfaces
    5. Write updated baseline
    6. Create Review Packet with:
       - Diff of old vs new baseline
       - Council ruling reference
       - All modified file hashes
    7. Require CEO sign-off
    8. Git commit with message: "GOVERNANCE: Baseline updated per <council_ruling_ref>"
    
    Outputs:
    - Updated config/governance_baseline.yaml
    - Review Packet in artifacts/review_packets/
    - Git commit hash
    """
```

**Commit Requirements:**
- Commit message MUST reference council ruling
- Commit MUST include both the modified governance surface(s) AND the updated baseline
- No other changes may be included in the commit

#### 2.5.3 Runtime Baseline Mismatch Behavior

**[v0.3 — P0.1]** When orchestrator detects baseline mismatch at mission start:

```python
def handle_baseline_mismatch(
    mismatched_files: List[MismatchRecord],
    expected_baseline: BaselineManifest,
    actual_hashes: Dict[str, str]
) -> Never:  # This function always escalates, never returns normally
    """
    Handle governance baseline mismatch.
    
    This function NEVER auto-updates the baseline.
    This function NEVER proceeds with the mission.
    This function ALWAYS escalates to CEO.
    
    Steps:
    1. Create evidence bundle:
       - List of mismatched files with expected vs actual hashes
       - Current git status
       - Current HEAD commit
       - Timestamp of detection
    2. Write evidence to logs/baseline_mismatches/<timestamp>/
    3. Create escalation record in SQLite
    4. HALT all autonomous operations
    5. Notify CEO with:
       - Mismatch summary
       - Evidence bundle path
       - Instructions for resolution
    
    Resolution paths (CEO action only):
    - Option A: Revert unauthorized changes, clear escalation
    - Option B: Authorize changes via Council review, update baseline per §2.5.2
    """
```

> [!CAUTION]
> **The orchestrator MUST NEVER auto-update the governance baseline.**
> Baseline updates require explicit CEO authorization and Council ruling reference.
> Any attempt by an agent to propose auto-update logic is a governance violation.

---

## 3. Design Principles

1. **Use what exists** — Build on Tier-2 orchestration infrastructure, existing packet schemas, existing governance framework. No greenfield rewrites.

2. **Model-agnostic** — LLM calls route through OpenRouter. No vendor lock-in. Model selection is configuration, not code.

3. **Staged handover** — Antigravity remains builder until OpenCode envelope is proven. Expansion requires evidence + council ruling.

4. **Fail-closed** — Envelope violations halt execution and escalate. Silent failures are forbidden.

5. **Evidence-first** — Every LLM call, every file write, every state transition is logged with deterministic identifiers.

6. **Reversibility** — Any mission can be rolled back to pre-execution state. Git is the ledger.

7. **[v0.2] Determinism** — Decision-affecting identifiers are deterministic; UUID/timestamps are metadata only.

8. **[v0.2] Atomicity** — Missions either complete fully or roll back completely; no partial states.

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
│                   Run Controller [v0.2]                         │
│         (Kill switch, Lock acquisition, State recovery)         │
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
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Mission Journal [v0.2]                   │   │
│  │        (Operation receipts, Compensation log)            │   │
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
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Envelope Enforcer [v0.2]                    │   │
│  │     (Path containment, Allowlist/Denylist, Symlink)      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Persistence Layer                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  SQLite   │ │    Git    │ │  Packets  │ │  Journal  │       │
│  │  (State)  │ │  (Ledger) │ │ (Artifacts)│ │  [v0.2]   │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
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
    call_id: str                 # Deterministic ID (see §5.1.3)
    call_id_audit: str           # UUID for audit/correlation (metadata only)
    role: str
    model_used: str              # Actual model that responded (pinned version)
    model_version: str           # Provider's most specific version identifier
    content: str                 # Raw response
    packet: Optional[dict]       # Parsed output packet (if valid)
    usage: dict                  # Token counts
    latency_ms: int
    timestamp: str               # ISO8601 (metadata only — MUST NOT affect decisions)

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

> [!CAUTION]
> **[v0.2 — P0.1]** Role prompt files are governance-controlled surfaces.
> Agent API Layer MUST verify prompt file hashes against `config/governance_baseline.yaml` before loading.
> Hash mismatch → HALT + escalate.

#### 5.1.1 Model Pinning Requirements [v0.2 — P0.3]

**[v0.2 — P0.3]** To support deterministic replay:

1. **Use provider's most specific version identifier**: When invoking OpenRouter, request the most specific model version available (e.g., `anthropic/claude-3-sonnet-20240229` not just `anthropic/claude-3-sonnet`).

2. **Record version in evidence**: The `AgentResponse.model_version` field MUST contain the exact version string returned by the provider.

3. **Version mismatch handling**: If a replay attempt uses a different model version than the original, the replay MUST be flagged with `replay_status: "version_drift"` in evidence.

#### 5.1.2 Replay Fixture Mechanism [v0.2 — P0.3]

**[v0.2 — P0.3]** For deterministic testing:

1. **Response cache**: All agent call responses are cached to `logs/agent_calls/cache/` keyed by `call_id_deterministic`.

2. **Fixture format**:
   ```yaml
   call_id_deterministic: "sha256:abc123..."
   role: "designer"
   model_version: "anthropic/claude-3-sonnet-20240229"
   input_packet_hash: "sha256:..."
   prompt_hash: "sha256:..."
   response_content: "..." 
   response_packet: {...}
   ```

3. **Test mode**: When `LIFEOS_TEST_MODE=replay` is set, Agent API Layer MUST:
   - Look up `call_id_deterministic` in cache
   - If found: return cached response without invoking LLM
   - If not found: fail with `ReplayMissError` (do not fall through to live call)

#### 5.1.3 Deterministic Identifiers [v0.2 — P0.3]

**[v0.2 — P0.3]** Decision-affecting identifiers MUST be deterministic:

```python
def compute_run_id_deterministic(
    mission_spec: dict,
    inputs_hash: str,
    governance_surface_hashes: dict,
    code_version_id: str  # git commit hash
) -> str:
    """
    Compute deterministic run identifier.
    
    run_id_deterministic = sha256(
        canonical_json(mission_spec) +
        inputs_hash +
        canonical_json(sorted(governance_surface_hashes.items())) +
        code_version_id
    )
    """

def compute_call_id_deterministic(
    run_id_deterministic: str,
    role: str,
    prompt_hash: str,
    packet_hash: str
) -> str:
    """
    Compute deterministic call identifier.
    
    call_id_deterministic = sha256(
        run_id_deterministic +
        role +
        prompt_hash +
        packet_hash
    )
    """
```

**UUID and Timestamp Policy:**
- `call_id_audit` (UUID) and `timestamp` fields are **audit metadata only**.
- These values MUST NOT be used in any decision logic, branching, or packet routing.
- They exist solely for human correlation and log ordering.

**Logging Contract:**

Every call produces a log entry in `logs/agent_calls/`:

```yaml
call_id_deterministic: "sha256:..."
call_id_audit: "550e8400-e29b-41d4-a716-446655440000"
timestamp: "2026-01-08T10:30:00Z"
role: "designer"
model_requested: "auto"
model_used: "anthropic/claude-3-sonnet-20240229"
model_version: "20240229"
input_packet_hash: "sha256:..."
prompt_hash: "sha256:..."
input_tokens: 1234
output_tokens: 567
latency_ms: 2340
output_packet_hash: "sha256:..."
status: "success"  # or "error", "timeout", "invalid_response"
prev_log_hash: "sha256:..."  # Hash chain (P1.2)
```

#### 5.1.4 Canonical JSON and Replay Equivalence [v0.3 — P0.3]

**[v0.3 — P0.3]** This section defines exact specifications for deterministic serialization and replay verification.

**canonical_json() Specification:**

```python
def canonical_json(obj: Any) -> bytes:
    """
    [v0.3 — P0.3] Produce canonical JSON for deterministic hashing.
    
    Exact specification:
    1. Encoding: UTF-8, no BOM
    2. Whitespace: None (no spaces after colons or commas, no newlines)
    3. Key ordering: Lexicographically sorted by Unicode code points (stable)
    4. Array ordering: Preserved as-is (arrays are order-sensitive)
    5. Numeric formatting:
       - Integers: No leading zeros, no decimal point
       - Floats: Shortest representation that round-trips correctly
       - No trailing zeros after decimal point
       - Scientific notation only if shorter (e.g., 1e10)
    6. String escaping: Only escape required characters (", \, control chars)
    7. Unicode: No unnecessary escaping (literal UTF-8 characters)
    8. Boolean/null: lowercase (true, false, null)
    
    Implementation (Python):
        import json
        return json.dumps(
            obj,
            separators=(',', ':'),
            sort_keys=True,
            ensure_ascii=False
        ).encode('utf-8')
    """
```

**Replay Equivalence Rules:**

Two runs are considered **replay-equivalent** if and only if their decision-bearing fields match.

**Metadata Fields (EXCLUDED from equivalence):**

These fields are audit/correlation only and MUST NOT affect decision logic:

| Field | Location | Purpose |
|-------|----------|---------|
| `call_id_audit` | AgentResponse | UUID for log correlation |
| `operation_id_audit` | OperationResult | UUID for log correlation |
| `timestamp` | All logs | Human readability, ordering |
| `latency_ms` | AgentResponse | Performance metric |
| `input_tokens` | AgentResponse | Cost metric |
| `output_tokens` | AgentResponse | Cost metric |
| `started_at` | MissionJournalEntry | Timing metadata |
| `completed_at` | MissionJournalEntry | Timing metadata |

**Decision-Bearing Fields (INCLUDED in equivalence):**

These fields MUST match for replay equivalence:

| Field | Location | Role |
|-------|----------|------|
| `run_id_deterministic` | Mission | Primary mission identity |
| `call_id_deterministic` | AgentResponse | Primary call identity |
| `prompt_hash` | AgentCall | Input to model |
| `input_packet_hash` | AgentCall | Input data |
| `output_packet_hash` | AgentResponse | Model output |
| `governance_baseline_hash` | Mission | System state |
| `model_used` | AgentResponse | Model identity |
| `model_version` | AgentResponse | Model version |
| `pre_state_hash` | OperationReceipt | Pre-operation state |
| `post_state_hash` | OperationReceipt | Post-operation state |
| `baseline_commit` | MissionRun | Git state |

**Replay Verification:**

```python
def verify_replay_equivalence(
    original_run: RunRecord,
    replay_run: RunRecord
) -> ReplayVerificationResult:
    """
    [v0.3 — P0.3] Verify replay matches original run.
    
    1. Compare run_id_deterministic (must match exactly)
    2. For each call in order:
       a. Compare call_id_deterministic (must match)
       b. Compare decision-bearing fields (must match)
       c. Ignore metadata fields
    3. If model_version differs: flag as "version_drift" (not failure)
    4. Return ReplayVerificationResult with:
       - equivalent: bool
       - drift_type: Optional[str] (e.g., "version_drift")
       - mismatches: List[FieldMismatch]
    """
```

**Hash Chain Genesis:**

The hash chain for logs MUST have a defined genesis:

```python
HASH_CHAIN_GENESIS = hashlib.sha256(b"LIFEOS_LOG_CHAIN_GENESIS_V1").hexdigest()
# = "a7d9e1f2c3b4a5968798..." (fixed constant)

# First entry in any log chain:
first_entry.prev_log_hash = HASH_CHAIN_GENESIS
```

This ensures the chain is anchored to a known constant, not an empty string.

#### 5.1.5 Model "auto" Semantics [v0.3 — P1.2]

**[v0.3 — P1.2]** When `model="auto"` is specified, model selection is deterministic:

**Priority-Ordered Model List:**

The `config/models.yaml` file defines deterministic fallback chains per role:

```yaml
# config/models.yaml
model_selection:
  default_chain:
    - "anthropic/claude-3-sonnet-20240229"
    - "anthropic/claude-3-haiku-20240307"
    - "openai/gpt-4-turbo-preview"
    
  role_overrides:
    designer:
      - "anthropic/claude-3-opus-20240229"
      - "anthropic/claude-3-sonnet-20240229"
    reviewer_architect:
      - "anthropic/claude-3-opus-20240229"
      - "anthropic/claude-3-sonnet-20240229"
    builder:
      - "anthropic/claude-3-sonnet-20240229"
      - "anthropic/claude-3-haiku-20240307"
```

**Resolution Logic:**

```python
def resolve_model_auto(role: str, models_config: dict) -> Tuple[str, str]:
    """
    [v0.3 — P1.2] Resolve "auto" to specific model deterministically.
    
    1. If role in role_overrides: use that chain
    2. Otherwise: use default_chain
    3. Try each model in order until one is available
    4. Return (selected_model, selection_reason)
    
    selection_reason is one of:
    - "primary": First model in chain was available
    - "fallback_N": Nth fallback was used (N = 1, 2, ...)
    - "error": No model available (escalate)
    """
```

**Logging Requirement:**

When `model="auto"` is used, the log MUST include:

```yaml
model_requested: "auto"
model_used: "anthropic/claude-3-sonnet-20240229"
model_selection_reason: "primary"  # or "fallback_1", etc.
model_selection_chain: ["anthropic/claude-3-sonnet-20240229", "anthropic/claude-3-haiku-20240307"]
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
    operation_id: str            # Deterministic ID
    operation_id_audit: str      # UUID for audit (metadata only)
    type: str
    status: str                  # "success", "failed", "escalated"
    output: Any                  # Operation-specific output
    evidence: dict               # Hashes, logs, timing
    receipt: OperationReceipt    # [v0.2] For journaling

@dataclass
class OperationReceipt:
    """[v0.2 — P0.4, v0.3 — P0.2] Receipt for idempotency and rollback."""
    operation_id: str
    timestamp: str
    pre_state_hash: str          # Hash of affected state before operation
    post_state_hash: str         # Hash of affected state after operation
    compensation_type: CompensationType  # [v0.3] Enum, not freeform string
    compensation_command: str    # The actual command to execute
    idempotency_key: str         # For rerun detection
    compensation_verified: bool  # [v0.3] Whether compensation was verified


class CompensationType(Enum):
    """[v0.3 — P0.2] Validated compensation type enum."""
    NONE = "none"                # Read-only operation, no compensation needed
    GIT_CHECKOUT = "git_checkout"    # git checkout -- <path>
    GIT_RESET_HEAD = "git_reset_head"  # git reset HEAD
    GIT_RESET_SOFT = "git_reset_soft"  # git reset --soft HEAD~N
    GIT_RESET_HARD = "git_reset_hard"  # git reset --hard <commit>
    GIT_CLEAN = "git_clean"      # git clean -fd
    FILESYSTEM_DELETE = "fs_delete"  # Remove created file
    FILESYSTEM_RESTORE = "fs_restore"  # Restore from backup
    CUSTOM_VALIDATED = "custom"  # Must be in whitelist


# [v0.3 — P0.2] Validated command whitelist for CUSTOM_VALIDATED
COMPENSATION_COMMAND_WHITELIST = [
    "git checkout -- .",
    "git reset HEAD",
    "git reset --soft HEAD~1",
    "git reset --hard HEAD~1",
    "git clean -fd",
]


def execute_operation(spec: OperationSpec, ctx: ExecutionContext) -> OperationResult:
    """
    Execute a single operation within the orchestrator.
    
    [v0.2] Before execution:
    1. Check kill switch (§5.6)
    2. Verify envelope constraints (§5.2.1)
    3. Record pre-state hash
    
    [v0.2] After execution:
    4. Record post-state hash
    5. Write receipt to mission journal
    
    [v0.3] Compensation validation:
    6. Validate compensation_type is valid enum
    7. If CUSTOM_VALIDATED, verify command is in whitelist
    
    Raises:
        EnvelopeViolation: If operation exceeds its envelope
        OperationFailed: If operation fails (will trigger rollback consideration)
        KillSwitchActive: If STOP_AUTONOMY file detected
        InvalidCompensation: If compensation type/command not validated
    """
```

**Integration with Existing Engine:**

The existing `engine.py` dispatches based on `step.kind`. Currently supports:
- `runtime` → executes `noop` or `fail`
- `human` → pass-through marker

Extended to support:
- `runtime` → dispatches to operation executor based on `payload.operation`

#### 5.2.1 Envelope Enforcement Mechanism [v0.2 — P0.2]

**[v0.2 — P0.2]** Envelope constraints are enforced at runtime, not merely described:

**Authoritative Envelope Policy Source:**

1. **Source of truth**: `scripts/opencode_gate_policy.py`
2. **Policy version recording**: At mission start, record:
   - Policy file hash
   - Policy version string (from file header)
   - Timestamp of policy load
3. **Immutability during mission**: Policy MUST NOT be reloaded mid-mission.

**Path Containment Rules (for `tool_invoke` with filesystem/git):**

```python
def validate_path_access(requested_path: str, operation: str, envelope: dict) -> ValidationResult:
    """
    [v0.2 — P0.2] Strict path validation before any filesystem/git operation.
    
    Checks performed:
    1. realpath_containment: os.path.realpath(requested_path) MUST be within repo_root
    2. symlink_rejection: If envelope.reject_symlinks, reject any symlink in path
    3. allowlist_match: Path MUST match at least one pattern in envelope.allowed_paths
    4. denylist_exclusion: Path MUST NOT match any pattern in envelope.denied_paths
    5. toctou_mitigation: Re-validate path immediately before execution (no caching)
    
    Returns ValidationResult with:
    - allowed: bool
    - reason: str
    - evidence: dict (hashes, timestamps)
    """
```

**TOCTOU (Time-of-Check-Time-of-Use) Mitigation:**

1. **State snapshot**: Before batch operations, record git status hash.
2. **Re-check before execution**: Immediately before each write operation, re-validate:
   - Path still exists (or doesn't, as expected)
   - Path hasn't been modified since check
3. **Atomic operations**: Where possible, use atomic filesystem operations.
4. **Single-writer assumption**: Only one mission may execute at a time (enforced by run lock).

**Symlink Defense:**

```python
def check_symlink_safety(path: str) -> bool:
    """
    [v0.2 — P0.2] Reject symlinks where disallowed.
    
    1. Check if path itself is a symlink
    2. Check if any component of path is a symlink
    3. Resolve realpath and verify it's within allowed root
    """
```

#### 5.2.2 Compensation Verification [v0.3 — P0.2]

**[v0.3 — P0.2]** Compensation actions MUST be validated before execution AND verified after execution:

**Pre-Execution Validation:**

```python
def validate_compensation(
    compensation_type: CompensationType,
    compensation_command: str
) -> ValidationResult:
    """
    [v0.3 — P0.2] Validate compensation action before operation execution.
    
    1. Verify compensation_type is a valid CompensationType enum value
    2. If NONE: command must be empty or "none"
    3. If CUSTOM_VALIDATED: command MUST be in COMPENSATION_COMMAND_WHITELIST
    4. For all other types: command must match expected pattern for type
    
    Returns ValidationResult with:
    - valid: bool
    - reason: str (if invalid)
    """
```

**Post-Compensation Verification:**

After any compensation action is executed, the following checks are MANDATORY:

```python
def verify_compensation_success(
    expected_state: ExpectedRepoState,
    compensation_receipt: OperationReceipt
) -> VerificationResult:
    """
    [v0.3 — P0.2] Verify compensation restored expected state.
    
    Mandatory checks:
    1. git status --porcelain MUST return empty (no staged/unstaged changes)
    2. git ls-files --others --exclude-standard MUST return empty (no untracked files)
    3. git rev-parse HEAD MUST match expected_state.baseline_commit
    4. Hash of working tree files MUST match expected_state.pre_operation_hash
    
    Returns VerificationResult with:
    - success: bool
    - failures: List[str] (which checks failed)
    - evidence: dict (actual vs expected values)
    """

def post_compensation_checks(repo_root: str) -> Tuple[bool, dict]:
    """
    [v0.3 — P0.2] Concrete post-compensation check implementation.
    
    Executes:
    1. git_status_clean = (subprocess.run(
           ["git", "status", "--porcelain"], 
           capture_output=True
       ).stdout.strip() == b"")
    
    2. git_untracked_clean = (subprocess.run(
           ["git", "ls-files", "--others", "--exclude-standard"],
           capture_output=True
       ).stdout.strip() == b"")
    
    3. current_head = subprocess.run(
           ["git", "rev-parse", "HEAD"],
           capture_output=True
       ).stdout.strip().decode()
    
    Returns (all_clean: bool, evidence: dict)
    """
```

**Escalation on Verification Failure:**

> [!CAUTION]
> **If ANY post-compensation check fails, the orchestrator MUST:**
> 1. HALT immediately — no further missions may run
> 2. Create evidence bundle with all check outputs
> 3. Record escalation in SQLite with severity="critical"
> 4. Write lock file to prevent any autonomous restart
> 5. Notify CEO with detailed failure report

**Compensation Idempotency Requirement:**

All compensation actions MUST be idempotent:
- Running compensation twice must produce the same end state
- Compensation must record an OperationReceipt with `compensation_verified: true/false`
- If compensation itself fails: escalate immediately (do not retry)

### 5.3 Mission Types

**Purpose:** Define the workflow templates for the autonomous build loop.

**Location:** `runtime/orchestration/missions/`

#### 5.3.1 Mission YAML Schema [v0.2 — P1.3]

**[v0.2 — P1.3]** All mission definitions MUST conform to this schema:

```yaml
# Mission YAML Schema v1.0
mission_schema:
  type: object
  required:
    - mission
    - version
    - inputs
    - outputs
    - steps
  properties:
    mission:
      type: string
      description: "Unique mission type identifier"
    version:
      type: string
      pattern: "^\\d+\\.\\d+$"
      description: "Mission definition version"
    inputs:
      type: array
      items:
        type: object
        required: [name, type]
        properties:
          name: {type: string}
          type: {type: string}
          required: {type: boolean, default: true}
    outputs:
      type: array
      items:
        type: object
        required: [name, type]
        properties:
          name: {type: string}
          type: {type: string}
    preconditions:
      type: array
      items: {type: string}
      description: "Conditions that must be true before mission starts"
    steps:
      type: array
      items:
        type: object
        required: [id, kind]
        properties:
          id: {type: string}
          kind: {type: string, enum: [runtime, mission, human]}
          operation: {type: string}
          params: {type: object}
          envelope: {type: object}
          for_each: {type: object}
          compensation: {type: string, description: "How to undo this step"}
    envelope:
      type: object
      description: "Mission-level envelope constraints"
    timeout_seconds:
      type: integer
      default: 3600
```

**Validation requirement**: Before executing any mission, the orchestrator MUST validate the mission YAML against this schema. Schema validation failure → HALT + escalate.

**Mission: `design`**

Transforms a task specification into a BUILD_PACKET.

```yaml
mission: design
version: "1.0"
inputs:
  - name: task_spec
    type: str
  - name: context_refs
    type: list[str]
outputs:
  - name: build_packet
    type: BUILD_PACKET
steps:
  - id: gather_context
    kind: runtime
    operation: tool_invoke
    params:
      tool: filesystem
      action: read_files
      paths: "{{context_refs}}"
    compensation: "none"  # Read-only, no compensation needed
  - id: design
    kind: runtime
    operation: llm_call
    params:
      role: designer
      input_packet:
        type: CONTEXT_RESPONSE_PACKET
        task: "{{task_spec}}"
        context: "{{steps.gather_context.output}}"
    compensation: "none"  # LLM call, no state change
  - id: validate_output
    kind: runtime
    operation: gate_check
    params:
      schema: BUILD_PACKET
      data: "{{steps.design.output.packet}}"
    compensation: "none"
```

**Mission: `review`**

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).

```yaml
mission: review
version: "1.0"
inputs:
  - name: subject_packet
    type: dict
  - name: review_type
    type: str
outputs:
  - name: verdict
    type: str
  - name: council_decision
    type: dict
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
version: "1.0"
inputs:
  - name: build_packet
    type: BUILD_PACKET
  - name: approval
    type: COUNCIL_APPROVAL_PACKET
outputs:
  - name: review_packet
    type: REVIEW_PACKET
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
    compensation: "git checkout -- ."  # Revert all unstaged changes
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
version: "1.0"
inputs:
  - name: review_packet
    type: REVIEW_PACKET
  - name: approval
    type: COUNCIL_APPROVAL_PACKET
outputs:
  - name: commit_hash
    type: str
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
    compensation: "git reset HEAD"
  - id: commit
    kind: runtime
    operation: tool_invoke
    params:
      tool: git
      action: commit
      message: "{{review_packet.mission_name}}: {{review_packet.summary}}"
    compensation: "git reset --soft HEAD~1"
  - id: record_completion
    kind: runtime
    operation: tool_invoke
    params:
      tool: filesystem
      action: update_state
      file: LIFEOS_STATE.md
      mark_done: "{{review_packet.mission_name}}"
```

> [!IMPORTANT]
> **[v0.2 — P0.4] Steward "Repo Clean on Exit" Guarantee:**
> The `steward` mission MUST leave the repository in a clean state on exit:
> - **Success path**: All changes committed on feature branch, working directory clean.
> - **Failure path**: All staged/unstaged changes reverted, evidence preserved in `logs/failed_missions/`.
> - **Crash path**: On restart, detect incomplete steward mission and execute compensation actions.

**Mission: `autonomous_build_cycle`**

Composes the above into a single end-to-end workflow.

```yaml
mission: autonomous_build_cycle
version: "1.0"
inputs:
  - name: task_spec
    type: str
  - name: context_refs
    type: list[str]
outputs:
  - name: commit_hash
    type: str
  - name: cycle_report
    type: dict
timeout_seconds: 7200  # 2 hours max
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

### 5.4 OpenCode Envelope (Current vs Future)

**Current Envelope (Phase 2 Doc Steward):**

Per `OpenCode_First_Stewardship_Policy_v1.1.md`:

- CAN: Modify `.md` files in `docs/` (excluding protected roots)
- CAN: Add `.md` files to `artifacts/review_packets/`
- CANNOT: Modify `docs/00_foundations/`, `docs/01_governance/`, `scripts/`, `config/`
- CANNOT: Delete, rename, move, copy files
- CANNOT: Modify non-`.md` files

**[v0.2 — P0.1] Self-Modification Locks (Current Phase):**

OpenCode Doc Steward CANNOT modify:
- `config/agent_roles/*` (role prompts)
- `config/models.yaml` (model mapping)
- `config/governance_baseline.yaml` (integrity manifest)
- `scripts/opencode_gate_policy.py` (its own envelope policy)
- `runtime/orchestration/transforms/*` (packet transforms)
- Any file listed in §2.3 Governance Surface Classification

**Future Envelope (Builder — Pending Council Ruling):**

To enable autonomous build loop, OpenCode would need:

- CAN: Create/modify `.py` files in `coo/`, `runtime/`, `tests/`
- CAN: Create/modify `.yaml` and `.json` config files in `config/` (EXCLUDING governance surfaces)
- CAN: Run `pytest`
- CANNOT: Modify governance surfaces (§2.3)
- CANNOT: Modify its own envelope definition
- CANNOT: Modify `scripts/opencode_gate_policy.py`

**Evidence-Gated Expansion Path:**

| Phase | Envelope Addition | Prerequisite | Evidence Required |
|-------|-------------------|--------------|-------------------|
| Current (Phase 2) | Doc steward (`.md` in `docs/`) | Active | — |
| Phase 3a | Test execution (`pytest`) | Council ruling | 30 days stable Phase 2 ops |
| Phase 3b | Code creation (`coo/`, `runtime/`, `tests/`) | Phase 3a stable + Council ruling | 30 days stable Phase 3a ops |
| Phase 3c | Config modification (`config/` non-governance) | Phase 3b stable + Council ruling | 30 days stable Phase 3b ops |

Each expansion requires:
1. Evidence of stable operation at current phase (30 days, <2% escalation rate)
2. Council review with full seat coverage (M2_FULL)
3. CEO sign-off
4. 48-hour observation period before next expansion

### 5.5 Governance Bindings

**[v0.2 — P0.1] Builder/Steward "CANNOT MODIFY" Rules:**

In addition to current envelope restrictions, Builder and Steward agents CANNOT modify:

1. Any file in `config/agent_roles/` (role prompts)
2. `config/models.yaml` (model mapping)
3. `config/governance_baseline.yaml` (integrity manifest)
4. `scripts/opencode_gate_policy.py` (envelope policy)
5. `runtime/orchestration/transforms/*.py` (packet transforms)
6. `runtime/governance/self_mod_protection.py` (self-mod protection)
7. Any architecture document (`docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_*.md`)
8. Any agent constitution (`GEMINI.md`, `CLAUDE.md`)

These restrictions apply regardless of mission instructions. Violation attempts are logged and escalated.

**Escalation Triggers (Automatic):**

| Condition | Action |
|-----------|--------|
| Envelope violation detected | HALT + escalate to CEO |
| Council verdict is "rejected" | HALT + escalate to CEO |
| Council verdict is "fix_required" after 2 cycles | HALT + escalate to CEO |
| Budget threshold exceeded | HALT + escalate to CEO |
| Test failure after retry | HALT + escalate to CEO |
| Any modification to governance surface | HALT + escalate to CEO |
| **[v0.2]** Governance baseline hash mismatch | HALT + escalate to CEO |
| **[v0.2]** Kill switch detected | HALT + escalate to CEO |
| **[v0.2]** ANY seat verdict is "Reject" | HALT + escalate to CEO (see §5.5.1) |

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
- **[v0.2]** Mission journal with operation receipts
- **[v0.2]** Completion bundle with essential evidence subset

Retention: Indefinite for mission logs and git history. 30 days for agent call logs (configurable).

**[v0.2 — P1.2] Completion Bundle Requirement:**

When a mission completes (success or failure), a **completion bundle** MUST be produced containing:
- Mission journal with all operation receipts
- Final state hashes
- Escalation records (if any)
- Subset of agent call logs for decision-affecting calls

This bundle ensures auditability survives the 30-day agent call log retention window.

#### 5.5.1 Council Quorum and Rejection Handling [v0.2 — P0.5]

**[v0.2 — P0.5]** Council seat-set policy and rejection handling:

**Seat-Set Modes:**

| Mode | Seats Required | Applicability |
|------|---------------|---------------|
| **M2_FULL** (Full Council) | All 9 seats + Chair + CoChair | Per CCP mode selection rules |
| **M1_STANDARD** (Standard) | Chair + CoChair + 4 core seats | Default for most reviews |
| **M0_FAST** (Fast Track) | L1 Unified Reviewer only | Low-risk, local-blast-radius changes only |

**Core Seats (M1_STANDARD):** Architect, Alignment, Risk/Adversarial, Governance

**Rejection Handling Rule (Binding):**

> [!CAUTION]
> **ANY seat verdict of "Reject" triggers escalation to CEO.**
> No tie-breaking mechanism may override a Reject verdict.
> This is a fail-safe to preserve human oversight.

Specifically:
1. If ANY reviewer seat outputs `Verdict: Reject`, the council synthesis MUST output `ESCALATED_TO_CEO`.
2. The Chair CANNOT synthesize "Approved" or "Approved with Conditions" if any Reject exists.
3. The CEO reviews the rejection rationale and may:
   - Uphold the rejection (mission halts)
   - Override with documented rationale (mission proceeds, logged as `ceo_override`)
   - Request re-review with clarification

**CCP Mode Compliance:**

This architecture binds to Council Protocol v1.2 mode selection rules. If any conflict exists between this document's seat-set definitions and the CCP-applied mode, the CCP mode takes precedence.

> [!NOTE]
> **Escalation Note (P0.5):** The previous draft §8.3 proposed reduced seat-sets for "low-risk" changes.
> This has been replaced by the formal M0_FAST/M1_STANDARD/M2_FULL mode system per Council Protocol v1.2.
> No ad-hoc seat reduction is permitted.

### 5.6 Run Controller [v0.2 — P0.4, P1.1]

**[v0.2]** New component managing run lifecycle:

**Location:** `runtime/orchestration/run_controller.py`

#### 5.6.1 Kill Switch and Lock Ordering [v0.2 — P1.1, v0.3 — P1.1]

**[v0.2 — P1.1]** File-based kill switch:

```python
KILL_SWITCH_PATH = "STOP_AUTONOMY"  # Repo root

def check_kill_switch() -> bool:
    """
    Check if kill switch is active.
    
    Returns True if STOP_AUTONOMY file exists.
    Called:
    - Before mission start
    - Before each step execution
    - Before each operation execution
    """
```

**[v0.3 — P1.1] Startup Check Sequence (Race-Safe Ordering):**

To eliminate race conditions between kill-switch and lock acquisition, the following EXACT order MUST be followed at mission startup:

```python
def mission_startup_sequence() -> StartupResult:
    """
    [v0.3 — P1.1] Race-safe startup sequence.
    
    Exact order:
    1. CHECK STOP_AUTONOMY (first check)
       - If exists: HALT immediately, do not acquire lock
       
    2. ACQUIRE single-run lock
       - If lock held by another process: HALT, report conflict
       - If stale lock (dead PID): enter crash recovery path
       
    3. RE-CHECK STOP_AUTONOMY (second check, post-lock)
       - Eliminates TOCTOU race where STOP_AUTONOMY is created
         between check (1) and lock acquisition (2)
       - If exists: release lock, HALT, escalate
       
    4. PROCEED with mission
       - Verify governance baseline
       - Verify clean workspace
       - Begin execution
    
    This double-check pattern ensures:
    - No mission starts if STOP_AUTONOMY exists
    - No race between concurrent "create STOP_AUTONOMY" and "start mission"
    """
```

**[v0.3 — P1.1] Mid-Run STOP_AUTONOMY Behavior:**

If STOP_AUTONOMY appears while a mission is running:

```python
def handle_mid_run_kill_switch(ctx: ExecutionContext) -> Never:
    """
    [v0.3 — P1.1] Handle kill switch detected mid-run.
    
    Behavior:
    1. Complete current atomic action OR rollback cleanly
       - If in middle of git operation: complete it
       - If in middle of file write: use atomic write with rollback
       - DO NOT leave partial state
       
    2. Execute compensation for completed steps (if needed)
       - Follow compensation verification rules (§5.2.2)
       - Record compensation receipts
       
    3. Create evidence bundle:
       - Mission journal state at halt
       - Current step ID and operation
       - STOP_AUTONOMY detection timestamp
       - Any partial work description
       
    4. Release run lock
       - Ensure lock file is deleted
       
    5. Write evidence to logs/kill_switch_activations/<timestamp>/
       - Include full mission state
       - Include steps completed vs remaining
       
    6. Create escalation record in SQLite
       - severity: "info" (clean halt)
       - reason: "Kill switch activated mid-run"
       
    7. Exit gracefully
       - No further steps
       - No automatic restart
    """
```

**Behavior when kill switch detected (at startup):**
1. HALT immediately — do not acquire lock
2. Write detection evidence to `logs/kill_switch_activations/`
3. Escalate to CEO with context
4. Do NOT proceed with any further steps

**Creating kill switch:** `touch STOP_AUTONOMY` in repo root
**Clearing kill switch:** Delete `STOP_AUTONOMY` file (CEO action only)

#### 5.6.2 Single-Run Lock [v0.2 — P0.4]

**[v0.2 — P0.4]** Only one mission may execute at a time:

```python
LOCK_FILE_PATH = ".lifeos_run_lock"

@dataclass
class RunLock:
    run_id: str
    pid: int
    started_at: str
    mission_type: str
    
def acquire_run_lock(run_id: str, mission_type: str) -> bool:
    """
    Attempt to acquire exclusive run lock.
    
    1. Check if lock file exists
    2. If exists, check if owning process is still alive (PID check)
    3. If process dead, treat as stale lock (crash recovery path)
    4. If process alive, fail to acquire (another run in progress)
    5. If no lock, create lock file with current run info
    
    Returns True if lock acquired, False if another run is active.
    """

def release_run_lock(run_id: str) -> bool:
    """
    Release run lock after mission completion.
    
    1. Verify we own the lock (run_id matches)
    2. Delete lock file
    3. Return True on success
    """
```

#### 5.6.3 Repo State Lock [v0.2 — P0.3]

**[v0.2 — P0.3]** Stable workspace guarantee:

At mission start:
1. Record `git rev-parse HEAD` as `baseline_commit`
2. Verify `git status --porcelain` is empty (clean working directory)
3. If not clean: HALT + escalate (do not proceed with dirty workspace)
4. Record workspace state hash

During mission:
- Single-writer assumption enforced by run lock
- No external modifications permitted while mission runs
- If external modification detected (git status changes unexpectedly): HALT + escalate

#### 5.6.4 Crash Recovery [v0.2 — P0.4]

**[v0.2 — P0.4]** Recovery from incomplete missions:

On startup, Run Controller checks for incomplete missions:

```python
def check_crash_recovery() -> Optional[RecoveryPlan]:
    """
    Check if previous run crashed and needs recovery.
    
    1. Check for stale lock file with dead PID
    2. If found, load mission journal from last known state
    3. Determine recovery action:
       - If last step was idempotent: resume from that step
       - If last step was non-idempotent: execute compensation, then restart
       - If unable to determine: escalate to CEO for manual recovery
    """
```

**Recovery modes:**

| Last Step State | Recovery Action |
|-----------------|-----------------|
| Completed successfully | Resume from next step |
| In progress (read-only) | Restart step |
| In progress (write) | Execute compensation, restart step |
| Unknown | Escalate to CEO |

### 5.7 Mission Journal [v0.2 — P0.4]

**[v0.2 — P0.4]** Persistent mission execution log:

**Location:** `logs/mission_journals/<run_id>/`

```python
@dataclass
class MissionJournalEntry:
    entry_id: str                # Deterministic
    run_id: str
    step_id: str
    operation_type: str
    status: str                  # "pending", "in_progress", "completed", "failed", "compensated"
    started_at: str
    completed_at: Optional[str]
    receipt: Optional[OperationReceipt]
    prev_entry_hash: str         # Hash chain

class MissionJournal:
    def record_step_start(self, run_id: str, step_id: str, operation: str) -> str:
        """Record step start, return entry_id."""
        
    def record_step_complete(self, entry_id: str, receipt: OperationReceipt) -> None:
        """Record successful completion with receipt."""
        
    def record_step_failed(self, entry_id: str, error: str, compensation_needed: bool) -> None:
        """Record failure, mark for potential compensation."""
        
    def get_incomplete_steps(self, run_id: str) -> List[MissionJournalEntry]:
        """Get steps that need attention (for crash recovery)."""
        
    def check_idempotency(self, run_id: str, step_id: str, idempotency_key: str) -> bool:
        """Check if this step was already completed (for rerun detection)."""
```

### 5.8 Evidence Integrity [v0.2 — P1.2]

**[v0.2 — P1.2]** Tamper-evident logging:

**Hash Chain Requirement:**

All log entries (agent calls, mission journal, operation receipts) MUST include:
- `prev_log_hash`: SHA-256 hash of previous entry
- `entry_hash`: SHA-256 hash of current entry (including prev_log_hash)

This creates an append-only chain where tampering is detectable.

**Chain Verification:**

```python
def verify_log_chain(log_path: str) -> VerificationResult:
    """
    Verify integrity of log chain.
    
    1. Load all entries
    2. For each entry, verify prev_log_hash matches previous entry_hash
    3. Return list of any breaks in chain
    """
```

**Completion Bundle Contents:**

When mission completes, produce bundle containing:
- Mission journal (full)
- Agent call log subset (decision-affecting calls only)
- Final governance surface hashes
- Git commit hash of result
- Hash chain root for verification

Bundle is stored permanently (not subject to 30-day retention).

---

## 6. Persistence Layer [v0.2 — P1.3]

### 6.1 SQLite Schema [v0.2 — P1.3]

**[v0.2 — P1.3]** Minimal required schema:

```sql
-- Mission runs table
CREATE TABLE mission_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL,           -- Unique mission instance ID
    run_id_deterministic TEXT NOT NULL, -- Deterministic run ID (§5.1.3)
    run_id_audit TEXT NOT NULL,         -- UUID for audit correlation
    mission_type TEXT NOT NULL,         -- e.g., "design", "build", "steward"
    status TEXT NOT NULL,               -- "pending", "running", "completed", "failed", "escalated"
    started_at TEXT NOT NULL,           -- ISO8601 timestamp
    completed_at TEXT,                  -- ISO8601 timestamp
    baseline_commit TEXT NOT NULL,      -- Git HEAD at mission start
    result_commit TEXT,                 -- Git commit after steward (if applicable)
    governance_baseline_hash TEXT NOT NULL, -- Hash of governance surfaces at start
    escalation_reason TEXT,             -- If escalated, why
    evidence_bundle_path TEXT,          -- Path to completion bundle
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Step logs table
CREATE TABLE step_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,               -- "pending", "running", "completed", "failed", "compensated"
    started_at TEXT NOT NULL,
    completed_at TEXT,
    pre_state_hash TEXT,                -- State hash before operation
    post_state_hash TEXT,               -- State hash after operation
    evidence_hash TEXT,                 -- Hash of evidence produced
    error_message TEXT,                 -- If failed, error details
    compensation_status TEXT,           -- "not_needed", "pending", "completed", "failed"
    prev_entry_hash TEXT NOT NULL,      -- Hash chain
    entry_hash TEXT NOT NULL,           -- This entry's hash
    FOREIGN KEY (mission_id) REFERENCES mission_runs(mission_id)
);

-- Escalation queue
CREATE TABLE escalation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escalation_id TEXT NOT NULL UNIQUE,
    mission_id TEXT,
    reason TEXT NOT NULL,
    severity TEXT NOT NULL,             -- "info", "warning", "critical"
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution TEXT,                    -- "approved", "rejected", "deferred"
    resolved_by TEXT,                   -- "CEO" or null
    notes TEXT
);

-- Indexes
CREATE INDEX idx_mission_runs_status ON mission_runs(status);
CREATE INDEX idx_step_logs_mission_id ON step_logs(mission_id);
CREATE INDEX idx_escalation_queue_resolved ON escalation_queue(resolved_at);
```

---

## 7. Implementation Phases

### Phase 1: Agent API Layer (Est. 3-5 days)

**Deliverables:**
- `runtime/agents/api.py` — OpenRouter client with role dispatch
- `runtime/agents/logging.py` — Deterministic call logging with hash chain
- `runtime/agents/fixtures.py` — [v0.2] Replay fixture mechanism
- `config/agent_roles/*.md` — Initial role prompts (designer, reviewer seats, builder)
- `config/models.yaml` — Role→model mapping
- `config/governance_baseline.yaml` — [v0.2] Initial governance surface manifest
- Unit tests for API layer
- Integration test with live OpenRouter call

**Exit Criteria:**
- `call_agent()` successfully invokes OpenRouter
- Response is logged deterministically with hash chain
- Role prompts load correctly with hash verification
- [v0.2] Replay fixture mode works
- Tests pass

### Phase 2: Operations + Run Controller (Est. 5-7 days)

**Deliverables:**
- `runtime/orchestration/operations.py` — Operation executor
- `runtime/orchestration/run_controller.py` — [v0.2] Run lifecycle management
- `runtime/orchestration/mission_journal.py` — [v0.2] Journal with receipts
- `runtime/governance/envelope_enforcer.py` — [v0.2] Path containment enforcement
- `runtime/governance/self_mod_protection.py` — [v0.2] Self-modification blocks
- Extensions to `engine.py` for new operation dispatch
- `llm_call`, `tool_invoke`, `packet_route`, `gate_check` implementations
- Unit tests for each operation type
- Integration tests with mock tools

**Exit Criteria:**
- Engine executes workflows with new operation types
- Envelope checks trigger violations correctly
- [v0.2] Kill switch halts operations
- [v0.2] Run lock prevents concurrent execution
- [v0.2] Mission journal records all operations
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
- [v0.2] Mission YAML schema validation
- End-to-end test with mock builder

**Exit Criteria:**
- Each mission executes in isolation
- `autonomous_build_cycle` composes correctly
- Escalation triggers work
- [v0.2] ANY seat rejection escalates to CEO
- [v0.2] Steward guarantees repo clean on exit
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
- [v0.2] Self-modification attempts are blocked
- Council ruling obtained for Phase 3a envelope

### Phase 5: End-to-End Validation (Est. 3-5 days)

**Deliverables:**
- Execute real backlog item through full cycle
- Document friction points and failures
- Fix critical issues
- Produce Milestone Report
- [v0.2] Validate crash recovery
- [v0.2] Validate evidence integrity chain

**Exit Criteria:**
- One task completes TODO→DONE without CEO routing
- Escalation works (test by injecting failure)
- [v0.2] Kill switch halts execution
- [v0.2] Crash recovery restores or rolls back correctly
- Audit trail is complete and useful
- CEO can review and approve via queue

---

## 8. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OpenRouter API instability | Medium | High | Implement retry with backoff; fallback model chain |
| LLM produces invalid packets | High | Medium | Strict schema validation; retry once; escalate on second failure |
| Runaway token spend | Medium | High | Budget caps per mission; daily ceiling; alerts |
| OpenCode envelope too restrictive | Medium | Medium | Staged expansion; measure what's blocked |
| Council automation reduces quality | Medium | High | Compare automated vs manual council verdicts; tune prompts |
| Self-modification escape | Low | Critical | Hardcoded protection for envelope definitions; no self-modification path; hash verification |
| **[v0.2]** Governance surface tampering | Low | Critical | Runtime hash verification; hash chain logs; completion bundles |
| **[v0.2]** Crash leaves dirty state | Medium | High | Mission journal; compensation actions; repo-clean guarantee |
| **[v0.2]** TOCTOU path exploits | Low | High | Realpath containment; re-check before execution; single-writer lock |

---

## 9. Open Questions (For CEO Decision)

1. **Model selection:** Default model for each role? (Recommendation: Claude Sonnet for speed, Opus for design/architecture seats)

2. **Budget ceiling:** Daily token/cost limit before automatic halt? (Recommendation: $10/day initial ceiling)

3. **~~Council seat reduction:~~** ~~Full 9-seat council for every review, or reduced set for low-risk changes?~~ **[v0.2 — Resolved]** Removed per P0.5. Use M0_FAST/M1_STANDARD/M2_FULL modes per Council Protocol v1.2.

4. **Observation period:** 48 hours between envelope expansions, or different cadence? (Recommendation: 48 hours minimum, extend if issues found)

5. **First workload:** Which backlog item to use for Phase 5 validation? (Recommendation: A bounded, low-governance-risk item like "Register `run_tests` in registry.py")

---

## 10. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| OpenRouter API access | Required | Need API key configured |
| OpenCode doc steward | Active | Current envelope sufficient for Phase 1-3 |
| Council Protocol v1.2 | Active | Binds council automation |
| Tier-2 Orchestration Engine | Active | Foundation for operations |
| Packet schemas v1.2 | Active | Contract layer |
| **[v0.2]** Governance baseline | To Create | `config/governance_baseline.yaml` |

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-08 | Claude + GL | Initial draft for council review |
| 0.2 | 2026-01-08 | Claude + GL | Council fix pack integration: P0.1 (governance surfaces + self-mod lock), P0.2 (envelope enforcement), P0.3 (determinism/replay), P0.4 (atomicity/rollback), P0.5 (council quorum), P1.1 (kill switch), P1.2 (evidence integrity), P1.3 (formal schemas) |
| 0.3 | 2026-01-08 | Claude + GL | Council re-review fixes: P0.1 (governance baseline ceremony), P0.2 (compensation verification + post-state checks), P0.3 (canonical_json spec + replay equivalence + hash chain genesis), P1.1 (kill-switch/lock ordering + mid-run behavior), P1.2 (model "auto" deterministic semantics) |

---

**END OF DOCUMENT**
