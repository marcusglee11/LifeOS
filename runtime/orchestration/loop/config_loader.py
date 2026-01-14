"""
Policy Configuration Loader for Phase B

Loads, validates, and computes canonical hashes for loop policy configuration.
Implements P0.1 (enum key normalization) and P0.2 (canonical hashing).
"""
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .taxonomy import FailureClass, TerminalOutcome, TerminalReason, LoopAction


class PolicyConfigError(Exception):
    """Configuration validation failure"""
    pass


@dataclass
class PolicyConfig:
    """Validated policy configuration with computed hashes"""
    schema_version: str
    policy_metadata: Dict[str, Any]
    budgets: Dict[str, Any]
    failure_routing: Dict[str, Any]
    waiver_rules: Dict[str, Any]
    progress_detection: Dict[str, Any]
    determinism: Dict[str, Any]

    # Hashes for determinism
    policy_hash_canonical: str  # Canonical hash (CRLF/LF-stable) - authoritative for resume
    policy_hash_bytes: str      # Raw bytes hash (forensics)


class PolicyConfigLoader:
    """
    Loads and validates loop policy configuration.

    P0.1: Enforces enum MEMBER NAME keys (fail-closed on value forms)
    P0.2: Computes canonical hash (CRLF/LF-stable, trailing newline normalized)
    """

    REQUIRED_SECTIONS = [
        "schema_version",
        "policy_metadata",
        "budgets",
        "failure_routing",
        "waiver_rules",
        "progress_detection",
        "determinism"
    ]

    REQUIRED_BUDGETS = [
        "max_attempts",
        "max_tokens",
        "max_wall_clock_minutes",
        "max_diff_lines_per_attempt",
        "retry_limits"
    ]

    REQUIRED_POLICY_METADATA = [
        "version",
        "effective_date",
        "author",
        "description"
    ]

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Default to repo_root/config/loop/policy_v1.0.yaml
            # Caller should provide explicit path
            config_path = Path("config/loop/policy_v1.0.yaml")
        self.config_path = config_path

    def load(self) -> PolicyConfig:
        """
        Load, validate, and hash config.

        Returns:
            PolicyConfig with parsed values + canonical and bytes hashes

        Raises:
            PolicyConfigError: If config is missing, invalid, or violates constraints
        """
        if not self.config_path.exists():
            raise PolicyConfigError(f"Config file not found: {self.config_path}")

        # Read raw content for hashing
        with open(self.config_path, 'rb') as f:
            raw_content = f.read()

        # P0.2: Compute canonical hash (CRLF/LF-stable)
        policy_hash_canonical = self._compute_canonical_hash(raw_content)

        # Compute raw bytes hash (forensics)
        policy_hash_bytes = hashlib.sha256(raw_content).hexdigest()

        # Parse YAML (safe_load only allows primitive types)
        with open(self.config_path, 'r', encoding='utf-8') as f:
            try:
                config_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise PolicyConfigError(f"YAML parsing failed: {e}")

        if not isinstance(config_data, dict):
            raise PolicyConfigError(f"Config root must be a dict, got {type(config_data)}")

        # Validate schema
        self._validate_schema(config_data)

        return PolicyConfig(
            schema_version=config_data["schema_version"],
            policy_metadata=config_data["policy_metadata"],
            budgets=config_data["budgets"],
            failure_routing=config_data["failure_routing"],
            waiver_rules=config_data["waiver_rules"],
            progress_detection=config_data["progress_detection"],
            determinism=config_data["determinism"],
            policy_hash_canonical=policy_hash_canonical,
            policy_hash_bytes=policy_hash_bytes
        )

    def _compute_canonical_hash(self, raw_bytes: bytes) -> str:
        """
        Compute SHA256 over normalized content (P0.2):
        1. Decode UTF-8
        2. Replace CRLF with LF
        3. Ensure exactly one trailing newline
        4. Hash normalized bytes

        This ensures identical hashes across Windows/Linux line endings.
        """
        try:
            content = raw_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise PolicyConfigError(f"Config must be UTF-8 encoded: {e}")

        # Normalize line endings (CRLF -> LF)
        content = content.replace('\r\n', '\n')

        # Ensure exactly one trailing newline
        content = content.rstrip('\n') + '\n'

        # Hash normalized bytes
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _validate_schema(self, data: Dict[str, Any]):
        """
        Validate required sections and basic structure.

        Enforces:
        - All REQUIRED_SECTIONS present
        - schema_version == "1.0"
        - All REQUIRED_BUDGETS present
        - All REQUIRED_POLICY_METADATA present
        - Calls specialized validators for routing and waiver rules
        """
        # Check top-level sections
        for section in self.REQUIRED_SECTIONS:
            if section not in data:
                raise PolicyConfigError(f"Missing required section: {section}")

        # Validate schema_version
        if data["schema_version"] != "1.0":
            raise PolicyConfigError(
                f"Unsupported schema version: {data['schema_version']}. "
                f"Expected: 1.0"
            )

        # Validate policy_metadata
        for key in self.REQUIRED_POLICY_METADATA:
            if key not in data["policy_metadata"]:
                raise PolicyConfigError(f"Missing policy_metadata key: {key}")

        # Validate budgets structure
        budgets = data["budgets"]
        for key in self.REQUIRED_BUDGETS:
            if key not in budgets:
                raise PolicyConfigError(f"Missing budget key: {key}")

        # Validate retry_limits are non-negative integers
        if not isinstance(budgets["retry_limits"], dict):
            raise PolicyConfigError("budgets.retry_limits must be a dict")

        for fc, limit in budgets["retry_limits"].items():
            if not isinstance(limit, int):
                raise PolicyConfigError(
                    f"Retry limit for {fc} must be an integer, got {type(limit)}"
                )
            if limit < 0:
                raise PolicyConfigError(
                    f"Retry limit for {fc} must be non-negative, got {limit}"
                )

        # P0.1: Validate failure_routing (enum key normalization + totality)
        self._validate_failure_routing(data["failure_routing"])

        # Validate waiver_rules
        self._validate_waiver_rules(data["waiver_rules"])

        # Validate progress_detection
        self._validate_progress_detection(data["progress_detection"])

        # Validate determinism section
        self._validate_determinism(data["determinism"])

    def _validate_failure_routing(self, routing: Dict[str, Any]):
        """
        P0.1: Validate failure_routing table.

        Enforces:
        1. All keys MUST be FailureClass enum MEMBER NAMES (e.g., TEST_FAILURE)
        2. No value-form keys (e.g., test_failure) allowed
        3. No mixed-case variants allowed
        4. Routing table must be TOTAL (cover ALL failure classes)
        5. Each routing entry has required fields (default_action, terminal_outcome, terminal_reason)
        """
        # Get valid enum MEMBER NAMES (not .value)
        valid_member_names = {fc.name for fc in FailureClass}

        # Check all keys are valid enum member names
        for key in routing.keys():
            if key not in valid_member_names:
                raise PolicyConfigError(
                    f"Invalid failure class key '{key}'. "
                    f"Must use enum MEMBER NAME (e.g., TEST_FAILURE), not value form. "
                    f"Valid keys: {sorted(valid_member_names)}"
                )

        # Totality check: routing table must cover ALL failure classes
        missing = valid_member_names - set(routing.keys())
        if missing:
            raise PolicyConfigError(
                f"Incomplete routing table. Missing entries for: {sorted(missing)}"
            )

        # Validate each routing entry
        for fc, routing_data in routing.items():
            if not isinstance(routing_data, dict):
                raise PolicyConfigError(f"Routing entry for {fc} must be a dict")

            # Validate default_action
            if "default_action" not in routing_data:
                raise PolicyConfigError(f"Missing 'default_action' for {fc}")

            action = routing_data["default_action"]
            if action not in ["RETRY", "TERMINATE"]:
                raise PolicyConfigError(
                    f"Invalid action for {fc}: '{action}'. Must be RETRY or TERMINATE."
                )

            # If TERMINATE, require terminal_outcome and terminal_reason
            if action == "TERMINATE":
                if "terminal_outcome" not in routing_data:
                    raise PolicyConfigError(
                        f"TERMINATE action requires 'terminal_outcome' for {fc}"
                    )
                if "terminal_reason" not in routing_data:
                    raise PolicyConfigError(
                        f"TERMINATE action requires 'terminal_reason' for {fc}"
                    )

                # Validate terminal_outcome is a valid TerminalOutcome enum value
                outcome = routing_data["terminal_outcome"]
                valid_outcomes = [to.name for to in TerminalOutcome]
                if outcome not in valid_outcomes:
                    raise PolicyConfigError(
                        f"Invalid terminal_outcome '{outcome}' for {fc}. "
                        f"Valid: {valid_outcomes}"
                    )

                # Validate terminal_reason is a valid TerminalReason enum value
                reason = routing_data["terminal_reason"]
                valid_reasons = [tr.name for tr in TerminalReason]
                if reason not in valid_reasons:
                    raise PolicyConfigError(
                        f"Invalid terminal_reason '{reason}' for {fc}. "
                        f"Valid: {valid_reasons}"
                    )

    def _validate_waiver_rules(self, waiver_rules: Dict[str, Any]):
        """
        Validate waiver_rules section.

        Enforces:
        - eligible_failure_classes and ineligible_failure_classes present
        - All failure class names are valid enum MEMBER NAMES
        - escalation_triggers is a list
        """
        if "eligible_failure_classes" not in waiver_rules:
            raise PolicyConfigError("waiver_rules missing 'eligible_failure_classes'")

        if "ineligible_failure_classes" not in waiver_rules:
            raise PolicyConfigError("waiver_rules missing 'ineligible_failure_classes'")

        valid_member_names = {fc.name for fc in FailureClass}

        # Validate eligible classes
        for fc in waiver_rules["eligible_failure_classes"]:
            if fc not in valid_member_names:
                raise PolicyConfigError(
                    f"Invalid failure class in eligible_failure_classes: '{fc}'"
                )

        # Validate ineligible classes
        for fc in waiver_rules["ineligible_failure_classes"]:
            if fc not in valid_member_names:
                raise PolicyConfigError(
                    f"Invalid failure class in ineligible_failure_classes: '{fc}'"
                )

        # Validate escalation_triggers (just check it's a list for now)
        if "escalation_triggers" in waiver_rules:
            if not isinstance(waiver_rules["escalation_triggers"], list):
                raise PolicyConfigError("escalation_triggers must be a list")

    def _validate_progress_detection(self, progress: Dict[str, Any]):
        """
        Validate progress_detection section.

        Enforces:
        - Required boolean flags present
        - Lookback values are positive integers
        """
        required_flags = [
            "no_progress_enabled",
            "oscillation_enabled"
        ]

        for flag in required_flags:
            if flag not in progress:
                raise PolicyConfigError(f"Missing progress_detection flag: {flag}")

            if not isinstance(progress[flag], bool):
                raise PolicyConfigError(f"{flag} must be a boolean")

        # Validate lookback values
        if "no_progress_lookback" in progress:
            if not isinstance(progress["no_progress_lookback"], int):
                raise PolicyConfigError("no_progress_lookback must be an integer")
            if progress["no_progress_lookback"] < 1:
                raise PolicyConfigError("no_progress_lookback must be >= 1")

        if "oscillation_lookback" in progress:
            if not isinstance(progress["oscillation_lookback"], int):
                raise PolicyConfigError("oscillation_lookback must be an integer")
            if progress["oscillation_lookback"] < 2:
                raise PolicyConfigError("oscillation_lookback must be >= 2")

    def _validate_determinism(self, determinism: Dict[str, Any]):
        """
        Validate determinism section.

        Enforces:
        - hash_algorithm is "sha256"
        - policy_change_action is valid TerminalOutcome
        - policy_change_reason is valid TerminalReason
        """
        if "hash_algorithm" not in determinism:
            raise PolicyConfigError("Missing determinism.hash_algorithm")

        if determinism["hash_algorithm"] != "sha256":
            raise PolicyConfigError(
                f"Unsupported hash_algorithm: {determinism['hash_algorithm']}. "
                f"Only 'sha256' supported."
            )

        if "policy_change_action" in determinism:
            valid_outcomes = [to.name for to in TerminalOutcome]
            if determinism["policy_change_action"] not in valid_outcomes:
                raise PolicyConfigError(
                    f"Invalid policy_change_action: {determinism['policy_change_action']}"
                )

        if "policy_change_reason" in determinism:
            valid_reasons = [tr.name for tr in TerminalReason]
            if determinism["policy_change_reason"] not in valid_reasons:
                raise PolicyConfigError(
                    f"Invalid policy_change_reason: {determinism['policy_change_reason']}"
                )
