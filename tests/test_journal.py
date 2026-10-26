"""Behavioral contracts for immutable journal history and focused retrieval."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import decision_journal as journal


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'evidence.md').write_text('Internal implementation evidence\n')

    def append(self, **overrides):
        args = dict(kind='decision', task=None, decision='Use local processing',
                    rationale='The work is deterministic.', alternatives=['Model processing rejected: unnecessary calls'],
                    outcome='Python selected.', status='accepted', evidence=['evidence.md'])
        args.update(overrides)
        return journal.append(self.root, **args)['id']

    def test_superseding_preserves_original_bytes_and_displays_current_status(self):
        first = self.append(task='T001')
        path = self.root / 'logging/journal.jsonl'
        prefix = path.read_bytes()
        second = self.append(task='T002', decision='Use a revised Python processor', supersedes=first)
        self.assertTrue(path.read_bytes().startswith(prefix))
        query = journal.query(self.root, task='T001')
        self.assertEqual(query['entries'][0]['superseded_by'], second)
        self.assertIn(f'superseded by {second}', (self.root / 'logging/journal.md').read_text())
        self.assertEqual(journal.query(self.root, entry_id=second)['entries'][0]['supersedes'], first)

    def test_limits_types_and_project_filters(self):
        for n in range(23):
            self.append(decision=f'Important decision {n}')
        self.append(kind='milestone', task='T001', status='recorded', decision='Task created')
        result = journal.query(self.root, max_chars=20000)
        self.assertEqual(len(result['entries']), 20)
        self.assertEqual(result['omitted'], 4)
        self.assertEqual(len(journal.query(self.root, task='project', kind='decision', limit=None, max_chars=20000)['entries']), 23)
        self.assertEqual(len(journal.query(self.root, task='T001')['entries']), 1)

    def test_bad_evidence_and_supersession_do_not_modify_history(self):
        first = self.append()
        original = (self.root / 'logging/journal.jsonl').read_bytes()
        for overrides in ({'evidence':['../outside.md']}, {'evidence':['missing.md']},
                          {'supersedes':'J999999'}, {'supersedes':''},
                          {'supersedes':first, 'status':'proposed'}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.append(**overrides)
            self.assertEqual(original, (self.root / 'logging/journal.jsonl').read_bytes())
        self.append(supersedes=first)
        with self.assertRaises(ValueError):
            self.append(supersedes=first)

    def test_read_does_not_create_files_and_corruption_blocks_append(self):
        self.assertEqual(journal.query(self.root)['entries'], [])
        self.assertFalse((self.root / 'logging').exists())
        self.append()
        path = self.root / 'logging/journal.jsonl'
        path.write_text(path.read_text().rstrip('\n'))
        broken = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.append()
        self.assertEqual(path.read_bytes(), broken)

    def test_render_repairs_view_without_rewriting_canonical(self):
        self.append()
        path = self.root / 'logging/journal.jsonl'
        original = path.read_bytes()
        view = self.root / 'logging/journal.md'
        view.unlink()
        journal.render(self.root)
        self.assertIn('Use local processing', view.read_text())
        self.assertEqual(original, path.read_bytes())


    def test_compact_queries_bound_characters_without_storing_summaries(self):
        for index in range(12):
            self.append(decision=f'Decision {index}: ' + 'detail ' * 100,
                        rationale='reason ' * 100, outcome='result ' * 100)
        canonical = self.root / 'logging/journal.jsonl'
        view = self.root / 'logging/journal.md'
        before = (canonical.read_bytes(), view.read_bytes())
        result = journal.query(self.root, limit=None, max_chars=1600)
        self.assertLessEqual(len(json.dumps(result, ensure_ascii=False, indent=2)) + 1, 1600)
        self.assertEqual(result['mode'], 'compact')
        self.assertEqual(result['matching'], 12)
        self.assertGreater(result['omitted'], 0)
        self.assertTrue(result['entries'])
        self.assertIn('decision', result['entries'][-1]['truncated_fields'])
        self.assertNotIn('alternatives', result['entries'][-1])
        self.assertIn('alternatives', result['excluded_fields'])
        self.assertEqual(before, (canonical.read_bytes(), view.read_bytes()))

    def test_full_query_preserves_complete_text_or_omits_whole_record(self):
        original = 'Complete original text\n' + 'long text ' * 1000
        entry_id = self.append(decision=original)
        compact = journal.query(self.root, entry_id=entry_id)
        self.assertIn('decision', compact['entries'][0]['truncated_fields'])
        full = journal.query(self.root, entry_id=entry_id, full=True, max_chars=20000)
        self.assertEqual(full['entries'][0]['decision'], original)
        self.assertIn('evidence', full['entries'][0])
        small = journal.query(self.root, entry_id=entry_id, full=True, max_chars=1000)
        self.assertEqual(small['entries'], [])
        self.assertEqual(small['omitted'], 1)
        for invalid in (0, 999, True):
            with self.assertRaises(ValueError):
                journal.query(self.root, max_chars=invalid)

    def test_render_failure_returns_saved_id_and_recovery_without_duplicate(self):
        arguments = dict(kind='decision', task=None, decision='Keep one canonical record',
                         rationale='View is rebuildable', alternatives=[], outcome='Saved',
                         status='accepted', evidence=['evidence.md'])
        with patch.object(journal, 'render', side_effect=OSError('simulated failure')):
            result = journal.append(self.root, **arguments)
        self.assertTrue(result['record_saved'])
        self.assertFalse(result['view_rendered'])
        self.assertEqual(result['id'], 'J000001')
        self.assertIn('do not repeat', result['recovery'])
        before = (self.root / 'logging/journal.jsonl').read_bytes()
        journal.render(self.root)
        self.assertEqual(len(journal.load(self.root)), 1)
        self.assertEqual(before, (self.root / 'logging/journal.jsonl').read_bytes())

    def test_real_append_failure_does_not_report_a_saved_record(self):
        original_open = Path.open
        def fail_canonical(path, *args, **kwargs):
            if path.name == 'journal.jsonl' and args and args[0] == 'a':
                raise OSError('simulated storage failure')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_canonical), self.assertRaises(OSError):
            self.append()
        self.assertEqual(journal.load(self.root), [])

    def test_markdown_is_escaped_but_canonical_text_and_links_are_preserved(self):
        title = '# [unsafe](javascript:alert(1))\n## Forged entry\n<script>alert(1)</script>'
        rationale = '**bold**\n> quoted & raw'
        ref = 'evidence [1] #notes.md'
        (self.root / ref).write_text('Internal evidence')
        self.append(decision=title, rationale=rationale, alternatives=['![image](x)'], evidence=[ref])
        original = journal.load(self.root)[0]
        self.assertEqual(original['decision'], title)
        self.assertEqual(original['rationale'], rationale)
        rendered = (self.root / 'logging/journal.md').read_text()
        self.assertEqual(sum(line.startswith('## ') for line in rendered.splitlines()), 1)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('![image]', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('../evidence%20%5B1%5D%20%23notes.md', rendered)

    def test_cli_saved_record_is_success_even_when_view_rendering_fails(self):
        import workflow
        payload = dict(decision='Keep one canonical record', rationale='View can be repaired',
                       alternatives=[], outcome='Saved', status='accepted', evidence=['evidence.md'])
        input_file = self.root / 'decision.json'
        input_file.write_text(json.dumps(payload))
        output, error = io.StringIO(), io.StringIO()
        with patch.object(workflow, 'ROOT', self.root), patch.object(sys, 'argv',
                ['workflow.py', 'decide', '--file', str(input_file)]), \
                patch.object(journal, 'render', side_effect=OSError('simulated view failure')), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = workflow.main()
        self.assertIn(result, (0, None))
        self.assertEqual(output.getvalue().strip(), 'J000001')
        self.assertIn('J000001 saved', error.getvalue())
        self.assertIn('Do not repeat', error.getvalue())
        self.assertEqual(len(journal.load(self.root)), 1)


if __name__ == '__main__':
    unittest.main()
