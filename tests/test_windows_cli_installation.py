import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import sys
from unittest.mock import patch
from opencontent.kernel import Kernel
from opencontent.providers import CodexProvider, activate_cli, detect_cli
from opencontent import __main__ as cli_main

class NativeCliInstallationTests(unittest.TestCase):
    def test_explicit_model_survives_kernel_cli_startup_without_agent_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/'codex.exe';native.write_bytes(b'not executed')
            captured={}
            class ProbeServer:
                def __init__(self,kernel,jobs,port):
                    captured['model']=jobs.providers['codex'].model
                    self.server_port=0;self.token='synthetic-test'
                def serve_forever(self,**kwargs):pass
                def server_close(self):pass
            argv=['opencontent','--vault',str(root/'vault'),'serve','--codex',str(native),'--model','preserved-user-model']
            with patch.object(sys,'argv',argv),patch.object(cli_main,'Server',ProbeServer),patch('builtins.print'),patch('subprocess.Popen',side_effect=AssertionError('startup must not call model')):
                cli_main.main()
            self.assertEqual(captured['model'],'preserved-user-model')

    @unittest.skipUnless(os.name == 'nt', 'Windows npm layout')
    def test_npm_wrappers_resolve_native_payload_without_running_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root/'node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
            native.parent.mkdir(parents=True); native.write_bytes(b'not executed')
            def which(name):
                return str(root/'codex.ps1') if name == 'codex.ps1' else None
            with patch('opencontent.providers.shutil.which', side_effect=which), patch('subprocess.Popen', side_effect=AssertionError('discovery must not execute')):
                found = detect_cli()
            self.assertEqual(next(p['path'] for p in found if p['name']=='codex'), str(native))

    def test_model_activation_preserves_explicit_executable_even_without_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); native=root/'custom-codex.exe';native.write_bytes(b'not executed')
            jobs=SimpleNamespace(kernel=Kernel(root/'vault'),providers={'codex':CodexProvider(native)},running=False)
            with patch('opencontent.providers.detect_cli', side_effect=AssertionError('explicit path must be preserved')):
                result=activate_cli(jobs,'codex','chosen-model')
            self.assertEqual(result['model'],'chosen-model')
            self.assertEqual(jobs.providers['codex'].executable,native)
            self.assertEqual(jobs.providers['codex'].model,'chosen-model')
