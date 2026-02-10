from enum import Enum, auto

class FailureClass(Enum):
    """
    Classification of failure modes for an attempt.
    """
    TEST_FAILURE = "test_failure"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    TEST_TIMEOUT = "test_timeout"  # Phase 3a: Test execution exceeded timeout
    VALIDATION_ERROR = "validation_error"  # e.g. Schema validation failed
    REVIEW_REJECTION = "review_rejection"
    LINT_ERROR = "lint_error"
    TEST_FLAKE = "test_flake"
    TYPO = "typo"
    FORMATTING_ERROR = "formatting_error"
    UNKNOWN = "unknown"

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

class LoopAction(Enum):
    """
    Decision made by the loop policy for the *next* step.
    Valid: RETRY, TERMINATE, ESCALATE, WAIVER
    """
    RETRY = "retry"
    TERMINATE = "terminate"
    ESCALATE = "escalate"
    WAIVER = "waiver"

