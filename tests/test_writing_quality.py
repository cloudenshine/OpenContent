"""Offline contract checks, not evidence of live model prose quality."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from opencontent.capabilities import CapabilityRuntime, PackRegistry
from opencontent.jobs import Jobs
from opencontent.kernel import Kernel
from opencontent import workbench
from opencontent.writing_quality import ROOT, writing_policy

REPO = Path(__file__).resolve().parents[1]

class CaptureProvider:
    def __init__(self): self.requests = []
    def run(self, request, workspace, cancel_event):
        self.requests.append(request)
        return {'candidate': {'title': '测试候选', 'body': '软件测试文本，不代表真实模型生成。'}, 'review': {'issues': []}}

class WritingQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.kernel = Kernel(self.tmp.name)
        self.pid = self.kernel.create_project('项目', '解释实际问题', '普通读者')['oc_id']

    def test_versioned_assets_and_licenses_match_manifest(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(len(manifest['sources']), 3)
        for source in manifest['sources']:
            self.assertEqual(source['license'], 'MIT')
            self.assertRegex(source['commit'], r'^[a-f0-9]{40}$')
            for item in source['files']:
                path = ROOT / item['path']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'])
                self.assertIn(source['commit'], item['url'])
        policy = writing_policy('write')
        self.assertEqual(policy['sha256'], hashlib.sha256(policy['instructions'].encode()).hexdigest())
        self.assertLess(len(policy['instructions']), 2500)

    def test_generic_production_injects_only_draft_and_critique(self):
        for stage in ('draft', 'critique'):
            request = self.kernel.request(self.pid, stage, [])
            policy = writing_policy(stage)
            self.assertIn(policy['instructions'], request['instructions'])
            self.assertEqual(request['writing_quality']['sha256'], policy['sha256'])
            self.assertEqual(request['writing_quality']['mode'], 'evidence-bound')
        for stage in ('distill', 'research'):
            self.assertNotIn('writing_quality', self.kernel.request(self.pid, stage, []))

    def test_workbench_revision_only_and_preserves_protocol(self):
        for mode in ('revise', 'discuss', 'illustrate'):
            request = workbench.request(self.kernel, self.pid, '只修改第二段', mode, [], mode)
            self.assertEqual('writing_quality' in request, mode == 'revise')
            self.assertEqual(request['instruction'], '只修改第二段')
            if mode == 'revise':
                self.assertIn('只在用户指定范围内', request['instructions'])
                self.assertIn('revision', request['response_schema'])

    def test_all_narrative_tasks_reach_provider_with_correct_profile_and_saved_hash(self):
        jobs = Jobs(self.kernel); provider = CaptureProvider(); jobs.providers['capture'] = provider
        registry = PackRegistry(); registry.discover([REPO / 'packs'])
        runtime = CapabilityRuntime(self.kernel, registry, jobs=jobs)
        for profile in ('general-fiction', 'serial-fiction', 'narrative-nonfiction'):
            for task in ('plan', 'write', 'continue', 'revise', 'critique'):
                result = runtime.execute_task(dict(schema='opencontent.creative-task.v1', project=self.pid, pack='narrative', profile=profile, task=task, instruction='保留用户声线'), provider_name='capture')
                request = provider.requests[-1]
                policy = writing_policy(task, fiction=profile != 'narrative-nonfiction')
                self.assertIn(policy['instructions'], request['instructions'])
                self.assertEqual(request['writing_quality']['modules'], policy['modules'])
                self.assertEqual(result['receipt']['writing_quality']['sha256'], policy['sha256'])
                saved = Path(self.tmp.name)/'.opencontent/runs'/result['receipt']['run_id']/'agent-request.json'
                self.assertEqual(json.loads(saved.read_text())['writing_quality'], request['writing_quality'])
                if profile != 'narrative-nonfiction':
                    self.assertIn('不需要给虚构场景加事实引用', request['instructions'])
                    self.assertNotIn('substance.md', policy['modules'])
                if task == 'plan': self.assertNotIn('voice.md', policy['modules'])

    def test_codex_and_claude_adapters_serialize_applied_policy_to_stdin(self):
        from opencontent.providers import CodexProvider, ClaudeProvider
        import threading
        captured = []
        class Process:
            returncode = 0
            def poll(self): return 0
            def wait(self, timeout=None): return 0
        class Group:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def close(self): pass
            def start(self, argv, stdin, stdout, stderr, cwd):
                captured.append(json.load(stdin))
                response = b'{"artifact":{"title":"fixture","body":"fixture"}}'
                (cwd/'response.json').write_bytes(response)
                stdout.write(response); stdout.flush()
                return Process()
        request = self.kernel.request(self.pid, 'draft', [])
        workspace = Path(self.tmp.name)/'provider'; workspace.mkdir()
        with patch('opencontent.providers.ProcessGroup', Group):
            for provider in (CodexProvider, ClaudeProvider):
                provider(sys.executable).run(request, workspace, threading.Event())
        self.assertEqual(len(captured), 2)
        for actual in captured:
            self.assertEqual(actual, request)
            self.assertIn(writing_policy('draft')['instructions'], actual['instructions'])

    def test_missing_policy_asset_fails_before_provider(self):
        jobs = Jobs(self.kernel); provider = CaptureProvider(); jobs.providers['capture'] = provider
        registry = PackRegistry(); registry.discover([REPO/'packs'])
        runtime = CapabilityRuntime(self.kernel, registry, jobs=jobs)
        from opencontent.vault import Problem
        with patch('opencontent.writing_quality.ROOT', Path(self.tmp.name)/'missing-assets'):
            with self.assertRaises(Problem):
                runtime.execute_task(dict(schema='opencontent.creative-task.v1', project=self.pid, pack='narrative', profile='general-fiction', task='write'), run_id='missing-policy')
        self.assertEqual(provider.requests, [])
        receipt = json.loads((Path(self.tmp.name)/'.opencontent/runs/missing-policy/receipt.json').read_text())
        self.assertEqual(receipt['status'], 'FAILED')

    def test_excluded_tasks_have_no_writing_policy(self):
        for task in ('cover', 'illustrate', 'long-scan', 'short-scan', 'long-analyze', 'research', 'classify'):
            self.assertIsNone(writing_policy(task))

    def test_installed_runtime_contains_working_policy_and_attribution(self):
        sys.path.insert(0, str(REPO/'scripts'))
        from release_files import plugin_files
        bundled = Path(self.tmp.name)/'installed'
        for source, relative in plugin_files(REPO):
            if relative.startswith('kernel/'):
                dest = bundled/relative[len('kernel/'):];dest.parent.mkdir(parents=True, exist_ok=True);dest.write_bytes(source.read_bytes())
        command = 'from opencontent.writing_quality import writing_policy; assert writing_policy("write", fiction=True); assert writing_policy("plan", fiction=True); print(writing_policy("write")["version"])'
        result = subprocess.run([sys.executable, '-I', '-c', 'import sys;sys.path.insert(0,'+repr(str(bundled))+');'+command], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '1.0.2')
        self.assertTrue((bundled/'opencontent/writing_skills/upstream/humanizer-zh/LICENSE').is_file())

    def test_composed_guidance_hash_and_concise_core_are_preserved(self):
        from opencontent.editorial import WRITING
        request = self.kernel.request(self.pid, 'draft', [])
        self.assertEqual(request['editorial_guidance'], WRITING)
        prompt = {key: request.get(key, '') for key in ('instructions', 'editorial_guidance')}
        digest = hashlib.sha256(json.dumps(prompt, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(request['writing_quality']['prompt_sha256'], digest)
        self.assertEqual(request['response_schema']['artifact']['claims'], ['existing Claim oc_id'])
        self.assertIn('each Claim statement verbatim', request['response_schema']['artifact']['body'])
        self.assertIn('Return only JSON matching response_schema', request['instructions'])

    def test_references_are_hashed_genre_scoped_and_not_default_instructions(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual({row['mode'] for row in manifest['reference_resources']}, {'fiction', 'evidence-bound'})
        for row in manifest['reference_resources']:
            text = (ROOT / row['path']).read_text()
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), row['sha256'])
            self.assertIn('manual-reference-only', row['loading'])
            for task in ('draft', 'write', 'continue', 'revise', 'plan', 'critique'):
                for fiction in (True, False):
                    self.assertNotIn(text, writing_policy(task, fiction=fiction)['instructions'])
        for fiction in (True, False):
            instructions = writing_policy('revise', fiction=fiction)['instructions']
            self.assertIn('只在用户指定范围内', instructions)
            self.assertIn('不动受保护的引文、Claim 原句/ID、代码、链接目标与数据', instructions)
            self.assertIn('不要代写全文', writing_policy('critique', fiction=fiction)['instructions'])
