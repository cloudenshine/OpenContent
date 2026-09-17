"""Schemas and contracts for OpenContent Creative Capability Pack architecture."""

PACK_SCHEMA_V1 = "opencontent.capability-pack.v1"
TASK_SCHEMA_V1 = "opencontent.creative-task.v1"
CONTEXT_SCHEMA_V1 = "opencontent.context.v1"
STATE_DELTA_SCHEMA_V1 = "opencontent.state-delta.v1"
CANDIDATE_SCHEMA_V1 = "opencontent.candidate-artifact.v1"

ALLOWED_TASK_TYPES = ("plan", "write", "continue", "revise", "critique")
ALLOWED_OUTPUTS = ("artifact", "proposal", "state_delta", "review")
ALLOWED_RUNTIME_LEVELS = ("required", "optional", "disabled")

EXECUTION_PROFILES = (
    "STRUCTURED_READONLY",
    "CREATIVE_WORKSPACE",
    "INDEPENDENT_REVIEW"
)
