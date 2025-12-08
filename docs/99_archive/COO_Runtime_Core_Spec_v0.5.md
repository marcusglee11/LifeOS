# **COO Multi-Agent System Specification v0.5-FINAL**
**"The Deterministic Agent Runtime"**

---

## **Document Control**
- **Version**: 0.5-FINAL
- **Date**: 2025-11-19
- **Status**: Pre-Implementation (Ready for Build)
- **Maintainer**: Kimi (Primary Engineer)
- **Reviewers**: ChatGPT (Co-Architect), Gemini (Security), GLM-4.6 (Micro-Tasks)
- **Change Log**: Integrated all amendments from Claude/Gemini/GLM review cycle

---

## **1. Executive Summary**

Build a **self-directed multi-agent system** where:
- **CEO (you)** provides natural-language missions via chat
- **COOAgent** plans and decomposes work
- **EngineerAgent** writes code and requests execution
- **QAAgent** reviews and gates execution
- All communication via **SQLite message bus** (no OpenAI runtime dependency)
- **Hard budget enforcement** (deterministic, no LLM self-estimation)
- **Network-isolated Docker sandbox** (no exceptions)
- **Multi-mission from day one** (bounded concurrency)
- **Crash recovery** with heartbeat-based message reclaim
- **Streaming UX**: CEO sees live progress via `STREAM` messages

**Shippable in ~6 weeks (solo dev).**

---

## **2. Goals & Non-Goals**

### **2.1 Goals (v1.0)**
1. Single orchestrator binary (`coo`) that runs multiple missions concurrently
2. COO → Engineer → QA message flow with approval gates
3. Code execution in **network-none, non-root Docker containers**
4. **Hard cap budget enforcement** with transaction rollback on exceed
5. **Streaming UX**: CEO sees live progress via `STREAM` messages
6. **Crash recovery**: Messages reclaimed after agent timeout
7. **Backpressure**: Hard pause if mission generates >50 pending messages
8. **Observability**: Structured JSON logs + DB timeline events

### **2.2 Non-Goals (v1.0 Explicit)**
- **No task DAG or dependency graph** (linear task lists only)
- **No conversation summary tables** (context window management only)
- **No alerting subsystem** (CLI status only)
- **No circuit breaker infrastructure** (simple pause logic)
- **No config schema migrations** (YAML files only)
- **No multi-worker orchestrators** (single process only)
- **No multi-storage artifact system** (inline TEXT only)
- **No async HTTP clients** (ThreadPoolExecutor for blocking calls)

---

## **3. High-Level Architecture**

```
CEO (CLI Chat)
    ↑↓
┌─────────────────────────────────────────┐
│  Orchestrator (Single Python Process)   │
│  - Asyncio main loop                    │
│  - ThreadPoolExecutor for LLM calls     │
│  - BudgetGuard (pre/post call)          │
│  - MessageStore (SQLite with WAL)       │
│  - Sandbox handler (direct SANDBOX_RUN) │
└─────────────────────────────────────────┘
    ↑↓ (message bus)
┌──────────┬──────────┬──────────┐
│ COOAgent │ Engineer │ QAAgent  │
│ (Planner)│ (Coder)  │ (Reviewer)│
└──────────┴──────────┴──────────┘
    ↓ (SANDBOX_RUN)
┌─────────────────────────────────────────┐
│  Docker Sandbox (Ephemeral, No Network)│
│  - Bind mount temp workspace           │
│  - Non-root user (1000:1000)           │
│  - Resource limits (512m RAM, 50% CPU) │
│  - --security-opt=no-new-privileges    │
│  - Readonly rootfs (v1.1)              │
└─────────────────────────────────────────┘
    ↓ (artifacts)
┌─────────────────────────────────────────┐
│  SQLite DB (coo.db, WAL mode)          │
│  - messages (durable queue)            │
│  - missions (FSM state)                │
│  - artifacts (inline content)          │
│  - sandbox_runs (idempotency)          │
│  - budget tracking                     │
└─────────────────────────────────────────┘
```

