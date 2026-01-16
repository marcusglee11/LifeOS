
import sys
import os
import unittest

# Add repo root to path
sys.path.insert(0, os.getcwd())

from runtime.agents.models import load_model_config

class TestFullConfigMatrix(unittest.TestCase):
    def test_full_matrix(self):
        """Verify primary and fallback key mappings for all defined roles."""
        config = load_model_config()
        
        roles_to_check = {
            "steward": {
                "primary": "ZEN_STEWARD_KEY",
                "fallback": "OPENROUTER_STEWARD_KEY",
                "fallback_provider": "openrouter"
            },
            "builder": {
                "primary": "ZEN_BUILDER_KEY",
                "fallback": "OPENROUTER_BUILDER_KEY",
                "fallback_provider": "openrouter"
            },
            "designer": {
                "primary": "ZEN_DESIGNER_KEY",
                "fallback": "OPENROUTER_DESIGNER_KEY",
                "fallback_provider": "openrouter"
            },
            "reviewer_architect": {
                "primary": "ZEN_REVIEWER_KEY",
                "fallback": "OPENROUTER_REVIEWER_KEY",
                "fallback_provider": "openrouter"
            }
        }

        print("\n=== Config Matrix Verification ===")
        
        for role, expectation in roles_to_check.items():
            print(f"Checking role: {role}...")
            
            # 1. Check Role Existence
            self.assertIn(role, config.agents, f"Role '{role}' missing from agents config")
            agent = config.agents[role]
            
            # 2. Check Primary Key
            actual_primary = agent.api_key_env
            print(f"  Primary Key Env: {actual_primary}")
            self.assertEqual(actual_primary, expectation["primary"], 
                             f"Role {role} primary key mismatch. Got {actual_primary}, expected {expectation['primary']}")
            
            # 3. Check Zen Provider for Primary
            self.assertEqual(agent.provider, "zen", f"Role {role} primary provider should be zen")

            # 4. Check Fallback Existence
            self.assertTrue(len(agent.fallback) > 0, f"Role {role} has no configured fallback")
            first_fallback = agent.fallback[0]
            
            # 5. Check Fallback Key
            actual_fallback_key = first_fallback.get("api_key_env")
            print(f"  Fallback Key Env: {actual_fallback_key}")
            self.assertEqual(actual_fallback_key, expectation["fallback"],
                             f"Role {role} fallback key mismatch. Got {actual_fallback_key}, expected {expectation['fallback']}")
                             
            # 6. Check Fallback Provider
            actual_fallback_provider = first_fallback.get("provider")
            self.assertEqual(actual_fallback_provider, expectation["fallback_provider"],
                             f"Role {role} fallback provider mismatch")

        print("=== Configuration Verified Successfully ===")

if __name__ == '__main__':
    unittest.main()
