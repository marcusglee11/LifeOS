---
paths: ["docs/**", "runtime/**"]
---
# Documentation Stewardship

- When modifying `docs/`, update `docs/INDEX.md` if you added, removed, or renamed a document.
- When modifying `runtime/` behavior, check if `docs/02_protocols/` needs updating.
- Run `python3 scripts/claude_doc_stewardship_gate.py` before committing if you modified docs/.
- Never modify `docs/00_foundations/` or `docs/01_governance/` without explicit Council approval.
