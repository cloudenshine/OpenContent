"""Narrative-specific context selector for tailoring context assembly."""
from typing import Dict, List, Any, Optional


def select_narrative_context(
    task: str,
    instruction: str,
    state_data: Dict[str, Any],
    artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Select prioritized narrative entities (characters, timeline, threads) relevant to current task."""
    text_corpus = (instruction + " " + (artifact.get("body", "") if artifact else "")).lower()

    characters = state_data.get("characters", [])
    selected_chars = []
    for char in characters:
        name = char.get("name", "").lower()
        # High relevance: mentioned in instruction or current draft, or marked active
        if name and (name in text_corpus or char.get("active", False)):
            selected_chars.append(char)

    timeline = state_data.get("timeline", [])
    # Recent chronological milestones
    selected_timeline = timeline[-6:] if len(timeline) > 6 else timeline

    open_threads = state_data.get("open_threads", [])
    # Relevant open threads
    selected_threads = []
    for thread in open_threads:
        t_desc = thread.get("description", "").lower()
        if any(w in t_desc for w in text_corpus.split() if len(w) > 3) or thread.get("urgent", False):
            selected_threads.append(thread)
    if not selected_threads:
        selected_threads = open_threads[:5]

    world_rules = state_data.get("world", [])[:8]

    return {
        "characters": selected_chars,
        "timeline": selected_timeline,
        "open_threads": selected_threads,
        "world": world_rules,
    }
