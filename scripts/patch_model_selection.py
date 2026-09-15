from pathlib import Path
import re

providers_path = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\providers.py")
text = providers_path.read_text(encoding="utf-8")

# 1. Update Codex command
old_codex_cmd = """    def command(self,request,output):
        sandbox='workspace-write' if request.get('stage')=='illustrate' else 'read-only'
        return [str(self.executable), 'exec', '--skip-git-repo-check', '--sandbox', sandbox,
                '--ephemeral', '--output-last-message', str(output), '-']"""

new_codex_cmd = """    def command(self,request,output):
        sandbox='workspace-write' if request.get('stage')=='illustrate' else 'read-only'
        cmd = [str(self.executable), 'exec', '--skip-git-repo-check', '--sandbox', sandbox]
        model = getattr(self, 'model', None) or request.get('model')
        if model:
            cmd.extend(['-c', f'model="{model}"'])
        cmd.extend(['--ephemeral', '--output-last-message', str(output), '-'])
        return cmd"""

if old_codex_cmd in text:
    text = text.replace(old_codex_cmd, new_codex_cmd)

# 2. Update Claude command
old_claude_cmd = """    def command(self,request,output):
        return [str(self.executable),'--print','--output-format','text','--tools','',
                '--permission-mode','dontAsk','--no-session-persistence']"""

new_claude_cmd = """    def command(self,request,output):
        cmd = [str(self.executable), '--print', '--output-format', 'text', '--tools', '',
               '--permission-mode', 'dontAsk', '--no-session-persistence']
        model = getattr(self, 'model', None) or request.get('model')
        if model:
            cmd.extend(['--model', str(model)])
        return cmd"""

if old_claude_cmd in text:
    text = text.replace(old_claude_cmd, new_claude_cmd)

# 3. Update activate_cli & bootstrap_cli
old_activate = """def activate_cli(jobs,name):
    if jobs.running:raise Problem('请等待运行任务结束后切换 CLI',409)
    selected=next((p for p in detect_cli() if p['name']==name),None)
    if not selected:raise Problem('未发现支持的本地原生 CLI；请先安装并在终端登录')
    provider=(CodexProvider if name=='codex' else ClaudeProvider)(selected['path'],timeout=300)
    jobs.providers[name]=provider
    atomic(jobs.kernel.vault.safe('.opencontent/cli-selection.json'),json.dumps(selected).encode())
    return {'name':name,'capabilities':provider.capabilities()}"""

new_activate = """def activate_cli(jobs,name,model=None):
    if jobs.running:raise Problem('请等待运行任务结束后切换 CLI',409)
    selected=next((p for p in detect_cli() if p['name']==name),None)
    if not selected:raise Problem('未发现支持的本地原生 CLI；请先安装并在终端登录')
    provider=(CodexProvider if name=='codex' else ClaudeProvider)(selected['path'],timeout=300)
    if model:
        provider.model = str(model).strip()
        selected['model'] = str(model).strip()
    jobs.providers[name]=provider
    atomic(jobs.kernel.vault.safe('.opencontent/cli-selection.json'),json.dumps(selected).encode())
    return {'name':name,'model':getattr(provider,'model',None),'capabilities':provider.capabilities()}"""

if old_activate in text:
    text = text.replace(old_activate, new_activate)

# 4. Update bootstrap_cli
old_bootstrap = """        if selection.exists():
            name=json.loads(selection.read_text(encoding='utf-8'))['name']
        else:
            candidates=detect_cli()
            if not candidates:
                return '未找到本地写作助手。请安装并登录 Codex 或 Claude，然后重新连接。'
            name=candidates[0]['name']
        activate_cli(jobs,name)"""

new_bootstrap = """        saved_model = None
        if selection.exists():
            sel_data = json.loads(selection.read_text(encoding='utf-8'))
            name = sel_data.get('name')
            saved_model = sel_data.get('model')
        else:
            candidates=detect_cli()
            if not candidates:
                return '未找到本地写作助手。请安装并登录 Codex 或 Claude，然后重新连接。'
            name=candidates[0]['name']
        activate_cli(jobs,name,model=saved_model)"""

if old_bootstrap in text:
    text = text.replace(old_bootstrap, new_bootstrap)

providers_path.write_text(text, encoding="utf-8")
print("providers.py successfully patched for dynamic model selection!")
