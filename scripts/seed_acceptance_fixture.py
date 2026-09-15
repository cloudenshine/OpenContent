"""Real Markdown/state transitions using explicitly synthetic editorial judgments."""
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests'))
from opencontent.kernel import Kernel
from test_kernel import response, STATEMENT
k=Kernel(root/'validation-vault')
title='软件门禁验收样本（合成内容与审查）'
existing=next((p for p in k.board()['projects'] if p['title']==title),None)
if existing:
    print(json.dumps({'project':existing['oc_id'],'artifact':existing['artifacts'][0]['oc_id']}));raise SystemExit()
p=k.create_project(title,'验证实际 Obsidian 内 Accept / Reject 按钮，不代表用户对文章的认可。','软件验收人员')['oc_id']
k.add(p,'Material','明确标注的合成原文',STATEMENT,{'source':'fixture:software-acceptance'},k.vault.token())
for stage in ('distill','research','draft','critique'):
    request=k.request(p,stage,[])
    k.apply_result(p,stage,response(request),request['token'],'synthetic-test-fixture','software-ui-fixture-'+stage)
artifact=k.inspect(p)['objects']
aid=next(o['oc_id'] for o in artifact if o['type']=='Artifact')
print(json.dumps({'project':p,'artifact':aid},ensure_ascii=False))
