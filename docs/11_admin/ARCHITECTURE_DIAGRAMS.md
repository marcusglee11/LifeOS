> [!NOTE]
> **STATUS**: Non-Canonical (Information Only). This document is provided for context and architectural reference but is not an authoritative specification.

# LifeOS Architecture Diagrams

**Generated:** 2026-01-28 00:35 AEDT  
**Purpose:** Visual system architecture and agent interaction flows

---

## 1. Current System Architecture (As-Is)

### 1.1 High-Level Component View

```mermaid
graph TB
    subgraph "External Layer"
        USER[👤 User / CEO]
        OPENCODE[OpenCode<br/>Autonomous Agent]
        ANTIGRAVITY[Antigravity<br/>Interactive Agent]
    end
    
    subgraph "LifeOS Runtime"
        CLI[CLI Interface<br/>runtime/cli.py]
        AGENTS[Agent API Layer<br/>runtime/agents/]
        ORCH[Orchestration Engine<br/>runtime/orchestration/]
        GOV[Governance Layer<br/>runtime/governance/]
        SAFETY[Safety Gates<br/>runtime/safety/]
        STATE[State Store<br/>runtime/state/]
    end
    
    subgraph "Persistence"
        GIT[Git Repository<br/>Source of Truth]
        DOCS[Documentation<br/>docs/]
        ARTIFACTS[Evidence Store<br/>artifacts/]
    end
    
    USER -->|Commands| CLI
    USER -->|Manual Orchestration<br/>"Waterboy Mode"| OPENCODE
    USER -->|Interactive Sessions| ANTIGRAVITY
    
    CLI --> AGENTS
    AGENTS --> ORCH
    ORCH --> GOV
    GOV --> SAFETY
    
    ORCH --> STATE
    STATE --> GIT
    ORCH --> ARTIFACTS
    DOCS -.Governance Rules.-> GOV
    
    style USER fill:#95e1d3
    style OPENCODE fill:#ffd93d
    style ANTIGRAVITY fill:#ffd93d
```

---

### 1.2 Runtime Module Structure

```mermaid
graph LR
    subgraph "runtime/"
        AGENTS[agents/<br/>API, Models, Logging]
        ORCH[orchestration/<br/>Engine, Missions, Ops]
        GOV[governance/<br/>Policy, Enforcement]
        SAFETY[safety/<br/>Gates, Validation]
        MISSION[mission/<br/>Mission Types]
        REACTIVE[reactive/<br/>Reactive Layer]
        TOOLS[tools/<br/>Tool Integration]
        CONFIG[config/<br/>Configuration]
        STATE[state/<br/>State Management]
    end
    
    AGENTS -->|call_agent| ORCH
    ORCH -->|check_policy| GOV
    ORCH -->|validate| SAFETY
    ORCH -->|dispatch| MISSION
    MISSION -->|execute| REACTIVE
    ORCH -->|use| TOOLS
    CONFIG -.provides.-> AGENTS
    STATE -.persists.-> ORCH
```

---

## 2. Agent Interaction Flows (Current State)

### 2.1 Manual "Waterboy" Mode (Current Problem)

```mermaid
sequenceDiagram
    participant CEO as 👤 CEO<br/>(Waterboy)
    participant Designer as Designer Agent
    participant Builder as Builder Agent
    participant Council as Council Review<br/>(Manual)
    
    Note over CEO: Has high-level intent
    CEO->>Designer: "Design this feature"
    Designer->>CEO: Design response (YAML)
    
    Note over CEO: Manually transfers context
    CEO->>Builder: "Build per this design"
    Builder->>CEO: Implementation + evidence
    
    Note over CEO: Manually orchestrates review
    CEO->>Council: "Review this build"
    Note over Council: CEO runs multiple models<br/>manually, consolidates
    Council->>CEO: Review feedback
    
    Note over CEO: Manually decides next step
    CEO->>Builder: "Fix these issues"
    Builder->>CEO: Updated implementation
    
    Note over CEO,Builder: CEO is the critical path<br/>Can't scale, bottleneck
```

**Problem:** CEO manually shuttles context between agents (waterboy mode)

---

### 2.2 Target State: Autonomous Agent Flow

