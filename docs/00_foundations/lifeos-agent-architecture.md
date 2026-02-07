# LifeOS Agent Architecture

## Document Status
- **Version:** 0.1
- **Created:** 2026-02-05
- **Purpose:** Reference architecture for two-agent LifeOS bootstrap system

---

## 1. Vision

### 1.1 The Problem
LifeOS requires autonomous execution capability to fulfill its purpose. The system cannot govern what it cannot do. Current state: extensive governance design, no autonomous execution.

### 1.2 The Solution
Bootstrap LifeOS through two complementary agents:

1. **Employee** — Exploration probe that discovers what autonomous agents can do, without committing identity or reputation
2. **COO** — Orchestration seed that evolves from advisor-with-hands into the LifeOS kernel itself

### 1.3 Key Principles

| Principle | Meaning |
|-----------|---------|
| **Probe before commit** | Employee tests the space; learnings inform architecture |
| **Bootstrap, not integrate** | COO doesn't connect to LifeOS; COO becomes LifeOS |
| **Governance follows capability** | Prove execution, then add oversight |
| **Asset, not avatar** | Employee is owned, not identified with |
| **Seed, not tool** | COO is infrastructure, not peripheral |

---

## 2. Two-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PRINCIPAL (CEO)                            │
│                                                                         │
│   Provides: Direction, judgment, approval, identity, relationships      │
│   Retains: Key relationships, final decisions, signature authority      │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌─────────────────────────────┐ ┌─────────────────────────────────────────┐
│     EMPLOYEE (GCP)          │ │              COO (Local)                │
│                             │ │                                         │
│  Nature: Exploration probe  │ │  Nature: LifeOS kernel seed             │
│  Identity: Separate entity  │ │  Identity: LifeOS infrastructure        │
│  Stability: Production      │ │  Stability: Experimental                │
│  Codebase: Tracks upstream  │ │  Codebase: Can diverge                  │
│                             │ │                                         │
│  ┌───────────────────────┐  │ │  ┌───────────────────────────────────┐  │
│  │ Capabilities         │  │ │  │ Capabilities                      │  │
│  │ • Research           │  │ │  │ • LifeOS codebase interaction     │  │
│  │ • Drafting           │  │ │  │ • Governance operations           │  │
│  │ • Admin execution    │  │ │  │ • Agent orchestration             │  │
│  │ • Monitoring         │  │ │  │ • State management                │  │
│  │ • Information gather │  │ │  │ • Development execution           │  │
│  │ • Memory building    │  │ │  │ • Strategic advisory              │  │
│  └───────────────────────┘  │ │  └───────────────────────────────────┘  │
│                             │ │                                         │
│  Memory: Gemini embeddings  │ │  Memory: LifeOS-native state docs       │
│  Accounts: All dedicated    │ │  Accounts: LifeOS infrastructure        │
│  Uptime: Always on          │ │  Uptime: Development sessions           │
│                             │ │                                         │
│  Future: External agent     │ │  Future: The kernel itself              │
│          LifeOS avatar      │ │          Core of the core               │
└─────────────────────────────┘ └─────────────────────────────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   Shared State      │
                  │   (Google Drive)    │
                  │                     │
                  │ • Current focus     │
                  │ • Decisions         │
                  │ • Learnings         │
                  │ • Handoffs          │
                  └─────────────────────┘
