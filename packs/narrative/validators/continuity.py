"""Continuity validator for narrative drafts and chapters."""
from typing import Dict, List, Any
import re


def check_continuity(
    draft_body: str,
    established_state: Dict[str, Any],
    profile_rules: Dict[str, Any],
) -> List[str]:
    """Inspect draft body for continuity violations against established state and world rules."""
    issues = []
    text_lower = draft_body.lower()

    # 1. Check deceased / inactive character violations
    for char in established_state.get("characters", []):
        name = char.get("name", "").lower()
        if not name:
            continue
        status = char.get("status", "alive").lower()
        if status in ("deceased", "dead", "destroyed"):
            # Check if name is mentioned in text
            if name in text_lower:
                # Disallow active participation unless in explicit memorial/memory/flashback phrasing
                memory_pattern = r"(回忆|梦见|想起|遗体|墓地|悼念|memorial|remembered|flashback|apparition)"
                if not re.search(memory_pattern, text_lower):
                    issues.append(f"Deceased character '{char.get('name')}' appears in active scene without memory/memorial context.")

    # 2. Check world rule conflicts
    for rule in established_state.get("world", []):
        assertion = rule.get("assertion", "")
        negative_marker = rule.get("forbidden_occurrence", "")
        if negative_marker and negative_marker.lower() in text_lower:
            issues.append(f"Draft violates world rule '{assertion}': found '{negative_marker}'.")

    return issues
