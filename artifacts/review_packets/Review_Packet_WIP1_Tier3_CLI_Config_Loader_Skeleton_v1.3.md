# Review Packet: WIP-1 v1.3 — Tier-3 CLI & Config Loader Skeleton

**Mission**: WIP-1 v1.3 — Tier-3 CLI & Config Loader Skeleton  
**Version**: 1.3  
**Date**: 2026-01-11  
**Author**: Antigravity (Builder)  
**Status**: SUBMITTED  

---

## 1. Executive Summary

This mission successfully implemented the minimal Tier-3 "CLI + config loader" skeleton for the `runtime` package. The implementation is fail-closed, deterministic, and supports cross-platform execution via a Python-based evidence capture runner.

**Key Deliverables**:

- Deterministic repo root detection (supporting standard repos and git worktrees).
- YAML configuration loading with Layer 1 structural validation.
- Stable CLI entrypoint via `python -m runtime`.
- Subcommands: `status`, `config validate`, `config show` (canonical JSON).
- Comprehensive pytest suite (14/14 PASS).

---

## 2. Acceptance Criteria Status

| Criteria | Status | Evidence |
|----------|--------|----------|
| Deterministic repo root (dir + file) | PASS | `test_detect_repo_root_*` |
| Global `--config` flag placement | PASS | `test_cli_global_config_placement` |
| YAML config load + Layer 1 validation | PASS | `test_load_config_*` |
| `config show` emits canonical JSON | PASS | `test_cli_canonical_json` |
| python -m runtime entrypoint | PASS | `status`, `config` subcommands working |
| Audit-grade evidence (unabridged) | PASS | `artifacts/evidence/*.log` |

---

## 3. Issue Catalogue

| ID | Severity | Status | Description |
|---|---|---|---|
| I-001 | Low | FIXED | `test_verify_containment_failure` was failing due to `temp_repo` being root of `tmp_path`. Fixed by making `temp_repo` a subdirectory. |
| I-002 | Low | FIXED | Evidence capture script was not fail-closed. Fixed in Patch v1.2. |
| I-003 | Low | FIXED | Reports contained ellipses (`...`) in command fields. Fixed in Fix v1.3. |

---

## 4. Discovery Basis

| Convention | Source | Value |
|------------|--------|-------|
| Package name | `runtime/` dir | `runtime` |
| CLI library | `doc_steward/cli.py` | `argparse` |
| Config format | `config/*.yaml` | `YAML` (PyYAML) |
| Repo marker | `test_run_controller.py` | `.git` |

---

## 5. Non-Goals (Omissions)

- No field-level schema validation (no canonical schema found in repo).
- No new environment variables introduced.
- No destructive operations or mission execution logic.

---

## Appendix A: Evidence Logs

| Log | Command | Path |
|-----|---------|------|
| Pytest | `python -m pytest runtime/tests/test_cli_skeleton.py -vv --tb=long` | [wip1_pytest.log](../../artifacts/evidence/wip1_pytest.log) |
| CLI Status | `python -m runtime --config c:\Users\cabra\Projects\LifeOS\runtime\tests\fixtures\wip1_config.yaml status` | [wip1_cli_status.log](../../artifacts/evidence/wip1_cli_status.log) |
| CLI Validate | `python -m runtime --config c:\Users\cabra\Projects\LifeOS\runtime\tests\fixtures\wip1_config.yaml config validate` | [wip1_cli_config_validate.log](../../artifacts/evidence/wip1_cli_config_validate.log) |
| CLI Show | `python -m runtime --config c:\Users\cabra\Projects\LifeOS\runtime\tests\fixtures\wip1_config.yaml config show` | [wip1_cli_config_show.log](../../artifacts/evidence/wip1_cli_config_show.log) |

---

## Appendix B: Flattened Code

### [runtime/config/repo_root.py](../../runtime/config/repo_root.py)

```python
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
```

### [runtime/config/loader.py](../../runtime/config/loader.py)

```python
import yaml
from pathlib import Path

def load_config(config_path: Path) -> dict:
    """
    Load and structurally validate a YAML config file.
    
    Args:
        config_path: Path to the YAML file
        
    Returns:
        Validated config as dict
        
    Raises:
        ValueError: If file is missing, malformed, or fails structural validation
    """
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in {config_path}: {e}")
    
    # Layer 1 Structural Validation
    if data is None:
        # Empty file is valid but must be returned as dict
        return {}
        
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping (dict), found {type(data).__name__}")
        
    for key in data.keys():
        if not isinstance(key, str):
            raise ValueError(f"Config keys must be strings, found {type(key).__name__}: {key}")
            
    return data
```

### [runtime/config/**init**.py](../../runtime/config/__init__.py)

```python
from .repo_root import detect_repo_root, verify_containment
from .loader import load_config

__all__ = ["detect_repo_root", "verify_containment", "load_config"]
```

### [runtime/**main**.py](../../runtime/__main__.py)

```python
import sys
from runtime.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

### [runtime/cli.py](../../runtime/cli.py)

```python
import argparse
import sys
import json
from pathlib import Path

from runtime.config import detect_repo_root, load_config

def cmd_status(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Print status of repo root, config, and validation."""
    print(f"repo_root: {repo_root}")
    if config_path:
        print(f"config_source: {config_path}")
        print("config_validation: VALID")
    else:
        print("config_source: NONE")
        print("config_validation: N/A")
    return 0

def cmd_config_validate(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Validate the configuration and exit 0/1."""
    if not config_path:
        print("Error: No config file provided. Use --config <path>")
        return 1
    
    # If we reached here, load_config already passed in main()
    print("VALID")
    return 0

def cmd_config_show(args: argparse.Namespace, repo_root: Path, config: dict | None, config_path: Path | None) -> int:
    """Show the configuration in canonical JSON format."""
    if config is None:
        if config_path:
             # This shouldn't happen if main loaded it, but for safety:
             try:
                 config = load_config(config_path)
             except Exception as e:
                 print(f"Error: {e}")
                 return 1
        else:
            print("{}")
            return 0
            
    # Canonical JSON: sort_keys=True, no spaces in separators, no ASCII escape
    output = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(output)
    return 0

def main() -> int:
    # Use a custom parser that handles global options before subcommands
    # This is achieved by defining them on the main parser.
    parser = argparse.ArgumentParser(
        prog="runtime",
        description="LifeOS Runtime Tier-3 CLI Skeleton",
        add_help=True
    )
    
    # Global --config flag
    parser.add_argument("--config", type=Path, help="Path to YAML config file")
    
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    
    # status command
    subparsers.add_parser("status", help="Show runtime status")
    
    # config group
    p_config = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = p_config.add_subparsers(dest="config_command", required=True)
    
    config_subparsers.add_parser("validate", help="Validate config file")
    config_subparsers.add_parser("show", help="Show config in canonical JSON")
    
    # Parse args
    # Note: argparse by default allows flags before subcommands
    args = parser.parse_args()
    
    try:
        # P0.2 & P0.4 - Repo root detection
        repo_root = detect_repo_root()
        
        # Config loading
        config = None
        if args.config:
            config = load_config(args.config)
            
        # Dispatch
        if args.subcommand == "status":
            return cmd_status(args, repo_root, config, args.config)
        
        if args.subcommand == "config":
            if args.config_command == "validate":
                return cmd_config_validate(args, repo_root, config, args.config)
            if args.config_command == "show":
                return cmd_config_show(args, repo_root, config, args.config)
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
```