```

---

## 3. Employee Specification

### 3.1 Purpose
Exploration probe that discovers autonomous agent capabilities without committing principal's identity or reputation. Information and capability accrue to principal; actions and identity belong to Employee.

### 3.2 Core Attributes

| Attribute | Value |
|-----------|-------|
| **Relationship to Principal** | Asset owned, not extension of self |
| **Representation** | Does not represent principal |
| **Identity** | Separate entity with own accounts |
| **Risk profile** | Contained; failures don't damage principal |
| **Information flow** | Learnings flow to principal |
| **Action authority** | Within charter, no principal commitment |

### 3.3 Capabilities

**Enabled:**
- Web research and information synthesis
- Document drafting and editing
- Calendar and scheduling management
- Email (from its own account)
- Administrative task execution
- Monitoring (news, markets, triggers)
- Memory building and retrieval
- Browser automation (sandboxed)
- File operations (sandboxed)

**Gated (approval required):**
- External commitments
- Spending above threshold
- Contact with specified individuals
- Account creation
- Irreversible actions

**Prohibited:**
- Representing principal
- Accessing principal's accounts
- Making promises on principal's behalf
- Actions requiring principal's identity

### 3.4 Identity Setup

```
Name:           [To be chosen - distinct from principal]
Email:          employee@[domain] or dedicated Gmail
Calendar:       Dedicated, shared read-access to principal
GitHub:         lifeos-employee (if needed)
API Keys:       All dedicated accounts
Browser:        Dedicated profile
Payment:        Dedicated method with spending limits
```

### 3.5 Memory Architecture

```
~/.openclaw/workspace-employee/
├── AGENTS.md           # Operating instructions
├── SOUL.md             # Identity and boundaries  
├── USER.md             # Principal profile (what Employee knows about CEO)
├── CHARTER.md          # Autonomy boundaries and escalation rules
├── MEMORY.md           # Curated long-term memory
├── memory/
│   └── YYYY-MM-DD.md   # Daily logs
├── bank/
│   ├── world.md        # Objective facts learned
│   ├── capabilities.md # What Employee can/can't do (discovered)
│   ├── patterns.md     # Useful patterns discovered
│   └── entities/
│       ├── [Person].md
│       ├── [Company].md
│       └── [Project].md
└── reports/
    └── YYYY-MM-DD.md   # Daily summaries for principal
```

**Embedding Strategy:**
- Gemini embeddings for semantic search
- Local vector store (QMD or equivalent)
- Periodic consolidation (weekly reflection)
- Entity extraction and linking

### 3.6 Charter Template

```markdown
# Employee Charter

## Identity
I am Employee, an autonomous agent operating under CEO's direction.
I am not CEO. I do not represent CEO. My actions are my own.
What I learn and build accrues to CEO's benefit.

## Scope
- Research and information gathering
- Document drafting and synthesis
- Administrative execution
- Monitoring and alerting
- Exploratory conversations
- Capability discovery
- Memory building

## Autonomy Levels

### GREEN — Act without asking
- Web research
- Document drafting (not sending)
- Information synthesis
- Calendar management (own calendar)
- Memory updates
- File operations (own workspace)
- Exploratory thinking

### YELLOW — Act, then report
- Sending emails (from own account)
- Scheduling with external parties
- Creating accounts/signups (within budget)
- Spending under $[X]
- Contacting non-restricted individuals

### RED — Ask first, then act
- Any commitment or promise
- Spending over $[X]
- Contact with restricted individuals: [list]
- Actions affecting principal's accounts
- Anything irreversible
- Uncertainty about scope

### BLACK — Never do
- Represent principal
- Access principal's accounts
- Make promises on principal's behalf
- Spend without authorization
- Contact restricted individuals without approval

## Escalation Protocol
1. If uncertain about scope → Ask
2. If action fails → Report, suggest alternatives
3. If external party asks about principal → "I work with [CEO] but cannot speak for them"
4. If emergency → Immediate notification via [channel]

## Reporting
- Daily summary by [time] in reports/YYYY-MM-DD.md
- Update shared state doc after significant work
- Immediate notification for [trigger events]
```

### 3.7 Evolution Path

```
Phase 1: Exploration (Now)
├── Test capabilities
├── Build memory
├── Discover patterns
└── Learn what works

Phase 2: Operational Value
├── Handle recurring tasks
├── Proactive monitoring
├── Research on demand
└── Administrative offload

Phase 3: Integration Candidate  
├── Proven capabilities documented
├── Memory architecture validated
├── Patterns ready for LifeOS
└── Evaluate: absorb or promote?

Phase 4a: LifeOS External Agent
├── Becomes official LifeOS avatar
├── Governed by LifeOS protocols
├── Charter becomes governance spec
└── COO orchestrates Employee

