"""Continue an isolated authored ideation replay through actual CLI production."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from opencontent import ideation
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.providers import CodexProvider,detect_cli

directory=Path(sys.argv[1]).resolve()
if not directory.is_relative_to(ROOT) or not (directory/'result.json').is_file():
    raise SystemExit('Use an isolated completed replay inside this workspace.')
k=Kernel(directory)
snapshot_files=list((directory/'.opencontent/ideation').glob('*/snapshot.json'))
if len(snapshot_files)!=1:raise SystemExit('Expected exactly one replay snapshot')
snapshot=json.loads(snapshot_files[0].read_text(encoding='utf-8'))
result=json.loads((directory/'result.json').read_text(encoding='utf-8'))
ideation.save(k,snapshot['id'],{'status':'SUCCEEDED','result':result})
p=ideation.create(k,snapshot['id'],result['ideas'][0]['id'])
provider=CodexProvider(next(c['path'] for c in detect_cli() if c['name']=='codex'),timeout=300)
jobs=Jobs(k,{'codex':provider});started=time.monotonic()
job=jobs.submit(p['oc_id'],expected=k.vault.token());previous=None
while True:
    row=next(r for r in jobs.list() if r['id']==job['id'])
    current=(row['status'],row['detail'].get('stage'))
    if current!=previous:print(current,flush=True);previous=current
    if row['status'] not in ('QUEUED','RUNNING'):break
    time.sleep(1)
jobs.close()
objects,errors=k.read()
report={'private_vault_used':False,'model_override':False,'seconds':round(time.monotonic()-started,2),
        'job':row,'diagnostics':errors,'objects':[o for o in objects.values() if o.get('project')==p['oc_id'] and o['type'] in ('Artifact','Review')]}
(directory/'production-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':row['status'],'seconds':report['seconds'],'error':row['detail'].get('error')}),flush=True)