---

## **4. Detailed Specification**

### **4.1 Persistence Layer (SQLite)**

**File**: `~/.local/share/coo/coo.db` (WAL mode)

**Connection Settings:**
```python
# In message_store.py
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;        # Wait 5s on lock conflict
```

**Core Tables:**

```sql
-- Missions table
CREATE TABLE missions (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,               -- created, planning, executing, reviewing, paused_*, completed, failed
    previous_status TEXT,               -- for resuming from paused_*
    description TEXT NOT NULL,
    config_json TEXT NOT NULL,          -- {max_cost_usd, max_loops, priority, safety_margin}
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    completed_at DATETIME,
    failed_at DATETIME,
    failure_reason TEXT,
    spent_cost_usd REAL NOT NULL DEFAULT 0,
    loop_count INTEGER NOT NULL DEFAULT 0,
    message_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_missions_status ON missions(status);

-- Messages = durable queue
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id),
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    kind TEXT NOT NULL,                 -- TASK, RESULT, STREAM, ERROR, APPROVAL, SANDBOX_RUN, CONTROL, QUESTION, SYSTEM
    status TEXT NOT NULL,               -- pending, processing, delivered, failed, expired
    body_json TEXT NOT NULL,            -- JSON string
    schema_version INTEGER NOT NULL DEFAULT 1,
    
    priority INTEGER NOT NULL DEFAULT 5,
    correlation_id TEXT,
    conversation_id TEXT,
    in_reply_to TEXT,
    
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    timeout_at DATETIME,
    locked_at DATETIME,                 -- Last heartbeat timestamp
    locked_by TEXT,                     -- Worker ID
    
    error_type TEXT,
    error_detail TEXT,
    
    created_at DATETIME NOT NULL,
    processed_at DATETIME
);
CREATE INDEX idx_messages_pending ON messages(to_agent, status, mission_id) WHERE status = 'pending';
CREATE INDEX idx_messages_mission ON messages(mission_id, created_at);

-- Artifacts (v1: inline content only)
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id),
    type TEXT NOT NULL,                 -- code, text, json, log, binary
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    content TEXT NOT NULL,              -- inline TEXT (files < 1MB)
    storage_type TEXT NOT NULL DEFAULT 'inline',
    path TEXT,                          -- future: filesystem path for large files
    checksum TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    created_by TEXT NOT NULL
);
CREATE INDEX idx_artifacts_mission ON artifacts(mission_id, created_at);

-- Agents registry
CREATE TABLE agents (
    name TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    status TEXT NOT NULL,               -- active, disabled
    last_active DATETIME,
    error_streak INTEGER NOT NULL DEFAULT 0,
    total_invocations INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0,
    avg_duration_ms REAL,
    success_rate REAL,
    capabilities_json TEXT,
    config_json TEXT                    -- {max_tokens_per_call, temperature}
);

-- Dead-letter queue
CREATE TABLE dead_letters (
    id TEXT PRIMARY KEY,
    original_message_id TEXT NOT NULL REFERENCES messages(id),
    mission_id TEXT NOT NULL REFERENCES missions(id),
    failed_at DATETIME NOT NULL,
    error_type TEXT NOT NULL,
    error_detail TEXT,
    retry_count INTEGER NOT NULL,
    payload_snapshot TEXT NOT NULL
);
CREATE INDEX idx_dead_letters_mission ON dead_letters(mission_id, failed_at);

-- Timeline events (append-only)
CREATE TABLE timeline_events (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id),
    event_type TEXT NOT NULL,           -- agent_invoked, state_transition, cost_update, sandbox_run, error
    event_json TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
CREATE INDEX idx_timeline_mission ON timeline_events(mission_id, created_at);

-- Budget tracking
CREATE TABLE budgets_global (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    daily_budget_usd REAL NOT NULL,
    daily_spent_usd REAL NOT NULL DEFAULT 0,
    monthly_budget_usd REAL NOT NULL,
    monthly_spent_usd REAL NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL
);

-- Sandbox runs (idempotency)
CREATE TABLE sandbox_runs (
    dedupe_id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL REFERENCES missions(id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    result_artifact_id TEXT,
    exit_code INTEGER,
    created_at DATETIME NOT NULL
);
CREATE INDEX idx_sandbox_runs_mission ON sandbox_runs(mission_id, created_at);
```

