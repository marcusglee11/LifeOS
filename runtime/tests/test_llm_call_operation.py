"""
Tests for LLM Call Operation in Orchestration Engine
=====================================================

Tests the llm_call operation handler using mocks (no real OpenCode server needed).
"""

import pytest
from unittest.mock import MagicMock, patch

from runtime.orchestration.engine import (
    Orchestrator,
    StepSpec,
    WorkflowDefinition,
    ExecutionContext,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def orchestrator():
    """Fresh orchestrator instance for each test."""
    return Orchestrator()


@pytest.fixture
def mock_llm_response():
    """Create a mock LLMResponse object."""
    response = MagicMock()
    response.content = "This is the LLM response content"
    response.call_id = "test-uuid-1234"
    response.model_used = "openrouter/anthropic/claude-sonnet-4"
    response.latency_ms = 1500
    response.timestamp = "2026-01-08T12:00:00Z"
    return response


# =============================================================================
# TEST: llm_call stores result in state
# =============================================================================

class TestLLMCallStoresResult:
    """Tests that llm_call properly stores results in state."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_llm_call_stores_result_in_state(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """llm_call should store response content in state under output_key."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        # Create workflow with llm_call step
        workflow = WorkflowDefinition(
            id="test-llm-workflow",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "What is 2+2?",
                        "output_key": "answer",
                    }
                )
            ]
        )

        ctx = ExecutionContext(initial_state={"input": "test"})

        # Execute workflow
        result = orchestrator.run_workflow(workflow, ctx)

        # Verify success
        assert result.success is True
        assert result.failed_step_id is None
        assert result.error_message is None

        # Verify state updated
        assert "answer" in result.final_state
        assert result.final_state["answer"] == "This is the LLM response content"

        # Verify metadata stored
        assert "answer_metadata" in result.final_state
        assert result.final_state["answer_metadata"]["call_id"] == "test-uuid-1234"
        assert result.final_state["answer_metadata"]["latency_ms"] == 1500

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_llm_call_default_output_key(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """llm_call should use 'llm_response' as default output_key."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-default-key",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Hello",
                        # No output_key specified
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is True
        assert "llm_response" in result.final_state
        assert result.final_state["llm_response"] == "This is the LLM response content"


# =============================================================================
# TEST: llm_call with missing prompt fails
# =============================================================================

class TestLLMCallValidation:
    """Tests for llm_call input validation."""

    def test_llm_call_with_missing_prompt_fails(self, orchestrator):
        """llm_call without prompt should fail gracefully."""
        workflow = WorkflowDefinition(
            id="test-missing-prompt",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        # Missing "prompt" field
                        "output_key": "result",
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is False
        assert result.failed_step_id == "step1"
        assert "missing required 'prompt' field" in result.error_message

    def test_llm_call_with_empty_prompt_fails(self, orchestrator):
        """llm_call with empty prompt should fail gracefully."""
        workflow = WorkflowDefinition(
            id="test-empty-prompt",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "",  # Empty prompt
                        "output_key": "result",
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is False
        assert result.failed_step_id == "step1"
        assert "missing required 'prompt' field" in result.error_message


# =============================================================================
# TEST: llm_call with custom output_key
# =============================================================================

class TestLLMCallCustomOutputKey:
    """Tests for custom output_key functionality."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_llm_call_with_custom_output_key(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """llm_call should use custom output_key when specified."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-custom-key",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Generate a name",
                        "output_key": "generated_name",
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is True
        assert "generated_name" in result.final_state
        assert result.final_state["generated_name"] == "This is the LLM response content"
        assert "generated_name_metadata" in result.final_state

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_multiple_llm_calls_different_keys(
        self, mock_client_class, orchestrator
    ):
        """Multiple llm_calls with different keys should all store results."""
        # Create responses with different content
        response1 = MagicMock()
        response1.content = "Response One"
        response1.call_id = "uuid-1"
        response1.model_used = "model-a"
        response1.latency_ms = 100
        response1.timestamp = "2026-01-08T12:00:00Z"

        response2 = MagicMock()
        response2.content = "Response Two"
        response2.call_id = "uuid-2"
        response2.model_used = "model-b"
        response2.latency_ms = 200
        response2.timestamp = "2026-01-08T12:00:01Z"

        mock_client = MagicMock()
        mock_client.call.side_effect = [response1, response2]
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-multiple-calls",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "First prompt",
                        "output_key": "first_result",
                    }
                ),
                StepSpec(
                    id="step2",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Second prompt",
                        "output_key": "second_result",
                    }
                ),
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is True
        assert result.final_state["first_result"] == "Response One"
        assert result.final_state["second_result"] == "Response Two"


# =============================================================================
# TEST: Workflow with mixed operations
# =============================================================================

