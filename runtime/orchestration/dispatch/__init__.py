"""
COO Dispatch Engine — Phase 1: Single-flight execution layer.

Provides:
- ExecutionOrder: YAML schema + validation
- DispatchEngine: Order lifecycle management + execution delegation
- RunManifest: Append-only JSONL canonical manifest
- ProviderPool: Health-aware provider routing (Phase 1 stub)
- SupervisorPort, CuratorPort: Protocol interfaces for future COO Agent integration
"""

from runtime.orchestration.dispatch.engine import DispatchEngine, DispatchConfig, DispatchResult
from runtime.orchestration.dispatch.manifest import RunManifest
from runtime.orchestration.dispatch.order import (
    ExecutionOrder,
    StepSpec,
    load_order,
    parse_order,
    OrderValidationError,
)
from runtime.orchestration.dispatch.ports import SupervisorPort, CuratorPort
from runtime.orchestration.dispatch.provider_pool import ProviderPool, ProviderHealth

__all__ = [
    "DispatchEngine",
    "DispatchConfig",
    "DispatchResult",
    "RunManifest",
    "ExecutionOrder",
    "StepSpec",
    "load_order",
    "parse_order",
    "OrderValidationError",
    "SupervisorPort",
    "CuratorPort",
    "ProviderPool",
    "ProviderHealth",
]
