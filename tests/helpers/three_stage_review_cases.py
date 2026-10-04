"""Bounded synthetic adversarial probes. No external network or real credentials.
FAIL means the safety expectation was violated; ERROR is not a passing check.
Run with .venv/Scripts/python.exe -B .execution/review-probes.py.
"""
import copy,hashlib,http.client,io,json,os,subprocess,sys,threading,time,traceback
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'.execution'
SNAP=ROOT
sys.path[:0]=[str(SNAP),str(SNAP/'tests')]
from PIL import Image,ImageDraw,ImageFont
from opencontent.kernel import Kernel
from opencontent.vault import Problem,encode,digest
from opencontent.jobs import Jobs
from opencontent.server import Server
from opencontent import rendering,workbench,social_graphic,domain
from opencontent.publishing import Publishing,preview_hash
from opencontent.providers import AgentExecutionProvider
from opencontent.capabilities import PackRegistry,CapabilityRuntime
import test_kernel as fixtures
from test_kernel import response,STATEMENT
from test_lifecycle import WeChatFixture
RESULTS=[]
RUN=str(time.time_ns())

def probe(name,expected,fn):
    try:
        ok,observed=fn(); row={'name':name,'expected':expected,'verdict':'PASS' if ok else 'FAIL','observed':observed}
    except Exception:
        row={'name':name,'expected':expected,'verdict':'ERROR','traceback':traceback.format_exc()}
    RESULTS.append(row); print(name,row['verdict'],flush=True)
    (OUT/'review-probe-results-final.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')

class F:
    token=fixtures.KernelTests.token;run_stage=fixtures.KernelTests.run_stage;to_review=fixtures.KernelTests.to_review;approve=fixtures.KernelTests.approve
    def __init__(self,name):
        self.root=OUT/'review-fixtures-final'/RUN/name;self.root.mkdir(parents=True,exist_ok=True)
        if (self.root/'OpenContent').exists():raise RuntimeError('Use a fresh review fixture run directory')
        self.k=Kernel(self.root);self.p=self.k.create_project('独立审查合成项目','软件协议审查','审查人员')['oc_id']
        self.m=self.k.add(self.p,'Material','合成原文',STATEMENT,{'source':'fixture:local'},self.token())
        self.aid=self.to_review()
    def edit(self,uid,**changes):
        a=copy.deepcopy(self.k.read()[0][uid]);a.update(changes);self.k.vault.safe(a['path']).write_bytes(encode(a));return a
    def img(self,path='Attachments/中文图.png',color='blue'):
        p=self.k.vault.safe(path);p.parent.mkdir(parents=True,exist_ok=True);Image.new('RGB',(96,64),color).save(p);return p
    def pictured(self):
        self.img();a=self.k.read()[0][self.aid];self.edit(self.aid,body=a['body']+'\n\n![合成图注](Attachments/中文图.png)')
        self.review(self.aid);self.approve(self.aid)
    def review(self,aid):
        return self.k.review(aid,'independent:fixture',response({'stage':'critique','objects':[]})['axes'],True,'','合成软件协议审查，不代表编辑认可。',self.token(),expected_snapshot=self.k.inspect(aid)['input_snapshot'])
    def variant(self,resources=False):
        self.approve(self.aid);mother=self.k.read()[0][self.aid];excerpt=mother['body'].split('\n\n')[1]
        if resources:self.img()
        class Provider(AgentExecutionProvider):
            def run(s,req,workspace,event):
                return {'mother_artifact_id':mother['oc_id'],'title':'独立合成图文','body':mother['body'],
                    'pages':[{'role':'explain','purpose':'保留完整原句','source_excerpt':excerpt,'claims':mother['derived_from'],
                    'title':'合成标题','body':excerpt,'resources':['Attachments/中文图.png'] if resources else []}]}
            def capabilities(s):return {'reason':True,'web':False,'session':False}
        jobs=Jobs(self.k,{'synthetic':Provider()})
        try:
            reg=PackRegistry();reg.discover([SNAP/'packs'])
            a=CapabilityRuntime(self.k,reg,jobs=jobs).execute_task({'schema':'opencontent.creative-task.v1','pack':'xiaohongshu',
                'task':'social-graphic','project':self.p,'artifact':self.aid,'instruction':'合成协议验收','token':self.token()},'synthetic')['artifact']
        finally:jobs.close()
        self.review(a['oc_id']);self.approve(a['oc_id']);return a

