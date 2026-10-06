# -*- coding: utf-8 -*-
"""Prepare frozen trigger cases and score complete independent judge reports.

prepare writes judging/VERSION/_prepared.json and _judge_card.md. score reads
that version's snapshot, validates all N reports, then atomically writes result.
This helper performs no model calls. rc=0 means scoring completed; inspect
train/test failures and the independent behavior gate before accepting a skill.
"""
import argparse
import os
import random
import re
import sys
from datetime import datetime

from eval_common import (component, description, fingerprint, load_json,
                         score_command, trigger_set, workspace_root, write_json)


def read_description(skill_root, skill_path=None):
    if skill_path:
        paths = [os.path.join(skill_path, 'SKILL.md') if os.path.isdir(skill_path) else skill_path]
    else:
        siblings = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        paths = [os.path.join(siblings, os.path.basename(skill_root), 'SKILL.md'),
                 os.path.join(skill_root, 'SKILL.md')]
    for path in paths:
        if os.path.isfile(path):
            return description(path), os.path.abspath(path)
    raise ValueError('找不到所选 SKILL.md；请传 --skill-path（显式路径不回退）')


def split_train_test(tset, seed):
    ids = [q['id'] for q in tset]
    random.Random(seed).shuffle(ids)
    cut = max(1, int(len(ids) * 0.6))
    return ids[:cut], ids[cut:]


def context(args):
    component(args.skill); component(args.version)
    teval = os.path.join(os.path.abspath(args.root), args.skill, 'trigger_eval')
    return teval, os.path.join(teval, 'judging', args.version)


def snapshot_key(sp, cases):
    return fingerprint({'description': sp['description'], 'version': sp['version'],
                        'comparison_key': comparison_key(sp, cases)})


def comparison_key(sp, cases):
    return fingerprint({'cases': cases, 'train_ids': sp['train_ids'], 'test_ids': sp['test_ids'],
                        'runs': sp['runs'], 'seed': sp['seed']})


def cmd_prepare(args):
    if args.runs < 1:
        raise ValueError('--runs 须为正整数')
    teval, judging = context(args)
    if os.path.exists(judging):
        raise ValueError('版本目录已存在；保留冻结输入和报告，请使用新的 --version')
    cases = trigger_set(os.path.join(teval, 'trigger_set.json'))
    if args.rev_desc is not None:
        if not args.rev_desc.strip():
            raise ValueError('--rev-desc 不能为空')
        desc, source = args.rev_desc, '(--rev-desc)'
    else:
        desc, source = read_description(os.path.dirname(teval), args.skill_path)
    train, test = split_train_test(cases, args.seed)
    sp = {'schema_version': 2, 'version': args.version, 'description': desc,
          'description_src': source, 'train_ids': train, 'test_ids': test,
          'runs': args.runs, 'seed': args.seed, 'split': {'train': 0.6, 'test': 0.4},
          'trigger_set_sha256': fingerprint(cases)}
    sp['comparison_key'] = comparison_key(sp, cases)
    sp['eval_fingerprint'] = snapshot_key(sp, cases)
    os.makedirs(judging, exist_ok=False)
    write_json(os.path.join(judging, '_prepared.json'), sp)
    write_json(os.path.join(teval, '_split.json'), sp)  # latest-view compatibility only
    queries = '\n'.join(f"{q['id']}: {q['query']}" for q in cases)
    command = score_command(os.path.abspath(__file__), args.skill, args.root, args.version)
    card = f'''# 触发判定卡 · {args.skill} · {args.version}

派 {args.runs} 个独立、互不可见的注册 sub-agent。只给 description 与待判用户消息，
不给 should_trigger 标签。独立性由派发记录证明，JSON 完整性不能证明独立性。

[skill description]
{desc}

[待判用例]
{queries}

各 agent 每条只判 TRIGGER 或 SKIP，写一份报告到 `{judging}/runN.json`。
报告形状（N 为该 agent 编号，1 至 {args.runs}；verdicts 必须覆盖全部 id 各一次）：
{{"run": N, "eval_fingerprint": "{sp['eval_fingerprint']}", "verdicts": [{{"id": 0, "decision": "TRIGGER"}}]}}

全部报告到齐后运行：
`{command}`
'''
    for path in (os.path.join(judging, '_judge_card.md'), os.path.join(teval, '_judge_card.md')):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(card)
    print(f"[prepare] {len(cases)} cases; train={len(train)} test={len(test)} runs={args.runs}")
    print(f"[prepare] {os.path.join(judging, '_judge_card.md')}")


def _majority(decisions):
    fire = decisions.count('TRIGGER'); skip = decisions.count('SKIP')
    return None if fire == skip else fire > skip


def _score_ids(by_id, ids, votes):
    passed, failures = 0, []
    for qid in ids:
        fired = _majority(votes[qid]); q = by_id[qid]
        if fired is not None and fired == q['should_trigger']:
            passed += 1
        else:
            failures.append({'id': qid, 'query': q['query'], 'should_trigger': q['should_trigger'],
                             'fired': fired, 'reason': 'TIE' if fired is None else 'MISMATCH'})
    return passed / len(ids), failures


