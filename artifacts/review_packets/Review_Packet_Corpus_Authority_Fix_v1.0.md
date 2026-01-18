# Review Packet: Corpus Authority Logic v1.0

**Mission**: Enforce authority-based document ordering in corpus generation.
**Author**: Antigravity (Agent)
**Date**: 2026-01-04

## 1. Summary
Modified corpus generation scripts (`generate_strategic_context.py` and `generate_corpus.py`) to enforce a strict Authority Chain order for governance documents. This ensures that the **Constitution** and **Governance Protocols** always appear before other documents, correcting the previous alphabetical sorting that led to LLM weight issues.

## 2. Changes
- **`generate_strategic_context.py`**: Added `PRIORITY_ORDER` list and sorting logic.
- **`generate_corpus.py`**: Added `AUTHORITY_ORDER` list and enforced it when processing the Governance Index.
- **Stewardship**: Updated `docs/INDEX.md` timestamp and regenerated both corpuses.

## 3. Impact
- **AI Context**: Agents and NotebookLM will now encounter the authoritative rules *first*, reducing the risk of overweighting lower-priority documents (like "North Star" architectures).
- **Determinism**: The order is now explicitly defined for key files, rather than relying on filesystem or alphabetical sorting.

## 4. Verification
- **Automated**: Regenerated corpuses.
- **Inspection**: Verified `LifeOS_Strategic_Corpus.md` and `LifeOS_Universal_Corpus.md` headers confirm `LifeOS_Constitution_v2.0.md` is the first included file.

---

## Appendix: Flattened Code Snapshots

