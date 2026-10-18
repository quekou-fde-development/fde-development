#!/usr/bin/env python3
"""Check source-backed business decisions before rendering a candidate.

This proves provenance, explicit state and required topic coverage. It cannot
prove that natural-language evidence entails the recorded decision or that a
named decision owner has authority; content review retains those duties.
"""
import hashlib
import json
import os
from pathlib import Path

TOPICS = frozenset({'app_target', 'role_authorization', 'system_boundary'})
DECISION_KINDS = frozenset({'project-evidence', 'project-decision'})


class DecisionContractError(ValueError):
    pass


class DecisionsOpen(DecisionContractError):
    def __init__(self, questions):
        self.questions = questions
        super().__init__('业务决定尚未齐备：' + '；'.join(questions))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    path = Path(os.path.abspath(path))
    if path.resolve() != path or not path.is_file() or path.is_symlink():
        raise DecisionContractError('决定依据须为无符号链接的普通文件: ' + str(path))
    return path


def child(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or Path(relative).is_absolute() or '..' in Path(relative).parts):
        raise DecisionContractError('决定依据路径须为运行目录内相对路径')
    path = regular(root / relative)
    if not path.is_relative_to(root):
        raise DecisionContractError('决定依据路径越界')
    return path


def load(path):
    raw = regular(path).read_bytes()
    try:
        return json.loads(raw), raw
    except (ValueError, UnicodeDecodeError) as exc:
        raise DecisionContractError('决定依据不是有效 JSON: ' + str(path)) from exc


