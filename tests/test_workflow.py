"""Core workflow behavior in isolated template copies; no provider calls."""
import json
import subprocess
import sys
import unittest

from harness import HarnessTestCase


class WorkflowTests(HarnessTestCase):
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
        self.assertIn('agents/tester.md', logged)

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
        import harness
        names = harness.harness_files(self.root)
        self.assertFalse([n for n in names if n.startswith(('data/raw/private', '.venv', '.workflow'))])

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


    def test_messages_name_the_fix(self):
        self.config['validation']['commands'] = ['python3 -m unittest']
        self.put('config.json', self.config)
        result = self.run_cli('validate-config', '--config', 'config.json', success=False)
        self.assertIn('[["python3", "-m", "unittest"', result.stderr)
        self.config['validation']['commands'] = [[sys.executable, '-c', 'pass']]
        self.put('config.json', self.config)
        self.configure(); self.add(); self.run_cli('start', 'T001')
        result = self.run_cli('start', 'T001', success=False)
        self.assertIn('T001 is already building', result.stderr)
        self.put('handoff.json', dict(json.loads((self.root / 'handoff.json').read_text()), memories=['T001 memory']))
        result = self.run_cli('handoff', 'T001', '--to', 'reviewer', '--file', 'handoff.json', success=False)
        self.assertIn('existing project-relative file paths', result.stderr)

    def test_assumed_defaults_are_journaled_at_configure(self):
        self.put('assumed.md', '- users: data managers\n- add-on: enabled\n')
        self.run_cli('configure', '--config', 'config.json', '--approved', '--assumed', 'assumed.md')
        entry = json.loads((self.root / 'logging/journal.jsonl').read_text().splitlines()[0])
        self.assertIn('Assumed defaults: - users: data managers - add-on: enabled', entry['outcome'])


if __name__ == '__main__':
    unittest.main()
