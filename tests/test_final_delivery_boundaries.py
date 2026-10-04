"""Final independent-review regressions. Synthetic records and account responses only."""
import copy
import io
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from opencontent.kernel import Kernel
from opencontent.vault import Problem, digest, encode
from opencontent import rendering, social_graphic, workbench
from opencontent.publishing import Publishing, preview_hash
from test_kernel import response, STATEMENT
from test_lifecycle import WeChatFixture


class FinalDeliveryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='oc-final-boundary-')
        self.addCleanup(self.tmp.cleanup)
        self.k = Kernel(self.tmp.name)
        self.pid = self.k.create_project('Synthetic boundary fixture', 'Verify exact delivery', 'Software test')['oc_id']
        self.k.add(self.pid, 'Material', 'Synthetic source', STATEMENT, {'source': 'fixture:synthetic'}, self.token())
        for stage in ('distill', 'research', 'draft', 'critique'):
            request = self.k.request(self.pid, stage, [])
            self.k.apply_result(self.pid, stage, response(request), request['token'], 'fixture', stage)
        self.aid = self.k.board()['projects'][0]['artifacts'][0]['oc_id']
        self.approve(self.aid)

    def token(self):
        return self.k.vault.token()

    def edit(self, uid, **fields):
        obj = copy.deepcopy(self.k.read()[0][uid]); obj.update(fields)
        self.k.vault.safe(obj['path']).write_bytes(encode(obj))
        return obj

    def approve(self, aid):
        self.k.review(aid, 'fixture:independent', response({'stage': 'critique', 'objects': []})['axes'],
                      True, '', 'Synthetic review, not author acceptance.', self.token(),
                      expected_snapshot=self.k.inspect(aid)['input_snapshot'])
        self.k.decide(aid, 'accept', 'fixture:human', 'Synthetic protocol decision only.', self.token())

    def variant(self, mother, approve=True):
        page = {'role': 'explain', 'purpose': 'Preserve source boundary', 'source_excerpt': STATEMENT,
                'claims': list(mother['derived_from']), 'title': 'Synthetic page', 'body': STATEMENT, 'resources': []}
        # Simulate a directly edited Markdown dependency when testing a wrong type.
        dependency = (social_graphic.mother_dependency(self.k, self.k.read()[0], mother)
                      if mother['type'] == 'Artifact' else
                      {'artifact': mother['oc_id'], **workbench.input_snapshot(self.k, self.k.read()[0], mother)})
        obj = self.k.vault.new('Artifact', 'Synthetic variant', mother['body'], self.pid,
            state='REVIEWING', author='fixture:writer', derived_from=mother['derived_from'], channel='xiaohongshu',
            mother_dependency=dependency,
            pages=[page], resource_bindings=[], pack='xiaohongshu', pack_version='1.0.0')
        with self.k.vault.lock(): self.k.vault.commit([obj], self.token())
        if approve: self.approve(obj['oc_id'])
        return obj['oc_id']

    def prepare(self, adapter=None):
        adapter = adapter or WeChatFixture()
        service = Publishing(self.k, {'fixture': adapter})
        prepared = service.prepare(self.aid, 'fixture', 'draft', self.token(),
                                   {'digest': 'Synthetic summary', 'thumb_media_id': 'fixture-cover'})
        return service, adapter, prepared

    def test_rehashed_payload_cannot_replace_authoritative_body(self):
        service, adapter, prepared = self.prepare()
        payload = copy.deepcopy(prepared['payload']); payload['content'] = '<p>UNREVIEWED SYNTHETIC SUBSTITUTE</p>'
        modified = self.edit(prepared['oc_id'], payload=payload, payload_hash=digest(payload))
        with self.assertRaises(Problem):
            service.confirm(modified['oc_id'], preview_hash(modified), 'fixture:human', self.token())
        self.assertEqual(adapter.calls.count('draft/add'), 0)

    def test_build_id_does_not_authorize_modified_build_fields(self):
        service, adapter, prepared = self.prepare()
        build = copy.deepcopy(prepared['build']); build['render_hash'] = '0' * 64
        modified = self.edit(prepared['oc_id'], build=build)
        with self.assertRaises(Problem):
            service.confirm(modified['oc_id'], preview_hash(modified), 'fixture:human', self.token())
        self.assertEqual(adapter.calls.count('draft/add'), 0)

    def test_changed_asset_manifest_is_rejected_before_upload(self):
        class Images(WeChatFixture):
            def __init__(self): super().__init__(); self.uploads = []
            def upload_image(self, raw, mime):
                self.uploads.append(raw); return {'url': 'https://mmbiz.qpic.cn/fixture.png'}
            def verify_image(self, url, asset):
                if not self.uploads or digest(self.uploads[-1]) != asset['hash']: raise Problem('Fixture image mismatch')
                return {'url': url, 'hash': asset['hash']}
        for name, color in [('reviewed.png', 'blue'), ('substitute.png', 'red')]:
            path = self.k.vault.safe('Attachments/' + name); path.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (32, 32), color).save(path)
        a = self.k.read()[0][self.aid]
        self.edit(self.aid, body=a['body'] + '\n\n![Synthetic image](Attachments/reviewed.png)')
        self.approve(self.aid)
        adapter = Images(); service, _, prepared = self.prepare(adapter)
        build = copy.deepcopy(prepared['build']); asset = build['assets'][0]
        replacement, _ = rendering.load_asset(self.k.vault, 'Attachments/substitute.png')
        for key in ('path', 'mime', 'size', 'width', 'height', 'hash'): asset[key] = replacement[key]
        modified = self.edit(prepared['oc_id'], build=build)
        with self.assertRaises(Problem):
            service.confirm(modified['oc_id'], preview_hash(modified), 'fixture:human', self.token())
        self.assertEqual(adapter.uploads, [])
        self.assertEqual(adapter.calls.count('draft/add'), 0)

    def test_material_cannot_be_an_approved_mother_artifact(self):
        mother = self.k.read()[0][self.aid]
        material = self.k.add(self.pid, 'Material', 'Wrong-type mother', mother['body'], {'source': 'fixture:synthetic'}, self.token())
        material = self.edit(material['oc_id'], derived_from=mother['derived_from'])
        with self.assertRaises(Problem):
            social_graphic.mother_dependency(self.k, self.k.read()[0], material)
        vid = self.variant(material, approve=False)
        quality = self.k.inspect(vid)['gate']
        self.assertEqual(quality['dependency_status'], 'STALE')
        self.assertEqual(quality['status'], 'BLOCKED')
        with self.assertRaises(Problem): self.approve(vid)
        with self.assertRaises(Problem): rendering.export_build(self.k, vid, self.token())

    def test_missing_mother_blocks_without_crashing_board(self):
        vid = self.variant(self.k.read()[0][self.aid])
        mother = self.k.read()[0][self.aid]
        self.k.vault.safe(mother['path']).unlink()  # Remove only this test-created temporary source.
        quality = self.k.inspect(vid)['gate']
        self.assertEqual(quality['dependency_status'], 'STALE')
        self.assertFalse(quality['approved'])
        self.assertTrue(self.k.board()['projects'])
        with self.assertRaises(Problem): rendering.export_build(self.k, vid, self.token())

    def test_exact_second_repeated_selection_changes_only_that_range(self):
        text = 'Repeated synthetic sentence.'
        a = self.k.read()[0][self.aid]
        a = self.edit(self.aid, body=a['body'] + '\n\n' + text + '\n\n' + text)
        start = a['body'].rindex(text); end = start + len(text)
        selection = {'start': start, 'end': end, 'text': text, 'base_hash': digest({'title': a['title'], 'body': a['body']})}
        uid = 'b' * 32
        workbench.request(self.k, self.pid, 'Revise exactly the selected second occurrence', 'revise', [], uid, self.aid, selection)
        replacement = 'Only the second occurrence has changed.'
        workbench.complete(self.k, self.pid, uid, {'reply': 'Synthetic proposal.',
            'revision': {'artifact': self.aid, 'title': a['title'], 'body': replacement},
            'illustrations': [], 'images': []}, self.k.vault.runtime)
        workbench.apply_revision(self.k, self.pid, uid, self.token())
        self.assertEqual(self.k.read()[0][self.aid]['body'], a['body'][:start] + replacement + a['body'][end:])

    def test_exportable_image_requires_an_image_filename(self):
        stream = io.BytesIO(); Image.new('RGB', (16, 16), 'white').save(stream, format='PNG')
        for filename in ('fixture.png', 'fixture.JPG', 'fixture.jpeg'):
            path = self.k.vault.safe('Attachments/' + filename); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(stream.getvalue())
            self.assertEqual(rendering.load_asset(self.k.vault, 'Attachments/' + filename)[0]['mime'], 'image/png')
        for filename in ('fixture.html', 'fixture.txt', 'fixture.svg', 'fixture'):
            path = self.k.vault.safe('Attachments/' + filename); path.write_bytes(stream.getvalue())
            with self.subTest(filename=filename), self.assertRaises(Problem):
                rendering.load_asset(self.k.vault, 'Attachments/' + filename)
