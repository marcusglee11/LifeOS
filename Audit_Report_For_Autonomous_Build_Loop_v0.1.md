# Audit Report: Autonomous Build Loop Architecture
**Version:** 0.1
**Date:** 2026-01-08
**Prepared by:** Claude Code (claude.ai/code)
**Purpose:** Inform design decisions for the Autonomous Build Loop Architecture

---

## Executive Summary

### What EXISTS (Build On This)

| Component | Location | Maturity |
|-----------|----------|----------|
| **Orchestration Engine** | `runtime/orchestration/engine.py` | Architecture-clean, feature-minimal |
| **StepSpec/WorkflowDefinition** | `runtime/orchestration/engine.py` | Production-ready dataclasses |
| **OpenCode Integration** | `scripts/opencode_ci_runner.py` | Full HTTP REST interface |
| **Gate Policy (Phase 2 v2.0)** | `scripts/opencode_gate_policy.py` | Hardened, fail-closed, 39 reason codes |
| **SQLite Database** | `project_builder/database/schema.sql` | 5 tables, mission/task/artifact/timeline |
| **Packet Schemas** | `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml` | v1.2, 12 packet types |
| **Packet Validator** | `scripts/validate_packet.py` | Schema-driven, lineage verification |
| **Test Infrastructure** | `runtime/tests/`, `tests_doc/`, `tests_recursive/` | 67+ test files, pytest |
| **Agent Role Prompts** | `docs/09_prompts/v1.0/`, `v1.2/` | Chair, reviewers, protocols |
| **State Persistence** | `runtime/state_store.py` | JSON with deterministic hashing |

### What's MISSING (Must Build)

| Component | Gap | Effort |
|-----------|-----|--------|
| **Operation Handlers** | Only `noop`/`fail` exist; no `llm_call`, `tool_invoke` | Medium |
| **State Mutation Logic** | Commented as "future" in engine.py | Medium |
| **Direct LLM Client** | All via OpenCode abstraction; no native API client | Low (can use OpenCode) |
| **Packet Routing Layer** | Implicit via validator; no explicit router | Low |
| **Centralized Model Config** | Model specified at CLI invocation time | Low |
| **LIFEOS_STATE.md Automation** | Currently manual agent updates | Medium |

### Critical Design Insight

**The orchestration engine is architecture-complete but operation-empty.** Adding `llm_call` is purely additive—extend the dispatch `if/elif` chain in `engine.py`, no breaking changes needed. The hardest part is already done (workflow definition, anti-failure constraints, deterministic hashing).

---

## 1. Current Orchestration Implementation

### 1.1 Operation Types Supported

**File:** `runtime/orchestration/engine.py`

Currently supports only **2 operations**:

```python
operation = step.payload.get("operation", "noop")

if operation == "fail":
    # Halt execution with failure
    success = False
    failed_step_id = step.id
    reason = step.payload.get("reason", "unspecified")
    error_message = f"Step '{step.id}' failed: {reason}"
    break

# For "noop" or any other operation, continue without state change
# (Future: could implement state mutations here)
```

**Operations:**
1. `"fail"` — Stops workflow execution with failure status
2. `"noop"` (default) — No-operation, continues without state mutation

### 1.2 StepSpec Interface

```python
@dataclass
class StepSpec:
    """
    Specification for a single workflow step.

    Attributes:
        id: Unique identifier for the step.
        kind: Type of step ('runtime' or 'human').
        payload: Step-specific configuration data.
    """
    id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict with stable key ordering."""
        return {
            "id": self.id,
            "kind": self.kind,
            "payload": dict(sorted(self.payload.items())) if self.payload else {},
        }
```

### 1.3 WorkflowDefinition Interface

```python
@dataclass
class WorkflowDefinition:
    """
    Definition of a multi-step workflow.

    Attributes:
        id: Unique identifier for the workflow.
        steps: Ordered list of steps to execute.
        metadata: Additional workflow metadata.
        name: Alias for id (for compatibility).
    """
    id: str = ""
    steps: List[StepSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    name: str = ""  # Alias for id

    def __post_init__(self):
        # Enforce consistency between 'id' and 'name'
        if self.id and not self.name:
            self.name = self.id
        elif self.name and not self.id:
            self.id = self.name
        elif self.id and self.name and self.id != self.name:
            raise ValueError(f"WorkflowDefinition id/name mismatch: '{self.id}' vs '{self.name}'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict with stable key ordering."""
        return {
            "id": self.id,
            "metadata": dict(sorted(self.metadata.items())) if self.metadata else {},
            "steps": [s.to_dict() for s in self.steps],
        }
```