class TestMixedOperationWorkflows:
    """Tests for workflows combining different operation types."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_workflow_with_mixed_operations(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """Workflow with noop, llm_call, and human steps should work."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-mixed-ops",
            steps=[
                StepSpec(id="prep", kind="runtime", payload={"operation": "noop"}),
                StepSpec(
                    id="llm_step",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Generate content",
                        "output_key": "content",
                    }
                ),
                StepSpec(id="review", kind="human", payload={}),
                StepSpec(id="finalize", kind="runtime", payload={"operation": "noop"}),
            ]
        )

        ctx = ExecutionContext(initial_state={"status": "started"})
        result = orchestrator.run_workflow(workflow, ctx)

        assert result.success is True
        assert len(result.executed_steps) == 4
        assert result.final_state["content"] == "This is the LLM response content"
        assert result.final_state["status"] == "started"  # Original state preserved

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_noop_before_llm_call(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """noop operation should not interfere with subsequent llm_call."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-noop-then-llm",
            steps=[
                StepSpec(id="noop1", kind="runtime", payload={"operation": "noop"}),
                StepSpec(id="noop2", kind="runtime", payload={"operation": "noop"}),
                StepSpec(
                    id="llm_step",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Final prompt",
                        "output_key": "final_output",
                    }
                ),
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is True
        assert len(result.executed_steps) == 3
        assert "final_output" in result.final_state


# =============================================================================
# TEST: Error handling
# =============================================================================

class TestLLMCallErrorHandling:
    """Tests for error handling in llm_call operation."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_llm_call_client_error(self, mock_client_class, orchestrator):
        """llm_call should handle client errors gracefully."""
        from runtime.agents.opencode_client import OpenCodeError

        mock_client = MagicMock()
        mock_client.call.side_effect = OpenCodeError("Connection failed")
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-client-error",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Test prompt",
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is False
        assert result.failed_step_id == "step1"
        assert "llm_call failed" in result.error_message
        assert "Connection failed" in result.error_message

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_llm_call_unexpected_error(self, mock_client_class, orchestrator):
        """llm_call should handle unexpected errors gracefully."""
        mock_client = MagicMock()
        mock_client.call.side_effect = RuntimeError("Unexpected crash")
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-unexpected-error",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Test prompt",
                    }
                )
            ]
        )

        result = orchestrator.run_workflow(workflow, ExecutionContext())

        assert result.success is False
        assert result.failed_step_id == "step1"
        assert "unexpected error" in result.error_message


# =============================================================================
# TEST: Client lifecycle
# =============================================================================

class TestClientLifecycle:
    """Tests for LLM client lifecycle management."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_client_started_only_on_llm_call(self, mock_client_class, orchestrator):
        """Client should only start when llm_call operation is executed."""
        # Workflow with no llm_call
        workflow = WorkflowDefinition(
            id="test-no-llm",
            steps=[
                StepSpec(id="step1", kind="runtime", payload={"operation": "noop"}),
            ]
        )

        orchestrator.run_workflow(workflow, ExecutionContext())

        # Client should never be instantiated for noop-only workflows
        mock_client_class.assert_not_called()

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_client_stopped_after_workflow(
        self, mock_client_class, orchestrator, mock_llm_response
    ):
        """Client should be stopped after workflow completes."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-cleanup",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Test",
                    }
                )
            ]
        )

        orchestrator.run_workflow(workflow, ExecutionContext())

        # Verify stop_server was called
        mock_client.stop_server.assert_called_once()

    @patch("runtime.orchestration.engine.OpenCodeClient")
    def test_client_reused_for_multiple_calls(
        self, mock_client_class, orchestrator
    ):
        """Same client instance should be reused for multiple llm_calls."""
        response = MagicMock()
        response.content = "Response"
        response.call_id = "uuid"
        response.model_used = "model"
        response.latency_ms = 100
        response.timestamp = "2026-01-08T12:00:00Z"

        mock_client = MagicMock()
        mock_client.call.return_value = response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-reuse",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={"operation": "llm_call", "prompt": "P1", "output_key": "r1"}
                ),
                StepSpec(
                    id="step2",
                    kind="runtime",
                    payload={"operation": "llm_call", "prompt": "P2", "output_key": "r2"}
                ),
            ]
        )

        orchestrator.run_workflow(workflow, ExecutionContext())

        # Client should only be created once
        assert mock_client_class.call_count == 1
        # But call() should be invoked twice
        assert mock_client.call.call_count == 2


# =============================================================================
# TEST: Custom model
# =============================================================================

class TestLLMCallCustomModel:
    """Tests for custom model specification."""

    @patch("runtime.orchestration.engine.OpenCodeClient")
    @patch("runtime.orchestration.engine.LLMCall")
    def test_llm_call_with_custom_model(
        self, mock_llm_call_class, mock_client_class, orchestrator, mock_llm_response
    ):
        """llm_call should pass custom model to LLMCall."""
        mock_client = MagicMock()
        mock_client.call.return_value = mock_llm_response
        mock_client_class.return_value = mock_client

        workflow = WorkflowDefinition(
            id="test-custom-model",
            steps=[
                StepSpec(
                    id="step1",
                    kind="runtime",
                    payload={
                        "operation": "llm_call",
                        "prompt": "Test",
                        "model": "openrouter/openai/gpt-4",
                    }
                )
            ]
        )

        orchestrator.run_workflow(workflow, ExecutionContext())

        # Verify LLMCall was created with custom model
        mock_llm_call_class.assert_called_once_with(
            prompt="Test",
            model="openrouter/openai/gpt-4"
        )