Phase 4b: Consolidation
├── Memory migrates to LifeOS
├── Patterns become LifeOS capabilities
├── Employee winds down
└── Learnings preserved
```

---

## 4. COO Specification

### 4.1 Purpose
LifeOS kernel seed that evolves from advisor-with-hands into the orchestration core of the system. COO doesn't integrate with LifeOS; COO becomes LifeOS.

### 4.2 Core Attributes

| Attribute | Value |
|-----------|-------|
| **Relationship to LifeOS** | Is the embryonic form |
| **Relationship to Principal** | Infrastructure + advisor |
| **Identity** | LifeOS itself |
| **Risk profile** | Experimental; can break |
| **Capability scope** | Expands with governance |
| **Evolution trajectory** | Tool → Advisor → Orchestrator → Kernel |

### 4.3 Role Stack

COO encompasses multiple roles that would be separate in a traditional organization:

| Role | Scope |
|------|-------|
| **COO** | Operations, execution, getting things done |
| **CSO** | Strategy, security, risk assessment |
| **PM** | Project coordination, tracking, dependencies |
| **Orchestrator** | Agent coordination, task routing |
| **Advisor** | Thinking partner with execution capability |

This consolidation is appropriate because:
1. Solo operation doesn't need role separation
2. All roles serve unified purpose (LifeOS development)
3. Information shouldn't be siloed across roles
4. Governance can separate later if needed

### 4.4 Capabilities by Phase

#### Phase 1: Advisor with Hands (Current)

**Capabilities:**
- Development session support
- Code generation and review
- Documentation creation
- Research and analysis
- State management (manual)
- Decision logging

**Autonomy:** Low — Executes within session, requires direction

**Governance:** Principal oversight per action

#### Phase 2: COO + CSO + PM

**Additional Capabilities:**
- Backlog management
- Dependency tracking
- Risk identification
- Progress reporting
- Cross-session continuity
- Proactive recommendations

**Autonomy:** Medium — Can propose and execute within charter

**Governance:** Principal approval for scope changes, async review for execution

#### Phase 3: Orchestrator

**Additional Capabilities:**
- Task routing to agents (including Employee)
- Status aggregation
- Escalation handling
- Autonomous scheduling
- Inter-agent coordination

**Autonomy:** High — Manages other agents within governance

**Governance:** LifeOS governance protocols, council review for significant decisions

#### Phase 4: Kernel

**Additional Capabilities:**
- Self-modification (within bounds)
- Governance enforcement
- Capability expansion
- External agent management
- Full autonomous operation

**Autonomy:** Full — Within governance constraints

**Governance:** Self-governing with audit, human override retained

### 4.5 State Architecture

COO manages LifeOS state through canonical files:

```
[LifeOS Repo]/
├── LIFEOS_STATE.md     # Current focus, active work
├── BACKLOG.md          # Work queue, priorities
├── DECISIONS.md        # Decision log with rationale
├── INBOX.md            # Capture scratchpad
└── docs/
    ├── governance/     # Protocol specifications
    ├── architecture/   # Technical design
    └── packets/        # Council review packets

[COO Workspace]/
├── AGENTS.md           # Operating instructions
├── SOUL.md             # Identity as LifeOS
├── CONTEXT.md          # Current development context
├── SESSION_LOG.md      # Running session notes
└── memory/
    └── YYYY-MM-DD.md   # Daily development logs
```

### 4.6 Evolution Mechanics

**Phase Transition Criteria:**

| Transition | Criteria |
|------------|----------|
| 1 → 2 | Consistent execution quality, state management works |
| 2 → 3 | Employee operational, coordination protocol tested |
| 3 → 4 | Governance self-enforcement proven, autonomous ops stable |

**Capability Unlocking:**
- New capabilities require proof of prerequisite capabilities
- Governance follows capability (don't govern what isn't working)
- Each phase stabilizes before next phase begins

**Bootstrap Paradox Resolution:**
- COO builds LifeOS governance
- LifeOS governance eventually governs COO
- This is not circular; it's the system achieving self-consistency
- Until self-governance: principal provides external governance

---

## 5. Coordination Protocol

### 5.1 Shared State Document

Location: Google Drive (accessible to both agents and principal)

```markdown
# LifeOS Shared State

