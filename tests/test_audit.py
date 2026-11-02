import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from audit import audit

ROOT = Path(__file__).resolve().parents[1]


class AuditTests(unittest.TestCase):
    def check_data(self, text, schema):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.csv'
            path.write_text(text, encoding='utf-8')
            return audit(path, schema)

    def test_example_contract_and_exit_codes(self):
        for filename, expected in [('orders.csv', 0), ('broken.csv', 1)]:
            result = subprocess.run([sys.executable, str(ROOT / 'audit.py'), str(ROOT / 'examples' / filename), '--schema', str(ROOT / 'examples/schema.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['valid'], expected == 0)

    def test_reports_distinct_failures(self):
        schema = json.loads((ROOT / 'examples/schema.json').read_text())
        report = audit(ROOT / 'examples/broken.csv', schema)
        self.assertEqual(report['issue_count'], 6)
        self.assertEqual({i['code'] for i in report['issues']}, {'duplicate', 'below_min', 'invalid_type', 'invalid_choice', 'missing_value'})

    def test_bom_and_quoted_multiline_record(self):
        result = self.check_data('\ufeffname,id\n"a\nb",1\nc,1\n', {'columns': {'id': {'type': 'integer', 'unique': True}}})
        self.assertEqual(result['issues'][0]['line'], 4)

    def test_missing_header_and_bad_row(self):
        report = self.check_data('id\n1,extra\n', {'columns': {'id': {}, 'amount': {}}})
        self.assertEqual([x['code'] for x in report['issues']], ['missing_column', 'row_width'])

    def test_normalized_numeric_uniqueness(self):
        report = self.check_data('id\n01\n1\n', {'columns': {'id': {'type': 'integer', 'unique': True}}})
        self.assertEqual(report['issues'][0]['code'], 'duplicate')

    def test_rejects_invalid_schema_and_headers(self):
        for text, schema in [('id,id\n1,2\n', {'columns': {'id': {}}}), ('id\n', {'columns': {}}), ('id\n', {'columns': {'id': {'type': 'blob'}}})]:
            with self.assertRaises(ValueError):
                self.check_data(text, schema)


if __name__ == '__main__':
    unittest.main()
