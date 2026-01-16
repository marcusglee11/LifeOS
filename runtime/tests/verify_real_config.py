
import sys
import os
import unittest

# Add repo root to path
sys.path.insert(0, os.getcwd())

from runtime.agents.models import load_model_config, get_api_key_for_role

class TestRealConfig(unittest.TestCase):
    def test_config_loads_agents(self):
        """Verify that config/models.yaml now successfully loads the agents section."""
        config = load_model_config()
        
        # Check steward config
        self.assertIn("steward", config.agents)
        steward = config.agents["steward"]
        self.assertEqual(steward.api_key_env, "OPENROUTER_STEWARD_KEY")
        self.assertEqual(steward.model, "x-ai/grok-4.1-fast")
        
        # Check builder config
        self.assertIn("builder", config.agents)
        builder = config.agents["builder"]
        self.assertEqual(builder.api_key_env, "OPENROUTER_BUILDER_KEY")
        
        # Check fallback (simple existence check for now as models.py AgentConfig might not fully parse dicts deeply into objs yet)
        self.assertTrue(len(steward.fallback) > 0)
        self.assertEqual(steward.fallback[0]["provider"], "zen")

if __name__ == '__main__':
    unittest.main()
