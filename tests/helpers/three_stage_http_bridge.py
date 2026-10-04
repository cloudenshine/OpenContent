"""Persistent real HTTP/kernel bridge with explicitly synthetic CLI responses.

Stdout emits only an ephemeral localhost connection descriptor. No real model,
Vault, account, image-generation tool or production credential is used.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_kernel import response, STATEMENT
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server
from opencontent.providers import AgentExecutionProvider


class SyntheticProvider(AgentExecutionProvider):
    def capabilities(self):return {'reason':True,'session':False,'web':False,'image_generation':False,'test_only':True}
    def run(self,request,workspace,cancel_event):
        if request['stage']=='critique':
            return {**response(request),'artifact_id':request['target_artifact_id']}
        if request['stage']=='social-graphic':
            mother=request['context']['current_artifact'];cid=next(o['oc_id'] for o in request['objects'] if o['type']=='Claim')
            return {'mother_artifact_id':mother['oc_id'],'title':'合成 UI 图文候选','body':mother['body'],
                    'pages':[{'role':'explain','purpose':'完整保留来源判断','source_excerpt':STATEMENT,
                              'claims':[cid],'title':'合成图文页','body':STATEMENT,'resources':[]}]}
        target=request['context']['current_artifact']
        if request['mode']=='illustrate':
            from PIL import Image
            for name,color in (('one.png','blue'),('two.png','red')):Image.new('RGB',(64,64),color).save(Path(workspace)/name)
            return {'reply':'Synthetic image candidates','revision':None,'illustrations':[],
                    'images':[{'path':name,'alt':'合成图片','placement':'正文'} for name in ('one.png','two.png')]}
        revision=None
        if request['mode']=='revise':
            selection=request.get('selection')
            body='选区改写仅用于合成验收。' if selection else target['body']+'\n合成 UI 改稿候选。'
            revision={'artifact':target['oc_id'],'title':target['title'],'body':body}
        return {'reply':'明确标记的合成 Provider 响应，不是实际模型执行。','revision':revision,'illustrations':[],'images':[]}


def main():
    with tempfile.TemporaryDirectory(prefix='opencontent-three-stage-http-') as root:
        k=Kernel(root);pid=k.create_project('合成 UI 验收','证明真实 UI→HTTP→Kernel 接线','软件验收')['oc_id']
        k.add(pid,'Material','合成原文',STATEMENT,{'source':'fixture:synthetic'},k.vault.token())
        for stage in ('distill','research','draft','critique'):
            request=k.request(pid,stage,[]);k.apply_result(pid,stage,response(request),request['token'],'fixture',stage)
        first=k.board()['projects'][0]['artifacts'][0];aid=first['oc_id']
        k.decide(aid,'accept','合成审查人','本决定仅用于软件协议验收，不代表实际编辑确认。',k.vault.token())
        second=k.add(pid,'Artifact','合成第二稿',first['body'],{'derived_from':first['derived_from'],'author':'fixture:writer'},k.vault.token())
        jobs=Jobs(k,{'synthetic':SyntheticProvider()});server=Server(k,jobs)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        print(json.dumps({'port':server.server_port,'token':server.token,'project':pid,'first':aid,'second':second['oc_id']}),flush=True)
        try:sys.stdin.readline()
        finally:server.shutdown();server.server_close();jobs.close();thread.join()


if __name__=='__main__':main()