def check(run_dir):
    """Return frozen files and decision rows, or fail closed before any writes."""
    root = Path(run_dir).resolve()
    manifest_path = child(root, 'input/source_manifest.json')
    manifest, manifest_raw = load(manifest_path)
    if not isinstance(manifest, dict):
        raise DecisionContractError('来源清单须为 JSON 对象')
    sources = manifest.get('sources')
    if not isinstance(sources, list):
        raise DecisionContractError('来源清单缺 sources')
    registers = [s for s in sources if isinstance(s, dict) and s.get('kind') == 'decision-register']
    if not registers:
        raise DecisionsOpen(['缺少取源前的业务决定记录；核对 App 选择、角色／对象授权和系统读写边界'])
    if len(registers) != 1:
        raise DecisionContractError('来源清单须恰有一份 decision-register')
    snapshot_path = child(root, 'working/source_snapshot.json')
    snapshot, snapshot_raw = load(snapshot_path)
    receipt_path = child(root, 'acquire_sources_receipt.json')
    receipt, receipt_raw = load(receipt_path)
    frozen = [(manifest_path, manifest_raw), (snapshot_path, snapshot_raw), (receipt_path, receipt_raw)]
    if (not isinstance(snapshot, dict) or not isinstance(receipt, dict)
            or snapshot.get('schema_version') != '1.0'
            or snapshot.get('source_manifest_sha256') != digest(manifest_raw)):
        raise DecisionContractError('来源清单在取源后改变；使用包含补充决定的新候选目录')
    by_id, expected, actual = {}, [], {}
    if not isinstance(manifest.get('source_roots'), list) or not manifest['source_roots']:
        raise DecisionContractError('来源清单缺 source_roots')
    roots = []
    for value in manifest['source_roots']:
        if not isinstance(value, str) or '..' in Path(value).parts or '\\' in value:
            raise DecisionContractError('非法来源根')
        path = Path(value) if Path(value).is_absolute() else root / 'input' / value
        if path.resolve() != path.absolute() or not path.is_dir():
            raise DecisionContractError('来源根无效')
        roots.append(path.resolve())
    for s in sources:
        if not isinstance(s, dict) or set(s) != {'id', 'path', 'kind'}:
            raise DecisionContractError('来源条目格式错误')
        if not all(isinstance(s[k], str) and s[k].strip() for k in s) or s['id'] in by_id:
            raise DecisionContractError('来源标识、路径或种类无效')
        if '..' in Path(s['path']).parts or '\\' in s['path']:
            raise DecisionContractError('非法来源路径')
        path = Path(s['path']) if Path(s['path']).is_absolute() else root / 'input' / s['path']
        path = regular(path)
        if not any(path.is_relative_to(p) for p in roots):
            raise DecisionContractError('来源不在声明的根内')
        if path == manifest_path or (path.is_relative_to(root) and not path.is_relative_to(root / 'input')):
            raise DecisionContractError('中间分析和候选正文不能充当决定原件')
        raw = path.read_bytes()
        rel = 'working/sources/' + s['id'] + '.bin'
        saved_path = child(root, rel)
        saved = saved_path.read_bytes()
        if saved != raw:
            raise DecisionContractError('来源或业务决定记录在取源后改变: ' + s['id'])
        expected.append({'id': s['id'], 'source_path_sha256': digest(s['path'].encode()),
                         'content_sha256': digest(raw), 'byte_count': len(raw), 'snapshot_path': rel})
        by_id[s['id']] = s
        actual[s['id']] = raw
        frozen.extend([(path, raw), (saved_path, saved)])
    if snapshot.get('sources') != expected:
        raise DecisionContractError('业务决定与完整来源快照不一致')
    outputs = [{'id': 'working/source_snapshot.json', 'kind': 'file', 'sha256': digest(snapshot_raw)[:16]}]
    outputs += [{'id': r['snapshot_path'], 'kind': 'file', 'sha256': r['content_sha256'][:16]} for r in expected]
    output_hash = digest(json.dumps(outputs, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())[:16]
    if (receipt.get('stage') != 'acquire_sources'
            or receipt.get('source_id') != 'sha256:' + digest(manifest_raw)
            or receipt.get('source_count') != len(expected)
            or receipt.get('outputs') != outputs or receipt.get('output_count') != len(outputs)
            or receipt.get('outputs_sha256') != output_hash):
        raise DecisionContractError('业务决定与取源回执不一致')
    try:
        register = json.loads(actual[registers[0]['id']])
    except (ValueError, UnicodeDecodeError) as exc:
        raise DecisionContractError('decision-register 须为 UTF-8 JSON') from exc
    if (not isinstance(register, dict) or set(register) != {'schema_version', 'decisions'}
            or register['schema_version'] != '1.0' or not isinstance(register['decisions'], list)):
        raise DecisionContractError('decision-register 须含 schema_version=1.0 和 decisions 数组')
    ids, topics, questions = set(), set(), []
    for row in register['decisions']:
        if (not isinstance(row, dict)
                or set(row) != {'id', 'topic', 'state', 'statement', 'owner', 'evidence'}
                or not all(isinstance(row[k], str) and row[k].strip()
                           for k in ('id', 'topic', 'state', 'statement', 'owner'))
                or row['id'] in ids or row['state'] not in {'open', 'defined', 'proposed'}):
            raise DecisionContractError('业务决定条目格式、状态或唯一编号无效')
        if row['topic'] in TOPICS and row['topic'] in topics:
            raise DecisionContractError('同一必需主题须只有一条当前决定；合并明确边界或保留 open: ' + row['topic'])
        ids.add(row['id']); topics.add(row['topic'])
        if not isinstance(row['evidence'], list) or not row['evidence']:
            raise DecisionContractError('每项业务决定须引用原始来源，未知项也保留来源: ' + row['id'])
        for anchor in row['evidence']:
            if (not isinstance(anchor, dict)
                    or set(anchor) != {'source_id', 'line_start', 'line_end', 'quote'}
                    or anchor['source_id'] not in by_id
                    or type(anchor['line_start']) is not int or type(anchor['line_end']) is not int
                    or anchor['line_start'] < 1 or anchor['line_end'] < anchor['line_start']
                    or not isinstance(anchor['quote'], str) or not anchor['quote'].strip()):
                raise DecisionContractError('决定来源锚点无效: ' + row['id'])
            sid = anchor['source_id']
            if sid == registers[0]['id']:
                raise DecisionContractError('决定记录不能引用自身作为依据')
            try:
                lines = actual[sid].decode('utf-8').splitlines()
            except UnicodeDecodeError as exc:
                raise DecisionContractError('决定依据须提供可逐行核对的 UTF-8 原文或取源转写') from exc
            if (anchor['line_end'] > len(lines)
                    or '\n'.join(lines[anchor['line_start']-1:anchor['line_end']]) != anchor['quote']):
                raise DecisionContractError('决定摘录与原件逐行内容不符: ' + row['id'])
            if row['state'] != 'open' and by_id[sid]['kind'] not in DECISION_KINDS:
                raise DecisionContractError('模拟、参考或未分类来源不能关闭项目业务决定: ' + row['id'])
        if row['state'] == 'open':
            questions.append(row['id'] + ': ' + row['statement'])
    questions.extend('缺少业务决定主题: ' + topic for topic in sorted(TOPICS - topics))
    if questions:
        raise DecisionsOpen(questions)
    return [(str(path), raw) for path, raw in frozen], register['decisions']
