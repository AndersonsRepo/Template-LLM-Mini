#!/usr/bin/env python3
"""Standard-library workflow controller; one coordinator owns all writes."""
import argparse
import difflib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import data_analysis
import profiling
import decision_journal

ROOT = Path(__file__).resolve().parents[1]
VERSION = 3
FIELDS = ('objective', 'files', 'memories', 'decisions', 'changes', 'validation',
          'unresolved', 'next_action')
KINDS = ('prompts', 'handoffs', 'reviews', 'tests', 'memories', 'checkpoints', 'inspections', 'analyses', 'profiles')
# Never hash datasets, workflow records, environments, or generated caches.
EXCLUDED = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', 'node_modules'}
ROOT_EXCLUDED = {'data', '.workflow', 'handoffs', 'memories', 'logging', 'dist', 'build'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encoded(value):
    return json.dumps(value, indent=2, ensure_ascii=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def dump(path, value):
    write(path, encoded(value) + '\n')


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(x) for x in value)


def local(ref):
    require(text(ref), 'Expected a project-relative path')
    path = Path(ref)
    require(not path.is_absolute() and '..' not in path.parts, 'Paths must stay inside the project')
    current = ROOT
    for part in path.parts:
        current /= part
        require(not current.is_symlink(), f'Symlinks are not supported: {ref}')
    require(current.resolve().is_relative_to(ROOT.resolve()), 'Path escapes project')
    return current


def source_allowed(ref):
    parts = Path(ref).parts
    return (not any(p in EXCLUDED for p in parts)
            and (not parts or parts[0] not in ROOT_EXCLUDED)
            and not (len(parts) >= 2 and parts[:2] == ('prompts', 'logs'))
            and Path(ref).name not in {'tasks.md', 'project-config.json'}
            and not any(p == '.env' or p.startswith('.env.') for p in parts)
            and Path(ref).suffix not in {'.pyc', '.tmp'})


def validate_config(c):
    template = read(ROOT / 'templates/config.json')

    def structure(actual, expected, location='config'):
        if isinstance(expected, dict):
            require(isinstance(actual, dict) and set(actual) == set(expected), f'{location}: keys differ from template')
            for key, value in expected.items():
                structure(actual[key], value, location + '.' + key)
        elif isinstance(expected, str):
            require(text(actual), f'{location}: provide a nonempty string; use none explicitly')
        elif type(expected) is bool:
            require(type(actual) is bool, f'{location}: expected boolean')
        elif type(expected) is int:
            require(type(actual) is int, f'{location}: expected integer')
        elif isinstance(expected, list):
            require(isinstance(actual, list) and (actual or location in ('config.analysis.datasets', 'config.data.provenance')), f'{location}: expected nonempty list')
    structure(c, template)
    require(c['config_version'] == 1, 'Unsupported configuration version')
    data_analysis.validate_settings(c['analysis'], ROOT)
    profile_settings = c['analysis']['profiling']
    require(1 <= profile_settings['max_columns'] <= 1000 and 500 <= profile_settings['max_chars'] <= 100000, 'Invalid profiling limits')
    require(not profile_settings['enabled'] or c['analysis']['data_access'] == 'approved-summaries', 'Profiling requires approved-summaries access')
    data_analysis.validate_provenance(ROOT, c['data']['provenance'])
    require(strings(c['project']['acceptance_criteria']), 'Acceptance criteria must be strings')
    require(c['roles'] == ['builder', 'reviewer', 'tester'], 'Required roles: builder, reviewer, tester')
    require(c['delegation']['review_mode'] in ('independent', 'approved-same-agent'), 'Unsupported review mode')
    require(c['delegation']['max_concurrency'] >= 1 and c['handoffs']['max_repairs'] >= 0, 'Invalid concurrency/repair limit')
    for key in ('raw_policy', 'git_policy'):
        require(c['data'][key] == template['data'][key], 'Preserve required data policies')
    v = c['validation']
    require(all(strings(command) and command for command in v['commands']), 'Commands must be nonempty argument arrays')
    require(1 <= v['timeout_seconds'] <= 3600, 'Timeout must be 1..3600 seconds')
    require(v['diagnostics'] in ('off', 'summary'), 'Diagnostics must be off or summary')
    require(1 <= v['summary_max_chars'] <= 10000, 'Summary limit must be 1..10000 characters')
    require(strings(v['source_paths']), 'Source paths must be strings')
    for ref in v['source_paths']:
        local(ref)
        require(source_allowed(ref), f'Cannot fingerprint generated/data/environment path: {ref}')
    require(2000 <= c['context']['max_chars'] <= 100000, 'Context limit must be 2000..100000 characters')


def body(path):
    value = Path(path).read_text(encoding='utf-8').strip()
    require(value, 'Artifact cannot be empty')
    return value + '\n'


def artifact(task, kind, content, suffix='json'):
    folder = {'prompts': 'prompts/logs', 'memories': 'memories/features'}.get(kind, 'handoffs')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    ref = f'{folder}/{task["id"]}-{kind}-{stamp}.{suffix}'
    path = local(ref)
    write(path, content)
    task.setdefault(kind, []).append(ref)
    task['artifacts'][ref] = digest(path.read_bytes())
    return ref


def evidence(task, kind):
    require(task[kind], f'Missing {kind} evidence')
    return read(local(task[kind][-1]))



def inspect_phase(task, config, phase):
    current = data_analysis.scan(ROOT, config, task, phase)
    entry = task['analysis_state'].get(phase, {})
    if task['data_mode'] == 'none' or not entry.get('inspection'):
        return current
    old = read(local(entry['inspection']))['inspection']
    old_refs = {item['path'] for item in old['files']}
    now_refs = {item['path'] for item in current['files']}
    vanished = sorted(old_refs - now_refs)
    if vanished:
        current.pop('hash', None)
        current['status'] = 'needs-input'
        current['reason'] = ''
        current['issues'].append('Previously inspected data disappeared: ' + ', '.join(vanished))
        current['files'].extend({'path': ref, 'status': 'missing previously used data'} for ref in vanished)
        current['question'] = ('Previously used data is missing: ' + ', '.join(vanished)
                               + '. Please restore it or explicitly approve a data-scope change. How should dependent work proceed?')
        return data_analysis.seal(current)
    return current


def analysis_stale(task, config):
    if task['status'] == 'done':
        return False
    return any(entry.get('inspection') and entry.get('data_hash') != inspect_phase(task, config, phase)['hash']
               for phase, entry in task['analysis_state'].items())


def fingerprint(config, task):
    files = set()
    for ref in config['validation']['source_paths'] + task['source_files']:
        path = local(ref)
        require(path.exists(), f'Fingerprint path missing: {ref}')
        candidates = [path]
        if path.is_dir():
            candidates = []
            for directory, dirs, names in os.walk(path, followlinks=False):
                dirs[:] = [name for name in dirs if source_allowed(
                    (Path(directory) / name).relative_to(ROOT).as_posix())]
                for name in dirs:
                    local((Path(directory) / name).relative_to(ROOT).as_posix())
                candidates.extend(Path(directory) / name for name in names)
        for candidate in candidates:
            name = candidate.relative_to(ROOT).as_posix()
            if not source_allowed(name):
                continue
            candidate = local(name)
            if candidate.is_file():
                files.add(name)
    require(files, 'No source files selected for validation')
    hashes = {ref: digest(local(ref).read_bytes()) for ref in sorted(files)}
    snapshot = {'files': hashes, 'config': config, 'criteria': task['criteria'],
                'data': {phase: inspect_phase(task, config, phase)['hash']
                         for phase in task['analysis_phases']} if task['data_mode'] != 'none' else {}}
    return {'hash': digest(json.dumps(snapshot, sort_keys=True).encode()), 'files': hashes, 'data': snapshot['data']}


def invalidate(task, config, repair=False):
    task['cycle'] += 1
    task['repairs'] += int(repair)
    task['review_pass'] = task['test_pass'] = False
    task['snapshot'] = None
    task.pop('previous_status', None)
    task['status'] = 'blocked' if task['repairs'] > config['handoffs']['max_repairs'] else 'building'


def fresh(task, config):
    try:
        return task['snapshot'] is not None and fingerprint(config, task) == task['snapshot']
    except (ValueError, OSError):
        return False


def ensure_fresh(task, config, state):
    if not fresh(task, config):
        invalidate(task, config)
        save(state)
        raise ValueError('Source/configuration changed; passes invalidated. Build and obtain a fresh review.')


def validate_task(task, config, complete=False, live=False):
    for kind in KINDS:
        for ref in task.get(kind, []):
            path = local(ref)
            require(path.is_file() and path.stat().st_size, f'Missing artifact: {ref}')
            require(digest(path.read_bytes()) == task['artifacts'].get(ref), f'Artifact changed: {ref}')
    require(task['prompts'], 'Missing major prompt')
    if complete:
        for phase in task['analysis_phases']:
            entry = task['analysis_state'].get(phase, {})
            require(entry.get('status') in ('pass', 'skipped'), f'{phase} analysis is incomplete')
            if task['data_mode'] != 'none':
                require(entry['data_hash'] == task['snapshot']['data'][phase], 'Analysis selection changed')
            if entry['status'] == 'pass':
                report = read(local(entry['report']))
                require(report['verdict'] == 'pass' and report['data_hash'] == entry['data_hash'], 'Stale analysis report')
        require(task['review_pass'] and task['test_pass'] and task['snapshot'], 'Passing review/tests required')
        for kind in ('reviews', 'tests', 'memories', 'handoffs'):
            item = evidence(task, kind)
            require(item.get('task') == task['id'] and item.get('cycle') == task['cycle']
                    and item.get('snapshot') == task['snapshot']['hash'], f'Stale {kind} evidence')
        require(evidence(task, 'reviews')['verdict'] == 'pass', 'Review rejected')
        results = evidence(task, 'tests')['results']
        require(results and all(r['exit_code'] == 0 for r in results), 'Checks failed')
        require(evidence(task, 'tests')['sources_unchanged'], 'Checks changed their source inputs')
        require(evidence(task, 'handoffs')['target'] == 'coordinator', 'Final tester handoff required')
        if live:
            require(fresh(task, config), 'Evidence no longer matches working files')


def save(state):
    dump(ROOT / '.workflow/state.json', state)
    lines = ['# Tasks', '', 'Generated; use workflow.py show/context for focused reads.', '']
    for task in state['tasks']:
        lines += [f'## {task["id"]}: {task["title"]}', '',
                  f'Status: {task["status"]} | Repairs: {task["repairs"]}', '',
                  *[f'- {criterion}' for criterion in task['criteria']], '',
                  'Dependencies: ' + (', '.join(task['dependencies']) or 'none'), '',
                  'Analysis: ' + encoded({phase: entry['status'] for phase, entry in task['analysis_state'].items()}), '',
                  'Data question: ' + (task.get('data_question') or 'none'), '']
        for kind in KINDS:
            lines += [kind.title() + ': ' + (', '.join(f'[{Path(p).name}]({p})' for p in task.get(kind, [])) or 'none'), '']
    write(ROOT / 'tasks.md', '\n'.join(lines))
    base = ROOT / 'memories/template-index.md'
    entries = ['# Feature memories', '', 'Load only relevant entries.', '',
               base.read_text(encoding='utf-8') if base.exists() else '', '\n## Project features\n']
    for task in state['tasks']:
        for ref in task['memories']:
            entries.append(f'- {task["id"]} {task["title"]}: [{Path(ref).name}](../{ref})')
    write(ROOT / 'memories/index.md', '\n'.join(entries) + '\n')


def envelope(task, **values):
    return dict(task=task['id'], cycle=task['cycle'], snapshot=task['snapshot']['hash'] if task['snapshot'] else None, **values)


def handoff_input(path):
    h = read(path)
    require(isinstance(h, dict) and set(h) == set(FIELDS), 'Use templates/handoff.json fields')
    for key in FIELDS:
        require(strings(h[key]) if key in ('files', 'memories') else text(h[key]), f'Invalid handoff field: {key}')
    for ref in h['files'] + h['memories']:
        require(local(ref).is_file(), f'Handoff reference missing: {ref}')
    return h


def assignment(task, target, ref):
    instruction = (f'Read AGENTS.md and prompts/roles/{target}.md; read handoff {ref}; '
                   'return results to the coordinator without writing workflow state.'
                   if target != 'coordinator' else
                   f'Read AGENTS.md and final handoff {ref}; verify evidence and close the task.')
    artifact(task, 'prompts', instruction + '\n', 'md')



def analysis_gate(task, config, state, phase):
    require(phase in task['analysis_phases'], 'Phase is not selected for this task')
    inspection = inspect_phase(task, config, phase)
    previous = task['analysis_state'].get(phase, {})
    if previous.get('status') in ('pass', 'skipped') and previous.get('data_hash') == inspection['hash']:
        return True
    pending = task.get('analysis_pending')
    require(not pending or pending['phase'] == phase, 'Resolve the pending analysis phase first')
    resume = pending['resume_status'] if pending else task['status']
    if task['snapshot'] and previous.get('data_hash') != inspection['hash']:
        invalidate(task, config)
        resume = 'building'
    if inspection['status'] == 'skipped':
        task['analysis_state'][phase] = dict(status='skipped', data_hash=inspection['hash'], reason=inspection['reason'])
        if pending:
            task['status'] = resume
            task['analysis_pending'] = None
            task['data_question'] = None
            if resume == 'building':
                assignment(task, 'builder', task['prompts'][0])
        save(state)
        return True
    if previous.get('response_required') and previous.get('data_hash') == inspection['hash']:
        task['status'] = 'awaiting-data'
        print('User question: ' + task['data_question'])
        save(state)
        return False
    if pending and previous.get('status') == 'pending' and previous.get('data_hash') == inspection['hash']:
        print('Analyzer assignment is already pending; read its current context.')
        return False
    ref = artifact(task, 'inspections', encoded(envelope(task, inspection=inspection)) + '\n')
    task['analysis_pending'] = dict(phase=phase, resume_status=resume)
    task['analysis_state'][phase] = dict(status='pending', inspection=ref, data_hash=inspection['hash'])
    task['data_question'] = inspection['question']
    if inspection['status'] == 'needs-input':
        task['status'] = 'awaiting-data'
        task['analysis_state'][phase]['status'] = 'needs-input'
        print('User question: ' + inspection['question'])
    else:
        task['status'] = 'analyzing'
        assignment(task, 'analyzer', ref)
        print(f'{phase} analysis required; give the analyzer its focused context and record analysis-report.')
    save(state)
    return False


def analysis_report(task, config, state, args):
    require(task['status'] == 'analyzing' and task['analysis_pending']['phase'] == args.phase,
            'A matching analyzer assignment is required')
    previous = task['analysis_state'][args.phase]
    current = inspect_phase(task, config, args.phase)
    if current['hash'] != previous['data_hash']:
        analysis_gate(task, config, state, args.phase)
        raise ValueError('Data changed during analysis; use the new inspection')
    require(current['status'] == 'ready', 'Data must pass deterministic inspection first')
    report = body(args.file)
    require(args.verdict == 'pass' or text(args.question), 'Explain the discrepancy as a user question')
    ref = artifact(task, 'analyses', encoded(envelope(task, phase=args.phase, data_hash=current['hash'],
                   verdict=args.verdict, report=report, question=args.question)) + '\n')
    previous.update(report=ref, status='pass' if args.verdict == 'pass' else 'needs-input')
    if args.verdict != 'pass':
        task['status'] = 'awaiting-data'
        task['data_question'] = args.question
        previous['response_required'] = True
        print('User question: ' + args.question)
    else:
        resume = task['analysis_pending']['resume_status']
        task['status'] = resume
        task['analysis_pending'] = None
        task['data_question'] = None
        if resume == 'building':
            assignment(task, 'builder', ref)


def run_checks(config):
    v = config['validation']
    results = []
    for command in v['commands']:
        result = {'command': command}
        # Off mode never captures output. Summary mode trusts an approved wrapper,
        # and accepts only its explicit JSON summary, never raw stderr.
        with tempfile.TemporaryFile() as output:
            try:
                completed = subprocess.run(command, cwd=ROOT, timeout=v['timeout_seconds'],
                                           stdout=output if v['diagnostics'] == 'summary' else subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                result['exit_code'] = completed.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                result.update(exit_code=-1, error_type=type(exc).__name__)
            if v['diagnostics'] == 'summary':
                output.seek(0)
                raw = output.read(65537)
                try:
                    require(len(raw) <= 65536, 'Summary too large')
                    summary = json.loads(raw)['summary']
                    require(text(summary), 'Missing summary')
                    result['summary'] = summary[:v['summary_max_chars']]
                    result['summary_truncated'] = len(summary) > v['summary_max_chars']
                except (ValueError, KeyError, TypeError, UnicodeError):
                    result['diagnostic_error'] = 'Wrapper must emit a bounded JSON object with a summary string'
                    if result['exit_code'] == 0:
                        result['exit_code'] = -1
        results.append(result)
    return results


def task_view(task):
    return {key: task[key] for key in ('id', 'title', 'status', 'criteria', 'dependencies', 'cycle', 'repairs')} | {
        'data_mode': task['data_mode'], 'analysis': {phase: entry['status'] for phase, entry in task['analysis_state'].items()},
        'pending_question': task.get('data_question'),
        'latest': {kind: task[kind][-1] if task.get(kind) else None for kind in KINDS}}


def context(task, config, role, limit):
    validate_task(task, config)
    packet = task_view(task) | {'role': role, 'omitted': [], 'rules': 'AGENTS.md',
                              'validation_stale': bool(task['snapshot']) and task['status'] != 'done' and not fresh(task, config)}
    packet['analysis_stale'] = analysis_stale(task, config)
    pending = task.get('analysis_pending')
    packet['active_analysis'] = pending
    packet['selected_datasets'] = task['datasets']
    packet['role_instruction_ref'] = f'prompts/roles/{role}.md' if role != 'coordinator' else 'AGENTS.md'
    candidates = []
    order = ('inspections', 'analyses', 'handoffs', 'checkpoints', 'reviews', 'tests') if role == 'analyzer' else ('handoffs', 'reviews', 'tests', 'inspections', 'analyses', 'checkpoints')
    for kind in order:
        if task.get(kind):
            item = evidence(task, kind)
            if kind == 'checkpoints':
                item = {key: value for key, value in item.items() if key != 'working_snapshot'}
            candidates.append((kind, item))
    if role != 'coordinator':
        candidates.append(('role_instruction', (ROOT / f'prompts/roles/{role}.md').read_text(encoding='utf-8')))
    if role == 'analyzer' and config['analysis']['profiling']['enabled'] and config['analysis']['data_access'] == 'approved-summaries' and task.get('profiles'):
        summary = evidence(task, 'profiles')
        if summary['summary']['data_hash'] == inspect_phase(task, config, summary['phase'])['hash']:
            candidates.insert(2, ('profile', summary))
    candidates += [('analysis_evidence', task['analysis_state']), ('technology', config['technology']),
                   ('approvals', config['approvals']), ('delegation', config['delegation']), ('validation', config['validation'])]
    if role == 'analyzer':
        candidates.insert(1, ('analysis_policy', {'data_access': config['analysis']['data_access']}))
    if task['checkpoints']:
        checkpoint = evidence(task, 'checkpoints')
        try:
            changed = checkpoint['working_snapshot'] != fingerprint(
                config, task | {'source_files': checkpoint['source_files']})
        except (ValueError, OSError):
            changed = True
        packet['checkpoint_stale'] = (checkpoint['cycle'] != task['cycle']
                                      or checkpoint['status'] != task['status'] or changed)
    for key, value in candidates:
        packet[key] = value
    # Remove entire optional sections, never silently truncate criteria or evidence.
    while len(encoded(packet)) > limit and candidates:
        key, _ = candidates.pop()
        del packet[key]
        packet['omitted'].append(key)
    require(len(encoded(packet)) <= limit, 'Core task exceeds context limit; use show or explicitly increase --max-chars')
    print(encoded(packet))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('configure'); c.add_argument('--config', required=True); c.add_argument('--approved', action='store_true')
    c = sub.add_parser('add'); c.add_argument('--title', required=True); c.add_argument('--criterion', action='append', required=True); c.add_argument('--depends', action='append', default=[]); c.add_argument('--prompt', required=True)
    c.add_argument('--data', choices=['auto', 'expected', 'none'], default='auto')
    c.add_argument('--data-reason', default='')
    c.add_argument('--dataset', action='append', default=[])
    c.add_argument('--analysis-phase', choices=['pre', 'post'], action='append')
    for name in ('start', 'handoff', 'review', 'test', 'memory', 'done', 'block', 'unblock', 'log', 'checkpoint', 'rebuild', 'show', 'context', 'resume', 'data-check', 'analysis-report', 'data-resolve', 'profile'):
        c = sub.add_parser(name); c.add_argument('task')
        if name in ('handoff', 'review', 'memory', 'log', 'block', 'checkpoint', 'rebuild', 'analysis-report', 'data-resolve'):
            c.add_argument('--file', required=True)
        if name in ('data-check', 'analysis-report', 'profile'):
            c.add_argument('--phase', choices=['pre', 'post'], required=True)
        if name == 'analysis-report':
            c.add_argument('--verdict', choices=['pass', 'needs-input'], required=True)
            c.add_argument('--question')
        if name == 'data-resolve':
            c.add_argument('--approved', action='store_true')
            c.add_argument('--data', choices=['auto', 'expected', 'none'])
        if name == 'review':
            c.add_argument('--verdict', choices=['pass', 'fail'], required=True)
        if name == 'handoff':
            c.add_argument('--to', choices=['reviewer', 'tester', 'coordinator'], required=True)
        if name in ('context', 'resume'):
            c.add_argument('--role', choices=['builder', 'reviewer', 'tester', 'coordinator', 'analyzer'], default='coordinator')
            c.add_argument('--max-chars', type=int)
    c = sub.add_parser('decide'); c.add_argument('--file', required=True); c.add_argument('--task'); c.add_argument('--supersedes')
    c = sub.add_parser('journal'); c.add_argument('--task'); c.add_argument('--type', choices=['decision', 'milestone']); c.add_argument('--id'); c.add_argument('--limit', type=int, default=20); c.add_argument('--all', action='store_true'); c.add_argument('--render', action='store_true'); c.add_argument('--full', action='store_true'); c.add_argument('--max-chars', type=int, default=6000)
    sub.add_parser('check')
    sub.add_parser('validate-config').add_argument('--config', required=True)
    c = sub.add_parser('update-config'); c.add_argument('--config', required=True); c.add_argument('--approved', action='store_true'); c.add_argument('--preview-hash')
    sub.add_parser('status').add_argument('--all', action='store_true')
    return p




def report_journal_result(result):
    if not result['view_rendered']:
        print(f"Journal record {result['id']} saved; Markdown view failed ({result['view_error']}). "
              'Do not repeat the append. Run workflow.py journal --render to rebuild the view.', file=sys.stderr)
    return result['id']


def milestone(decision, *, rationale, outcome, evidence, task=None):
    return report_journal_result(decision_journal.append(ROOT, kind='milestone', task=task, decision=decision,
                                   rationale=rationale, alternatives=[], outcome=outcome,
                                   status='recorded', evidence=evidence))


def config_changes(old, new, path=''):
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            result.extend(config_changes(old.get(key), new.get(key), path + '.' + key if path else key))
        return result
    return [] if old == new else [{'path': path, 'before': old, 'after': new}]


def update_config(args):
    candidate = read(args.config)
    validate_config(candidate)
    current = read(ROOT / '.workflow/config.json')
    state = read(ROOT / '.workflow/state.json')
    require(state.get('schema_version') == VERSION, 'State migration required before updating configuration')
    rules = (ROOT / 'templates/agent_rules.md').read_text(encoding='utf-8')
    changes = config_changes(current, candidate)
    previous_guidance = {name: (ROOT / name).read_text(encoding='utf-8') for name in ('AGENTS.md', 'PROJECT.md')}
    new_guidance = {'AGENTS.md': '# Project agent instructions\n\n' + rules,
                    'PROJECT.md': '# Project brief\n\n' + '\n'.join(f'**{key}**: {value}\n' for key, value in candidate['project'].items())}
    guidance_changes = {name: ''.join(difflib.unified_diff(previous_guidance[name].splitlines(True),
                        new_guidance[name].splitlines(True), fromfile=name, tofile=name))
                        for name in previous_guidance if previous_guidance[name] != new_guidance[name]}
    preview_hash = digest(json.dumps({'current': current, 'state': state, 'candidate': candidate,
                                     'rules': rules, 'previous_guidance': previous_guidance}, sort_keys=True).encode())
    affected = [task['id'] for task in state['tasks'] if task['status'] != 'done'] if changes or guidance_changes else []
    conflicts = []
    for task in state['tasks']:
        if task['status'] != 'done':
            try:
                data_analysis.validate_selection(ROOT, candidate['analysis'], task['datasets'], task['analysis_phases'])
            except ValueError as exc:
                conflicts.append({'task': task['id'], 'issue': str(exc)})
    data_scope_changed = (current.get('analysis', {}).get('datasets') != candidate['analysis']['datasets'])
    preview = {'preview_hash': preview_hash, 'changes': changes, 'affected_tasks': affected,
               'guidance_changes': guidance_changes,
               'data_scope_changed': data_scope_changed,
               'conflicts': conflicts, 'action': 'Active evidence will be invalidated; completed history is preserved.'}
    if not args.approved:
        require(args.preview_hash is None, '--preview-hash is only used with --approved')
        print(encoded(preview))
        return 0
    require(args.preview_hash == preview_hash, 'Missing/stale preview hash; preview again and obtain approval')
    require(not conflicts, 'Resolve task selection/phase conflicts before applying this update')
    if not changes and not guidance_changes:
        print('Configuration unchanged; no writes made.')
        return 0
    decision_journal.load(ROOT)
    previous_state = json.loads(json.dumps(state))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    revision = ROOT / f'.workflow/config-revisions/{stamp}.json'
    dump(revision, {'status': 'prepared', 'preview': preview, 'previous_config': current,
                    'new_config': candidate, 'previous_state': previous_state,
                    'previous_guidance': previous_guidance, 'new_guidance': new_guidance})
    for task in state['tasks']:
        task.setdefault('profiles', [])
        if task['status'] == 'done':
            continue
        planned = task['status'] == 'planned'
        paused = task['status'] in ('analyzing', 'awaiting-data')
        previous_status = task['status']
        previous_pending = task.get('analysis_pending')
        previous_question = task.get('data_question')
        invalidate(task, candidate)
        task['status'] = 'planned' if planned else task['status']
        task['datasets'] = data_analysis.validate_selection(ROOT, candidate['analysis'], task['datasets'], task['analysis_phases'])
        if data_scope_changed:
            task['analysis_state'] = {}
        else:
            # Keep inspected file references so an unrelated config edit cannot
            # silently forget a disappeared dataset. Reports remain in history.
            for entry in task['analysis_state'].values():
                entry['status'] = 'unreviewed'
        task['analysis_pending'] = None
        task['data_question'] = None
        if not data_scope_changed and paused and previous_pending:
            task['status'] = previous_status
            task['analysis_pending'] = previous_pending | {'resume_status': 'building'}
            task['data_question'] = previous_question
        artifact(task, 'prompts', f'Approved configuration update {revision.relative_to(ROOT)}; reassess data and validation before continuing.\n', 'md')
    dump(ROOT / '.workflow/config.json', candidate)
    for name, content in new_guidance.items():
        write(ROOT / name, content)
    save(state)
    record = read(revision); record['status'] = 'applied'; dump(revision, record)
    milestone('Configuration update applied', rationale='Coordinator recorded approval of the matching configuration preview.',
              outcome='Active evidence reassessed; completed history preserved.', evidence=[revision.relative_to(ROOT).as_posix()])
    print(f'Configuration applied; revision preserved at {revision.relative_to(ROOT)}.')
    return 0


def main():
    args = parser().parse_args()
    cmd = args.command
    if cmd == 'journal':
        require(args.limit > 0, 'Journal limit must be positive')
        if args.render:
            decision_journal.render(ROOT)
        print(encoded(decision_journal.query(ROOT, task=args.task, kind=args.type, entry_id=args.id,
                                           limit=None if args.all else args.limit, full=args.full, max_chars=args.max_chars)))
        return
    if cmd == 'decide':
        payload = read(args.file)
        require(isinstance(payload, dict) and set(payload) == {'decision', 'rationale', 'alternatives', 'outcome', 'status', 'evidence'},
                'Use templates/decision.json fields')
        if args.task:
            state = read(ROOT / '.workflow/state.json')
            require(state.get('schema_version') == VERSION and any(t['id'] == args.task for t in state['tasks']), 'Unknown task')
        print(report_journal_result(decision_journal.append(ROOT, kind='decision', task=args.task, supersedes=args.supersedes, **payload)))
        return
    if cmd == 'validate-config':
        validate_config(read(args.config)); print('Configuration valid; no changes made.'); return
    if cmd == 'update-config':
        return update_config(args)
    if cmd == 'configure':
        require(args.approved, 'Explicit user approval required')
        decision_journal.load(ROOT)
        c = read(args.config); validate_config(c)
        require(not (ROOT / '.workflow/config.json').exists(), 'Already configured; review a migration before reconfiguration')
        rules = (ROOT / 'templates/agent_rules.md').read_text(encoding='utf-8')
        brief = '# Project brief\n\n' + '\n'.join(f'**{k}**: {v}\n' for k, v in c['project'].items())
        write(ROOT / 'PROJECT.md', brief)
        write(ROOT / 'AGENTS.md', '# Project agent instructions\n\n' + rules)
        dump(ROOT / '.workflow/config.json', c)
        save({'schema_version': VERSION, 'tasks': []})
        milestone('Initial configuration approved', rationale='Coordinator recorded explicit user approval via configure --approved.',
                  outcome='Project brief, instructions, and task state initialized.', evidence=['.workflow/config.json', 'PROJECT.md', 'AGENTS.md'])
        print('Configured. Read PROJECT.md and AGENTS.md.'); return
    config = read(ROOT / '.workflow/config.json'); validate_config(config)
    state = read(ROOT / '.workflow/state.json')
    require(state.get('schema_version') == VERSION, 'Old state schema; explicit migration required (do not overwrite history)')
    if cmd == 'status':
        print(encoded([task_view(t) for t in state['tasks'] if args.all or t['status'] != 'done'])); return
    if cmd == 'check':
        decision_journal.load(ROOT)
        for t in state['tasks']:
            validate_task(t, config, complete=t['status'] == 'done')
            require(not analysis_stale(t, config), f'{t["id"]}: analysis inspection is stale; run data-check')
            if t['snapshot'] and t['status'] in ('reviewing', 'testing'):
                require(fresh(t, config), f'{t["id"]}: validation stale; rebuild required')
        print('Workflow evidence valid; semantic correctness requires review.'); return
    if cmd == 'add':
        decision_journal.load(ROOT)
        require(text(args.title) and strings(args.criterion), 'Title/criteria must not be empty')
        require(set(args.depends) <= {t['id'] for t in state['tasks']}, 'Unknown dependency')
        require(args.data != 'none' or text(args.data_reason), 'Explain why this task does not involve data')
        phases = [phase for phase in ('pre', 'post') if phase in (args.analysis_phase or config['analysis']['phases'])]
        datasets = data_analysis.validate_selection(ROOT, config['analysis'], args.dataset, phases)
        require(args.data != 'none' or not datasets, 'A no-data task cannot select datasets')
        t = dict(id=f'T{len(state["tasks"]) + 1:03}', title=args.title, criteria=args.criterion,
                 dependencies=args.depends, status='planned', repairs=0, cycle=0, review_pass=False,
                 test_pass=False, snapshot=None, source_files=[], artifacts={}, data_mode=args.data,
                 data_reason=args.data_reason, datasets=datasets,
                 analysis_phases=phases,
                 analysis_state={}, analysis_pending=None, data_question=None, **{k: [] for k in KINDS})
        artifact(t, 'prompts', body(args.prompt), 'md'); state['tasks'].append(t)
        save(state)
        milestone('Task created: ' + t['title'], task=t['id'], rationale='A requested feature/task was registered with acceptance criteria.',
                  outcome='Task planned.', evidence=[t['prompts'][0]])
        print(t['id']); return
    matches = [t for t in state['tasks'] if t['id'] == args.task]
    require(matches, 'Unknown task'); t = matches[0]
    if cmd == 'show':
        print(encoded(task_view(t))); return
    if cmd in ('context', 'resume'):
        limit = config['context']['max_chars'] if args.max_chars is None else args.max_chars
        require(2000 <= limit <= 100000, 'Context limit must be 2000..100000 characters')
        context(t, config, args.role, limit); return
    require(t['status'] != 'done' or cmd == 'log', 'Completed tasks are immutable; create a follow-up')
    validate_task(t, config)
    decision_journal.load(ROOT)
    if cmd in ('review', 'test', 'memory', 'done') and t['status'] in ('reviewing', 'testing'):
        for phase in t['analysis_phases']:
            if not analysis_gate(t, config, state, phase):
                return 2
    if cmd in ('review', 'test', 'memory', 'done') or (cmd == 'handoff' and args.to != 'reviewer'):
        if t['snapshot']:
            ensure_fresh(t, config, state)
    if cmd == 'start':
        require(t['status'] == 'planned', 'Only planned tasks can start')
        require(all(x['status'] == 'done' for x in state['tasks'] if x['id'] in t['dependencies']), 'Dependencies incomplete')
        t['status'] = 'building'
        if 'pre' in t['analysis_phases'] and not analysis_gate(t, config, state, 'pre'):
            return 2
        assignment(t, 'builder', t['prompts'][0])
    elif cmd == 'handoff':
        h = handoff_input(args.file); target = args.to
        require((t['status'], target) in (('building', 'reviewer'), ('reviewing', 'tester'), ('testing', 'coordinator')), 'Invalid handoff stage')
        if target == 'reviewer':
            for phase in t['analysis_phases']:
                if not analysis_gate(t, config, state, phase):
                    return 2
            require(all(source_allowed(ref) for ref in h['files']), 'Use source files, not datasets/generated artifacts, in files')
            t['source_files'] = h['files']
            t['snapshot'] = fingerprint(config, t)
        else:
            require(t['review_pass'], 'Passing review required')
            require(all(ref in t['snapshot']['files'] for ref in h['files']), 'New source reference needs rebuild and review')
            require(target != 'coordinator' or t['test_pass'], 'Passing tests required')
        ref = artifact(t, 'handoffs', encoded(envelope(t, target=target, acceptance_criteria=t['criteria'],
                       analysis_evidence=t['analysis_state'], **h)) + '\n')
        assignment(t, target, ref)
        t['status'] = {'reviewer': 'reviewing', 'tester': 'testing', 'coordinator': 'testing'}[target]
    elif cmd == 'review':
        require(t['status'] == 'reviewing', 'Reviewer handoff required')
        artifact(t, 'reviews', encoded(envelope(t, verdict=args.verdict, report=body(args.file))) + '\n')
        t['review_pass'] = args.verdict == 'pass'
        if not t['review_pass']:
            invalidate(t, config, repair=True)
    elif cmd == 'test':
        require(t['status'] == 'testing' and t['review_pass'], 'Passing review and tester handoff required')
        results = run_checks(config)
        # A check that edits selected sources invalidates its own evidence.
        unchanged = fresh(t, config)
        artifact(t, 'tests', encoded(envelope(t, results=results, sources_unchanged=unchanged)) + '\n')
        t['test_pass'] = unchanged and all(x['exit_code'] == 0 for x in results)
        if not t['test_pass']:
            invalidate(t, config, repair=True)
        print('Checks passed' if t['test_pass'] else 'Checks failed; inspect test evidence')
    elif cmd == 'memory':
        require(t['status'] == 'testing' and t['test_pass'], 'Passing tests required')
        artifact(t, 'memories', encoded(envelope(t, report=body(args.file))) + '\n')
    elif cmd == 'done':
        require(t['status'] == 'testing', 'Task must be in testing')
        validate_task(t, config, complete=True, live=True)
        t['status'] = 'done'
    elif cmd == 'profile':
        require(t['status'] in ('building', 'analyzing', 'awaiting-data', 'reviewing', 'testing'), 'Start task before profiling')
        result = profiling.profile(ROOT, config, t, args.phase)
        require(result['data_hash'] == inspect_phase(t, config, args.phase)['hash'], 'Resolve data inspection before profiling')
        artifact(t, 'profiles', encoded(envelope(t, phase=args.phase, summary=result)) + '\n')
        print('Profile recorded; use analyzer context.')
    elif cmd == 'data-check':
        require(t['status'] in ('building', 'analyzing', 'awaiting-data', 'reviewing', 'testing'), 'Start the task first')
        if not analysis_gate(t, config, state, args.phase):
            return 2
    elif cmd == 'analysis-report':
        analysis_report(t, config, state, args)
    elif cmd == 'data-resolve':
        require(t['status'] == 'awaiting-data' and args.approved, 'User response and --approved required')
        artifact(t, 'prompts', body(args.file), 'md')
        if args.data:
            t['data_mode'] = args.data
            t['data_reason'] = body(args.file).strip()
        phase = t['analysis_pending']['phase']
        t['analysis_state'][phase]['response_required'] = False
        t['analysis_state'][phase]['status'] = 'recheck'
        if not analysis_gate(t, config, state, phase):
            return 2
    elif cmd == 'checkpoint':
        h = handoff_input(args.file)
        require(all(source_allowed(ref) for ref in h['files']), 'Checkpoint files must be source paths')
        selected = sorted(set(t['source_files'] + h['files']))
        working = fingerprint(config, t | {'source_files': selected})
        artifact(t, 'checkpoints', encoded(envelope(t, status=t['status'], content=h,
                 source_files=selected, working_snapshot=working)) + '\n')
    elif cmd == 'rebuild':
        require(t['status'] in ('reviewing', 'testing'), 'Rebuild applies to reviewed/tested work')
        artifact(t, 'prompts', body(args.file), 'md'); invalidate(t, config)
    elif cmd == 'block':
        require(t['status'] != 'blocked', 'Already blocked')
        t['previous_status'] = t['status']; t['status'] = 'blocked'
        artifact(t, 'prompts', body(args.file), 'md')
    elif cmd == 'unblock':
        require(t['status'] == 'blocked', 'Task is not blocked')
        require(t['repairs'] <= config['handoffs']['max_repairs'], 'Repair allowance exceeded; obtain direction and create a follow-up task')
        t['status'] = t.pop('previous_status', 'building')
    elif cmd == 'log':
        artifact(t, 'prompts', body(args.file), 'md')
    save(state)
    if cmd == 'done':
        milestone('Task completed: ' + t['title'], task=t['id'], rationale='Completion checks accepted current review, tests, memory, and final handoff.',
                  outcome='Task marked done.', evidence=[t['reviews'][-1], t['tests'][-1], t['memories'][-1], t['handoffs'][-1]])
    if cmd == 'test' and not t['test_pass']:
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Workflow error: {exc}', file=sys.stderr)
        sys.exit(1)
