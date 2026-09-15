"""Archive only projects identified by this turn's synthetic UI acceptance receipt."""
import json
from pathlib import Path
import shutil
import sys
root=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(root))
from opencontent.kernel import Kernel
vault=(root/'validation-vault').resolve();report=json.loads((root/'docs/obsidian-lifecycle-v0.4.json').read_text(encoding='utf-8'))
pids={report['project'],report['next_project']};k=Kernel(vault);objects,_=k.read();moved=[]
for pid in pids:
 assert objects[pid]['title'].startswith('v0.4 '), 'Only synthetic fixture projects may be archived'
for obj in objects.values():
 if obj['oc_id'] not in pids and obj.get('project') not in pids:continue
 src=(vault/obj['path']).resolve();dest=(vault/'_Validation-History'/'v0.4'/obj['type']/src.name).resolve()
 assert src.is_relative_to(vault/'OpenContent') and dest.is_relative_to(vault/'_Validation-History'/'v0.4')
 assert not dest.exists()
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(src),str(dest));moved.append(obj['oc_id'])
print(json.dumps({'archived_synthetic_objects':len(moved),'project_ids':list(pids)}))
