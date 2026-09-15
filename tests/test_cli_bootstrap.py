import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from opencontent.kernel import Kernel
from opencontent.providers import bootstrap_cli


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jobs=SimpleNamespace(kernel=Kernel(self.tmp.name),providers={},running=False)
        self.executable=Path(self.tmp.name)/'codex.exe'
        self.executable.write_bytes(b'not executed')

    def test_first_use_discovers_and_remembers_without_executing(self):
        with patch('opencontent.providers.detect_cli',return_value=[{'name':'codex','path':str(self.executable)}]), patch('subprocess.Popen',side_effect=AssertionError('must not execute')):
            self.assertIsNone(bootstrap_cli(self.jobs))
        self.assertIn('codex',self.jobs.providers)
        saved=json.loads(self.jobs.kernel.vault.safe('.opencontent/cli-selection.json').read_text())
        self.assertEqual(saved['name'],'codex')

    def test_explicit_provider_is_not_replaced_by_saved_selection(self):
        explicit=object();self.jobs.providers={'codex':explicit}
        with patch('opencontent.providers.detect_cli',side_effect=AssertionError('must preserve explicit config')):
            self.assertIsNone(bootstrap_cli(self.jobs))
        self.assertIs(self.jobs.providers['codex'],explicit)

    def test_unavailable_saved_selection_does_not_silently_switch(self):
        selection=self.jobs.kernel.vault.safe('.opencontent/cli-selection.json')
        selection.write_text('{"name":"claude"}')
        with patch('opencontent.providers.detect_cli',return_value=[{'name':'codex','path':str(self.executable)}]):
            self.assertIn('不会自动换用',bootstrap_cli(self.jobs))
        self.assertEqual(self.jobs.providers,{})
        self.assertEqual(json.loads(selection.read_text())['name'],'claude')

    def test_missing_or_corrupt_configuration_keeps_manual_work_available(self):
        with patch('opencontent.providers.detect_cli',return_value=[]):
            self.assertIn('未找到',bootstrap_cli(self.jobs))
        self.jobs.kernel.vault.safe('.opencontent/cli-selection.json').write_text('broken')
        self.assertIn('暂不可用',bootstrap_cli(self.jobs))
        self.assertEqual(self.jobs.providers,{})