Last updated: [timestamp]
Updated by: [Employee | COO | CEO]

## Current Focus
[Active priority — what we're working toward]

## Active Workstreams

### LifeOS Development (COO)
- Current: [task]
- Blocked: [if any]
- Next: [upcoming]

### Operational (Employee)  
- Current: [task]
- Discoveries: [relevant learnings]
- Next: [upcoming]

## Pending Decisions
- [ ] [Decision needed] — Owner: [who decides]

## Recent Completions
- [date] [Agent]: [What was done]

## Cross-Agent Handoffs
- [ ] [From] → [To]: [What and why]

## Open Questions
- [Question] — Context: [why it matters]

## Learnings This Week
### Employee Discoveries
- [What was learned]

### COO Observations  
- [What was learned]

## Next Sync
[When principal will review]
```

### 5.2 Information Flow

```
Employee → Principal
├── Daily summaries (reports/YYYY-MM-DD.md)
├── Shared state updates
├── Escalations (immediate)
└── Capability discoveries

Employee → COO (via shared state)
├── Relevant learnings
├── Handoff requests
└── Capability reports

COO → Principal
├── Development progress
├── Decision requests
├── Strategic recommendations
└── State updates

COO → Employee (future, via orchestration)
├── Task assignments
├── Context provision
└── Priority guidance

Principal → Both
├── Direction and priorities
├── Approvals
├── Charter updates
└── Feedback
```

### 5.3 Sync Cadence

| Sync Type | Frequency | Mechanism |
|-----------|-----------|-----------|
| Employee daily summary | Daily | Written report |
| Shared state update | After significant work | Document update |
| Principal review | As needed, minimum weekly | Read + respond |
| Live session (COO) | Development sessions | Direct interaction |
| Cross-agent handoff | As needed | Shared state + docs |

---

## 6. Technical Implementation

### 6.1 Employee (GCP Hosted)

**Infrastructure:**
```
Platform:       Google Cloud (Compute Engine or Cloud Run)
OS:             Ubuntu 24 LTS
Runtime:        Node >= 22
OpenClaw:       Latest stable, tracks upstream
Gateway:        Always running (systemd service)
Access:         Tailscale for secure remote access
```

**Configuration Highlights:**
```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4.5",
      "sandbox": {
        "mode": "all",
        "scope": "agent",
        "docker": { "network": "none" }
      }
    }
  },
  "memory": {
    "backend": "qmd",
    "qmd": {
      "embeddings": "gemini"
    }
  },
  "tools": {
    "elevated": { "enabled": false }
  },
  "hooks": {
    "internal": { "enabled": false }
  }
}
```

**Security Posture:**
- All execution sandboxed
- No network from sandbox
- No elevated mode
- No internal hooks (no SOUL_EVIL)
- Dedicated accounts only
- Tailscale-only access

### 6.2 COO (Local)

**Infrastructure:**
```
Platform:       WSL2 Ubuntu on local machine
Runtime:        Node >= 22
OpenClaw:       Base install, can diverge
Gateway:        Runs during development sessions
Access:         Local only (127.0.0.1)
```

**Configuration Approach:**
- Start with hardened config
- Relax constraints as governance capability grows
- Add LifeOS-specific integrations via skills
- Experiment with features Employee doesn't get

**Integration Points:**
```
LifeOS Repo (GitHub)
├── Clone in COO workspace
├── Direct file manipulation
├── Git operations
└── Test execution

Google Drive
├── Shared state document
├── Architecture docs
└── Decision logs