```mermaid
sequenceDiagram
    participant CEO as 👤 CEO
    participant Orch as Orchestrator Agent
    participant Designer as Designer Agent
    participant Builder as Builder Agent
    participant Council as Council Agent
    participant Evidence as Evidence Store
    
    CEO->>Orch: "Build feature X"
    Note over Orch: Creates task plan<br/>Tracks state
    
    Orch->>Designer: Design request + context
    Designer->>Orch: Design response
    Orch->>Evidence: Store design
    
    Orch->>Builder: Build request + design
    Builder->>Orch: Implementation + evidence
    Orch->>Evidence: Store build artifacts
    
    Orch->>Council: Review request + CCP
    Note over Council: Runs 9-seat review<br/>Autonomous
    Council->>Orch: Verdict + Fix Plan
    
    alt Verdict: PASS
        Orch->>CEO: ✅ "Feature complete"
    else Verdict: FIX
        Orch->>Builder: "Apply fixes"
        Builder->>Orch: Fixed implementation
        Orch->>Council: Re-review
    else Verdict: REJECT
        Orch->>CEO: ⚠️ "Needs CEO decision"
    end
    
    Note over CEO: Async oversight<br/>Intervenes by exception
```

**Benefit:** CEO sets intent, agents execute, CEO reviews async

---

## 3. Council Agent Architecture (Planned)

### 3.1 Council Agent Internal Structure

```mermaid
graph TD
    subgraph "Council Agent"
        INPUT[CCP Input<br/>YAML + AUR]
        PARSER[CCP Parser<br/>Validate schema]
        MODE[Mode Selector<br/>M0/M1/M2]
        
        subgraph "Execution Layer"
            CHAIR[Chair Agent<br/>Orchestrator]
            COCHAIR[Co-Chair Agent<br/>Validator]
            SEATS[Seat Executors<br/>9 Reviewers]
        end
        
        SYNTH[Chair Synthesis<br/>Verdict + Fix Plan]
        LOG[Log Writer<br/>Audit Trail]
        OUTPUT[Council Run Log<br/>Evidence]
    end
    
    INPUT --> PARSER
    PARSER --> MODE
    MODE -->|M0_FAST| SEATS
    MODE -->|M1_STANDARD| CHAIR
    MODE -->|M2_FULL| CHAIR
    
    CHAIR --> SEATS
    SEATS --> CHAIR
    CHAIR --> COCHAIR
    COCHAIR --> SYNTH
    SYNTH --> LOG
    LOG --> OUTPUT
    
    style INPUT fill:#4ecdc4
    style OUTPUT fill:#95e1d3
```

---

### 3.2 Council Review Workflow (M2_FULL)

```mermaid
sequenceDiagram
    participant User as Caller
    participant Chair as Chair Agent
    participant CoChair as Co-Chair
    participant Arch as Architect Seat
    participant Tech as Technical Seat
    participant Risk as Risk Seat
    participant Gov as Governance Seat
    participant Other as Other Seats (5)
    participant Log as Audit Log
    
    User->>Chair: Council Context Pack (CCP)
    Chair->>Chair: Validate CCP, select M2_FULL
    
    par Execute Seats in Parallel
        Chair->>Arch: Review architecture
        Chair->>Tech: Review implementation
        Chair->>Risk: Review failure modes
        Chair->>Gov: Review governance compliance
        Chair->>Other: Review other aspects
    end
    
    Arch->>Chair: Findings + evidence
    Tech->>Chair: Findings + evidence
    Risk->>Chair: Findings + evidence
    Gov->>Chair: Findings + evidence
    Other->>Chair: Findings + evidence
    
    Chair->>Chair: Aggregate findings<br/>Generate Contradiction Ledger
    Chair->>CoChair: Draft synthesis
    CoChair->>Chair: Challenge + validation
    
    Chair->>Chair: Final verdict + Fix Plan
    Chair->>Log: Write Council Run Log
    Log->>User: Complete audit trail
```

---

## 4. Orchestrator Agent Architecture (Planned)

### 4.1 Orchestrator Internal Structure

```mermaid
graph TB
    subgraph "Orchestrator Agent"
        INPUT[Task Input<br/>CEO Intent]
        PLANNER[Task Planner<br/>Manager-Led]
        DISPATCH[Dispatcher<br/>Route to agents]
        
        subgraph "Agent Registry"
            DESIGNER[Designer Agent]
            BUILDER[Builder Agent]
            COUNCIL[Council Agent]
            STEWARD[Doc Steward]
        end
        
        HANDOFF[Handoff Manager<br/>Context Transfer]
        STATE[State Tracker<br/>Progress Monitor]
        EVIDENCE[Evidence Collector<br/>Audit Trail]
        OUTPUT[Task Complete<br/>Report to CEO]
    end
    
    INPUT --> PLANNER
    PLANNER --> DISPATCH
    DISPATCH --> DESIGNER
    DISPATCH --> BUILDER
    DISPATCH --> COUNCIL
    DISPATCH --> STEWARD
    
    DESIGNER -.handoff.-> HANDOFF
    BUILDER -.handoff.-> HANDOFF
    COUNCIL -.handoff.-> HANDOFF
    
    HANDOFF --> STATE
    STATE --> DISPATCH
    DISPATCH --> EVIDENCE
    EVIDENCE --> OUTPUT
    
    style INPUT fill:#4ecdc4
    style OUTPUT fill:#95e1d3
```

