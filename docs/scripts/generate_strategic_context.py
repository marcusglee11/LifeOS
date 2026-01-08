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
        return "## Test Status\nNot found.\n"
    
    return "\n".join(result_lines)


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
    
    pruned_content = "\n".join(filtered_lines)
    
    # Check if any active tasks remain
    if not TASK_ACTIVE_PATTERN.search(pruned_content):
        return "No active tasks pending.\n"
    
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
            f"\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\n\n"
            "*[Reference Pointer: Raw schema/example omitted for strategic clarity]*\n\n"
        )

    # 3. Protocol Referencing (Specs)
    if SPEC_PACKET_PATTERN.search(filename) and not PROTOCOL_PATTERN.search(filename):
        if "10_meta" not in str(file_path):
            print(f"Placeholding Technical Spec: {filename}")
            return (
                f"\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\n\n"
                "*[Reference Pointer: See full text in Universal Corpus for implementation details]*\n\n"
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
        clean_content = "\n".join(filtered_lines)

    return f"\n# File: {file_path.relative_to(DOCS_DIR).as_posix()}\n\n{clean_content}\n\n"


def main():
    print(f"Generating Strategic Context (v1.3) at {OUTPUT_FILE}...")

    # 1. Dashboard Data
    dash = get_dashboard_data()

    full_content = []

    # Preamble (Dashboard) - Note: No volatile timestamp per deterministic bundle conventions
    dashboard = (
        f"# ⚡ LifeOS Strategic Dashboard\n"
        f"**Current Tier:** {dash['tier']}\n"
        f"**Active Roadmap Phase:** {dash['roadmap']}\n"
        f"**Current Governance Mode:** {dash['mode']}\n"
        f"**Purpose:** High-level strategic reasoning and catch-up context.\n"
        f"**Authority Chain:** Constitution (Supreme) → Governance → Runtime (Mechanical)\n"
        f"\n---\n"
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
            full_content.append("\n---\n")

    # Write
    OUTPUT_FILE.write_text("".join(full_content), encoding='utf-8')
    print(f"Successfully generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