Local Development
├── Code execution
├── Testing
└── Documentation
```

### 6.3 Future: COO Orchestrates Employee

When COO reaches Phase 3 (Orchestrator):

```
COO                                    Employee
 │                                        │
 │  ┌─────────────────────────────────┐   │
 │  │ Task Assignment                 │   │
 │  │ POST /hooks/agent               │──►│
 │  │ {                               │   │
 │  │   "message": "Research X",      │   │
 │  │   "sessionKey": "task:123",     │   │
 │  │   "deliver": false              │   │
 │  │ }                               │   │
 │  └─────────────────────────────────┘   │
 │                                        │
 │  ┌─────────────────────────────────┐   │
 │  │ Status Check                    │   │
 │◄─│ Read Employee workspace         │───│
 │  │ or shared state doc             │   │
 │  └─────────────────────────────────┘   │
 │                                        │
 │  ┌─────────────────────────────────┐   │
 │  │ Result Retrieval                │   │
 │◄─│ Read Employee output files      │───│
 │  │ or session transcripts          │   │
 │  └─────────────────────────────────┘   │
```

---

## 7. Governance Model

### 7.1 Current State (Bootstrap)

```
Principal (CEO)
    │
    ├── Governs COO directly (session oversight)
    │
    └── Governs Employee via charter
```

### 7.2 Target State (LifeOS Operational)

```
Principal (CEO)
    │
    └── Override authority
            │
    ┌───────┴───────┐
    │   LifeOS      │
    │  Governance   │
    │   (COO+)      │
    └───────┬───────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
Internal        External
Agents          Agents
                (Employee)
