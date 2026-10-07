# -*- coding: utf-8 -*-
"""Aggregate frozen eval runs without mixing artifact and routing metrics.

Requires iteration_plan.json produced by init_eval_workspace.py. Missing or
malformed runs are reported as INCOMPLETE, with exit code 1. Route match rate,
observed same-route convergence and all-k-correct rate are separate metrics.
"""
import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from eval_common import fingerprint, load_json, write_json


def normalize_stuck_notes(value):
    if isinstance(value, list):
        return [str(x.get('note', '')) if isinstance(x, dict) else str(x) for x in value]
    return [str(value)] if value else []


def run_metric(g):
    if not isinstance(g, dict):
        raise ValueError('grading 须为对象')
    et = g.get('eval_type')
    if et == 'end_state':
        score = g.get('summary', {}).get('pass_rate')
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('pass_rate 须为 [0,1] 内有限数')
        return et, score
    if et == 'route_convergence':
        value = g.get('route_result', {}).get('route_match')
        if type(value) is not bool:
            raise ValueError('route_match 须为 JSON boolean')
        return et, float(value)
    raise ValueError('eval_type 非法')


def aggregate(it_dir, skill, model=''):
    plan = load_json(os.path.join(it_dir, 'iteration_plan.json'))
    cases = load_json(os.path.join(os.path.dirname(it_dir), 'evals', 'evals.json'))['evals']
    if plan.get('schema_version') != 1 or plan.get('evals_sha256') != fingerprint(cases):
        raise ValueError('iteration 的冻结用例与当前 evals.json 不符')
    k = plan.get('runs')
    if type(k) is not int or k < 1:
        raise ValueError('iteration runs 非法')
    expected = [{'directory': f"eval-{ev['id']}-{config}-run{rn}", 'eval_id': ev['id'],
                 'eval_type': ev['eval_type'], 'configuration': config, 'run_number': rn}
                for ev in cases for config in ('with_skill', 'without_skill') for rn in range(1, k + 1)]
    if not expected or expected != plan.get('expected_runs'):
        raise ValueError('iteration 的 expected_runs 无效')
    names = {r['directory'] for r in expected}
    if len(names) != len(expected):
        raise ValueError('iteration 有重复 eval/run')
    extras = {n for n in os.listdir(it_dir) if n.startswith('eval-')} - names
    if extras:
        raise ValueError(f'iteration 有未登记 run: {sorted(extras)}')
    records, groups, errors = [], defaultdict(list), []
    for entry in expected:
        row = dict(entry)
        try:
            g = load_json(os.path.join(it_dir, entry['directory'], 'grading.json'))
            et, score = run_metric(g)
            if et != entry['eval_type']:
                raise ValueError('grading eval_type 与冻结用例不同')
            rr = g.get('route_result', {})
            actual = rr.get('actual_route') if et == 'route_convergence' else None
            if actual is not None and not isinstance(actual, (str, list, dict)):
                raise ValueError('actual_route 须为字符串/数组/对象')
            row.update({'result': {'primary_metric': 'pass_rate' if et == 'end_state' else 'route_match_rate',
                                   'pass_rate': score if et == 'end_state' else None,
                                   'route_match': bool(score) if et == 'route_convergence' else None},
                        'actual_route': actual, 'expectations': g.get('expectations', []),
                        'notes': normalize_stuck_notes(rr.get('stuck'))})
            groups[(entry['eval_id'], entry['configuration'], et)].append((score, actual))
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            row['result'] = {'missing': True, 'error': str(error)}
            errors.append({'directory': entry['directory'], 'error': str(error)})
        records.append(row)

    def summarize(config):
        by_type = {}
        for et in sorted({ev['eval_type'] for ev in cases}):
            ids = [ev['id'] for ev in cases if ev['eval_type'] == et]
            batches = [groups[(eid, config, et)] for eid in ids]
            complete = all(len(batch) == k for batch in batches)
            result = {'evals': len(ids), 'complete': complete, 'pass_k': None}
            if et == 'end_state':
                result['pass_rate'] = None
            else:
                result.update({'route_match_rate': None, 'convergence_rate': None})
            if complete:
                mean = statistics.mean(statistics.mean(x[0] for x in batch) for batch in batches)
                result['pass_rate' if et == 'end_state' else 'route_match_rate'] = mean
                result['pass_k'] = statistics.mean(float(all(x[0] == 1 for x in batch)) for batch in batches)
                if et == 'route_convergence' and all(x[1] is not None for batch in batches for x in batch):
                    result['convergence_rate'] = statistics.mean(float(len({fingerprint(x[1]) for x in batch}) == 1) for batch in batches)
            by_type[et] = result
        only = next(iter(by_type)) if len(by_type) == 1 else None
        primary = 'pass_rate' if only == 'end_state' else 'route_match_rate' if only else 'mixed'
        return {'by_eval_type': by_type, 'primary_metric': primary,
                'pass_rate': by_type.get('end_state', {}).get('pass_rate'),
                'route_match_rate': by_type.get('route_convergence', {}).get('route_match_rate'),
                'convergence_rate': by_type.get('route_convergence', {}).get('convergence_rate')}

    with_s, without_s = summarize('with_skill'), summarize('without_skill')
    delta = {}
    for et, vals in with_s['by_eval_type'].items():
        delta[et] = {}
        for metric in ('pass_rate', 'route_match_rate', 'convergence_rate', 'pass_k'):
            if metric in vals:
                a, b = vals[metric], without_s['by_eval_type'][et][metric]
                delta[et][metric] = a-b if a is not None and b is not None else None
    result = {'metadata': {'skill_name': skill, 'executor_model': model,
                          'timestamp': datetime.now().isoformat(timespec='seconds'),
                          'evals_run': len(cases), 'runs_per_configuration': k,
                          'expected_runs': len(expected), 'valid_runs': len(expected)-len(errors),
                          'status': 'INCOMPLETE' if errors else 'COMPLETE',
                          'evals_sha256': plan['evals_sha256']},
              'runs': records, 'run_summary': {'with_skill': with_s, 'without_skill': without_s, 'delta': delta},
              'errors': errors, 'notes': ['pass_k is the observed fraction of cases with all k runs correct.']}
    target = os.path.join(it_dir, 'benchmark', 'benchmark.json')
    write_json(target, result)
    lines = [f'# benchmark · {skill}', '', f"Status: {result['metadata']['status']}", '',
             '| eval_type | metric | with_skill | without_skill | delta |', '|---|---|---|---|---|']
    for et, metrics in delta.items():
        for metric, difference in metrics.items():
            lines.append(f"| {et} | {metric} | {with_s['by_eval_type'][et][metric]} | {without_s['by_eval_type'][et][metric]} | {difference} |")
    if errors:
        lines += ['', '## Incomplete runs', *[f"- {e['directory']}: {e['error']}" for e in errors]]
    with open(os.path.join(it_dir, 'benchmark', 'benchmark.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines)+'\n')
    print(f"{result['metadata']['status']} valid={len(expected)-len(errors)}/{len(expected)}; {target}")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('iteration_dir'); ap.add_argument('--skill-name', required=True)
    ap.add_argument('--model', default='')
    args = ap.parse_args()
    try:
        return aggregate(os.path.abspath(args.iteration_dir), args.skill_name, args.model)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
