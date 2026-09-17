"""Security, continuity, and state-delta validators for Capability Tasks."""
from pathlib import Path
from typing import Dict, Any, List
from opencontent.vault import Problem
from .contracts import STATE_DELTA_SCHEMA_V1, CANDIDATE_SCHEMA_V1

ALLOWED_DELTA_ORIGINS = ("observed_from_output", "explicit_user_instruction", "agent_inference")


def validate_workspace_path(rel_path: str, workspace_root: Path) -> Path:
    """Ensure relative path does not escape workspace directory."""
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise Problem("Path must be a non-empty string")
    workspace_root = Path(workspace_root).resolve()
    target = (workspace_root / rel_path).resolve()
    if not target.is_relative_to(workspace_root):
        raise Problem(f"Path escapes task workspace: '{rel_path}'")
    for p in (target, *target.parents):
        if p == workspace_root:
            break
        if p.is_symlink():
            raise Problem(f"Symlinks are forbidden in task workspace: '{rel_path}'")
    return target


def validate_state_delta(delta: Dict[str, Any]) -> Dict[str, Any]:
    """Validate structured State Delta output from a creative task."""
    if not isinstance(delta, dict):
        raise Problem("State delta must be an object")

    schema = delta.get("schema")
    if schema != STATE_DELTA_SCHEMA_V1:
        raise Problem(f"Invalid state delta schema: '{schema}'. Expected '{STATE_DELTA_SCHEMA_V1}'")

    for key in ("characters", "relationships", "timeline", "world", "open_threads", "resolved_threads", "new_proposals"):
        items = delta.get(key, [])
        if not isinstance(items, list):
            raise Problem(f"State delta section '{key}' must be a list")
        for item in items:
            if not isinstance(item, dict):
                raise Problem(f"Item in state delta '{key}' must be an object")
            origin = item.get("origin")
            if origin and origin not in ALLOWED_DELTA_ORIGINS:
                raise Problem(f"Invalid origin '{origin}' in state delta '{key}'. Allowed: {ALLOWED_DELTA_ORIGINS}")

    return delta


def validate_candidate_output(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Candidate Artifact produced by creator workflow."""
    if not isinstance(candidate, dict):
        raise Problem("Candidate artifact must be an object")
    
    title = candidate.get("title")
    if not isinstance(title, str) or not title.strip():
        raise Problem("Candidate artifact requires a non-empty title")

    body = candidate.get("body")
    if not isinstance(body, str) or not body.strip():
        raise Problem("Candidate artifact requires non-empty body content")

    return candidate
