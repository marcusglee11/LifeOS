"""Build phase packet transform."""

from __future__ import annotations

from typing import Any, Dict

from .base import register_transform


@register_transform("to_build_packet", version="1.0.0")
def to_build_packet(packet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform design output into a BUILD_PACKET.

    Preserve the canonical design fields so the transformed packet remains
    directly consumable by the legacy build mission contract.
    """
    return {
        "packet_type": "BUILD_PACKET",
        "goal": packet.get("goal", ""),
        "scope": packet.get("scope", {}),
        "deliverables": packet.get("deliverables", []),
        "constraints": packet.get("constraints", []),
        "acceptance_criteria": packet.get("acceptance_criteria", []),
        "build_type": packet.get("build_type", ""),
        "proposed_changes": packet.get("proposed_changes", []),
        "verification_plan": packet.get("verification_plan", {}),
        "risks": packet.get("risks", []),
        "assumptions": packet.get("assumptions", []),
        "source_design": packet.get("design_summary", ""),
        "phase": "build",
        "build_ready": True,
    }
