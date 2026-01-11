"""
Tests for backlog synthesizer.

Per Mission Synthesis Engine MVP - P1.3
"""
import pytest
from pathlib import Path
from textwrap import dedent

from runtime.backlog.synthesizer import (
    synthesize_mission,
    MissionPacket,
    SynthesisError,
)


@pytest.fixture
def repo_with_docs(tmp_path):
    """Create a mock repo with full structure."""
    # Docs
    (tmp_path / "docs" / "11_admin").mkdir(parents=True)
    (tmp_path / "docs" / "11_admin" / "LIFEOS_STATE.md").write_text("# State")
    (tmp_path / "docs" / "03_runtime").mkdir(parents=True)
    (tmp_path / "docs" / "03_runtime" / "LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md").write_text("# Arch")
    (tmp_path / "GEMINI.md").write_text("# Constitution")
    
    # Config
    (tmp_path / "config").mkdir()
    
    return tmp_path


@pytest.fixture
def valid_backlog(repo_with_docs):
    """Create a valid backlog file."""
    content = dedent("""
        schema_version: "1.0"
        tasks:
          - id: "TASK-001"
            description: "Update documentation"
            priority: P1
            context_hints:
              - "docs/11_admin/LIFEOS_STATE.md"
    """).strip()
    backlog_path = repo_with_docs / "config" / "backlog.yaml"
    backlog_path.write_text(content, encoding="utf-8")
    return backlog_path


class TestSynthesizeMission:
    """Tests for synthesize_mission function."""
    
    def test_synthesize_valid_task(self, repo_with_docs, valid_backlog):
        """Valid task synthesizes to MissionPacket."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        assert isinstance(packet, MissionPacket)
        assert packet.task_id == "TASK-001"
        assert packet.task_description == "Update documentation"
        assert packet.priority == "P1"
    
    def test_packet_id_deterministic(self, repo_with_docs, valid_backlog):
        """Same inputs produce same packet ID."""
        packet1 = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        packet2 = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        assert packet1.packet_id == packet2.packet_id
    
    def test_context_refs_populated(self, repo_with_docs, valid_backlog):
        """Context refs include resolved hints + baseline."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        assert "docs/11_admin/LIFEOS_STATE.md" in packet.context_refs
        # Baseline also included
        assert "GEMINI.md" in packet.context_refs
    
    def test_default_mission_type(self, repo_with_docs, valid_backlog):
        """Default mission type is steward."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        assert packet.mission_type == "steward"
    
    def test_custom_mission_type(self, repo_with_docs, valid_backlog):
        """Custom mission type respected."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
            mission_type="design",
        )
        assert packet.mission_type == "design"
    
    def test_constraints_included(self, repo_with_docs):
        """Constraints from task included in packet."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "TASK-002"
                description: "Task with constraints"
                priority: P0
                constraints:
                  - "Must be fast"
                  - "No breaking changes"
        """).strip()
        backlog_path = repo_with_docs / "config" / "backlog.yaml"
        backlog_path.write_text(content)
        
        packet = synthesize_mission(
            task_id="TASK-002",
            backlog_path=backlog_path,
            repo_root=repo_with_docs,
        )
        assert len(packet.constraints) == 2
        assert "Must be fast" in packet.constraints


class TestSynthesisErrors:
    """Tests for synthesis error handling."""
    
    def test_task_not_found(self, repo_with_docs, valid_backlog):
        """Unknown task raises SynthesisError."""
        with pytest.raises(SynthesisError, match="not found in backlog"):
            synthesize_mission(
                task_id="NONEXISTENT",
                backlog_path=valid_backlog,
                repo_root=repo_with_docs,
            )
    
    def test_backlog_not_found(self, repo_with_docs):
        """Missing backlog raises SynthesisError."""
        with pytest.raises(SynthesisError, match="Failed to parse backlog"):
            synthesize_mission(
                task_id="TASK-001",
                backlog_path=repo_with_docs / "nonexistent.yaml",
                repo_root=repo_with_docs,
            )
    
    def test_context_resolution_failure(self, repo_with_docs):
        """Unresolvable hint raises SynthesisError."""
        content = dedent("""
            schema_version: "1.0"
            tasks:
              - id: "BAD-TASK"
                description: "Bad context"
                priority: P1
                context_hints:
                  - "docs/does_not_exist.md"
        """).strip()
        backlog_path = repo_with_docs / "config" / "backlog.yaml"
        backlog_path.write_text(content)
        
        with pytest.raises(SynthesisError, match="Failed to resolve context"):
            synthesize_mission(
                task_id="BAD-TASK",
                backlog_path=backlog_path,
                repo_root=repo_with_docs,
            )


class TestMissionPacket:
    """Tests for MissionPacket dataclass."""
    
    def test_immutable(self, repo_with_docs, valid_backlog):
        """MissionPacket is frozen."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        with pytest.raises(AttributeError):
            packet.task_id = "CHANGED"
    
    def test_packet_id_format(self, repo_with_docs, valid_backlog):
        """Packet ID has expected format."""
        packet = synthesize_mission(
            task_id="TASK-001",
            backlog_path=valid_backlog,
            repo_root=repo_with_docs,
        )
        assert packet.packet_id.startswith("MSE-")
        assert len(packet.packet_id) == 20  # MSE- + 16 hex chars
