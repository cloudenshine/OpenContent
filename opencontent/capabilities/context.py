"""Context Assembler for Creative Capability Tasks."""
from typing import Dict, List, Any, Optional
from opencontent.vault import Problem
from .contracts import CONTEXT_SCHEMA_V1


class ContextAssembler:
    """Assembles structured, bounded, prioritized Context Package for creative tasks."""

    def assemble(
        self,
        task: str,
        instruction: str,
        project: Dict[str, Any],
        artifact: Optional[Dict[str, Any]] = None,
        profile: Optional[Dict[str, Any]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        state_data: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        budget_limit: int = 120000,
    ) -> Dict[str, Any]:
        profile = profile or {}
        sources = sources or []
        state_data = state_data or {}
        constraints = constraints or {}

        provenance = []

        # 1. P0: Intent and Instruction
        intent = {
            "task": task,
            "instruction": instruction.strip(),
            "goal": project.get("goal", ""),
            "audience": project.get("audience", ""),
            "thesis": project.get("thesis", ""),
        }
        provenance.append({
            "target": "intent",
            "source_type": "Project",
            "source_id": project.get("oc_id", ""),
            "priority": "P0",
            "category": "instruction",
            "reason": "Explicit user task and project goals",
        })

        # 2. P0: Current Artifact target
        current_artifact_ctx = {}
        if artifact:
            current_artifact_ctx = {
                "oc_id": artifact.get("oc_id"),
                "title": artifact.get("title"),
                "body": artifact.get("body", ""),
                "state": artifact.get("state"),
                "version": artifact.get("version", 1),
            }
            provenance.append({
                "target": "current_artifact",
                "source_type": "Artifact",
                "source_id": artifact.get("oc_id", ""),
                "priority": "P0",
                "category": "artifact",
                "reason": "Target draft for continuation, revision, or critique",
            })

        # 3. P0: Must Preserve & Must Not Do
        must_preserve = list(constraints.get("must_preserve", []))
        must_not_do = list(constraints.get("must_not_do", []))

        # Profile invariants added to constraints
        if profile.get("invariants"):
            must_preserve.extend(profile["invariants"])
        if profile.get("forbidden"):
            must_not_do.extend(profile["forbidden"])

        provenance.append({
            "target": "constraints",
            "source_type": "Profile",
            "source_id": profile.get("id", "default"),
            "priority": "P0",
            "category": "setting",
            "reason": "Profile rules, continuity boundaries, and negative constraints",
        })

        # 4. P1: Relevant state (characters, timeline, world rules)
        # Select selectively based on mention in instruction, current artifact or active threads
        all_chars = state_data.get("characters", [])
        all_rules = state_data.get("world", [])
        all_timeline = state_data.get("timeline", [])
        all_threads = state_data.get("open_threads", [])

        # Priority filtering: only include characters mentioned in instruction, artifact, or explicitly marked active
        search_corpus = (instruction + " " + (artifact.get("body", "") if artifact else "")).lower()
        selected_chars = []
        for c in all_chars:
            c_name = c.get("name", "").lower()
            if not c_name or c_name in search_corpus or c.get("active", False):
                selected_chars.append(c)
                provenance.append({
                    "target": f"character:{c.get('name')}",
                    "source_type": "StateData",
                    "source_id": c.get("id", c.get("name")),
                    "priority": "P1",
                    "category": "setting",
                    "reason": "Active or mentioned character in current scope",
                })

        # Timeline: only recent or relevant events
        selected_timeline = all_timeline[-5:] if len(all_timeline) > 5 else all_timeline
        if selected_timeline:
            provenance.append({
                "target": "timeline",
                "source_type": "StateData",
                "source_id": "timeline",
                "priority": "P1",
                "category": "fact",
                "reason": "Recent chronological milestones",
            })

        relevant_state = {
            "characters": selected_chars,
            "relationships": state_data.get("relationships", []),
            "timeline": selected_timeline,
            "world": all_rules[:10],
        }

        # 5. P1: Sources with explicit provenance
        selected_sources = []
        for s in sources:
            s_body = s.get("body", "")
            excerpt = s_body if len(s_body) <= 2000 else s_body[:2000] + "\n[...]"
            selected_sources.append({
                "oc_id": s.get("oc_id"),
                "title": s.get("title"),
                "source": s.get("source"),
                "excerpt": excerpt,
                "role": s.get("role", "reference"),
            })
            provenance.append({
                "target": f"source:{s.get('oc_id')}",
                "source_type": "Material",
                "source_id": s.get("oc_id", ""),
                "priority": "P1",
                "category": "fact",
                "reason": "Referenced factual or background material",
            })

        # 6. Style & Freedom
        style = {
            "tone": profile.get("tone", "narrative"),
            "voice": profile.get("voice", "third-person limited"),
            "guidance": profile.get("guidance", ""),
        }
        freedom = profile.get("creative_freedom", [
            "Pacing and scene staging",
            "Dialogue phrasing and subtext",
            "Sensory descriptions and imagery",
        ])

        package = {
            "schema": CONTEXT_SCHEMA_V1,
            "task": task,
            "intent": intent,
            "current_artifact": current_artifact_ctx,
            "must_preserve": must_preserve,
            "must_not_do": must_not_do,
            "relevant_state": relevant_state,
            "open_threads": all_threads,
            "sources": selected_sources,
            "style": style,
            "freedom": freedom,
            "provenance": provenance,
        }

        return package
