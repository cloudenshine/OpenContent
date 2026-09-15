import http.client
import json
import tempfile
import threading
import unittest
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.k=Kernel(self.tmp.name);self.jobs=Jobs(self.k)
        self.server=Server(self.k,self.jobs);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.jobs.close();self.thread.join();self.tmp.cleanup()
    def call(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        default={'Authorization':'Bearer '+self.server.token,'Content-Type':'application/json'}
        default.update(headers or {})
        conn.request(method,path,json.dumps(body) if body is not None else None,default)
        res=conn.getresponse();data=json.loads(res.read());status=res.status;conn.close();return status,data
    def test_auth_origin_host_invalid_payload(self):
        self.assertEqual(self.call('GET','/board',headers={'Authorization':''})[0],401)
        self.assertEqual(self.call('GET','/board',headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.call('GET','/board',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.call('POST','/projects',[])[0],400)
        self.assertEqual(self.call('POST','/projects',{})[0],422)
        self.assertEqual(self.call('GET','/../CONTENT.md')[0],404)
    def test_real_http_persistence_no_agent(self):
        status,p=self.call('POST','/projects',{'title':'HTTP项目','goal':'验证持久化','audience':'测试人员'})
        self.assertEqual(status,200)
        self.assertTrue((self.k.vault.root/p['path']).is_file())
        self.assertEqual(self.call('POST','/jobs',{'project':p['oc_id']})[0],503)
        self.assertEqual(self.call('GET','/board')[1]['projects'][0]['state'],'CAPTURED')
        self.assertEqual(self.call('GET','/health')[1]['providers'],{})

    def test_discovery_and_conversation_routes_require_auth_and_validate_inputs(self):
        for route in ('/discovery','/projects/selected','/conversation/send','/conversation/apply','/providers/activate','/ideation/preview','/ideation/start','/ideation/status','/ideation/create','/ideation/retry'):
            self.assertEqual(self.call('POST',route,{},headers={'Authorization':''})[0],401)
            self.assertEqual(self.call('POST',route,{},headers={'Origin':'https://evil.example'})[0],403)
        (self.k.vault.root/'知识追踪.md').write_text('知识追踪需要明确来源，让材料与主张关联起来供读者复核。',encoding='utf-8')
        status,r=self.call('POST','/discovery',{'goal':'知识追踪'})
        self.assertEqual(status,200)
        status,p=self.call('POST','/projects/selected',{'title':'知识追踪教程','goal':'知识追踪','audience':'读者','selected':r['candidates'],'token':r['token']})
        self.assertEqual(status,200)
        self.assertEqual(self.call('POST','/conversation/history',{'project':p['oc_id']})[1]['turns'],[])
        self.assertEqual(self.call('POST','/conversation/send',{'project':p['oc_id'],'instruction':'请继续讨论','token':self.k.vault.token()})[0],503)
        self.assertEqual(self.call('POST','/conversation/apply',{'project':p['oc_id'],'turn':'missing','token':self.k.vault.token()})[0],422)
        self.assertEqual(self.call('POST','/providers/activate',{'name':'untrusted-shell'})[0],422)
        self.assertEqual(self.call('GET','/ideation/scope',headers={'Authorization':''})[0],401)
        self.assertEqual(self.call('GET','/ideation/scope')[0],200)
        self.assertEqual(self.call('POST','/ideation/preview',{'folders':['../escape']})[0],422)
        status,scope=self.call('POST','/ideation/preview',{'direction':'知识与写作'})
        self.assertEqual(status,200);self.assertNotIn('candidates',scope)
        self.assertEqual(self.call('POST','/ideation/start',{'preview':scope['id']})[0],503)
        self.assertEqual(self.call('POST','/ideation/status',{'id':'../escape'})[0],422)

    def test_capture_and_handoff_routes(self):
        _, p = self.call('POST','/projects',{'title':'捕获','goal':'验证 API','audience':'测试人员'})
        payload = {'project':p['oc_id'],'title':'摘录','body':'selected text','source':'vault:note.md','token':self.k.vault.token()}
        status, result = self.call('POST','/capture',payload)
        self.assertEqual(status,200);self.assertFalse(result['duplicate'])
        self.assertEqual(self.call('POST','/capture',payload)[0],409)
        payload['token'] = self.k.vault.token()
        self.assertTrue(self.call('POST','/capture',payload)[1]['duplicate'])
        self.assertEqual(self.call('POST','/handoff',{'artifact':p['oc_id'],'token':self.k.vault.token()})[0],422)

    def test_lifecycle_http_routes_and_external_write_auth(self):
        self.assertEqual(self.call('GET','/sources')[0],200)
        self.assertEqual(self.call('GET','/publications')[1]['channels'],[])
        for path in ('/channels','/channels/cover','/publications/confirm','/publications/reconcile','/feedback'):
            self.assertEqual(self.call('POST',path,{},headers={'Authorization':''})[0],401)
            self.assertEqual(self.call('POST',path,{},headers={'Origin':'https://evil.example'})[0],403)
        _,p=self.call('POST','/projects',{'title':'计划项目','goal':'端点验证','audience':'测试员'})
        status,planned=self.call('POST','/projects/plan',{'project':p['oc_id'],'planned_for':'2026-09-22','token':self.k.vault.token()})
        self.assertEqual(status,200);self.assertEqual(planned['planning']['planned_for'],'2026-09-22')


if __name__=='__main__':unittest.main()
