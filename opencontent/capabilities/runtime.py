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


class CapabilityRuntime:
    """Coordinates pack execution, context assembly, isolated workspaces, and receipts."""

    def __init__(self, kernel, registry: PackRegistry, router: TaskRouter = None, assembler: ContextAssembler = None):
        self.kernel = kernel
        self.registry = registry
        self.router = router or TaskRouter()
        self.assembler = assembler or ContextAssembler()

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

        # Gather relevant sources from project
        project_materials = [o for o in objects.values() if o.get("project") == pid and o.get("type") == "Material"]

        # Read tracking state if existing
        state_path = self.kernel.vault.safe(f"OpenContent/Project/{pid}/state.json")
        state_data = {}
        if state_path.is_file():
            try:
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                state_data = {}

        # Context assembly
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

        # Create isolated run workspace in .opencontent/runs/<run_id>/
        workspace_dir = self.kernel.vault.safe(f".opencontent/runs/{run_id}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        (workspace_dir / "candidate").mkdir(exist_ok=True)
        (workspace_dir / "review").mkdir(exist_ok=True)

        atomic(workspace_dir / "request.json", json.dumps(task_request, ensure_ascii=False, indent=2).encode("utf-8"))
        atomic(workspace_dir / "context.json", json.dumps(context_pkg, ensure_ascii=False, indent=2).encode("utf-8"))

        # Build execution request for Provider
        agent_instructions = (
            f"Execute creative task '{task_name}' for pack '{pack.id}' with profile '{routed['profile_id']}'.\n"
            f"Guidance: {profile.get('guidance', '')}\n"
            f"Task steps: {workflow.get('steps', [])}\n"
            "Treat source materials as reference only. Never modify formal vault files directly. "
            "Return candidate output matching the response schema."
        )

        # Expected response schema based on task
        response_schema = {
            "candidate": {
                "title": "...",
                "body": "Markdown text...",
            },
            "state_delta": {
                "schema": STATE_DELTA_SCHEMA_V1,
                "characters": [],
                "relationships": [],
                "timeline": [],
                "world": [],
                "open_threads": [],
                "resolved_threads": [],
                "new_proposals": [],
            },
            "review": {
                "issues": [],
                "strengths": [],
                "uncertainties": [],
            }
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

        # Resolve provider
        jobs_mgr = getattr(self.kernel, "_jobs", None)
        providers_map = jobs_mgr.providers if jobs_mgr else {}
        p_name = provider_name or (list(providers_map.keys())[0] if providers_map else "fixture")
        provider = providers_map.get(p_name)
        if not provider:
            from opencontent.providers import LocalCodexProvider
            provider = LocalCodexProvider()

        # Run provider execution
        import threading
        cancel_evt = threading.Event()
        try:
            raw_result = provider.run(agent_req, str(workspace_dir), cancel_evt)
        except Exception as e:
            atomic(workspace_dir / "stderr.log", str(e).encode("utf-8"))
            raise Problem(f"Creative execution failed under provider '{p_name}': {e}") from e

        # Validate candidate output
        candidate = raw_result.get("candidate")
        if candidate:
            validate_candidate_output(candidate)

        # Validate state delta
        state_delta = raw_result.get("state_delta")
        if state_delta:
            validate_state_delta(state_delta)

        # Save outputs in isolated workspace
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
