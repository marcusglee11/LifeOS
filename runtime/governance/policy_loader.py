"""
Policy Loader - Deterministic includes resolution and validation.

Implements P0.4 includes resolution rules:
- Order: list order in includes: (stable)
- Duplicates: ERROR (fail-closed)
- Path safety: relative only; reject absolute paths and ..
- Unknown keys: ERROR (fail-closed)
"""

from __future__ import annotations

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import centralized workspace resolution
from runtime.util.workspace import resolve_workspace_root as _util_resolve_workspace_root

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    # P0.3: FAIL-CLOSED on missing jsonschema in authoritative mode
    HAS_JSONSCHEMA = False
    ValidationError = Exception


class PolicyLoadError(Exception):
    """Raised when policy loading fails (fail-closed)."""
    pass


class PolicyLoader:
    """
    Loads and validates policy configuration with includes resolution.
    """
    
    CONFIG_DIR = Path("config/policy")
    SCHEMA_FILE = "policy_schema.json"
    MASTER_FILE = "policy_rules.yaml"
    
    # Known top-level keys in master config (fail-closed on unknown)
    KNOWN_MASTER_KEYS = {
        "schema_version", "includes", "policy_metadata", "posture",
        "variables", "failure_classes", "audit", "metrics", "escalation",
        "tool_rules", "loop_rules", "failure_routing", "budgets",
        "waiver_rules", "progress_detection"
    }
    
    def __init__(self, config_dir: Optional[Path] = None, authoritative: bool = False):
        """Initialize PolicyLoader.
        
        Args:
            config_dir: Optional config directory (defaults to workspace root / config/policy)
            authoritative: If True, fail-closed on missing jsonschema
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # P0.3: Anchor to workspace root instead of cwd-relative
            self.config_dir = self._resolve_workspace_root() / self.CONFIG_DIR
        self._effective_config: Optional[Dict[str, Any]] = None
        self._authoritative = authoritative
    
    def load(self) -> Dict[str, Any]:
        """
        Load and validate the effective config.
        
        Returns:
            Effective config dict (post-includes merge)
            
        Raises:
            PolicyLoadError: On any validation failure (fail-closed)
        """
        # 1. Parse master config
        master_path = self.config_dir / self.MASTER_FILE
        if not master_path.exists():
            raise PolicyLoadError(f"Master config not found: {master_path}")
        
        master = self._parse_yaml(master_path)
        
        # 2. Check for unknown keys (fail-closed)
        unknown_keys = set(master.keys()) - self.KNOWN_MASTER_KEYS
        if unknown_keys:
            raise PolicyLoadError(f"Unknown keys in master config: {unknown_keys}")
        
        # 3. Resolve includes
        includes = master.get("includes", [])
        tool_rules, loop_rules = self._resolve_includes(includes)
        
        # 4. Build effective config
        effective = dict(master)
        effective["tool_rules"] = tool_rules
        effective["loop_rules"] = loop_rules
        
        # Remove includes key from effective (it's resolved now)
        effective.pop("includes", None)
        
        # 5. Validate effective config against schema
        self._validate_schema(effective)
        
        # 6. Semantic validation
        self._validate_semantics(effective)
        
        self._effective_config = effective
        return effective
    
    def _parse_yaml(self, path: Path) -> Any:
        """Parse YAML file with error handling."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PolicyLoadError(f"YAML parse error in {path}: {e}")
        except FileNotFoundError:
            raise PolicyLoadError(f"Config file not found: {path}")
    
    def _resolve_includes(self, includes: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """
        Resolve includes with fail-closed rules.
        
        Returns:
            (tool_rules, loop_rules) lists
        """
        if not includes:
            return [], []
        
        # Check for duplicates
        seen = set()
        for inc in includes:
            if inc in seen:
                raise PolicyLoadError(f"Duplicate include: {inc}")
            seen.add(inc)
        
        tool_rules = []
        loop_rules = []
        
        for inc in includes:
            # Path safety: must be relative, no ..
            if os.path.isabs(inc):
                raise PolicyLoadError(f"Absolute path in includes not allowed: {inc}")
            if ".." in inc:
                raise PolicyLoadError(f"Path traversal in includes not allowed: {inc}")
            
            inc_path = self.config_dir / inc
            if not inc_path.exists():
                raise PolicyLoadError(f"Include file not found: {inc_path}")
            
            data = self._parse_yaml(inc_path)
            
            # Determine which rules this is based on filename
            if "tool" in inc.lower():
                if isinstance(data, list):
                    tool_rules.extend(data)
                else:
                    raise PolicyLoadError(f"tool_rules file must be a list: {inc}")
            elif "loop" in inc.lower():
                if isinstance(data, list):
                    loop_rules.extend(data)
                else:
                    raise PolicyLoadError(f"loop_rules file must be a list: {inc}")
            else:
                raise PolicyLoadError(f"Unknown include type: {inc}")
        
        return tool_rules, loop_rules
    
    def _validate_schema(self, effective: Dict[str, Any]) -> None:
        """Validate effective config against JSON schema."""
        if not HAS_JSONSCHEMA:
            # P0.3: FAIL-CLOSED in authoritative mode
            if self._authoritative:
                raise PolicyLoadError(
                    "jsonschema module required for authoritative policy validation. "
                    "Install via: pip install jsonschema"
                )
            # In non-authoritative mode, skip validation (best-effort)
            return
        
        schema_path = self.config_dir / self.SCHEMA_FILE
        if not schema_path.exists():
            raise PolicyLoadError(f"Schema file not found: {schema_path}")
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            raise PolicyLoadError(f"Schema JSON parse error: {e}")
        
        try:
            validate(instance=effective, schema=schema)
        except ValidationError as e:
            raise PolicyLoadError(f"Schema validation failed: {e.message}")
    
    def _validate_semantics(self, effective: Dict[str, Any]) -> None:
        """
        Semantic validation beyond JSON schema.
        
        Validates:
        - Tool rules use tool decisions only
        - Loop rules use loop decisions only
        - filesystem ALLOW rules have path_scope
        """
        tool_decisions = {"ALLOW", "DENY", "ESCALATE", "WAIVER"}
        loop_decisions = {"RETRY", "TERMINATE", "ESCALATE", "WAIVER"}
        
        # Validate tool rules
        for rule in effective.get("tool_rules", []):
            decision = rule.get("decision", "")
            if decision not in tool_decisions:
                raise PolicyLoadError(
                    f"Invalid tool decision '{decision}' in rule {rule.get('rule_id', '?')}"
                    f" (valid: {tool_decisions})"
                )
            
            # Check filesystem ALLOW requires path_scope
            match = rule.get("match", {})
            if match.get("tool") == "filesystem" and decision == "ALLOW":
                if "path_scope" not in rule:
                    raise PolicyLoadError(
                        f"filesystem ALLOW rule {rule.get('rule_id', '?')} "
                        f"must declare path_scope"
                    )
        
        # Validate loop rules
        for rule in effective.get("loop_rules", []):
            decision = rule.get("decision", "")
            if decision not in loop_decisions:
                raise PolicyLoadError(
                    f"Invalid loop decision '{decision}' in rule {rule.get('rule_id', '?')}"
                    f" (valid: {loop_decisions})"
                )
    
    def _resolve_workspace_root(self) -> Path:
        """Resolve workspace root deterministically.

        Delegates to runtime.util.workspace for single source of truth.

        Returns:
            Workspace root Path
        """
        try:
            return _util_resolve_workspace_root()
        except RuntimeError:
            # Fallback to cwd if utility fails
            return Path.cwd().resolve()
    
    @property
    def effective_config(self) -> Optional[Dict[str, Any]]:
        return self._effective_config


def load_policy_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to load policy config.
    
    Args:
        config_dir: Optional override for config directory
        
    Returns:
        Effective config dict
        
    Raises:
        PolicyLoadError: On any failure (fail-closed)
    """
    loader = PolicyLoader(config_dir)
    return loader.load()
