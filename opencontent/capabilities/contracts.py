"""Schemas and contracts for OpenContent Creative Capability Pack architecture."""

PACK_SCHEMA_V1 = "opencontent.capability-pack.v1"
TASK_SCHEMA_V1 = "opencontent.creative-task.v1"
CONTEXT_SCHEMA_V1 = "opencontent.context.v1"
STATE_DELTA_SCHEMA_V1 = "opencontent.state-delta.v1"
CANDIDATE_SCHEMA_V1 = "opencontent.candidate-artifact.v1"

ALLOWED_TASK_TYPES = (
    "long-scan",
    "short-scan",
    "long-analyze",
    "short-analyze",
    "plan",
    "write",
    "continue",
    "revise",
    "critique",
    "cover",
)

ALLOWED_OUTPUTS = (
    "artifact",
    "proposal",
    "state_delta",
    "review",
    "market_report",
    "mechanism_cards",
    "cover_spec",
)

ALLOWED_RUNTIME_LEVELS = ("required", "optional", "disabled")

EXECUTION_PROFILES = (
    "STRUCTURED_READONLY",
    "CREATIVE_WORKSPACE",
    "INDEPENDENT_REVIEW"
)
