import os
from pathlib import Path

def detect_repo_root(start_path: Path | None = None, max_depth: int = 20) -> Path:
    """
    Detect repo root by walking up to find .git directory or file.
    
    Args:
        start_path: Path to start searching from (default: CWD)
        max_depth: Maximum levels to walk up before failing closed
        
    Returns:
        Absolute Path to repo root
        
    Raises:
        RuntimeError: If repo root cannot be found or detection is ambiguous
    """
    current = Path(start_path or os.getcwd()).resolve()
    
    for _ in range(max_depth):
        git_marker = current / ".git"
        if git_marker.exists():
            # Found a marker. Verify it.
            if git_marker.is_dir():
                return current
            elif git_marker.is_file():
                # Potential worktree or submodule
                try:
                    content = git_marker.read_text(encoding="utf-8").strip()
                    if content.startswith("gitdir:"):
                        return current
                except Exception:
                    pass
        
        # Walk up
        parent = current.parent
        if parent == current: # Reached filesystem root
            break
        current = parent
        
    raise RuntimeError(f"Fail-closed: Repo root not found from {start_path or os.getcwd()} (max_depth={max_depth})")

def verify_containment(path: Path, repo_root: Path) -> bool:
    """
    Verify that a path is contained within the repo root (no escape).
    Uses realpath to resolve symlinks before checking.
    """
    try:
        abs_path = Path(os.path.realpath(path))
        abs_root = Path(os.path.realpath(repo_root))
        return abs_root in abs_path.parents or abs_path == abs_root
    except Exception:
        return False