---

### **4.2 Messaging Protocol**

**Canonical Message Structure:**
```json
{
  "id": "msg_001",
  "schema_version": 1,
  "from_agent": "COO",
  "to_agent": "Engineer",
  "mission_id": "m_42",
  "conversation_id": "conv_001",
  "in_reply_to": null,
  "priority": 5,
  "kind": "TASK",
  "status": "pending",
  "retry_count": 0,
  "max_retries": 3,
  "timeout_at": "2025-01-20T15:00:00Z",
  "created_at": "2025-01-20T14:30:00Z",
  "body_json": {
    "action": "implement_feature",
    "summary": "Create Fibonacci function",
    "details": "Implement fibonacci(n) with docstring",
    "context_refs": ["artifact_codebase_main"],
    "required_capabilities": ["python"]
  },
  "meta": {
    "correlation_id": "corr_abc123",
    "checksum": "sha256:..."
  }
}
```

**Complete Message Kinds (v1 Protocol):**
- `TASK` - Request to perform work
- `RESULT` - Response with output/artifact
- `STREAM` - Incremental progress update (live UX)
- `ERROR` - Failure report with `error_type`
- `APPROVAL` - CEO/QA approval/rejection gate
- `SANDBOX_RUN` - System command to execute code (idempotent)
- `CONTROL` - System-level instructions (pause, resume, budget increase)
- `QUESTION` - Clarification request
- `SYSTEM` - Internal orchestration messages

---

### **4.3 Agent Interface (Async Generator)**

**File**: `agent.py`

```python
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List
from dataclasses import dataclass

@dataclass
class Emission:
    type: str  # "message" | "side_effect" | "sandbox_run"
    data: Dict[str, Any]

class Agent(ABC):
    name: str
    timeout_seconds: int = 300

    @abstractmethod
    def process_stream(
        self, mission: Dict[str, Any], messages: List[Dict[str, Any]]
    ) -> Generator[Emission, None, None]:
        """
        Blocking generator that yields emissions as work progresses:
        - Emission(type="message", data={...}) → STREAM/RESULT/etc
        - Emission(type="side_effect", data={cost_delta_usd, state_transition, ...})
        - Emission(type="sandbox_run", data={artifact_id, entrypoint, timeout, dedupe_id})
        
        Must be deterministic/idempotent for same inputs.
        Agent updates `locked_at` heartbeat every ~30s by yielding side_effects.
        """
        pass

    def process(self, mission, messages):
        """Legacy one-shot (default impl). Override for streaming agents."""
        raise NotImplementedError
```

**Context Window Management (v1):**
- **Always included**: Mission description, config
- **Last K messages**: K = 5 (hardcoded in v1)
- **No summarization**: Older messages dropped silently
- **No vector DB**: All context in prompt text

---

### **4.4 Mission Lifecycle (FSM)**

**States:**
- `created` → `planning` → `executing` → `reviewing` → `completed`
- `paused_budget`, `paused_approval`, `paused_error`, `paused_manual`, `failed`

**Transitions:**
| From | Event | To | Guard |
|------|-------|----|-------|
| `created` | `plan_ready` | `planning` | COO finished plan |
| `planning` | `budget_exhausted` | `paused_budget` | Pre-check failed |
| `executing` | `budget_exceeded` | `failed` | Post-call rollback |
| `executing` | `approval_requested` | `paused_approval` | Budget increase needed |
| `executing` | `backpressure_exceeded` | `paused_error` | >50 pending messages |
| `any` | `manual_pause` | `paused_manual` | CEO CONTROL message |
| `any` | `_fatal_error` | `failed` | Unrecoverable error |

