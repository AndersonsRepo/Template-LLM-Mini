"""Direct behavioral contracts for strict parsing, schema rules, and summaries."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import data_analysis
import profiling


class DataQualityTests(unittest.TestCase):
    def test_json_never_silently_overwrites_keys_or_accepts_nonfinite_numbers(self):
        for value in (b'[{"id":1,"id":2}]', b'[{"x":NaN}]', b'[{"x":Infinity}]', b'[{"x":1e999}]'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                data_analysis.records(value, 'json', [])

    def test_nullable_type_range_unique_and_date_rules(self):
        cases = [
            (b'id\n\"\"\n', {'id': {'nullable': False}}),
            (b'[{"id":null}]', {'id': {'nullable': False}}),
            (b'[{"id":true}]', {'id': {'type': 'integer'}}),
            (b'[{"id":-1}]', {'id': {'minimum': 0}}),
            (b'[{"id":"2026-02-30"}]', {'id': {'type': 'date'}}),
            (b'[{"id":1},{"id":1}]', {'id': {'unique': True}}),
            (b'id\n01\n1\n', {'id': {'type':'integer', 'unique': True}}),
        ]
        for raw, rules in cases:
            with self.subTest(raw=raw):
                fmt = 'json' if raw.startswith(b'[') else 'csv'
                # A completely blank CSV row is not a record. Use a second field
                # to distinguish a present null id from an entirely empty record.
                if raw == b'id\n\"\"\n':
                    raw = b'id,other\n,exists\n'
                with self.assertRaises(ValueError):
                    data_analysis.records(raw, fmt, [], rules)
        raw = b'id,amount,day\n1,5,2026-10-25\n2,3,2026-10-26\n'
        self.assertEqual(data_analysis.records(raw, 'csv', ['id'], {
            'id': {'type':'integer','unique':True,'nullable':False},
            'amount': {'minimum':0}, 'day': {'type':'date'}}), 2)

    def test_settings_do_not_inspect_an_unrelated_working_directory(self):
        settings = {'mode':'auto','phases':['pre','post'],'data_access':'metadata-only',
                    'max_file_bytes':1000,'max_files':10,
                    'datasets':[{'path':'./data/raw/a.csv','phase':'pre','format':'csv',
                                 'required_columns':[], 'min_records':1,'purpose':'Example', 'required':True}]}
        import os
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            try:
                (root / 'actual').mkdir()
                try:
                    (root / 'data').symlink_to(root / 'actual', target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest('Symlink creation is not available')
                os.chdir(root)
                data_analysis.validate_settings(settings)  # Syntax-only; no unrelated filesystem checks.
                self.assertEqual(settings['datasets'][0]['path'], 'data/raw/a.csv')
            finally:
                os.chdir(previous)

    def test_profile_bounds_and_no_categorical_values(self):
        rows = [{'a':1, 'b':'PRIVATE_VALUE'}, {'a':3, 'b':None}, {'a':3, 'b':None}]
        summary = profiling.summarize(rows, 'json', 1)
        self.assertEqual(summary['duplicate_records'], 1)
        self.assertEqual(summary['omitted_columns'], 1)
        self.assertEqual(summary['columns']['a']['numeric']['mean'], 7/3)
        self.assertNotIn('PRIVATE_VALUE', json.dumps(summary))


if __name__ == '__main__':
    unittest.main()
