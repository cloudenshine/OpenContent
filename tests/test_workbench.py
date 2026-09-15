from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import test_kernel as fixtures
from opencontent import discovery, workbench
from opencontent.jobs import Jobs
from opencontent.kernel import Kernel
from opencontent.providers import AgentExecutionProvider, CodexProvider, ClaudeProvider
from opencontent.vault import Problem, encode

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.k=Kernel(self.tmp.name)
        self.note('知识来源追踪.md','知识来源追踪，需要明确出处。材料和主张应关联起来，以供复核。')
        self.note('旅行计划.md','旅行计划应提前安排路线，确认时间，收集行程信息与住宿需求。')
    def note(self,path,text):
        p=self.k.vault.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p
    def test_goal_ranking_selected_atomic_capture_and_duplicate_exclusion(self):
        r=discovery.recommend(self.k,'知识来源追踪')
        self.assertEqual(r['candidates'][0]['path'],'知识来源追踪.md')
        p=discovery.create_selected(self.k,'来源追踪教程','解释知识来源追踪','读者',[r['candidates'][0]],r['token'])
        objects,errors=self.k.read();self.assertFalse(errors)
        materials=[o for o in objects.values() if o['type']=='Material'];self.assertEqual(len(materials),1)
        self.assertFalse(self.k.source_issues(objects,p['oc_id']))
        suggestions=discovery.recommend(self.k)
        used=next(n for n in suggestions['candidates'] if n['path']=='知识来源追踪.md')
        self.assertTrue(used['existing_projects'])
        self.assertIn('旅行计划.md',[n['path'] for n in suggestions['candidates']])
        self.note('改名后的资料.md',materials[0]['body'])
        renamed=next(n for n in discovery.recommend(self.k)['candidates'] if n['path']=='改名后的资料.md')
        self.assertEqual(renamed['existing_projects'][0]['reason'],'内容已覆盖')
        with self.assertRaises(Problem):discovery.create_selected(self.k,p['title'],p['goal'],p['audience'],[],self.k.vault.token())
    def test_stale_selection_or_escaped_note_never_creates_partial_project(self):
        r=discovery.recommend(self.k,'来源');n=r['candidates'][0]
        self.note(n['path'],'来源文件已被修改。'*10)
        with self.assertRaises(Problem):discovery.create_selected(self.k,'新项目','目标','读者',[n],r['token'])
        with self.assertRaises(Problem):discovery.create_selected(self.k,'新项目','目标','读者',[{'path':'../private.md','hash':'x'}],r['token'])
        self.assertEqual(self.k.board()['projects'],[])
    def test_private_and_generated_folders_are_excluded(self):
        self.note('.private/secret.md','知识来源追踪私有内容。'*10)
        self.note('OpenContent-Workspace/chat.md','知识来源追踪生成内容。'*10)
        self.note('OpenContent-Exports/export.md','知识来源追踪重复内容。'*10)
        r=discovery.recommend(self.k,'来源')
        self.assertEqual([n['path'] for n in r['candidates']],['知识来源追踪.md'])

class ReplyProvider(AgentExecutionProvider):
    def __init__(self):self.requests=[];self.result=None
    def capabilities(self):return {'reason':True}
    def run(self,request,workspace,cancel_event):
        self.requests.append(deepcopy(request))
        return self.result or {'reply':'收到，我会沿用此前约定继续讨论。','revision':None,'illustrations':[],'images':[]}

