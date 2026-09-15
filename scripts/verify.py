import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
checks=[]
files=[p for directory in ('opencontent','plugin','tests','templates','scripts') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
commands=[['node','--check','plugin/main.js'],['node','--test','tests/sidebar.test.cjs','tests/ideation-ui.test.cjs','tests/doctor-ui.test.cjs','tests/writing-ui.test.cjs','tests/adversarial-review.test.cjs','plugin/engine/domain.test.cjs','plugin/engine/pipeline.test.cjs','plugin/engine/typography.test.cjs'],[sys.executable,'-m','compileall','-q','opencontent'],[sys.executable,'-m','unittest','discover','-s','tests','-v']]
for command in commands:
    result=subprocess.run(command,cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
    checks.append({'command':command,'exit_code':result.returncode,'output':result.stdout+result.stderr})
    print(('PASS ' if result.returncode==0 else 'FAIL ')+ ' '.join(command),flush=True)
    if result.returncode:print(result.stdout+result.stderr)
files=[p for directory in ('opencontent','plugin','tests','templates','scripts') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
changed=[name for name in before.keys()|after.keys() if before.get(name)!=after.get(name)]
report={'changed_during_checks':changed,'at':datetime.now(timezone.utc).isoformat(),'passed':not changed and all(c['exit_code']==0 for c in checks),'checks':checks,
        'hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(root/'docs'/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if report['passed'] else 1)

