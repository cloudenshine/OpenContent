"""Synthetic end-to-end failure contracts, written before implementation.

No fixture represents a real model, image generator, or platform delivery.
Failure inventory: unsafe images/links/HTML, stale image bytes and approvals,
wrong or missing multi-target, title/body/selection races, cross-artifact Critic,
cancelled provider, lost upload receipts/restart, account changes, evidence
truncation, stale mother, unapproved social export, missing glyphs/overflow.
"""
import copy
import http.client
import json
from pathlib import Path
import threading
import unittest

from PIL import Image
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server
from opencontent.vault import Problem, encode, digest
from opencontent import workbench
import test_kernel as fixtures
from test_kernel import response


class ThreeStageE2E(unittest.TestCase):
    setUp = fixtures.KernelTests.setUp
    token = fixtures.KernelTests.token
    run_stage = fixtures.KernelTests.run_stage
    to_review = fixtures.KernelTests.to_review
    approve = fixtures.KernelTests.approve

    def edit(self, aid, **changes):
        a = copy.deepcopy(self.k.inspect(aid)['object']); a.update(changes)
        self.k.vault.safe(a['path']).write_bytes(encode(a))
        return a

    def review_now(self, aid):
        self.k.review(aid, 'fixture:independent', response({'stage':'critique','objects':[]})['axes'],
                      True, '', 'Synthetic protocol review only.', self.token(),expected_snapshot=self.k.inspect(aid)['input_snapshot'])
        self.approve(aid)

    def image(self, color='blue'):
        path = self.k.vault.safe('Attachments/中文图片.png'); path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (640, 360), color).save(path)
        return path

    def test_http_build_export_image_replace_and_safety(self):
        aid = self.to_review(); a = self.k.inspect(aid)['object']; self.image()
        self.edit(aid, body=a['body']+'\n\n![合成图注](Attachments/中文图片.png)\n\n| 项 | 值 |\n|---|---|\n| 否定 | 不能省略 |\n\n```python\nprint("fixture")\n```\n\n> 引用不等于批准。')
        self.review_now(aid)
        jobs = Jobs(self.k); server = Server(self.k, jobs)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            def post(route, payload):
                c = http.client.HTTPConnection('127.0.0.1', server.server_port)
                c.request('POST', route, json.dumps(payload), {'Authorization':'Bearer '+server.token,'Content-Type':'application/json'})
                r = c.getresponse(); value = json.loads(r.read()); c.close(); return r.status, value
            status, build = post('/build', {'artifact':aid,'theme':'academic','token':self.token()})
            self.assertEqual(status, 200, build)
            self.assertEqual(build['assets'][0]['width'], 640)
            self.assertIn('<table', build['html']); self.assertIn('<pre', build['html'])
            self.assertNotIn('[[', build['html']); self.assertNotIn(str(self.k.vault.root), build['html'])
            status, exported = post('/build/export', {'artifact':aid,'theme':'academic','token':self.token()})
            self.assertEqual(status, 200, exported)
            self.assertEqual(build['build_id'], exported['build_id'])
            self.assertTrue(self.k.vault.safe(exported['path']+'/preview.html').is_file())
            self.image('red')
            self.assertFalse(self.k.inspect(aid)['gate']['approved'])
            self.assertNotEqual(build['semantic_hash'], post('/build',{'artifact':aid,'token':self.token()})[1]['semantic_hash'])
            self.assertNotEqual(post('/build/export',{'artifact':aid,'token':self.token()})[0],200)
            for unsafe in ('https://127.0.0.1/private.png','../secret.png','C:/secret.png','.opencontent/secret.png'):
                self.edit(aid, body=a['body']+f'\n![x]({unsafe})')
                self.assertNotEqual(post('/build',{'artifact':aid,'token':self.token()})[0],200)
        finally:
            server.shutdown(); server.server_close(); jobs.close(); thread.join()

    def test_multi_target_local_proposal_races_and_critic(self):
        aid = self.to_review(); a = self.k.inspect(aid)['object']
        second = self.k.add(self.p,'Artifact','第二稿',a['body'],{'derived_from':a['derived_from'],'author':'fixture:writer'},self.token())['oc_id']
        with self.assertRaises(Problem): workbench.request(self.k,self.p,'改稿','revise',[],'1'*32)
        start = a['body'].index('这是一份'); end = a['body'].index('读者可以')
        selection = {'start':start,'end':end,'text':a['body'][start:end],'base_hash':digest({'title':a['title'],'body':a['body']})}
        req = workbench.request(self.k,self.p,'只改选中段落','revise',[],'2'*32,target_artifact_id=aid,selection=selection)
        proposal = {'reply':'Synthetic selection proposal.','revision':{'artifact':second,'title':a['title'],'body':'替换选区。'},'illustrations':[],'images':[]}
        with self.assertRaises(Problem):workbench.complete(self.k,self.p,'2'*32,proposal,self.k.vault.runtime)
        proposal['revision']['artifact']=aid
        turn=workbench.complete(self.k,self.p,'2'*32,proposal,self.k.vault.runtime)
        self.assertIn('diff',turn['revision'])
        workbench.apply_revision(self.k,self.p,'2'*32,self.token())
        after=self.k.inspect(aid)['object']['body']
        self.assertEqual(after,a['body'][:start]+'替换选区。'+a['body'][end:])
        self.assertEqual(self.k.inspect(second)['object']['body'],a['body'])
        workbench.request(self.k,self.p,'改稿','revise',[],'3'*32,target_artifact_id=second)
        self.edit(second,title='外部新标题')
        proposal['revision'].update(artifact=second,body=a['body'])
        with self.assertRaises(Problem):workbench.complete(self.k,self.p,'3'*32,proposal,self.k.vault.runtime)
        req=self.k.request(self.p,'critique',[],target_artifact_id=aid)
        wrong=response(req);wrong['artifact_id']=second
        with self.assertRaises(Problem):self.k.apply_result(self.p,'critique',wrong,req['token'],'fixture','bad',target_artifact_id=aid)

    def test_budget_never_silently_truncates_evidence(self):
        from opencontent.capabilities.context import ContextAssembler
        assembler=ContextAssembler(); source={'oc_id':'s','body':'证据原文。'*800,'title':'合成来源'}
        with self.assertRaises(Problem):assembler.assemble('revise','改稿',{},sources=[source],budget_limit=100)
        package=assembler.assemble('revise','改稿',{},sources=[source],budget_limit=20000)
        self.assertEqual(package['sources'][0]['excerpt'],source['body'])
        self.assertLessEqual(package['budget']['bytes'],20000)

    def test_social_pack_candidate_approval_bundle_staleness_and_overflow(self):
        from opencontent.capabilities import PackRegistry, CapabilityRuntime
        from opencontent.social_graphic import export_bundle, preview_bundle
        from opencontent.providers import AgentExecutionProvider
        aid=self.to_review();self.approve(aid); mother=self.k.inspect(aid)['object']
        class Synthetic(AgentExecutionProvider):
            def run(self, request, workspace, cancel_event):
                return {'mother_artifact_id':aid,'title':'合成小红书图文','body':mother['body'],
                        'pages':[{'role':'explain','purpose':'保留原主张及限定条件','source_excerpt':mother['body'].split('\n\n')[1],
                                  'claims':mother['derived_from'],'title':'合成图文','body':mother['body'].split('\n\n')[1], 'resources':[]}]}
            def capabilities(self):return {'reason':True,'web':False,'session':False}
        jobs=Jobs(self.k,{'synthetic':Synthetic()});self.addCleanup(jobs.close)
        reg=PackRegistry();reg.discover([Path(__file__).resolve().parents[1]/'packs'])
        rt=CapabilityRuntime(self.k,reg,jobs=jobs)
        result=rt.execute_task({'schema':'opencontent.creative-task.v1','pack':'xiaohongshu','task':'social-graphic','project':self.p,
                               'artifact':aid,'instruction':'合成软件验收，不是实际渠道文案。','token':self.token()},'synthetic')
        variant=result['artifact'];vid=variant['oc_id']
        self.assertFalse(self.k.inspect(vid)['gate']['approved'])
        with self.assertRaises(Problem):export_bundle(self.k,vid,self.token())
        preview=preview_bundle(self.k,vid,self.token());self.assertEqual(preview['status'],'UNAPPROVED_PREVIEW')
        self.review_now(vid);bundle=export_bundle(self.k,vid,self.token())
        self.assertEqual(bundle['status'],'LOCAL_BUNDLE_READY')
        root=self.k.vault.safe(bundle['path']);self.assertTrue((root/'manifest.json').is_file())
        with Image.open(root/'page-01.png') as png:self.assertEqual(png.size,(1080,1440))
        pages=copy.deepcopy(variant['pages']);pages[0]['body']='太长。'*4000
        self.edit(vid,pages=pages)
        with self.assertRaises(Problem):preview_bundle(self.k,vid,self.token())
        self.edit(vid,pages=variant['pages']);self.edit(aid,body=mother['body']+'\n母稿外部更新。')
        self.assertEqual(self.k.inspect(vid)['gate']['dependency_status'],'STALE')
        with self.assertRaises(Problem):export_bundle(self.k,vid,self.token())

    def test_publication_upload_unknown_restart_recovery_and_identity(self):
        from opencontent.publishing import Publishing
        from opencontent.publishing_adapters import UnknownOutcome
        from test_lifecycle import WeChatFixture
        class PlatformFixture(WeChatFixture):
            def __init__(self):super().__init__();self.uploads=0;self.lose=True;self.asset=None
            def upload_image(self,raw,mime):
                self.uploads+=1;self.asset=raw
                if self.lose:raise UnknownOutcome('Synthetic lost upload acknowledgement')
                return {'url':'https://mmbiz.qpic.cn/synthetic.png'}
            def verify_image(self,url,asset):
                self.assert_asset=asset
                if digest(self.asset)!=asset['hash']:raise Problem('Synthetic readback mismatch')
                return {'url':url,'hash':asset['hash']}
        aid=self.to_review();a=self.k.inspect(aid)['object'];self.image()
        self.edit(aid,body=a['body']+'\n\n![合成图](Attachments/中文图片.png)');self.review_now(aid)
        adapter=PlatformFixture();pub=Publishing(self.k,{'fixture':adapter})
        preview=pub.prepare(aid,'fixture','draft',self.token(),{'digest':'合成测试摘要','thumb_media_id':'cover'})
        unknown=pub.confirm(preview['oc_id'],preview['preview_hash'],'合成测试人',self.token())
        self.assertEqual(unknown['delivery_status'],'UNKNOWN');self.assertEqual(adapter.uploads,1)
        fresh=Publishing(Kernel(self.tmp.name),{'fixture':adapter})
        with self.assertRaises(Problem):fresh.confirm(preview['oc_id'],preview['preview_hash'],'合成测试人',self.token())
        with self.assertRaises(Problem):fresh.reconcile(preview['oc_id'])
        self.assertNotIn('draft/add',adapter.calls)
        asset=preview['build']['assets'][0]
        with self.assertRaises(Problem):fresh.reconcile_asset(preview['oc_id'],asset['hash'],'https://127.0.0.1/x')
        adapter.appid='wxffffffffffffffff'
        with self.assertRaises(Problem):fresh.reconcile_asset(preview['oc_id'],asset['hash'],'https://mmbiz.qpic.cn/synthetic.png')
        adapter.appid='wx0123456789abcdef'
        recovered=fresh.reconcile_asset(preview['oc_id'],asset['hash'],'https://mmbiz.qpic.cn/synthetic.png')
        self.assertEqual(recovered['delivery_status'],'PREPARED')
        from opencontent.publishing import preview_hash
        done=fresh.confirm(preview['oc_id'],preview_hash(recovered),'合成测试人',self.token())
        self.assertEqual(done['delivery_status'],'REMOTE_DRAFT');self.assertEqual(adapter.uploads,1)
        self.assertEqual(adapter.calls.count('draft/add'),1)
        self.assertIn('https://mmbiz.qpic.cn/synthetic.png',adapter.drafts['draft-id']['news_item'][0]['content'])

    def test_malicious_html_link_internal_id_and_theme_confirmation(self):
        from opencontent.rendering import build
        from opencontent.publishing import Publishing
        from test_lifecycle import WeChatFixture
        aid=self.to_review();a=self.k.inspect(aid)['object'];self.approve(aid)
        before=build(self.k,aid,self.token(),'serif',True)
        themed=build(self.k,aid,self.token(),'techDark',True)
        self.assertEqual(before['semantic_hash'],themed['semantic_hash']);self.assertNotEqual(before['build_id'],themed['build_id'])
        self.edit(aid,body=a['body']+'\n<script src="https://example.org/x"></script>')
        safe=build(self.k,aid,self.token());self.assertIn('&lt;script',safe['html']);self.assertNotIn('<script',safe['html'])
        for bad in ('[secret](javascript:alert%281%29)',f'[[{"f"*32}]]','![network](https://example.org/x.png)'):
            self.edit(aid,body=a['body']+'\n'+bad)
            with self.assertRaises(Problem):build(self.k,aid,self.token())
        self.edit(aid,body=a['body']);self.review_now(aid)
        pub=Publishing(self.k,{'fixture':WeChatFixture()});prepared=pub.prepare(aid,'fixture','draft',self.token(),{'digest':'合成摘要','thumb_media_id':'cover'})
        local=copy.deepcopy(prepared);local.pop('token');local.pop('preview_hash');local['build']['theme']='techDark'
        self.k.vault.safe(local['path']).write_bytes(encode(local))
        with self.assertRaises(Problem):pub.confirm(prepared['oc_id'],prepared['preview_hash'],'合成测试人',self.token())
