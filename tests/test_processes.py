import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from opencontent.providers import CodexProvider
from opencontent.vault import Problem


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)
    def fixture(self,code):
        # Python treats the adapter's first argv ('exec') as this test script.
        # This exercises process IO/lifecycle; it does not impersonate a real model run.
        (self.path/'exec').write_text(code,encoding='utf-8')
    def test_process_success_invalid_output_nonzero(self):
        provider=CodexProvider(sys.executable,2)
        self.fixture("from pathlib import Path\nPath('response.json').write_text('{\"ok\":true}')\n")
        self.assertEqual(provider.run({},self.path,threading.Event()),{'ok':True})
        self.fixture("from pathlib import Path\nPath('response.json').write_text('not JSON')\n")
        with self.assertRaises(Problem):provider.run({},self.path,threading.Event())
        self.fixture('raise SystemExit(7)\n')
        with self.assertRaisesRegex(Problem,'exited 7'):provider.run({},self.path,threading.Event())
    def test_output_cap_and_cancel(self):
        self.fixture("import time\nfrom pathlib import Path\nPath('response.json').write_text('x'*2100000)\ntime.sleep(5)\n")
        with self.assertRaisesRegex(Problem,'output limit'):CodexProvider(sys.executable,2).run({},self.path,threading.Event())
        (self.path/'response.json').unlink()
        self.fixture('import time\ntime.sleep(5)\n');event=threading.Event();event.set()
        with self.assertRaisesRegex(Problem,'cancelled'):CodexProvider(sys.executable,2).run({},self.path,event)
    def test_timeout_owns_descendants(self):
        self.fixture("import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c',\"import time;time.sleep(2);open('escaped.txt','w').write('bad')\"])\nPath('child.txt').write_text(str(p.pid))\ntime.sleep(10)\n")
        with self.assertRaisesRegex(Problem,'timed out'):CodexProvider(sys.executable,.4).run({},self.path,threading.Event())
        pid=int((self.path/'child.txt').read_text())
        if os.name=='nt':
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.restype=ctypes.c_void_p
            handle=kernel.OpenProcess(0x1000,False,pid)
            if handle:
                code=ctypes.c_ulong();kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code));kernel.CloseHandle(ctypes.c_void_p(handle))
                self.assertNotEqual(code.value,259,'descendant remains active')
        else:
            with self.assertRaises(ProcessLookupError):os.kill(pid,0)
        self.assertFalse((self.path/'escaped.txt').exists())


if __name__=='__main__':unittest.main()