**Implementation**: `StateManager.transition(mission_id, event)` validates, updates DB, writes timeline event, logs.

---

### **4.5 Budget & Cost Governance**

**Hard Cap Rules (Deterministic):**

1. **Per-agent token limits** (enforced in `ModelClient`, no LLM override):
   ```yaml
   agents:
     COO: { max_tokens_per_call: 6000 }
     Engineer: { max_tokens_per_call: 8000 }
     QA: { max_tokens_per_call: 4000 }
   ```

2. **Pre-call check** (Governor):
   ```python
   worst_case = agent.max_tokens_per_call * pricing[model]["output_per_1k"] / 1000
   if spent + worst_case > max_cost * 0.95:
       transition(mission_id, "paused_budget")
   ```

3. **Post-call enforcement** (BudgetGuard):
   ```python
   def commit(self, actual_cost: float, actual_tokens: int):
       if actual_tokens > self.token_limit:
           raise SecurityViolation()
       self.spent += actual_cost
       if self.spent > self.max_cost:
           raise BudgetExceededError()  # triggers rollback
   ```

4. **Rollback**: Each LLM call wrapped in DB transaction. On `BudgetExceededError`:
   - Delete artifacts from this transaction
   - Revert `missions.spent_cost_usd`
   - Transition to `failed`
   - Emit timeline event

5. **Budget increase limit**: Max 3 requests per mission, then `paused_error`.

---

### **4.6 Sandbox Execution (Direct SANDBOX_RUN)**

**Message Kind**: `SANDBOX_RUN` (system-handled, not LLM-routed)

**Body Schema:**
```json
{
  "artifact_id": "art_123",
  "entrypoint": "python main.py",
  "timeout": 300,
  "dedupe_id": "msg_001"  # Use message.id for idempotency
}
```

**Orchestrator Flow:**
1. Check `dedupe_id` in `sandbox_runs` table
2. Materialize artifact to `/tmp/coo-workspace/{mission_id}/`
3. **Docker run**:
   ```bash
   docker run --rm \
     --network none \
     --user 1000:1000 \
     --security-opt=no-new-privileges \
     -m 512m --cpu-quota=50000 \
     -v /tmp/coo-workspace:/workspace \
     coo-sandbox:latest \
     bash -c "cd /workspace && {entrypoint}"
   ```
4. Capture stdout/stderr, exit code
5. Store result as artifact (`type: log`)
6. Insert `sandbox_runs` row with `dedupe_id`
7. Emit RESULT message to QA/COO

**Security (Non-Negotiable):**
- `--network none` (no internet, ever)
- `--user 1000:1000` (non-root)
- `--security-opt=no-new-privileges` (no privilege escalation)
- Resource limits: 512m RAM, 50% CPU
- **Fat image**: `coo-sandbox:latest` pre-baked with Python, pytest, safe libs. **No `pip install` allowed.**
- **Docker failure**: If daemon unreachable → mission `failed`, no unsandboxed fallback.

---

### **4.7 Observability**

**Structured Logging** (stdout, JSON, secret-scrubbed):
```python
import structlog

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
log = structlog.get_logger()

# Scrub secrets before logging
def scrub_secrets(data: dict) -> dict:
    # Remove API keys, tokens from log payload
    return {k: v for k, v in data.items() if "key" not in k.lower()}

# Log all key events:
log.info("coo_started", db_path="...", version="0.5")
log.info("mission_state_changed", mission_id=mid, from_state=old, to_state=new, event=event)
log.info("llm_call", mission_id=mid, agent="Engineer", model="deepseek-v3",
         prompt_tokens=1200, completion_tokens=800, cost_usd=0.0028)
log.warning("mission_backpressure", mission_id=mid, pending=55)
log.error("agent_error", mission_id=mid, agent="Engineer", error_type="timeout")
log.info("sandbox_run", mission_id=mid, artifact_id=art_id, exit_code=0)
```

