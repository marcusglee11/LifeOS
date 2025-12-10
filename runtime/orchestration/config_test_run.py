"""
Tier-2 Config-Driven Test Run Entrypoint

This module provides the high-level deterministic entrypoint for executing
test runs directly from configuration mappings (e.g. loaded from YAML).

Features:
- Validates and parses config dicts via ConfigAdapter.
- Executes full test run via TestRunAggregator.
- Returns TestRunResult with stable metadata.
- No I/O, network, or subprocess access.
"""
from typing import Any, Mapping

from runtime.orchestration.config_adapter import (
    parse_suite_definition,
    parse_expectations_definition,
    ConfigError,
)
from runtime.orchestration.test_run import (
    TestRunResult,
    run_test_run,
)


def run_test_run_from_config(
    suite_cfg: Mapping[str, Any],
    expectations_cfg: Mapping[str, Any],
) -> TestRunResult:
    """
    Deterministic Tier-2 entrypoint:
    - Parses config mappings into validated Tier-2 dataclasses.
    - Executes full test run via run_test_run.
    - Returns TestRunResult.
    - Raises ConfigError on invalid configs.
    
    Args:
        suite_cfg: Configuration mapping for the scenario suite.
        expectations_cfg: Configuration mapping for expectations.
        
    Returns:
        TestRunResult with aggregated verdict and metadata.
        
    Raises:
        ConfigError: If configuration validation fails.
    """
    # 1. Parse and Validate Inputs
    # The adapter guarantees deterministic ConfigError on failure
    # and ensures no mutation of input mappings.
    suite_def = parse_suite_definition(suite_cfg)
    expectations_def = parse_expectations_definition(expectations_cfg)
    
    # 2. Execute Test Run
    # run_test_run handles execution, expectation evaluation, and
    # result aggregation with stable hashing.
    result = run_test_run(suite_def, expectations_def)
    
    return result
