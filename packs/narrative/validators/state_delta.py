"""State delta validator for Narrative Pack."""
from typing import Dict, Any, List
from opencontent.vault import Problem
from opencontent.capabilities.validation import validate_state_delta


def validate_narrative_delta(delta: Dict[str, Any]) -> Dict[str, Any]:
    """Validate narrative-specific state delta structures."""
    # First run standard capability state delta validation
    validate_state_delta(delta)

    # Narrative-specific checks: character state transitions
    for char in delta.get("characters", []):
        name = char.get("name")
        if not name or not isinstance(name, str):
            raise Problem("Character entry in state delta requires a valid 'name'")

    for rule in delta.get("world", []):
        if not rule.get("assertion"):
            raise Problem("World rule entry requires an 'assertion'")

    return delta
