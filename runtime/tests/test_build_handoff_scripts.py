"""
Tests for package_context.py, steward_blocked.py, and check_readiness.py.

Minimal smoke tests per mission requirements.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "docs" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestPackageContext:
    """Tests for package_context.py."""
    
    def test_alias_resolution(self, tmp_path):
        """Test workstream resolution via aliases."""
        # Import after path setup
        import package_context as pkg
        
        # Create temp workstreams.yaml
        workstreams = {
            "mission_registry": {
                "component_human_name": "Mission Registry",
                "status": "CONFIRMED",
                "aliases": ["registry", "mission reg"],
            }
        }
        
        with patch.object(pkg, 'WORKSTREAMS_PATH', tmp_path / "workstreams.yaml"):
            (tmp_path / "workstreams.yaml").write_text(yaml.dump(workstreams))
            
            # Test exact match
            slug = pkg.resolve_component_to_slug("Mission Registry")
            assert slug == "mission_registry"
            
            # Test alias match
            slug = pkg.resolve_component_to_slug("registry")
            assert slug == "mission_registry"
    
    def test_caps_enforcement(self):
        """Test list truncation with caps."""
        import package_context as pkg
        
        items = ["a", "b", "c", "d", "e", "f"]
        truncated = pkg.truncate_list(items, 3)
        assert len(truncated) == 3
        assert truncated[-1] == "[TRUNCATED]"
        
        # No truncation needed
        short = ["a", "b"]
        result = pkg.truncate_list(short, 5)
        assert result == short
    
    def test_packet_shape_architect(self, tmp_path):
        """Test ARCHITECT_CONTEXT_PACKET has required fields."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'STATE_PATH', tmp_path / "LIFEOS_STATE.md"), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"):
            
            # Create minimal state
            (tmp_path / "LIFEOS_STATE.md").write_text("## Current Focus\nTest focus")
            
            packet = pkg.generate_architect_context("test_slug", "Test Component", 0)
            
            # Verify required fields
            assert packet["packet_type"] == "ARCHITECT_CONTEXT_PACKET"
            assert "packet_id" in packet
            assert "component_human_name" in packet
            assert "workstream_slug" in packet
            assert "goal_summary" in packet
            assert "constraints" in packet
            assert "success_criteria" in packet
            assert packet["state_ref"] == "docs/11_admin/LIFEOS_STATE.md"
            assert "caps" in packet


class TestStewardBlocked:
    """Tests for steward_blocked.py."""
    
    def test_grouping_determinism(self, tmp_path):
        """Test that packets are grouped by owner deterministically."""
        import steward_blocked as sb
        
        packets = [
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T00:00:00Z"}, "_source_path": "a.yaml"},
            {"blocked": {"owner": "CEO", "created_at": "2026-01-04T00:00:00Z"}, "_source_path": "b.yaml"},
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T00:00:00Z"}, "_source_path": "c.yaml"},
        ]
        
        groups = sb.group_by_owner(packets)
        
        assert len(groups["Builder"]) == 2
        assert len(groups["CEO"]) == 1
        assert len(groups["Council"]) == 0
    
    def test_age_calculation(self):
        """Test age calculation from created_at."""
        import steward_blocked as sb
        
        # Recent timestamp
        now = datetime.now(timezone.utc)
        created = now.isoformat()
        age = sb.calculate_age_hours(created)
        assert "h" in age
        assert float(age.replace("h", "")) < 1  # Should be very recent
        
        # Unknown
        age = sb.calculate_age_hours(None)
        assert age == "UNKNOWN"


class TestCheckReadiness:
    """Tests for check_readiness.py."""
    
    def test_sha256_hash(self):
        """Test hash computation."""
        import check_readiness as cr
        
        result = cr.sha256_hash("test content")
        assert result.startswith("sha256:")
        assert len(result) > 10
        
        # Same input = same hash
        result2 = cr.sha256_hash("test content")
        assert result == result2
    
    def test_success_path_emits_packet(self, tmp_path):
        """Test that success path emits log + readiness packet."""
        import check_readiness as cr
        
        with patch.object(cr, 'REPO_ROOT', tmp_path), \
             patch.object(cr, 'LOGS_DIR', tmp_path / "logs" / "preflight"), \
             patch.object(cr, 'PACKETS_DIR', tmp_path / "packets" / "readiness"), \
             patch.object(cr, 'CURRENT_DIR', tmp_path / "packets" / "current"), \
             patch.object(cr, 'STATE_PATH', tmp_path / "LIFEOS_STATE.md"):
            
            # Create minimal state
            (tmp_path / "LIFEOS_STATE.md").write_text("## Blockers\nNone")
            
            # Mock pytest success
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "42 passed"
            mock_result.stderr = ""
            
            with patch('subprocess.run', return_value=mock_result):
                test_result = cr.run_pytest("test_component")
            
            assert test_result["exit_code"] == 0
            assert "stdout_hash" in test_result
            assert "log_path" in test_result
            
            # Verify log was written
            log_path = tmp_path / test_result["log_path"]
            assert log_path.exists()
    
    def test_failure_path_emits_packet(self, tmp_path):
        """Test that failure path still emits log + readiness packet."""
        import check_readiness as cr
        
        with patch.object(cr, 'REPO_ROOT', tmp_path), \
             patch.object(cr, 'LOGS_DIR', tmp_path / "logs" / "preflight"):
            
            # Mock pytest failure
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = "3 failed"
            mock_result.stderr = "error details"
            
            with patch('subprocess.run', return_value=mock_result):
                test_result = cr.run_pytest("test_component")
            
            assert test_result["exit_code"] == 1
            assert "stdout_hash" in test_result
            assert "stderr_hash" in test_result
            
            # Log should still be written
            log_path = tmp_path / test_result["log_path"]
            assert log_path.exists()