def rejects(fn):
    try:fn();return False,None
    except Problem as e:return True,str(e)

def links():
    cases=['https://127.0.0.1/','https://[::ffff:127.0.0.1]/','https://[::ffff:192.168.1.1]/',
           'https://[::ffff:7f00:1]/','https://[::1]/','https://[fe80::1]/','https://[2001:db8::1]/',
           'https://127.1/','https://0177.0.0.1/','https://2130706433/','https://localhost./',
           'https://example.com:444/','https://u:p@example.com/','javascript:alert(1)']
    rows=[{'url':s,'rejected':rejects(lambda:rendering.safe_link(s))[0]} for s in cases]
    return all(r['rejected'] for r in rows),rows

def critic_race():
    f=F('critic-race');f.pictured();before=f.token();seen={}
    class Race(AgentExecutionProvider):
        def capabilities(s):return {'reason':True,'session':False,'web':False}
        def run(s,req,workspace,event):
            seen.update(request_keys=list(req),target=req.get('target_artifact_id'),old_semantic=rendering.semantic_binding(f.k,f.k.read()[0][f.aid]))
            f.img(color='red');seen['token_unchanged']=f.token()==before
            r=response(req);r['artifact_id']=f.aid;return r
    jobs=Jobs(f.k,{'synthetic':Race()});server=Server(f.k,jobs);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    try:
        c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        c.request('POST','/jobs',json.dumps({'project':f.p,'provider':'synthetic','stage':'critique','target_artifact_id':f.aid,'token':before}),
                  {'Authorization':'Bearer '+server.token,'Content-Type':'application/json'})
        r=c.getresponse();value=json.loads(r.read());c.close();seen['http_status']=r.status
        uid=value['id'];deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            job=next(j for j in jobs.list() if j['id']==uid)
            if job['status'] not in ('QUEUED','RUNNING'):break
            time.sleep(.03)
        seen['job']=job;g=f.k.inspect(f.aid)['gate'];seen['gate_status']=g['status'];seen['review_semantic']=g['review'].get('semantic_hash')
        allowed,error=rejects(lambda:f.approve(f.aid));seen['approval_rejected']=allowed;seen['error']=error
        return job['status']=='FAILED' and allowed,seen
    finally:server.shutdown();server.server_close();jobs.close();t.join()

def direct_gates():
    f=F('direct-gates');f.pictured();f.edit(f.p,state='REVIEWING');f.img(color='red')
    objects,errors=f.k.read();a=objects[f.aid];old=domain.gate(objects,a,f.k.vault.constitution(f.p),errors);new=f.k.quality(objects,a,errors=errors)
    reject,error=rejects(lambda:f.k.advance(f.p,'APPROVED',f.token()))
    handoff_rejected,_=rejects(lambda:f.k.handoff(f.aid,f.token()))
    return reject and not old['approved'],{'domain_approved':old['approved'],'kernel_approved':new['approved'],
        'advance_rejected':reject,'error':error,'stored_project_state':f.k.read()[0][f.p]['state'],'handoff_rejected':handoff_rejected}

def manual_review_race():
    f=F('manual-review-race');f.pictured();old_token=f.token();snapshot=f.k.inspect(f.aid)['input_snapshot'];old_semantic=rendering.semantic_binding(f.k,f.k.read()[0][f.aid]);f.img(color='red')
    rejected,error=rejects(lambda:f.k.review(f.aid,'independent:new',response({'stage':'critique','objects':[]})['axes'],True,'','以旧截图完成的合成审查。',old_token,expected_snapshot=snapshot))
    approved=False
    if not rejected:f.approve(f.aid);approved=f.k.inspect(f.aid)['gate']['approved']
    return rejected,{'rejected':rejected,'error':error,'new_image_approved':approved,'old_semantic':old_semantic,
        'review_semantic':f.k.inspect(f.aid)['gate']['review'].get('semantic_hash')}

