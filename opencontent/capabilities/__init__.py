"""OpenContent Creative Capability Pack Architecture."""

from .contracts import (
    PACK_SCHEMA_V1,
    TASK_SCHEMA_V1,
    CONTEXT_SCHEMA_V1,
    STATE_DELTA_SCHEMA_V1,
    CANDIDATE_SCHEMA_V1,
    ALLOWED_TASK_TYPES,
    ALLOWED_OUTPUTS,
    EXECUTION_PROFILES,
)
from .manifest import PackManifest, validate_manifest, load_manifest
from .registry import PackRegistry
from .router import TaskRouter
from .context import ContextAssembler
from .validation import (
    validate_workspace_path,
    validate_state_delta,
    validate_candidate_output,
)

__all__ = [
    "PACK_SCHEMA_V1",
    "TASK_SCHEMA_V1",
    "CONTEXT_SCHEMA_V1",
    "STATE_DELTA_SCHEMA_V1",
    "CANDIDATE_SCHEMA_V1",
    "ALLOWED_TASK_TYPES",
    "ALLOWED_OUTPUTS",
    "EXECUTION_PROFILES",
    "PackManifest",
    "validate_manifest",
    "load_manifest",
    "PackRegistry",
    "TaskRouter",
    "ContextAssembler",
    "validate_workspace_path",
    "validate_state_delta",
    "validate_candidate_output",
]