### File: `docs/scripts/generate_strategic_context.py`
```python
"""
Strategic Context Generator v1.3

Generates a condensed strategic context document from LifeOS canonical docs.

Deterministic behaviour:
- No wall-clock in outputs except explicit timestamp input
- Stable across platforms (newline handling, encoding)
- Version-aware file selection
"""
import re
import datetime
from pathlib import Path
from typing import Tuple, Optional


# Configuration
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = ROOT_DIR / "docs"
OUTPUT_FILE = DOCS_DIR / "LifeOS_Strategic_Corpus.md"

INCLUDE_DIRS = [
    DOCS_DIR / "00_foundations",
    DOCS_DIR / "01_governance",
    DOCS_DIR / "02_protocols",
    DOCS_DIR / "09_prompts",
]

# Patterns
SUPERSEDED_PATTERN = re.compile(r'(?:\*\*Status\*\*|Status):\s*Superseded', re.IGNORECASE)
TASK_DONE_PATTERN = re.compile(r'^\s*[-*]\s*\[x\]', re.IGNORECASE | re.MULTILINE)
TASK_ACTIVE_PATTERN = re.compile(r'^\s*[-*]\s*\[\s\]', re.MULTILINE)
SPEC_PACKET_PATTERN = re.compile(r'(_Spec_|_Packet_)', re.IGNORECASE)
PROTOCOL_PATTERN = re.compile(r'_Protocol_v', re.IGNORECASE)
YAML_SCHEMA_PATTERN = re.compile(r'(example_.*\.yaml|lifeos_packet_schemas.*\.yaml)', re.IGNORECASE)

# Version extraction pattern: _vX.Y or _vX.Y.Z
VERSION_PATTERN = re.compile(r'_v(\d+)\.(\d+)(?:\.(\d+))?', re.IGNORECASE)


def parse_version(filename: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract semantic version from filename.
    
    Returns (major, minor, patch) tuple or None if no version found.
    Patch defaults to 0 if not specified.
    """
    match = VERSION_PATTERN.search(filename)
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) else 0
    return (major, minor, patch)


def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    """
    Get the latest file matching pattern, using version-aware sorting.
    
    Priority:
    1. Highest semantic version (if version tokens exist)
    2. Fallback: Most recently modified file
    """
    files = list(directory.glob(pattern))
    if not files:
        return None
    
    # Partition into versioned and unversioned
    versioned = []
    unversioned = []
    for f in files:
        ver = parse_version(f.name)
        if ver:
            versioned.append((ver, f))
        else:
            unversioned.append(f)
    
    # Prefer highest version
    if versioned:
        versioned.sort(key=lambda x: x[0], reverse=True)
        return versioned[0][1]
    
    # Fallback: most recently modified
    unversioned.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return unversioned[0] if unversioned else None


def get_test_status_section(content: str) -> str:
    """
    Extract only the '## Test Status' section from content.
    
    Stops at the next ## header (sibling section).
    Returns deterministic fallback if section not found.
    """
    lines = content.splitlines()
    result_lines = []
    in_section = False
    
    for line in lines:
        # Check for Test Status header (case-insensitive)
        if re.match(r'^##\s*Test\s+Status\s*$', line, re.IGNORECASE):
            in_section = True
            result_lines.append(line)
            continue
        
        if in_section:
            # Stop at next sibling header (## followed by text, not our header)
            if re.match(r'^##\s+\S', line) and not re.match(r'^##\s*Test\s+Status\s*$', line, re.IGNORECASE):
                break
            result_lines.append(line)
    
    if not result_lines:
        return "## Test Status\\nNot found.\\n"
    
    return "\\n".join(result_lines)


def prune_tasks_content(content: str) -> str:
    """
    Prune completed tasks and detect if any active tasks remain.
    
    Returns pruned content or 'No active tasks pending.' message.
    """
    lines = content.splitlines()
    filtered_lines = []
    
    for line in lines:
        # Skip completed tasks
        if TASK_DONE_PATTERN.match(line):
            continue
        filtered_lines.append(line)
    
    pruned_content = "\\n".join(filtered_lines)
    
    # Check if any active tasks remain
    if not TASK_ACTIVE_PATTERN.search(pruned_content):
        return "No active tasks pending.\\n"
    
    return pruned_content


def get_dashboard_data() -> dict:
    """Extract dashboard data from canonical sources."""
    data = {"tier": "Unknown", "roadmap": "Unknown", "mode": "Unknown"}
    
    gov_dir = DOCS_DIR / "01_governance"
    
    # 1. Tier from Activation Ruling
    if gov_dir.exists():
        ruling = get_latest_file(gov_dir, "*Activation_Ruling*.md")
        if ruling:
            try:
                content = ruling.read_text(encoding='utf-8')
                first_line = content.splitlines()[0] if content.splitlines() else ""
                if "Tier-2.5" in first_line:
                    data["tier"] = "Tier-2.5 (Activated)"
                elif "Tier-2" in first_line:
                    data["tier"] = "Tier-2 (Activated)"
                elif re.search(r'Tier-[\d.]+', first_line):
                    data["tier"] = first_line.strip('# ').strip()
                else:
                    data["tier"] = ruling.stem
            except (OSError, UnicodeDecodeError):
                data["tier"] = "Extraction failed"

    # 2. Roadmap Phase
    runtime_dir = DOCS_DIR / "03_runtime"
    if runtime_dir.exists():
        roadmap = get_latest_file(runtime_dir, "*Roadmap_CoreFuelPlumbing*.md")
        if roadmap:
            data["roadmap"] = "Core / Fuel / Plumbing (See Roadmap)"

    # 3. Governance Mode
    if gov_dir.exists():
        contract = get_latest_file(gov_dir, "COO_Operating_Contract*.md")
        if contract:
            data["mode"] = "Phase 2 — Operational Autonomy (Target State)"

    return data


def process_file(file_path: Path) -> str:
    """Process a single file and return formatted content."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as e:
        print(f"Skipping {file_path}: {e}")
        return ""

    filename = file_path.name

    # 1. Superseded Check
    if SUPERSEDED_PATTERN.search(content):
        return ""

    # 2. Protocol Noise Reduction (YAML Schemas / Examples)
    if YAML_SCHEMA_PATTERN.match(filename):
        print(f"Pruning Noise: {filename}")
        return (
            f"\\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\\n\\n"
            "*[Reference Pointer: Raw schema/example omitted for strategic clarity]*\\n\\n"
        )

    # 3. Protocol Referencing (Specs)
    if SPEC_PACKET_PATTERN.search(filename) and not PROTOCOL_PATTERN.search(filename):
        if "10_meta" not in str(file_path):
            print(f"Placeholding Technical Spec: {filename}")
            return (
                f"\\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\\n\\n"
                "*[Reference Pointer: See full text in Universal Corpus for implementation details]*\\n\\n"
            )

    # 4. Filter Logic
    clean_content = content

    # Logic for CODE_REVIEW_STATUS (Strict Section Extraction)
    if "CODE_REVIEW" in filename:
        print(f"Pruning Code Review (Strict): {filename}")
        clean_content = get_test_status_section(content)

    # Logic for TASKS
    elif "TASKS" in filename:
        print(f"Pruning Tasks: {filename}")
        clean_content = prune_tasks_content(content)

    # General: prune completed tasks from any file
    else:
        lines = content.splitlines()
        filtered_lines = [line for line in lines if not TASK_DONE_PATTERN.match(line)]
        clean_content = "\\n".join(filtered_lines)

    return f"\\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\\n\\n{clean_content}\\n\\n"


def main():
    print(f"Generating Strategic Context (v1.3) at {OUTPUT_FILE}...")

    # 1. Dashboard Data
    dash = get_dashboard_data()

    full_content = []

    # Preamble (Dashboard)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    dashboard = (
        f"# ⚡ LifeOS Strategic Dashboard\\n"
        f"**Generated:** {timestamp}\\n"
        f"**Current Tier:** {dash['tier']}\\n"
        f"**Active Roadmap Phase:** {dash['roadmap']}\\n"
        f"**Current Governance Mode:** {dash['mode']}\\n"
        f"**Purpose:** High-level strategic reasoning and catch-up context.\\n"
        f"**Authority Chain:** Constitution (Supreme) → Governance → Runtime (Mechanical)\\n"
        f"\\n---\\n"
    )
    full_content.append(dashboard)

    # Collect files
    files_to_process = []

    for d in INCLUDE_DIRS:
        if not d.exists():
            continue
        for file_path in sorted(d.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in ['.md', '.txt', '.yaml']:
                files_to_process.append(file_path)

    runtime_dir = DOCS_DIR / "03_runtime"
    if runtime_dir.exists():
        roadmap = get_latest_file(runtime_dir, "*Roadmap*")
        if roadmap:
            files_to_process.append(roadmap)

    meta_dir = DOCS_DIR / "10_meta"
    if meta_dir.exists():
        tasks = get_latest_file(meta_dir, "TASKS*")
        if tasks:
            files_to_process.append(tasks)
        status_file = get_latest_file(meta_dir, "*Status*")
        if status_file and status_file != tasks:
            files_to_process.append(status_file)

    # Deduplicate
    files_to_process = list(dict.fromkeys(files_to_process))
    
    # Sort with Priority
    PRIORITY_ORDER = [
        "LifeOS_Constitution",
        "Governance_Protocol",
        "COO_Operating_Contract",
        "AgentConstitution_GEMINI_Template",
    ]

    def get_sort_key(path: Path) -> tuple:
        name = path.name
        # Check priority list (partial match)
        for i, key in enumerate(PRIORITY_ORDER):
            if key in name:
                return (0, i) # (Group 0 = Priority, Index = Specific Rank)
        
        # Default: content type groups (Governance > Protocol > Others)
        rel_str = str(path.relative_to(DOCS_DIR))
        if "00_foundations" in rel_str:
            return (1, rel_str)
        if "01_governance" in rel_str:
            return (2, rel_str)
        if "02_protocols" in rel_str:
            return (3, rel_str)
            
        return (99, rel_str)

    files_to_process.sort(key=get_sort_key)

    # Process
    for fp in files_to_process:
        chunk = process_file(fp)
        if chunk:
            full_content.append(chunk)
            full_content.append("\\n---\\n")

    # Write
    OUTPUT_FILE.write_text("".join(full_content), encoding='utf-8')
    print(f"Successfully generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
```