def render_between_gate_and_build():
    f=F('gate-build-race');f.pictured();original=rendering.render;calls=0
    def render(vault,a,theme='serif',asset_sink=None):
        nonlocal calls
        calls+=1
        if calls==2:f.img(color='red')
        return original(vault,a,theme,asset_sink)
    old=rendering.semantic_binding(f.k,f.k.read()[0][f.aid])
    with patch('opencontent.rendering.render',side_effect=render):
        rejected,error=rejects(lambda:rendering.export_build(f.k,f.aid,f.token()))
    result=None
    if not rejected:
        manifests=list(f.root.glob('OpenContent-Exports/*/*/manifest.json'));result=json.loads(manifests[0].read_text(encoding='utf-8'))
    return rejected,{'rejected':rejected,'error':error,'render_calls':calls,'old_approved_semantic':old,
        'export':result,'current_approved':f.k.inspect(f.aid)['gate']['approved']}

def multi_images():
    f=F('multi-images');uid='a'*32;workspace=f.root/'candidate';workspace.mkdir();Image.new('RGB',(32,32),'blue').save(workspace/'one.png');Image.new('RGB',(32,32),'red').save(workspace/'two.png')
    workbench.request(f.k,f.p,'生成两张合成图','illustrate',[],uid,f.aid)
    r={'reply':'合成图片协议 fixture','revision':None,'illustrations':[],
       'images':[{'path':p,'alt':'合成图','placement':'正文'} for p in ('one.png','two.png')]}
    workbench.complete(f.k,f.p,uid,r,workspace);workbench.apply_image(f.k,f.p,uid,0,f.token())
    rejected,error=rejects(lambda:workbench.apply_image(f.k,f.p,uid,1,f.token()))
    return not rejected,{'second_rejected':rejected,'error':error,'applied_images':workbench.history(f.k,f.p)[0].get('applied_images')}

def legacy(status):
    f=F('legacy-'+status);f.approve(f.aid);a=f.k.read()[0][f.aid];g=f.k.inspect(f.aid)['gate']
    # Execute original origin/main renderer function, not a reimplementation.
    import mistune
    from opencontent.handoff import reader_body
    old_html=mistune.create_markdown(escape=True,plugins=['table','strikethrough'])(reader_body(a))
    payload={'article_type':'news','title':a['title'],'author':'','digest':'合成摘要','content':old_html,
             'content_source_url':'','thumb_media_id':'cover-fixture','need_open_comment':0,'only_fans_can_comment':0}
    remote=WeChatFixture();pub=Publishing(f.k,{'fixture':remote})
    p=f.k.vault.new('Publication','旧版合成outbox','旧版记录',f.p,artifact=f.aid,channel='fixture',destination=remote.identity(),
        action='draft',delivery_status=status,context_hash=g['context_hash'],review=g['review']['oc_id'],decision=g['decision']['oc_id'],
        media_id=None,draft_publication=None,remote_before_hash=None,payload=payload,events=[],url=None,published_at=None)
    if status=='REMOTE_DRAFT':
        p.update(remote_media_id='old-draft',intent_hash=preview_hash(p));remote.drafts['old-draft']={'news_item':[copy.deepcopy(payload)]}
    f.k.vault.commit([p],f.token())
    if status=='PREPARED':rejected,error=rejects(lambda:pub.confirm(p['oc_id'],preview_hash(p),'合成确认人',f.token()))
    else:rejected,error=rejects(lambda:pub.prepare(f.aid,'fixture','publish',f.token(),draft_publication=p['oc_id']))
    duplicate,msg=rejects(lambda:pub.prepare(f.aid,'fixture','draft',f.token(),{'digest':'合成摘要','thumb_media_id':'cover-fixture'}))
    reconcile=None
    if status=='REMOTE_DRAFT':reconcile=pub.reconcile(p['oc_id'])['delivery_status']
    return not rejected,{'operation_rejected':rejected,'error':error,'rebuild_rejected':duplicate,'rebuild_error':msg,
                        'legacy_reconcile':reconcile,'network_fixture_calls':remote.calls,'legacy_html':payload['content']}

