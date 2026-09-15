import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from opencontent.kernel import Kernel
from opencontent.vault import Problem, encode, parse, atomic
from opencontent.domain import AXES, STATES
from opencontent.jobs import Jobs
from opencontent.providers import AgentExecutionProvider, discover_skills

STATEMENT = "在本验收材料中，内容需要保留可读取的来源。"


def response(request):
    """Deterministic software fixture, never represented as a real AI run."""
    stage = request['stage']; objects = request['objects']
    ids = lambda kind: [o['oc_id'] for o in objects if o['type'] == kind]
    if stage == 'distill':
        return {'knowledge': [{'key':'k1','title':'合成知识','body':'从明确来源中保留可验证依据。','materials':ids('Material')}],
                'idea': {'title':'合成想法','body':'说明来源为何要保留。','thesis':'写作应保留来源。','knowledge':['k1']}}
    if stage == 'research':
        return {'claims':[{'key':'c1','title':'来源保留','statement':STATEMENT,'knowledge':ids('Knowledge'),'confidence':'medium'}],
                'evidence':[{'title':'材料原文','claim':'c1','material':ids('Material')[0],'quote':STATEMENT,'relation':'supports','reason':'原文直接支持此有限主张。'}]}
    if stage == 'draft':
        cid=ids('Claim')[0]
        return {'artifact':{'title':'合成验收草稿','body':f'# 可追踪内容\n\n{STATEMENT} [[{cid}]]\n\n这是一份软件验收文本，不是实际编辑认可的文章。它展示如何将一个明确来源、知识与主张关联。读者可以打开证据，检查原文，再决定是否采用结论。这里不声称已完成外部研究、原创性鉴定或实际发表。','claims':ids('Claim')}}
    return {'axes':{axis:{'status':'PASS','reason':'合成测试评审：只验证此维度状态与版本门禁，不代表真实质量。'} for axis in AXES},'claims_complete':True,'conflict_resolution':'','summary':'软件 fixture 审查，仅用于验证。'}


