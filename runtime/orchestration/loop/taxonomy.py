from enum import Enum, auto

class FailureClass(Enum):
    """
    Classification of failure modes for an attempt.
    Phase A: 6 classes (TEST_FAILURE through UNKNOWN)
    Phase B: 11 classes (added 5 new classes)
    """
    # Phase A classes
    TEST_FAILURE = "test_failure"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"  # e.g. Schema validation failed
    REVIEW_REJECTION = "review_rejection"
    UNKNOWN = "unknown"

    # Phase B additions
    DEPENDENCY_ERROR = "dependency_error"           # Missing deps, import errors
    ENVIRONMENT_ERROR = "environment_error"         # Workspace issues, git conflicts
    TOOL_INVOCATION_ERROR = "tool_invocation_error" # Builder/steward mission failures
    CONFIG_ERROR = "config_error"                   # Invalid config, schema mismatch
    GOVERNANCE_VIOLATION = "governance_violation"   # Protected path, DAP violation

class TerminalOutcome(Enum):
    """
    High-level terminal states for the loop.
    Strictly defined in Phase A Plan v2.2.
    """
    PASS = "PASS"
    WAIVER_REQUESTED = "WAIVER_REQUESTED"          # Explicit CEO waiver required
    ESCALATION_REQUESTED = "ESCALATION_REQUESTED"  # Human decision required
    BLOCKED = "BLOCKED"                            # Fail-closed / determinism failure

class TerminalReason(Enum):
    """
    Specific reasons for entering a terminal state.
    Phase A: 13 reasons (PASS through CRITICAL_FAILURE)
    Phase B: 22 reasons (added 9 new reasons)
    """
    PASS = "pass"

    # Budget / Resource
    BUDGET_EXHAUSTED = "budget_exhausted"
    DIFF_BUDGET_EXCEEDED = "diff_budget_exceeded"
    TOKEN_ACCOUNTING_UNAVAILABLE = "token_accounting_unavailable"

    # Progress / Algorithmic
    NO_PROGRESS = "no_progress"              # hash(N) == hash(N-1) or delta == 0
    OSCILLATION_DETECTED = "oscillation_detected" # hash(N) == hash(N-2)

    # Integrity / Determinism
    LEDGER_CORRUPT = "ledger_corrupt"
    POLICY_CHANGED_MID_RUN = "policy_changed_mid_run"
    HANDOFF_VERSION_MISMATCH = "handoff_version_mismatch"
    WORKSPACE_RESET_UNAVAILABLE = "workspace_reset_unavailable"

    # Other
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded" # Specific to retry policy if not just "budget"
    CRITICAL_FAILURE = "critical_failure" # Generic buckets

    # Phase B additions
    NON_CONVERGENCE = "non_convergence"             # Review rejection retries exhausted
    TIMEOUT_RETRY_LIMIT = "timeout_retry_limit"     # Timeout retries exhausted
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable" # Dependencies can't be resolved
    ENVIRONMENT_ISSUE = "environment_issue"         # Workspace corruption
    GOVERNANCE_ESCALATION = "governance_escalation" # Protected path touched
    WAIVER_APPROVED = "waiver_approved"             # Post-waiver resume (PASS via waiver)
    WAIVER_REJECTED = "waiver_rejected"             # CEO rejected waiver
    PREFLIGHT_CHECKLIST_FAILED = "preflight_checklist_failed"   # PPV failed
    POSTFLIGHT_CHECKLIST_FAILED = "postflight_checklist_failed" # POFV failed
    UNKNOWN_FAILURE = "unknown_failure"             # Unknown failure bucket

class LoopAction(Enum):
    """
    Decision made by the loop policy for the *next* step.
    """
    RETRY = "retry"
    TERMINATE = "terminate"