### 1.4 Engine Dispatch Logic

```python
ALLOWED_KINDS = frozenset({"runtime", "human"})

for step in workflow.steps:
    # Record step as executed
    executed_steps.append(copy.deepcopy(step))

    if step.kind == "runtime":
        # Process runtime step
        operation = step.payload.get("operation", "noop")

        if operation == "fail":
            # Halt execution with failure
            success = False
            failed_step_id = step.id
            reason = step.payload.get("reason", "unspecified")
            error_message = f"Step '{step.id}' failed: {reason}"
            break

        # For "noop" or any other operation, continue without state change
        # (Future: could implement state mutations here)

    elif step.kind == "human":
        # Human steps: record but don't modify state
        # (In real implementation, would wait for human input)
        pass
```

**Pre-flight validation:**
```python
for step in workflow.steps:
    if step.kind not in self.ALLOWED_KINDS:
        raise EnvelopeViolation(
            f"Step '{step.id}' has disallowed kind '{step.kind}'. "
            f"Allowed kinds: {sorted(self.ALLOWED_KINDS)}"
        )
```

### 1.5 Adding New Operation Types

**Required changes to add `llm_call`, `tool_invoke`:**

1. **Extend dispatch in `engine.py`:**
```python
if operation == "fail":
    # handle fail
elif operation == "llm_call":
    model = step.payload.get("model", "claude-3-opus")
    prompt = step.payload.get("prompt", "")
    result = call_llm(model, prompt)  # New handler
    state[step.id] = result
elif operation == "tool_invoke":
    tool_name = step.payload.get("tool_name")
    args = step.payload.get("args", {})
    result = invoke_tool(tool_name, args)  # New handler
    state[step.id] = result
elif operation == "noop":
    pass
```

2. **Define payload schemas per operation**
3. **Update ExecutionContext to handle outputs**
4. **Add operation-specific constraints if needed**

**Effort estimate:** Medium — dispatch extension is trivial, but handlers need implementation.

---

## 2. OpenCode Integration

### 2.1 Invocation Interface

**File:** `scripts/opencode_ci_runner.py`

**CLI Usage:**
```bash
python scripts/opencode_ci_runner.py \
  --port 62586 \
  --model openrouter/x-ai/grok-4.1-fast \
  --task '<JSON_STRING>'
```

**Arguments:**
- `--port` (int, default=62586): HTTP port for ephemeral OpenCode server
- `--model` (str, default="openrouter/x-ai/grok-4.1-fast"): LLM model routing
- `--task` (str, required): JSON-structured task specification

### 2.2 Task JSON Schema

```json
{
  "files": ["docs/some_file.md", "artifacts/review_packets/some_review.md"],
  "action": "create",
  "instruction": "Create a review packet summarizing the changes..."
}
```

**Required fields:** `files`, `action`, `instruction`
**Action values:** `"create"` | `"modify"` (no delete in Phase 2)
**Constraint:** Free-text input rejected—must be JSON-structured.

### 2.3 OpenCode HTTP Protocol

```python
# 1. Server Start
subprocess.Popen(["opencode", "serve", "--port", str(port)], env=env, ...)

# 2. Health Check
GET http://127.0.0.1:{port}/global/health
# Expected: status_code == 200

# 3. Session Creation
POST http://127.0.0.1:{port}/session
JSON body: {"title": "Steward Mission", "model": model}
# Response: {"id": "<session_id>"}

# 4. Message Submission
POST http://127.0.0.1:{port}/session/{session_id}/message
JSON body: {"parts": [{"type": "text", "text": instruction}]}
# Timeout: 120 seconds

# 5. Response Format
{"parts": [{"type": "text", "text": "...response..."}]}
```

### 2.4 OpenCode Return Contract

The runner **does NOT parse LLM response content**. Instead:
1. Executes the mission (waits for session/message calls)
2. Extracts only `session_id`
3. Validates changes via **post-execution git diff**

OpenCode modifies repository files directly; the runner validates those changes against the envelope.

### 2.5 Envelope Checks (Gate Policy v2.0)

