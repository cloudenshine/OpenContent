"""Capability Runtime orchestrator for executing creative tasks."""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

from opencontent.vault import Problem, atomic, now, digest
from opencontent.jobs import Jobs
from .contracts import (
    TASK_SCHEMA_V1,
    CANDIDATE_SCHEMA_V1,
    STATE_DELTA_SCHEMA_V1,
    EXECUTION_PROFILES,
)
from .registry import PackRegistry
from .router import TaskRouter
from .context import ContextAssembler
from .validation import (
    validate_workspace_path,
    validate_state_delta,
    validate_candidate_output,
)
from .market import LongMarketAnalyzer, ShortMarketAnalyzer
from .deconstruction import StoryDeconstructor
from .media import MediaGenerationAdapter


class CapabilityRuntime:
    """Coordinates pack execution, context assembly, isolated workspaces, and receipts."""

    def __init__(self, kernel, registry: PackRegistry, router: TaskRouter = None, assembler: ContextAssembler = None):
        self.kernel = kernel
        self.registry = registry
        self.router = router or TaskRouter()
        self.assembler = assembler or ContextAssembler()
        self.long_market = LongMarketAnalyzer(kernel)
        self.short_market = ShortMarketAnalyzer(kernel)
        self.deconstructor = StoryDeconstructor(kernel)
        self.media_adapter = MediaGenerationAdapter(kernel)

    def execute_task(
        self,
        task_request: Dict[str, Any],
        provider_name: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a creative task within an isolated run workspace."""
        start_time = time.monotonic()
        run_id = run_id or uuid.uuid4().hex
        pid = task_request.get("project")
        if not pid:
            raise Problem("Task request requires 'project' ID")

        objects, errors = self.kernel.read()
        if pid not in objects or objects[pid]["type"] != "Project":
            raise Problem(f"Project not found: {pid}")
        project = objects[pid]

        # Route task to pack, profile, workflow
        routed = self.router.route(task_request, self.registry)
        pack = routed["pack"]
        profile = routed["profile"]
        workflow = routed["workflow"]
        task_name = routed["task"]

        # Target artifact resolution
        target_aid = task_request.get("artifact")
        target_artifact = objects.get(target_aid) if target_aid else None

        # 1. Specialized Market Scan Tasks
        if task_name == "long-scan":
            raw_data = task_request.get("raw_data")
            if not raw_data:
                # Default sample seed if none passed
                raw_data = {
                    "qidian": [
                        {"rank": 1, "title": "宿命之环", "author": "爱潜水的乌贼", "genre": "玄幻", "words": 280, "recommendation": 500000, "intro": "诡秘世界第二部，蒸汽与神秘的再次交织。"},
                        {"rank": 2, "title": "赤心巡天", "author": "情何以甚", "genre": "仙侠", "words": 420, "recommendation": 450000, "intro": "上古时代，妖族绝迹，少年拔剑起于微末。"},
                        {"rank": 3, "title": "道诡异仙", "author": "狐尾的笔", "genre": "悬疑", "words": 190, "recommendation": 400000, "intro": "诡异修仙，心素迷茫，现实与幻觉交替。"},
                    ]
                }
            report = self.long_market.analyze(raw_data, scan_id=run_id)
            return {"receipt": {"run_id": run_id, "task": "long-scan", "status": "SUCCEEDED", "at": now()}, "market_report": report}

        if task_name == "short-scan":
            raw_data = task_request.get("raw_data")
            if not raw_data:
                raw_data = {
                    "zhihu": [
                        {"rank": 1, "title": "洗冤录：法医妻子的一份报告", "author": "冷月", "genre": "刑侦", "words": 1.2, "reads": 88000, "emotional_hook": "专业复仇 / 伦理反转", "reversal_type": "物证翻转", "intro": "作为首席法医，在解剖台前我认出了那块特殊的腕表。"},
                        {"rank": 2, "title": "退婚后我成了前夫的小舅妈", "author": "晚风", "genre": "言情", "words": 1.5, "reads": 92000, "emotional_hook": "决绝离开 / 全员打脸", "reversal_type": "身份反转", "intro": "签字离婚那天，我没有流一滴泪。"},
                    ]
                }
            report = self.short_market.analyze(raw_data, scan_id=run_id)
            return {"receipt": {"run_id": run_id, "task": "short-scan", "status": "SUCCEEDED", "at": now()}, "market_report": report}

        # 2. Specialized Deconstruction Tasks
        if task_name == "long-analyze":
            title = task_request.get("title", project["title"])
            chapters = task_request.get("chapters", [
                {"title": "第一章", "body": target_artifact.get("body", "") if target_artifact else "开篇建立主角身处困境的严酷现实，不可调和的矛盾前置。"}
            ])
            res = self.deconstructor.deconstruct_long(title, chapters, task_request.get("platform", "qidian"), deconstruct_id=run_id)
            return {"receipt": {"run_id": run_id, "task": "long-analyze", "status": "SUCCEEDED", "at": now()}, **res}

        if task_name == "short-analyze":
            title = task_request.get("title", project["title"])
            text = task_request.get("text") or (target_artifact.get("body", "") if target_artifact else "前言交代极速冲突。开局三句内亮出物证，主角不再妥协，直接公布对方隐瞒的真相，情节瞬间翻转。")
            res = self.deconstructor.deconstruct_short(title, text, task_request.get("platform", "zhihu"), deconstruct_id=run_id)
            return {"receipt": {"run_id": run_id, "task": "short-analyze", "status": "SUCCEEDED", "at": now()}, **res}

        # 3. Specialized Cover Presentation Task
        if task_name == "cover":
            title = task_request.get("title", project["title"])
            genre = task_request.get("genre", "通用")
            platform = task_request.get("platform", "general")
            res = self.media_adapter.generate_cover_candidates(pid, title, project.get("author", "作者"), genre, project.get("goal", ""), platform)
            return {"receipt": {"run_id": run_id, "task": "cover", "status": "SUCCEEDED", "at": now()}, **res}

        # 4. Standard Agent Creative Workflows (plan, write, continue, revise, critique)
        project_materials = [o for o in objects.values() if o.get("project") == pid and o.get("type") == "Material"]
        state_path = self.kernel.vault.safe(f"OpenContent/Project/{pid}/state.json")
        state_data = {}
        if state_path.is_file():
            try:
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                state_data = {}

        context_pkg = self.assembler.assemble(
            task=task_name,
            instruction=task_request.get("instruction", ""),
            project=project,
            artifact=target_artifact,
            profile=profile,
            sources=project_materials,
            state_data=state_data,
            constraints=task_request.get("constraints", {}),
        )

        workspace_dir = self.kernel.vault.safe(f".opencontent/runs/{run_id}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "candidate").mkdir(exist_ok=True)
        (workspace_dir / "review").mkdir(exist_ok=True)

        atomic(workspace_dir / "request.json", json.dumps(task_request, ensure_ascii=False, indent=2).encode("utf-8"))
        atomic(workspace_dir / "context.json", json.dumps(context_pkg, ensure_ascii=False, indent=2).encode("utf-8"))

        agent_instructions = (
            f"Execute creative task '{task_name}' for pack '{pack.id}' with profile '{routed['profile_id']}'.\n"
            f"Guidance: {profile.get('guidance', '')}\n"
            f"Task steps: {workflow.get('steps', [])}\n"
            "Treat source materials as reference only. Never modify formal vault files directly. "
            "Return candidate output matching the response schema."
        )

        response_schema = {
            "candidate": {"title": "...", "body": "Markdown text..."},
            "state_delta": {
                "schema": STATE_DELTA_SCHEMA_V1,
                "characters": [], "relationships": [], "timeline": [], "world": [],
                "open_threads": [], "resolved_threads": [], "new_proposals": [],
            },
            "review": {"issues": [], "strengths": [], "uncertainties": []}
        }

        agent_req = {
            "protocol": "opencontent.creative-run.v1",
            "run_id": run_id,
            "project": project,
            "task": task_name,
            "pack": pack.id,
            "pack_version": pack.version,
            "profile": routed["profile_id"],
            "context": context_pkg,
            "token": self.kernel.vault.token(),
            "response_schema": response_schema,
            "instructions": agent_instructions,
        }

        jobs_mgr = getattr(self.kernel, "_jobs", None)
        providers_map = jobs_mgr.providers if jobs_mgr else {}
        p_name = provider_name or (list(providers_map.keys())[0] if providers_map else "fixture")
        provider = providers_map.get(p_name)
        if not provider:
            from opencontent.providers import LocalCodexProvider
            provider = LocalCodexProvider()

        import threading
        cancel_evt = threading.Event()
        try:
            raw_result = provider.run(agent_req, str(workspace_dir), cancel_evt)
        except Exception as e:
            atomic(workspace_dir / "stderr.log", str(e).encode("utf-8"))
            raise Problem(f"Creative execution failed under provider '{p_name}': {e}") from e

        candidate = raw_result.get("candidate")
        if candidate:
            validate_candidate_output(candidate)

        state_delta = raw_result.get("state_delta")
        if state_delta:
            validate_state_delta(state_delta)

        if candidate:
            atomic(workspace_dir / "candidate" / "artifact.json", json.dumps(candidate, ensure_ascii=False, indent=2).encode("utf-8"))
        if state_delta:
            atomic(workspace_dir / "state-delta.json", json.dumps(state_delta, ensure_ascii=False, indent=2).encode("utf-8"))

        duration = time.monotonic() - start_time
        receipt = {
            "run_id": run_id,
            "project": pid,
            "task": task_name,
            "pack": pack.id,
            "pack_version": pack.version,
            "profile": routed["profile_id"],
            "provider": p_name,
            "duration_seconds": round(duration, 3),
            "status": "SUCCEEDED",
            "at": now(),
            "context_items_count": len(context_pkg.get("provenance", [])),
            "has_candidate": bool(candidate),
            "has_state_delta": bool(state_delta),
        }
        atomic(workspace_dir / "receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8"))

        return {
            "receipt": receipt,
            "candidate": candidate,
            "state_delta": state_delta,
            "review": raw_result.get("review"),
            "context": context_pkg,
        }
