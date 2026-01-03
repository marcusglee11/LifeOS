# DECISION LOG (append-only; low volume)

- **2026-01-02 — Decision:** Activate Tier-2.5 Semi-Autonomous Development Layer
  - **Why:** All activation conditions (F3, F4, F7) satisfied; Tier-2 tests 100% pass
  - **Scope:** Enables semi-autonomous doc stewardship, recursive builder, agentic missions
  - **Evidence:** [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](../01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md)

- **2026-01-02 — Decision:** Approve Stewardship Runner for agent-triggered runs
  - **Why:** Provides authoritative gating mechanism for stewardship ops with mandatory dry-run
  - **Scope:** Runtime stewardship, doc hygiene automation
  - **Evidence:** [Council_Review_Stewardship_Runner_v1.0.md](../01_governance/Council_Review_Stewardship_Runner_v1.0.md)

- **2026-01-03 — Decision:** Adopt thin control plane v1.1
  - **Why:** Reduces friction by externalising in-head state; prevents scaffolding spiral
  - **Scope:** Project admin via LIFEOS_STATE, BACKLOG, DECISIONS, INBOX
  - **Evidence:** `293f227`, `docs/00_admin/`

- **2026-01-03 — Decision:** Upgrade thin control plane to v1.2
  - **Why:** Refine evidence rules (anchoring), clarify hygiene triggers, adopt default sequencing rule
  - **Scope:** Admin hygiene protocols and evidence standards
  - **Evidence:** `3e545f7`, `docs/00_admin/`
