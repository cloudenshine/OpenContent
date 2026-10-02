"""Real Windows junction boundaries; do not replace privileged symlink tests."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from opencontent.capabilities.validation import validate_workspace_path
from opencontent.vault import Problem


@unittest.skipUnless(os.name == 'nt', 'Windows directory junction regression')
class WindowsWorkspaceJunctionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='opencontent-junction-')
        self.root = Path(self.temporary.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.links = []

    def tearDown(self):
        # Remove only verified junction entries before recursive temporary cleanup.
        # Their targets remain in this same explicitly owned temporary root.
        for link in self.links:
            self.assertTrue(link.parent.resolve().is_relative_to(self.root.resolve()))
            self.assertTrue(link.is_junction())
            self.assertTrue(link.resolve().is_relative_to(self.root.resolve()))
            os.rmdir(link)
        self.assertTrue(self.root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.temporary.cleanup()

    def junction(self, name, target):
        link = self.workspace / name
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                        'New-Item -ItemType Junction -Path ' + quote(link) + ' -Target ' + quote(target) + ' | Out-Null'],
                       check=True, capture_output=True)
        self.assertTrue(link.is_junction())
        self.links.append(link)
        return link

    def test_internal_junction_read_and_output_paths_are_refused(self):
        target = self.workspace / 'real'
        target.mkdir()
        witness = target / 'input.txt'
        witness.write_text('synthetic internal witness')
        self.junction('internal', target)
        for path in ('internal/input.txt', 'internal/output.txt'):
            with self.subTest(path=path), self.assertRaises(Problem):
                validate_workspace_path(path, self.workspace)
        self.assertEqual(witness.read_text(), 'synthetic internal witness')
        self.assertFalse((target / 'output.txt').exists())

    def test_external_junction_cannot_return_read_or_write_paths(self):
        target = self.root / 'outside'
        target.mkdir()
        witness = target / 'input.txt'
        witness.write_text('synthetic outside witness')
        self.junction('escape', target)
        for path in ('escape/input.txt', 'escape/output.txt'):
            with self.subTest(path=path), self.assertRaises(Problem):
                validate_workspace_path(path, self.workspace)
        self.assertEqual(witness.read_text(), 'synthetic outside witness')
        self.assertFalse((target / 'output.txt').exists())

    def test_ordinary_workspace_output_remains_writable(self):
        target = validate_workspace_path('output.txt', self.workspace)
        target.write_text('synthetic allowed output')
        self.assertEqual(target.read_text(), 'synthetic allowed output')
        self.assertEqual(target.parent, self.workspace.resolve())