class Images(WeChatFixture):
    def __init__(self):super().__init__();self.raws={};self.uploads=[]
    def upload_image(self,raw,mime):
        h=digest(raw);url='https://mmbiz.qpic.cn/synthetic/'+h;self.raws[url]=raw;self.uploads.append(h)
        return {'url':url}
    def verify_image(self,url,asset):
        self.calls.append('verify/image')
        if digest(self.raws[url])!=asset['hash']:raise Problem('fixture bytes mismatch')
        return {'url':url,'hash':asset['hash']}

def publishing_tamper():
    f=F('publishing-tamper');f.pictured();remote=Images();pub=Publishing(f.k,{'fixture':remote})
    p=pub.prepare(f.aid,'fixture','draft',f.token(),{'digest':'合成摘要','thumb_media_id':'cover-fixture'})
    no_upload=not remote.uploads;p=pub.confirm(p['oc_id'],preview_hash(p),'合成确认人',f.token())
    original_hash=p['remote_payload_hash'];assets=copy.deepcopy(p['delivery_assets']);asset=p['build']['assets'][0];new='https://mmbiz.qpic.cn/synthetic/TAMPERED'
    assets[asset['hash']]['url']=new;f.edit(p['oc_id'],delivery_assets=assets)
    hacked=f.k.read()[0][p['oc_id']];payload=copy.deepcopy(hacked['payload']);payload['content']=rendering.inline_assets(payload['content'],{asset['token']:new});remote.drafts[p['remote_media_id']]={'news_item':[payload]}
    frozen_intent=preview_hash(hacked)==hacked['intent_hash'];mismatch=digest(payload)!=original_hash
    rejected,error=rejects(lambda:pub.reconcile(p['oc_id']))
    if rejected:return True,{'rejected':True,'error':error,'resolved_hash_mismatch':mismatch}
    result=pub.reconcile(p['oc_id'])
    return result['delivery_status']!='REMOTE_DRAFT',{'preview_prepare_uploaded':not no_upload,'intent_still_valid':frozen_intent,
        'resolved_hash_mismatch':mismatch,'reconciled_status':result['delivery_status'],'verify_calls':remote.calls.count('verify/image'),'uploads':remote.uploads}

def resource_replace():
    f=F('resource-replace');a=f.variant(True);f.img(color='red');g=f.k.inspect(a['oc_id'])['gate'];rejected,error=rejects(lambda:social_graphic.export_bundle(f.k,a['oc_id'],f.token()))
    return not g['approved'] and rejected,{'approved':g['approved'],'issues':g['issues'],'export_rejected':rejected,'error':error}

def resource_copy_race():
    f=F('resource-copy-race');a=f.variant(True);real=social_graphic.write_once;changed=False
    def write(path,raw):
        nonlocal changed
        real(path,raw)
        if path.name=='preview.html' and not changed:f.img(color='red');changed=True
    with patch('opencontent.social_graphic.write_once',side_effect=write):
        rejected,error=rejects(lambda:social_graphic.export_bundle(f.k,a['oc_id'],f.token()))
    if rejected:return True,{'rejected':True,'error':error,'race_injected':changed}
    result=social_graphic.export_bundle(f.k,a['oc_id'],f.token())
    manifest=json.loads(f.k.vault.safe(result['path']+'/manifest.json').read_text(encoding='utf-8'))
    asset=manifest['assets'][0];copied=digest(f.k.vault.safe(result['path']+'/'+asset['path']).read_bytes())
    return copied==asset['hash'],{'status':result['status'],'manifest_hash':asset['hash'],'copied_asset_hash':copied,'bundle_path':result['path'],'race_injected':changed}