**File:** `scripts/opencode_gate_policy.py`

**Blocked Operations (Terminal):**
```python
PH2_DELETE_BLOCKED = "PH2_DELETE_BLOCKED"
PH2_RENAME_BLOCKED = "PH2_RENAME_BLOCKED"
PH2_COPY_BLOCKED = "PH2_COPY_BLOCKED"
```

**Allowlist Roots:**
```python
ALLOWLIST_ROOTS = [
    "artifacts/review_packets/",
    "docs/",
]
```

**Denylist Roots:**
```python
DENYLIST_ROOTS = [
    "config/",
    "docs/00_foundations/",  # Governance-protected
    "docs/01_governance/",    # Governance-protected
    "scripts/",
]
```

**Policy Ordering:**
1. Blocked ops check (D/R/C)
2. Denylist-first (terminal, no bypass)
3. Allowlist check
4. Extension validation (under docs/)
5. Review packets (add-only `.md`)

**Evidence Bundle Generated:**
```
mission_{timestamp}/
├── exit_report.json       # {"status": "PASS"|"BLOCK", "reason_code": str}
├── changed_files.json     # [{"status": "A"|"M"|"D", "path": "..."}]
├── classification.json    # {"is_governance": bool, "risk_level": "P0"|"P1"}
├── runner.log             # Truncated log (max 500 lines)
└── hashes.json            # SHA-256 hashes of all above
```

### 2.6 Programmatic vs CLI

**Current:** CLI-only via subprocess + HTTP REST
**No native SDK:** All LLM interaction abstracted through OpenCode
**To add direct API:** Would need to add OpenRouter/Anthropic/OpenAI client library

---

## 3. Existing Agent/LLM Infrastructure

### 3.1 LLM API Clients

| Client | Present? | Notes |
|--------|----------|-------|
| OpenRouter API | NO | Model string passed to OpenCode, not called directly |
| Anthropic SDK | NO | Not imported anywhere |
| OpenAI SDK | NO | Explicitly blocked as fallback (`OPENAI_API_KEY=""`) |
| `requests` library | YES | For HTTP calls to OpenCode server only |

**All LLM interaction is abstracted through OpenCode's HTTP API.**

### 3.2 Agent Role Definitions

**Location:** `docs/09_prompts/`

**v1.2 (Latest):**
- `chair_prompt_v1.2.md` — Orchestrator, packet construction, role routing
- `cochair_prompt_v1.2.md` — Challenge synthesis, hunt hallucinations
- `reviewer_l1_unified_v1.2.md` — Unified 4-lens reviewer
- Specialized reviewers: alignment, architect, governance, risk, technical, testing

**v1.0 (Foundational):**
- Chair responsibilities: Intake & Framing, Packet Construction, Role Routing, Governance & Safety, Summarisation & Handoff
- Review output format: Verdict, Issues, Risks, Required Changes, Questions

**Doc Steward Agent (AGENTS.md):**
```markdown
## Core Directives
1. Governance & Authority: Subordinate to LifeOS governance
2. Review Packet Protocol: Every mission MUST end with Review_Packet
3. Doc Stewardship: Update docs/INDEX.md, regenerate Corpus
4. Zero-Friction Rule: Don't ask user for file lists
```

### 3.3 Model Configuration

**No centralized config file.** Model specified at runtime:
- Default: `"openrouter/x-ai/grok-4.1-fast"`
- Override via: `--model` CLI flag
- Tokenizer config in `project_builder/context/tokenizer.py` references generic provider

---

## 4. Test Infrastructure

### 4.1 pytest Configuration

**File:** `pytest.ini`

```ini
[pytest]
testpaths =
    runtime/tests
    tests_doc
    tests_recursive
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --ignore=runtime/tests/archive_legacy_r6x
```

### 4.2 Test Structure

| Suite | Location | Files | Purpose |
|-------|----------|-------|---------|
| **Runtime** | `runtime/tests/` | 56 | Core orchestration, FSM, governance, safety |
| **Documentation** | `tests_doc/` | 5 | Index consistency, TDD compliance |
| **Recursive** | `tests_recursive/` | 6 | Planner, gate policy, kernel tests |

### 4.3 Integration Test Pattern

**File:** `runtime/tests/test_demo_approval_determinism.py`

