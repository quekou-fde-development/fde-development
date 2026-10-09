"""Deterministic engineering fixtures; these do not test AI semantic ability."""
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

from document_structure import NAMES, parse, specification, validate

ROOT = Path(__file__).resolve().parent.parent


def prepare_review_fixture(root):
    """Test input declaration only; never use this helper for business review."""
    args = [sys.executable, str(ROOT / 'scripts/run_meta_stages.py'),
            '--stage', 'render_documents', '--preview', '--run-dir', str(root)]
    proc = subprocess.run(args, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if proc.returncode:
        raise AssertionError({'args': args, 'rc': proc.returncode, 'stderr': proc.stderr})
    output = json.loads(proc.stdout)
    receipt = json.loads((root / output['preview_receipt']).read_text())
    coverage = root / 'working/engineering-review.txt'
    coverage.write_text('Engineering fixture declaration. No business content or human approval is evaluated.\n')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    request = json.loads((root / 'working/render_request.json').read_text())
    table = request['structure_bindings']['tables'][0]
    key = request['documents']['03-data-model.md'][table]['tables'][0][0][1]
    coverage.write_text('Engineering fixture declaration. No business content or human approval is evaluated.\n'
                        f'engineering-fixture: {table}.{key}\n')
    proof = {'schema_version': '1.0', 'decision': 'CONTENT_REVIEW_COMPLETED',
             'scope': 'CONTENT_ONLY', 'reviewer': 'engineering-fixture-no-business-verdict',
             'reviewed_at': datetime.now(timezone.utc).isoformat(),
             'render_request_sha256': receipt['request_sha256'],
             'preview_receipt_path': output['preview_receipt'],
             'preview_documents_sha256': receipt['documents_sha256'],
             'source_snapshot_sha256': digest(root / 'working/source_snapshot.json'),
             'coverage_path': 'working/engineering-review.txt', 'coverage_sha256': digest(coverage),
             'field_checks': [{'table': table, 'field_key': key, 'source_anchor': 'engineering-fixture'}]}
    (root / 'working/content_review_proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    return {'args': args, 'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}


def fixture():
    b = {'project': '结构验证项目', 'special_topic': '业务专项约束',
         'roles': ['主管', '执行员'], 'surfaces': ['Workbench'],
         'api_groups': ['Arcubase'], 'tables': ['业务表'],
         'scenarios': ['完整业务'], 'flows': ['BF-01 / UC-01 完整业务']}
    b['sources'] = {key: 'fixture://explicit-structure' for key in b}
    docs = {}
    for name, sections in specification(b).items():
        chunks = []
        for section in sections:
            title = section['title']
            chunk = '#' * section['level'] + ' ' + title + '\n\n'
            chunk += '确定性结构夹具，不代表真实业务设计。\n\n'
            for header in section['tables']:
                if name == '01-concept.md' and title == '角色边界':
                    rows = [[role, 'Workbench', '夹具职责'] for role in b['roles']]
                elif name == '05-site-architecture.md' and title == '角色边界':
                    rows = [['Workbench', '官方入口', '主管、执行员', '夹具职责']]
                elif name == '02-use-cases.md' and header == ['编号', '用例', '主流程', '验收']:
                    role_number = b['roles'].index(title.removesuffix('用例')) + 1
                    case_title = '完整业务' if role_number == 1 else '核对结果'
                    rows = [[f'UC-{role_number:02}', case_title, '执行夹具步骤', '核对夹具结果']]
                else:
                    rows = [['夹具值'] * len(header)]
                chunk += '| ' + ' | '.join(header) + ' |\n'
                chunk += '| ' + ' | '.join('---' for _ in header) + ' |\n'
                chunk += ''.join('| ' + ' | '.join(row) + ' |\n' for row in rows) + '\n'
            for label in section['labels']:
                chunk += label + ':\n- 已明确的夹具条件。\n\n'
            if section['form'] == 'tree':
                chunk += '```text\nWorkbench\n└─ 业务\n```\n\n'
            elif section['form'] == 'bullet':
                chunk += '- 已明确的夹具约束。\n\n'
            elif section['form'] == 'ordered':
                chunk += '1. 执行已确认动作。\n2. 核对结果。\n\n'
            elif section['form'] == 'flow':
                chunk += ''.join(f'{i}. **{label}：**夹具动作与结果。\n' for i, label in enumerate(
                    ['触发与读取', '判断与动作', '状态与回读', '异常与人工决定'], 1)) + '\n'
            chunks.append(chunk)
        docs[name] = ''.join(chunks)
    return {'schema_version': '1.0', 'unresolved_questions': [], 'structure_bindings': b, 'documents': docs}


def run(root):
    root.mkdir(parents=True, exist_ok=False)
    request = fixture()
    errors = validate(request['documents'], request['structure_bindings'])
    if errors:
        raise AssertionError(errors)
    # Independent shape expectations taken from the reference review, not from
    # a count returned by the production validator.
    h2 = [sum(line.startswith('## ') for line in request['documents'][n].splitlines()) for n in NAMES]
    assert h2 == [5, 4, 4, 9, 4, 3, 4, 5, 7], h2
    data = request['documents']['03-data-model.md']
    assert '必要时用一张简表补充' not in data
    assert 'tenant.<domain>' not in request['documents']['04-security-privacy.md']
    assert 'label（展示名） | key（稳定代码键） | FieldVO 类型 | 业务含义 | 必填 | 唯一 | 默认值模式 / 值 | 类型专属 options 与证据 | 记录职责 | 可读 / 可写角色 | 已确认约束' in data
    cases = []
    # Report all malformed delimiters together, without changing any input.
    malformed = '# 示例\n\n| A | B |\n| --- |\n| x | y |\n\n| C | D | E |\n| --- | --- |\n| a | b | c |\n'
    snapshot = malformed
    try:
        parse(malformed)
        raise AssertionError('malformed tables accepted')
    except ValueError as exc:
        diagnostic = str(exc)
        assert '第 4 行' in diagnostic and '第 8 行' in diagnostic, diagnostic
        assert '| --- | --- |' in diagnostic and '| --- | --- | --- |' in diagnostic
        assert malformed == snapshot
    cases.append({'case': 'all_delimiter_errors_reported_without_mutation', 'verdict': 'PASS', 'rejected': diagnostic})
    mutations = [
        ('rename_fixed_heading', '01-concept.md', '## 概念(Glossary)', '## 自行改名'),
        ('promote_table', '03-data-model.md', '### 业务表', '## 业务表'),
        ('merge_link_and_flow', '03-data-model.md', '## 4. 这些表与 Link 承载怎样的业务流', '这些表与 Link 承载业务流'),
        ('swap_headings', '01-concept.md', '## 概念(Glossary)', '## 角色边界'),
        ('field_column_name', '03-data-model.md', '类型专属 options 与证据', '随意合并列'),
        ('field_column_order', '03-data-model.md', '必填 | 唯一', '唯一 | 必填'),
        ('remove_tree', '01-concept.md', '```text\nWorkbench\n└─ 业务\n```', '只有正文，没有关系树。'),
        ('remove_stage_label', '09-implementation-roadmap.md', '完成门槛:', '完成说明:'),
        ('remove_flow_label', '03-data-model.md', '**异常与人工决定：**', '**结束：**'),
        ('invent_section', '08-tech-stack-and-directory.md', '## 5. 开发顺序建议', '## 新增无关章节\n\n内容\n\n## 5. 开发顺序建议'),
        ('role_inventory', '01-concept.md', '| 主管 |', '| 未知角色 |'),
        ('missing_doc', '01-concept.md', None, None),
    ]
    for label, name, old, new in mutations:
        bad = copy.deepcopy(request)
        if old is None:
            bad['documents'].pop(name)
        else:
            assert old in bad['documents'][name], label
            bad['documents'][name] = bad['documents'][name].replace(old, new, 1)
        errors = validate(bad['documents'], bad['structure_bindings'])
        assert errors, label
        cases.append({'case': label, 'verdict': 'PASS', 'rejected': errors})
    for label, replacement in [('dangling_flow_use_case', 'UC-99'), ('wrong_flow_use_case_name', 'UC-02')]:
        bad = copy.deepcopy(request)
        before = bad['structure_bindings']['flows'][0]
        after = before.replace('UC-01', replacement)
        bad['structure_bindings']['flows'][0] = after
        bad['documents']['03-data-model.md'] = bad['documents']['03-data-model.md'].replace(before, after)
        errors = validate(bad['documents'], bad['structure_bindings'])
        assert errors, label
        cases.append({'case': label, 'verdict': 'PASS', 'rejected': errors})
    # Execute the real renderer, then independently re-read through the auditor.
    golden = root / 'golden'
    (golden / 'input/sources').mkdir(parents=True)
    (golden / 'working').mkdir()
    (golden / 'input/sources/brief.md').write_text('机械夹具资料，不代表业务验收。\n')
    (golden / 'input/source_manifest.json').write_text(json.dumps({'schema_version': '1.0', 'source_roots': ['sources'], 'sources': [{'id': 'brief', 'path': 'sources/brief.md', 'kind': 'markdown'}]}))
    (golden / 'working/render_request.json').write_text(json.dumps(content_fixture(), ensure_ascii=False, indent=2) + '\n')
    commands = []
    for args in [
        ['run_meta_stages.py', '--stage', 'acquire_sources', '--run-dir', str(golden)],
        ['run_meta_stages.py', '--stage', 'render_documents', '--run-dir', str(golden)],
        ['audit.py', str(golden), '--all', '--contract', str(ROOT / 'assertions.json'), '--manifest', str(golden / 'run_manifest.json'), '--package', str(ROOT)],
    ]:
        if args[0] == 'run_meta_stages.py' and args[2] == 'render_documents':
            commands.append(prepare_review_fixture(golden))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / args[0]), *args[1:]], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        commands.append({'args': args, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise AssertionError(commands[-1])
    output = {'engineering_fixture_only': True, 'cases': cases, 'commands': commands,
              'verdict': 'PASS', 'golden': str(golden)}
    (root / 'result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    return output


def content_fixture():
    """Test-only input from the pre-generator reference fixture, not the compiler."""
    original = fixture()
    result = {**original, 'schema_version': '2.0', 'documents': {}}
    for name, spec in specification(original['structure_bindings']).items():
        sections = parse(original['documents'][name])
        values = {}
        for source, section in zip(sections, spec):
            value = {'text': '确定性结构夹具，不代表真实业务设计。'}
            if section['tables']:
                lines = [line for line in source['body'] if line.startswith('|')]
                value['tables'] = [[[cell.strip() for cell in line.strip('|').split('|')]
                                    for line in lines[2:]]]
            if section['form'] == 'bullet':
                value['items'] = ['已明确的夹具约束。']
            elif section['form'] == 'ordered':
                value['items'] = ['执行已确认动作。', '核对结果。']
            elif section['form'] == 'tree':
                value['tree'] = 'Workbench\n└─ 业务'
            elif section['form'] == 'flow':
                value['steps'] = {label: '夹具动作与结果。' for label in
                                  ['触发与读取', '判断与动作', '状态与回读', '异常与人工决定']}
            if section['labels']:
                value['labels'] = {label: '- 已明确的夹具条件。' for label in section['labels']}
            values[section['title']] = value
        result['documents'][name] = values
    # Independently authored known native-field examples. These remain fixtures.
    result['documents']['03-data-model.md']['业务表']['tables'] = [[
        ['业务编号', 'code', 'text', '夹具业务编号', '是', '是', '0 / null',
         '{"type":"text"}', '业务编号', '主管读写', 'fixture://native-text'],
        ['说明', 'note', 'textarea', '夹具文本', '否', '否', '0 / null',
         '{"html":false,"size":6}', '业务事实', '主管读写', 'fixture://native-textarea'],
        ['发生时刻', 'occurred_at', 'datetime', '夹具时间', '是', '否', '0 / null',
         '{"type":"datetime"}', '时间事实', '主管读写', 'fixture://native-datetime'],
        ['业务状态', 'business_status', 'select', '夹具状态', '是', '否', '0 / null',
         '{"options":{"mode":"custom","items":[{"key":1,"value":"启用"},{"key":2,"value":"停用"}]}}',
         '状态', '主管读写', 'fixture://native-select']
    ]]
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    args = ap.parse_args()
    output = run(Path(args.run_dir))
    print(json.dumps({'verdict': output['verdict'], 'rejections': len(output['cases']), 'golden': output['golden']}, ensure_ascii=False))
