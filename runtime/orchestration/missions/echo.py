from typing import Any, Dict

from runtime.orchestration.missions.base import BaseMission, MissionContext, MissionResult, MissionType

class EchoMission(BaseMission):
    """
    Minimal offline mission for verifying dispatcher wiring.
    Returns inputs unchanged.
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.ECHO
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        # Accept anything
        pass
        
    def run(self, ctx: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        """Echo inputs back as output."""
        return MissionResult(
            success=True,
            mission_type=self.mission_type,
            outputs=inputs,
            error=None
        )
