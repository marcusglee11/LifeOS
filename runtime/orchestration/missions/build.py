"""
Phase 3 Mission Types - Build Mission

Invokes builder (OpenCode) with approved BUILD_PACKET.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: build
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)

logger = logging.getLogger(__name__)


class BuildMission(BaseMission):
    """
    Build mission: Invoke builder with approved BUILD_PACKET.
    
    Inputs:
        - build_packet (dict): The approved BUILD_PACKET
        - approval (dict): Council approval decision
        
    Outputs:
        - review_packet (dict): Package of build outputs for review
        
    Preconditions:
        - approval.verdict == "approved"
        
    Steps:
        1. check_envelope: Verify build is within envelope
        2. invoke_builder: Execute build (stubbed for MVP)
        3. collect_evidence: Gather build outputs
        4. package_output: Create REVIEW_PACKET
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.BUILD
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate build mission inputs.
        
        Required: build_packet (dict), approval (dict with verdict="approved")
        """
        # Check build_packet
        build_packet = inputs.get("build_packet")
        if not build_packet:
            raise MissionValidationError("build_packet is required")
        if not isinstance(build_packet, dict):
            raise MissionValidationError("build_packet must be a dict")
        
        # Validate build_packet has required fields
        if not build_packet.get("goal"):
            raise MissionValidationError("build_packet.goal is required")
        
        # Check approval
        approval = inputs.get("approval")
        if not approval:
            raise MissionValidationError("approval is required")
        if not isinstance(approval, dict):
            raise MissionValidationError("approval must be a dict")
        
        # Verify approval verdict
        verdict = approval.get("verdict")
        if verdict != "approved":
            raise MissionValidationError(
                f"Build requires approved verdict, got: '{verdict}'"
            )
    
    def _apply_build_packet(
        self, context: MissionContext, packet: dict
    ) -> Tuple[List[str], List[str]]:
        """
        Apply file changes from the LLM response packet to disk.

        The builder LLM returns a YAML packet with a 'files' array.
        Each entry has path, action (create/modify/delete), and content.
        This method writes those changes so git can detect them.

        Returns:
            Tuple of (applied_paths, errors)
        """
        files = packet.get("files", [])
        if not files or not isinstance(files, list):
            return [], []

        applied = []
        errors = []

        for entry in files:
            if not isinstance(entry, dict):
                continue

            rel_path = entry.get("path", "")
            action = entry.get("action", "modify")
            content = entry.get("content", "")

            if not rel_path:
                continue

            # Normalize and validate path (no escapes, no absolute)
            rel_path = rel_path.replace("\\", "/").lstrip("/")
            if ".." in rel_path.split("/"):
                errors.append(f"BLOCKED: path traversal in {rel_path}")
                continue

            full_path = Path(context.repo_root) / rel_path

            try:
                if action == "delete":
                    if full_path.exists():
                        full_path.unlink()
                        applied.append(rel_path)
                elif action in ("create", "modify"):
                    if action == "modify" and self._looks_like_diff(content):
                        ok = self._apply_diff(context.repo_root, content)
                        if ok:
                            applied.append(rel_path)
                        else:
                            errors.append(f"diff apply failed for {rel_path}")
                    else:
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content, encoding="utf-8")
                        applied.append(rel_path)
                else:
                    errors.append(f"unknown action '{action}' for {rel_path}")
            except Exception as exc:
                errors.append(f"{rel_path}: {type(exc).__name__}: {exc}")

        return applied, errors

    @staticmethod
    def _looks_like_diff(content: str) -> bool:
        """Check if content appears to be a unified diff."""
        lines = content.strip().splitlines()
        if len(lines) < 3:
            return False
        return lines[0].startswith("---") and lines[1].startswith("+++")

    @staticmethod
    def _apply_diff(repo_root: Path, diff_content: str) -> bool:
        """Apply a unified diff via git apply, with whitespace-lenient fallback."""
        for extra_args in [[], ["--ignore-whitespace"]]:
            try:
                result = subprocess.run(
                    ["git", "apply", "--allow-empty"] + extra_args + ["-"],
                    input=diff_content,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return True
            except Exception:
                return False
        return False

    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []

        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")

            build_packet = inputs["build_packet"]

            # Step 2: Invoke builder via Agent API
            from runtime.agents.api import call_agent, AgentCall

            # Read actual file contents so the builder can generate correct diffs.
            # Without this, the LLM guesses file structure and produces inapplicable patches.
            context_refs = []
            for deliverable in build_packet.get("deliverables", []):
                if isinstance(deliverable, dict):
                    file_path = deliverable.get("file", "")
                    if file_path:
                        full = Path(context.repo_root) / file_path
                        if full.exists():
                            try:
                                context_refs.append({
                                    "path": file_path,
                                    "current_content": full.read_text(encoding="utf-8"),
                                })
                            except Exception:
                                pass

            call = AgentCall(
                role="builder",
                packet={
                    "build_packet": build_packet,
                    "context_refs": context_refs,
                    # Ask for full content — diffs are prone to hunk-count mismatches.
                    "output_instructions": (
                        "For all file modifications: return the COMPLETE file content "
                        "in the 'content' field (not a unified diff). "
                        "Use action='modify'. Do not use diff/patch format."
                    ),
                },
                model="auto",
            )

            response = call_agent(call, run_id=context.run_id)
            executed_steps.append("invoke_builder_llm_call")

            # Step 2.5: Apply LLM packet to disk if available
            apply_errors = []
            if response.packet and isinstance(response.packet, dict):
                applied_paths, apply_errors = self._apply_build_packet(
                    context, response.packet
                )
                if applied_paths:
                    logger.info("Applied %d file(s) from LLM packet: %s", len(applied_paths), applied_paths)
                if apply_errors:
                    logger.warning("Apply errors: %s", apply_errors)
            executed_steps.append("apply_build_output")

            # Step 3: Detect all changed files (includes both packet-applied and
            # any changes made by an agentic OpenCode CLI session).
            # git status --porcelain detects modified tracked files AND new untracked files.
            artifacts_produced = []
            constructed_packet = None
            try:
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=context.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if status_result.returncode == 0 and status_result.stdout.strip():
                    all_changed = []
                    for line in status_result.stdout.strip().split('\n'):
                        if not line.strip():
                            continue
                        # Format: "XY path" (XY are two-char status codes)
                        parts = line.strip().split(None, 1)
                        if len(parts) >= 2:
                            file_path = parts[1].strip()
                            # Handle renamed/copied: "R old -> new" format
                            if " -> " in file_path:
                                file_path = file_path.split(" -> ")[-1]
                            all_changed.append(file_path)

                    artifacts_produced = [
                        f for f in all_changed
                        if not f.startswith(('artifacts/loop_state/', 'artifacts/terminal/', 'logs/'))
                    ]

                    if not response.packet and artifacts_produced:
                        files_list = []
                        for artifact in artifacts_produced:
                            diff_cmd = subprocess.run(
                                ["git", "diff", artifact],
                                cwd=context.repo_root,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if diff_cmd.returncode == 0:
                                files_list.append({
                                    "path": artifact,
                                    "action": "modify",
                                    "content": diff_cmd.stdout
                                })

                        constructed_packet = {
                            "files": files_list,
                            "tests": [],
                            "verification_commands": []
                        }
            except Exception:
                pass

            # Step 4: Package output as REVIEW_PACKET
            review_packet = {
                "mission_name": f"build_{context.run_id[:8]}",
                "summary": f"Build for: {build_packet.get('goal', 'unknown')}",
                "payload": {
                    "build_packet": build_packet,
                    "content": response.content,
                    "packet": constructed_packet or response.packet,
                    "artifacts_produced": artifacts_produced,
                },
                "evidence": {
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "usage": response.usage,
                    "apply_errors": apply_errors,
                }
            }
            executed_steps.append("package_output")

            return self._make_result(
                success=True,
                outputs={"review_packet": review_packet},
                executed_steps=executed_steps,
                evidence=review_packet["evidence"],
            )

        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Build mission failed: {e}",
            )
