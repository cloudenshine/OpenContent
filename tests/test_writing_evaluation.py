"""The evaluation control must not accidentally contain the treatment."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from opencontent.kernel import Kernel
from opencontent.writing_quality import writing_policy

spec = importlib.util.spec_from_file_location('evaluate_writing', Path(__file__).resolve().parents[1] / 'scripts/evaluate_writing.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

class WritingEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.kernel = Kernel(self.tmp.name)
        self.pid = self.kernel.create_project('测试', '测试明确范围', '普通读者')['oc_id']
        self.request = self.kernel.request(self.pid, 'draft', [])

    def test_control_removes_entire_current_layer_but_preserves_every_other_field(self):
        pair = evaluation.paired_requests(self.request)
        baseline, enhanced = pair['baseline'], pair['enhanced']
        self.assertEqual(enhanced, self.request)
        self.assertNotIn('writing_quality', baseline)
        self.assertNotIn(writing_policy('draft')['instructions'], baseline['instructions'])
        self.assertEqual(baseline['instructions'] + '\n\n' + writing_policy('draft')['instructions'], enhanced['instructions'])
        for key in baseline.keys() - {'instructions'}:
            self.assertEqual(baseline[key], enhanced[key], key)
        self.assertNotEqual(evaluation.request_sha256(baseline), evaluation.request_sha256(enhanced))
        baseline['project']['goal'] = 'changed'
        self.assertNotEqual(baseline['project'], self.request['project'])

    def test_control_rejects_stale_or_tampered_metadata_and_nonwriting_input(self):
        for field in ('version', 'sha256', 'prompt_sha256'):
            request = copy.deepcopy(self.request)
            request['writing_quality'][field] = 'wrong'
            with self.assertRaises(ValueError): evaluation.paired_requests(request)
        request = copy.deepcopy(self.request); request['instructions'] += '\nUnexpected instruction'
        with self.assertRaises(ValueError): evaluation.paired_requests(request)
        with self.assertRaises(ValueError): evaluation.paired_requests(self.kernel.request(self.pid, 'research', []))

    def test_missing_process_log_does_not_hide_original_failure(self):
        self.assertEqual(evaluation.runtime_identity(Path(self.tmp.name)), {})
