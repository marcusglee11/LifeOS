# WIP & Non-Canonical Log

This file tracks all documents, protocols, and specifications that are currently in a **Work-In-Progress (WIP)** or **Non-Canonical** state. These items are NOT binding until ratified by the Council or CEO.

## Status Enum (Allowed Values)

**Valid status values:** `WIP | FINALIZED | CANONICAL | DEFERRED`

- **WIP**: Active work in progress, not yet complete
- **FINALIZED**: Complete but awaiting formal ratification/activation
- **CANONICAL**: Ratified and active (binding)
- **DEFERRED**: Work paused or postponed

## Active WIP Items

| Ref | Document | Class | Status | Target Maturity |
|-----|----------|-------|--------|-----------------|
| W1 | [CSO_Role_Constitution_v1.0.md](../01_governance/CSO_Role_Constitution_v1.0.md) | GOVERNANCE | FINALIZED | Functional MVP |
| W2 | [Emergency_Declaration_Protocol_v1.0.md](../02_protocols/Emergency_Declaration_Protocol_v1.0.md) | PROTOCOL | CANONICAL | Functional MVP |

| W4 | [Test_Protocol_v2.0.md](../02_protocols/Test_Protocol_v2.0.md) | PROTOCOL | WIP | Tier-2.5 Hardening |
| W6 | [ARTEFACT_INDEX_SCHEMA.md](../01_governance/ARTEFACT_INDEX_SCHEMA.md) | GOVERNANCE | WIP | Stewardship MVP |
| W7 | [QUICKSTART.md](../QUICKSTART.md) | GUIDE | WIP | Onboarding Ready |

## History

| Date | Item | Event | Agent |
|------|------|-------|-------|
| 2026-01-07 | W1-W7 | Created/Restored | antigravity |
| 2026-01-07 | W4 | Supersedes v1.0 | antigravity |
| 2026-01-07 | W3 | Stewarded v1.1 | antigravity |

---

**Rules for Engagement**:
1. Documents MUST maintain the `WIP (Non-Canonical)` header.
2. Effective dates MUST be marked `Provisional`.
3. Links to these documents in `INDEX.md` MUST include the `(WIP)` marker.