---

### 4.2 Multi-Step Build Workflow

```mermaid
stateDiagram-v2
    [*] --> TaskReceived: CEO Request
    TaskReceived --> DesignPhase: Create plan
    
    DesignPhase --> BuildPhase: Design approved
    DesignPhase --> DesignReview: Design complete
    DesignReview --> DesignPhase: Fixes needed
    DesignReview --> BuildPhase: Approved
    
    BuildPhase --> BuildReview: Build complete
    BuildReview --> BuildPhase: Fixes needed
    BuildReview --> TestPhase: Approved
    
    TestPhase --> TestReview: Tests complete
    TestReview --> BuildPhase: Test failures
    TestReview --> CouncilReview: Tests pass
    
    CouncilReview --> BuildPhase: Council: Fix
    CouncilReview --> CEOEscalation: Council: Reject
    CouncilReview --> Complete: Council: Pass
    
    CEOEscalation --> BuildPhase: CEO: Rework
    CEOEscalation --> Complete: CEO: Accept
    
    Complete --> [*]: Report to CEO
```

---

## 5. Data Flow Architecture

### 5.1 Evidence & Audit Trail Flow

```mermaid
graph LR
    subgraph "Inputs"
        INTENT[CEO Intent]
        SPEC[Specifications]
        CODE[Code Changes]
    end
    
    subgraph "Processing"
        DESIGNER[Designer Agent]
        BUILDER[Builder Agent]
        COUNCIL[Council Agent]
    end
    
    subgraph "Outputs"
        DESIGN[Design Artifacts]
        BUILD[Build Evidence]
        REVIEW[Review Logs]
    end
    
    subgraph "Persistence"
        GIT[Git Commits]
        ARTIFACTS[artifacts/]
        LOGS[Audit Logs]
    end
    
    INTENT --> DESIGNER
    SPEC --> DESIGNER
    DESIGNER --> DESIGN
    
    DESIGN --> BUILDER
    CODE --> BUILDER
    BUILDER --> BUILD
    
    BUILD --> COUNCIL
    COUNCIL --> REVIEW
    
    DESIGN --> ARTIFACTS
    BUILD --> GIT
    REVIEW --> LOGS
    
    ARTIFACTS -.referenced.-> GIT
    LOGS -.referenced.-> ARTIFACTS
```

---

## 6. Tier Architecture (LifeOS Layers)

### 6.1 Tier Structure

```mermaid
graph TB
    subgraph "Tier 3 - Autonomous Construction"
        T3_ORCH[Orchestrator Agent]
        T3_COUNCIL[Council Agent]
        T3_PLANNER[Task Planner]
    end
    
    subgraph "Tier 2 - Execution & Governance"
        T2_DESIGNER[Designer Agent]
        T2_BUILDER[Builder Agent]
        T2_STEWARD[Doc Steward]
        T2_GOV[Governance Engine]
    end
    
    subgraph "Tier 1 - Foundation"
        T1_RUNTIME[Runtime Core]
        T1_AGENTS[Agent API]
        T1_SAFETY[Safety Gates]
        T1_STATE[State Store]
    end
    
    T3_ORCH --> T2_DESIGNER
    T3_ORCH --> T2_BUILDER
    T3_COUNCIL --> T2_GOV
    
    T2_DESIGNER --> T1_AGENTS
    T2_BUILDER --> T1_AGENTS
    T2_GOV --> T1_SAFETY
    
    T1_AGENTS --> T1_RUNTIME
    T1_SAFETY --> T1_RUNTIME
    T1_STATE --> T1_RUNTIME
    
    style T3_ORCH fill:#95e1d3
    style T3_COUNCIL fill:#95e1d3
```

**Current Status:**
- ✅ Tier 1: Complete (Foundation operational)
- ✅ Tier 2: Mostly complete (Governance operational, agents external)
- ⏳ Tier 3: In progress (Council Agent building, Orchestrator planned)

---

## 7. Deployment Architecture

### 7.1 Execution Environments

