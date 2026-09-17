"""One explicit runtime allowlist for installation and plugin archives."""
from pathlib import Path
import json
import re

def plugin_files(root):
    root=Path(root)
    files=[(root/'plugin'/n,n) for n in ('main.js','manifest.json','styles.css')] + [(p,'engine/'+p.name) for p in sorted((root/'plugin/engine').glob('*.js'))]
    files += [(p,'kernel/opencontent/'+p.relative_to(root/'opencontent').as_posix()) for p in sorted((root/'opencontent').rglob('*.py')) if '__pycache__' not in p.parts]
    if (root/'packs').is_dir():
        files += [(p,'kernel/packs/'+p.relative_to(root/'packs').as_posix()) for p in sorted((root/'packs').rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    files += [(root/'templates/CONTENT.md','kernel/templates/CONTENT.md'),(root/'scripts/doctor.py','kernel/doctor.py')]
    files += [(root/n,'kernel/'+n) for n in ('requirements.txt','LICENSE','PRIVACY.md')]
    for source,_ in files:
        if not source.is_file() or source.is_symlink():raise ValueError('Missing or linked release file: '+str(source))
    return files


def installed_runtime(root):
    version=json.loads((Path(root)/'plugin/manifest.json').read_text(encoding='utf-8'))['version']
    if not isinstance(version,str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):raise ValueError('Invalid runtime version')
    return 'kernel-'+version


def installed_files(root):
    runtime=installed_runtime(root)
    return [(source,runtime+'/'+name[len('kernel/'):] if name.startswith('kernel/') else name) for source,name in plugin_files(root)]

