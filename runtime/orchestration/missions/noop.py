"""
Test-only mission for E2E acceptance proof verification.

This mission is designed to work in any repository context without
requiring specific configuration (no backlog.yaml, etc.). It exists
solely to test the Mission CLI's acceptance proof generation path.
"""

from typing import Any, Dict

from runtime.orchestration.missions.base import BaseMission, MissionContext, MissionResult, MissionType


class NoopMission(BaseMission):
    """
    Minimal test-only mission for E2E acceptance proof verification.
    
    This mission:
    - Accepts any inputs (no validation)
    - Always succeeds immediately
    - Requires no repo-specific configuration
    - Exists solely to test acceptance token generation
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.NOOP
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Accept any inputs without validation."""
        pass
        
    def run(self, ctx: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        """Return success immediately with no side effects."""
        return MissionResult(
            success=True,
            mission_type=self.mission_type,
            outputs={"test": "noop executed successfully"},
            error=None
        )
