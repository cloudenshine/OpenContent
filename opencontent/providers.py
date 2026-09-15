"""Replaceable execution boundary; providers never own domain objects."""
from abc import ABC, abstractmethod
import json
from pathlib import Path
import subprocess
import time
import os
import shutil
from .processes import ProcessGroup
from .vault import Problem, atomic


class AgentExecutionProvider(ABC):
    @abstractmethod
    def capabilities(self): ...

    @abstractmethod
    def run(self, request, workspace, cancel_event): ...

    def resume(self, request, workspace, cancel_event, previous):
        """Explicit retry against fresh input, not an invented native session."""
        return self.run(request, workspace, cancel_event)

    def cancel(self, cancel_event):
        cancel_event.set()


def discover_skills(roots):
    found = []
    for root in roots:
        root = Path(root).resolve()
        paths = [root] if root.is_file() and root.name == "SKILL.md" else sorted(root.glob("*/SKILL.md"))
        if (root / "SKILL.md").is_file():
            paths.insert(0, root / "SKILL.md")
        for path in paths:
            if path.is_symlink() or path.stat().st_size > 50_000:
                continue
            found.append({"path": str(path), "content": path.read_text(encoding="utf-8")})
            if len(found) >= 8:
                return found
    return found


class CodexProvider(AgentExecutionProvider):
    def __init__(self, executable, timeout=180):
        self.executable = Path(executable).resolve()
        if not self.executable.is_file() or self.executable.suffix.lower() in (".cmd", ".bat", ".ps1", ".sh"):
            raise Problem("Codex adapter requires a native executable")
        self.timeout = timeout

    def capabilities(self):
        return {"read": True, "write": False, "reason": True, "tools": "illustration-workspace-only", "web": False,
                "skills": True, "session": False, "project_history":True,
                "image_generation":"runtime-dependent", "resume": "fresh-attempt", "cancel": True}

    def command(self,request,output):
        sandbox='workspace-write' if request.get('stage')=='illustrate' else 'read-only'
        cmd = [str(self.executable), 'exec', '--skip-git-repo-check', '--sandbox', sandbox]
        model = getattr(self, 'model', None) or request.get('model')
        if model:
            cmd.extend(['-c', f'model="{model}"'])
        cmd.extend(['--ephemeral', '--output-last-message', str(output), '-'])
        return cmd

    def run(self, request, workspace, cancel_event):
        workspace = Path(workspace)
        output = workspace / "response.json"
        prompt = json.dumps(request, ensure_ascii=False).encode("utf-8")
        atomic(workspace / "request.json", prompt)
        argv = self.command(request,output)
        timeout=max(self.timeout,480) if request.get('stage')=='illustrate' else max(self.timeout,300) if request.get('stage') in ('classify','synthesize') else self.timeout
        # File-backed IO avoids pipe deadlocks and prevents unbounded memory growth.
        with (workspace / "request.json").open("rb") as stdin, (workspace / "stdout.log").open("wb") as stdout, (workspace / "stderr.log").open("wb") as stderr, ProcessGroup() as group:
            process = group.start(argv, stdin=stdin, stdout=stdout, stderr=stderr, cwd=workspace)
            start = time.monotonic()
            try:
                while process.poll() is None:
                    if cancel_event.wait(.1):
                        raise Problem("Agent execution cancelled")
                    if time.monotonic() - start > timeout:
                        raise Problem(f"Agent timed out after {timeout}s")
                    if any(p.stat().st_size > 2_000_000 for p in (workspace / "stdout.log", workspace / "stderr.log", output) if p.exists()):
                        raise Problem("Agent output limit exceeded")
                if process.returncode:
                    raise Problem(f"Agent exited {process.returncode}; inspect stderr.log")
            finally:
                group.close()
                process.wait(timeout=10)
        if isinstance(self,ClaudeProvider):output=workspace/'stdout.log'
        if not output.exists() or output.stat().st_size > 1_000_000:
            raise Problem("Agent did not produce a bounded JSON response")
        from .json_cleaner import robust_extract_json
        raw_text = output.read_text(encoding="utf-8").strip()
        try:
            return robust_extract_json(raw_text)
        except Exception as e:
            raise Problem("Agent final response is not valid JSON: " + str(e)) from e


class ClaudeProvider(CodexProvider):
    def capabilities(self):
        return {**super().capabilities(),'tools':False,'image_generation':False}

    def command(self,request,output):
        cmd = [str(self.executable), '--print', '--output-format', 'text', '--tools', '',
               '--permission-mode', 'dontAsk', '--no-session-persistence']
        model = getattr(self, 'model', None) or request.get('model')
        if model:
            cmd.extend(['--model', str(model)])
        return cmd


def detect_cli():
    candidates={'codex':[], 'claude':[]}
    for name in candidates:
        located=shutil.which(name+'.exe' if os.name=='nt' else name)
        if located:candidates[name].append(Path(located))
    local=Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))
    candidates['codex'].extend(sorted((local/'OpenAI/Codex/bin').glob('*/codex.exe'),key=lambda p:p.stat().st_mtime,reverse=True))
    candidates['claude'].append(Path.home()/'.local/bin/claude.exe')
    return [{'name':name,'path':str(next(p for p in paths if p.is_file()))}
            for name,paths in candidates.items() if any(p.is_file() for p in paths)]


def activate_cli(jobs,name,model=None):
    if jobs.running:raise Problem('请等待运行任务结束后切换 CLI',409)
    selected=next((p for p in detect_cli() if p['name']==name),None)
    if not selected:raise Problem('未发现支持的本地原生 CLI；请先安装并在终端登录')
    provider=(CodexProvider if name=='codex' else ClaudeProvider)(selected['path'],timeout=300)
    if model:
        provider.model = str(model).strip()
        selected['model'] = str(model).strip()
    jobs.providers[name]=provider
    atomic(jobs.kernel.vault.safe('.opencontent/cli-selection.json'),json.dumps(selected).encode())
    return {'name':name,'model':getattr(provider,'model',None),'capabilities':provider.capabilities()}


def bootstrap_cli(jobs):
    """Reuse explicit settings first; first use needs no separate enable click.

    Discovery only locates an executable. Authentication is verified by the first
    requested task, never by sending a hidden model prompt during startup.
    """
    if jobs.providers:
        return None
    selection=jobs.kernel.vault.safe('.opencontent/cli-selection.json')
    try:
        saved_model = None
        if selection.exists():
            sel_data = json.loads(selection.read_text(encoding='utf-8'))
            name = sel_data.get('name')
            saved_model = sel_data.get('model')
        else:
            candidates=detect_cli()
            if not candidates:
                return '未找到本地写作助手。请安装并登录 Codex 或 Claude，然后重新连接。'
            name=candidates[0]['name']
        activate_cli(jobs,name,model=saved_model)
        return None
    except (Problem,ValueError,KeyError,TypeError,OSError):
        return '之前选择的写作助手暂不可用。请检查连接设置；不会自动换用其他工具。'
