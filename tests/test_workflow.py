"""Regression checks for capture, preview binding and approved handoff (software fixtures)."""
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import test_kernel as fixtures
from test_kernel import FixtureProvider, STATEMENT
from opencontent.jobs import Jobs
from opencontent.vault import Problem, encode, parse


class WorkflowTests(unittest.TestCase):
    setUp = fixtures.KernelTests.setUp
    token = fixtures.KernelTests.token
    run_stage = fixtures.KernelTests.run_stage
    to_review = fixtures.KernelTests.to_review
    approve = fixtures.KernelTests.approve

    def test_capture_deduplicates_and_preserves_changed_snapshots(self):
        def capture(body, pid=None):
            return self.k.capture(pid or self.p, '摘录', body, 'vault:source.md', self.token(), 'https://example.com/article')
        first = capture('原始选区')
        token = self.token()
        duplicate = capture('  原始选区\r\n')
        self.assertTrue(duplicate['duplicate'])
        self.assertEqual(first['object']['oc_id'], duplicate['object']['oc_id'])
        self.assertEqual(token, self.token())
        changed = capture('编辑后的选区')
        self.assertNotEqual(changed['object']['oc_id'], first['object']['oc_id'])
        self.assertEqual(self.k.inspect(first['object']['oc_id'])['object']['body'], '原始选区')
        other = self.k.create_project('另一项目', '独立来源快照', '读者')['oc_id']
        self.assertFalse(capture('原始选区', other)['duplicate'])

    def test_capture_validates_boundary_and_stale_token(self):
        before = self.token()
        for url in ('file:///private', 'https://[bad', 'https://u:p@example.com', 42):
            with self.assertRaises(Problem):
                self.k.capture(self.p, '来源', '文字', 'vault:file.md', before, url)
        self.assertEqual(before, self.token())
        self.k.capture(self.p, '来源', '文字', 'vault:file.md', before)
        with self.assertRaises(Problem) as error:
            self.k.capture(self.p, '来源', '文字', 'vault:file.md', before)
        self.assertEqual(error.exception.status, 409)

    def test_approved_handoff_is_clean_idempotent_and_local(self):
        material = self.k.inspect(self.m['oc_id'])['object']
        material['source'] = 'vault:private/path.md'
        material['source_url'] = 'https://example.com/article?token=private#fragment'
        (self.k.vault.root/material['path']).write_bytes(encode(material))
        aid = self.to_review()
        with self.assertRaises(Problem): self.k.handoff(aid, self.token())
        self.approve(aid)
        token = self.token()
        result = self.k.handoff(aid, token)
        self.assertEqual(result, self.k.handoff(aid, token))
        self.assertEqual(self.token(), token)
        self.assertEqual(result['status'], 'LOCAL_HANDOFF_ONLY')
        article = (self.k.vault.root/result['path']).read_text(encoding='utf-8')
        self.assertIn(STATEMENT, article)
        self.assertNotIn('[^oc', article)
        self.assertNotIn('https://example.com/article', article)
        self.assertNotIn('参考来源', article)
        self.assertEqual(result['protocol'], 'opencontent.approved-markdown.v2')
        self.assertIn('[[' , self.k.inspect(aid)['object']['body'])
        for private in ('token=private', '#fragment', 'vault:private', self.m['oc_id'], '合成测试决定人', '[[ '):
            self.assertNotIn(private, article)
        self.assertNotIn('[[', article)
        self.assertEqual(self.k.board()['projects'][0]['state'], 'APPROVED')
        self.assertFalse(any(o['type']=='Publication' for o in self.k.read()[0].values()))
        target = self.k.vault.root/result['path']
        target.write_text('用户后续编辑', encoding='utf-8')
        with self.assertRaises(Problem): self.k.handoff(aid, token)
        self.assertEqual(target.read_text(encoding='utf-8'), '用户后续编辑')

    def test_handoff_rechecks_sources_and_constitution(self):
        aid = self.to_review(); self.approve(aid)
        for file in (self.k.vault.root/self.m['path'], self.k.vault.root/'CONTENT.md'):
            original = file.read_bytes()
            file.write_bytes(original+b'\nChanged after approval\n')
            with self.assertRaises(Problem): self.k.handoff(aid, self.token())
            file.write_bytes(original)
        self.assertFalse((self.k.vault.root/'OpenContent-Exports').exists())

    def test_handoff_checks_again_after_preparation(self):
        from opencontent.handoff import gate as real_gate
        aid = self.to_review(); self.approve(aid)
        def changed_during_gate(*args):
            result = real_gate(*args)
            file = self.k.vault.root/self.m['path']
            file.write_bytes(file.read_bytes()+b'\nExternal edit during preparation\n')
            return result
        with patch('opencontent.handoff.gate', side_effect=changed_during_gate):
            with self.assertRaises(Problem): self.k.handoff(aid, self.token())
        self.assertFalse((self.k.vault.root/'OpenContent-Exports').exists())

    def test_cache_uses_bytes_not_mtime_and_never_returns_shared_objects(self):
        self.k.vault._parse_cache.clear()
        with patch('opencontent.vault.parse', wraps=parse) as parser:
            objects, _ = self.k.read(); calls = parser.call_count
            objects[self.m['oc_id']]['body'] = 'poison'
            self.assertEqual(self.k.read()[0][self.m['oc_id']]['body'], STATEMENT)
            self.assertEqual(parser.call_count, calls)
            file = self.k.vault.root/self.m['path']; stat = file.stat()
            raw = file.read_bytes(); changed = raw.replace('来源'.encode(), '原文'.encode())
            self.assertEqual(len(raw), len(changed)); file.write_bytes(changed)
            os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            self.assertNotEqual(self.k.read()[0][self.m['oc_id']]['body'], STATEMENT)
            self.assertEqual(parser.call_count, calls+1)
            file.unlink(); self.assertNotIn(self.m['oc_id'], self.k.read()[0])

    def test_preview_stale_or_queued_edit_never_calls_provider(self):
        provider = FixtureProvider(); jobs = Jobs(self.k, {'fixture':provider}); self.addCleanup(jobs.close)
        stale = self.token()
        self.k.capture(self.p, '新材料', '新文字', 'vault:new.md', stale)
        with patch.object(provider, 'run') as run:
            with self.assertRaises(Problem): jobs.submit(self.p, expected=stale)
            run.assert_not_called()
            # Delay the thread at request construction, then modify a captured source.
            entered = threading.Event(); release = threading.Event(); original = self.k.request
            def delayed(*args):
                entered.set(); release.wait(3); return original(*args)
            with patch.object(self.k, 'request', side_effect=delayed):
                job = jobs.submit(self.p, expected=self.token())
                self.assertTrue(entered.wait(3))
                self.k.capture(self.p, '排队期间新材料', '已变更', 'vault:queued.md', self.token())
                release.set()
                with jobs.mutex: thread = jobs.running[job['id']]['thread']
                thread.join(5)
                result = next(j for j in jobs.list() if j['id']==job['id'])
                self.assertEqual(result['status'], 'FAILED')
                self.assertIn('no material sent', result['detail']['error'])
                run.assert_not_called()


if __name__ == '__main__': unittest.main()
