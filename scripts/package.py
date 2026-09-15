"""Build reviewable archives from an explicit allowlist; never include a user's Vault."""
import hashlib
import json
from pathlib import Path
import zipfile
from release_files import plugin_files
root=Path(__file__).resolve().parent.parent
dist=root/'dist';dist.mkdir(exist_ok=True)
version=json.loads((root/'plugin'/'manifest.json').read_text(encoding='utf-8'))['version']
source_name=f'opencontent-source-{version}.zip'
bundles={
    f'opencontent-plugin-{version}.zip':[p for p,_ in plugin_files(root)],
    source_name:[root/name for name in ('README.md','PRIVACY.md','LICENSE','NOTICE.md','requirements.txt','Connect-WeChat.cmd','OpenContent — Codex Implementation Charter.md')]
}
for directory in ('opencontent','plugin','templates','scripts','tests'):
    bundles[source_name].extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
bundles[source_name].extend(root/'docs'/name for name in (
    'PUBLIC-READINESS.md','TRIAL-QUICKSTART.md','BLOCKERS-v0.8.md','trial-forms/first-use.csv','trial-forms/return-use.csv','trial-forms/host-checks.csv','trial-forms/editorial-review.csv','ARCHITECTURE.md','SCHEMA.md','VALIDATION.md','verification.json','runtime-evidence.json',
    'data-ownership.json','obsidian-interactions.json','obsidian-responsiveness.json',
    'obsidian-board.png','obsidian-inbox.png','obsidian-inspector.png',
    'MARKET-STRATEGY.md','NOTEBOOK-COMPETITION-AND-FULL-LIFECYCLE.md','PILOT-PLAN.md','pilot-observations.csv','VALIDATION-v0.3.md',
    'obsidian-workflow-v0.3.json','obsidian-continue-v0.3.png',
    'LIFECYCLE-IMPLEMENTATION.md','WECHAT-SETUP.md','PRODUCT-EVOLUTION-v0.4.md','VALIDATION-v0.4.md',
    'WECHAT-PERSONAL-ACCOUNT.md','READER-OUTPUT-v0.4.2.md','PROJECT-WORKBENCH-v0.5.md','workbench-runtime-v0.5.json',
    'CORPUS-IDEATION-v0.6.md','ideation-runtime-v0.6.json','ideation-recovery-v0.6.1.json',
    'obsidian-lifecycle-v0.4.json','lifecycle-runtime-v0.4.json','obsidian-publishing-v0.4.png',
    'market-evidence/market-snapshot.json','market-evidence/ailu-audit-manifest.json'))
bundles[source_name].append(root/'docs/market-evidence/wechat-api-sources.json')
report={}
for name,files in bundles.items():
    with zipfile.ZipFile(dist/name,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            relative=dict(plugin_files(root))[file] if name.startswith('opencontent-plugin') else file.relative_to(root).as_posix()
            archive.write(file,relative)
    with zipfile.ZipFile(dist/name) as archive:
        assert archive.testzip() is None
        assert not any('.opencontent' in p or 'validation-vault' in p or 'archive/' in p for p in archive.namelist())
        assert not any('/ailu-audit/' in p for p in archive.namelist())
    report[name]={'sha256':hashlib.sha256((dist/name).read_bytes()).hexdigest(),'files':len(files)}
from package_trial import build
trial=build(root);report[Path(trial['archive']).name]={'sha256':trial['sha256'],'files':trial['files']}
(dist/'SHA256.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
