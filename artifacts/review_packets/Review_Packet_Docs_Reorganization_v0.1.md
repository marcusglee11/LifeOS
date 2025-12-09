# Review_Packet_Docs_Reorganization_v0.1

**Title:** Review_Packet_Docs_Reorganization_v0.1
**Version:** v0.1
**Author:** Antigravity Agent
**Date:** 2025-12-09
**Mission Context:** Docs Directory Reorganization & Grand Index
**Scope:** `docs/`, `config/`, `artifacts/`, `doc_steward/`

---

## Summary
Comprehensive reorganization of the `docs/` directory.

**Before:** 22 stray files at root (scripts, drafts, 3 indices)
**After:** 1 file at root (`INDEX.md`)

**Key Changes:**
- Moved 16 Python/config files to `doc_steward/scripts/`
- Moved `GEMINI.md` (Constitution) to `config/`
- Archived 2 draft READMEs to `99_archive/`
- Consolidated 3 indices → single `docs/INDEX.md`
- Updated `builder.py` to maintain `INDEX.md` for docs, config, artifacts
- Added `artifacts` domain to Recursive Kernel

---

## Grand Index Structure
```
/docs/INDEX.md         # 124 entries, auto-maintained
/config/INDEX.md       # 5 entries, auto-maintained
/artifacts/INDEX.md    # 3 entries, auto-maintained
```

All indices are now named `INDEX.md` (no version suffix) and rebuilt by the Recursive Kernel.

---

## Invariant Compliance
- **zero_donkey_work**: COMPLIANT
- **max_human_actions**: COMPLIANT (1 action: approval)

---

## Acceptance Criteria
- [x] `docs/` root contains only `INDEX.md`
- [x] All indices unified to `INDEX.md`
- [x] Recursive Kernel supports `artifacts` domain
- [x] All tests pass

---

## Appendix — Flattened Code Snapshots

### File: recursive_kernel/builder.py
```python
import os
from .planner import Task

class Builder:
    def build(self, task: Task) -> bool:
        if task.type == 'rebuild_index':
            if task.domain == 'docs':
                return self._rebuild_index("docs", "INDEX.md", "Documentation Index")
            elif task.domain == 'config':
                return self._rebuild_index("config", "INDEX.md", "Config Index")
            elif task.domain == 'artifacts':
                return self._rebuild_index("artifacts", "INDEX.md", "Artifacts Index")
        return False

    def _rebuild_index(self, directory: str, index_filename: str, title: str) -> bool:
        repo_root = os.getcwd()
        target_root = os.path.join(repo_root, directory)
        index_path = os.path.join(target_root, index_filename)
        
        if not os.path.exists(target_root):
            return False

        files_to_index = []
        for root, dirs, files in os.walk(target_root):
            for file in files:
                if file != index_filename:
                    rel_path = os.path.relpath(os.path.join(root, file), target_root).replace('\\', '/')
                    files_to_index.append(rel_path)
        
        files_to_index.sort()
        
        content = f"# {title}\n\n"
        for f in files_to_index:
            content += f"- [{f}](./{f})\n"
            
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
```

### File: config/recursive_kernel_config.yaml
```yaml
safe_domains:
  - docs
  - tests_doc
  - config
  - artifacts

test_command: "pytest"

max_diff_lines_auto_merge: 200

risk_rules:
  low_risk_paths:
    - "docs/"
    - "tests_doc/"
    - "config/"
    - "artifacts/"
```
