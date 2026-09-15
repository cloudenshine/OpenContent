"""Isolated Obsidian UI fixture. Never contacts WeChat; refuses other Vaults."""
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(root),str(root/'tests')]
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server
from opencontent.publishing import Publishing
from test_kernel import response,STATEMENT
from test_lifecycle import WeChatFixture
k=Kernel(root/'validation-vault')
assert k.vault.root.resolve()==(root/'validation-vault').resolve()
p=k.create_project('v0.4 微信闭环软件验收','验证管理到反馈的实际界面；使用模拟微信，不代表真实发表。','软件验收人员')['oc_id']
source='v0.4-来源验收.md';(k.vault.root/source).write_text(STATEMENT,encoding='utf-8')
k.capture(p,'软件验收来源',STATEMENT,'vault:'+source,k.vault.token())
for stage in ('distill','research','draft','critique'):
 request=k.request(p,stage,[]);k.apply_result(p,stage,response(request),request['token'],'synthetic-ui-fixture','v0.4-'+stage)
a=next(o for o in k.inspect(p)['objects'] if o['type']=='Artifact')
k.decide(a['oc_id'],'accept','软件验收决定人','仅批准合成测试数据，用于软件界面验证。',k.vault.token())
jobs=Jobs(k);server=Server(k,jobs);remote=WeChatFixture();remote.publish_status=0
server.publishing=Publishing(k,{'software-fixture':remote})
folder=root/'.validation-runtime';folder.mkdir(exist_ok=True)
(folder/'wechat-fixture.json').write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','token':server.token,'vault':str(k.vault.root),'project':p,'artifact':a['oc_id']}),encoding='utf-8')
print('ISOLATED_WECHAT_FIXTURE_READY; no external requests',flush=True)
try:server.serve_forever(.2)
finally:
 (folder/'wechat-fixture-calls.json').write_text(json.dumps(remote.calls),encoding='utf-8')
 jobs.close();server.server_close()
