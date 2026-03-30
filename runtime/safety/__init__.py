"""runtime.safety package"""

from .halt import (
    HaltError,
    HaltEvent,
    find_last_good_snapshot,
    halt_on_health_failure,
    halt_runtime,
    log_halt_event,
    rollback_to_snapshot,
)
from .health_checks import (
    HealthStatus,
    check_amu0_chain_integrity,
    check_amu0_readability,
    check_dap_write_health,
    check_index_coherence,
    run_all_health_checks,
)

__all__ = [
    "HealthStatus",
    "check_dap_write_health",
    "check_index_coherence",
    "check_amu0_readability",
    "check_amu0_chain_integrity",
    "run_all_health_checks",
    "HaltEvent",
    "HaltError",
    "halt_runtime",
    "halt_on_health_failure",
    "find_last_good_snapshot",
    "rollback_to_snapshot",
    "log_halt_event",
]
