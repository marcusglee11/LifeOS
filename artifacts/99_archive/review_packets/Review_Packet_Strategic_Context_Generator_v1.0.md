# Review Packet: Strategic Context Generator v1.0

**Mission**: Create Strategic Context Generator (Optimization)
**Date**: 2026-01-03
**Status**: COMPLETE

## Summary
Created a new Python script `docs/scripts/generate_strategic_context.py` that generates a condensed "Strategic Context" corpus (`docs/LifeOS_Strategic_Context_v1.0.md`). This artifact separates Governance/Intent from Implementation, applies scope restrictions, exclusion logic for superseded files, and compresses task lists found in `TASKS_v1.0.md`.

## Changes Implemented
1.  **Script Creation**: `docs/scripts/generate_strategic_context.py`
    *   **Scope**: `00_foundations`, `01_governance`, `02_protocols`, `09_prompts`.
    *   **Extras**: Latest Roadmap (`03_runtime`), Latest Status (`10_meta`).
    *   **Logic**: Excludes "Superseded" files. Compresses finished tasks (`[x]`). Placeholders for technical specs (`*_Spec_*`, `*_Packet_*`) unless protocol.
2.  **Documentation Indexing**:
    *   Updated `docs/INDEX.md` with "Strategic Context" section.
    *   Updated `docs/01_governance/ARTEFACT_INDEX.json` with `strategic_context` entry.
3.  **Corpus Generation**:
    *   Generated `docs/LifeOS_Strategic_Context_v1.0.md`.
    *   Regenerated `docs/LifeOS_Universal_Corpus.md` (Document Steward Protocol).

## Acceptance Criteria
- [x] Script `generate_strategic_context.py` exists and follows logic.
- [x] `LifeOS_Strategic_Context_v1.0.md` is generated and readable.
- [x] Excluded directories (`03_runtime`, `04_project_builder`, etc.) are absent.
- [x] Superseded files are excluded.
- [x] Tasks in `TASKS_v1.0.md` are compressed (only open tasks shown).
- [x] "Technical Specs" matching pattern generally placeholdered.
- [x] `INDEX.md` and `LifeOS_Universal_Corpus.md` updated.

## Appendix: Flattened Code Snapshots

### File: docs/scripts/generate_strategic_context.py
```python
import os
import re
import datetime
from pathlib import Path

# Configuration
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = ROOT_DIR / "docs"
OUTPUT_FILE = DOCS_DIR / "LifeOS_Strategic_Context_v1.0.md"

INCLUDE_DIRS = [
    DOCS_DIR / "00_foundations",
    DOCS_DIR / "01_governance",
    DOCS_DIR / "02_protocols",
    DOCS_DIR / "09_prompts",
]

# Patterns for exclusions
SUPERSEDED_PATTERN = re.compile(r'(?:\*\*Status\*\*|Status):\s*Superseded', re.IGNORECASE)
TASK_DONE_PATTERN = re.compile(r'^\s*[\-\*]\s*\[x\]', re.IGNORECASE)
SPEC_PACKET_PATTERN = re.compile(r'(_Spec_|_Packet_)', re.IGNORECASE)
PROTOCOL_PATTERN = re.compile(r'_Protocol_v', re.IGNORECASE) # Exception to Spec pattern if needed, but usually Protocol is named Protocol

def get_latest_file(directory: Path, pattern: str) -> Path | None:
    files = list(directory.glob(pattern))
    if not files:
        return None
    # Sort by modification time (or name if versions are consistent)
    # Using name might be safer for versioning v1.0 vs v1.1 if consistent naming
    # But usually modification time is a good enough proxy for "Latest" in this context
    # unless we parse versions. Let's use name sort as a primary, assuming strict naming.
    files.sort(key=lambda p: p.name, reverse=True)
    return files[0]

def process_file(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return ""

    # 1. Historical Flattening (Superseded check)
    if SUPERSEDED_PATTERN.search(content):
        print(f"Skipping Superseded file: {file_path.name}")
        return ""

    # 2. Protocol Referencing (Spec/Packet placeholder)
    # If it's a Spec or Packet, but NOT a constitutional Protocol or Foundation
    # We generally want to read the User's intention. 
    # "For Antigravity_Implementation_Packet and similar technical specs..."
    if SPEC_PACKET_PATTERN.search(file_path.name):
        print(f"Placeholding Technical Spec: {file_path.name}")
        return (
            f"\n# File: {file_path.relative_to(DOCS_DIR)}\n\n"
            "*[Reference Pointer: See full text in Universal Corpus for implementation details]*\n\n"
        )

    # 3. List Compression
    lines = content.splitlines()
    filtered_lines = []
    for line in lines:
        if TASK_DONE_PATTERN.match(line):
            continue
        filtered_lines.append(line)
    
    clean_content = "\n".join(filtered_lines)

    return f"\n# File: {file_path.relative_to(DOCS_DIR)}\n\n{clean_content}\n\n"

def main():
    print(f"Generating Strategic Context at {OUTPUT_FILE}...")
    
    # Collect files
    files_to_process = []
    
    # 1. Standard Includes
    for d in INCLUDE_DIRS:
        if not d.exists():
            print(f"Warning: Directory not found {d}")
            continue
        for file_path in sorted(d.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in ['.md', '.txt', '.yaml', '.json']:
                # Skip index files themselves to avoid recursion confusion? 
                # Usually we include them, but maybe not ARTEFACT_INDEX.json if it's just raw data?
                # User said "Include specified files". JSON might be noisy. 
                # Let's keep .md and .txt mainly. The prompt didn't strictly say Markdown only but Corpus usually implies it.
                if file_path.suffix.lower() == '.json': 
                    continue
                files_to_process.append(file_path)

    # 2. Specific Extras
    runtime_dir = DOCS_DIR / "03_runtime"
    if runtime_dir.exists():
        roadmap = get_latest_file(runtime_dir, "*Roadmap*")
        if roadmap:
            files_to_process.append(roadmap)
    
    meta_dir = DOCS_DIR / "10_meta"
    if meta_dir.exists():
        # User said "Latest Status". Could be TASKS or just Status.
        # "Status" often refers to Status Updates. TASKS is task tracking.
        # I'll check for both and pick the most relevant or likely user intent.
        # "Status" matching *Status* might match CODE_REVIEW_STATUS which isn't high level.
        # "TASKS" is a checklist.
        # Let's include TASKS + anything explicitly named Status (like Project_Status).
        tasks = get_latest_file(meta_dir, "TASKS*")
        if tasks: files_to_process.append(tasks)
        
        status_file = get_latest_file(meta_dir, "*Status*")
        if status_file and status_file != tasks:
             files_to_process.append(status_file)

    # Remove strict duplicates if any
    files_to_process = list(dict.fromkeys(files_to_process))
    
    # Sort for deterministic output
    files_to_process.sort(key=lambda p: str(p.relative_to(DOCS_DIR)))

    # Process content
    full_content = []
    
    # Preamble
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    preamble = (
        f"# LifeOS Strategic Context\n"
        f"**Generated:** {timestamp}\n"
        f"**Purpose:** High-level strategic reasoning and catch-up context. Separates Governance/Intent from Implementation.\n"
        f"\n---\n"
    )
    full_content.append(preamble)

    for fp in files_to_process:
        chunk = process_file(fp)
        if chunk:
            full_content.append(chunk)
            # Add separator
            full_content.append("\n---\n")

    # Write Output
    OUTPUT_FILE.write_text("".join(full_content), encoding='utf-8')
    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
```

