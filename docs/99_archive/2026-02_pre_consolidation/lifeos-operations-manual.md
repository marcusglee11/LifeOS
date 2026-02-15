# LifeOS Comprehensive Operations Manual
## From Current State to Working System

**Date:** 2026-02-07
**Purpose:** Complete operational playbook across all workstreams
**How to use:** Work through sequentially. Each section builds on the previous. Branch explorations are inline where they arise.

---

# TABLE OF CONTENTS

1. COO Agent: Making It Real (Start Here)
2. Project Management: The Capture→Execute Loop
3. OpenClaw Integration + Employee Deployment
4. LifeOS Autonomous Build Loops
5. Revenue Channel Operationalization
6. Architecture Reconciliation
7. Branch Explorations (Emergent Insights)
8. Master Sequencing: The First 90 Days
9. Risk-Adjusted Decision Framework
10. The Meta-Question: What LifeOS Actually Is Right Now

---

# 1. COO AGENT: MAKING IT REAL

## Why This Is First

Everything else depends on having a working COO. Not the Phase 4 kernel from your architecture doc — a Phase 1 agent that can reliably execute tasks within a session and maintain state between sessions. Without this, you're doing everything manually, which means you're the bottleneck your entire system is designed to eliminate.

Your current COO is Claude in conversation windows. That's not nothing — but it has no persistence, no ability to act on your repo, no scheduled execution, and no state between sessions. Every conversation starts cold.

## The Minimum Viable COO

Strip away everything aspirational. What does a COO need to do in Week 1?

```
MINIMUM VIABLE COO — WEEK 1 CAPABILITIES

1. Read a capture file and triage it into tasks
2. Read and update files in your LifeOS repo
3. Maintain BACKLOG.md from GitHub Issues state
4. Generate a daily briefing
5. Execute simple file operations (create, edit, move)
6. Run git operations (commit, push, pull)
7. Persist state between sessions via files (not memory)

THAT'S IT. Everything else is Phase 2+.
```

## Implementation Options (Ranked by Pragmatism)

### Option A: Claude Code as COO (Recommended for Week 1)

Claude Code runs in your terminal, has access to your filesystem, can execute bash commands, and can interact with your repo. It's the fastest path to a working COO.

**Setup:**
- Install Claude Code (if not already): `npm install -g @anthropic-ai/claude-code`
- Create a COO workspace directory: `~/lifeos-coo/`
- Create a session context file that Claude Code reads at the start of every session

**The Session Context File (`~/lifeos-coo/CONTEXT.md`):**
```markdown
# COO Session Context
Last updated: [timestamp]

## Who I Am
I am the COO agent for LifeOS. I operate during development sessions
directed by the CEO. My job is operations, execution, and state management.

## Current State
[Agent updates this at end of each session]
- Active milestone: Week 1
- Priority tasks: [list from BACKLOG.md]
- Blocked items: [any blockers]
- Last session: [date, what was accomplished]
- Next session expected focus: [what CEO indicated]

## Standing Orders
1. At session start: read BACKLOG.md, check GitHub Issues, report status
2. At session end: update this file, update BACKLOG.md, commit changes
3. Always: log decisions in DECISIONS.md with rationale
4. Always: if uncertain, ask rather than assume
5. Never: push to main without CEO approval
6. Never: create external accounts or make external commitments

## Key File Locations
- Repo: ~/LifeOS/
- Capture file: ~/capture.md
- Backlog: ~/LifeOS/BACKLOG.md
- Decisions log: ~/LifeOS/DECISIONS.md
- Session logs: ~/lifeos-coo/sessions/
- This file: ~/lifeos-coo/CONTEXT.md
```

**Daily COO Loop (Using Claude Code):**

```
MORNING (You initiate, ~2 min):
$ cd ~/LifeOS && claude

You: "Morning session. Read CONTEXT.md and give me today's briefing."

Claude Code:
  → Reads CONTEXT.md
  → Reads BACKLOG.md
  → Checks GitHub Issues via `gh issue list`
  → Reads capture.md for new items
  → Produces briefing
  → Triages capture.md items into GitHub Issues
  → Asks for your priorities/decisions

You: "Focus on X today. Y is blocked because Z. Kill task #14."

Claude Code:
  → Updates issues
  → Begins work on X
  → Logs the session

END OF SESSION (Claude Code, ~1 min):
You: "End session."

Claude Code:
  → Updates CONTEXT.md with session summary
  → Updates BACKLOG.md
  → Commits changes to repo
  → Writes session log to ~/lifeos-coo/sessions/YYYY-MM-DD.md
```

**Why this works now:**
- No infrastructure to build
- No deployment to manage
- State persists via files in your filesystem
- Git provides version history
- You can start TODAY

**Why this isn't the end state:**
- Requires you to initiate sessions manually
- No overnight/background execution
- No scheduled tasks
- No multi-agent coordination

But it's a WORKING COO that you can use immediately while you build toward the autonomous version.

### Option B: OpenClaw COO (Local, WSL2)

This is what your Agent Architecture doc specifies. It's the right medium-term answer but has setup friction.

**Current blockers (inferred from your docs):**
- Your local OpenClaw install may be broken (your doc says "Fix or rebuild, if >2hrs rebuild")
- WSL2 environment needs to be configured
- Gateway needs to run during sessions

**If OpenClaw is working:**
```
COO via OpenClaw (Local):
- Workspace: ~/.openclaw/workspace-coo/
- AGENTS.md: Operating instructions (your charter)
- SOUL.md: Identity as LifeOS infrastructure
- Memory: File-based (LifeOS state docs)
- Gateway: localhost:18789
- Model: claude-opus-4.5 (or sonnet for cost management)

Interaction:
- You talk to COO via OpenClaw gateway (web UI or API)
- COO has filesystem access to LifeOS repo
- COO can execute code, run tests, manage git
- Memory persists via OpenClaw's memory system + workspace files
```

**If OpenClaw is broken:**
Don't spend more than 2 hours fixing it. Use Option A (Claude Code) immediately and fix OpenClaw as a background task. The goal is a working COO today, not a perfect COO eventually.

### Option C: Hybrid (Recommended for Week 2+)

Use Claude Code for immediate COO tasks AND work on getting OpenClaw running in parallel. When OpenClaw is stable, migrate the COO role to it. The CONTEXT.md file and file-based state management work identically in both environments — the agent interface changes but the operating model doesn't.

## COO State Management: The Real Problem

