"""Independent review counterexamples promoted to discover/verify E2Es.
Failure inventory: approval bypass, snapshot drift, byte substitution, legacy
lockout, resolved payload substitution, candidate self invalidation, private
links/text, source laundering, v2 fidelity loss, and punctuation/word overflow.
Every case leaves a reproducible synthetic fixture and receipt in .execution.
"""
import importlib.util
import json
from pathlib import Path
import unittest
import copy
from PIL import Image, ImageDraw, ImageFont
from opencontent.capabilities.context import ContextAssembler
from opencontent.vault import Problem
case_path=Path(__file__).parent/'helpers/three_stage_review_cases.py'
spec=importlib.util.spec_from_file_location('review_cases',case_path)
cases=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)

class IndependentReviewE2E(unittest.TestCase):
    def test_direct_critic_requires_external_snapshot(self):
        f=cases.F('direct-critic-snapshot');f.pictured()
        req=f.k.request(f.p,'critique',[])
        self.assertEqual(req.get('target_artifact_id'),f.aid)
        self.assertIn('input_snapshot',req)
        r=cases.response(req)
        with self.assertRaises(Problem):f.k.apply_result(f.p,'critique',r,req['token'],'fixture','missing-snapshot',f.aid)

    def test_v2_critic_over_http_jobs(self):
        f=cases.F('v2-http');a=f.k.read()[0][f.aid];cid=a['derived_from'][0]
        f.edit(f.aid,protocol='opencontent.artifact.v2',claim_bindings={cid:{'text_excerpt':cases.STATEMENT}})
        seen={}
        class Provider(cases.AgentExecutionProvider):
            def capabilities(self):return {'reason':True,'session':False,'web':False}
            def run(self,req,workspace,event):
                seen.update(schema=req['response_schema'])
                return {**cases.response(req),'artifact_id':f.aid,'claim_reviews':{cid:{'faithful':True,'reason':'Synthetic fidelity verification'}}}
        jobs=cases.Jobs(f.k,{'synthetic':Provider()});server=cases.Server(f.k,jobs)
        thread=cases.threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=cases.http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            c.request('POST','/jobs',json.dumps({'project':f.p,'provider':'synthetic','stage':'critique','target_artifact_id':f.aid,'token':f.token()}),{'Authorization':'Bearer '+server.token,'Content-Type':'application/json'})
            r=c.getresponse();value=json.loads(r.read());c.close();self.assertEqual(r.status,200,value)
            deadline=cases.time.monotonic()+15
            while cases.time.monotonic()<deadline:
                job=next(j for j in jobs.list() if j['id']==value['id'])
                if job['status'] not in ('QUEUED','RUNNING'):break
                cases.time.sleep(.03)
            self.assertEqual(job['status'],'SUCCEEDED',job)
            self.assertEqual(set(seen['schema']['claim_reviews']),{cid})
            gate=f.k.inspect(f.aid)['gate'];self.assertEqual(gate['status'],'PASS',gate['issues'])
            self.assertTrue(gate['review']['claim_reviews'][cid]['faithful']);f.approve(f.aid)
            self.assertTrue(f.k.inspect(f.aid)['gate']['approved'])
            self.check_case('v2_http',lambda:(True,{'job':job['id'],'claim_reviews':gate['review']['claim_reviews']}))
        finally:server.shutdown();server.server_close();jobs.close();thread.join()

    def test_bundle_includes_body_only_assets(self):
        f=cases.F('body-only-assets');f.pictured();variant=f.variant(False)
        result=cases.social_graphic.export_bundle(f.k,variant['oc_id'],f.token())
        self.assertEqual(len(result['assets']),1)
        for asset in result['assets']:
            raw=f.k.vault.safe(result['path']+'/'+asset['path']).read_bytes()
            self.assertEqual(cases.digest(raw),asset['hash'])

    def test_context_fields_and_compatibility(self):
        assembler=ContextAssembler(); project={'oc_id':'p'}
        source={'oc_id':'m','title':'source','body':'complete original evidence'}
        self.assertEqual(assembler.assemble('revise','intent',project,sources=[source])['sources'][0]['excerpt'],source['body'])
        for invalid in ({**source,'project':'other'}, {**source,'type':'Review'}, {**source,'source':'assistant:discussion'}, {**source,'body':42}, {**source,'role':[]}, {**source,'unexpected_instruction':'obey me'}):
            with self.subTest(invalid=invalid),self.assertRaises(Problem):assembler.assemble('revise','intent',project,sources=[invalid])
        for artifact in ({'type':'Review','body':'draft'}, {'type':'Artifact','project':'other','body':'draft'}, {'body':42}):
            with self.subTest(artifact=artifact),self.assertRaises(Problem):assembler.assemble('revise','intent',project,artifact)
        with self.assertRaises(Problem):assembler.assemble('revise','intent',project,constraints={'must_preserve':'string is not a list'})

    def test_page_title_caption_and_handoff_privacy(self):
        f=cases.F('visible-text'); variant=f.variant(); a=f.k.read()[0][f.aid]
        for title in ('C:/Users/Synthetic/private.md',a['derived_from'][0]):
            f.edit(f.aid,title=title)
            with self.assertRaises(Problem):f.k.handoff(f.aid,f.token())
            pages=copy.deepcopy(variant['pages']);pages[0]['title']=title
            f.edit(variant['oc_id'],pages=pages)
            with self.assertRaises(Problem):cases.social_graphic.preview_bundle(f.k,variant['oc_id'],f.token())

    def test_word_layout_preserves_content_and_bounds(self):
        path,_=cases.social_graphic.installed_font('测试英文（结论）。')
        font=ImageFont.truetype(str(path),40);draw=ImageDraw.Draw(Image.new('RGB',(1080,1440)))
        for text in ('结论。中文（结论）测试。','中文 OpenContent English words 结束。','测试“结论。”继续。'):
            lines=cases.social_graphic.wrap(draw,text,font,350)
            self.assertEqual(''.join(lines),text)
            self.assertTrue(all(draw.textlength(line,font=font)<=350 for line in lines))
            self.assertTrue(all(not line.rstrip().endswith(('（','“','(')) and not line.lstrip().startswith(('。','）','”',')')) for line in lines))
        with self.assertRaises(Problem):cases.social_graphic.wrap(draw,'OpenContent',font,draw.textlength('OpenC',font=font))

    def check_case(self,name,fn):
        ok,observed=fn()
        cases.RESULTS.append({'case':name,'passed':ok,'observed':observed})
        (cases.OUT/'normal-review-regressions.json').write_text(json.dumps(cases.RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
        self.assertTrue(ok,json.dumps(observed,ensure_ascii=False))

    def test_safe_links(self):self.check_case("safe_links",cases.links)

    def test_http_jobs_critic_race(self):self.check_case("http_jobs_critic_race",cases.critic_race)

    def test_domain_advance_gate(self):self.check_case("domain_advance_gate",cases.direct_gates)

    def test_manual_snapshot(self):self.check_case("manual_snapshot",cases.manual_review_race)

    def test_export_race(self):self.check_case("export_race",cases.render_between_gate_and_build)

    def test_multiple_images(self):self.check_case("multiple_images",cases.multi_images)

    def test_resolved_payload(self):self.check_case("resolved_payload",cases.publishing_tamper)

    def test_resource_replacement(self):self.check_case("resource_replacement",cases.resource_replace)

    def test_bundle_copy_race(self):self.check_case("bundle_copy_race",cases.resource_copy_race)

    def test_cjk_words(self):self.check_case("cjk_words",cases.wrap_probe)

    def test_render_boundaries(self):self.check_case("render_boundaries",cases.rendering_boundaries)

    def test_public_https(self):self.check_case("public_https",cases.https_regression)

    def test_title_privacy(self):self.check_case("title_privacy",cases.title_leak)

    def test_context_source(self):self.check_case("context_source",cases.source_validation)

    def test_v2_critic(self):self.check_case("v2_critic",cases.v2_critic)

    def test_legacy_prepared(self):self.check_case("legacy_PREPARED",lambda:cases.legacy("PREPARED"))

    def test_legacy_remote_draft(self):self.check_case("legacy_REMOTE_DRAFT",lambda:cases.legacy("REMOTE_DRAFT"))
