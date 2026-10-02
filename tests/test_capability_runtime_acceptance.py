"""HTTP/runtime acceptance checks for production-honest creative execution."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from opencontent.kernel import Kernel
from opencontent.jobs import Jobs
from opencontent.server import Server
from opencontent.capabilities import CapabilityRuntime, PackRegistry
from opencontent.capabilities.validation import validate_workspace_path
from opencontent.vault import Problem

class Provider:
    def __init__(self, response): self.response = response; self.requests = []
    def capabilities(self): return {'reason': True, 'image_generation': False}
    def run(self, request, workspace, cancel_event):
        self.requests.append(request)
        return self.response

class RuntimeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.kernel = Kernel(self.tmp.name)
        self.project = self.kernel.create_project('Acceptance', 'Goal', 'Audience')['oc_id']
        self.jobs = Jobs(self.kernel)
        self.registry = PackRegistry();self.registry.discover([Path(__file__).resolve().parents[1] / 'packs'])
        self.runtime = CapabilityRuntime(self.kernel, self.registry, jobs=self.jobs)
    def request(self, task='long-scan', **extra):
        return dict(schema='opencontent.creative-task.v1', project=self.project, pack='narrative', profile='general-fiction', task=task, **extra)
    def test_missing_market_input_fails_and_saves_failed_receipt(self):
        for task in ('long-scan', 'short-scan'):
            with self.assertRaises(Problem): self.runtime.execute_task(self.request(task), run_id=task)
            receipt=json.loads((Path(self.tmp.name)/f'.opencontent/runs/{task}/receipt.json').read_text())
            self.assertEqual(receipt['status'], 'FAILED')
        self.assertFalse(list(Path(self.tmp.name).glob('OpenContent/Market/**/*.md')))
    def test_run_path_reuse_and_cross_platform_paths_blocked(self):
        for run_id in ('../outside', '/absolute', 'C:/Windows', 'a\\b', '.', 'x'*81):
            with self.assertRaises(Problem):self.runtime.execute_task(self.request(),run_id=run_id)
        with self.assertRaises(Problem):self.runtime.execute_task(self.request(),run_id='one')
        with self.assertRaises(Problem) as error:self.runtime.execute_task(self.request(),run_id='one')
        self.assertEqual(error.exception.status,409)
    def test_output_path_rejects_internal_symlinks_and_windows_forms(self):
        ws=Path(self.tmp.name)/'workspace';ws.mkdir();(ws/'real').mkdir();(ws/'link').symlink_to(ws/'real',target_is_directory=True)
        for path in ('link/image.png','C:/image.png','C:image.png','\\\\host\\share\\image.png','a\\..\\image.png','../image.png'):
            with self.assertRaises(Problem):validate_workspace_path(path,ws)
    def test_explicit_provider_wiring_and_empty_output_fail_closed(self):
        provider=Provider({'candidate':{'title':'New','body':'Real provider output'}})
        self.jobs.providers['test']=provider
        result=self.runtime.execute_task(self.request('write'),provider_name='test')
        self.assertEqual(result['receipt']['provider'],'test');self.assertEqual(len(provider.requests),1)
        with self.assertRaises(Problem):self.runtime.execute_task(self.request('write'),provider_name='missing')
        provider.response={}
        with self.assertRaises(Problem):self.runtime.execute_task(self.request('write'),provider_name='test')
    def test_http_capabilities_routes_use_server_jobs_and_fail_without_images(self):
        provider=Provider({'candidate':{'title':'HTTP','body':'Through server jobs'}})
        self.jobs.providers['test']=provider
        server=Server(self.kernel,self.jobs);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            def call(task):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
                conn.request('POST','/capabilities/execute',json.dumps(self.request(task,provider='test')),{'Authorization':'Bearer '+server.token,'Content-Type':'application/json'})
                response=conn.getresponse();body=json.loads(response.read());status=response.status;conn.close();return status,body
            status,result=call('write');self.assertEqual(status,200,result);self.assertEqual(result['receipt']['provider'],'test')
            status,result=call('cover');self.assertNotEqual(status,200,result);self.assertNotIn('candidates',result)
        finally:server.shutdown();server.server_close();thread.join()
