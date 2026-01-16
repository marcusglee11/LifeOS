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
        content_body.append("\n## 🏛️ Priority Governance Artefacts\n")
        
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
    
    content_body.append("\n## 📂 Full Documentation Tree\n")
    
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
