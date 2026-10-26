"""Opt-in local aggregate summaries. No samples or categorical values are emitted."""
import json
import math

import data_analysis


def summarize(rows, fmt, maximum):
    objects = [row if isinstance(row, dict) else {'value': row} for row in rows]
    names = sorted({key for row in objects for key in row})
    columns = {}
    for name in names[:maximum]:
        values = [row.get(name) for row in objects]
        available = [value for value in values if not data_analysis.missing(value)]
        types = sorted({type(value).__name__ for value in available})
        column = {'types': types, 'missing': len(values) - len(available),
                  'unique': len({json.dumps(value, sort_keys=True, ensure_ascii=False) for value in available})}
        numbers = [data_analysis.numeric(value) for value in available]
        if numbers and all(number is not None for number in numbers):
            # fsum(v/n) avoids an intermediate overflow from adding large finite values.
            mean = math.fsum(value / len(numbers) for value in numbers)
            column['numeric'] = {'minimum': min(numbers), 'maximum': max(numbers), 'mean': mean}
        columns[name] = column
    return {'records': len(rows),
            'duplicate_records': len(rows) - len({json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows}),
            'columns': columns, 'omitted_columns': max(0, len(names) - maximum)}


def profile(root, config, task, phase):
    settings = config['analysis']['profiling']
    data_analysis.require(settings['enabled'] and config['analysis']['data_access'] == 'approved-summaries',
                          'Profiling needs enabled=true and approved-summaries access in approved configuration')
    data_analysis.require(phase in task['analysis_phases'], 'Phase not selected for this task')
    before = data_analysis.scan(root, config, task, phase)
    data_analysis.require(before['status'] == 'ready', 'Data must pass inspection before profiling')
    result = {'phase': phase, 'data_hash': before['hash'], 'files': [], 'omitted': [],
              'limitations': ['Aggregates may reveal sensitive information; this is not automatic anonymization.',
                              'Numeric summaries use floating-point approximations, not exact decimal accounting.']}
    for item in before['files']:
        path = data_analysis.data_path(root, item['path'])
        with path.open('rb') as handle:
            raw = handle.read(config['analysis']['max_file_bytes'] + 1)
        data_analysis.require(len(raw) <= config['analysis']['max_file_bytes'], 'Data changed during profiling')
        rows = data_analysis.parse_rows(raw, item['format'])
        summary = {key: item[key] for key in ('path', 'sha256', 'provenance')}
        summary.update(summarize(rows, item['format'], settings['max_columns']))
        result['files'].append(summary)
    after = data_analysis.scan(root, config, task, phase)
    data_analysis.require(before['hash'] == after['hash'], 'Data changed during profiling; summary discarded')
    # Preserve full column statistics or omit a whole section; never truncate JSON.
    size = lambda: len(json.dumps(result, ensure_ascii=False, indent=2))
    for item in reversed(result['files']):
        for name in reversed(list(item['columns'])):
            if size() <= settings['max_chars']:
                break
            del item['columns'][name]
            item['omitted_columns'] += 1
        if size() > settings['max_chars']:
            result['omitted'].append({'path': item['path'], 'reason': 'summary character limit; use focused dataset selection'})
    while size() > settings['max_chars'] and result['files']:
        result['files'].pop()
    data_analysis.require(size() <= settings['max_chars'], 'Summary metadata exceeds limit; narrow dataset selection')
    return result
