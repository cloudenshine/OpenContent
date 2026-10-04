"""Final review regressions. All sources, decisions and accounts are synthetic."""
import copy
from pathlib import Path
import tempfile
import unittest

from opencontent.kernel import Kernel
from opencontent.vault import Problem, digest, encode
from opencontent import rendering, social_graphic, workbench
from opencontent.publishing import Publishing, preview_hash
import test_kernel as kernel_fixtures
import test_lifecycle as lifecycle_fixtures


class FinalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.k = Kernel(Path(self.temp.name) / 'vault')
        self.pid = self.k.create_project('Synthetic review', 'Verify boundaries', 'Fixture only')['oc_id']
        self.k.add(self.pid, 'Material', 'Synthetic source', kernel_fixtures.STATEMENT,
                   {'source': 'fixture:synthetic'}, self.k.vault.token())
        for stage in ('distill', 'research', 'draft', 'critique'):
            request = self.k.request(self.pid, stage, [])
            self.k.apply_result(self.pid, stage, kernel_fixtures.response(request),
                                request['token'], 'fixture', stage)
        self.aid = next(a['oc_id'] for a in self.k.read()[0].values() if a['type'] == 'Artifact')
        self.approve(self.aid)

    def edit(self, uid, **fields):
        obj = copy.deepcopy(self.k.read()[0][uid])
        obj.update(fields)
        self.k.vault.safe(obj['path']).write_bytes(encode(obj))
        return self.k.read()[0][uid]

    def approve(self, aid):
        axes = kernel_fixtures.response({'stage': 'critique', 'objects': []})['axes']
        self.k.review(aid, 'fixture:independent', axes, True, '', 'Synthetic review, not author approval',
                      self.k.vault.token(), expected_snapshot=self.k.inspect(aid)['input_snapshot'])
        self.k.decide(aid, 'accept', 'fixture:human', 'Synthetic protocol decision', self.k.vault.token())

    def variant(self, mother=None):
        mother = mother or self.k.read()[0][self.aid]
        # Deliberately emulate file-authored frontmatter, independent of helper validation.
        bound = {'artifact': mother['oc_id'], **workbench.input_snapshot(self.k, self.k.read()[0], mother)}
        page = {'role': 'explain', 'purpose': 'Preserve synthetic evidence',
                'source_excerpt': kernel_fixtures.STATEMENT, 'claims': list(mother['derived_from']),
                'title': 'Synthetic page', 'body': kernel_fixtures.STATEMENT, 'resources': []}
        obj = self.k.vault.new('Artifact', 'Synthetic variant', mother['body'], self.pid,
                               state='REVIEWING', author='fixture:writer', derived_from=mother['derived_from'],
                               channel='xiaohongshu', mother_dependency=bound, pages=[page],
                               resource_bindings=[], pack='xiaohongshu', pack_version='1.0.0')
        with self.k.vault.lock():
            self.k.vault.commit([obj], self.k.vault.token())
        return obj['oc_id']

    def prepared(self, theme='serif'):
        adapter = lifecycle_fixtures.WeChatFixture()
        publishing = Publishing(self.k, {'fixture': adapter})
        result = publishing.prepare(self.aid, 'fixture', 'draft', self.k.vault.token(),
                                     {'digest': 'Synthetic summary', 'thumb_media_id': 'synthetic-cover', 'theme': theme})
        return publishing, adapter, result

    def test_confirm_rejects_rehashed_unapproved_body_before_any_remote_write(self):
        publishing, adapter, pub = self.prepared()
        payload = copy.deepcopy(pub['payload'])
        payload['content'] = '<p>UNREVIEWED SYNTHETIC SUBSTITUTE</p>'
        self.edit(pub['oc_id'], payload=payload, payload_hash=digest(payload))
        current = self.k.read()[0][pub['oc_id']]
        with self.assertRaises(Problem):
            publishing.confirm(pub['oc_id'], preview_hash(current), 'fixture:human', self.k.vault.token())
        self.assertNotIn('draft/add', adapter.calls)
        self.assertEqual(self.k.read()[0][pub['oc_id']]['delivery_status'], 'PREPARED')

    def test_confirm_rejects_changed_build_metadata_even_with_original_build_id(self):
        publishing, adapter, pub = self.prepared()
        forged = copy.deepcopy(pub['build'])
        forged['renderer_version'] = 'synthetic-substitute'
        self.edit(pub['oc_id'], build=forged)
        current = self.k.read()[0][pub['oc_id']]
        with self.assertRaises(Problem):
            publishing.confirm(pub['oc_id'], preview_hash(current), 'fixture:human', self.k.vault.token())
        self.assertNotIn('draft/add', adapter.calls)

    def test_publish_prepare_rejects_self_consistent_replacement_in_verified_draft(self):
        publishing, adapter, pub = self.prepared()
        done = publishing.confirm(pub['oc_id'], preview_hash(pub), 'fixture:human', self.k.vault.token())
        self.assertEqual(done['delivery_status'], 'REMOTE_DRAFT')
        payload = copy.deepcopy(done['payload'])
        payload['content'] = '<p>UNREVIEWED SYNTHETIC SUBSTITUTE</p>'
        self.edit(pub['oc_id'], payload=payload, payload_hash=digest(payload), remote_payload_hash=digest(payload))
        adapter.drafts[done['remote_media_id']]['news_item'][0]['content'] = payload['content']
        with self.assertRaises(Problem):
            publishing.prepare(self.aid, 'fixture', 'publish', self.k.vault.token(), draft_publication=pub['oc_id'])
        self.assertNotIn('freepublish/submit', adapter.calls)

    def test_wrong_type_mother_blocks_review_and_formal_export(self):
        source = self.k.read()[0][self.aid]
        material = self.k.add(self.pid, 'Material', 'Not a mother artifact', source['body'],
                              {'source': 'fixture:synthetic'}, self.k.vault.token())
        material = self.edit(material['oc_id'], derived_from=source['derived_from'])
        vid = self.variant(material)
        gate = self.k.inspect(vid)['gate']
        self.assertEqual(gate.get('dependency_status'), 'STALE')
        self.assertFalse(gate['approved'])
        with self.assertRaises(Problem):
            self.approve(vid)
        with self.assertRaises(Problem):
            rendering.export_build(self.k, vid, self.k.vault.token())

    def test_mother_dependency_builder_rejects_nonartifact(self):
        material = next(o for o in self.k.read()[0].values() if o['type'] == 'Material')
        with self.assertRaises(Problem):
            social_graphic.mother_dependency(self.k, self.k.read()[0], material)

    def test_deleted_mother_marks_variant_stale_without_breaking_board(self):
        vid = self.variant()
        self.approve(vid)
        mother = self.k.read()[0][self.aid]
        self.k.vault.safe(mother['path']).unlink()
        inspected = self.k.inspect(vid)
        self.assertEqual(inspected['gate'].get('dependency_status'), 'STALE')
        self.assertFalse(inspected['gate']['approved'])
        board = self.k.board()
        self.assertTrue(any(a['oc_id'] == vid for p in board['projects'] for a in p['artifacts']))
        with self.assertRaises(Problem):
            rendering.export_build(self.k, vid, self.k.vault.token())

    def test_malformed_mother_binding_is_diagnostic_not_board_crash(self):
        vid = self.variant()
        for bound in ({'artifact': 'missing'}, {'context_hash': 'missing-id'}, ['not-a-map'], {}, None):
            with self.subTest(bound=bound):
                self.edit(vid, mother_dependency=bound)
                gate = self.k.inspect(vid)['gate']
                self.assertEqual(gate.get('dependency_status'), 'STALE')
                self.assertFalse(gate['approved'])
                self.k.board()

    def test_exact_second_occurrence_is_revised_without_changing_first(self):
        original = self.k.read()[0][self.aid]
        repeated = 'Repeated synthetic sentence.'
        a = self.edit(self.aid, body=original['body'] + '\n\n' + repeated + '\n\n' + repeated)
        start = a['body'].rindex(repeated)
        selection = {'start': start, 'end': start + len(repeated), 'text': repeated,
                     'base_hash': digest({'title': a['title'], 'body': a['body']})}
        uid = 'a' * 32
        workbench.request(self.k, self.pid, 'Revise this exact second occurrence', 'revise', [], uid, self.aid, selection)
        replacement = 'Revised second occurrence.'
        workbench.complete(self.k, self.pid, uid,
                           {'reply': 'Synthetic scoped revision', 'revision': {'artifact': self.aid, 'title': a['title'], 'body': replacement},
                            'illustrations': [], 'images': []}, Path(self.temp.name))
        workbench.apply_revision(self.k, self.pid, uid, self.k.vault.token())
        actual = self.k.read()[0][self.aid]['body']
        self.assertEqual(actual, a['body'][:start] + replacement + a['body'][selection['end']:])
        self.assertEqual(actual.count(repeated), 1)

    def test_stale_exact_range_is_still_rejected(self):
        a = self.k.read()[0][self.aid]
        selection = {'start': 0, 'end': 4, 'text': a['body'][:4],
                     'base_hash': digest({'title': a['title'], 'body': a['body']})}
        self.edit(self.aid, body=a['body'] + '\nChanged after selection.')
        with self.assertRaises(Problem):
            workbench.request(self.k, self.pid, 'Revise stale range', 'revise', [], 'b' * 32, self.aid, selection)