class TestPackageContextP1:
    """P1 Tests: Council refs, fail-closed, caps."""
    
    def test_council_packet_protected_paths_policy_ref(self, tmp_path):
        """Test council packet includes correct protected_paths_policy_ref."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            # Create minimal prompts dir
            (tmp_path / "prompts").mkdir(parents=True)
            
            packet = pkg.generate_council_context("test", "Test", None)
            
            assert packet["scope_boundaries"]["protected_paths_policy_ref"] == "config/governance/protected_artefacts.json"
    
    def test_council_packet_includes_role_prompts(self, tmp_path):
        """Test council packet includes role prompts when present."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            # Create prompts
            prompts_dir = tmp_path / "prompts"
            prompts_dir.mkdir(parents=True)
            (prompts_dir / "chair_prompt.md").write_text("Chair prompt")
            (prompts_dir / "reviewer_prompt.md").write_text("Reviewer prompt")
            
            packet = pkg.generate_council_context("test", "Test", None)
            
            assert len(packet["required_role_prompts_refs"]) == 2
            # Lexicographic order
            assert "chair_prompt.md" in packet["required_role_prompts_refs"][0]
    
    def test_council_packet_includes_procedure_refs(self, tmp_path):
        """Test council packet includes procedure refs when present."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            # Create minimal structure
            (tmp_path / "prompts").mkdir(parents=True)
            
            # Create procedure doc
            proc_dir = tmp_path / "docs" / "01_governance"
            proc_dir.mkdir(parents=True)
            (proc_dir / "Council_Invocation_Runtime_Binding_Spec_v1.0.md").write_text("Spec")
            
            with patch.object(pkg, 'COUNCIL_PROCEDURE_REFS', ["docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md"]):
                packet = pkg.generate_council_context("test", "Test", None)
            
            assert len(packet["council_procedure_refs"]) >= 1
    
    def test_fail_closed_unknown_component(self, tmp_path):
        """Test that unknown component fails closed without --allow-provisional."""
        import package_context as pkg
        
        with patch.object(pkg, 'WORKSTREAMS_PATH', tmp_path / "workstreams.yaml"), \
             patch.object(pkg, 'PACKETS_BASE', tmp_path / "packets"):
            
            # Create empty workstreams
            (tmp_path / "workstreams.yaml").write_text(yaml.dump({}))
            
            # Should fail closed
            result = pkg.resolve_component_to_slug("Unknown Component", allow_provisional=False)
            assert result is None
            
            # Should emit BLOCKED packet
            blocked_dir = tmp_path / "packets" / "blocked"
            blocked_files = list(blocked_dir.glob("*.yaml")) if blocked_dir.exists() else []
            assert len(blocked_files) == 1
    
    def test_decision_questions_capped(self):
        """Test decision questions list is capped."""
        import package_context as pkg
        
        caps = pkg.CAPS["council"]
        assert caps["decision_questions"] == 5
        
        items = ["q1", "q2", "q3", "q4", "q5", "q6", "q7"]
        truncated = pkg.truncate_list(items, caps["decision_questions"])
        assert len(truncated) == 5
        assert truncated[-1] == "[TRUNCATED]"


class TestProtectedArtefacts:
    """P2 Test: GEMINI.md protection."""
    
    def test_gemini_in_protected_artefacts(self):
        """Test GEMINI.md is included in protected_artefacts.json."""
        import json
        
        config_path = Path(__file__).parent.parent.parent / "config" / "governance" / "protected_artefacts.json"
        assert config_path.exists(), f"protected_artefacts.json not found at {config_path}"
        
        with open(config_path) as f:
            config = json.load(f)
        
        protected = config.get("protected_paths", [])
        assert "GEMINI.md" in protected, "GEMINI.md should be in protected_paths"


class TestStewardBlockedP3:
    """P3 Tests: Deterministic ordering."""
    
    def test_deterministic_ordering_by_created_at(self):
        """Test items are sorted by created_at ascending, UNKNOWN last."""
        import steward_blocked as sb
        
        packets = [
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T10:00:00Z"}, "_source_path": "c.yaml"},
            {"blocked": {"owner": "Builder"}, "_source_path": "b.yaml"},  # No date = UNKNOWN
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T08:00:00Z"}, "_source_path": "a.yaml"},
        ]
        
        # Sort using the key
        sorted_packets = sorted(packets, key=sb.sort_key_for_item)
        
        # First should be earliest date
        assert sorted_packets[0]["_source_path"] == "a.yaml"
        # Second should be later date
        assert sorted_packets[1]["_source_path"] == "c.yaml"
        # Last should be UNKNOWN date
        assert sorted_packets[2]["_source_path"] == "b.yaml"
    
    def test_deterministic_ordering_same_date_by_path(self):
        """Test items with same date are sorted by path."""
        import steward_blocked as sb
        
        packets = [
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T10:00:00Z"}, "_source_path": "z.yaml"},
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T10:00:00Z"}, "_source_path": "a.yaml"},
            {"blocked": {"owner": "Builder", "created_at": "2026-01-04T10:00:00Z"}, "_source_path": "m.yaml"},
        ]
        
        sorted_packets = sorted(packets, key=sb.sort_key_for_item)
        
        assert sorted_packets[0]["_source_path"] == "a.yaml"
        assert sorted_packets[1]["_source_path"] == "m.yaml"
        assert sorted_packets[2]["_source_path"] == "z.yaml"


class TestForwardSlashRefs:
    """P1 Tests: Forward-slash normalization for refs."""
    
    def test_normalize_repo_path(self):
        """Test normalize_repo_path converts backslashes to forward slashes."""
        import package_context as pkg
        
        # Windows-style path
        result = pkg.normalize_repo_path("docs\\09_prompts\\v1.0\\roles\\chair.md")
        assert "\\" not in result
        assert "/" in result
        assert result == "docs/09_prompts/v1.0/roles/chair.md"
        
        # Already forward-slash
        result2 = pkg.normalize_repo_path("docs/scripts/test.py")
        assert result2 == "docs/scripts/test.py"
    
    def test_council_packet_refs_use_forward_slashes(self, tmp_path):
        """Test council packet refs contain forward slashes, not backslashes."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            # Create prompts with subdirs (to test path separators)
            prompts_dir = tmp_path / "prompts"
            prompts_dir.mkdir(parents=True)
            (prompts_dir / "chair_prompt.md").write_text("Chair")
            
            packet = pkg.generate_council_context("test", "Test", None)
            
            # Check all refs for backslashes
            for ref in packet.get("required_role_prompts_refs", []):
                assert "\\" not in ref, f"Backslash found in ref: {ref}"
            for ref in packet.get("council_procedure_refs", []):
                assert "\\" not in ref, f"Backslash found in ref: {ref}"
            assert "\\" not in packet.get("scope_boundaries", {}).get("protected_paths_policy_ref", "")


