"""Run only while the validation kernel/plugin is stopped. Preserve every database."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from opencontent.kernel import Kernel
from opencontent.vault import digest, now
root=Path(__file__).resolve().parent.parent
vault=root/'validation-vault';runtime=vault/'.opencontent'
db=runtime/'runtime.sqlite3';backup=runtime/'runtime-before-rebuild.sqlite3';rebuilt=runtime/'rebuilt-empty.sqlite3'
if backup.exists() or rebuilt.exists():raise SystemExit('Rebuild evidence files already exist; do not overwrite')
if (vault/'.obsidian'/'plugins'/'opencontent').exists():raise SystemExit('Move disabled plugin out of installation directory first')
before={str(p.relative_to(vault)):digest(p.read_bytes()) for p in (vault/'OpenContent').rglob('*.md')}
db.rename(backup)
try:
    k=Kernel(vault);board=k.board()
    after={str(p.relative_to(vault)):digest(p.read_bytes()) for p in (vault/'OpenContent').rglob('*.md')}
    assert before==after
    assert len(board['projects'])==2
    assert next(p for p in board['projects'] if p['title'].startswith('真实 Agent'))['effective_state']=='REVIEWING'
    assert next(p for p in board['projects'] if p['title'].startswith('软件门禁'))['artifacts'][0]['gate']['approved']
    result={'at':now(),'plugin_installed':False,'runtime_rebuilt':True,'markdown_files_unchanged':len(before),
            'projects':[{'id':p['oc_id'],'title':p['title'],'state':p['effective_state']} for p in board['projects']],
            'diagnostics':board['diagnostics'],'file_hashes':before}
    (root/'docs'/'data-ownership.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='file_hashes'},ensure_ascii=False))
finally:
    if db.exists():db.rename(rebuilt)
    backup.rename(db)
