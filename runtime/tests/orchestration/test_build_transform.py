from __future__ import annotations

from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.transforms.build import to_build_packet


def test_to_build_packet_preserves_build_mission_contract() -> None:
    design_packet = {
        "goal": "Implement feature X",
        "scope": {"module": "runtime"},
        "deliverables": [{"file": "runtime/example.py"}],
        "constraints": ["No breaking changes"],
        "acceptance_criteria": ["Tests pass"],
        "build_type": "code_creation",
        "proposed_changes": ["Add support for the new flow"],
        "verification_plan": {"steps": ["pytest runtime/tests -q"]},
        "risks": ["Low regression risk"],
        "assumptions": ["No schema changes required"],
        "design_summary": "Approved design summary",
    }

    transformed = to_build_packet(design_packet, context={})

    BuildMission().validate_inputs(
        {
            "build_packet": transformed,
            "approval": {"verdict": "approved"},
        }
    )

    assert transformed["packet_type"] == "BUILD_PACKET"
    assert transformed["goal"] == design_packet["goal"]
    assert transformed["acceptance_criteria"] == design_packet["acceptance_criteria"]
    assert transformed["build_type"] == design_packet["build_type"]
    assert transformed["proposed_changes"] == design_packet["proposed_changes"]
    assert transformed["verification_plan"] == design_packet["verification_plan"]
    assert transformed["risks"] == design_packet["risks"]
    assert transformed["assumptions"] == design_packet["assumptions"]
    assert transformed["source_design"] == design_packet["design_summary"]