class TestCT3TriggerDecision:
    """P2 Tests: CT-3 trigger explicit decision."""
    
    def test_council_packet_includes_ct3_trigger(self, tmp_path):
        """Test council packet includes CT-3 trigger for gating scripts."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            (tmp_path / "prompts").mkdir(parents=True)
            
            packet = pkg.generate_council_context("test", "Test", None)
            
            trigger_ids = [t["trigger_id"] for t in packet.get("trigger_reasons", [])]
            
            # CT-2 must be present (governance paths)
            assert "CT-2" in trigger_ids
            # CT-3 must be present (gating scripts)
            assert "CT-3" in trigger_ids
    
    def test_ct3_has_rationale(self, tmp_path):
        """Test CT-3 trigger has explicit rationale."""
        import package_context as pkg
        
        with patch.object(pkg, 'REPO_ROOT', tmp_path), \
             patch.object(pkg, 'REVIEW_PACKETS', tmp_path / "review_packets"), \
             patch.object(pkg, 'COUNCIL_PROMPTS_DIR', tmp_path / "prompts"):
            
            (tmp_path / "prompts").mkdir(parents=True)
            
            packet = pkg.generate_council_context("test", "Test", None)
            
            ct3_triggers = [t for t in packet.get("trigger_reasons", []) if t["trigger_id"] == "CT-3"]
            assert len(ct3_triggers) == 1
            assert "description" in ct3_triggers[0]
            assert len(ct3_triggers[0]["description"]) > 10  # Has meaningful rationale


