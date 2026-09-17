"""Deterministic Task Router for Creative Capability Packs."""
from pathlib import Path
from typing import Dict, Any
import yaml

from opencontent.vault import Problem
from .contracts import TASK_SCHEMA_V1, ALLOWED_TASK_TYPES
from .registry import PackRegistry


class TaskRouter:
    """Routes creative tasks to explicit pack, profile, and workflow definition."""

    def route(self, request: Dict[str, Any], registry: PackRegistry) -> Dict[str, Any]:
        if not isinstance(request, dict):
            raise Problem("Task request must be a dictionary")

        schema = request.get("schema")
        if schema != TASK_SCHEMA_V1:
            raise Problem(f"Unsupported task schema '{schema}'. Expected '{TASK_SCHEMA_V1}'")

        task_name = request.get("task")
        if task_name not in ALLOWED_TASK_TYPES:
            raise Problem(f"Unsupported task '{task_name}'. Allowed: {ALLOWED_TASK_TYPES}")

        pack_id = request.get("pack")
        if not pack_id or not isinstance(pack_id, str):
            raise Problem("Task request requires an explicit 'pack' identifier")

        pack = registry.get_pack(pack_id)
        if task_name not in pack.tasks:
            raise Problem(f"Task '{task_name}' is not supported by pack '{pack_id}'. Supported: {pack.tasks}")

        profile_id = request.get("profile")
        if not profile_id or not isinstance(profile_id, str):
            # Fall back to pack's first profile explicitly
            profile_id = pack.profiles[0]

        profile_data = registry.get_profile(pack_id, profile_id)

        wf_rel = pack.workflows.get(task_name)
        if not wf_rel:
            raise Problem(f"No workflow configured for task '{task_name}' in pack '{pack_id}'")

        wf_path = pack.root_dir / wf_rel
        if not wf_path.is_file():
            raise Problem(f"Workflow file '{wf_path}' not found")

        try:
            workflow_data = yaml.safe_load(wf_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            raise Problem(f"Failed to load workflow '{wf_path}': {e}") from e

        return {
            "task": task_name,
            "pack": pack,
            "profile_id": profile_id,
            "profile": profile_data,
            "workflow": workflow_data,
        }