class FixtureProvider(AgentExecutionProvider):
    def capabilities(self): return {'reason':True,'web':False,'session':False}
    def run(self,request,workspace,cancel_event): return response(request)


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.k=Kernel(self.tmp.name)
        self.p=self.k.create_project('验收 Project','证明完整状态链','软件验收人员')['oc_id']
        self.m=self.k.add(self.p,'Material','合成原文',STATEMENT,{'source':'fixture:local'},self.token())
    def token(self):return self.k.vault.token()
    def run_stage(self,stage):
        req=self.k.request(self.p,stage,[])
        return self.k.apply_result(self.p,stage,response(req),req['token'],'fixture',stage+'-run')
    def to_review(self):
        for stage in ('distill','research','draft','critique'):self.run_stage(stage)
        return self.k.board()['projects'][0]['artifacts'][0]['oc_id']
    def approve(self,aid):return self.k.decide(aid,'accept','合成测试决定人','合成软件验收批准，不代表实际用户确认。',self.token())
    def test_full_pipeline_and_rebuild_without_runtime(self):
        aid=self.to_review();b=self.k.board();self.assertEqual(b['projects'][0]['state'],'REVIEWING')
        self.assertEqual(b['inbox'][0]['gate']['status'],'PASS');self.assertFalse(b['inbox'][0]['gate']['approved'])
        self.approve(aid)
        self.assertEqual(self.k.board()['projects'][0]['state'],'APPROVED')
        history=self.k.inspect(self.p)['object']['history']
        self.assertEqual([h['to'] for h in history],list(STATES[1:8]))
        self.k.vault.db.unlink()
        fresh=Kernel(self.tmp.name)
        self.assertTrue(fresh.inspect(aid)['gate']['approved'])
        self.assertEqual(fresh.inspect(aid)['provenance'][0]['materials'][0]['oc_id'],self.m['oc_id'])
        for file in Path(self.tmp.name).glob('OpenContent/*/*.md'):
            self.assertIn('---',file.read_text(encoding='utf-8'))
    def test_cannot_skip_or_agent_approve(self):
        with self.assertRaises(Problem):self.k.advance(self.p,'APPROVED',self.token())
        req=self.k.request(self.p,'distill',[]);result=response(req);result['state']='APPROVED'
        with self.assertRaises(Problem):self.k.apply_result(self.p,'distill',result,req['token'],'fake','1')
        self.assertEqual(self.k.board()['projects'][0]['state'],'CAPTURED')
    def test_unreviewed_approval_blocked(self):
        for stage in ('distill','research','draft'):self.run_stage(stage)
        aid=self.k.board()['projects'][0]['artifacts'][0]['oc_id']
        with self.assertRaises(Problem):self.approve(aid)
    def test_edits_sources_constitution_invalidate_approval(self):
        aid=self.to_review();self.approve(aid)
        for file in [self.k.vault.root/self.m['path'],self.k.vault.root/'CONTENT.md',self.k.vault.root/self.k.inspect(aid)['object']['path']]:
            original=file.read_bytes();file.write_bytes(original+b'\nExternal editor change\n')
            self.assertFalse(self.k.inspect(aid)['gate']['approved'])
            self.assertEqual(self.k.board()['projects'][0]['effective_state'],'REVIEWING')
            file.write_bytes(original)
            self.assertTrue(self.k.inspect(aid)['gate']['approved'])
    def test_bad_quote_transaction_does_not_leak_objects(self):
        self.run_stage('distill');before=self.token();req=self.k.request(self.p,'research',[]);r=response(req);r['evidence'][0]['quote']='invented quotation'
        with self.assertRaises(Problem):self.k.apply_result(self.p,'research',r,req['token'],'fixture','bad')
        self.assertEqual(self.token(),before)
    def test_stale_job_and_two_writers(self):
        token=self.token();req=self.k.request(self.p,'distill',[])
        self.k.add(self.p,'Material','第二份来源','new content',{'source':'fixture:new'},token)
        with self.assertRaises(Problem):self.k.apply_result(self.p,'distill',response(req),req['token'],'fixture','stale')
        with self.assertRaises(Problem):self.k.add(self.p,'Material','第三份来源','new',{'source':'fixture:new'},token)
    def test_warn_fail_incomplete_and_self_review(self):
        aid=self.to_review();detail=self.k.inspect(aid);r=detail['gate']['review']
        axes=copy.deepcopy(r['axes']);axes['Originality']['status']='WARN'
        self.k.review(aid,'不同的审查人',axes,True,'','警告',self.token())
        with self.assertRaises(Problem):self.approve(aid)
        axes['Originality']['status']='PASS'
        self.k.review(aid,'不同的审查人',axes,False,'','未登记完整',self.token())
        self.assertIn('Important facts are missing',str(self.k.inspect(aid)['gate']['issues']))
        with self.assertRaises(Problem):self.k.review(aid,detail['object']['author'],axes,True,'','自己审查',self.token())
    def test_opposing_evidence_requires_resolution(self):
        aid=self.to_review();claim=self.k.inspect(aid)['provenance'][0]['claim']
        self.k.add(self.p,'Evidence','反对证据','软件 fixture 模拟争议',{'claim':claim['oc_id'],'material':self.m['oc_id'],'quote':STATEMENT,'relation':'opposes'},self.token())
        self.run_stage('critique')
        self.assertIn('Opposing Evidence',str(self.k.inspect(aid)['gate']['issues']))
    def test_reject_recritique_and_version_binding(self):
        aid=self.to_review();self.k.decide(aid,'reject','合成决定人','请增加一个具体例子后重新检查。',self.token())
        self.assertEqual(self.k.board()['inbox'][0]['kind'],'revision')
        self.run_stage('critique');self.approve(aid);self.assertTrue(self.k.inspect(aid)['gate']['approved'])
        self.run_stage('critique');self.assertFalse(self.k.inspect(aid)['gate']['approved'])
    def test_duplicate_malformed_and_path_escape(self):
        original=self.k.vault.root/self.m['path'];duplicate=original.with_name('duplicate.md');duplicate.write_bytes(original.read_bytes())
        self.assertTrue(self.k.board()['diagnostics']);duplicate.unlink()
        original.write_text('---\nwrong: [\n---\n',encoding='utf-8')
        self.assertTrue(self.k.board()['diagnostics'])
        with self.assertRaises(Problem):self.k.vault.safe('../escape.md')
        with self.assertRaises(Problem):parse(b'---\na: &b [1]\ntype: Material\n---\nbody','a.md')
    def test_forged_declared_state_is_not_approval(self):
        aid=self.to_review()
        for uid in (aid,self.p):
            obj=self.k.inspect(uid)['object'];obj['state']='APPROVED'
            (self.k.vault.root/obj['path']).write_bytes(encode(obj))
        self.assertFalse(self.k.inspect(aid)['gate']['approved'])
        self.assertEqual(self.k.board()['projects'][0]['effective_state'],'REVIEWING')
    def test_missing_source_and_claim_marker_block(self):
        aid=self.to_review()
        material=self.k.inspect(self.m['oc_id'])['object'];material['source']=''
        (self.k.vault.root/material['path']).write_bytes(encode(material))
        self.assertIn('Material requires',str(self.k.inspect(aid)['gate']['issues']))
        artifact=self.k.inspect(aid)['object'];artifact['body']=artifact['body'].replace('[[','[')
        (self.k.vault.root/artifact['path']).write_bytes(encode(artifact))
        self.assertIn('Draft Claim links',str(self.k.inspect(aid)['gate']['issues']))
    def test_manual_publication_tracking_requires_approved_version(self):
        aid=self.to_review()
        fields={'artifact':aid,'url':'https://example.com/software-fixture','published_at':'2026-09-08T00:00:00Z'}
        with self.assertRaises(Problem):self.k.add(self.p,'Publication','合成发表记录','手动观察记录',fields,self.token())
        self.approve(aid)
        with self.assertRaises(Problem):self.k.add(self.p,'Publication','坏地址','',dict(fields,url='javascript:bad'),self.token())
        self.k.add(self.p,'Publication','合成发表记录','手动软件验收观察，不代表实际发表。',fields,self.token())
        self.k.advance(self.p,'PUBLISHED',self.token())
        self.k.advance(self.p,'LEARNING',self.token())
        self.assertEqual(self.k.board()['projects'][0]['state'],'LEARNING')
    def test_journal_rollback_and_preserve_external_changes(self):
        before=self.token();original_atomic=atomic;calls=0
        def failing(path,data):
            nonlocal calls
            if path.suffix=='.md':
                calls+=1
                if calls==2:raise OSError('injected disk failure')
            original_atomic(path,data)
        req=self.k.request(self.p,'distill',[])
        with patch('opencontent.vault.atomic',failing),self.assertRaises(OSError):
            self.k.apply_result(self.p,'distill',response(req),req['token'],'fixture','disk')
        self.assertEqual(self.token(),before)
        target=self.k.vault.root/self.m['path'];original=target.read_text(encoding='utf-8')
        journal=[{'path':self.m['path'],'before':original,'after':original+'after'}]
        atomic(self.k.vault.runtime/'transaction.json',json.dumps(journal).encode())
        target.write_text(original+'human edit',encoding='utf-8')
        with self.assertRaises(Problem):self.k.vault.recover()
        self.assertTrue(target.read_text(encoding='utf-8').endswith('human edit'))
    def test_no_ai_manual_path(self):
        kid=self.k.add(self.p,'Knowledge','人工知识','明确保留资料来源',{'derived_from':[self.m['oc_id']]},self.token())['oc_id']
        self.k.advance(self.p,'DISTILLED',self.token())
        self.k.add(self.p,'Idea','人工想法','向读者展示来源',{'derived_from':[kid]},self.token())
        self.k.advance(self.p,'IDEA',self.token(),'写作应保留来源。');self.k.advance(self.p,'RESEARCHING',self.token())
        cid=self.k.add(self.p,'Claim','人工主张',STATEMENT,{'derived_from':[kid],'confidence':'medium'},self.token())['oc_id']
        self.k.add(self.p,'Evidence','人工证据','与原文一致',{'claim':cid,'material':self.m['oc_id'],'quote':STATEMENT,'relation':'supports'},self.token())
        self.k.advance(self.p,'ARGUMENT_READY',self.token());self.k.advance(self.p,'DRAFTING',self.token())
        req=self.k.request(self.p,'draft',[]);draft=response(req)['artifact']
        aid=self.k.add(self.p,'Artifact',draft['title'],draft['body'],{'derived_from':[cid],'author':'人工作者'},self.token())['oc_id']
        self.k.review(aid,'人工审查者',response({'stage':'critique','objects':[]})['axes'],True,'','独立人工审查',self.token())
        self.k.advance(self.p,'REVIEWING',self.token());self.approve(aid)
        self.assertTrue(self.k.inspect(aid)['gate']['approved'])
    def test_jobs_provider_independence_and_fail_resume(self):
        class Failing(FixtureProvider):
            def run(self,*args):raise RuntimeError('fixture unavailable')
        jobs=Jobs(self.k,{'different-agent':Failing()});self.addCleanup(jobs.close)
        first=jobs.submit(self.p)['id']
        self.wait_job(jobs,first);self.assertEqual(jobs.list()[0]['status'],'FAILED')
        jobs.providers['different-agent']=FixtureProvider()
        second=jobs.submit(self.p,resume=first)['id'];self.wait_job(jobs,second)
        self.assertEqual(jobs.list()[0]['status'],'SUCCEEDED')
        self.assertEqual(self.k.board()['projects'][0]['state'],'REVIEWING')
        self.assertEqual(len(jobs.list()[0]['detail']['attempts']),4)
    def wait_job(self,jobs,uid):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            row=next(j for j in jobs.list() if j['id']==uid)
            if row['status'] not in ('RUNNING','QUEUED'):return row
            time.sleep(.03)
        self.fail('Job failed to terminate')
    def test_cancel_restart_and_skill_discovery(self):
        class Blocking(FixtureProvider):
            def run(self,request,workspace,event):event.wait(5);raise Problem('cancelled')
        jobs=Jobs(self.k,{'blocking':Blocking()});self.addCleanup(jobs.close)
        uid=jobs.submit(self.p)['id'];jobs.cancel(uid);self.assertEqual(self.wait_job(jobs,uid)['status'],'CANCELLED')
        with self.k.vault.connection() as db:db.execute("UPDATE jobs SET status='RUNNING' WHERE id=?",(uid,))
        self.assertEqual(Jobs(self.k).list()[0]['status'],'INTERRUPTED')
        skill=Path(self.tmp.name)/'external-skill'/'SKILL.md';skill.parent.mkdir();skill.write_text('# Skill\nInspect evidence.',encoding='utf-8')
        self.assertEqual(discover_skills([skill.parent])[0]['path'],str(skill))


if __name__=='__main__':unittest.main()
