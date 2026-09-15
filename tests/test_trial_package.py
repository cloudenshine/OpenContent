import importlib.util
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from package_trial import build

class TrialPackageTests(unittest.TestCase):
    def test_trial_is_self_contained_without_private_data_and_cannot_claim_participants(self):
        result=build()
        with zipfile.ZipFile(result['archive']) as archive:
            names=archive.namelist()
            self.assertIn('SampleVault/.obsidian/plugins/opencontent/kernel/doctor.py',names)
            self.assertIn('SampleVault/.obsidian/plugins/opencontent/kernel/opencontent/origins.py',names)
            self.assertFalse(any('data.json' in n or '.opencontent/' in n or 'response.json' in n or '.validation' in n for n in names))
            state=json.loads(archive.read('trial-status.json'));self.assertEqual(state['external_participants'],0);self.assertEqual(state['public_release'],'BLOCKED')
            self.assertEqual(len(archive.read('feedback/first-use.csv').decode().splitlines()),1)
    def test_quality_cases_fixed_and_include_four_distinct_categories(self):
        suite=json.loads((ROOT/'tests/fixtures/ideation-quality.json').read_text(encoding='utf-8'));cases=suite['cases']
        self.assertEqual(len(cases),12);self.assertEqual(len({c['id'] for c in cases}),12)
        for category in ('focused','mixed','same-origin','insufficient'):self.assertEqual(len([c for c in cases if c['category']==category]),3)