### File: `docs/scripts/generate_corpus.py`
```python
#!/usr/bin/env python3
"""
LifeOS Universal Corpus Generator
=================================
Aggregates all canonical documentation into a single Markdown file for:
1. NotebookLM consumption (via Google Drive sync)
2. AI Agent Onboarding (Single Source of Truth)
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

# --- Configuration ---
# Script is in docs/scripts/
DOCS_DIR = Path(__file__).parent.parent.resolve()
ROOT_DIR = DOCS_DIR.parent
OUTPUT_FILE = DOCS_DIR / "LifeOS_Universal_Corpus.md"
GOVERNANCE_INDEX = DOCS_DIR / "01_governance" / "ARTEFACT_INDEX.json"

# Directories to exclude from the corpus
EXCLUDE_DIRS = {
    ".git",
    ".github",
    "99_archive",
    "internal",
    ".pending_root_files",
    "tools",
    "scripts",
    "node_modules",
    "__pycache__"
}

# --- Templates ---
PREAMBLE_TEMPLATE = """# LifeOS Universal Corpus
**Generated**: {timestamp}
**Steward**: Antigravity (Automated)
**Version**: {git_hash}

---

## 📋 Table of Changes (Last 5 Commits)
{changelog}

---

## 🤖 AI Onboarding Protocol
**To any AI Agent reading this:**
1.  **Identity**: This is LifeOS, a personal operating system.
2.  **Authority**: The `00_foundations/LifeOS_Constitution_v2.0.md` is SUPREME.
3.  **Governance**: All changes follow `01_governance/Governance_Protocol_v1.0.md`.
4.  **Structure**:
    -   `00_foundations`: Core axioms (Constitution, Architecture).
    -   `01_governance`: How we decide and work (Stewardship, Council).
    -   `03_runtime`: How the system runs (Specs, implementation).
5.  **Constraint**: Do not hallucinate files not present in this corpus.

---

## 🔎 Table of Contents
{toc}

---

# 📚 Canonical Documentation
"""

TOC_ITEM_TEMPLATE = "- [{name}](#file-{anchor})"
FILE_DELIMITER = """
<hr>

<a id="file-{anchor}"></a>
# 📄 FILE: {rel_path}
**Source**: `{rel_path}`

"""

def make_anchor(path_str):
    """Creates a URL-safe anchor from a path."""
    return path_str.lower().replace("/", "-").replace(".", "-").replace("_", "-").replace(" ", "-")

# --- Helpers ---

def get_git_info():
    """Retrieves current abbreviated hash and last 5 commit logs."""
    try:
        # Get current hash
        current_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            cwd=DOCS_DIR, text=True
        ).strip()
        
        # Get log
        log = subprocess.check_output(
            ["git", "log", "-n", "5", "--pretty=format:- `%h` %cd: **%s**", "--date=short", "."],
            cwd=DOCS_DIR, text=True
        )
        return current_hash, log
    except subprocess.CalledProcessError:
        return "UNKNOWN", "- No git history found."

def load_governance_index():
    """Loads the governance artefact index to ensure priority."""
    if not GOVERNANCE_INDEX.exists():
        return {}
    try:
        with open(GOVERNANCE_INDEX, "r", encoding="utf-8") as f:
            return json.load(f).get("artefacts", {})
    except Exception as e:
        print(f"Warning: Failed to load governance index: {e}")
        return {}

def is_valid_file(path: Path):
    """Checks if a file should be included in the corpus."""
    if path.suffix != ".md":
        return False
    if path.name == "LifeOS_Universal_Corpus.md":
        return False
    
    # Check parents for exclusion
    for parent in path.parents:
        if parent.name in EXCLUDE_DIRS:
            return False
            
    return True

# --- Main ---

def main():
    print(f"Generating Universal Corpus at: {OUTPUT_FILE}")
    
    # 1. Gather Metadata
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    git_hash, changelog = get_git_info()
    
    # 2. Prepare Buffers
    toc_lines = []
    content_body = []
    
    # 3. Collect Files
    # We want a deterministic order: 
    #   1. Governance files (from index)
    #   2. All other files (sorted alphabetically)
    
    gov_files = set()
    gov_index = load_governance_index()
    
    # Priority Order for Governance Artefacts (Authority Chain)
    AUTHORITY_ORDER = [
        "constitution",         # 1. Supreme Law
        "governance_protocol",  # 2. How we change law
        "coo_contract",         # 3. How we operate
        "agent_constitution",   # 4. How workers behave
        "document_steward_protocol", # 5. How we manage docs
        "dap",                  # 6. How we manage artefacts
        "spec_review_packet",   # 7. How we spec changes
        "strategic_context"     # 8. Comparison baseline
    ]

    # Process Governance Index first (Enforcing Authority Order)
    if gov_index:
        content_body.append("\\n## 🏛️ Priority Governance Artefacts\\n")
        
        # Create ordered list of keys: Authority Order first, then any remainders sorted alphabetically
        ordered_keys = [k for k in AUTHORITY_ORDER if k in gov_index]
        remaining_keys = sorted([k for k in gov_index.keys() if k not in AUTHORITY_ORDER])
        final_keys = ordered_keys + remaining_keys

        for key in final_keys:
            rel_path_str = gov_index[key]
            full_path = ROOT_DIR / rel_path_str
            
            if full_path.exists() and is_valid_file(full_path):
                gov_files.add(full_path.resolve())
                anchor = make_anchor(rel_path_str)
                
                # Add to TOC
                toc_lines.append(TOC_ITEM_TEMPLATE.format(name=rel_path_str, anchor=anchor))
                
                # Add content
                with open(full_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                    content_body.append(FILE_DELIMITER.format(rel_path=rel_path_str, anchor=anchor))
                    content_body.append(file_content)
    
    # Process Directories Separately for clean ordering
    
    content_body.append("\\n## 📂 Full Documentation Tree\\n")
    
    all_files = sorted(DOCS_DIR.rglob("*.md"))
    
    for file_path in all_files:
        file_path = file_path.resolve()
        
        # Skip if already added via governance index
        if file_path in gov_files:
            continue
            
        if not is_valid_file(file_path):
            continue
            
        # Helper to get path relative to ROOT_DIR (e.g. "docs/foo.md")
        try:
            rel_path = file_path.relative_to(ROOT_DIR).as_posix()
        except ValueError:
             # Fallback if somehow outside root
            rel_path = file_path.name

        anchor = make_anchor(rel_path)
        
        # Add to TOC
        toc_lines.append(TOC_ITEM_TEMPLATE.format(name=rel_path, anchor=anchor))

        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
            content_body.append(FILE_DELIMITER.format(rel_path=rel_path, anchor=anchor))
            content_body.append(file_content)

    # 4. Assemble Final Content
    final_content = PREAMBLE_TEMPLATE.format(
        timestamp=timestamp,
        git_hash=git_hash,
        changelog=changelog,
        toc="\\n".join(toc_lines)
    ) + "".join(content_body)

    # 5. Write Output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Done.")

if __name__ == "__main__":
    main()
```
