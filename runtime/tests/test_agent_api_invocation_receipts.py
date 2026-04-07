from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from runtime.agents.api import AgentCall, call_agent, call_agent_cli
from runtime.agents.cli_dispatch import CLIDispatchResult, CLIProvider
from runtime.agents.models import AgentConfig, CLIProviderConfig, ModelConfig
from runtime.receipts.invocation_receipt import (
    finalize_run_receipts,
    reset_invocation_receipt_collectors,
)


def _config() -> ModelConfig:
    return ModelConfig(timeout_seconds=1)


def _logger() -> Mock:
    logger = Mock()
    logger.log_call.return_value = None
    return logger


def setup_function() -> None:
    reset_invocation_receipt_collectors()


def teardown_function() -> None:
    reset_invocation_receipt_collectors()


def test_call_agent_records_receipt(tmp_path) -> None:
    class FakeOpenCodeClient:
        def __init__(self, **_: object):
            pass

        def call(self, _: object) -> SimpleNamespace:
            return SimpleNamespace(
                content="verdict: approved\nrationale: ok\n",
                model_used="openai-codex/gpt-5.3-codex",
                usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
                call_id="audit-123",
            )

    call = AgentCall(role="designer", packet={"task_spec": "x"}, model="openai-codex/gpt-5.3-codex")
    with (
        patch("runtime.agents.api._load_role_prompt", return_value=("system", "sha256:prompt")),
        patch("runtime.agents.opencode_client.OpenCodeClient", FakeOpenCodeClient),
    ):
        response = call_agent(
            call,
            run_id="run_receipt_api",
            logger_instance=_logger(),
            config=_config(),
        )

    assert response.packet is not None

    index_path = finalize_run_receipts("run_receipt_api", tmp_path)
    assert index_path is not None
    assert (index_path.parent / "0001_openai-codex.json").exists()

    index = json.loads(index_path.read_text("utf-8"))
    assert index["receipt_count"] == 1
    receipt = index["receipts"][0]
    assert receipt["mode"] == "api"
    assert receipt["provider_id"] == "openai-codex"
    assert receipt["schema_validation"] == "pass"
    assert receipt["token_usage"]["prompt_tokens"] == 11
    assert receipt["token_usage"]["completion_tokens"] == 7
    assert receipt["token_usage"]["total_tokens"] == 18
    assert receipt["token_usage"]["actual_tokens"] == 18
    assert receipt["token_usage"]["token_source"] == "actual"


def test_call_agent_cli_records_receipt(tmp_path) -> None:
    call = AgentCall(role="designer", packet={"task_spec": "x"}, model="gpt-5-mini")

    with (
        patch("runtime.agents.api._load_role_prompt", return_value=("system", "sha256:prompt")),
        patch("runtime.agents.models.is_cli_dispatch", return_value=True),
        patch(
            "runtime.agents.models.get_agent_config",
            return_value=AgentConfig(
                provider="openrouter",
                model="gpt-5-mini",
                endpoint="unused",
                api_key_env="OPENROUTER_API_KEY",
                dispatch_mode="cli",
                cli_provider="codex",
            ),
        ),
        patch(
            "runtime.agents.models.get_cli_provider_config",
            return_value=CLIProviderConfig(
                binary="codex", timeout_seconds=5, sandbox=True, enabled=True
            ),
        ),
        patch(
            "runtime.agents.cli_dispatch.dispatch_cli_agent",
            return_value=CLIDispatchResult(
                output="verdict: approved\n",
                exit_code=0,
                latency_ms=12,
                provider=CLIProvider.CODEX,
                model="gpt-5-mini",
                partial=False,
                errors=[],
            ),
        ),
    ):
        response = call_agent_cli(
            call,
            run_id="run_receipt_cli",
            logger_instance=_logger(),
            config=_config(),
        )

    assert response.packet is not None

    index_path = finalize_run_receipts("run_receipt_cli", tmp_path)
    assert index_path is not None
    assert (index_path.parent / "0001_codex.json").exists()

    index = json.loads(index_path.read_text("utf-8"))
    assert index["receipt_count"] == 1
    receipt = index["receipts"][0]
    assert receipt["mode"] == "cli"
    assert receipt["provider_id"] == "codex"
    assert receipt["schema_validation"] == "pass"
    assert receipt["token_usage"]["total_tokens"] > 0
    assert receipt["token_usage"]["estimated_tokens"] == receipt["token_usage"]["total_tokens"]
    assert receipt["token_usage"]["token_source"] == "estimated"