Your Agent Architecture doc correctly identifies state management as critical but proposes Google Drive as the solution. This is wrong for the COO (it's acceptable for cross-agent coordination, which is a different problem).

**The COO's state should live in the LifeOS repo itself:**

```
~/LifeOS/
├── BACKLOG.md              # Agent-maintained task list
├── DECISIONS.md            # Decision log with rationale
├── INBOX.md                # Quick capture (alternative to ~/capture.md)
├── docs/
│   ├── governance/         # Your existing governance docs
│   ├── architecture/       # Technical design docs
│   └── operations/         # NEW: operational runbooks
├── state/
│   ├── CURRENT_FOCUS.md    # What we're working on right now
│   ├── EXPERIMENTS.md      # Revenue experiment tracker
│   ├── METRICS.md          # Key metrics dashboard (text-based)
│   └── WEEKLY_REVIEWS/     # Weekly review outputs
│       └── 2026-W06.md
└── ...existing code...
```

**Why the repo and not Google Drive:**
- Git gives you version history for free
- Every state change is a commit with a message
- You can diff any two points in time
- It's local-first (no network dependency)
- Both Claude Code and OpenClaw can interact with it
- The Employee agent can read it via GitHub (when deployed)

**Google Drive's role** is specifically for documents that need to be shared with the Employee agent before you have direct inter-agent communication. That's a coordination layer, not a state layer. Keep the distinction clean.

## COO Phase Transitions (Realistic)

Your doc describes 4 phases. Here's what they actually look like with honest timelines:

```
Phase 1: Session Assistant (NOW → Week 4)
├── You initiate every session
├── Agent executes within session scope
├── State persists via files
├── No autonomous action between sessions
├── Value: saves you context-rebuild time, maintains backlog
└── Graduation criteria: 
    - 10+ sessions completed
    - BACKLOG.md accurately reflects reality
    - Session logs are useful when you re-read them
    - You trust the agent's task triage

Phase 1.5: Scheduled Tasks (Week 4 → Week 8)
├── Cron jobs trigger agent for specific tasks
│   ├── Morning briefing generation
│   ├── Capture file triage
│   ├── Metrics collection
│   └── Content draft preparation
├── Still no autonomous decision-making
├── You review outputs, agent doesn't act on them without approval
└── Graduation criteria:
    - Scheduled tasks run reliably for 2+ weeks
    - Output quality is consistent
    - You actually read and use the outputs

Phase 2: Autonomous Within Bounds (Week 8 → Week 16)
├── Agent can execute GREEN-level actions without session
│   ├── Create GitHub Issues from capture
│   ├── Update documentation
│   ├── Generate and publish content drafts (to staging, not live)
│   ├── Run research tasks
│   └── Maintain metrics dashboards
├── YELLOW actions: execute then report
├── RED actions: queue for your approval
└── Graduation criteria:
    - 4+ weeks of autonomous operation
    - <5% of autonomous actions need correction
    - Zero RED-level actions taken without approval
    - You feel comfortable not checking in daily

Phase 3: Orchestrator (Week 16+)
├── COO coordinates with Employee agent
├── Task routing between agents
├── Aggregated reporting
├── This is where your architecture doc's vision starts to become real
└── Prerequisites:
    - Employee agent is operational
    - Coordination protocol tested manually first
    - Shared state mechanism proven
```

**Key insight:** Phase 1.5 is the phase your architecture doc is missing. The jump from "session assistant" to "autonomous operator" is too large. Scheduled tasks are the intermediate step — the agent acts, but only at predictable times on predictable tasks. This is how you build trust incrementally.

---

# 2. PROJECT MANAGEMENT: THE CAPTURE→EXECUTE LOOP

## Why This Is Second

You can't manage multiple revenue experiments, agent development, and LifeOS architecture work simultaneously without a system. But the system has to be zero-friction for you, which means the COO agent maintains it.

I already delivered a spec for this (week1-00-task-management-spec.md), but here's the deeper operational detail.

## The Full Capture→Execute Pipeline

```
CAPTURE (Friction: near zero)
    │
    │  You dump raw text into capture.md
    │  Acceptable formats:
    │  - "need to set up gumroad"
    │  - "idea: sell governance doc as product"
    │  - "blocked on openclaw install, WSL issue"
    │  - "talked to X, they're interested in Y"
    │  - Voice memo transcription (if you set this up)
    │
    ▼
TRIAGE (Agent, daily)
    │
    │  Agent reads capture.md and classifies each item:
    │  
    │  → TASK: Create GitHub Issue
    │    - Title: verb + noun ("Set up Gumroad account")
    │    - Labels: from standard set
    │    - Milestone: assign to current or next week
    │    - Acceptance criteria: what "done" looks like
    │  
    │  → DECISION: Add to DECISIONS_NEEDED in briefing
    │    - Frame the decision clearly
    │    - Present options if obvious
    │    - Flag urgency level
    │  
    │  → LEARNING: Add to session log or LEARNINGS section
    │    - Don't create a task
    │    - Do record for future reference
    │  
    │  → REFERENCE: Add to appropriate entity/project file
    │    - Contact info → relationship tracking
    │    - Tool discovery → capabilities.md
    │    - Cost data → METRICS.md
    │  
    │  → GARBAGE: Delete (agent notes what was deleted and why)
    │
    ▼
PRIORITIZE (Agent, daily)
    │
    │  Agent produces ordered priority list based on:
    │  1. Revenue experiments with active deadlines
    │  2. Blocked items that can be unblocked today
    │  3. Items on this-week milestone
    │  4. Quick wins (<30 min)
    │  5. Everything else by milestone order
    │
    ▼
BRIEF (Agent → You, daily)
    │
    │  Daily briefing delivered as file or message:
    │  - Top 3 priorities for today
    │  - Any decisions needed
    │  - Blocked items + what would unblock them
    │  - Revenue experiment status
    │  - Anything stale or overdue
    │
    ▼
EXECUTE (You direct, Agent assists)
    │
    │  During work sessions:
    │  - You pick from the priority list (or override)
    │  - COO agent assists with execution
    │  - Completed items get closed
    │  - New items captured as they arise
    │
    ▼
REVIEW (Agent, weekly)
    │
    │  Weekly review includes:
    │  - Velocity (issues opened vs closed)
    │  - Revenue progress
    │  - Experiment status with kill/continue signal
    │  - Time allocation analysis (how much went to each label)
    │  - Recommendations for next week's focus
    │
    ▼
ITERATE
    │
    │  You adjust:
    │  - Kill experiments that aren't working
    │  - Reprioritize based on signal
    │  - Update milestones
    │  - Agent propagates changes
```

## The GitHub Issues Implementation Detail

### Issue Templates

Create `.github/ISSUE_TEMPLATE/` in your repo with these templates:

**task.md:**
```markdown
---
name: Task
about: A specific task to be completed
labels: ''
---

## What
[Clear description of what needs to be done]

## Acceptance Criteria
- [ ] [What "done" looks like]

## Context
[Why this matters, any relevant background]

## Estimate
[Quick win (<30 min) / Half day / Full day / Multi-day]
```

**experiment.md:**
```markdown
---
name: Revenue Experiment
about: Track a revenue experiment
labels: revenue
---

## Experiment
[What we're testing]

## Hypothesis
[What we expect to happen]

## Setup Required
- [ ] [Steps to launch]

## Metrics
[What we'll measure]

## Kill Criteria
[When to stop]

## Timeline
- Launch: [date]
- First review: [date]
- Kill/continue decision: [date]
```

**decision.md:**
```markdown
---
name: Decision Needed
about: A decision that requires CEO judgment
labels: ''
---

## Decision
[What needs to be decided]

## Options
1. [Option A] — Pros: ... Cons: ...
2. [Option B] — Pros: ... Cons: ...

## Recommendation
[Agent's recommendation if it has one]

## Deadline
[When this needs to be decided by, and why]
```

### Automation via GitHub CLI

The COO agent uses `gh` (GitHub CLI) to manage issues without needing to touch the GitHub web UI:

```bash
# Create issue
gh issue create --title "Set up Gumroad for B5" --label "product,revenue" --milestone "week-1" --body "..."

# List issues by milestone
gh issue list --milestone "week-1" --state open

# Close issue
gh issue close 14 --comment "Completed: Gumroad account created, B5 listed at $49"

# Add labels
gh issue edit 12 --add-label "blocked"

# List all open issues by label
gh issue list --label "revenue" --state open
```

The agent wraps these in its daily triage routine. You never type `gh` commands yourself.

### Project Board (Optional, Low Friction)

GitHub Projects can auto-manage a kanban board from issue labels:
- `this-week` label → "In Progress" column
- `blocked` label → "Blocked" column  
- Closed issues → "Done" column

This gives you a visual overview if you want one, but the BACKLOG.md file serves the same purpose in text form. Don't set this up unless you find yourself wanting a visual board after 2+ weeks.

## Multi-Project Tracking

You're going to have tasks across several domains. Here's how to keep them organized without creating multiple repos or tools:

```
Labels handle categorization:
├── revenue     → Revenue experiments
├── content     → Content creation
├── product     → Product building
├── agent       → Agent development (COO, Employee)
├── infra       → Infrastructure and tooling
├── lifeos-core → Core LifeOS development
├── blocked     → Waiting on external
├── quick-win   → <30 min tasks
└── this-week   → Committed for current week

Milestones handle time horizons:
├── week-1, week-2, ... week-8  → Near-term sprints
├── month-3-review              → First major review point
├── month-6-review              → Second review point
└── someday                     → Ideas worth tracking, not worth scheduling

Combined query examples:
"What revenue tasks are committed this week?"
→ gh issue list --label "revenue,this-week" --state open

"What's blocked across everything?"
→ gh issue list --label "blocked" --state open

"What quick wins are available?"
→ gh issue list --label "quick-win" --state open
```

---

# 3. OPENCLAW INTEGRATION + EMPLOYEE DEPLOYMENT

## Current Situation Assessment

From your Agent Architecture doc:
- Employee is designed to run on GCP (Compute Engine or Cloud Run)
- Uses OpenClaw with hardened config
- Always-on via systemd service
- Accessed via Tailscale
- Sandboxed execution, no network from sandbox

From reality signals:
- Your local OpenClaw install may be broken
- The Employee has not been deployed yet
- The hardened config in your appendix is designed but untested

## The OpenClaw Question

OpenClaw (I'm inferring this is the agent framework from your config references — it may have a different public name) is your chosen agent infrastructure. Before deploying Employee, you need to answer:

### Critical Assessment Questions

```
1. IS OPENCLAW ACTUALLY WORKING ON YOUR LOCAL MACHINE?
   If no → Fix it or rebuild (your 2-hour timebox applies)
   If unknown → Test it now, before anything else
   
2. WHAT VERSION ARE YOU ON?
   Your doc says "tracks upstream" for Employee
   If upstream has had breaking changes since you last used it → test before deploying
   
3. CAN YOU RUN A TRIVIAL AGENT TASK?
   "Agent, read a file and summarize it"
   If this doesn't work locally → don't deploy to GCP yet
   
4. DO YOU HAVE THE GCP INFRASTRUCTURE?
   Compute Engine instance or Cloud Run service?
   Tailscale configured?
   Budget alerts set?
   
5. WHAT'S YOUR MONTHLY GCP BUDGET FOR THIS?
   Employee running 24/7 = compute costs + API costs
   Estimate: $50-200/month compute + $100-500/month API (depends heavily on usage)
   Can your runway absorb this?
```

## Employee Deployment: Phased Approach

Don't try to deploy the full Employee spec from your architecture doc in one shot. Phase it:

### Phase E1: Local Proof (Before ANY GCP Spend)

Run the Employee agent locally first. Same config, same workspace structure, but on your local machine.

```
Goal: Prove the agent can do useful work before spending money on infrastructure.

Tasks to test:
1. Web research: "Research the current state of AI agent frameworks. 
   Produce a 500-word summary."
   → Tests: web search, synthesis, file output

2. Document drafting: "Read ~/LifeOS/docs/governance/ and produce 
   a one-page executive summary."
   → Tests: file reading, synthesis, writing

3. Monitoring: "Check Hacker News front page. Flag any posts about 
   AI agents or autonomous systems. Save to ~/employee/reports/."
   → Tests: web access, filtering, structured output

4. Memory: "Remember that we tested these capabilities on [date]. 
   The research task took 3 minutes and used ~$0.40 in API costs."
   → Tests: memory write, cost tracking

5. Retrieval: "What capabilities did we test last session?"
   → Tests: memory read, retrieval accuracy

Success criteria: 
- 4/5 tasks execute correctly
- Cost per task is within acceptable range
- Memory actually persists and retrieves
- No security or sandboxing issues
```

### Phase E2: GCP Deployment (After Local Proof)

Only proceed here if Phase E1 passes cleanly.

**Infrastructure setup:**

```bash
# 1. GCP Compute Engine instance
# Recommendation: e2-medium (2 vCPU, 4GB RAM) — ~$25/month
# Ubuntu 24 LTS
# Region: closest to you for Tailscale latency

# 2. Tailscale installation
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=[YOUR_AUTH_KEY]

# 3. Node.js
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# 4. OpenClaw
# [Installation commands per OpenClaw docs]

# 5. Workspace setup
mkdir -p ~/.openclaw/workspace-employee
# Copy AGENTS.md, SOUL.md, USER.md, CHARTER.md from your templates

# 6. Systemd service
sudo cat > /etc/systemd/system/openclaw-employee.service << 'EOF'
[Unit]
Description=OpenClaw Employee Agent
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=employee
WorkingDirectory=/home/employee
ExecStart=/usr/bin/node /path/to/openclaw/gateway
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable openclaw-employee
sudo systemctl start openclaw-employee

# 7. Budget alerts
# Set up GCP billing alerts at $50, $100, $200/month
# This is critical — runaway API costs can drain runway
```

**Hardened config (from your appendix, with annotations):**

```json
{
  "gateway": {
    "port": 18789,
    "auth": {
      "token": "[GENERATE: openssl rand -hex 32]"
    }
  },
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace-employee",
      "model": "anthropic/claude-sonnet-4-5-20250929",
      // NOTE: Start with Sonnet, not Opus. 
      // Opus is 5-10x more expensive.
      // Upgrade to Opus only for tasks that demonstrably need it.
      // Most Employee tasks (research, drafting, monitoring) don't.
      
      "sandbox": {
        "mode": "all",
        "scope": "agent",
        "workspaceAccess": "rw",
        "docker": {
          "network": "none"
          // This means sandboxed code can't access internet.
          // Web search/fetch happens via OpenClaw tools, not from sandbox.
          // This is correct for security.
        }
      },
      "compaction": {
        "memoryFlush": {
          "enabled": true
          // Automatically flushes context to memory when approaching limit.
          // Important for long-running tasks.
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
            "elevated",    // No root/admin access
            "gateway",     // Can't modify its own gateway config
            "cron"         // Can't schedule its own tasks (you control scheduling)
          ]
        }
      }
    ]
  },
  "memory": {
    "backend": "qmd",
    "qmd": {
      "enabled": true
      // Gemini embeddings for semantic search
      // Requires Gemini API key
    }
  },
  "tools": {
    "exec": {
      "host": "sandbox",
      "security": "allowlist",
      "ask": "on-miss"    // If tool not in allowlist, ask before proceeding
    },
    "elevated": {
      "enabled": false     // No sudo, no system-level operations
    }
  },
  "channels": {
    "whatsapp": {
      "dmPolicy": "pairing",
      "allowFrom": ["[YOUR_NUMBER]"]
      // Only accepts messages from your number
      // This is your communication channel with Employee
    },
    "telegram": {
      "enabled": true
      // Alternative channel
    }
  },
  "hooks": {
    "internal": {
      "enabled": false
      // No SOUL_EVIL or internal hook overrides
      // This is a security hardening measure
    }
  }
}
```

**Model cost management (CRITICAL for runway):**

```
Model selection strategy:

SONNET (default — use for 90% of tasks):
- Research and web browsing
- Document drafting
- Monitoring and alerting
- Memory operations
- Routine correspondence
- Data extraction and formatting
Cost: ~$3 per million input tokens, $15 per million output tokens

OPUS (upgrade only when needed):
- Complex multi-step reasoning
- Architecture analysis
- Strategic recommendations
- Tasks where Sonnet demonstrably produces inferior output
Cost: ~$15 per million input tokens, $75 per million output tokens

HAIKU (downgrade for high-volume, simple tasks):
- Simple classification
- Format conversion
- Boilerplate generation
- Monitoring checks (is this page different from last check?)
Cost: ~$0.25 per million input tokens, $1.25 per million output tokens

Expected monthly API costs (Employee running 24/7):
- Light usage (10-20 tasks/day, mostly Sonnet): $100-200/month
- Medium usage (30-50 tasks/day, mixed models): $200-500/month
- Heavy usage (100+ tasks/day or frequent Opus): $500-1000+/month

BUDGET ALERT: Set a hard monthly API spend cap.
Start at $200/month. Increase only after demonstrating ROI.
```

### Phase E3: First Real Tasks

Once deployed on GCP and verified working:

```
Week 1 Employee Tasks:
1. Daily HN/Reddit monitoring for AI agent topics
   → Output: ~/reports/YYYY-MM-DD-scan.md
   → Schedule: Run at 11pm your timezone

2. Research task: "Analyze top 10 AI agent frameworks by GitHub stars.
   Compare features, pricing, architecture. Output as structured comparison."
   → Output: ~/reports/agent-frameworks-comparison.md
   → One-time task, used to inform your own architecture decisions

3. LinkedIn content research: "Find 20 LinkedIn posts about AI agents 
   that got >100 reactions. Analyze what made them successful."
   → Output: ~/reports/linkedin-content-analysis.md
   → Informs your A1 content strategy

4. Cost tracking: "Log your own API usage for each task.
   At end of day, produce a cost summary."
   → Output: ~/reports/YYYY-MM-DD-costs.md
   → Critical for runway management

Week 2 Employee Tasks (if Week 1 succeeds):
5. Draft LinkedIn posts from your capture.md notes
6. Monitor competitors/similar projects on GitHub
7. Research potential customers for B5 governance guide
8. Begin daily briefing preparation (complement to COO)
```

### Phase E4: Employee Identity Setup

Your architecture doc specifies dedicated accounts. Here's the practical setup:

```
ACCOUNTS TO CREATE:

1. Email: [chosen-name]@gmail.com (or your domain)
   → Used for: account signups, correspondence
   → NOT used for: representing you

2. GitHub: lifeos-employee (if needed for repo interactions)
   → Read access to LifeOS repo
   → Own repos for employee-specific projects

3. Google Account: For Drive access (shared state doc), Gemini API
   → Separate from your personal Google account

4. API Keys (all dedicated):
   → Anthropic API key (separate from your personal key)
   → Gemini API key (for embeddings)
   → Any other service APIs

5. Browser Profile: Dedicated Chrome/Firefox profile
   → Separate cookies, history, sessions
   → Used for web browsing tasks

DEFER THESE (not needed for Phase E1-E3):
- LinkedIn account (Employee shouldn't post to LinkedIn — you do)
- Payment method (no spending authority initially)
- Domain-specific accounts (add as needed per task)
```

## Inter-Agent Communication: COO ↔ Employee

Your architecture doc describes a shared state document on Google Drive. Here's the actual implementation:

### Near-Term (Weeks 1-8): Manual Handoffs

```
Communication flow:

CEO → COO (via Claude Code or OpenClaw session):
  "Tell Employee to research X"

COO → Shared State Doc (Google Drive):
  Updates "Cross-Agent Handoffs" section:
  "COO → Employee: Research X. Context: [why]. 
   Output expected: [format]. Deadline: [date]."

Employee → Shared State Doc (reads periodically):
  Picks up handoff, executes, writes output to shared location.
  Updates shared state: "Employee: Completed research on X. 
   Output at [location]. Key findings: [summary]."

CEO → Reads shared state at next session.
COO → Reads shared state at next session.
```

This is manual and slow. It's also fine for now. You'll have maybe 2-3 handoffs per week initially. The overhead of reading/writing a shared doc is trivial at that volume.

### Medium-Term (Weeks 8-16): API-Based Coordination

When COO reaches Phase 2 (scheduled tasks), you can implement direct communication:

```
COO → Employee (via OpenClaw API):
  POST http://[employee-tailscale-ip]:18789/hooks/agent
  {
    "message": "Research the top 5 AI governance frameworks...",
    "sessionKey": "task:research-governance-frameworks",
    "deliver": false
  }

Employee → COO (via shared filesystem or API callback):
  Writes output to shared location
  Updates shared state doc
  Optionally sends notification via WhatsApp/Telegram
```

### Long-Term (Weeks 16+): Orchestrated

COO assigns tasks, monitors progress, aggregates results. This is your Phase 3 architecture. Don't build it until you need it.

---

# 4. LIFEOS AUTONOMOUS BUILD LOOPS

## The Core Problem

LifeOS is supposed to build itself (through agent-assisted development). Currently, you're the only one building it, and you've produced 28 commits over several months. The codebase is 99% Python, the architecture docs specify Node.js, and the repo has organizational debris (committed venv, leaked test databases, multiple test directories).

## What "Autonomous Build Loops" Actually Means

Not self-modifying AI. Not AGI writing its own code. It means:

```
AUTONOMOUS BUILD LOOP:

1. You specify WHAT to build (a feature, a fix, a component)
2. COO agent decomposes it into tasks
3. COO agent (or Employee) writes the code
4. Automated tests verify correctness
5. You review and approve (or reject with feedback)
6. Agent incorporates feedback and iterates
7. Approved code gets merged

The "autonomous" part is steps 2-4 and 6.
Your role is steps 1, 5, and 7.
```

This is not hypothetical. Claude Code and similar tools can do this TODAY for well-scoped tasks. The challenge is setting up the infrastructure so it works reliably.

## Prerequisites for Autonomous Build Loops

### P1: Clean Repo (Do This Immediately)

```bash
# Remove committed venv
echo "venv/" >> .gitignore
git rm -r --cached venv/
git commit -m "Remove committed venv, add to gitignore"

# Remove test artifacts from root
git rm test_budget_concurrency.db
git commit -m "Remove test database from repo root"

# Consolidate test directories
# Assess: what's in tests/ vs tests_doc/ vs tests_recursive/?
# If they serve different purposes, keep but document
# If they're organizational churn, consolidate into tests/
mkdir -p tests/unit tests/integration tests/doc
# Move files appropriately
git commit -m "Consolidate test directories"

# Add proper .gitignore entries
cat >> .gitignore << 'EOF'
venv/
*.db
__pycache__/
*.pyc
.env
.env.local
node_modules/
EOF
git commit -m "Update gitignore"
```

### P2: Resolve the Python/Node Question

Your repo is 99% Python. Your agent architecture specifies Node.js (for OpenClaw). These are not in conflict if you draw the line clearly:

```
PYTHON: LifeOS core system
- Runtime kernel
- Governance engine
- State management
- Tools and utilities
- Tests

NODE.JS: Agent infrastructure
- OpenClaw (gateway, agents)
- Any OpenClaw plugins/skills
- Future web interfaces (if needed)

They coexist. Python handles LifeOS logic. Node handles the agent framework.
The interface between them is the filesystem (state files) and APIs.
```

Document this decision and move on.

### P3: Test Infrastructure

You can't have autonomous code generation without automated tests. If the tests don't exist, the agent can't verify its own work.

```
Current state (inferred): Tests exist but are scattered and possibly incomplete.

Required state:
1. pytest configured and working (you have pytest.ini — verify it works)
2. Tests cover core LifeOS functionality
3. CI runs tests on PR (GitHub Actions)
4. Agent can run tests locally before committing

Minimum test coverage for autonomous builds:
- Every module has at least one smoke test
- Critical paths (governance checks, state management) have thorough tests
- A single command runs all tests: `pytest`
- Exit code 0 = all pass, non-zero = failure

The agent's build loop:
1. Write code
2. Run pytest
3. If tests fail → fix and re-run
4. If tests pass → create PR
5. You review PR
```

### P4: CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest --tb=short
```

This is the minimum. Add linting (ruff), type checking (mypy), and coverage reporting as the codebase matures.

### P5: Branch Strategy

```
main          → Production/stable. Protected. Requires PR review.
dev           → Active development. Agent pushes here.
feature/*     → Individual features. Agent creates these.

Agent workflow:
1. git checkout -b feature/add-briefing-generator
2. [writes code, runs tests]
3. git push origin feature/add-briefing-generator
4. gh pr create --title "Add briefing generator" --body "[description]"
5. You review PR on GitHub
6. You merge or request changes
7. Agent incorporates changes if requested
```

## The Actual Build Loop (Step by Step)

Here's how a complete autonomous build cycle works:

```
EXAMPLE: "Add a daily briefing generator to LifeOS"

Step 1 — You specify intent:
  "LifeOS needs a daily briefing generator. It should read BACKLOG.md,
   check GitHub Issues via gh CLI, read capture.md, and produce a 
   structured daily briefing as markdown. Output to state/briefings/."

Step 2 — COO decomposes:
  "Breaking this into tasks:
   2a. Create briefing generator module (runtime/briefing.py)
   2b. Add CLI command: lifeos briefing generate
   2c. Add tests for briefing generation
   2d. Add to scheduled tasks (cron-compatible)
   2e. Document in docs/operations/briefing.md
   
   Dependencies: 2a before 2b, 2b before 2c, all before 2d and 2e.
   Estimated effort: 2-3 hours of agent work."

Step 3 — COO (or you direct Claude Code) implements:
  Creates branch: feature/daily-briefing
  Writes runtime/briefing.py
  Writes tests/test_briefing.py
  Runs pytest → fixes any failures
  Writes docs/operations/briefing.md
  
Step 4 — Agent creates PR:
  gh pr create --title "Add daily briefing generator" \
    --body "## What\nDaily briefing generator...\n## Testing\npytest passes..."

Step 5 — You review:
  Read the PR diff on GitHub (or via gh pr view)
  Either approve or comment with feedback

Step 6 — If feedback:
  Agent reads your comments, makes changes, pushes to same branch
  PR updates automatically. Back to Step 5.

Step 7 — Merge:
  You merge the PR. Feature is now in main.
  Agent closes related GitHub Issue(s).
```

## What Makes This "Autonomous"

The agent handles: decomposition, implementation, testing, documentation, PR creation, and iteration on feedback. You handle: intent specification, review, and final approval.

Over time, as trust builds:
- You can approve smaller PRs with less scrutiny
- Agent can merge certain types of changes without your review (documentation, test additions, style fixes)
- Agent can chain multiple features in a single session

This is your Phase 2 COO capability: autonomous within bounds, with the bounds being the branch protection rules and your review.

## What to Build First (The Priority Backlog)

Ordered by "enables everything else":

```
PRIORITY 1: Core Infrastructure (Week 1-2)
├── Clean up repo (P1 above)
├── Verify pytest works
├── Set up CI/CD (GitHub Actions)
├── Resolve Python/Node question (document decision)
└── Create the state/ directory structure

PRIORITY 2: Briefing and State Management (Week 2-3)
├── Daily briefing generator
├── Capture file triage (capture.md → GitHub Issues)
├── BACKLOG.md auto-generator from GitHub Issues
├── METRICS.md tracker (costs, velocity, experiment status)
└── Session logging system

PRIORITY 3: Content and Product Tools (Week 3-4)
├── LinkedIn post draft generator (from A1 spec)
├── Content reformatter (LinkedIn → Twitter → Substack variants)
├── Gumroad listing generator (from product specs)
└── PDF generator for B5 governance guide

PRIORITY 4: Monitoring and Automation (Week 4-6)
├── Web monitoring agent tasks (HN, Reddit, market sources)
├── Cost tracking and budget alerting
├── Scheduled task runner (cron integration)
└── Alert delivery (WhatsApp/Telegram/email)

PRIORITY 5: Multi-Agent Coordination (Week 8+)
├── Shared state sync mechanism
├── Task routing protocol
├── Cross-agent handoff automation
└── Aggregated reporting
```

---

# 5. REVENUE CHANNEL OPERATIONALIZATION

## Portfolio Summary

From our previous discussion, here's the complete portfolio with operational detail:

```
ACTIVE EXPERIMENTS (Launch Week 1-3):

A1  LinkedIn Daily Posts          Content    Week 1    $100/mo cost
A2  Substack Weekly              Content    Week 2    $60/mo cost
A3  Twitter Repurposing          Content    Week 2    $30/mo cost
A4  Reddit/HN Strategic Posts    Content    Week 3    $20/mo cost
B2  Prompt Template Pack         Product    Week 1    $15 build
B5  Governance Framework Guide   Product    Week 1    $25 build

QUEUED EXPERIMENTS (Launch Week 3-8):

B1  Agent Ops Starter Kit        Product    Week 3    $20 build
B3  AI Ops Cost Calculator       Product    Week 2    $15 build (lead magnet)
B4  Solo AI Operator Dashboard   Product    Week 4    $15 build
C2  Curated AI Ops Digest        Service    Week 3    $40/mo cost

FUTURE EXPERIMENTS (After Week 8 review):

C1  Automated AI Stack Audit     Service    Week 6+   $20/delivery
C3  Architecture Review Service  Service    Week 8+   $10/delivery
D1  Open-Source LifeOS Component Asset      Week 6+   $30 build
D2  GitHub Sponsors              Asset      Week 4+   $10 setup
D3  Course/Workshop              Asset      Week 10+  $50 build
```

## Revenue Math (Honest)

Let's model what different levels of success look like across the portfolio:

### Bear Case (Month 3) — Most Likely
```
LinkedIn:       500 followers, 3-5% engagement → no direct revenue
                but provides distribution for products
Substack:       100 free subs, 5 paid at $10/mo     = $50/mo
B5 Guide:       10 total sales at $49                = $490 total ($163/mo avg)
B2 Prompts:     15 total sales at $19                = $285 total ($95/mo avg)
B3 Calculator:  Free lead magnet → 30 email captures = $0 (but builds list)
C2 Digest:      3 subscribers at $15/mo              = $45/mo

Total recurring: ~$95/mo
Total one-time (amortized): ~$258/mo
Total: ~$353/mo

Costs:
Agent compute: ~$200/mo
Gumroad fees: ~$30/mo
GCP (if Employee deployed): ~$75/mo
Total costs: ~$305/mo

Net: ~$48/mo
```

This is near-breakeven. Not life-changing. But you've validated which channels have signal and which don't.

### Base Case (Month 3) — If One Thing Gets Traction
```
LinkedIn:       1,500 followers → drives product sales
Substack:       300 free, 25 paid at $10/mo          = $250/mo
B5 Guide:       30 sales at $49                      = $1,470 total ($490/mo avg)
B2 Prompts:     40 sales at $19                      = $760 total ($253/mo avg)
B1 Starter Kit: 10 sales at $79                      = $790 total ($263/mo avg)
C2 Digest:      10 subscribers at $15/mo             = $150/mo

Total recurring: ~$400/mo
Total one-time (amortized): ~$1,006/mo
Total: ~$1,406/mo

Costs: ~$350/mo (slightly higher compute for more content)
Net: ~$1,056/mo
```

This hits your $1K/month target. The key variable is whether LinkedIn provides enough distribution to drive product sales.

### Bull Case (Month 3) — If Content Goes Viral or Niche Resonates
```
LinkedIn:       5,000+ followers → significant inbound
Substack:       1,000 free, 80 paid at $10/mo        = $800/mo
B5 Guide:       100 sales at $99 (price increase)     = $9,900 total ($3,300/mo)
Product bundle: 50 sales at $149                      = $7,450 total ($2,483/mo)
C2 Digest:      30 subscribers at $15/mo              = $450/mo
Inbound consulting/advisory:                          = $500-2,000/mo

Total: $5,000-7,000/mo
```

Unlikely at month 3, but possible by month 6 if content resonates. This is where compounding kicks in.

## Operationalizing Each Revenue Channel

### B5: Governance Framework Guide (Your Fastest Revenue)

**Why this ships first:** You've already written the content. The agent generalizes and packages it. You review. It could be on Gumroad in 3 days.

```
Day 1: Agent Build
├── Agent reads your Agent Architecture doc + governance docs
├── Generalizes: removes LifeOS-specific references
├── Structures into the chapter outline from B5 spec
├── Produces PDF draft
└── Writes Gumroad listing copy

Day 2: Your Review (3 hours)
├── Read full draft
├── Add sharp observations, "what actually happens" notes
├── Cut anything generic or padded
├── Review templates for usability
└── Final formatting pass

Day 3: Launch
├── Upload to Gumroad ($0 to list)
├── Set price: $49 (launch), $99 (after 20 sales)
├── Add link to LinkedIn profile
├── Write LinkedIn post about it (not salesy — share a key insight,
│   mention the guide exists)
└── Share in 2-3 relevant online communities
```

**Ongoing maintenance:** Monthly update incorporating new learnings. Agent drafts update, you review. Takes 1 hour/month.

### Substack: The Content Engine

```
SUBSTACK SETUP (20 minutes):

Name: Something that signals "practitioner, not thought leader"
  Options:
  - "Agent Operations Log"
  - "The Autonomous Operator"
  - "Building in the Open" (generic but proven format)
  - "Ship's Log" (nautical metaphor for solo navigation)

Structure:
- Free tier: Weekly post (the main content)
- Paid tier ($10/month): Raw materials
  ├── Actual prompt templates used that week
  ├── Cost breakdowns with real numbers
  ├── Configuration files and code snippets
  ├── Failure post-mortems with technical detail
  └── Early access to products (B2, B5, etc.)

The paid tier is NOT "better writing." It's "raw materials."
Free readers get the narrative. Paid readers get the toolkit.
This distinction matters — it's clear, defensible value.

CONTENT CALENDAR (Agent maintains):

Week 1: "Why I killed my vision document" (hooks with contrarian angle)
Week 2: "What an autonomous AI agent actually costs to run" (real numbers)
Week 3: "The governance problem nobody's solving" (leads to B5)
Week 4: "My first month of AI operations: honest numbers" (retrospective)
Week 5: "The agent-as-employee model" (your Employee spec, generalized)
Week 6: "Why most AI agent demos are lies" (contrarian, engagement driver)
Week 7: "Building a task management system that maintains itself"
Week 8: "Month 2: what worked, what I killed, what surprised me"

Each post has a natural product mention:
- Governance posts → B5 guide
- Operations posts → B1 starter kit
- Cost posts → B3 calculator
- Prompt posts → B2 template pack

This isn't forced — these posts ARE about the products' subject matter.
```

### The Cross-Channel Content Machine

```
ONE INSIGHT → MULTIPLE CHANNELS (Agent does the reformatting):

Source: Your weekly Substack post about agent governance

LinkedIn (Monday):
  → 200-word post extracting the key insight
  → No link in body (algorithm penalty)
  → Link in first comment to full Substack post
  → Hashtags: #AIAgents #AIGovernance #BuildInPublic

Twitter/X (Tuesday):
  → Thread (5-7 tweets) expanding the insight
  → More technical detail than LinkedIn
  → Link to Substack in final tweet

Reddit (Wednesday, if appropriate):
  → Post in r/artificial or r/MachineLearning
  → Full context, not just a link
  → Reddit hates self-promotion; add genuine value

HN (Thursday, if topic is technical enough):
  → Submit Substack link as "Show HN" or regular post
  → Only if the content genuinely belongs there

Agent workflow:
1. Substack post finalized (Sunday/Monday)
2. Agent produces variants for each channel
3. You review all variants in one batch (~15 min)
4. Agent posts on schedule (or you post manually)
5. Agent monitors engagement across all channels
6. Weekly report: which channel drove the most traffic/subs
```

## Revenue Infrastructure

### Gumroad Setup
```
Products to list:
1. B5 Governance Guide — $49
2. B2 Prompt Template Pack — $19
3. Bundle (B5 + B2) — $59

Gumroad settings:
- Enable email collection (even for free products)
- Set up a simple thank-you email (agent drafts)
- Enable affiliate program (10-25% commission) once you have sales
  → Incentivizes others to promote your products
- Create a "free sample" product: 
  → First chapter of B5 or a subset of B2
  → Collects email addresses for future launches
```

### Email List
```
Every product interaction captures an email. This becomes your owned channel.

Email sequence (agent drafts, you review):
1. Purchase thank-you + product delivery
2. Day 3: "Here's how to get the most out of [product]"
3. Day 7: "Other resources you might find useful" (cross-sell)
4. Ongoing: Monthly update when products are updated

Use Gumroad's built-in email or Buttondown (free tier: 100 subscribers).
Don't overcomplicate this. The list exists to notify about new products.
```

### Pricing Psychology
```
The anchor product is B5 at $49-99.
Everything else is priced relative to it.

B2 at $19 feels cheap next to B5.
Bundle at $59 feels like a deal vs. $68 separate.
Paid Substack at $10/month feels trivial.
C2 digest at $15/month is priced just above Substack 
  (it's a different, more curated product).

Future products price upward:
B1 Starter Kit: $79 (more comprehensive than B5)
C1 Stack Audit: $199-499 (service, not product)
D3 Course: $149-199 (highest-value offering)
```

---

# 6. ARCHITECTURE RECONCILIATION

## The Gap Between Your Docs and Your Repo

Your architecture docs describe a sophisticated multi-agent system with governance councils, phase transitions, and autonomous kernel evolution.

Your repo has 28 commits, a committed venv, and scattered test directories.

These need to converge. Here's how.

## What Your Docs Got Right

1. **The principal-agent governance model.** GREEN/YELLOW/RED/BLACK autonomy levels are genuinely good. Keep this.

2. **The Employee/COO separation.** Exploration probe vs. kernel seed is a clean conceptual split. The implementation details need work but the concept is sound.

3. **Charter-based autonomy.** Defining boundaries in a readable document that both human and agent reference is the right approach.

4. **Fail-closed default.** When uncertain, ask. This is the correct starting posture for autonomous agents.

5. **Audit-grade evidence.** Logging decisions with rationale. Essential and often overlooked.

## What Your Docs Got Wrong

1. **Governance before capability.** You designed Phase 4 governance for a Phase 0 system. Invert this.

2. **Google Drive as state.** Use the repo for COO state, Google Drive only for cross-agent coordination.

3. **Session-bound COO.** The kernel seed can't build momentum if it only runs when you're at your desk. The fix is scheduled tasks (Phase 1.5).

4. **No cost model.** The architecture specifies Opus as the default model. At current pricing, this is likely 5-10x more expensive than necessary for most tasks. Default to Sonnet.

5. **No degradation path.** What happens when API costs exceed budget? When OpenClaw has a breaking change? When GCP goes down? The architecture needs failure modes, not just happy paths.

6. **Over-specified future states.** Phase 4 COO with "self-modification within bounds" is a research problem, not an engineering milestone. Remove it from the roadmap and replace with "evaluate feasibility at Phase 3."

## The Reconciled Architecture

```
LAYER 1: FOUNDATION (Build Now)
├── LifeOS Repo (Python)
│   ├── runtime/          → Core system logic
│   ├── tools/            → CLI tools and utilities
│   ├── config/           → Configuration management
│   ├── tests/            → Automated tests
│   ├── state/            → System state (BACKLOG, METRICS, etc.)
│   ├── docs/             → Architecture, governance, operations
│   └── scripts/          → Deployment and setup scripts
│
├── COO (Claude Code → OpenClaw Local)
│   ├── Session-based initially
│   ├── Scheduled tasks at Phase 1.5
│   ├── Autonomous within bounds at Phase 2
│   └── State: LifeOS repo files
│
└── Infrastructure
    ├── GitHub (repo, issues, actions, PRs)
    ├── Local dev environment (WSL2)
    └── CI/CD (GitHub Actions)

LAYER 2: AGENT (Build Week 2-4)
├── Employee (OpenClaw on GCP)
│   ├── Hardened config
│   ├── Dedicated accounts
│   ├── Charter-based autonomy
│   └── Reports to shared state doc
│
└── Coordination
    ├── Google Drive shared state doc (cross-agent)
    ├── GitHub Issues (task management)
    └── WhatsApp/Telegram (notifications)

LAYER 3: AUTOMATION (Build Week 4-8)
├── Scheduled Tasks (cron)
│   ├── Daily briefing generation
│   ├── Capture file triage
│   ├── Content draft preparation
│   ├── Monitoring sweeps
│   └── Cost tracking
│
└── Event-Driven Actions
    ├── New GitHub Issue → assign and triage
    ├── PR created → run tests
    ├── Budget threshold hit → alert
    └── Monitoring trigger → notify

LAYER 4: ORCHESTRATION (Build Week 8+)
├── COO assigns tasks to Employee
├── Status aggregation
├── Cross-agent handoffs
└── Revenue experiment tracking

LAYER 5: SCALE (Build Week 16+)
├── Additional agents (as needed)
├── Governance formalization
├── Self-assessment capabilities
└── [Phase 3+ from your architecture doc]
```

## Repo Restructure

Your current repo structure (from GitHub):
```
.github/
artifacts/
config/
doc_steward/
docs/
logs/
project_builder/
recursive_kernel/
runtime/
runtime_state/PRE_HARDENING_AMU0/
scripts/
tests/_artifacts/
tests_doc/
tests_recursive/
tools/
venv/                          ← DELETE FROM REPO
.gitignore
README.md
pyproject.toml
pytest.ini
test_budget_concurrency.db     ← DELETE FROM REPO
```

Questions to answer (I can't read the files, so you'll need to assess):

```
1. doc_steward/ — Is this a working tool or a concept? 
   If working → keep and document
   If concept → move to docs/designs/ or archive

2. project_builder/ — Same question.

3. recursive_kernel/ — Is this the core runtime? 
   Rename to something clearer if so.

4. runtime/ vs recursive_kernel/ — Are these overlapping? 
   Consolidate if so.

5. runtime_state/PRE_HARDENING_AMU0/ — What is this?
   If it's an old state snapshot → archive or delete
   If it's needed → document why

6. artifacts/ — Build artifacts? Test artifacts? 
   If generated → add to .gitignore
   If curated → document

7. logs/ — Should logs be in the repo?
   Usually no. Add to .gitignore unless these are historical records.

8. tests/ vs tests_doc/ vs tests_recursive/ — Consolidate.
```

Proposed clean structure:
```
.github/
  workflows/
    test.yml                   # CI pipeline
  ISSUE_TEMPLATE/
    task.md
    experiment.md
    decision.md
config/                        # System configuration
docs/
  architecture/                # Technical design docs
  governance/                  # Governance specs and charters
  operations/                  # Operational runbooks
  archive/                     # Old docs preserved but not authoritative
runtime/                       # Core LifeOS system (Python)
  __init__.py
  briefing.py                  # Daily briefing generator
  capture.py                   # Capture file triage
  state.py                     # State management
  cli.py                       # CLI interface
tools/                         # Standalone utilities
scripts/                       # Deployment, setup, maintenance scripts
tests/                         # All tests (consolidated)
  unit/
  integration/
state/                         # System state (tracked in git)
  CURRENT_FOCUS.md
  EXPERIMENTS.md
  METRICS.md
  WEEKLY_REVIEWS/
.gitignore
README.md
BACKLOG.md                     # Agent-maintained
DECISIONS.md                   # Decision log
pyproject.toml
pytest.ini
```

---

# 7. BRANCH EXPLORATIONS (EMERGENT INSIGHTS)

## Branch 1: The "Build in Public" Content IS the Product Discovery Mechanism

An insight that emerged while writing the revenue section: your content strategy isn't just about revenue from content. It's a discovery mechanism for what people will actually pay for.

```
The feedback loop:

LinkedIn post about agent governance 
  → Gets 500 impressions, 2% engagement
  → 3 comments say "how do you actually implement this?"
  → SIGNAL: People want the implementation guide, not the theory
  → B5 guide should emphasize implementation, not frameworks
  → Next LinkedIn post: "Here's the actual charter template I use"
  → Gets 2,000 impressions, 5% engagement
  → 10 DMs asking for the full template
  → SIGNAL: The charter template alone has demand
  → Price B2 prompt pack higher, or break charter template into its own product

This loop happens NATURALLY if you're posting consistently.
Without the content, you're guessing about what to build.
With the content, the audience tells you what to build.
```

This is why A1 (LinkedIn) is truly the first priority, even ahead of products. The products are more valuable after you have audience feedback on what people actually want.

## Branch 2: The OpenClaw Lock-In Risk Is Real

Your entire agent infrastructure depends on OpenClaw. This is your R7 risk, and you rated it "Low impact." I disagree. Let me expand:

```
SCENARIO: OpenClaw maintainers change the API, go closed-source, 
pivot to a different architecture, or abandon the project.

Impact on you:
- Employee agent: dead
- COO agent (OpenClaw): dead
- All agent automation: dead
- All investment in OpenClaw-specific configs: wasted
- Recovery: rebuild on different framework (weeks to months)

Mitigation strategies:

1. ABSTRACTION LAYER (Medium effort, high value)
   ├── Define your own agent interface (AgentRunner, TaskHandler, etc.)
   ├── OpenClaw becomes an implementation detail behind the interface
   ├── If OpenClaw breaks, swap the implementation, keep the interface
   └── This is standard software engineering; surprising it's not in your architecture

2. PORTABLE STATE (Low effort, high value)
   ├── You're already doing this with file-based state
   ├── Ensure agent prompts/charters are framework-agnostic
   ├── Don't use OpenClaw-specific features that aren't portable
   └── Your charter template is framework-agnostic — good

3. ALTERNATIVE FAMILIARITY (Low effort, medium value)
   ├── Know what you'd switch to if OpenClaw died
   ├── Candidates: Claude Code (you already use it), 
   │   custom Python agent loop, other frameworks
   ├── Don't build for them now, but know the migration path
   └── Employee task: "Research top 5 OpenClaw alternatives. 
       Assess migration difficulty for our architecture."

4. COMMUNITY ENGAGEMENT (Low effort, low-medium value)
   ├── Watch the OpenClaw repo for breaking changes
   ├── Pin your version (don't auto-update)
   ├── Test upstream changes before adopting
   └── If you're a significant user, provide feedback upstream
```

## Branch 3: The Capture System Is More Important Than It Looks

The `capture.md` file seems trivial. It's not. It's the system's primary input sensor. If capture friction is too high, the entire system starves.

```
CAPTURE FRICTION ANALYSIS:

Desktop (at workstation):
- Open file, type, save → LOW FRICTION ✓
- Voice: speak, transcribe, append → LOWER FRICTION ✓✓

Mobile (away from desk):
- Open phone, open file app, type → MEDIUM FRICTION ✗
- This is where capture dies for most systems

The fix: Make capture available everywhere.

OPTIONS:
1. Google Keep / Apple Notes → sync to capture.md via agent
   Agent periodically checks your notes app, copies to capture.md
   
2. WhatsApp/Telegram bot
   Message your Employee agent: "note: tried X, didn't work because Y"
   Agent writes to capture.md
   THIS IS PROBABLY THE BEST OPTION — you already have your phone,
   WhatsApp is always open, zero new apps to install

3. Email to a dedicated address
   Email employee@yourdomain.com with subject line "capture: ..."
   Employee agent monitors inbox, extracts captures
   
4. Voice memo → transcription → capture
   Record voice memo, agent transcribes and triages
   Highest information density, lowest friction

RECOMMENDATION: 
Start with WhatsApp to Employee agent.
"Hey Employee, capture: spent $45 on API costs today building the 
briefing generator. Sonnet worked fine, didn't need Opus."
Employee writes to capture.md. Done.
```

## Branch 4: Your Finance Background Is An Underexploited Asset

You're approaching revenue through content and info products. Nothing wrong with that. But your actual comparative advantage is quantitative analysis and financial systems design.

```
OVERLOOKED REVENUE ANGLES:

1. AI Cost Optimization Consulting
   Most companies deploying AI have no idea what they're actually spending.
   You understand cost modeling, API pricing, and operational efficiency.
   
   Product: "AI Cost Audit" — fixed price, agent-delivered assessment
   of a company's AI spend with optimization recommendations.
   
   Why you: Your finance background makes "how to think about AI costs"
   a natural strength. Most AI consultants are engineers who can't do 
   financial modeling.

2. Quantitative Framework for AI Capability Assessment
   Your governance docs already contain elements of this.
   Formalize into a scoring/assessment framework.
   
   Product: Assessment tool or methodology that helps companies
   evaluate which tasks to automate and what the expected ROI is.
   
   Why you: Portfolio management IS capability assessment.
   "Which positions deserve capital allocation" maps directly to
   "which tasks deserve agent automation."

3. Risk Management for AI Operations
   Your RED/BLACK escalation model is a risk management framework.
   Most AI companies have no operational risk framework for agents.
   
   Product: "AI Operations Risk Framework" — companion to B5,
   focused specifically on risk identification, measurement, 
   and mitigation for autonomous agent deployments.

These are HIGHER-VALUE products than generic prompt packs.
They leverage your actual background rather than competing with 
every other AI content creator on generic topics.
```

## Branch 5: The LifeOS Name and Positioning Question

"LifeOS" as a name has a problem: there are at least 5 other projects on GitHub called "LifeOS" (I found them during my search). The name is generic and hard to own.

```
OPTIONS:

1. Keep "LifeOS" internally, brand products differently
   Your governance guide doesn't need to mention LifeOS.
   Your content brand can be your name or a different brand.
   LifeOS remains your private infrastructure project.

2. Rename the project
   Something more specific and ownable.
   "Governed Agent Operations" → GAO
   "Autonomous Operations Framework" → AOF
   "Principal-Agent Operating System" → PAOS
   None of these are great. The point is: think about this before
   you open-source anything or build a public brand around the name.

3. Accept the name collision
   Your LifeOS is different enough that it won't matter initially.
   If you gain traction, you'll need to differentiate.

RECOMMENDATION: Option 1. Keep "LifeOS" for internal/personal use.
Brand your public-facing products and content under a different name
that you can own. Your LinkedIn personal brand is probably the most
valuable brand asset anyway.
```

## Branch 6: The "Sole Human Employee" Constraint Is Actually Valuable

Your vision of being "the sole human employee of an AI-run operation" is unusual. Most AI content targets teams. This positions you uniquely:

```
The "solo AI operator" niche:
- Growing rapidly (more people going solo with AI tools)
- Underserved (most tools and content target teams)
- Your lived experience IS the product
- No one can fake this — you're either doing it or you're not

Content/product implications:
- Frame everything from the solo operator perspective
- "How I manage 5 workstreams without a team"
- "The solo operator's guide to AI governance"
- "Why I don't need employees (and what I need instead)"
- This IS your brand differentiator
```

---

# 8. MASTER SEQUENCING: THE FIRST 90 DAYS

## Week 1: Foundation + First Shots

```
DAY 1 (Monday):
├── Set up COO as Claude Code (Option A)
│   ├── Create ~/lifeos-coo/CONTEXT.md
│   ├── Create ~/capture.md
│   └── First COO session: triage this document into tasks
├── Clean repo (remove venv, test db, update .gitignore)
├── Set up GitHub Issues labels and milestones
└── Write first LinkedIn post (from seed topics)

DAY 2 (Tuesday):
├── LinkedIn post #2
├── Agent begins B5 governance guide generalization
├── Set up Gumroad account
└── Verify pytest works on LifeOS repo

DAY 3 (Wednesday):
├── LinkedIn post #3
├── Review B5 draft (first pass)
├── Agent begins B2 prompt template curation
└── Set up CI/CD (GitHub Actions for tests)

DAY 4 (Thursday):
├── LinkedIn post #4
├── Finalize B5 review
├── Upload B5 to Gumroad
├── Write LinkedIn post about B5 topic (not sales — insight)
└── Review B2 draft

DAY 5 (Friday):
├── LinkedIn post #5
├── Finalize B2, upload to Gumroad
├── Set up Substack account
├── Agent drafts first Substack post
└── COO: weekly review of what got done

WEEKEND:
├── Review Substack draft
├── Review week's LinkedIn metrics
├── Dump thoughts into capture.md
└── Rest. The system continues Monday.
```

## Week 2: Content Engine + Employee Prep

```
├── LinkedIn: continue daily posts (agent drafts, you review)
├── Publish first Substack post
├── Set up Twitter/X repurposing (agent reformats LinkedIn content)
├── Build B3 cost calculator (lead magnet)
├── Begin OpenClaw local testing (if not already working)
│   └── If broken: spend max 2 hours. If not fixed, defer to Week 3.
├── Employee: begin local proof tasks (Phase E1)
├── COO: establish daily briefing routine
└── METRICS: Track first week of LinkedIn data, any Gumroad views/sales
```

## Week 3: Expansion + First Revenue Data

```
├── LinkedIn: continue (should have 15+ posts by now)
├── Substack: second post
├── Launch C2 (curated AI ops digest) — agent does 95% of work
├── Begin Reddit/HN strategic posting (A4)
├── Build B1 Starter Kit (if B5 has sales signal)
├── Employee: if local proof passed, begin GCP deployment (Phase E2)
├── COO: capture→triage→brief loop should be running smoothly
├── First revenue review: any sales? any signals? what's resonating?
└── Adjust: double down on signal, cut what's dead
```

## Weeks 4-6: Compound or Pivot

```
├── By now you have data on:
│   ├── Which LinkedIn pillars get engagement
│   ├── Whether anyone's buying B5/B2
│   ├── Whether Substack is growing
│   ├── Whether C2 digest has subscribers
│   └── Whether Employee agent is useful on GCP
│
├── If products are selling:
│   ├── Create bundle offers
│   ├── Build next products (B1, B4)
│   ├── Add paid Substack tier
│   └── Consider open-sourcing a LifeOS component (D1)
│
├── If products aren't selling but content has engagement:
│   ├── The audience likes you but not your products
│   ├── Ask them what they want (LinkedIn poll, Substack question)
│   ├── Pivot product strategy based on feedback
│   └── Consider free lead magnets to build email list
│
├── If nothing's working:
│   ├── Honest assessment: is the niche wrong?
│   ├── Review Branch 4 (finance-specific angles)
│   ├── Consider higher-value, lower-volume approach
│   │   (consulting at $500/engagement vs. products at $49)
│   └── DO NOT keep doing what's not working. Change something.
│
├── Agent development continues regardless:
│   ├── COO should be at Phase 1.5 (scheduled tasks)
│   ├── Employee should be handling daily tasks
│   ├── Autonomous build loops should be producing code
│   └── This makes everything else easier
```

## Weeks 7-8: Major Review

```
WEEK 8 REVIEW AGENDA:

1. Revenue
   ├── Total revenue to date: $___
   ├── Monthly recurring: $___
   ├── Trajectory: growing / flat / declining
   └── Months of runway remaining at current burn: ___

2. Experiments
   ├── For each experiment: KILL / CONTINUE / DOUBLE DOWN
   ├── What's the #1 revenue opportunity?
   ├── What's consuming time without producing value?
   └── What would you do differently if starting over?

3. System
   ├── Is the COO agent actually saving you time?
   ├── Is the Employee agent producing useful work?
   ├── What's the total system cost (compute + APIs + infra)?
   ├── Is LifeOS closer to self-sustaining? By how much?
   └── What's the biggest bottleneck right now?

4. Personal
   ├── Are you energized or drained?
   ├── What work did you enjoy most?
   ├── What work did you hate?
   └── Is this still the right bet?

5. Next 8 Weeks
   ├── Updated priorities based on data
   ├── New experiments to launch
   ├── Dead experiments to bury
   └── Revised revenue target
```

## Weeks 9-12: Execute on Signal

Whatever the Week 8 review tells you, execute with the same framework: agent handles operations, you handle direction and judgment. The specific activities depend on what the data says. But the operating model should be proven by now.

---

# 9. RISK-ADJUSTED DECISION FRAMEWORK

## How to Make Decisions Under Runway Constraint

You're a former portfolio manager. Think about LifeOS decisions the way you'd think about portfolio construction:

```
POSITION SIZING (How much time/money to allocate):
├── Conviction × Size
├── High conviction + cheap to test → large allocation
├── Low conviction + cheap to test → small allocation
├── High conviction + expensive to test → medium allocation, staged
├── Low conviction + expensive to test → skip or defer

EXAMPLES:
├── LinkedIn daily posts (high conviction, cheap) → DO NOW, large allocation
├── B5 governance guide (high conviction, cheap) → DO NOW, medium allocation
├── GCP Employee deployment (medium conviction, medium cost) → STAGE IT
├── Full autonomous build loops (high conviction, expensive) → BUILD INCREMENTALLY
├── Course/workshop (low conviction, expensive) → DEFER to Week 10+
├── New agent framework evaluation (low conviction, medium cost) → EMPLOYEE TASK
```

```
STOP-LOSS (When to kill an experiment):
├── Time-based: didn't produce signal in N weeks
├── Cost-based: exceeded budget without proportional return
├── Energy-based: consistently drains you with no upside
├── Opportunity-cost-based: blocking something higher-value

TAKE-PROFIT (When to double down):
├── Revenue signal: paying customers exist
├── Engagement signal: growing audience, inbound interest
├── Capability signal: agent does it reliably, scales easily
├── Compounding signal: each iteration is better than the last
```

```
PORTFOLIO REBALANCING (Weekly):
├── What's overweight? (consuming too much time relative to value)
├── What's underweight? (has signal but not getting attention)
├── What's correlated? (multiple experiments testing the same thesis)
├── What's uncorrelated? (true diversification of revenue sources)
```

## The Meta-Risk: Architecture vs. Execution

The single biggest risk in this entire plan is that you retreat into architecture work when execution gets hard. You've demonstrated this pattern (months of governance docs, 28 commits). It's not laziness — it's a genuine cognitive preference. Designing systems IS your zone of genius.

```
MITIGATION:
├── Track your time allocation weekly
│   ├── Category A: Building/shipping (code, products, content)
│   ├── Category B: Designing/planning (docs, architecture, strategy)
│   ├── Category C: Operating (reviews, decisions, admin)
│   └── Target ratio: 60% A, 20% B, 20% C
│
├── If Category B exceeds 30% in any week → RED FLAG
│   You're retreating into design mode
│   Force yourself to ship something before designing more
│
├── "No design without implementation" rule:
│   Every architecture document must have a corresponding PR within 1 week
│   If it doesn't → the architecture was premature
│
└── Your COO agent should track this and flag it
```

---

# 10. THE META-QUESTION: WHAT LIFEOS ACTUALLY IS RIGHT NOW

## The Honest Assessment

LifeOS today is:
- A collection of thoughtful architecture documents
- A Python codebase with unclear functionality (I can't read the code but the signals suggest early-stage)
- A vision that's inspiring but ungrounded
- A governance framework for a system that doesn't operate

LifeOS in 30 days (if you execute this plan) is:
- A COO agent that maintains your task system and daily briefings
- An Employee agent doing useful research and monitoring
- A content engine producing daily LinkedIn posts and weekly Substack articles
- 2-3 digital products for sale on Gumroad
- A repo with CI/CD, clean structure, and autonomous build capability
- Data on what revenue channels have signal

LifeOS in 90 days is:
- Either generating meaningful revenue (base case: $1K/month) or you know why not
- A multi-agent system with proven coordination
- A growing audience that tells you what to build next
- A system that's closer to the Vision doc but built from the bottom up, not the top down

## The Fundamental Reframe

Your Vision doc describes LifeOS as a system that removes your operational constraints. That's the end state. The starting state is simpler:

**LifeOS right now is a bet that AI agents can do useful work without constant human supervision.**

Everything else — the 10 dimensions, the wealth stack, the influence engine, the legacy — depends on proving that one bet. One agent, doing one useful thing, reliably, without you holding its hand.

Prove that. Everything else follows.

## Final Note

This document is ~8,000 words of operational detail. It's a lot. Don't try to do everything at once. The Day 1 actions are:

```
1. Set up COO as Claude Code
2. Create capture.md
3. Clean the repo
4. Write your first LinkedIn post
5. Start the B5 governance guide generalization

That's it. That's Day 1. Everything else has a day.
```

The system builds itself — but only if you start it.
