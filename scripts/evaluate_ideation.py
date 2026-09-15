"""Replay a fixed authored corpus through the actual ideation implementation and optional local CLI.
This measures execution/guards only; never certifies human editorial quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from opencontent import ideation
from opencontent.kernel import Kernel
from opencontent.providers import CodexProvider,ClaudeProvider,detect_cli
from opencontent.vault import Problem,atomic

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--provider',choices=['codex','claude'],required=True)
    parser.add_argument('--executable')
    parser.add_argument('--case',action='append',dest='case_ids',help='Replay only these case IDs; repeat to select multiple.')
    args=parser.parse_args();suite=ROOT/'tests/fixtures/ideation-quality.json';raw=suite.read_bytes();cases=json.loads(raw)['cases']
    if args.case_ids:
        unknown=set(args.case_ids)-{c['id'] for c in cases}
        if unknown:parser.error('Unknown cases: '+', '.join(sorted(unknown)))
        cases=[c for c in cases if c['id'] in args.case_ids]
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=False)
    executable=args.executable or next((c['path'] for c in detect_cli() if c['name']==args.provider),None)
    if not executable:raise SystemExit('Native CLI unavailable; install/login using CLI documentation first.')
    base=(CodexProvider if args.provider=='codex' else ClaudeProvider)(executable,timeout=300)
    report={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'suite_sha256':hashlib.sha256(raw).hexdigest(),
            'provider':args.provider,'model_override':False,'private_vault_used':False,'host_ui':'NOT_TESTED','editorial_quality':'NOT_REVIEWED','public_release':'BLOCKED','rounds':[]}
    def save():atomic(output/'execution.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
    save()
    class CountingProvider:
        def __init__(self):self.stages=[]
        def run(self,request,workspace,event):self.stages.append(request['stage']);return base.run(request,workspace,event)
    for case in cases:
        start=time.monotonic();directory=output/case['id'];(directory/'.obsidian').mkdir(parents=True)
        k=Kernel(directory)
        for note in case['notes']:(directory/note['name']).write_text(note['body'],encoding='utf-8')
        snapshot=ideation.load_snapshot(k,ideation.preview(k,case['direction'])['id']);provider=CountingProvider()
        row={'case':case['id'],'category':case['category'],'expected':case['expectation'],'run':snapshot['id'],
             'families':len(snapshot['families']),'sources':len(snapshot['sources']),'human_review':'PENDING'}
        try:
            result=ideation.execute(k,snapshot,provider,threading.Event(),lambda stage:print(case['id']+' '+stage,flush=True))
            atomic(directory/'result.json',json.dumps(result,ensure_ascii=False,indent=2).encode())
            row.update(outcome='MODEL_COMPLETED',candidates=len(result['ideas']),excluded=len(result['excluded']))
        except Problem as e:
            row.update(outcome='SOURCE_BLOCKED' if len(snapshot['families'])<2 and not provider.stages else 'FAILED',error=str(e))
        row.update(stages=provider.stages,seconds=round(time.monotonic()-start,2),execution_pass=row['outcome']==case['expectation'])
        report['rounds'].append(row);save();print(case['id']+' '+row['outcome'],flush=True)
    report['execution_passed']=all(r['execution_pass'] for r in report['rounds']);save()
    print(json.dumps({'execution_passed':report['execution_passed'],'rounds':len(report['rounds']),'editorial_quality':'NOT_REVIEWED'}))
    return 0 if report['execution_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
