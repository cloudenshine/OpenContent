"""Context Assembler for Creative Capability Tasks."""
from typing import Dict, List, Any, Optional
import json
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
        if not isinstance(task,str) or not isinstance(instruction,str) or not isinstance(project,dict):raise Problem('Context task, instruction and project have invalid types')
        for name,value in (('artifact',artifact),('profile',profile),('state_data',state_data),('constraints',constraints)):
            if value is not None and not isinstance(value,dict):raise Problem('Context '+name+' must be an object')
        if project.get('type','Project')!='Project':raise Problem('Context project must be Project')
        if artifact is not None:
            if artifact.get('type','Artifact')!='Artifact' or not isinstance(artifact.get('body',''),str):raise Problem('Context target must be an Artifact with text')
            if artifact.get('project') is not None and artifact['project']!=project.get('oc_id'):raise Problem('Context artifact belongs to another project')
        profile = profile or {}
        sources = sources or []
        state_data = state_data or {}
        constraints = constraints or {}
        if set(constraints)-{'must_preserve','must_not_do'}:raise Problem('Unsupported context constraints')
        for owner,fields in ((constraints,('must_preserve','must_not_do')),(profile,('invariants','forbidden','creative_freedom'))):
            for field in fields:
                if field in owner and (not isinstance(owner[field],list) or any(not isinstance(item,str) for item in owner[field])):raise Problem('Context '+field+' must be a text list')
        for field in ('characters','world','timeline','open_threads','relationships'):
            if field in state_data and not isinstance(state_data[field],list):raise Problem('Context state '+field+' must be a list')

        if not isinstance(sources,list):raise Problem('Context sources must be a list')
        for source in sources:
            if not isinstance(source,dict) or not isinstance(source.get('body'),str) or not source['body'].strip():
                raise Problem('Context sources require complete original text')
            if source.get('type','Material')!='Material':raise Problem('Only original Material is factual source context')
            if source.get('project') is not None and source['project']!=project.get('oc_id'):
                raise Problem('Context source belongs to another project')
            allowed={'oc_id','type','title','body','source','source_url','project','created','derived_from','path','hash','role','capture_hash','source_note_hash','versions','reused_from','execution','provenance'}
            if set(source)-allowed:raise Problem('Unsupported source context fields')
            for field in ('oc_id','title','source','source_url','role'):
                if field in source and not isinstance(source[field],str):raise Problem('Context source '+field+' must be text')
            if source.get('source','').lower().startswith(('assistant:','agent:','model:','discussion:')):raise Problem('Model discussion is not original source evidence')
            if source.get('role','reference') not in ('reference','primary','background','evidence'):raise Problem('Unsupported source evidence role')
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
            excerpt = s_body
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

        package['omissions'] = {
            'characters': len(all_chars)-len(selected_chars),
            'timeline': max(0,len(all_timeline)-len(selected_timeline)),
            'world': max(0,len(all_rules)-len(relevant_state['world'])),
            'sources': 0,
        }
        if not isinstance(budget_limit,int) or isinstance(budget_limit,bool) or budget_limit <= 0:
            raise Problem('Context budget_limit must be a positive byte limit')
        # Byte accounting includes provenance, omissions, and the budget receipt.
        package['budget'] = {'limit':budget_limit,'bytes':0,'unit':'utf8-bytes'}
        for _ in range(5):
            size=len(json.dumps(package,ensure_ascii=False).encode('utf-8'))
            if size==package['budget']['bytes']:break
            package['budget']['bytes']=size
        if package['budget']['bytes'] > budget_limit:
            raise Problem('Required context/evidence exceeds budget; reduce scope explicitly, no evidence was silently dropped')
        return package