class WorkbenchTests(unittest.TestCase):
    setUp=fixtures.KernelTests.setUp
    token=fixtures.KernelTests.token
    run_stage=fixtures.KernelTests.run_stage
    to_review=fixtures.KernelTests.to_review
    approve=fixtures.KernelTests.approve
    def wait(self,jobs,uid):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            job=next(j for j in jobs.list() if j['id']==uid)
            if job['status'] not in ('QUEUED','RUNNING'):
                for record in list(jobs.running.values()):record['thread'].join(1)
                return job
            time.sleep(.01)
        self.fail('job did not complete')
    def test_two_turn_history_restart_and_no_domain_mutation(self):
        provider=ReplyProvider();jobs=Jobs(self.k,{'reply':provider});self.addCleanup(jobs.close)
        before=self.k.read()[0]
        for message in ('文章面向初学者，请记住。','按刚才的读者继续给建议。'):
            uid=jobs.submit(self.p,expected=self.token(),instruction=message)['id']
            self.assertEqual(self.wait(jobs,uid)['status'],'SUCCEEDED')
        self.assertEqual(provider.requests[1]['history'][0]['user'],'文章面向初学者，请记住。')
        self.assertEqual(before,self.k.read()[0])
        self.assertEqual(len(workbench.history(Kernel(self.tmp.name),self.p)),2)
        self.assertEqual(self.k.request(self.p,'distill',[])['project_dialogue'][-1]['user'],'按刚才的读者继续给建议。')
    def revision(self,uid='a'*32):
        aid=self.to_review();self.approve(aid);a=self.k.inspect(aid)['object']
        request=workbench.request(self.k,self.p,'把结尾写得更清楚','revise',[],uid)
        result={'reply':'提出一版更清楚的结尾，请核对。','revision':{'artifact':aid,'title':a['title'],'body':a['body']+'\n\n请从一条具体主张开始复核。'},'illustrations':[],'images':[]}
        turn=workbench.complete(self.k,self.p,uid,result,self.k.vault.runtime)
        return aid,turn,request
    def test_revision_requires_apply_invalidates_approval_and_is_not_reapplied(self):
        aid,turn,request=self.revision()
        self.assertTrue(self.k.inspect(aid)['gate']['approved'])
        workbench.apply_revision(self.k,self.p,turn['id'],self.token())
        self.assertFalse(self.k.inspect(aid)['gate']['approved'])
        self.assertEqual(self.k.inspect(aid)['object']['state'],'REVIEWING')
        self.assertEqual(len(self.k.inspect(aid)['object']['versions']),1)
        with self.assertRaises(Problem):workbench.apply_revision(self.k,self.p,turn['id'],self.token())
    def test_stale_revision_never_overwrites_editor_changes(self):
        aid,turn,request=self.revision();a=self.k.inspect(aid)['object'];a['body']+='\n本人编辑。'
        (self.k.vault.root/a['path']).write_bytes(encode(a))
        with self.assertRaises(Problem):workbench.apply_revision(self.k,self.p,turn['id'],self.token())
        self.assertIn('本人编辑',self.k.inspect(aid)['object']['body'])
    def test_missing_image_capability_is_brief_only_and_path_escape_rejected(self):
        uid='b'*32;workbench.request(self.k,self.p,'为文章配图','illustrate',[],uid)
        result={'reply':'当前无图像工具，只能提供方案。','revision':None,'illustrations':[{'placement':'封面','prompt':'清晰的知识来源示意图','alt':'来源示意'}],'images':[]}
        turn=workbench.complete(self.k,self.p,uid,result,self.k.vault.runtime)
        self.assertEqual(turn['image_status'],'BRIEF_ONLY')
        result['images']=[{'path':'../secret.png','alt':'图','placement':'封面'}]
        with self.assertRaises(Problem):workbench.complete(self.k,self.p,uid,result,self.k.vault.runtime)
    def test_generated_image_is_imported_with_receipt_and_nonimage_rejected(self):
        uid='c'*32;workbench.request(self.k,self.p,'生成封面','illustrate',[],uid)
        workspace=self.k.vault.runtime/'image-run';workspace.mkdir()
        # Small known PNG fixture; not presented as a model-generated acceptance image.
        import base64
        (workspace/'image.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1cAAAAASUVORK5CYII='))
        result={'reply':'测试图像导入。','revision':None,'illustrations':[],'images':[{'path':'image.png','alt':'图','placement':'封面'}]}
        turn=workbench.complete(self.k,self.p,uid,result,workspace)
        self.assertEqual(turn['image_status'],'GENERATED')
        self.assertTrue(self.k.vault.safe(turn['images'][0]['path']).is_file())
        (workspace/'image.png').write_text('not an image')
        with self.assertRaises(Problem):workbench.complete(self.k,self.p,uid,result,workspace)
    def test_cancellation_and_error_persist_transcript(self):
        class Blocking(ReplyProvider):
            def run(self,request,workspace,cancel_event):
                cancel_event.wait(2);raise Problem('cancelled')
        jobs=Jobs(self.k,{'reply':Blocking()});self.addCleanup(jobs.close)
        uid=jobs.submit(self.p,expected=self.token(),instruction='讨论一下')['id']
        deadline=time.monotonic()+2
        while not workbench.history(self.k,self.p) and time.monotonic()<deadline:time.sleep(.01)
        jobs.cancel(uid);self.assertEqual(self.wait(jobs,uid)['status'],'CANCELLED')
        self.assertEqual(workbench.history(self.k,self.p)[0]['status'],'INTERRUPTED')

    def test_native_commands_preserve_model_defaults_and_limit_tool_scope(self):
        import sys
        codex=CodexProvider(sys.executable)
        regular=codex.command({'stage':'conversation'},Path('response.json'))
        image=codex.command({'stage':'illustrate'},Path('response.json'))
        self.assertIn('read-only',regular);self.assertIn('workspace-write',image)
        for argv in (regular,image):
            self.assertNotIn('--model',argv);self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',argv)
        claude=ClaudeProvider(sys.executable)
        argv=claude.command({},Path('response.json'))
        self.assertEqual(argv[argv.index('--tools')+1],'')
        self.assertIn('dontAsk',argv)
        self.assertFalse(claude.capabilities()['image_generation'])

if __name__=='__main__':unittest.main()
