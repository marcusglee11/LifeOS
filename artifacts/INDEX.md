# Artifacts Index

**Last Updated**: 2026-01-04

## Directory Structure

| Folder | Purpose | Naming Convention |
|--------|---------|-------------------|
| `plans/` | Implementation plans, architecture plans | `Plan_<Topic>_v<X.Y>.md` |
| `review_packets/` | Completed work for CEO review | `Review_Packet_<Mission>_v<X.Y>.md` |
| `context_packs/` | Agent-to-agent handoff context | `ContextPack_<Type>_<UUID>.yaml` |
| `bundles/` | Zipped multi-file handoffs | `Bundle_<Topic>_<Date>.zip` |
| `missions/` | Mission telemetry logs | `<Date>_<Type>_<UUID>.yaml` |
| `packets/` | Structured YAML packets (inter-agent) | Per packet schema naming |
| `gap_analyses/` | Gap analysis artifacts | `GapAnalysis_<Scope>_v<X.Y>.md` |
| `for_ceo/` | **CEO pickup folder** — files requiring CEO action | Copies of originals |

## Protocol

1. All artifacts MUST use proper naming per convention
2. Files requiring CEO action MUST be copied to `for_ceo/`
3. Agent MUST auto-open Explorer to `for_ceo/` when notifying CEO
4. CEO clears `for_ceo/` after pickup

## Current Contents

### plans/
- `Plan_AgentDelegation_v0.1.md` — Phase 1 agent delegation architecture

### gap_analyses/
- `GapAnalysis_Constitutional_Enforcement_v0.1.md`

### for_ceo/
- `Plan_AgentDelegation_v0.1.md` — Awaiting review
