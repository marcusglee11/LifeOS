# BACKLOG (prune aggressively; target ≤ 40 items)

## Now (ready soon; not in WIP yet)

### P0 (Critical)
- [ ] **G-CBS v1.0: Implement closure_manifest + validate_closure_bundle + build_closure_bundle** — DoD: validator PASS on A1/A2 — Owner: antigravity
- [ ] **G-CBS Invariant: Max 2 closure cycles then WAIVER or BLOCKED** — DoD: Hardcoded limit enforced — Owner: antigravity
- [ ] **G-CBS: Enforce no forbidden tokens in closure artefacts** — DoD: Scan for ellipses, PENDING, TBD, TODO — Owner: antigravity

### P1 (High)
- [ ] **Re-close A1/A2 using G-CBS** — DoD: Convert or rerun cleanly; replace waiver with strict PASS — Owner: antigravity
- [ ] **Standardize raw capture primitive** — DoD: cmd redirection + explicit exitcode file + hashes as reusable helper — Owner: antigravity
- [ ] **Finalize CSO_Role_Constitution v1.0** — DoD: CEO approved; markers removed — Owner: antigravity
- [ ] **Finalize Emergency_Declaration_Protocol v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Intent_Routing_Rule v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Test_Protocol v2.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize Tier_Definition_Spec v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize ARTEFACT_INDEX_SCHEMA v1.0** — DoD: Markers removed — Owner: antigravity
- [ ] **Finalize QUICKSTART v1.0** — DoD: Context scan pass complete — Owner: antigravity
- [x] **Suspend OpenCode Robot** — DoD: Processes killed, runners disabled — Owner: antigravity
- [ ] **Review OpenCode deletion logic** — DoD: Root cause of `git clean` found — Owner: antigravity

## Next (valuable, but not imminent)
- [ ] **Reactive Layer Hygiene: Tighten Canonical JSON** — DoD: Require explicit escape sequence for non-ASCII input (no permissive fallback) — Owner: antigravity
- [ ] **Reactive Layer Hygiene: Verify README Authority Pointer** — DoD: Ensure stable canonical link to authority anchor — Owner: antigravity
- [ ] **Tier-3 planning** — Why Next: After Tier-2.5 Phase 2 completes, scope Tier-3 Autonomous Construction Layer
- [ ] **Recursive Builder iteration** — Why Next: Recursive kernel exists but may need refinement
- [ ] **OpenCode Sandbox Activation** — Why Next: Enable doc steward/builder via API; requested via Inbox


## Later (not actionable / unclear / exploratory)
- [ ] **Fuel track exploration** — Why Later: Not blocking Core; future consideration per roadmap
- [ ] **Productisation of Tier-1/Tier-2 engine** — Why Later: Depends on Core stabilisation

## Done (last ~20 only)
- [x] **F3 — Tier-2.5 Activation Conditions Checklist** — Date: 2026-01-02
- [x] **F4 — Tier-2.5 Deactivation & Rollback Conditions** — Date: 2026-01-02
- [x] **F7 — Runtime ↔ Antigrav Mission Protocol** — Date: 2026-01-02
- [x] **Strategic Context Generator v1.2** — Date: 2026-01-03
- [x] **Security remediation (venv removal, gitignore, path sanitisation)** — Date: 2026-01-02
- [x] **Document Steward Protocol formalisation** — Date: 2026-01-01
- [x] **Agent Packet Protocol v1.0 (schemas, templates)** — Date: 2026-01-02
- [x] **F2 — API Evolution & Versioning Strategy** — Date: 2026-01-03
- [x] **F6 — Violation Hierarchy Clarification** — Date: 2026-01-03
- [x] **F1 — Artefact Manifest Completeness** — Date: 2026-01-03
- [x] **F5 — Obsolete Comment Removal** — Date: 2026-01-03
