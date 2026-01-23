"""
Backlog Parser for Recursive Builder Integration (Phase 4 P1)

Parses BACKLOG.md into structured BacklogItem instances with:
- SHA256-based item_key for deterministic identification
- Fail-closed validation on dispatchable items
- Atomic mutation helper for marking done
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Use existing atomic write utility
from runtime.util.atomic_write import atomic_write_text


class BacklogParseError(Exception):
    """Raised when a dispatchable backlog item cannot be parsed."""
    pass


class ItemStatus(str, Enum):
    """Backlog item status mapped from checkbox tokens."""
    TODO = "TODO"           # [ ]
    DONE = "DONE"           # [x]
    INPROGRESS = "INPROGRESS"  # [/]
    BLOCKED = "BLOCKED"     # [!] or explicit


class Priority(str, Enum):
    """Valid priority levels in precedence order."""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


# Priority ordering for sorting
PRIORITY_ORDER = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}


@dataclass(frozen=True)
class BacklogItem:
    """
    A parsed backlog item with deterministic key.
    
    Attributes:
        item_key: SHA256 hash of normalized header line (truncated to 16 chars for display)
        item_key_full: Full SHA256 hash for internal use
        priority: P0/P1/P2/P3
        title: Task title
        dod: Definition of Done
        owner: Task owner
        status: TODO/DONE/INPROGRESS/BLOCKED
        context: Any additional context lines
        line_number: 1-indexed line number in source file
        original_line: Original line text for mutation
    """
    item_key: str
    item_key_full: str
    priority: Priority
    title: str
    dod: str
    owner: str
    status: ItemStatus
    context: str
    line_number: int
    original_line: str
    
    def to_dispatch_payload(self) -> dict:
        """Convert to structured payload for mission dispatch."""
        return {
            "item_key": self.item_key,
            "priority": self.priority.value,
            "title": self.title,
            "dod": self.dod,
            "owner": self.owner,
            "context": self.context,
        }


# Regex pattern for dispatchable backlog items
# Format: - [ ] **Title** — DoD: ... — Owner: ... — Context: ...
# Also supports: - [ ] **Title** — Why Now: ... — Owner: ...
ITEM_PATTERN = re.compile(
    r'^-\s*\[([ xX/!])\]\s*'                   # Checkbox: [ ], [x], [/], [!]
    r'\*\*(.+?)\*\*'                            # Title in bold
    r'(?:\s*[—-]+\s*(?:DoD|Why\s*Now):\s*(.+?))?'  # Optional DoD or Why Now
    r'(?:\s*[—-]+\s*Owner:\s*(\w+))?'          # Optional Owner
    r'(?:\s*[—-]+\s*Context:\s*(.+?))?'        # Optional Context
    r'\s*$',
    re.IGNORECASE
)

# Pattern for section headers to detect priority context
# Matches: ### P0 (Critical), ### P1 (High), etc.
PRIORITY_HEADER_PATTERN = re.compile(
    r'^###\s*(P[0-3])\b',
    re.IGNORECASE
)


def _normalize_line(line: str) -> str:
    """Normalize a line for hashing: strip + single-space collapse."""
    return ' '.join(line.strip().split())


def _compute_item_key(line: str) -> Tuple[str, str]:
    """
    Compute SHA256-based item key from normalized line.
    
    Returns:
        (truncated_key, full_hash)
    """
    normalized = _normalize_line(line)
    full_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    return full_hash[:16], full_hash


def _parse_checkbox_status(char: str) -> ItemStatus:
    """Map checkbox character to ItemStatus."""
    char = char.strip().lower()
    if char == 'x':
        return ItemStatus.DONE
    elif char == '/':
        return ItemStatus.INPROGRESS
    elif char == '!':
        return ItemStatus.BLOCKED
    else:
        return ItemStatus.TODO


def parse_backlog(path: Path) -> List[BacklogItem]:
    """
    Parse BACKLOG.md into structured items.
    
    Args:
        path: Path to backlog file
        
    Returns:
        List of BacklogItem in file order
        
    Raises:
        BacklogParseError: If a dispatchable item is missing required fields
        FileNotFoundError: If backlog file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Backlog file not found: {path}")
    
    content = path.read_text(encoding='utf-8')
    lines = content.splitlines()
    
    items: List[BacklogItem] = []
    seen_keys: dict[str, int] = {}  # key -> line_number for collision detection
    current_priority: Optional[Priority] = None
    
    for line_num, line in enumerate(lines, start=1):
        # Check for priority section header (### P0/P1/P2/P3)
        header_match = PRIORITY_HEADER_PATTERN.match(line)
        if header_match:
            priority_str = header_match.group(1).upper()
            try:
                current_priority = Priority(priority_str)
            except ValueError:
                current_priority = None
            continue
        
        # Reset priority on ## section headers (e.g., "## Next", "## Later")
        # This prevents items under non-priority sections from inheriting stale priority
        if line.startswith('## ') and not line.startswith('### '):
            current_priority = None
            continue
        
        # Check for dispatchable item
        item_match = ITEM_PATTERN.match(line)
        if not item_match:
            continue
        
        checkbox_char = item_match.group(1)
        title = item_match.group(2).strip() if item_match.group(2) else ""
        dod = item_match.group(3).strip() if item_match.group(3) else ""
        owner = item_match.group(4).strip() if item_match.group(4) else ""
        context = item_match.group(5).strip() if item_match.group(5) else ""
        
        status = _parse_checkbox_status(checkbox_char)
        
        # Use section priority or default to P3
        priority = current_priority if current_priority else Priority.P3
        
        # Fail-closed: ONLY P0/P1 TODO items (dispatchable) MUST have required fields
        # P2/P3 and items outside priority sections can have incomplete fields
        is_dispatchable = status == ItemStatus.TODO and priority in (Priority.P0, Priority.P1)
        
        if is_dispatchable:
            missing = []
            if not title:
                missing.append("title")
            if not dod:
                missing.append("DoD")
            if not owner:
                missing.append("Owner")
            
            if missing:
                raise BacklogParseError(
                    f"Line {line_num}: Dispatchable item missing required fields: {', '.join(missing)}\n"
                    f"Line content: {line}"
                )
        
        # Compute item key
        item_key, item_key_full = _compute_item_key(line)
        
        # Collision detection
        if item_key_full in seen_keys:
            raise BacklogParseError(
                f"Line {line_num}: Duplicate item key collision with line {seen_keys[item_key_full]}\n"
                f"Line content: {line}"
            )
        seen_keys[item_key_full] = line_num
        
        items.append(BacklogItem(
            item_key=item_key,
            item_key_full=item_key_full,
            priority=priority,
            title=title,
            dod=dod,
            owner=owner,
            status=status,
            context=context,
            line_number=line_num,
            original_line=line,
        ))
    
    return items


