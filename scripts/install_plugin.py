"""Install a portable kernel beside the thin plugin; preserve settings and backups."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime
from release_files import installed_files, installed_runtime

parser=argparse.ArgumentParser()
parser.add_argument('--vault',required=True)
parser.add_argument('--config-dir',default='.obsidian',help='Existing Vault-relative Obsidian configuration directory')
parser.add_argument('--configure',action='store_true',help='Use the bundled kernel and this Python, preserving other settings')
parser.add_argument('--codex')
parser.add_argument('--live-safe',action='store_true',help='Install into a fresh runtime directory without moving a running kernel')
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
vault=Path(args.vault).resolve()
config_relative=Path(args.config_dir)
if config_relative.is_absolute() or '..' in config_relative.parts or config_relative == Path('.'):
    raise SystemExit('Configuration directory must be a nonempty Vault-relative path without traversal')
config_directory=vault/config_relative
if not config_directory.resolve().is_relative_to(vault):
    raise SystemExit('Configuration directory escapes Vault')
if not vault.is_dir() or not config_directory.is_dir():
    raise SystemExit('Target must be an existing Obsidian Vault with the selected configuration directory; no new Vault will be created')
dest=config_directory/'plugins/opencontent'
def inside(p):
    if not p.is_relative_to(vault) or not p.resolve().is_relative_to(vault):raise SystemExit('Install path escapes Vault: '+str(p))
    for component in (p,*p.parents):
        if component==vault:break
        if component.is_symlink() or component.is_junction():raise SystemExit('Install path is linked: '+str(component))
    return p
inside(dest);inside(vault/'.opencontent/install-backups')
runtime=installed_runtime(root)
payload=installed_files(root)
if args.live_safe:
    if not args.configure:raise SystemExit('--live-safe requires --configure')
    previous_runtime=runtime
    runtime+='-'+datetime.now().strftime('%Y%m%d%H%M%S%f')
    payload=[(source,runtime+relative[len(previous_runtime):] if relative.startswith(previous_runtime+'/') else relative) for source,relative in payload]
config=dest/'data.json';settings=json.loads(config.read_text(encoding='utf-8-sig')) if config.is_file() else {}
dest.mkdir(parents=True,exist_ok=True)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup=inside(vault/'.opencontent/install-backups'/stamp)
names=['main.js','manifest.json','styles.css','engine',runtime]+(['data.json'] if args.configure else [])
for name in names:inside(dest/name)
with tempfile.TemporaryDirectory(prefix='.install-',dir=dest) as temporary:
    stage=inside(Path(temporary))
    for source,relative in payload:
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    if args.configure:
        settings.update(kernelPath=str(dest/runtime),python=sys.executable)
        if args.codex:settings['codex']=str(Path(args.codex).resolve())
        (stage/'data.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
    installed=[];saved=[]
    try:
        for name in names:
            target=dest/name
            if target.exists():
                backup.mkdir(parents=True,exist_ok=True)
                # Both resolved locations were checked inside the explicitly selected Vault.
                os.replace(target,backup/name);saved.append(name)
            os.replace(stage/name,target);installed.append(name)
    except BaseException:
        for name in reversed(installed):os.replace(dest/name,stage/('failed-'+name))
        for name in reversed(saved):os.replace(backup/name,dest/name)
        raise
print(json.dumps({'installed':str(dest),'kernel':str(dest/runtime),'previous_runtime_retained':True,'backup':str(backup) if backup.exists() else None},ensure_ascii=False))

