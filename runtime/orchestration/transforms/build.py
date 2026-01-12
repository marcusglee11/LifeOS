"""Build phase packet transform."""

from typing import Dict, Any

from .base import register_transform


@register_transform("to_build_packet", version="1.0.0")
def to_build_packet(packet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform design output into a BUILD_PACKET.
    
    Per v0.3 spec: BUILD_PACKET with scope, deliverables, constraints.
    """
    return {
        "packet_type": "BUILD_PACKET",
        "scope": packet.get("scope", {}),
        "deliverables": packet.get("deliverables", []),
        "constraints": packet.get("constraints", []),
        "source_design": packet.get("design_summary", ""),
        "phase": "build",
        "build_ready": True,
    }
