"""Behavioral checks in isolated template copies; no provider calls."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        # Copy only harness source, never adopted state, datasets, or environments.
        names = ['.gitignore', 'AGENTS.md', 'README.md', 'CONFIGURE.md',
                 'prompts/template_prompt_initialization.md', 'memories/template-index.md']
        for folder in ('scripts', 'templates', 'prompts/roles'):
            names += [p.relative_to(SOURCE).as_posix() for p in (SOURCE / folder).rglob('*')
                      if p.is_file() and p.suffix in ('.py', '.md', '.json')]
        names += [p.relative_to(SOURCE).as_posix() for p in (SOURCE / 'tests').glob('*.py')]
        names += [f'data/{folder}/.gitkeep' for folder in ('raw', 'processed', 'generated')]
        for name in names:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, destination)
        c = json.loads((self.root / 'templates/config.json').read_text())
        c['project'] = dict(name='Sample', purpose='Example', users='Developer',
                            scope='One feature', exclusions='Deployment', acceptance_criteria=['Works'])
        c['technology'] = 'Python'
        c['data'].update(usage='Synthetic examples only', sources='none',
                         sensitivity='Public synthetic data', expected_size='Under 1 MB',
                         retention='Keep for project lifetime', generated_outputs='Example records',
                         approved_git_exceptions='none')
        c['delegation']['capabilities'] = 'Independent review session'
        c['validation']['commands'] = [[sys.executable, '-c', 'assert 2 + 2 == 4']]
        c['approvals'] = 'Configuration and external publication'
        c['delivery'] = 'Local working feature'
        self.config = c
        self.put('config.json', c)
        self.put('example.py', 'assert 2 + 2 == 4\n')
        self.put('prompt.md', 'Add an example feature.\n')
        self.put('review.md', 'Reviewed implementation against Works; no findings.\n')
        self.put('memory.md', 'Behavior: example. Decision: small. Validation: arithmetic. Limitations: synthetic.\n')
        self.put('handoff.json', dict(objective='Works', files=['example.py'], memories=[],
                 decisions='Small scope', changes='Example', validation='See recorded checks',
                 unresolved='none', next_action='Evaluate acceptance criteria'))

    def put(self, name, data):
        (self.root / name).write_text(json.dumps(data) if not isinstance(data, str) else data)

    def run_cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/workflow.py'), *args],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def configure(self):
        self.run_cli('configure', '--config', 'config.json', '--approved')

    def add(self, depends=None, data='none', phases=None):
        args = ['add', '--title', 'Example', '--criterion', 'Works', '--prompt', 'prompt.md']
        args += ['--data', data]
        if data == 'none':
            args += ['--data-reason', 'Arithmetic fixture does not require datasets']
        for phase in phases or []:
            args += ['--analysis-phase', phase]
        if depends:
            args += ['--depends', depends]
        return self.run_cli(*args).stdout.strip()

    def handoff(self, target):
        self.run_cli('handoff', 'T001', '--to', target, '--file', 'handoff.json')

    def task(self):
        return json.loads((self.root / '.workflow/state.json').read_text())['tasks'][0]

    def test_full_feature_and_completion_gates(self):
        self.configure(); self.add()
        self.run_cli('done', 'T001', success=False)
        self.run_cli('start', 'T001'); self.handoff('reviewer')
        self.run_cli('test', 'T001', success=False)
        self.run_cli('review', 'T001', '--verdict', 'pass', '--file', 'review.md')
        self.handoff('tester'); self.run_cli('test', 'T001')
        self.run_cli('done', 'T001', success=False)
        self.run_cli('memory', 'T001', '--file', 'memory.md')
        self.run_cli('done', 'T001', success=False)
        self.handoff('coordinator'); self.run_cli('done', 'T001'); self.run_cli('check')
        self.assertEqual(self.task()['status'], 'done')
        self.assertEqual(len(self.task()['prompts']), 5)
        self.assertIn('T001', (self.root / 'memories/index.md').read_text())
        self.assertIn('Sample', (self.root / 'PROJECT.md').read_text())
        self.assertNotIn('Public synthetic data', (self.root / 'AGENTS.md').read_text())
        self.assertIn('Python', (self.root / 'AGENTS.md').read_text())
        self.assertIn('data/generated/', (self.root / 'AGENTS.md').read_text())
        self.run_cli('start', 'T001', success=False)

    def test_rejection_repair_limit_and_dependencies(self):
        self.config['handoffs']['max_repairs'] = 0
        self.put('config.json', self.config); self.configure(); self.add(); self.add('T001')
        self.run_cli('start', 'T002', success=False)
        self.run_cli('start', 'T001'); self.handoff('reviewer')
        self.run_cli('review', 'T001', '--verdict', 'fail', '--file', 'review.md')
        self.assertEqual(self.task()['status'], 'blocked')
        self.run_cli('unblock', 'T001', success=False)

    def test_failed_validation_invalidates_review(self):
        self.config['validation']['commands'] = [[sys.executable, '-c', 'raise SystemExit(3)']]
        self.put('config.json', self.config); self.configure(); self.add()
        self.run_cli('start', 'T001'); self.handoff('reviewer')
        self.run_cli('review', 'T001', '--verdict', 'pass', '--file', 'review.md')
        self.handoff('tester'); self.run_cli('test', 'T001', success=False)
        self.assertEqual(self.task()['status'], 'building')
        self.assertFalse(self.task()['review_pass'])
        self.run_cli('memory', 'T001', '--file', 'memory.md', success=False)

    def test_approval_and_configuration_validation(self):
        self.run_cli('configure', '--config', 'config.json', success=False)
        self.config['validation']['commands'] = []
        self.put('config.json', self.config)
        self.run_cli('configure', '--config', 'config.json', '--approved', success=False)
        self.assertFalse((self.root / '.workflow/config.json').exists())

    def test_missing_evidence_is_detected(self):
        self.configure(); self.add()
        (self.root / self.task()['prompts'][0]).unlink()
        self.run_cli('check', success=False)

    def test_malformed_handoff_does_not_advance_task(self):
        self.configure(); self.add(); self.run_cli('start', 'T001')
        self.put('bad.json', {'objective': 'Missing remaining fields'})
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'bad.json', success=False)
        self.assertEqual(self.task()['status'], 'building')

    def test_data_configuration_requires_answers_and_preserves_policies(self):
        self.config['data']['sources'] = ''
        self.put('config.json', self.config)
        self.run_cli('configure', '--config', 'config.json', '--approved', success=False)
        self.config['data']['sources'] = 'none'
        self.config['data']['raw_policy'] = 'Overwrite originals'
        self.put('config.json', self.config)
        self.run_cli('configure', '--config', 'config.json', '--approved', success=False)
        self.assertFalse((self.root / '.workflow/config.json').exists())

    @unittest.skipUnless(shutil.which('git'), 'Git is needed to verify ignore behavior')
    def test_git_ignores_datasets_but_preserves_layout(self):
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True, capture_output=True)
        for folder in ('raw', 'processed', 'generated'):
            base = self.root / 'data' / folder
            self.assertTrue((base / '.gitkeep').is_file())
            (base / 'nested').mkdir()
            for name in ('records.csv', 'nested/records.json'):
                (base / name).write_text('sample')
                result = subprocess.run(['git', 'check-ignore', '--no-index', '-q',
                                         f'data/{folder}/{name}'], cwd=self.root)
                self.assertEqual(result.returncode, 0)
            result = subprocess.run(['git', 'check-ignore', '--no-index', '-q',
                                     f'data/{folder}/.gitkeep'], cwd=self.root)
            self.assertEqual(result.returncode, 1)


    def prepare_testing(self):
        self.configure(); self.add(); self.run_cli('start', 'T001')
        self.handoff('reviewer')
        self.run_cli('review', 'T001', '--verdict', 'pass', '--file', 'review.md')
        self.handoff('tester')

    def finish(self):
        self.run_cli('test', 'T001')
        self.run_cli('memory', 'T001', '--file', 'memory.md')
        self.handoff('coordinator'); self.run_cli('done', 'T001')

    def test_source_changes_invalidate_passes(self):
        self.prepare_testing(); self.run_cli('test', 'T001')
        self.put('example.py', 'raise RuntimeError("changed")\n')
        self.run_cli('memory', 'T001', '--file', 'memory.md', success=False)
        self.assertEqual(self.task()['status'], 'building')
        self.assertFalse(self.task()['review_pass'])
        self.assertFalse(self.task()['test_pass'])

    def test_added_source_file_invalidates_review(self):
        self.prepare_testing()
        self.put('scripts/new_feature.py', 'print("new")\n')
        self.run_cli('test', 'T001', success=False)
        self.assertFalse(self.task()['review_pass'])

    def test_completion_rejects_missing_memory(self):
        self.prepare_testing(); self.run_cli('test', 'T001')
        self.run_cli('memory', 'T001', '--file', 'memory.md'); self.handoff('coordinator')
        (self.root / self.task()['memories'][-1]).unlink()
        self.run_cli('done', 'T001', success=False)
        self.run_cli('check', success=False)

    def test_tampered_evidence_rejected(self):
        self.prepare_testing(); self.run_cli('test', 'T001')
        record = self.root / self.task()['reviews'][-1]
        record.write_text(record.read_text().replace('"pass"', '"fail"'))
        self.run_cli('memory', 'T001', '--file', 'memory.md', success=False)
        self.run_cli('check', success=False)

    def test_later_source_changes_preserve_completed_history(self):
        self.prepare_testing(); self.finish()
        self.put('example.py', 'print("next feature")\n')
        self.run_cli('check')
        self.assertEqual(self.task()['status'], 'done')

    def test_checkpoint_resume_and_stale_warning(self):
        self.configure(); self.add(); self.run_cli('start', 'T001')
        before = self.task()['status']
        self.run_cli('checkpoint', 'T001', '--file', 'handoff.json')
        resumed = json.loads(self.run_cli('resume', 'T001', '--role', 'builder').stdout)
        self.assertEqual(before, self.task()['status'])
        self.assertFalse(resumed['checkpoint_stale'])
        self.assertEqual(resumed['checkpoints']['content']['next_action'], 'Evaluate acceptance criteria')
        self.put('example.py', 'print("later change")\n')
        resumed = json.loads(self.run_cli('resume', 'T001').stdout)
        self.assertTrue(resumed['checkpoint_stale'])

    def test_context_budget_reports_omissions(self):
        self.prepare_testing()
        h = json.loads((self.root / 'handoff.json').read_text())
        h['changes'] = 'large detail ' * 2000
        self.put('handoff.json', h)
        self.run_cli('checkpoint', 'T001', '--file', 'handoff.json')
        r = self.run_cli('context', 'T001', '--role', 'tester', '--max-chars', '2000')
        packet = json.loads(r.stdout)
        self.assertLessEqual(len(r.stdout.strip()), 2000)
        self.assertTrue(packet['omitted'])
        self.assertEqual(packet['criteria'], ['Works'])
        self.assertIn('checkpoints', packet['latest'])

    def test_status_and_show_are_focused(self):
        self.prepare_testing(); self.finish(); self.add()
        active = json.loads(self.run_cli('status').stdout)
        self.assertEqual([x['id'] for x in active], ['T002'])
        all_tasks = json.loads(self.run_cli('status', '--all').stdout)
        self.assertEqual(len(all_tasks), 2)
        view = json.loads(self.run_cli('show', 'T001').stdout)
        self.assertNotIn('artifacts', view)
        self.assertEqual(view['status'], 'done')

    def test_assignment_logs_reference_handoffs_without_copying(self):
        self.prepare_testing()
        logged = (self.root / self.task()['prompts'][-1]).read_text()
        self.assertIn(self.task()['handoffs'][-1], logged)
        self.assertNotIn('"acceptance_criteria"', logged)
        self.assertIn('prompts/roles/tester.md', logged)

    def test_history_survives_configuration_and_saves(self):
        old = (self.root / 'memories/template-index.md').read_text()
        self.configure(); self.add()
        self.assertIn(old, (self.root / 'memories/index.md').read_text())

    def test_strict_config_types_and_source_exclusions(self):
        self.config['project']['purpose'] = 7
        self.put('config.json', self.config)
        self.run_cli('configure', '--config', 'config.json', '--approved', success=False)
        self.config['project']['purpose'] = 'Sample'
        self.config['validation']['source_paths'] = ['data/raw']
        self.put('config.json', self.config)
        self.run_cli('configure', '--config', 'config.json', '--approved', success=False)

    def test_data_changes_do_not_invalidate_sources(self):
        self.prepare_testing()
        self.put('data/raw/input.csv', 'unrelated data\n')
        self.run_cli('test', 'T001')
        self.assertTrue(self.task()['test_pass'])

    def test_summary_diagnostics_are_explicit_and_bounded(self):
        self.config['validation'].update(diagnostics='summary', summary_max_chars=5, timeout_seconds=120)
        self.config['validation']['commands'] = [[sys.executable, '-c',
            'import json; print(json.dumps({"summary": "safe diagnostic"})); raise SystemExit(3)']]
        self.put('config.json', self.config); self.prepare_testing()
        self.run_cli('test', 'T001', success=False)
        record = json.loads((self.root / self.task()['tests'][-1]).read_text())
        self.assertEqual(record['results'][0]['summary'], 'safe ')
        self.assertTrue(record['results'][0]['summary_truncated'])

    def test_raw_diagnostics_are_not_saved(self):
        self.config['validation']['commands'] = [[sys.executable, '-c',
            'print("PRIVATE-" + str(42)); raise SystemExit(3)']]
        self.put('config.json', self.config); self.prepare_testing()
        self.run_cli('test', 'T001', success=False)
        content = (self.root / self.task()['tests'][-1]).read_text()
        self.assertNotIn('PRIVATE-42', content)

    def test_checks_that_change_source_invalidate_their_results(self):
        self.config['validation']['commands'] = [[sys.executable, '-c',
            'from pathlib import Path; Path("example.py").write_text("changed")']]
        self.put('config.json', self.config); self.prepare_testing()
        self.run_cli('test', 'T001', success=False)
        self.assertFalse(self.task()['test_pass'])
        self.assertEqual(self.task()['status'], 'building')

    def test_setup_works_from_configured_adoption_without_copying_data(self):
        self.configure()
        self.put('data/raw/private.csv', 'private data')
        (self.root / '.venv').mkdir()
        self.put('.venv/large.bin', 'unwanted environment')
        namespace = type(self).setUp.__globals__
        original = namespace['SOURCE']
        other = type(self)()
        try:
            namespace['SOURCE'] = self.root
            other.setUp()
            other.configure()
            self.assertFalse((other.root / 'data/raw/private.csv').exists())
            self.assertFalse((other.root / '.venv').exists())
        finally:
            namespace['SOURCE'] = original
            other.doCleanups()


    def analyzer_pass(self, phase):
        self.put('analysis.md', 'Findings: data fits the request. Limitations: synthetic example only.\n')
        self.run_cli('analysis-report', 'T001', '--phase', phase, '--verdict', 'pass', '--file', 'analysis.md')

    def test_empty_data_automatically_skips_analyzer(self):
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001')
        self.assertEqual(self.task()['status'], 'building')
        self.assertEqual(self.task()['analysis_state']['pre']['status'], 'skipped')
        self.assertEqual(self.task()['analyses'], [])
        self.assertEqual(self.task()['inspections'], [])

    def test_pre_and_post_analysis_complete_without_exposing_records(self):
        original = 'id,value\n1,PRIVATE_VALUE_42\n'
        self.put('data/raw/input.csv', original)
        self.configure(); self.add(data='auto')
        self.run_cli('start', 'T001', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')
        packet = self.run_cli('context', 'T001', '--role', 'analyzer').stdout
        self.assertNotIn('PRIVATE_VALUE_42', packet)
        self.assertIn('metadata-only', packet)
        self.analyzer_pass('pre')
        self.put('data/processed/output.json', [{'id': 1, 'total': 2}])
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        self.assertEqual(self.task()['analysis_pending']['phase'], 'post')
        self.analyzer_pass('post'); self.handoff('reviewer')
        self.run_cli('review', 'T001', '--verdict', 'pass', '--file', 'review.md')
        self.handoff('tester'); self.finish(); self.run_cli('check')
        self.assertEqual((self.root / 'data/raw/input.csv').read_text(), original)
        self.assertEqual(len(self.task()['analyses']), 2)
        self.put('data/raw/input.csv', 'id,value\n2,newer_dataset\n')
        self.run_cli('check')  # Saved historical reports remain valid.

    def test_expected_missing_data_asks_and_does_not_block_other_tasks(self):
        self.configure(); self.add(data='expected')
        result = self.run_cli('start', 'T001', success=False)
        self.assertIn('User question:', result.stdout)
        self.assertEqual(self.task()['status'], 'awaiting-data')
        other = self.add(); self.run_cli('start', other)
        self.put('data/raw/input.csv', 'id\n1\n')
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')
        self.analyzer_pass('pre')
        self.assertEqual(self.task()['status'], 'building')

    def test_schema_mismatch_asks_for_correct_data(self):
        spec = json.loads((self.root / 'templates/dataset.json').read_text())
        spec.update(path='data/raw/input.csv', required_columns=['required_id'])
        self.config['analysis']['datasets'] = [spec]
        self.put('config.json', self.config)
        self.put('data/raw/input.csv', 'wrong_column\nvalue\n')
        self.configure(); self.add(data='auto')
        result = self.run_cli('start', 'T001', success=False)
        self.assertIn('required columns missing', result.stdout)
        self.assertEqual(self.task()['analyses'], [])
        self.assertEqual(self.task()['status'], 'awaiting-data')

    def test_semantic_mismatch_requires_a_user_response(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.put('analysis.md', 'The file appears unrelated to the requested sales data.')
        self.run_cli('analysis-report', 'T001', '--phase', 'pre', '--verdict', 'needs-input',
                     '--file', 'analysis.md', '--question', 'Is this the correct sales dataset?')
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.put('reply.md', 'Yes, use this dataset; the identifiers represent sales.')
        self.run_cli('data-resolve', 'T001', '--file', 'reply.md', success=False)
        self.run_cli('data-resolve', 'T001', '--file', 'reply.md', '--approved', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')
        self.analyzer_pass('pre')
        self.assertEqual(self.task()['status'], 'building')

    def test_changed_data_requires_new_analysis_and_review(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.analyzer_pass('pre'); self.handoff('reviewer')
        self.run_cli('review', 'T001', '--verdict', 'pass', '--file', 'review.md'); self.handoff('tester')
        self.put('data/raw/input.csv', 'id\n2\n')
        self.run_cli('test', 'T001', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')
        self.assertFalse(self.task()['review_pass'])
        self.analyzer_pass('pre')
        self.assertEqual(self.task()['status'], 'building')

    def test_changed_data_rejects_in_progress_analysis_report(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.put('data/raw/input.csv', 'id\n2\n')
        self.put('analysis.md', 'Stale findings')
        self.run_cli('analysis-report', 'T001', '--phase', 'pre', '--verdict', 'pass',
                     '--file', 'analysis.md', success=False)
        self.assertEqual(self.task()['analyses'], [])
        self.analyzer_pass('pre')

    def test_user_can_explicitly_revise_data_scope(self):
        self.configure(); self.add(data='expected'); self.run_cli('start', 'T001', success=False)
        self.put('reply.md', 'Approved scope change: this task does not need data.')
        self.run_cli('data-resolve', 'T001', '--file', 'reply.md', '--approved', '--data', 'none')
        self.assertEqual(self.task()['status'], 'building')
        self.assertEqual(self.task()['data_mode'], 'none')
        self.assertEqual(self.task()['analysis_state']['pre']['status'], 'skipped')

    def test_unsupported_and_empty_data_do_not_launch_analyzer(self):
        self.put('data/raw/input.bin', 'binary format requires a custom extractor')
        self.put('data/raw/empty.txt', '')
        self.configure(); self.add(data='auto')
        self.run_cli('start', 'T001', success=False)
        self.assertEqual(self.task()['status'], 'awaiting-data')
        saved = (self.root / self.task()['inspections'][-1]).read_text()
        self.assertIn('unsupported format', saved)
        self.assertIn('empty content', saved)
        self.assertEqual(self.task()['analyses'], [])

    def test_generated_data_can_use_post_only_analysis(self):
        self.configure(); self.add(data='expected', phases=['post'])
        self.run_cli('start', 'T001')
        self.put('data/generated/output.jsonl', '{"id":1}\n')
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        self.analyzer_pass('post'); self.handoff('reviewer')
        self.assertNotIn('pre', self.task()['analysis_state'])

    def test_analysis_limits_and_bad_settings_are_explicit(self):
        self.config['analysis']['max_file_bytes'] = 3
        self.put('config.json', self.config)
        self.put('data/raw/input.txt', 'too large')
        self.configure(); self.add(data='auto')
        result = self.run_cli('start', 'T001', success=False)
        self.assertIn('size limit', result.stdout)
        self.assertEqual(self.task()['status'], 'awaiting-data')


    def provenance_entry(self, path, **overrides):
        entry = json.loads((self.root / 'templates/provenance.json').read_text())
        entry.update(path=path, **overrides)
        return entry

    def test_inspection_preserves_declared_source_and_locator(self):
        entry = self.provenance_entry('data/raw/input.csv', source='Publisher export 2026-10',
                                      locator='sheet Sales, rows 2-5, field id')
        self.config['data']['provenance'] = [entry]
        self.put('config.json', self.config)
        self.put('data/raw/input.csv', 'id\nPRIVATE_ROW_VALUE\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        record = json.loads((self.root / self.task()['inspections'][-1]).read_text())
        provenance = record['inspection']['files'][0]['provenance']
        self.assertEqual(provenance['source'], entry['source'])
        self.assertEqual(provenance['locator'], entry['locator'])
        self.assertEqual(provenance['attribution'], 'provided; not independently verified')
        self.assertNotIn('PRIVATE_ROW_VALUE', self.run_cli('context', 'T001', '--role', 'analyzer').stdout)

    def test_unknown_origins_explicit_even_in_generated_folder(self):
        self.put('data/generated/input.json', [{'id': 1}])
        self.configure(); self.add(data='auto', phases=['post']); self.run_cli('start', 'T001')
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        record = json.loads((self.root / self.task()['inspections'][-1]).read_text())
        provenance = record['inspection']['files'][0]['provenance']
        self.assertEqual(provenance['kind'], 'unknown')
        self.assertEqual(provenance['source'], 'source unavailable')
        self.assertEqual(provenance['locator'], 'source unavailable')
        self.assertNotEqual(provenance['attribution'], 'exempt')

    def test_original_generated_content_has_explicit_exemption(self):
        self.config['data']['provenance'] = [self.provenance_entry('data/generated/input.json', kind='generated')]
        self.put('config.json', self.config); self.put('data/generated/input.json', [{'id': 1}])
        self.configure(); self.add(data='auto', phases=['post']); self.run_cli('start', 'T001')
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        record = json.loads((self.root / self.task()['inspections'][-1]).read_text())
        provenance = record['inspection']['files'][0]['provenance']
        self.assertEqual(provenance['attribution'], 'exempt')
        self.assertIn('not required', provenance['source'])

    def test_derived_outputs_retain_original_source_lineage(self):
        raw = self.provenance_entry('data/raw/input.csv', source='Original exported ledger', locator='row 2')
        derived = self.provenance_entry('data/processed/output.json', kind='derived',
                                        derived_from=['data/raw/input.csv'])
        self.config['data']['provenance'] = [raw, derived]
        self.put('config.json', self.config); self.put('data/raw/input.csv', 'id\n1\n')
        self.put('data/processed/output.json', [{'id': 1}])
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.analyzer_pass('pre')
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        record = json.loads((self.root / self.task()['inspections'][-1]).read_text())
        lineage = record['inspection']['files'][0]['provenance']['lineage']
        self.assertEqual(lineage[0]['source'], raw['source'])
        self.assertEqual(lineage[0]['locator'], 'row 2')

    def test_provenance_rejects_external_paths_cycles_and_false_exemptions(self):
        cases = [
            [self.provenance_entry('outside.csv')],
            [self.provenance_entry('data/raw/a.csv', kind='derived', derived_from=['../outside.csv'])],
            [self.provenance_entry('data/raw/a.csv', kind='derived', derived_from=['data/raw/b.csv']),
             self.provenance_entry('data/raw/b.csv', kind='derived', derived_from=['data/raw/a.csv'])],
            [self.provenance_entry('data/generated/a.json', kind='generated', derived_from=['data/raw/a.csv'])],
        ]
        for declarations in cases:
            with self.subTest(declarations=declarations):
                self.config['data']['provenance'] = declarations
                self.put('config.json', self.config)
                self.run_cli('configure', '--config', 'config.json', '--approved', success=False)
                self.assertFalse((self.root / '.workflow/config.json').exists())

    def test_provenance_changes_require_reassessment(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        c = json.loads((self.root / '.workflow/config.json').read_text())
        c['data']['provenance'] = [self.provenance_entry('data/raw/input.csv', source='Newly supplied original source')]
        self.put('.workflow/config.json', c)  # Simulate an explicitly reviewed configuration update.
        self.put('analysis.md', 'Stale origin details')
        self.run_cli('analysis-report', 'T001', '--phase', 'pre', '--verdict', 'pass', '--file', 'analysis.md', success=False)
        self.assertEqual(self.task()['analyses'], [])
        record = json.loads((self.root / self.task()['inspections'][-1]).read_text())
        self.assertEqual(record['inspection']['files'][0]['provenance']['source'], 'Newly supplied original source')


    def test_equivalent_dataset_paths_keep_schema_requirements(self):
        spec = json.loads((self.root / 'templates/dataset.json').read_text())
        spec.update(path='data/raw/input.csv', required_columns=['required_id'])
        self.config['analysis']['datasets'] = [spec]
        self.put('config.json', self.config); self.put('data/raw/input.csv', 'wrong_column\n1\n')
        self.configure()
        self.run_cli('add', '--title', 'Analyze', '--criterion', 'Schema valid', '--prompt', 'prompt.md',
                     '--data', 'expected', '--dataset', './data/raw/input.csv')
        self.run_cli('start', 'T001', success=False)
        self.assertEqual(self.task()['datasets'], ['data/raw/input.csv'])
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.assertIn('required columns missing', self.task()['data_question'])

    def test_explicit_dataset_phase_conflict_rejected_at_intake(self):
        self.configure()
        self.run_cli('add', '--title', 'Analyze', '--criterion', 'Valid', '--prompt', 'prompt.md',
                     '--data', 'expected', '--dataset', 'data/generated/output.csv',
                     '--analysis-phase', 'pre', success=False)
        self.assertEqual(json.loads((self.root / '.workflow/state.json').read_text())['tasks'], [])

    def test_disappeared_input_requires_user_question_not_skip(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.analyzer_pass('pre'); (self.root / 'data/raw/input.csv').unlink()
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.assertIn('missing', self.task()['data_question'])
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        self.assertEqual(self.task()['status'], 'awaiting-data')

    def test_pending_inspection_staleness_reported_before_model_work(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.put('data/raw/input.csv', 'id\n2\n')
        packet = json.loads(self.run_cli('context', 'T001', '--role', 'analyzer').stdout)
        self.assertTrue(packet['analysis_stale'])
        self.run_cli('check', success=False)
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        packet = json.loads(self.run_cli('context', 'T001', '--role', 'analyzer').stdout)
        self.assertFalse(packet['analysis_stale'])

    def test_context_prefers_inspection_over_generic_configuration(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        result = self.run_cli('context', 'T001', '--role', 'analyzer', '--max-chars', '3500')
        packet = json.loads(result.stdout)
        self.assertIn('inspections', packet)
        self.assertEqual(packet['active_analysis']['phase'], 'pre')
        self.assertNotIn('validation', packet)
        self.assertLessEqual(len(result.stdout.strip()), 3500)

    def test_ambiguous_json_does_not_reach_analyzer(self):
        self.configure()
        for index, raw in enumerate(('[{"id":1,"id":2}]', '[{"id":NaN}]', '[{"id":Infinity}]', '[{"id":1e999}]'), 1):
            name = f'data/raw/input{index}.json'
            self.put(name, raw)
            task = self.run_cli('add', '--title', 'Analyze', '--criterion', 'Valid JSON', '--prompt', 'prompt.md',
                                '--dataset', name).stdout.strip()
            self.run_cli('start', task, success=False)
        tasks = json.loads((self.root / '.workflow/state.json').read_text())['tasks']
        self.assertTrue(all(task['status'] == 'awaiting-data' and not task['analyses'] for task in tasks))

    def test_optional_column_contracts_enforced_without_rewriting(self):
        spec = json.loads((self.root / 'templates/dataset.json').read_text())
        spec.update(path='data/raw/input.csv', column_rules={'id': {'type':'integer','nullable':False,'unique':True},
                    'amount': {'type':'number','minimum':0}, 'day': {'type':'date'}})
        self.config['analysis']['datasets'] = [spec]
        self.put('config.json', self.config)
        original = 'id,amount,day\n1,-5,2026-10-25\n1,2,not-a-date\n'
        self.put('data/raw/input.csv', original)
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.assertEqual((self.root / 'data/raw/input.csv').read_text(), original)
        self.put('data/raw/input.csv', 'id,amount,day\n1,5,2026-10-25\n2,2,2026-10-26\n')
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')

    def test_upstream_version_changes_invalidate_selected_derived_data(self):
        self.config['data']['provenance'] = [self.provenance_entry('data/processed/output.json', kind='derived',
                                                                 derived_from=['data/raw/input.csv'])]
        self.put('config.json', self.config)
        self.put('data/raw/input.csv', 'id\n1\n'); self.put('data/processed/output.json', [{'id':1}])
        self.configure(); self.add(data='auto', phases=['post']); self.run_cli('start', 'T001')
        self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        old = (self.root / self.task()['inspections'][-1]).read_text()
        self.put('data/raw/input.csv', 'id\n2\n')
        packet = json.loads(self.run_cli('context', 'T001', '--role', 'analyzer').stdout)
        self.assertTrue(packet['analysis_stale'])
        self.run_cli('data-check', 'T001', '--phase', 'post', success=False)
        new = (self.root / self.task()['inspections'][-1]).read_text()
        self.assertNotEqual(old, new)
        self.assertIn('observed current parent', new)

    def enable_profiles(self):
        self.config['analysis']['data_access'] = 'approved-summaries'
        self.config['analysis']['profiling']['enabled'] = True
        self.put('config.json', self.config)

    def test_profile_aggregate_contract_and_default_off(self):
        self.put('data/raw/input.csv', 'amount,name\n1,PRIVATE_NAME_42\n3,OTHER_NAME\n3,OTHER_NAME\n')
        self.enable_profiles(); self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.run_cli('profile', 'T001', '--phase', 'pre')
        record = json.loads((self.root / self.task()['profiles'][-1]).read_text())
        summary = record['summary']['files'][0]
        self.assertEqual(summary['duplicate_records'], 1)
        self.assertEqual(summary['columns']['amount']['numeric']['mean'], 7/3)
        packet = self.run_cli('context', 'T001', '--role', 'analyzer').stdout
        self.assertIn('"profile"', packet)
        self.assertNotIn('PRIVATE_NAME_42', packet)

    def test_profile_requires_explicit_approved_access(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.run_cli('profile', 'T001', '--phase', 'pre', success=False)
        self.assertEqual(self.task()['profiles'], [])

    def test_configuration_preflight_and_preview_do_not_mutate_state(self):
        self.configure(); self.add()
        before = (self.root / '.workflow/state.json').read_bytes()
        self.run_cli('validate-config', '--config', 'config.json')
        self.config['context']['max_chars'] = 9000
        self.put('candidate.json', self.config)
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        self.assertIn('context.max_chars', [item['path'] for item in preview['changes']])
        self.assertEqual(before, (self.root / '.workflow/state.json').read_bytes())
        self.assertFalse((self.root / '.workflow/config-revisions').exists())
        self.run_cli('update-config', '--config', 'candidate.json', '--approved', success=False)

    def test_config_update_rejects_stale_preview_and_preserves_history(self):
        self.prepare_testing(); self.finish(); self.add()
        self.config['context']['max_chars'] = 9000
        self.put('candidate.json', self.config)
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        self.run_cli('log', 'T002', '--file', 'prompt.md')
        self.run_cli('update-config', '--config', 'candidate.json', '--approved',
                     '--preview-hash', preview['preview_hash'], success=False)
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        old_artifacts = dict(self.task()['artifacts'])
        self.run_cli('update-config', '--config', 'candidate.json', '--approved', '--preview-hash', preview['preview_hash'])
        self.assertEqual(self.task()['status'], 'done')
        self.assertEqual(self.task()['artifacts'], old_artifacts)
        self.run_cli('check')
        revision = next((self.root / '.workflow/config-revisions').glob('*.json'))
        saved = json.loads(revision.read_text())
        self.assertEqual(saved['status'], 'applied')
        self.assertEqual(len(saved['previous_state']['tasks']), 2)

    def test_profile_not_exposed_after_access_restriction(self):
        self.put('data/raw/input.csv', 'amount\n1\n3\n')
        self.enable_profiles(); self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.run_cli('profile', 'T001', '--phase', 'pre')
        self.config['analysis']['profiling']['enabled'] = False
        self.config['analysis']['data_access'] = 'metadata-only'
        self.put('candidate.json', self.config)
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        self.run_cli('update-config', '--config', 'candidate.json', '--approved', '--preview-hash', preview['preview_hash'])
        packet = json.loads(self.run_cli('context', 'T001', '--role', 'analyzer').stdout)
        self.assertNotIn('profile', packet)
        self.assertTrue(self.task()['profiles'])  # History preserved without injecting summaries.


    def test_config_update_preserves_unanswered_semantic_question(self):
        self.put('data/raw/input.csv', 'id\n1\n')
        self.configure(); self.add(data='auto'); self.run_cli('start', 'T001', success=False)
        self.put('analysis.md', 'Dataset meaning is unclear.')
        self.run_cli('analysis-report', 'T001', '--phase', 'pre', '--verdict', 'needs-input',
                     '--file', 'analysis.md', '--question', 'What does the id represent?')
        self.config['context']['max_chars'] = 9000
        self.put('candidate.json', self.config)
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        self.run_cli('update-config', '--config', 'candidate.json', '--approved', '--preview-hash', preview['preview_hash'])
        self.assertEqual(self.task()['status'], 'awaiting-data')
        self.assertEqual(self.task()['data_question'], 'What does the id represent?')
        self.run_cli('data-check', 'T001', '--phase', 'pre', success=False)
        self.put('reply.md', 'The id is a sales identifier; use this dataset.')
        self.run_cli('data-resolve', 'T001', '--file', 'reply.md', '--approved', success=False)
        self.assertEqual(self.task()['status'], 'analyzing')

    def test_guidance_edits_are_in_preview_and_invalidate_old_approval(self):
        self.configure()
        (self.root / 'AGENTS.md').write_text((self.root / 'AGENTS.md').read_text() + '\nCustom project rule.\n')
        preview = json.loads(self.run_cli('update-config', '--config', 'config.json').stdout)
        self.assertIn('Custom project rule.', preview['guidance_changes']['AGENTS.md'])
        (self.root / 'PROJECT.md').write_text('Changed after preview\n')
        self.run_cli('update-config', '--config', 'config.json', '--approved', '--preview-hash', preview['preview_hash'], success=False)


    def decision_payload(self, decision='Use Python for deterministic work'):
        payload = json.loads((self.root / 'templates/decision.json').read_text())
        payload.update(decision=decision, rationale='Avoid unnecessary model calls.',
                       outcome='Python selected; validation tracked separately.', evidence=['prompt.md'])
        self.put('decision.json', payload)

    def test_project_decision_before_config_and_automatic_milestones(self):
        self.decision_payload()
        first = self.run_cli('decide', '--file', 'decision.json').stdout.strip()
        prefix = (self.root / 'logging/journal.jsonl').read_bytes()
        self.prepare_testing(); self.finish()
        self.assertTrue((self.root / 'logging/journal.jsonl').read_bytes().startswith(prefix))
        records = json.loads(self.run_cli('journal', '--all').stdout)['entries']
        self.assertEqual(records[0]['id'], first)
        milestones = [record for record in records if record['type'] == 'milestone']
        self.assertEqual(len(milestones), 3)  # Configure, add, done.
        self.assertEqual([record['task'] for record in milestones], [None, 'T001', 'T001'])
        task_records = json.loads(self.run_cli('journal', '--task', 'T001').stdout)['entries']
        self.assertEqual(len(task_records), 2)

    def test_decisions_do_not_invalidate_validation_and_unknown_tasks_rejected(self):
        self.prepare_testing(); self.run_cli('test', 'T001')
        self.decision_payload()
        self.run_cli('decide', '--task', 'T999', '--file', 'decision.json', success=False)
        self.run_cli('decide', '--task', 'T001', '--file', 'decision.json')
        self.run_cli('memory', 'T001', '--file', 'memory.md')
        self.handoff('coordinator'); self.run_cli('done', 'T001'); self.run_cli('check')
        self.assertEqual(self.task()['status'], 'done')

    def test_config_update_adds_one_milestone_only_after_apply(self):
        self.configure()
        self.config['context']['max_chars'] = 9000
        self.put('candidate.json', self.config)
        before = (self.root / 'logging/journal.jsonl').read_bytes()
        preview = json.loads(self.run_cli('update-config', '--config', 'candidate.json').stdout)
        self.assertEqual(before, (self.root / 'logging/journal.jsonl').read_bytes())
        self.run_cli('update-config', '--config', 'candidate.json', '--approved', '--preview-hash', preview['preview_hash'])
        records = json.loads(self.run_cli('journal', '--type', 'milestone', '--all', '--full').stdout)['entries']
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1]['decision'], 'Configuration update applied')
        self.assertIn('config-revisions', records[-1]['evidence'][0])


    def test_journal_cli_defaults_compact_and_full_is_explicit(self):
        self.decision_payload('Long original decision ' + 'details ' * 100)
        self.run_cli('decide', '--file', 'decision.json')
        output = self.run_cli('journal', '--max-chars', '1500').stdout
        self.assertLessEqual(len(output), 1500)
        result = json.loads(output)
        self.assertEqual(result['mode'], 'compact')
        self.assertIn('decision', result['entries'][0]['truncated_fields'])
        full = json.loads(self.run_cli('journal', '--id', result['entries'][0]['id'], '--full').stdout)
        self.assertEqual(full['mode'], 'full')
        self.assertIn('evidence', full['entries'][0])
        self.assertGreater(len(full['entries'][0]['decision']), 160)


if __name__ == '__main__':
    unittest.main()
