"""
FP-4.x: Atomic Write Utilities
Provides atomic file write operations using write-temp + rename pattern.
"""
import os
import json
import tempfile
from typing import Any, Union
from pathlib import Path


def atomic_write_text(path: Union[Path, str], text: str, encoding: str = 'utf-8') -> None:
    """
    Atomically write text to a file.
    
    Uses write-temp + fsync + rename pattern to ensure
    the file is either fully written or unchanged.
    
    Args:
        path: Target file path.
        text: Text content to write.
        encoding: Text encoding (default: utf-8).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in same directory for atomic rename
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_write_json(
    path: Union[Path, str],
    data: Any,
    indent: int = 2,
    sort_keys: bool = True
) -> None:
    """
    Atomically write JSON to a file.
    
    Args:
        path: Target file path.
        data: JSON-serializable data.
        indent: JSON indentation (default: 2).
        sort_keys: Sort dictionary keys for determinism (default: True).
    """
    text = json.dumps(data, indent=indent, sort_keys=sort_keys)
    atomic_write_text(path, text)


def atomic_write_bytes(path: Union[Path, str], data: bytes) -> None:
    """
    Atomically write binary data to a file.
    
    Args:
        path: Target file path.
        data: Binary content to write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