**CLI Metrics** (DB queries):
```bash
coo status                    # Active missions + spent budgets
coo mission m_42              # Detail: state, cost, loops, messages
coo logs --mission m_42 --tail 50
coo dlq list
coo metrics --daily           # Daily/monthly spend
```

**Secret Scrubbing**: Apply to log payloads only. DB stores full message bodies for debugging.

---

### **4.8 Backpressure & Failure Modes**

**Hard Backpressure Rule**:
```python
MAX_PENDING_PER_MISSION = 50

pending = await store.count_pending_messages(mission_id)
if pending > MAX_PENDING_PER_MISSION:
    await state_manager.transition(mission_id, "paused_error", reason="backpressure")
    log.warning("mission_paused_backpressure", mission_id=mission_id, pending=pending)
    return  # Stop scheduling work for this mission
```

**Docker Failure Mode**:
```python
try:
    result = sandbox.run(...)
except DockerError as e:
    log.error("sandbox_unavailable", mission_id=mid, error=str(e))
    await state_manager.transition(mission_id, "failed", reason="sandbox_error")
    # No fallback to unsandboxed execution
```

---

## **5. Build Plan (5 Phases, ~6 Weeks)**

### **Phase 0: Core Infrastructure (4-5 days)**
- ✅ SQLite schema + migrations
- ✅ MessageStore async methods (`claim_pending`, `deliver_message`, `reclaim_stale`)
- ✅ Models (Pydantic schemas)
- ✅ CLI skeleton: `coo init-db`, `coo status`
- **Commit**: `git commit -m "Phase 0: Core DB and message bus"`

### **Phase 1: Orchestrator + Dummy Agents (3-4 days)**
- ✅ `orchestrator.py` with asyncio main loop + ThreadPoolExecutor
- ✅ `Agent` base class + `process_stream` generator
- ✅ `DummyCOO`, `DummyEngineer`, `DummyQA` emitting emissions
- ✅ `BudgetTracker` skeleton
- ✅ End-to-end test: mission flow with no LLMs
- **Commit**: `git commit -m "Phase 1: Orchestrator + dummy agents"`

### **Phase 2: Sandbox Integration (4-5 days)**
- ✅ Build `coo-sandbox:latest` Dockerfile (Python, pytest, std libs)
- ✅ `sandbox.py` Docker wrapper (`--network none`, resource limits)
- ✅ Orchestrator handles `SANDBOX_RUN` emissions
- ✅ Artifact materialization to bind mount
- ✅ Result artifact storage + RESULT message emission
- ✅ Test: Engineer → Sandbox → QA
- **Commit**: `git commit -m "Phase 2: Network-isolated sandbox"`

### **Phase 3: Real LLM Agents + Budget (7-10 days)**
- ✅ `ModelClient` for DeepSeek + GLM (sync HTTP in thread pool)
- ✅ Central token caps enforcement (`max_tokens_per_call`)
- ✅ COO/Engineer/QA prompts via `PromptManager`
- ✅ Cost calculation from API responses
- ✅ **Hard budget enforcement + rollback on exceed**
- ✅ Global daily/monthly budget tracking
- ✅ Test: budget exceed → rollback verified
- **Commit**: `git commit -m "Phase 3: Real LLM agents + budget safety"`

### **Phase 4: Observability + Hardening (5-7 days)**
- ✅ `structlog` integration with secret scrubbing
- ✅ Timeline events for all major actions
- ✅ CLI commands: `coo mission`, `coo logs`, `coo dlq`
- ✅ Approval flow (CEO gate) + CONTROL messages
- ✅ Backpressure hard pause implementation
- ✅ **Integration tests**: happy path, error path, budget exceed, sandbox failure
- ✅ README + operations guide
- **Commit**: `git commit -m "Phase 4: Observability + approval gates"`

### **v1.0 Definition of Done**
- Single mission end-to-end works: CEO → COO → Engineer → Sandbox → QA → COO → Completed
- Budget enforcement tested (simulate exceed → rollback observed)
- Sandbox security verified (`--network none`, non-root, resource limits)
- Crash recovery tested (kill -9 orchestrator → restart → reclaim works)
- CLI UX: create mission, watch logs, inspect DLQ, check budget
- All critical paths covered by at least one integration test

