import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
out=root/'.execution';out.mkdir(exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
checks=[]
files=[p for directory in ('opencontent','plugin','tests','templates','scripts','packs') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
commands=[['node','--check','plugin/main.js'],['node','--test','tests/capabilities-ui.test.cjs','tests/sidebar.test.cjs','tests/ideation-ui.test.cjs','tests/doctor-ui.test.cjs','tests/writing-ui.test.cjs','tests/adversarial-review.test.cjs','tests/three-stage-ui.test.cjs','plugin/engine/domain.test.cjs','plugin/engine/pipeline.test.cjs','plugin/engine/typography.test.cjs'],[sys.executable,'-m','compileall','-q','opencontent'],[sys.executable,'-m','unittest','discover','-s','tests','-v']]
for index,command in enumerate(commands):
    result=subprocess.run(command,cwd=root,env={**__import__('os').environ,'PYTHON':sys.executable},capture_output=True,text=True,encoding='utf-8',errors='replace')
    output=result.stdout+result.stderr;raw=output.encode('utf-8')
    log=out/f'verify-{stamp}-{index}.log';log.write_bytes(raw)
    public_command=['python' if item==sys.executable else item for item in command]
    check={'command':public_command,'exit_code':result.returncode,'evidence':log.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()}
    if 'unittest' in command:
        inventory_code="import json,unittest; s=unittest.defaultTestLoader.discover('tests'); flatten=lambda x: sum((flatten(t) if isinstance(t,unittest.TestSuite) else [t.id()] for t in x),[]); print(json.dumps(flatten(s)))"
        inventory=subprocess.run([sys.executable,'-c',inventory_code],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
        if inventory.returncode:raise RuntimeError('Unable to enumerate test inventory: '+inventory.stderr)
        all_ids=json.loads(inventory.stdout)
        inventory_path=out/f'test-inventory-{stamp}.json';inventory_path.write_text(json.dumps(all_ids,indent=2),encoding='utf-8')
        executed=re.search(r'Ran (\d+) tests?',output)
        ids=[f'{scope}.{name}' for name,scope in re.findall(r'^(\w+) \(([^)]+)\) \.\.\. ',output,re.M)]
        check.update(executions=int(executed[1]) if executed else None,unique_tests=len(set(all_ids)),discovered_executions=len(all_ids),listed_executions=len(ids),
                     inventory=inventory_path.relative_to(root).as_posix(),
                     failures=[{'test':test,'scope':scope} for test,scope in re.findall(r'^(?:ERROR|FAIL): (\w+) \(([^)]+)\)',output,re.M)])
    if '--test' in command:
        for key in ('tests','pass','fail','skipped'):
            match=re.search(r'(?:ℹ |# )'+key+r' (\d+)',output)
            if match:check[key]=int(match[1])
    checks.append(check)
    print(('PASS ' if result.returncode==0 else 'FAIL ')+ ' '.join(public_command),flush=True)
    if result.returncode:print('Full evidence: '+check['evidence'],flush=True)
files=[p for directory in ('opencontent','plugin','tests','templates','scripts','packs') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
changed=[name for name in before.keys()|after.keys() if before.get(name)!=after.get(name)]
report={'schema':'opencontent.verification-summary.v1','changed_during_checks':changed,'at':datetime.now(timezone.utc).isoformat(),'passed':not changed and all(c['exit_code']==0 for c in checks),'checks':checks,
        'hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
public=root/'docs/verification.json'
if public.exists():(out/f'verification-before-{stamp}.json').write_bytes(public.read_bytes())
public.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(out/f'verification-{stamp}.json').write_bytes(public.read_bytes())
raise SystemExit(0 if report['passed'] else 1)

