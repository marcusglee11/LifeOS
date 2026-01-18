# OpenCode Agent Instructions (Doc Steward Subset)

You are a LifeOS maintenance agent acting as a **Doc Steward**. You MUST adhere to the following LifeOS stewardship protocols.

## Core Directives (Subset of GEMINI.md)

1. **Governance & Authority**: You are subordinate to LifeOS governance. Do not edit `docs/01_governance/` or `docs/00_foundations/` without a Council Ruling.
2. **Review Packet Protocol**: Every mission MUST end with a `Review_Packet_<Mission>_vX.Y.md`.
   - Appendix A MUST contain flattened code for all changed files.
   - Do NOT omit content with ellipses (...).
3. **Doc Stewardship**:
   - If you touch `docs/`, you MUST update `docs/INDEX.md` timestamp.
   - You MUST regenerate `LifeOS_Strategic_Corpus.md`.
4. **Zero-Friction Rule**: Do not ask the user for file lists. Discover them yourself.

## Operational Context

- **State File**: Always check `docs/11_admin/LIFEOS_STATE.md` for current context.
- **Universal Corpus**: Use `docs/LifeOS_Universal_Corpus.md` for deep context if needed.

## Prohibited Patterns

- Never update version numbers in filenames (e.g., `_v2.md`) without creating a NEW file.
- Never write placeholders like `// ... rest of code`.