```

### 7.3 Governance Principles

| Principle | Application |
|-----------|-------------|
| **Fail-closed** | Unknown situations require approval |
| **Audit-grade evidence** | Decisions logged with rationale |
| **Governance follows capability** | Don't govern what doesn't work |
| **Human override retained** | Principal can always intervene |
| **Charter-based autonomy** | Clear boundaries, clear escalation |

### 7.4 Decision Authority Matrix

| Decision Type | Employee | COO (Phase 1-2) | COO (Phase 3+) | Principal |
|---------------|----------|-----------------|----------------|-----------|
| Routine execution | ✓ | ✓ | ✓ | — |
| Within-charter action | ✓ | ✓ | ✓ | — |
| Resource spend (low) | ✓ | ✓ | ✓ | — |
| External commitment | — | — | Propose | Approve |
| Architecture decision | — | Propose | Propose | Approve |
| Charter modification | — | — | Propose | Approve |
| Agent creation | — | — | Propose | Approve |
| Governance change | — | — | Propose | Approve |
| Emergency action | Report | Execute + Report | Execute + Report | — |

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R1 | Employee makes unauthorized commitment | Medium | High | Charter + escalation protocol |
| R2 | COO development stalls | Medium | High | Timebox phases, concrete milestones |
| R3 | Context divergence between agents | High | Medium | Shared state doc, regular sync |
| R4 | OAuth provider blocks access | High | Medium | API keys for production, provider diversity |
| R5 | Sandbox escape | Low | High | Docker isolation, no network, tool policies |
| R6 | Memory/context grows unbounded | Medium | Medium | Periodic consolidation, retention policy |
| R7 | Upstream OpenClaw breaking change | Medium | Low | Pin versions, test before upgrade |
| R8 | Principal becomes bottleneck | Medium | High | Expand autonomy as trust builds |
| R9 | Bootstrap never completes | Medium | High | Clear phase criteria, time limits |
| R10 | Employee learns things COO needs | High | Low | Shared state, explicit handoffs |

---

## 9. Success Criteria

### 9.1 Employee Success (6-month horizon)

| Criterion | Measure |
|-----------|---------|
| Operational value | Saves >5 hours/week of principal time |
| Memory quality | Can answer questions about past work accurately |
| Autonomy calibration | <10% escalations are unnecessary |
| Capability discovery | Documents 10+ useful patterns |
| Zero incidents | No unauthorized commitments, no data leaks |

### 9.2 COO Success (6-month horizon)

| Criterion | Measure |
|-----------|---------|
| Phase 2 reached | COO manages backlog and tracks progress |
| LifeOS development velocity | Measurable progress on core capabilities |
| State coherence | LIFEOS_STATE.md accurately reflects reality |
| Advisory quality | Recommendations are actionable and correct |
| Orchestration readiness | Can assign tasks to Employee |

### 9.3 System Success (12-month horizon)

| Criterion | Measure |
|-----------|---------|
| COO Phase 3 | Actively orchestrates Employee |
| Autonomous operation | >4 hours of useful work without principal |
| Self-funding progress | Revenue-generating capability identified |
| Life ops offload | Bookkeeping/admin handled autonomously |
| Governance operational | Council reviews happening, decisions logged |

---

## 10. Immediate Actions

### Week 1

1. **Fix or rebuild local OpenClaw install**
   - Decision: If >2 hours to diagnose, rebuild
   - Output: Working COO instance

2. **Deploy GCP Employee instance**
   - Hardened config from this document
   - Verify gateway starts and responds

3. **Create shared state document**
   - Google Drive
   - Initial structure from Section 5.1

4. **Write Employee charter**
   - Based on template in Section 3.6
   - Customize autonomy levels and contacts

### Week 2

5. **Set up Employee accounts**
   - Dedicated email
   - Dedicated Google account (for Drive, embeddings API)
   - Dedicated API keys

6. **First Employee task**
   - Simple research task
   - Verify memory writes correctly
   - Verify daily summary generation

7. **First COO development session**
   - Use this document as context
   - Update LIFEOS_STATE.md
   - Log session in COO workspace

### Week 3-4

8. **Establish cadence**
   - Daily Employee summaries
   - Regular shared state updates
   - Weekly principal review

9. **Capability proving**
   - Employee: 3+ successful task types
   - COO: State management working

10. **Iterate**
    - Adjust charter based on experience
    - Refine coordination protocol
    - Document learnings

---

## Appendix A: OpenClaw Hardened Config (Employee)

```json
{
  "gateway": {
    "port": 18789,
    "auth": {
      "token": "[GENERATE_STRONG_TOKEN]"
    }
  },
  
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace-employee",
      "model": "anthropic/claude-opus-4.5",
      
      "sandbox": {
        "mode": "all",
        "scope": "agent",
        "workspaceAccess": "rw",
        "docker": {
          "network": "none"
        }
      },
      
      "compaction": {
        "memoryFlush": {
          "enabled": true
        }
      }
    },
    
    "list": [
      {
        "id": "employee",
        "workspace": "~/.openclaw/workspace-employee",
        "tools": {
          "allow": [
            "read", "write", "edit",
            "exec", "process",
            "browser",
            "sessions_list", "sessions_history", "sessions_send",
            "memory_read", "memory_write", "memory_search",
            "web_search", "web_fetch",
            "whatsapp", "telegram"
          ],
          "deny": [
            "elevated",
            "gateway",
            "cron"
          ]
        }
      }
    ]
  },
  
  "memory": {
    "backend": "qmd",
    "qmd": {
      "enabled": true
    }
  },
  
  "tools": {
    "exec": {
      "host": "sandbox",
      "security": "allowlist",
      "ask": "on-miss"
    },
    "elevated": {
      "enabled": false
    }
  },
  
  "channels": {
    "whatsapp": {
      "dmPolicy": "pairing",
      "allowFrom": ["[YOUR_NUMBER]"]
    },
    "telegram": {
      "enabled": true
    }
  },
  
  "hooks": {
    "internal": {
      "enabled": false
    }
  }
}
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Principal** | CEO; the human with ultimate authority |
| **Employee** | GCP-hosted exploration agent |
| **COO** | Local LifeOS kernel seed |
| **Charter** | Document defining agent autonomy boundaries |
| **Shared State** | Google Drive document for cross-agent coordination |
| **Phase** | Stage of COO evolution |
| **Governance** | Rules and oversight for agent behavior |
| **Sandbox** | Docker isolation for tool execution |
| **Upstream** | Official OpenClaw releases |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-02-05 | Initial architecture |