---

## **6. Review Gates for AI Team**

### **When to Pause for ChatGPT (/review-gpt)**
- Agent interface changes (e.g., adding new emission types)
- Orchestrator concurrency model adjustments
- BudgetGuard logic modifications (pre/post call checks)
- Message protocol changes (new kinds, field removals)
- FSM transition table changes

### **When to Pause for Gemini (/review-gemini)**
- Sandbox security policy (network, user privileges, readonly rootfs)
- DB schema (privilege isolation, SQL injection risks)
- Overall architecture (coupling, complexity, over-engineering)
- Docker image supply chain (fat image vs dynamic install)

### **When to Delegate to GLM (/glm)**
- Pydantic model boilerplate
- pytest fixtures and stubs
- CLI argument parsing (click/typer)
- GitHub Actions YAML for CI
- README formatting and examples

---

## **7. Implementation Starter Code (Phase 0)**

**File: `coo/main.py`**
```python
import asyncio
import structlog
from pathlib import Path
from message_store import MessageStore
from budget import BudgetTracker

structlog.configure(processors=[structlog.processors.JSONRenderer()])
log = structlog.get_logger()

async def main():
    db_path = Path.home() / ".local/share/coo/coo.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    store = MessageStore(db_path)
    budget = BudgetTracker()
    
    await store.initialize()
    log.info("coo_started", db_path=str(db_path), version="0.5")
    
    # TODO: Implement Orchestrator
    # orchestrator = Orchestrator(store, budget, config)
    # await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**File: `coo/message_store.py` (Skeleton)**
```python
import aiosqlite
from pathlib import Path

class MessageStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL")
            await db.execute("PRAGMA synchronous = NORMAL")
            await db.execute("PRAGMA busy_timeout = 5000")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    locked_at DATETIME,
                    locked_by TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def claim_pending_messages(self, to_agent: str, mission_id: str, limit: int = 1) -> list[dict]:
        # TODO: Atomic UPDATE...RETURNING
        pass
    
    async def deliver_message(self, msg: dict):
        # TODO: INSERT into messages
        pass
```

---

## **8. Optional Features (v1.1+ Roadmap)**

These are **documented but not implemented** in v1.0:

- **DLQ replay CLI**: `coo dlq replay <id>` (v1.1)
- **Backup/restore tooling**: `coo backup`, `coo restore` (v1.1)
- **Agent enable/disable**: `coo agent disable Engineer` (v1.1)
- **Prometheus metrics endpoint**: `/metrics` (v1.1)
- **Async HTTP clients**: Replace ThreadPoolExecutor with `httpx.AsyncClient` (v1.1)
- **Message sequence numbers**: For ordering guarantees (v1.1)

---

## **9. Non-Goals (Explicitly Excluded)**

To prevent scope creep, **v1.0 will NOT include**:
- Task DAG or dependency graph
- Conversation summary tables or vector DB
- Alerting subsystem (PagerDuty, Slack)
- Circuit breaker infrastructure (Hystrix-style)
- Config schema migrations (semver config files)
- Multi-worker orchestrators (distributed mode)
- Multi-storage artifact system (S3, etc.)
- Advanced memory retrieval (RAG)

---

## **10. Next Steps for Implementation**

1. **Create repo**: `mkdir coo-agent && cd coo-agent && git init`
2. **Copy spec**: Save this file as `ARCHITECTURE-v0.5-FINAL.md`
3. **Create virtual env**: `python -m venv venv && source venv/bin/activate`
4. **Install deps**: `pip install aiosqlite structlog pydantic pytest`
5. **Phase 0**: Implement `message_store.py` and `main.py` skeleton
6. **Commit**: `git commit -m "Phase 0: Core DB skeleton"`
7. **Launch Claude Code**: `claude` with system prompt referencing this spec

**Build order**: Follow Phase 0 → Phase 4 sequentially. Do not skip.