def cmd_score(args):
    teval, judging = context(args)
    sp = load_json(os.path.join(judging, '_prepared.json'))
    cases = trigger_set(os.path.join(teval, 'trigger_set.json'))
    if sp.get('schema_version') != 2 or sp.get('version') != args.version:
        raise ValueError('缺当前版本冻结快照，须重新 prepare 并独立判定')
    if type(sp.get('runs')) is not int or sp['runs'] < 1:
        raise ValueError('冻结快照 runs 非法')
    train, test = split_train_test(cases, sp['seed'])
    if train != sp['train_ids'] or test != sp['test_ids'] or not set(train).isdisjoint(test):
        raise ValueError('冻结 train/test 分区不符')
    if (fingerprint(cases) != sp['trigger_set_sha256'] or
            comparison_key(sp, cases) != sp['comparison_key'] or
            snapshot_key(sp, cases) != sp['eval_fingerprint']):
        raise ValueError('数据集或冻结快照已改变，须重新 prepare 与判定')
    expected = {f'run{n}.json' for n in range(1, sp['runs'] + 1)}
    actual = {n for n in os.listdir(judging) if n.startswith('run') and n.endswith('.json')}
    if actual != expected:
        raise ValueError(f"判定文件集合不齐：missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    ids = {q['id'] for q in cases}; votes = {qid: [] for qid in ids}
    for number in range(1, sp['runs'] + 1):
        filename = f'run{number}.json'
        data = load_json(os.path.join(judging, filename))
        if not isinstance(data, dict) or type(data.get('run')) is not int or data['run'] != number:
            raise ValueError(f'{filename}: run 编号与文件名不符')
        if data.get('eval_fingerprint') != sp['eval_fingerprint']:
            raise ValueError(f'{filename}: 判定未绑定本次冻结输入')
        rows = data.get('verdicts')
        if not isinstance(rows, list):
            raise ValueError(f'{filename}: verdicts 须为数组')
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f'{filename}: verdict 须为对象')
            qid, decision = row.get('id'), row.get('decision')
            if type(qid) is not int or qid not in ids or qid in seen:
                raise ValueError(f'{filename}: id 非法/未知/重复 {qid!r}')
            if decision not in ('TRIGGER', 'SKIP'):
                raise ValueError(f'{filename}: decision 非法')
            seen.add(qid); votes[qid].append(decision)
        if seen != ids:
            raise ValueError(f'{filename}: 判定缺 id {sorted(ids-seen)}')
    by_id = {q['id']: q for q in cases}
    tr, tr_fail = _score_ids(by_id, train, votes)
    te, te_fail = _score_ids(by_id, test, votes)
    result_path = os.path.join(teval, 'result.json')
    old = load_json(result_path) if os.path.exists(result_path) else {'iterations': []}
    if not isinstance(old, dict) or not isinstance(old.get('iterations'), list) or any(not isinstance(x, dict) for x in old['iterations']):
        raise ValueError('既有 result.json 格式无效，保留原件')
    iters = [it for it in old['iterations'] if not (it.get('version') == args.version and it.get('comparison_key') == sp['comparison_key'])]
    iters.append({'version': args.version, 'description': sp['description'],
                  'comparison_key': sp['comparison_key'], 'eval_fingerprint': sp['eval_fingerprint'],
                  'train_score': tr, 'test_score': te, 'train_failures': tr_fail,
                  'test_failures': te_fail, 'validated_runs': sp['runs'],
                  'scored_at': datetime.now().isoformat(timespec='seconds')})
    eligible = [it for it in iters if it.get('comparison_key') == sp['comparison_key']]
    best = max(eligible, key=lambda it: it['test_score'])
    original = next((it['description'] for it in eligible if it['version'] == 'original'), None)
    result = {'skill_name': args.skill, 'original_description': original,
              'best_description': best['description'], 'best_version': best['version'],
              'best_test_score': best['test_score'], 'runs_per_query': sp['runs'],
              'comparison_key': sp['comparison_key'], 'split': sp['split'],
              'best_scope': 'current-comparison-key', 'current_version': args.version,
              'current_evaluation_pass': not (tr_fail or te_fail),
              'best_evaluation_pass': not (best['train_failures'] or best['test_failures']),
              'input_validation': 'COMPLETE', 'evaluation_pass': not (tr_fail or te_fail),
              'method': 'independent-agent-votes', 'iterations': iters,
              'updated_at': datetime.now().isoformat(timespec='seconds')}
    write_json(result_path, result)
    print(f'[score] COMPLETE runs={sp["runs"]}; train={tr:.3f} test={te:.3f}; failures={len(tr_fail)+len(te_fail)}')
    print(f'[score] {result_path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for verb in ('prepare', 'score'):
        p = sub.add_parser(verb)
        p.add_argument('--skill', required=True)
        p.add_argument('--root', default=workspace_root())
        p.add_argument('--version', default='original')
        if verb == 'prepare':
            p.add_argument('--skill-path')
            p.add_argument('--runs', type=int, default=3)
            p.add_argument('--seed', type=int, default=42)
            p.add_argument('--rev-desc')
        p.set_defaults(func=cmd_prepare if verb == 'prepare' else cmd_score)
    args = ap.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