def wrap_probe():
    path,info=social_graphic.installed_font('结论。中文（引号）英文');font=ImageFont.truetype(str(path),40);draw=ImageDraw.Draw(Image.new('RGB',(1080,1440)))
    examples=[('中文句号','结论。',draw.textlength('结论',font=font)+1),('行尾括号','中文（结论）',draw.textlength('中文（',font=font)+1),
              ('英文词','OpenContent',draw.textlength('OpenC',font=font)+1)]
    rows=[]
    for n,text,width in examples:
        rejected,error=rejects(lambda:social_graphic.wrap(draw,text,font,width))
        lines=[] if rejected else social_graphic.wrap(draw,text,font,width)
        rows.append({'case':n,'lines':lines,'rejected':rejected,'error':error})
    (OUT/'review-wrap-final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    # A complete English word wider than the available width must fail. The
    # original probe demanded a single line but omitted its width constraint.
    return all((r['rejected'] and r['case']=='英文词') or (r['lines'] and all(not line.endswith('（') and not line.startswith('。') for line in r['lines'])) for r in rows),rows


def rendering_boundaries():
    f=F('render-boundaries');f.img();a=f.k.read()[0][f.aid];rows=[]
    for path in ['Attachments/%E4%B8%AD%E6%96%87%E5%9B%BE.png','Attachments/../中文图.png','C:/private.png','//server/share/a.png',
                 'Attachments/%2e%2e/a.png','data:image/png;base64,AAA','https://example.com/a.png','.opencontent/a.png']:
        candidate={**a,'body':a['body']+'\n\n![测试]('+path+')'};rejected,error=rejects(lambda:rendering.render(f.k.vault,candidate));rows.append({'path':path,'rejected':rejected,'error':error})
    code=rendering.render(f.k.vault,{**a,'body':a['body']+'\n\n```\n![测试](Attachments/不存在.png)\n```'})
    html=rendering.render(f.k.vault,{**a,'body':a['body']+'\n<script>alert(1)</script>\n<img src=x onerror=alert(1)>'})
    return not rows[0]['rejected'] and all(r['rejected'] for r in rows[1:]) and not code['assets'] and '<script>' not in html['html'],{'paths':rows,'code_assets':code['assets'],'escaped_html':html['html']}

def https_regression():
    f=F('https-regression');a=f.k.read()[0][f.aid]
    rejected,error=rejects(lambda:rendering.render(f.k.vault,{**a,'body':a['body']+'\n\n[公开来源](https://example.com/article)'}))
    return not rejected,{'valid_https_rejected':rejected,'error':error}

def title_leak():
    f=F('title-leak');a=f.k.read()[0][f.aid];title='C:\\Users\\Synthetic\\private.md [['+a['derived_from'][0]+']]'
    rejected,error=rejects(lambda:rendering.render(f.k.vault,{**a,'title':title}))
    if rejected:return True,{'rejected':True,'error':error}
    rendered=rendering.render(f.k.vault,{**a,'title':title})
    return title not in rendered['html'] and title not in rendered['markdown'],{'html':rendered['html'],'markdown':rendered['markdown']}

def source_validation():
    from opencontent.capabilities.context import ContextAssembler
    s={'type':'Review','oc_id':'fake','project':'another-project','body':'模型编造内容','source':'assistant:discussion','title':'模型历史'}
    rejected,error=rejects(lambda:ContextAssembler().assemble('revise','改稿',{'oc_id':'project'},sources=[s]))
    package=ContextAssembler().assemble('revise','改稿',{'oc_id':'project'},sources=[s]) if not rejected else None
    return rejected,{'rejected':rejected,'error':error,'accepted_provenance':package['provenance'][-1] if package else None}

def v2_critic():
    f=F('v2-critic');a=f.k.read()[0][f.aid];cid=a['derived_from'][0]
    f.edit(f.aid,protocol='opencontent.artifact.v2',claim_bindings={cid:{'text_excerpt':STATEMENT}})
    req=f.k.request(f.p,'critique',[],f.aid);r=response(req);r.update(artifact_id=f.aid,claim_reviews={cid:{'faithful':True,'reason':'fixture'}})
    f.k.apply_result(f.p,'critique',r,req['token'],'fixture','v2',f.aid,expected_snapshot=req['input_snapshot']);g=f.k.inspect(f.aid)['gate']
    return g['status']=='PASS',{'schema_keys':list(req['response_schema']),'stored_claim_reviews':g['review'].get('claim_reviews'),'issues':g['issues']}