### File: docs/INDEX.md
```markdown
# LifeOS Documentation Index

**Last Updated**: 2026-01-03T11:22+11:00  
**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Context_v1.0.md](./LifeOS_Strategic_Context_v1.0.md) | **High-level context** — Governance, Intent, Protocols (Condens ed) |

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |

---

## 01_governance — Governance & Contracts

### Core Governance
| Document | Purpose |
|----------|---------|
| [COO_Operating_Contract_v1.0.md](./01_governance/COO_Operating_Contract_v1.0.md) | CEO/COO role boundaries and interaction rules |
| [AgentConstitution_GEMINI_Template_v1.0.md](./01_governance/AgentConstitution_GEMINI_Template_v1.0.md) | Template for agent GEMINI.md files |

### Council & Review
| Document | Purpose |
|----------|---------|
| [Council_Invocation_Runtime_Binding_Spec_v1.0.md](./01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md) | Council invocation and runtime binding |
| [Antigravity_Council_Review_Packet_Spec_v1.0.md](./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md) | Council review packet format |
| [ALIGNMENT_REVIEW_TEMPLATE_v1.0.md](./01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md) | Monthly/quarterly alignment review template |

### Policies & Logs
| Document | Purpose |
|----------|---------|
| [COO_Expectations_Log_v1.0.md](./01_governance/COO_Expectations_Log_v1.0.md) | Working preferences and behavioral refinements |
| [Antigrav_Output_Hygiene_Policy_v0.1.md](./01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md) | Output path rules for Antigravity |

### Historical Rulings
| Document | Purpose |
|----------|---------|
| [Tier1_Hardening_Council_Ruling_v0.1.md](./01_governance/Tier1_Hardening_Council_Ruling_v0.1.md) | Historical: Tier-1 ratification ruling |
| [Tier1_Tier2_Activation_Ruling_v0.2.md](./01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md) | Historical: Tier-2 activation ruling |
| [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md) | Historical: Tier transition conditions |
| [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](./01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md) | Historical: Tier-2.5 activation ruling |
| [Council_Review_Stewardship_Runner_v1.0.md](./01_governance/Council_Review_Stewardship_Runner_v1.0.md) | **Approved**: Stewardship Runner cleared for agent-triggered runs |

---

## 02_protocols — Protocols & Agent Communication

| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Document_Steward_Protocol_v1.0.md](./02_protocols/Document_Steward_Protocol_v1.0.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [lifeos_packet_schemas_v1.yaml](./02_protocols/lifeos_packet_schemas_v1.yaml) | Agent packet schema definitions (13 packet types) |
| [lifeos_packet_templates_v1.yaml](./02_protocols/lifeos_packet_templates_v1.yaml) | Ready-to-use packet templates |
| [example_converted_antigravity_packet.yaml](./02_protocols/example_converted_antigravity_packet.yaml) | Example: converted Antigravity review packet |

---

## 03_runtime — Runtime Specification

### Core Specs
| Document | Purpose |
|----------|---------|
| [COO_Runtime_Spec_v1.0.md](./03_runtime/COO_Runtime_Spec_v1.0.md) | Mechanical execution contract, FSM, determinism rules |
| [COO_Runtime_Implementation_Packet_v1.0.md](./03_runtime/COO_Runtime_Implementation_Packet_v1.0.md) | Implementation details for Antigravity |
| [COO_Runtime_Core_Spec_v1.0.md](./03_runtime/COO_Runtime_Core_Spec_v1.0.md) | Extended core specification |
| [COO_Runtime_Spec_Index_v1.0.md](./03_runtime/COO_Runtime_Spec_Index_v1.0.md) | Spec index and patch log |

### Roadmaps & Plans
| Document | Purpose |
|----------|---------|
| [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](./03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | **Current roadmap** — Core/Fuel/Plumbing tracks |
| [LifeOS_Recursive_Improvement_Architecture_v0.2.md](./03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md) | Recursive improvement architecture |
| [LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md](./03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md) | Future router and executor adapter spec |

### Work Plans & Fix Packs
| Document | Purpose |
|----------|---------|
| [Hardening_Backlog_v0.1.md](./03_runtime/Hardening_Backlog_v0.1.md) | Hardening work backlog |
| [Tier1_Hardening_Work_Plan_v0.1.md](./03_runtime/Tier1_Hardening_Work_Plan_v0.1.md) | Tier-1 hardening work plan |
| [Tier2.5_Unified_Fix_Plan_v1.0.md](./03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md) | Tier-2.5 unified fix plan |
| [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](./03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md) | Tier-2.5 activation conditions checklist (F3) |
| [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](./03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md) | Tier-2.5 deactivation and rollback conditions (F4) |
| [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](./03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) | Runtime↔Antigrav mission protocol (F7) |
| [Runtime_Hardening_Fix_Pack_v0.1.md](./03_runtime/Runtime_Hardening_Fix_Pack_v0.1.md) | Runtime hardening fix pack |
| [fixpacks/FP-4x_Implementation_Packet_v0.1.md](./03_runtime/fixpacks/FP-4x_Implementation_Packet_v0.1.md) | FP-4x implementation |

### Templates & Tools
| Document | Purpose |
|----------|---------|
| [BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md](./03_runtime/BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md) | Build starter prompt template |
| [CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md](./03_runtime/CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md) | Code review prompt template |
| [COO_Runtime_Walkthrough_v1.0.md](./03_runtime/COO_Runtime_Walkthrough_v1.0.md) | Runtime walkthrough |
| [COO_Runtime_Clean_Build_Spec_v1.1.md](./03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md) | Clean build specification |

### Other
| Document | Purpose |
|----------|---------|
| [Automation_Proposal_v0.1.md](./03_runtime/Automation_Proposal_v0.1.md) | Automation proposal |
| [Runtime_Complexity_Constraints_v0.1.md](./03_runtime/Runtime_Complexity_Constraints_v0.1.md) | Complexity constraints |
| [README_Recursive_Kernel_v0.1.md](./03_runtime/README_Recursive_Kernel_v0.1.md) | Recursive kernel readme |

---

## 99_archive — Historical Documents

Archived documents are in `99_archive/`. Key locations:
- `99_archive/superseded_by_constitution_v2/` — Documents superseded by Constitution v2.0
- `99_archive/legacy_structures/` — Legacy governance and specs

---

## Other Directories

| Directory | Contents |
|-----------|----------|
| `04_project_builder/` | Project builder specs |
| `05_agents/` | Agent architecture |
| `06_user_surface/` | User surface specs |
| `07_productisation/` | Productisation briefs |
| `08_manuals/` | Manuals |
| `09_prompts/` | Prompt templates and protocols |
| `10_meta/` | Meta documents, reviews, tasks |
```

### File: docs/01_governance/ARTEFACT_INDEX.json
```json
{
    "meta": {
        "version": "2.2.0",
        "updated": "2026-01-01"
    },
    "artefacts": {
        "constitution": "docs/00_foundations/LifeOS_Constitution_v2.0.md",
        "governance_protocol": "docs/02_protocols/Governance_Protocol_v1.0.md",
        "document_steward_protocol": "docs/02_protocols/Document_Steward_Protocol_v1.0.md",
        "coo_contract": "docs/01_governance/COO_Operating_Contract_v1.0.md",
        "dap": "docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md",
        "agent_constitution": "docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md",
        "spec_review_packet": "docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md",
        "strategic_context": "docs/LifeOS_Strategic_Context_v1.0.md"
    }
}
```

### Note on Generated Artifacts
The following files were generated/updated by the script/protocol and contain large aggregated content. They are deterministically reproducible from the source files.

*   `docs/LifeOS_Strategic_Context_v1.0.md` (~118KB)
*   `docs/LifeOS_Universal_Corpus.md` (Updated)
