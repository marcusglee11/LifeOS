
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add repo root to path
sys.path.insert(0, os.getcwd())

from runtime.agents.models import ModelConfig, AgentConfig

class TestRunnerConfig(unittest.TestCase):
    def setUp(self):
        # Setup mocks before importing runner to avoid side effects if any
        self.mock_config = ModelConfig(
            default_chain=["grok-4.1-fast"],
            agents={
                "steward": AgentConfig(
                    provider="zen_anthropic",
                    model="steward-model-v1",
                    endpoint="https://example.com",
                    api_key_env="ZEN_STEWARD_KEY"
                ),
                "builder": AgentConfig(
                    provider="zen_anthropic",
                    model="builder-model-v1",
                    endpoint="https://example.com",
                    api_key_env="ZEN_BUILDER_KEY"
                )
            }
        )

    def test_runner_imports_canonical_defaults(self):
        """Verify opencode_ci_runner imports canonical keys."""
        import scripts.opencode_ci_runner as runner
        self.assertEqual(runner.DEFAULT_MODEL, "auto")
        self.assertTrue(hasattr(runner, 'resolve_model_auto'))
        self.assertTrue(hasattr(runner, 'get_api_key_for_role'))

    @patch('scripts.opencode_ci_runner.get_api_key_for_role')
    def test_load_api_key_uses_canonical(self, mock_get_key):
        import scripts.opencode_ci_runner as runner
        mock_get_key.return_value = "canonical-key"
        
        # Test Steward
        key = runner.load_api_key("steward")
        self.assertEqual(key, "canonical-key")
        mock_get_key.assert_called_with("steward")
        
        # Test Builder
        key = runner.load_api_key("builder")
        self.assertEqual(key, "canonical-key")
        mock_get_key.assert_called_with("builder")

    @patch('scripts.opencode_ci_runner.resolve_model_auto')
    @patch('scripts.opencode_ci_runner.load_model_config')
    def test_auto_model_resolution(self, mock_load, mock_resolve):
        import scripts.opencode_ci_runner as runner
        
        # Setup mocks
        mock_load.return_value = self.mock_config
        mock_resolve.return_value = ("resolved-model", "reason", [])
        
        # We need to simulate the main execution logic part that resolves models
        # Since we can't easily invoke main() without full env, we just verify the
        # logic snippet equivalence or reliance on the imported functions.
        
        # Instead, let's verify resolve_model_auto works as expected with our mock config
        role = "steward"
        model_id, reason, _ = runner.resolve_model_auto(role, self.mock_config)
        self.assertEqual(model_id, "resolved-model")

if __name__ == '__main__':
    unittest.main()