def select_eligible_item(items: List[BacklogItem]) -> Optional[BacklogItem]:
    """
    Select first eligible item for dispatch.
    
    Eligibility:
    - Status is TODO
    - Priority is P0 or P1
    
    Ordering:
    - Priority (P0 before P1)
    - Then file order (line number)
    - Then item_key (for determinism)
    
    Returns:
        First eligible item or None
    """
    eligible = [
        item for item in items
        if item.status == ItemStatus.TODO and item.priority in (Priority.P0, Priority.P1)
    ]
    
    if not eligible:
        return None
    
    # Sort by priority, then line number, then key
    eligible.sort(key=lambda x: (PRIORITY_ORDER[x.priority], x.line_number, x.item_key))
    
    return eligible[0]


def mark_item_done(
    path: Path,
    item: BacklogItem,
    expected_original: Optional[str] = None
) -> None:
    """
    Atomically mark a backlog item as DONE.
    
    Args:
        path: Path to backlog file
        item: Item to mark done
        expected_original: Optional expected original line for guard check
        
    Raises:
        BacklogParseError: If item not found or file changed unexpectedly
    """
    content = path.read_text(encoding='utf-8')
    lines = content.splitlines(keepends=True)
    
    # Find the target line (0-indexed)
    target_idx = item.line_number - 1
    
    if target_idx >= len(lines):
        raise BacklogParseError(
            f"Line {item.line_number} not found in file (file has {len(lines)} lines)"
        )
    
    current_line = lines[target_idx].rstrip('\n\r')
    
    # Guard: verify original line matches
    if expected_original is not None:
        if current_line != expected_original:
            raise BacklogParseError(
                f"File changed unexpectedly at line {item.line_number}.\n"
                f"Expected: {expected_original}\n"
                f"Found: {current_line}"
            )
    else:
        # Use item's stored original line
        if current_line != item.original_line:
            raise BacklogParseError(
                f"File changed unexpectedly at line {item.line_number}.\n"
                f"Expected: {item.original_line}\n"
                f"Found: {current_line}"
            )
    
    # Replace checkbox [ ] with [x]
    new_line = re.sub(r'\[\s*\]', '[x]', current_line, count=1)
    
    # Preserve original line ending
    original_ending = lines[target_idx][len(current_line):] if len(lines[target_idx]) > len(current_line) else '\n'
    lines[target_idx] = new_line + original_ending
    
    # Atomic write
    new_content = ''.join(lines)
    atomic_write_text(path, new_content)