```python
def run_demo(input_str="yes"):
    """Run the approval demo via subprocess."""
    cmd = [sys.executable, "-m", "coo.cli", "run-approval-demo"]
    result = subprocess.run(
        cmd,
        input=input_str.encode("utf-8"),
        cwd=str(REPO_ROOT),
        capture_output=True,
        check=True
    )
    return result

def test_demo_approval_determinism():
    """F3: Deterministic Test (Automated)
    Run DEMO_APPROVAL_V1 twice with same input/approval.
    Assert identical artifacts."""
    # Runs subprocess, compares hashes
```

### 4.4 Orchestration Test Pattern

**File:** `runtime/tests/test_tier2_orchestrator.py`

```python
def test_orchestrator_runs_steps_in_order():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=3, human_steps=1)
    ctx = ExecutionContext(initial_state={"counter": 0})
    result = orchestrator.run_workflow(workflow, ctx)
    assert result.success is True
    assert [s.id for s in result.executed_steps] == ["step-0", "step-1", "step-2"]

def _stable_hash(obj: Any) -> str:
    """Deterministic hash helper."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

### 4.5 External Tool Tests

Tests that invoke external tools:
- `test_demo_approval_determinism.py` — subprocess to CLI
- `tests_recursive/test_opencode_gate_policy.py` — gate policy validation
- `scripts/opencode_phase0_validation.py` — OpenCode connectivity test

---

## 5. State Management

### 5.1 ExecutionContext

**File:** `runtime/orchestration/engine.py`

```python
@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    initial_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
```

**OrchestrationResult:**
```python
@dataclass
class OrchestrationResult:
    """Result of a workflow execution."""
    id: str
    success: bool
    executed_steps: List[StepSpec]
    final_state: Dict[str, Any]
    failed_step_id: Optional[str] = None
    error_message: Optional[str] = None
    lineage: Dict[str, Any] = field(default_factory=dict)
    receipt: Dict[str, Any] = field(default_factory=dict)
