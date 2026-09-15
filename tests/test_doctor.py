import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('doctor',ROOT/'scripts/doctor.py');doctor=importlib.util.module_from_spec(spec);spec.loader.exec_module(doctor)

class DoctorTests(unittest.TestCase):
    def test_current_environment_offline_and_does_not_touch_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            v=Path(tmp);(v/'.obsidian').mkdir();(v/'private.md').write_text('private contents')
            before={p.name:p.read_bytes() for p in v.iterdir() if p.is_file()}
            report=doctor.diagnose(ROOT,v)
            self.assertTrue(report['passed'],report);self.assertFalse(report['network_used']);self.assertFalse(report['notes_read']);self.assertFalse(report['credentials_read'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in v.iterdir() if p.is_file()})
            self.assertEqual(next(c for c in report['checks'] if c['name']=='cli-login')['status'],'NOT_CHECKED')
    def test_clean_python_missing_dependencies_returns_actionable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,'-m','venv','--without-pip',tmp],check=True,capture_output=True,timeout=30)
            exe=Path(tmp)/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            run=subprocess.run([str(exe),str(ROOT/'scripts/doctor.py'),'--runtime',str(ROOT)],capture_output=True,text=True,timeout=20,env={**os.environ,'PYTHONPATH':''})
            self.assertEqual(run.returncode,1,run.stderr);report=json.loads(run.stdout);self.assertFalse(report['passed'])
            failed={c['name']:c for c in report['checks'] if c['status']=='FAIL'}
            self.assertIn('PyYAML',failed);self.assertIn('mistune',failed);self.assertIn('pip install',failed['PyYAML']['action'])
    def test_invalid_vault_missing_runtime_and_permission_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=doctor.diagnose(tmp,tmp);self.assertFalse(report['passed'])
            self.assertEqual({c['name'] for c in report['checks'] if c['status']=='FAIL'},{'kernel','vault'})
            (Path(tmp)/'.obsidian').mkdir()
            with patch.object(doctor.tempfile,'TemporaryFile',side_effect=PermissionError('do not expose raw path')):
                report=doctor.diagnose(ROOT,tmp)
            self.assertFalse(report['passed']);self.assertNotIn('do not expose',str(report))
    def test_wrong_dependency_version_is_not_reported_supported(self):
        with patch.object(doctor.importlib.metadata,'version',return_value='0.0'):
            report=doctor.diagnose(ROOT)
        self.assertFalse(report['passed']);self.assertEqual(len([c for c in report['checks'] if c['status']=='FAIL']),2)
