from copy import deepcopy
import tempfile
import time
import unittest
from opencontent import ideation, discovery
from opencontent.jobs import Jobs
from opencontent.kernel import Kernel
from opencontent.providers import AgentExecutionProvider
from opencontent.vault import Problem

class Synthesizer(AgentExecutionProvider):
    def __init__(self):self.stages=[];self.before_return=None
    def capabilities(self):return {'reason':True}
    def run(self,req,workspace,event):
        self.stages.append(req['stage'])
        if req['stage']=='classify':
            result={'themes':[{'id':'t1','label':'质量控制','summary':'通过明确依据减少不可复核判断。'},
                              {'id':'t2','label':'认知负担','summary':'通过限制在制工作改善注意力分配。'}],
                    'cards':[{'source':s['id'],'themes':['t1' if i%2==0 else 't2'],'insight':'资料提供了一个明确的方法与边界。','evidence_id':s['passages'][0]['id']} for i,s in enumerate(req['sources'])]}
        else:
            result={'ideas':[{'title':'为什么创作系统需要限制在制主张','question':'如何把工作量限制应用到证据核查？','audience':'知识创作者',
                             'promise':'形成一个可试验的审查排队方法。','collision':'将限制在制工作的排队思路迁移到证据核查，比较吞吐与质量之间的关系。',
                             'sources':[{'id':c['source'],'role':'提供核查方法或工作量限制视角。'} for c in req['source_map']['cards']],
                             'outline':['解释两种方法解决的不同问题','提出组合假设和验证方式'],
                             'novelty':{'status':'extension' if req['existing_projects'] else 'new','nearest_project':req['existing_projects'][0]['id'] if req['existing_projects'] else None,'difference':'从保存来源扩展到安排有限的核查注意力。'},
                             'gaps':['需要实际编辑场景验证工作量阈值。']}],'insufficient':''}
        if self.before_return:self.before_return(req)
        return result

class IdeationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.k=Kernel(self.tmp.name)
        self.a='事实核查应保留原文与引用关系，让主张能够复查，同时区分证据支持与推测。'
        self.b='看板限制同时进行的任务，避免过多任务争抢注意力；这是一条需要结合场景调整的方法。'
        (self.k.vault.root/'事实核查.md').write_text(self.a,encoding='utf-8')
        (self.k.vault.root/'看板.md').write_text(self.b,encoding='utf-8')
        self.provider=Synthesizer();self.jobs=Jobs(self.k,{'synth':self.provider});self.addCleanup(self.jobs.close)
    def execute(self):
        pre=ideation.preview(self.k);self.jobs.discover(pre['id'],'synth');deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            row=ideation.read(self.k,pre['id'])
            if row['status'] not in ('RUNNING','QUEUED'):
                for v in list(self.jobs.running.values()):v['thread'].join(1)
                return row
            time.sleep(.01)
        self.fail('synthesis timeout')
    def test_two_stages_cross_source_idea_creates_multi_material_project(self):
        row=self.execute();self.assertEqual(row['status'],'SUCCEEDED',row.get('error'))
        self.assertEqual(self.provider.stages,['classify','synthesize'])
        idea=row['result']['ideas'][0];self.assertEqual(len(idea['sources']),2)
        p=ideation.create(self.k,row['id'],idea['id'])
        self.assertEqual(self.k.board()['projects'][0]['counts']['Material'],2)
        self.assertIn('组合假设',str(p['editorial_brief']['outline']))
        self.assertTrue(self.k.vault.safe(row['path']).is_file())
        with self.assertRaises(Problem):ideation.create(self.k,row['id'],idea['id'])
    def test_used_source_remains_available_for_new_question(self):
        note=discovery.recommend(self.k,'事实核查')['candidates'][0]
        discovery.create_selected(self.k,'记录事实出处','解释为什么应保存出处','读者',[note],self.k.vault.token())
        row=self.execute();self.assertEqual(row['status'],'SUCCEEDED')
        self.assertEqual(len(row['result']['ideas']),1)
        self.assertEqual(row['result']['ideas'][0]['novelty']['status'],'extension')
    def test_status_explains_stale_results_before_adoption(self):
        row=self.execute()
        self.assertTrue(ideation.status(self.k,row['id'])['adoption']['available'])
        (self.k.vault.root/'事实核查.md').write_text('资料已更新，旧候选不能直接采用。',encoding='utf-8')
        stale=ideation.status(self.k,row['id'])
        self.assertFalse(stale['adoption']['available'])
        self.assertTrue(stale['adoption']['reason'])
        self.assertEqual(stale['result'],row['result'])
    def test_one_source_and_duplicate_copies_do_not_make_a_collision(self):
        (self.k.vault.root/'看板.md').write_text(self.a,encoding='utf-8')
        pre=ideation.preview(self.k);self.assertEqual(pre['stats']['selected'],1)
        with self.assertRaises(Problem):self.jobs.discover(pre['id'])
        self.assertFalse(self.provider.stages)
    def test_fabricated_quotes_and_single_source_ideas_rejected(self):
        pre=ideation.preview(self.k);s=ideation.load_snapshot(self.k,pre['id'])
        mapping=self.provider.run(ideation.classify_request(s),None,None)
        bad=deepcopy(mapping);bad['cards'][0]['quote']='原文不存在的编造引文。'
        with self.assertRaises(Problem):ideation.validate_map(bad,s)
        ideas=self.provider.run(ideation.synthesis_request(s,mapping),None,None)
        ideas['ideas'][0]['sources']=ideas['ideas'][0]['sources'][:1]
        with self.assertRaises(Problem):ideation.validate_ideas(ideas,s,mapping)
    def test_duplicate_question_is_excluded_and_cannot_be_created(self):
        self.k.create_project('为什么创作系统需要限制在制主张','如何把工作量限制应用到证据核查？','读者')
        row=self.execute();self.assertEqual(row['status'],'SUCCEEDED');self.assertFalse(row['result']['ideas'])
        self.assertEqual(len(row['result']['excluded']),1)
        with self.assertRaises(Problem):ideation.create(self.k,row['id'],row['result']['excluded'][0]['id'])
    def test_source_change_during_model_run_fails_without_creating_project(self):
        self.provider.before_return=lambda req:(self.k.vault.root/'看板.md').write_text(self.b+'新内容',encoding='utf-8')
        row=self.execute();self.assertEqual(row['status'],'FAILED');self.assertFalse(self.k.board()['projects'])
    def test_no_viable_idea_is_valid_with_reason(self):
        pre=ideation.preview(self.k);s=ideation.load_snapshot(self.k,pre['id']);mapping=self.provider.run(ideation.classify_request(s),None,None)
        result=ideation.validate_ideas({'ideas':[],'insufficient':'现有两类材料之间缺少可解释的关联，需要补充共同应用场景。'},s,mapping)
        self.assertFalse(result['ideas'])

    def test_passage_ids_preserve_markdown_crlf_and_reject_cross_source(self):
        pre=ideation.preview(self.k);s=ideation.load_snapshot(self.k,pre['id'])
        s['sources'][0]['excerpt']='**可查找性**: 文件名包含日期 + 类型标识\r\n必须从文件重建\r\n'
        raw=self.provider.run(ideation.classify_request(s),None,None)
        mapping=ideation.validate_map(raw,s)
        self.assertEqual(mapping['cards'][0]['quote'],s['sources'][0]['excerpt'])
        bad=deepcopy(raw);bad['cards'][0]['evidence_id']=raw['cards'][1]['evidence_id']
        with self.assertRaisesRegex(Problem,'其他资料'):ideation.validate_map(bad,s)
        bad['cards'][0]['evidence_id']='s1:p999'
        with self.assertRaises(Problem):ideation.validate_map(bad,s)

    def test_sixty_source_map_uses_resolved_original_passages(self):
        pre=ideation.preview(self.k);s=ideation.load_snapshot(self.k,pre['id'])
        s['sources']=[{**s['sources'][0],'id':'s'+str(i),'excerpt':f'资料 {i} 的**方法**必须保留边界。\r\n'+('核查原文内容。'*70)} for i in range(1,61)]
        request=ideation.classify_request(s)
        mapping=ideation.validate_map(self.provider.run(request,None,None),s)
        self.assertEqual(len(mapping['cards']),60)
        for card,source in zip(mapping['cards'],s['sources']):self.assertIn(card['quote'],source['excerpt'])

    def test_passages_do_not_quote_across_sample_gaps(self):
        source={'id':'s1','excerpt':'开头的原文内容'*100+'\n[中段摘录]\n'+'中部的原文内容'*60+'\n[末段摘录]\n'+'最后的原文内容'*60}
        for p in ideation.passages(source):
            self.assertIn(p['text'],source['excerpt']);self.assertNotIn('摘录]',p['text'])
        short_tail={'id':'s2','excerpt':'完整原文'*100+'末尾字'}
        self.assertEqual(ideation.passages(short_tail),[{'id':'s2:p1','text':short_tail['excerpt']}])

    def wait_run(self,run):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            row=ideation.read(self.k,run)
            if row['status'] not in ('RUNNING','QUEUED'):
                for v in list(self.jobs.running.values()):v['thread'].join(1)
                return row
            time.sleep(.01)
        self.fail('timeout')

    def test_folder_scope_is_honored_before_sending_and_limits_are_validated(self):
        for folder in ('Research','Research/Sub','Private'):
            directory=self.k.vault.root/folder;directory.mkdir(parents=True,exist_ok=True)
            (directory/'memo.md').write_text(folder+'资料具有完整的论点和充足的正文供本地选择及核验。',encoding='utf-8')
        pre=ideation.preview(self.k,folders=['Research'],limit=2)
        snapshot=ideation.load_snapshot(self.k,pre['id'])
        self.assertEqual(len(snapshot['sources']),2)
        self.assertTrue(all(s['path'].startswith('Research/') for s in snapshot['sources']))
        self.assertNotIn('Private',str(ideation.classify_request(snapshot)))
        for folders in (['../escape'],['/absolute'],['Private/../Research'],['_hidden'],['Research\\Sub']):
            with self.assertRaises(Problem):ideation.preview(self.k,folders=folders)
        for limit in (1,61,True,'24'):
            with self.assertRaises(Problem):ideation.preview(self.k,limit=limit)
        root_only=ideation.load_snapshot(self.k,ideation.preview(self.k,folders=['.'])['id'])
        self.assertTrue(all('/' not in s['path'] for s in root_only['sources']))

    def test_retry_after_restart_reuses_classification_but_preserves_failed_receipt(self):
        def fail(req):
            if req['stage']=='synthesize':raise Problem('temporary synthesis failure')
        self.provider.before_return=fail
        failed=self.execute();self.assertEqual(failed['status'],'FAILED')
        self.jobs.close();self.jobs=Jobs(self.k,{'synth':self.provider});self.addCleanup(self.jobs.close)
        self.provider.before_return=None
        retry=self.jobs.retry_ideation(failed['id']);done=self.wait_run(retry['id'])
        self.assertEqual(done['status'],'SUCCEEDED',done.get('error'))
        self.assertEqual(self.provider.stages,['classify','synthesize','synthesize'])
        self.assertEqual(ideation.read(self.k,failed['id'])['status'],'FAILED')
        self.assertEqual(done['retry_of'],failed['id'])

    def test_retry_refuses_changed_material(self):
        def fail(req):
            if req['stage']=='synthesize':raise Problem('temporary failure')
        self.provider.before_return=fail;failed=self.execute()
        (self.k.vault.root/'看板.md').write_text(self.b+'资料已改变',encoding='utf-8')
        with self.assertRaises(Problem):self.jobs.retry_ideation(failed['id'])
        self.assertEqual(self.provider.stages,['classify','synthesize'])

    def test_corrupt_checkpoint_reclassifies_instead_of_trusting_it(self):
        def fail(req):
            if req['stage']=='synthesize':raise Problem('temporary failure')
        self.provider.before_return=fail;failed=self.execute()
        ideation.path(self.k,failed['id'],'classification.json').write_text('{bad json',encoding='utf-8')
        self.provider.before_return=None
        done=self.wait_run(self.jobs.retry_ideation(failed['id'])['id'])
        self.assertEqual(done['status'],'SUCCEEDED')
        self.assertEqual(self.provider.stages,['classify','synthesize','classify','synthesize'])

    def test_missing_interrupted_receipt_does_not_prevent_kernel_start(self):
        import json,uuid
        from opencontent.vault import now
        run=uuid.uuid4().hex
        with self.k.vault.connection() as db:
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',(run,'@ideation','RUNNING',json.dumps({'kind':'ideation','stage':'classify'}),now(),now()))
        recovered=Jobs(self.k);self.addCleanup(recovered.close)
        record=next(j for j in recovered.list() if j['id']==run)
        self.assertEqual(record['status'],'INTERRUPTED')
        self.assertIn('记录缺失',record['detail']['error'])

    def test_repeated_status_polling_and_restart_result(self):
        for _ in range(12):
            row=self.execute();self.assertEqual(row['status'],'SUCCEEDED',row.get('error'))
            self.assertEqual(ideation.read(Kernel(self.tmp.name),row['id'])['status'],'SUCCEEDED')

if __name__=='__main__':unittest.main()
