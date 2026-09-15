"""Lifecycle and WeChat protocol fixtures; no real WeChat account or publication."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_kernel as fixtures
from opencontent import lifecycle
from opencontent.kernel import Kernel
from opencontent.publishing import Publishing, preview_hash, render_content
from opencontent.publishing_adapters import WeChat, UnknownOutcome, RemoteRejected
from opencontent.vault import Problem, encode

class WeChatFixture:
    def __init__(self):
        self.drafts={};self.articles={};self.calls=[];self.publish_status=1;self.timeout=None;self.rejection=None;self.onwrite=None
        self.appid='wx0123456789abcdef'
    def identity(self):return {'kind':'wechat','appid':self.appid}
    def token(self):return 'fixture-token'
    def add_draft(self,payload):
        self.calls.append('draft/add')
        if self.rejection:raise self.rejection
        self.drafts['draft-id']={'news_item':[deepcopy(payload)]}
        if self.onwrite:self.onwrite()
        if self.timeout=='draft':raise UnknownOutcome('fixture timeout after remote commit')
        return {'media_id':'draft-id'}
    def get_draft(self,mid):self.calls.append('draft/get');return deepcopy(self.drafts[mid])
    def submit(self,mid):
        self.calls.append('freepublish/submit')
        if self.rejection:raise self.rejection
        self.articles['article-id']=deepcopy(self.drafts[mid])
        if self.onwrite:self.onwrite()
        if self.timeout=='publish':raise UnknownOutcome('fixture timeout after remote commit')
        return {'errcode':0,'publish_id':'publish-id'}
    def status(self,pid):
        self.calls.append('freepublish/get')
        return {'publish_id':pid,'publish_status':self.publish_status,'article_id':'article-id',
            'article_detail':{'count':1,'item':[{'idx':1,'article_url':'https://mp.weixin.qq.com/s?__biz=fixture&mid=1'}]}}
    def article(self,aid):self.calls.append('freepublish/getarticle');return deepcopy(self.articles[aid])

class LifecycleTests(unittest.TestCase):
    setUp=fixtures.KernelTests.setUp
    token=fixtures.KernelTests.token
    run_stage=fixtures.KernelTests.run_stage
    to_review=fixtures.KernelTests.to_review
    approve=fixtures.KernelTests.approve
    def ready(self):
        self.aid=self.to_review();self.approve(self.aid);self.remote=WeChatFixture();self.pub=Publishing(self.k,{'fixture':self.remote})
    def prepare(self,action='draft',draft=None):
        return self.pub.prepare(self.aid,'fixture',action,self.token(),
            {'title':'软件验收稿','author':'验收','digest':'纯软件协议验收，不是实际发表。','thumb_media_id':'cover-fixture'},draft)
    def confirm(self,p):return self.pub.confirm(p['oc_id'],p['preview_hash'],'合成测试确认人',self.token())
    def remote_draft(self):return self.confirm(self.prepare())
    def published(self):
        self.remote.publish_status=0;draft=self.remote_draft();return self.confirm(self.prepare('publish',draft['oc_id']))

    def test_reader_output_omits_internal_provenance_preserves_local_graph(self):
        self.ready()
        before=self.k.read()[0]
        local=deepcopy(before[self.aid])
        draft=self.remote_draft()
        content=draft['payload']['content']
        for internal in ('参考来源', '本地材料', '〔1〕', '[['):
            self.assertNotIn(internal,content)
        self.assertIn(fixtures.STATEMENT,content)
        after=self.k.read()[0]
        self.assertEqual(local,after[self.aid])
        for uid,obj in before.items():
            if obj['type'] in ('Claim','Evidence','Material','Review'):
                self.assertEqual(obj,after[uid])
        self.assertEqual(draft['delivery_status'],'REMOTE_DRAFT')

    def test_reader_output_preserves_authored_links_and_html_escaping(self):
        cid='a'*32
        artifact={'derived_from':[cid], 'body':f'观点[[{cid}|内部证据]]。\n\n[公开出处](https://example.org)\n\n<script>alert(1)</script>'}
        content=render_content({},artifact)
        self.assertNotIn('内部证据',content)
        self.assertIn('观点。',content)
        self.assertIn('href="https://example.org"',content)
        self.assertIn('&lt;script&gt;',content)

    def test_source_change_review_gate_refresh_history_and_cross_project_reuse(self):
        source=self.k.vault.root/'source.md';source.write_text(fixtures.STATEMENT,encoding='utf-8')
        material=self.k.inspect(self.m['oc_id'])['object'];material['source']='vault:source.md'
        material['source_note_hash']=lifecycle.note_snapshot(self.k.vault,material['source'])['hash']
        (self.k.vault.root/material['path']).write_bytes(encode(material))
        self.ready();self.assertTrue(self.k.inspect(self.aid)['gate']['approved'])
        source.write_text(fixtures.STATEMENT+'\n新增来源说明。',encoding='utf-8')
        self.assertFalse(self.k.inspect(self.aid)['gate']['approved'])
        with self.assertRaises(Problem):self.prepare()
        row=lifecycle.library(self.k)['sources'][0]['materials'][0];self.assertEqual(row['freshness'],'CHANGED')
        preview=lifecycle.refresh_preview(self.k,material['oc_id'])
        updated=lifecycle.refresh_source(self.k,material['oc_id'],preview['current_body'],preview['source_hash'],preview['token'])
        self.assertEqual(updated['versions'][0]['body'],fixtures.STATEMENT)
        self.assertFalse(self.k.inspect(self.aid)['gate']['approved'])
        pid=self.k.create_project('新项目','复用可靠来源','编辑')['oc_id']
        result=lifecycle.reuse_material(self.k,material['oc_id'],pid,self.token())
        self.assertEqual(result['object']['reused_from'],material['oc_id'])
        self.assertTrue(lifecycle.reuse_material(self.k,material['oc_id'],pid,self.token())['duplicate'])
        self.assertEqual(len(lifecycle.library(self.k)['sources']),1)

    def test_source_changed_again_and_missing_refused(self):
        source=self.k.vault.root/'source.md';source.write_text('原文',encoding='utf-8')
        m=self.k.capture(self.p,'原文','原文','vault:source.md',self.token())['object']
        preview=lifecycle.refresh_preview(self.k,m['oc_id']);source.write_text('新文',encoding='utf-8')
        with self.assertRaises(Problem):lifecycle.refresh_source(self.k,m['oc_id'],'原文',preview['source_hash'],self.token())
        source.unlink();self.assertEqual(lifecycle.freshness(self.k.vault,m)['status'],'MISSING')

    def test_plan_does_not_invalidate_editorial_approval(self):
        self.ready();lifecycle.plan_project(self.k,self.p,'2026-09-20',self.token())
        self.assertTrue(self.k.inspect(self.aid)['gate']['approved'])
        with self.assertRaises(Problem):lifecycle.plan_project(self.k,self.p,'tomorrow',self.token())

    def test_two_confirmations_async_status_and_feedback_reuse_restart(self):
        self.ready();draft=self.remote_draft();self.assertEqual(draft['delivery_status'],'REMOTE_DRAFT')
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'APPROVED')
        publishing=self.confirm(self.prepare('publish',draft['oc_id']));self.assertEqual(publishing['delivery_status'],'SUBMITTED')
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'APPROVED')
        with self.assertRaises(Problem):self.prepare()
        self.remote.publish_status=0
        self.pub=Publishing(Kernel(self.tmp.name),{'fixture':self.remote})
        published=self.pub.reconcile(publishing['oc_id']);self.assertEqual(published['delivery_status'],'PUBLISHED')
        self.assertIn('?__biz=',published['url']);self.assertEqual(self.k.inspect(self.p)['object']['state'],'PUBLISHED')
        fb=lifecycle.feedback(self.k,published['oc_id'],'微信后台 2026-09-08','读者询问具体步骤','下次增加逐步示例',self.token())
        with self.assertRaises(Problem):lifecycle.next_project(self.k,published['oc_id'],fb['id'],'标题','目标','读者',self.token())
        lifecycle.judge_feedback(self.k,published['oc_id'],fb['id'],'accept','编辑','多条独立反馈均指出步骤不足。',self.token())
        nextp=lifecycle.next_project(self.k,published['oc_id'],fb['id'],'教程改进','加入逐步示例','新读者',self.token())
        self.assertEqual(nextp['object']['editorial_lessons'][0]['lesson'],'下次增加逐步示例')
        self.assertTrue(lifecycle.next_project(self.k,published['oc_id'],fb['id'],'标题','目标','读者',self.token())['duplicate'])
        self.pub.reconcile(published['oc_id']);self.assertEqual(self.k.inspect(self.p)['object']['state'],'LEARNING')
        self.assertEqual(self.remote.calls.count('freepublish/submit'),1)

    def test_duplicate_confirmation_and_stale_preview_never_write(self):
        self.ready();preview=self.prepare()
        with self.assertRaises(Problem):self.pub.confirm(preview['oc_id'],'wrong','editor',self.token())
        self.assertFalse(self.remote.calls)
        self.confirm(preview)
        with self.assertRaises(Problem):self.confirm(preview)
        self.assertEqual(self.remote.calls.count('draft/add'),1)

    def test_manually_tampered_outbox_cannot_bypass_approved_body(self):
        self.ready();preview=self.prepare();record=self.k.inspect(preview['oc_id'])['object']
        record['payload']['content']='<p>未经审查的正文</p>'
        (self.k.vault.root/record['path']).write_bytes(encode(record))
        with self.assertRaises(Problem):self.pub.confirm(record['oc_id'],preview_hash(record),'编辑',self.token())
        self.assertFalse(self.remote.calls)

    def test_recovery_cannot_bind_different_article(self):
        self.ready();self.remote.timeout='draft';draft=self.remote_draft()
        self.remote.drafts['draft-id']['news_item'][0]['title']='另一篇文章'
        with self.assertRaises(Problem):self.pub.reconcile(draft['oc_id'],'draft-id')
        self.assertFalse(self.k.inspect(draft['oc_id'])['object'].get('remote_media_id'))

    def test_unknown_draft_never_resubmits_and_manual_id_readback_recovers(self):
        self.ready();self.remote.timeout='draft';draft=self.remote_draft()
        self.assertEqual(draft['delivery_status'],'UNKNOWN')
        with self.assertRaises(Problem):self.pub.reconcile(draft['oc_id'])
        with self.assertRaises(Problem):self.prepare()
        result=Publishing(Kernel(self.tmp.name),{'fixture':self.remote}).reconcile(draft['oc_id'],'draft-id')
        self.assertEqual(result['delivery_status'],'REMOTE_DRAFT');self.assertEqual(self.remote.calls.count('draft/add'),1)

    def test_unknown_publish_id_can_only_bind_after_content_verified(self):
        self.ready();draft=self.remote_draft();self.remote.timeout='publish'
        receipt=self.confirm(self.prepare('publish',draft['oc_id']));self.assertEqual(receipt['delivery_status'],'UNKNOWN')
        with self.assertRaises(Problem):self.pub.reconcile(receipt['oc_id'],'publish-id')
        self.remote.publish_status=0
        self.assertEqual(self.pub.reconcile(receipt['oc_id'],'publish-id')['delivery_status'],'PUBLISHED')
        self.assertEqual(self.remote.calls.count('freepublish/submit'),1)

    def test_rejected_permission_is_failed_and_secret_not_reflected(self):
        self.ready();self.remote.rejection=RemoteRejected('微信接口错误 48001：账号无权限')
        self.assertEqual(self.remote_draft()['delivery_status'],'FAILED')
        with self.assertRaises(RemoteRejected) as e:WeChat.check({'errcode':48001,'errmsg':'sensitive-secret'})
        self.assertNotIn('sensitive-secret',str(e.exception))

    def test_remote_drift_blocks_publish_without_overwriting(self):
        self.ready();draft=self.remote_draft();preview=self.prepare('publish',draft['oc_id'])
        self.remote.drafts['draft-id']['news_item'][0]['content']+='远端人工编辑'
        with self.assertRaises(Problem):self.confirm(preview)
        self.assertNotIn('freepublish/submit',self.remote.calls)

    def test_local_edit_during_remote_commit_preserves_receipt_but_not_current_approval(self):
        self.ready();draft=self.remote_draft();preview=self.prepare('publish',draft['oc_id']);self.remote.publish_status=0
        file=self.k.vault.root/self.k.inspect(self.aid)['object']['path']
        self.remote.onwrite=lambda:file.write_bytes(file.read_bytes()+b'\nlocal change\n')
        result=self.confirm(preview);self.assertEqual(result['delivery_status'],'PUBLISHED')
        self.assertFalse(self.pub.list()['publications'][0]['current_approval'])
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'APPROVED')

    def test_local_ack_failure_recovers_id_without_second_post(self):
        self.ready();preview=self.prepare();real=self.pub.persist;failed=False
        def fail_once(uid,changes,event,intent=None):
            nonlocal failed
            if changes.get('remote_media_id') and not failed:
                failed=True;raise OSError('fixture disk failure')
            return real(uid,changes,event,intent)
        with patch.object(self.pub,'persist',side_effect=fail_once):result=self.confirm(preview)
        self.assertEqual(result['delivery_status'],'UNKNOWN')
        self.assertEqual(self.pub.reconcile(result['oc_id'])['delivery_status'],'REMOTE_DRAFT')
        self.assertEqual(self.remote.calls.count('draft/add'),1)

    def test_failure_and_withdrawal_are_not_success(self):
        self.ready();draft=self.remote_draft();receipt=self.confirm(self.prepare('publish',draft['oc_id']))
        for state in (2,3,4,5,6):
            self.remote.publish_status=state;result=self.pub.reconcile(receipt['oc_id'])
            self.assertEqual(result['delivery_status'],'FAILED' if state<5 else 'WITHDRAWN')
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'APPROVED')

    def test_published_revision_requires_new_review_and_keeps_old_receipt(self):
        self.ready();original=self.published();old_hash=original['context_hash']
        with self.assertRaises(Problem):self.prepare()
        file=self.k.vault.root/self.k.inspect(self.aid)['object']['path']
        file.write_bytes(file.read_bytes()+b'\nRevised explanation for the next edition.\n')
        self.assertFalse(self.pub.list()['publications'][0]['current_approval'])
        with self.assertRaises(Problem):self.prepare()
        self.run_stage('critique');self.approve(self.aid);preview=self.prepare()
        self.assertTrue(any(h['from']=='PUBLISHED' and h['to']=='REVIEWING' for h in self.k.inspect(self.p)['object']['history']))
        self.assertNotEqual(preview['context_hash'],old_hash)
        self.assertEqual(self.k.inspect(original['oc_id'])['object']['context_hash'],old_hash)
        self.assertEqual(self.remote.calls.count('freepublish/submit'),1)

    def test_token_expiry_does_not_retry_content_write(self):
        writes=[]
        def transport(path,body,kind,write):
            if path.endswith('stable_token'):return {'access_token':'expired-test-token','expires_in':7200}
            writes.append(path);return {'errcode':42001,'errmsg':'expired-test-token'}
        adapter=WeChat('wx0123456789abcdef','test-secret',transport)
        with self.assertRaises(RemoteRejected):adapter.add_draft({'title':'fixture'})
        self.assertEqual(len(writes),1);self.assertFalse(adapter.cached_token)

    def test_other_rejected_artifact_prevents_project_publication_promotion(self):
        self.ready();self.published();first=self.aid
        original=self.k.inspect(first)['object']
        other=self.k.add(self.p,'Artifact','第二份软件验收稿',original['body'],
            {'derived_from':original['derived_from'],'author':'fixture:second-writer'},self.token())
        axes={axis:{'status':'PASS','reason':'合成软件审查，验证独立稿件批准。'} for axis in fixtures.AXES}
        self.k.review(other['oc_id'],'fixture:second-critic',axes,True,'','合成第二稿审查',self.token())
        self.aid=other['oc_id'];self.approve(self.aid);second=self.published()
        self.k.decide(first,'reject','软件编辑','第一份稿件需要重新核对，暂不接受。',self.token())
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'REVIEWING')
        self.pub.reconcile(second['oc_id'])
        self.assertEqual(self.k.inspect(self.p)['object']['state'],'REVIEWING')

    def test_configuration_credentials_encrypted_and_not_returned(self):
        self.ready();channel=self.pub.configure('测试公众号','wx0123456789abcdef','LOCAL-ONLY-TEST-SECRET')
        self.assertNotIn('SECRET',json.dumps(channel));self.assertNotIn('SECRET',json.dumps(self.pub.configs()))
        encrypted=list((self.k.vault.root/'.opencontent/credentials').glob('*.bin'))[0].read_bytes()
        self.assertNotIn(b'LOCAL-ONLY-TEST-SECRET',encrypted)
        self.assertEqual(self.pub.adapter(channel['id']).secret,'LOCAL-ONLY-TEST-SECRET')

    def test_draft_only_account_can_create_draft_but_cannot_publish(self):
        self.ready();self.pub=Publishing(self.k)
        channel=self.pub.configure('个人公众号','wx0123456789abcdef','TEST_ONLY_SECRET')
        self.assertEqual(channel['publish_mode'],'draft_only')
        with patch.object(self.pub,'adapter',return_value=self.remote):
            preview=self.pub.prepare(self.aid,channel['id'],'draft',self.token(),
                {'title':'个人号验收','digest':'软件测试，非真实发表','thumb_media_id':'test-cover'})
            draft=self.confirm(preview)
            self.assertEqual(draft['delivery_status'],'REMOTE_DRAFT')
            with self.assertRaises(Problem) as error:
                self.pub.prepare(self.aid,channel['id'],'publish',self.token(),draft_publication=draft['oc_id'])
            self.assertEqual(error.exception.status,403)
            self.assertNotIn('freepublish/submit',self.remote.calls)

    def test_publish_preview_blocked_after_account_mode_restricted(self):
        self.ready();self.pub=Publishing(self.k)
        channel=self.pub.configure('接口验收','wx0123456789abcdef','TEST_ONLY_SECRET',publish_mode='draft_and_publish')
        with patch.object(self.pub,'adapter',return_value=self.remote):
            draft=self.confirm(self.pub.prepare(self.aid,channel['id'],'draft',self.token(),
                {'title':'模式变更验收','digest':'软件测试，非真实发表','thumb_media_id':'test-cover'}))
            preview=self.pub.prepare(self.aid,channel['id'],'publish',self.token(),draft_publication=draft['oc_id'])
            self.pub.configure('接口验收','wx0123456789abcdef','TEST_ONLY_SECRET',channel_id=channel['id'],publish_mode='draft_only')
            with self.assertRaises(Problem):self.confirm(preview)
            self.assertNotIn('freepublish/submit',self.remote.calls)

    def test_wechat_protocol_token_cache_and_no_retry(self):
        calls=[]
        def transport(path,body,kind,write):
            calls.append((path,json.loads(body),write))
            if path.endswith('stable_token'):return {'access_token':'fixture-token','expires_in':7200}
            return {'media_id':'draft-fixture'}
        api=WeChat('wx0123456789abcdef','never-real',transport)
        api.add_draft({'title':'协议草稿'});api.get_draft('draft-fixture')
        self.assertEqual(len(calls),3);self.assertEqual(calls[0][1]['force_refresh'],False)
        self.assertEqual(calls[1][1],{'articles':[{'title':'协议草稿'}]});self.assertTrue(calls[1][2]);self.assertFalse(calls[2][2])
        self.assertTrue(calls[2][0].startswith('/cgi-bin/draft/get?access_token='))

if __name__=='__main__':unittest.main()
