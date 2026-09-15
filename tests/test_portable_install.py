import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from release_files import installed_runtime
RUNTIME=installed_runtime(ROOT)

class PortableInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.vault=Path(self.tmp.name)/'Vault';(self.vault/'.obsidian/plugins/opencontent').mkdir(parents=True)
        self.dest=self.vault/'.obsidian/plugins/opencontent'
    def install(self,*extra):
        return subprocess.run([sys.executable,str(ROOT/'scripts/install_plugin.py'),'--vault',str(self.vault),*extra],capture_output=True,text=True,encoding='utf-8',timeout=30)
    def test_bundled_kernel_works_without_checkout_and_preserves_settings(self):
        settings={'kernelPath':'Z:/removed-checkout','reviewer':'existing-user','lastProject':'preserve-me'}
        (self.dest/'data.json').write_text(json.dumps(settings),encoding='utf-8')
        first=self.install();self.assertEqual(first.returncode,0,first.stderr)
        self.assertEqual(json.loads((self.dest/'data.json').read_text()),settings)
        run=subprocess.run([sys.executable,'-m','opencontent','--vault',str(self.vault),'board'],cwd=self.dest/RUNTIME,env={**os.environ,'PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['projects'],[])
        second=self.install('--configure');self.assertEqual(second.returncode,0,second.stderr)
        new=json.loads((self.dest/'data.json').read_text())
        self.assertEqual(new['kernelPath'],str(self.dest/RUNTIME));self.assertEqual(new['lastProject'],'preserve-me')
        backup=Path(json.loads(second.stdout)['backup'])
        self.assertEqual(json.loads((backup/'data.json').read_text()),settings)
        self.assertTrue((backup/RUNTIME/'opencontent/__main__.py').is_file())
    def test_bad_settings_fail_before_replacing_plugin(self):
        (self.dest/'main.js').write_text('old plugin',encoding='utf-8')
        (self.dest/'data.json').write_text('{bad json',encoding='utf-8')
        result=self.install('--configure');self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.dest/'main.js').read_text(),'old plugin')

    def test_live_safe_update_preserves_current_runtime_and_settings(self):
        first=self.install('--configure');self.assertEqual(first.returncode,0,first.stderr)
        old=self.dest/RUNTIME
        original=(old/'opencontent/__main__.py').read_bytes()
        settings=json.loads((self.dest/'data.json').read_text())
        settings['lastProject']='keep-live-project'
        (self.dest/'data.json').write_text(json.dumps(settings),encoding='utf-8-sig')
        second=self.install('--configure','--live-safe');self.assertEqual(second.returncode,0,second.stderr)
        updated=json.loads((self.dest/'data.json').read_text())
        self.assertNotEqual(updated['kernelPath'],str(old))
        self.assertTrue((Path(updated['kernelPath'])/'opencontent/__main__.py').is_file())
        self.assertEqual((old/'opencontent/__main__.py').read_bytes(),original)
        self.assertEqual(updated['lastProject'],'keep-live-project')
    def test_partial_install_failure_restores_all_original_files(self):
        import runpy
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts'))
        for name in ('main.js','manifest.json','styles.css'):(self.dest/name).write_text('original '+name,encoding='utf-8')
        (self.dest/'data.json').write_text('{"lastProject":"keep"}',encoding='utf-8')
        (self.dest/RUNTIME).mkdir();(self.dest/RUNTIME/'old.txt').write_text('original kernel',encoding='utf-8')
        before={str(p.relative_to(self.dest)):p.read_bytes() for p in self.dest.rglob('*') if p.is_file()}
        original=os.replace;failed=False
        def replace(source,target):
            nonlocal failed
            if not failed and Path(target)==self.dest/'styles.css' and '.install-' in str(source):
                failed=True;raise OSError('simulated locked destination')
            return original(source,target)
        with patch.object(sys,'argv',['install_plugin.py','--vault',str(self.vault),'--configure']),patch('os.replace',side_effect=replace):
            with self.assertRaisesRegex(OSError,'locked destination'):runpy.run_path(str(ROOT/'scripts/install_plugin.py'),run_name='__main__')
        after={str(p.relative_to(self.dest)):p.read_bytes() for p in self.dest.rglob('*') if p.is_file()}
        self.assertEqual(before,after)


    def test_version_update_does_not_move_live_previous_kernel(self):
        previous=self.dest/'kernel';previous.mkdir()
        (previous/'old.txt').write_text('live old runtime',encoding='utf-8')
        (self.dest/'data.json').write_text(json.dumps({'kernelPath':str(previous),'lastProject':'keep'}),encoding='utf-8')
        # Windows holds a directory open when a process uses it as cwd: reproduce the real install failure.
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],cwd=previous,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            result=self.install('--configure');self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((previous/'old.txt').read_text(),'live old runtime')
            self.assertEqual(json.loads((self.dest/'data.json').read_text())['kernelPath'],str(self.dest/RUNTIME))
            self.assertEqual(child.poll(),None)
            self.assertTrue((self.dest/RUNTIME/'opencontent/__main__.py').is_file())
        finally:child.terminate();child.wait(timeout=5)

    def test_payload_contains_template_and_no_private_runtime(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from release_files import plugin_files
        names=[n for _,n in plugin_files(ROOT)]
        self.assertIn('kernel/templates/CONTENT.md',names)
        self.assertIn('kernel/opencontent/__main__.py',names)
        self.assertTrue(all('.opencontent' not in n and '__pycache__' not in n and 'data.json' not in n for n in names))