```mermaid
graph TB
    subgraph "Development"
        DEV_LOCAL[Local Dev<br/>Interactive]
        DEV_OPENCODE[OpenCode Server<br/>localhost:4096]
    end
    
    subgraph "CI/CD"
        CI_RUNNER[OpenCode CI Runner<br/>scripts/opencode_ci_runner.py]
        CI_TESTS[Test Suite<br/>97 tests]
        CI_GATES[Safety Gates<br/>Validation]
    end
    
    subgraph "Production"
        PROD_AGENTS[Agent Cluster<br/>24/7 Operation]
        PROD_STATE[State Persistence<br/>Git + Artifacts]
        PROD_AUDIT[Audit Trail<br/>Immutable Logs]
    end
    
    DEV_LOCAL --> CI_RUNNER
    DEV_OPENCODE --> CI_RUNNER
    CI_RUNNER --> CI_TESTS
    CI_TESTS --> CI_GATES
    CI_GATES -->|Pass| PROD_AGENTS
    
    PROD_AGENTS --> PROD_STATE
    PROD_AGENTS --> PROD_AUDIT
```

---

## 8. Integration Points

### 8.1 External Tool Integration

```mermaid
graph LR
    subgraph "LifeOS Core"
        RUNTIME[Runtime]
    end
    
    subgraph "AI Providers"
        OPENROUTER[OpenRouter<br/>Multi-model]
        ANTHROPIC[Anthropic<br/>Claude]
        OPENCODE_API[OpenCode<br/>Gemini/GPT]
    end
    
    subgraph "Development Tools"
        GIT[Git<br/>Version Control]
        PYTEST[Pytest<br/>Testing]
        SCRIPTS[Scripts<br/>Automation]
    end
    
    subgraph "Infrastructure"
        FS[Filesystem<br/>State Store]
        ENV[Environment<br/>Secrets]
    end
    
    RUNTIME --> OPENROUTER
    RUNTIME --> ANTHROPIC
    RUNTIME --> OPENCODE_API
    
    RUNTIME --> GIT
    RUNTIME --> PYTEST
    RUNTIME --> SCRIPTS
    
    RUNTIME --> FS
    RUNTIME --> ENV
```

---

## 9. Security & Governance Boundaries

```mermaid
graph TD
    subgraph "Untrusted Zone"
        EXTERNAL[External Input<br/>User/API]
    end
    
    subgraph "Validation Layer"
        INPUT_VAL[Input Validation]
        POLICY[Policy Engine]
    end
    
    subgraph "Execution Zone (Sandboxed)"
        AGENTS[Agent Execution]
        TOOLS[Tool Usage]
    end
    
    subgraph "Governance Layer"
        REVIEW[Council Review]
        AUDIT[Audit Log]
    end
    
    subgraph "Trusted Zone"
        COMMIT[Git Commit]
        PROD[Production State]
    end
    
    EXTERNAL --> INPUT_VAL
    INPUT_VAL --> POLICY
    POLICY -->|Approved| AGENTS
    POLICY -->|Rejected| EXTERNAL
    
    AGENTS --> TOOLS
    TOOLS --> REVIEW
    REVIEW -->|Pass| COMMIT
    REVIEW -->|Fail| AGENTS
    
    COMMIT --> PROD
    AGENTS --> AUDIT
    REVIEW --> AUDIT
    
    style EXTERNAL fill:#ff6b6b
    style COMMIT fill:#95e1d3
    style PROD fill:#95e1d3
```

---

## 10. Roadmap: Current → Target State

```mermaid
timeline
    title LifeOS Architecture Evolution
    
    section Phase 3 (Current)
        Tier 1/2 Complete : Runtime operational
                          : Manual orchestration
                          : External agents (OpenCode)
    
    section Phase 4 (Week 2)
        Council Agent : Autonomous reviews
                      : Exit waterboy for reviews
                      : Multi-model governance
    
    section Phase 4 (Week 4)
        Orchestrator Agent : Autonomous dispatch
                           : Designer→Builder→Council
                           : State tracking
    
    section Rung 2 (Week 4)
        Supervised Chains : Multi-step workflows
                          : Checkpoint approval
                          : Audit trail complete
    
    section Future
        Tier 3 Complete : Delegated domains
                        : Autonomous initiative
                        : Full autonomy
```

---

**Maintained in:** `/home/cabra/clawd/lifeos/docs/11_admin/ARCHITECTURE_DIAGRAMS.md`  
**Format:** Mermaid (visual rendering)  
**Last Updated:** 2026-01-28 00:35 AEDT
