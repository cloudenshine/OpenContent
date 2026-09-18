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
from .runtime import CapabilityRuntime
from .validation import (
    validate_workspace_path,
    validate_state_delta,
    validate_candidate_output,
)
from .market import (
    LongMarketAnalyzer,
    ShortMarketAnalyzer,
    normalize_record,
    clean_intro,
)
from .deconstruction import (
    StoryDeconstructor,
    MechanismCard,
)
from .media import (
    CoverDirector,
    MediaGenerationAdapter,
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
    "CapabilityRuntime",
    "validate_workspace_path",
    "validate_state_delta",
    "validate_candidate_output",
    "LongMarketAnalyzer",
    "ShortMarketAnalyzer",
    "normalize_record",
    "clean_intro",
    "StoryDeconstructor",
    "MechanismCard",
    "CoverDirector",
    "MediaGenerationAdapter",
]