```

### 5.2 State Persistence

**File:** `runtime/state_store.py`

```python
class StateStore:
    def __init__(self, storage_path: str = "persistence"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def write_state(self, key: str, state: Dict[str, Any]):
        """Write state dict to JSON file (sorted keys for determinism)."""
        path = os.path.join(self.storage_path, f"{key}.json")
        with open(path, "w") as f:
            json.dump(state, f, sort_keys=True)

    def read_state(self, key: str) -> Dict[str, Any]:
        path = os.path.join(self.storage_path, f"{key}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"State key {key} not found")
        with open(path, "r") as f:
            return json.load(f)

    def create_snapshot(self, key: str) -> str:
        """Returns SHA256 hash of state (deterministic)."""
        state = self.read_state(key)
        serialized = json.dumps(state, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
```

### 5.3 SQLite Database

**File:** `project_builder/database/schema.sql`

**Tables:**
```sql
missions:
  - id, status, previous_status, description
  - max_cost_usd, max_loops, priority
  - config_json, spent_cost_usd, loop_count, message_count
  - created_at, updated_at, completed_at, failed_at, failure_reason

mission_tasks:
  - id, mission_id, task_order, description
  - context_files (JSON), required_artifact_ids (JSON)
  - status (pending|executing|review|repair_retry|approved|failed_terminal|skipped)
  - result_artifact_ids (JSON), repair_attempt, consumed_tokens
  - started_at, locked_at, locked_by, created_at, updated_at, completed_at

artifacts:
  - id, mission_id, file_path, version_number, supersedes_id
  - is_deleted, kind, mime_type, checksum, size_bytes, content (BLOB)
  - metadata_json, created_at

timeline_events:
  - id (UUIDv5), mission_id, task_id
  - event_type (agent_invoked|state_transition|task_started|...)
  - event_json, created_at
```

### 5.4 Timeline Event Generation

**File:** `project_builder/database/timeline.py`

```python
TIMELINE_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-000000000001')

def generate_timeline_event_id(mission_id: str, task_id: str, event_type: str, created_at: datetime) -> str:
    """Generates a deterministic UUIDv5 for a timeline event."""
    counter = _get_next_counter(task_id)  # Per-task monotonic counter
    name = f"{mission_id}:{task_id}:{event_type}:{created_at.isoformat()}:{counter}"
    return str(uuid.uuid5(TIMELINE_NAMESPACE, name))
```

### 5.5 LIFEOS_STATE.md Updates

**File:** `docs/11_admin/LIFEOS_STATE.md`

**Currently:** Manual updates by agents
**Contract:** "DONE requires evidence refs; 'assuming done' forbidden"
**Constraints:** Max 2 WIP items, max 3 CEO decisions
**No programmatic update mechanism exists.**

---

## 6. Packet Handling

### 6.1 Packet Schema

**File:** `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml`

```yaml
schema_version: "1.2"

limits:
  max_payload_size_kb: 8192
  max_clock_skew_seconds: 300

envelope:
  required:
    - packet_id (UUID)
    - packet_type (string)
    - schema_version (semver)
    - created_at (ISO datetime)
    - source_agent, target_agent (strings)
    - chain_id (UUID)
    - priority (string)
    - nonce (UUID)
    - ttl_hours (integer)

taxonomy:
  core_packet_types:
    - COUNCIL_REVIEW_PACKET
    - COUNCIL_APPROVAL_PACKET
    - BUILD_PACKET
    - REVIEW_PACKET
    - HANDOFF_PACKET
    - STATE_MANAGEMENT_PACKET
    - CONTEXT_REQUEST_PACKET
    - CONTEXT_RESPONSE_PACKET
    - DOC_STEWARD_REQUEST_PACKET
    # ... (12 total)
```

### 6.2 Packet Validation

**File:** `scripts/validate_packet.py`

**Exit Codes:**
```python
EXIT_PASS = 0
EXIT_FAIL_GENERIC = 1
EXIT_SCHEMA_VIOLATION = 2
EXIT_SECURITY_VIOLATION = 3
EXIT_LINEAGE_VIOLATION = 4
EXIT_REPLAY_VIOLATION = 5
EXIT_VERSION_INCOMPATIBLE = 6
```

**Validation Chain:**
1. Required envelope fields (schema-driven)
2. UUID validation (packet_id, chain_id, nonce)
3. Timestamp + clock skew check
4. TTL enforcement
5. Signature enforcement (for COUNCIL_APPROVAL_PACKET)
6. Taxonomy enforcement (fail-closed on unknown types)
7. Payload validation (per packet type)
8. Replay check (nonce deduplication)
9. Lineage verification (approval→review hash match)

**Usage:**
```bash
# Single packet
python scripts/validate_packet.py /path/to/packet.yaml --schema docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml

# Bundle (directory)
python scripts/validate_packet.py --bundle /path/to/dir --schema ...
```

### 6.3 Packet Creation Pattern

From test files:
```python
# Create YAML with frontmatter
data = {
    'packet_id': str(uuid.uuid4()),
    'packet_type': 'COUNCIL_REVIEW_PACKET',
    'schema_version': '1.2',
    'created_at': datetime.utcnow().isoformat() + 'Z',
    'source_agent': 'TestAgent',
    'target_agent': 'Council',
    'chain_id': str(uuid.uuid4()),
    'priority': 'P1_HIGH',
    'nonce': str(uuid.uuid4()),
    'ttl_hours': 72,
    # ... payload fields
}
path.write_text(yaml.dump(data), encoding='utf-8')
```

### 6.4 Packet Routing

**No explicit routing layer.** Pattern is implicit:
1. Packets are immutable once created (hash-based references)
2. Lineage via canonical hashing (YAML dump → SHA256)
3. Routing by `packet_type` and `target_agent` fields
4. Validation is schema-driven (loaded at runtime)

---

## 7. Gaps and Recommendations

### 7.1 Infrastructure to Build On

| Component | Recommendation |
|-----------|----------------|
| **Orchestration Engine** | Extend dispatch chain—architecture is solid |
| **StepSpec/WorkflowDefinition** | Use as-is, no changes needed |
| **Packet Schema v1.2** | Use as-is, add new packet types as needed |
| **SQLite Database** | Use for mission/task state; schema is comprehensive |
| **Gate Policy** | Use as validation layer for any autonomous actions |
| **Test Infrastructure** | Follow existing patterns (subprocess, hash comparison) |

### 7.2 Must Build from Scratch

| Component | Approach |
|-----------|----------|
| **`llm_call` operation handler** | Add to engine.py dispatch; use OpenCode HTTP or add direct client |
| **`tool_invoke` operation handler** | Add to engine.py dispatch; define tool registry |
| **State mutation logic** | Implement the "Future" comment in engine.py |
| **Operation schemas** | Define payload specs for each new operation |
| **LIFEOS_STATE.md automation** | Add programmatic update function (optional) |

### 7.3 Design Spec Conflicts

**Potential conflicts identified:**

1. **Direct LLM API assumption:** Design may assume direct OpenRouter/Anthropic calls, but codebase uses OpenCode as abstraction layer. Either adapt design to use OpenCode HTTP, or add native client.

2. **State mutation:** Design may assume state flows through operations, but current engine has no-op state handling. Must implement `state[step.id] = result` pattern.

3. **Model configuration:** Design may assume centralized model config, but current system uses CLI-time `--model` flag. May need config file if design requires it.

### 7.4 Simplest Path to Working `llm_call`

**Option A: Use OpenCode (Recommended)**
```python
# In engine.py dispatch
elif operation == "llm_call":
    model = step.payload.get("model", "openrouter/x-ai/grok-4.1-fast")
    prompt = step.payload.get("prompt", "")

    # Start ephemeral OpenCode server
    server = start_opencode_server(port=62586, model=model)

    # Create session and send message
    session_id = create_session(server, model)
    response = send_message(session_id, prompt)

    # Store result
    state[step.id] = response
    server.terminate()
```

**Option B: Direct API Client**
```python
# In engine.py dispatch
elif operation == "llm_call":
    import anthropic  # or openai, or requests to OpenRouter

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=step.payload.get("model", "claude-3-opus-20240229"),
        messages=[{"role": "user", "content": step.payload["prompt"]}]
    )
    state[step.id] = response.content[0].text
```

**Recommendation:** Start with Option A (OpenCode) since infrastructure exists. Add Option B later if needed for performance or specific model requirements.

---

## Files Inspected

### Orchestration
- `runtime/orchestration/engine.py`
- `runtime/orchestration/builder.py`
- `runtime/orchestration/harness.py`
- `runtime/orchestration/registry.py`
- `runtime/orchestration/config_adapter.py`
- `runtime/orchestration/daily_loop.py`
- `runtime/orchestration/suite.py`
- `runtime/orchestration/test_run.py`
- `runtime/orchestration/expectations.py`

### OpenCode Integration
- `scripts/opencode_ci_runner.py`
- `scripts/opencode_gate_policy.py`
- `scripts/opencode_phase0_validation.py`
- `scripts/debug_opencode_response.py`
- `opencode.json`
- `.github/workflows/opencode_ci.yml`

### State Management
- `runtime/state_store.py`
- `project_builder/database/schema.sql`
- `project_builder/database/timeline.py`
- `project_builder/database/snapshot.py`
- `project_builder/database/migrations.py`
- `project_builder/orchestrator/missions.py`
- `docs/11_admin/LIFEOS_STATE.md`

### Packet Handling
- `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml`
- `docs/02_protocols/lifeos_packet_schemas_v1.2.yaml`
- `docs/02_protocols/build_artifact_schemas_v1.yaml`
- `scripts/validate_packet.py`
- `runtime/tests/test_packet_validation.py`

### Test Infrastructure
- `pytest.ini`
- `runtime/tests/` (56 files)
- `tests_doc/` (5 files)
- `tests_recursive/` (6 files)
- `runtime/tests/test_tier2_orchestrator.py`
- `runtime/tests/test_demo_approval_determinism.py`

### Agent Definitions
- `AGENTS.md`
- `docs/09_prompts/v1.0/roles/chair_prompt_v1.0.md`
- `docs/09_prompts/v1.0/roles/reviewer_l1_unified_v1.0.md`
- `docs/09_prompts/v1.2/` (multiple files)

### Configuration
- `config/steward_runner.yaml`
- `config/governance/protected_artefacts.json`
- `config/invariants.yaml`
- `project_builder/context/tokenizer.py`

---

## Summary

**Bottom line:** The LifeOS codebase has solid architectural foundations for the Autonomous Build Loop. The orchestration engine, packet system, and database schema are production-ready. The main gap is operation handlers—the engine dispatches based on `step.kind` and `operation`, but only `noop`/`fail` are implemented. Adding `llm_call` is a 50-line change to `engine.py` plus an HTTP client to OpenCode (which already works). No architectural changes required.
