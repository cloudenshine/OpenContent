import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from opencontent.kernel import Kernel
k=Kernel(root/'validation-vault');board=k.board()
with k.vault.connection() as db:
    jobs=[{**dict(row),'detail':json.loads(row['detail'])} for row in db.execute('SELECT * FROM jobs ORDER BY created')]
projects=[]
for p in board['projects']:
    projects.append({'id':p['oc_id'],'title':p['title'],'state':p['state'],'effective_state':p['effective_state'],'counts':p['counts'],
                     'history':p['history'],'artifacts':[{'id':a['oc_id'],'title':a['title'],'gate':a['gate']['status'],'issues':a['gate']['issues'],'approved':a['gate']['approved'],'context_hash':a['gate']['context_hash'],'axes':a['gate']['axes']} for a in p['artifacts']]})
result={'at':datetime.now(timezone.utc).isoformat(),'projects':projects,'jobs':jobs,'diagnostics':board['diagnostics'],
        'run_files':{str(p.relative_to(k.vault.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (k.vault.runtime/'runs').rglob('*.json')},
        'markdown_files':{str(p.relative_to(k.vault.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in k.vault.content.rglob('*.md')}}
(root/'docs'/'runtime-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'projects':len(projects),'jobs':len(jobs),'diagnostics':board['diagnostics']},ensure_ascii=False))
