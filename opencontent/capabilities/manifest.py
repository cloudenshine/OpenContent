"""Manifest parser and validator for Capability Packs."""
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Any
import yaml

from opencontent.vault import Problem
from .contracts import (
    PACK_SCHEMA_V1,
    ALLOWED_TASK_TYPES,
    ALLOWED_OUTPUTS,
    ALLOWED_RUNTIME_LEVELS,
)


@dataclass
class PackManifest:
    id: str
    name: str
    version: str
    description: str
    profiles: List[str]
    tasks: List[str]
    runtime: Dict[str, str]
    workflows: Dict[str, str]
    context_selector: Optional[str]
    outputs: List[str]
    root_dir: Path
    raw: Dict[str, Any] = field(default_factory=dict)


def validate_manifest(raw: Dict[str, Any], root_dir: Path) -> PackManifest:
    """Validate a pack.yaml dictionary and return structured PackManifest."""
    if not isinstance(raw, dict):
        raise Problem("Capability pack manifest must be a dictionary")

    schema = raw.get("schema")
    if schema != PACK_SCHEMA_V1:
        raise Problem(f"Unsupported capability pack schema: '{schema}'. Expected '{PACK_SCHEMA_V1}'")

    pack_id = raw.get("id")
    if not isinstance(pack_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", pack_id):
        raise Problem(f"Invalid pack id '{pack_id}': must be 2-32 lowercase alphanumeric with hyphens/underscores")

    version = raw.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise Problem(f"Invalid pack version '{version}': must follow semver X.Y.Z")

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Problem("Capability pack requires a non-empty name")

    description = raw.get("description", "").strip()

    profiles = raw.get("profiles", [])
    if not isinstance(profiles, list) or not profiles or not all(isinstance(p, str) for p in profiles):
        raise Problem("Pack requires a non-empty list of profiles")

    tasks = raw.get("tasks", [])
    if not isinstance(tasks, list) or not tasks or not all(isinstance(t, str) for t in tasks):
        raise Problem("Pack requires a non-empty list of tasks")
    for t in tasks:
        if t not in ALLOWED_TASK_TYPES:
            raise Problem(f"Invalid task '{t}'; allowed tasks are: {ALLOWED_TASK_TYPES}")

    runtime = raw.get("runtime", {})
    if not isinstance(runtime, dict):
        raise Problem("Pack runtime section must be a dictionary")
    for k, v in runtime.items():
        if v not in ALLOWED_RUNTIME_LEVELS:
            raise Problem(f"Invalid runtime requirement for '{k}': '{v}'. Expected {ALLOWED_RUNTIME_LEVELS}")

    workflows = raw.get("workflows", {})
    if not isinstance(workflows, dict):
        raise Problem("Pack workflows must be a dictionary mapping task to workflow definition path")

    root_dir = Path(root_dir).resolve()

    for task_name in tasks:
        wf_rel = workflows.get(task_name)
        if not wf_rel or not isinstance(wf_rel, str):
            raise Problem(f"Missing workflow path for task '{task_name}' in pack '{pack_id}'")
        wf_path = (root_dir / wf_rel).resolve()
        if not wf_path.is_relative_to(root_dir) or not wf_path.is_file():
            raise Problem(f"Workflow file for '{task_name}' does not exist or escapes pack: '{wf_rel}'")

    context_sec = raw.get("context", {})
    selector_rel = context_sec.get("selector") if isinstance(context_sec, dict) else None
    if selector_rel:
        sel_path = (root_dir / selector_rel).resolve()
        if not sel_path.is_relative_to(root_dir) or not sel_path.is_file():
            raise Problem(f"Context selector file does not exist or escapes pack: '{selector_rel}'")

    for prof in profiles:
        prof_path = (root_dir / "profiles" / f"{prof}.yaml").resolve()
        if not prof_path.is_file():
            prof_path_yml = (root_dir / "profiles" / f"{prof}.yml").resolve()
            if not prof_path_yml.is_file():
                raise Problem(f"Profile file for '{prof}' not found in profiles/ for pack '{pack_id}'")

    outputs = raw.get("outputs", [])
    if not isinstance(outputs, list) or not outputs:
        raise Problem("Pack requires non-empty outputs list")
    for out in outputs:
        if out not in ALLOWED_OUTPUTS:
            raise Problem(f"Unknown output type '{out}'; allowed outputs: {ALLOWED_OUTPUTS}")

    return PackManifest(
        id=pack_id,
        name=name,
        version=version,
        description=description,
        profiles=profiles,
        tasks=tasks,
        runtime=runtime,
        workflows=workflows,
        context_selector=selector_rel,
        outputs=outputs,
        root_dir=root_dir,
        raw=raw,
    )


def load_manifest(pack_dir: Path) -> PackManifest:
    """Load and validate pack.yaml or pack.yml from a directory."""
    pack_dir = Path(pack_dir).resolve()
    manifest_file = pack_dir / "pack.yaml"
    if not manifest_file.is_file():
        manifest_file = pack_dir / "pack.yml"
    if not manifest_file.is_file():
        raise Problem(f"Capability pack missing pack.yaml in '{pack_dir}'")
    try:
        raw = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise Problem(f"Failed to parse YAML manifest in '{manifest_file}': {e}") from e
    return validate_manifest(raw, pack_dir)
