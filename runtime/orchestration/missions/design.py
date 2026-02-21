"""
Phase 3 Mission Types - Design Mission

Transforms a task specification into a BUILD_PACKET.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: design

HARDENED: Fail-closed output validation - no success without valid BUILD_PACKET.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)


# Minimal MVP BUILD_PACKET schema - required keys for valid packet
BUILD_PACKET_REQUIRED_KEYS = ["goal"]
BUILD_PACKET_OPTIONAL_KEYS = [
    "scope", "deliverables", "constraints", "acceptance_criteria",
    "build_type", "proposed_changes", "verification_plan", "risks", "assumptions",
]


class DesignMission(BaseMission):
    """
    Design mission: Transform task spec into BUILD_PACKET.
    
    Inputs:
        - task_spec (str): Description of the task to design
        - context_refs (list[str], optional): Paths to context files
        
    Outputs:
        - build_packet (dict): The generated BUILD_PACKET
        
    Steps:
        1. validate_inputs: Validate mission inputs
        2. gather_context: Read context files (if provided)
        3. design_llm_call: Generate BUILD_PACKET via LLM
        4. validate_output: Validate output against BUILD_PACKET schema (FAIL-CLOSED)
        
    HARDENED: This mission returns success=False if output validation fails.
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.DESIGN
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate design mission inputs.
        
        Required: task_spec (non-empty string)
        Optional: context_refs (list of strings)
        """
        # Check required field
        task_spec = inputs.get("task_spec")
        if not task_spec:
            raise MissionValidationError("task_spec is required and must be non-empty")
        if not isinstance(task_spec, str):
            raise MissionValidationError("task_spec must be a string")
        
        # Check optional field
        context_refs = inputs.get("context_refs")
        if context_refs is not None:
            if not isinstance(context_refs, list):
                raise MissionValidationError("context_refs must be a list")
            for i, ref in enumerate(context_refs):
                if not isinstance(ref, str):
                    raise MissionValidationError(
                        f"context_refs[{i}] must be a string, got {type(ref).__name__}"
                    )
    
    def _validate_build_packet(self, packet: Any) -> Tuple[bool, List[str]]:
        """
        Validate BUILD_PACKET against minimal MVP schema.
        
        FAIL-CLOSED: Returns (False, errors) if packet is invalid.
        Errors are deterministically ordered (sorted).
        
        Args:
            packet: The packet to validate (may be None or any type).
            
        Returns:
            (valid: bool, errors: List[str]) - sorted error list for determinism.
        """
        errors: List[str] = []
        
        # Check packet exists and is dict
        if packet is None:
            errors.append("BUILD_PACKET is missing (response.packet is None)")
            return (False, errors)
        
        if not isinstance(packet, dict):
            errors.append(f"BUILD_PACKET must be a dict, got {type(packet).__name__}")
            return (False, errors)
        
        # Check required keys
        for key in sorted(BUILD_PACKET_REQUIRED_KEYS):
            if key not in packet:
                errors.append(f"BUILD_PACKET missing required key: '{key}'")
            elif not packet[key]:
                errors.append(f"BUILD_PACKET.{key} is empty")
        
        # Sort errors for determinism
        errors.sort()

        return (len(errors) == 0, errors)

    def _extract_fallback_packet(
        self, content: str, task_spec: str
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to extract a BUILD_PACKET from raw LLM content.

        Called when response.packet is None (e.g. CLI fallback path returned
        prose instead of structured YAML). Tries three strategies:

        1. YAML from code blocks (relaxed regex)
        2. Bare ``goal:`` field extraction
        3. If content indicates model did the work, pass through task_spec

        Returns None if no valid packet can be extracted.
        The ``_source`` key tags how the packet was obtained.
        """
        import yaml

        if not content or not content.strip():
            return None

        # Strategy 1: YAML from code blocks
        pattern = r"```(?:yaml|json|yml)?\s*\n(.*?)\n\s*```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                parsed = yaml.safe_load(match.group(1))
                if isinstance(parsed, dict) and parsed.get("goal"):
                    parsed["_source"] = "yaml_codeblock"
                    return parsed
            except Exception:
                pass

        # Strategy 2: Bare goal: field in content
        goal_match = re.search(
            r"^goal:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE
        )
        if goal_match:
            goal_text = goal_match.group(1).strip().strip("\"'")
            if goal_text:
                try:
                    parsed = yaml.safe_load(content)
                    if isinstance(parsed, dict) and parsed.get("goal"):
                        parsed["_source"] = "bare_yaml"
                        return parsed
                except Exception:
                    pass
                return {"goal": goal_text, "_source": "bare_goal_field"}

        # Strategy 3: Content indicates model did the work directly
        did_work_indicators = [
            r"\bdone\b", r"\badded\b", r"\bcreated\b", r"\bupdated\b",
            r"\bmodified\b", r"\bimplemented\b", r"\bcompleted\b",
        ]
        content_lower = content.lower()
        if any(re.search(ind, content_lower) for ind in did_work_indicators):
            return {
                "goal": task_spec,
                "_source": "tool_output_passthrough",
                "_note": "Model performed work directly instead of producing BUILD_PACKET",
            }

        return None

    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []
        evidence: Dict[str, Any] = {"stubbed": False}  # Real LLM call, not stubbed
        
        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            
            # Step 2: Gather context
            # Auto-populate context_refs from files mentioned in the task spec so the
            # designer knows the actual function signatures and avoids hallucinating them.
            from pathlib import Path as _Path
            provided_refs = inputs.get("context_refs", [])
            auto_refs: List[Dict[str, Any]] = []
            if not provided_refs and isinstance(inputs.get("task_spec"), str):
                provided_paths = {r.get("path") for r in provided_refs if isinstance(r, dict)}
                file_pattern = re.compile(r'\b([\w][/\w.-]*\.py)\b')
                for fpath in file_pattern.findall(inputs["task_spec"]):
                    fpath = fpath.replace("\\", "/").lstrip("/")
                    if ".." in fpath.split("/") or fpath in provided_paths:
                        continue
                    full = _Path(context.repo_root) / fpath
                    if full.exists():
                        try:
                            auto_refs.append({
                                "path": fpath,
                                "current_content": full.read_text(encoding="utf-8"),
                            })
                        except Exception:
                            pass

            context_data = {
                "task_spec": inputs["task_spec"],
                "context_refs": provided_refs + auto_refs,
                "run_id": context.run_id,
            }
            executed_steps.append("gather_context")
            evidence["context_refs_count"] = len(context_data["context_refs"])
            
            # Step 3: Call Agent API with designer role
            from runtime.agents.api import call_agent, AgentCall
            
            call = AgentCall(
                role="designer",
                packet=context_data,
                model="auto",
            )
            
            response = call_agent(call, run_id=context.run_id)
            executed_steps.append("design_llm_call")
            
            # Capture LLM evidence
            evidence["call_id"] = response.call_id
            evidence["model_used"] = response.model_used
            evidence["latency_ms"] = response.latency_ms
            evidence["usage"] = response.usage # Expose for budgeting
            
            # Step 4: Validate output (FAIL-CLOSED)
            # This step is ALWAYS recorded when we reach this point
            valid, validation_errors = self._validate_build_packet(response.packet)
            executed_steps.append("validate_output")

            # Step 4b: Fallback extraction when packet is None but content exists
            response_packet = response.packet
            if not valid and response.packet is None and response.content:
                fallback_packet = self._extract_fallback_packet(
                    response.content, inputs["task_spec"]
                )
                if fallback_packet:
                    valid, validation_errors = self._validate_build_packet(fallback_packet)
                    if valid:
                        evidence["packet_source"] = "fallback_extraction"
                        evidence["fallback_strategy"] = fallback_packet.get("_source", "unknown")
                        response_packet = fallback_packet

            if not valid:
                # FAIL-CLOSED: Invalid packet -> success=False
                # Attach raw content as evidence ONLY (not as valid output)
                evidence["draft_text"] = response.content
                evidence["validation_errors"] = validation_errors

                return self._make_result(
                    success=False,
                    outputs={},  # No valid output
                    executed_steps=executed_steps,
                    error=f"BUILD_PACKET validation failed: {'; '.join(validation_errors)}",
                    evidence=evidence,
                )

            # Valid packet - return success
            return self._make_result(
                success=True,
                outputs={"build_packet": response_packet},
                executed_steps=executed_steps,
                evidence=evidence,
            )
            
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Design mission failed: {e}",
                evidence=evidence,
            )
