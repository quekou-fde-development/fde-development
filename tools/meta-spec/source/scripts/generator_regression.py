#!/usr/bin/env python3
"""Regression of fixed formatting; does not certify architecture semantics."""
import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from document_content import compile_documents, template
from document_structure import parse, validate
from structure_regression import content_fixture, prepare_review_fixture

PACKAGE = Path(__file__).resolve().parent.parent


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run_command(root, label, argv):
    proc = subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    row = {'label': label, 'argv': list(map(str, argv)), 'exit_code': proc.returncode,
           'stdout': proc.stdout, 'stderr': proc.stderr}
    save(root / 'execution' / (label + '.json'), row)
    return row


def prepare(root, request):
    save(root / 'working/render_request.json', request)
    save(root / 'input/source_manifest.json', {'schema_version': '1.0', 'source_roots': ['sources'],
        'sources': [{'id': 'brief', 'path': 'sources/brief.md', 'kind': 'markdown'}]})
    (root / 'input/sources').mkdir()
    (root / 'input/sources/brief.md').write_text('固定格式工程夹具，不代表业务正确性。\n')


def resign(root):
    """Re-sign after a mutation so a hash check alone cannot detect the fault."""
    rows = []
    for file in sorted((root / 'design').glob('*.md')):
        raw = file.read_bytes()
        rows.append({'id': file.name, 'path': 'design/' + file.name, 'kind': 'markdown',
                     'sha256': hashlib.sha256(raw).hexdigest()[:16], 'byte_count': len(raw)})
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()[:16]
    for name in ['render_input_receipt.json', 'render_documents_receipt.json']:
        receipt = json.loads((root / name).read_text())
        receipt.update(documents=rows, documents_sha256=digest, document_count=len(rows))
        save(root / name, receipt)


def run(root, failed_draft=None):
    root.mkdir(parents=True, exist_ok=False)
    req = content_fixture()
    cases = []
    rendered = compile_documents(req['documents'], req['structure_bindings'])
    assert not validate(rendered, req['structure_bindings'])
    shuffled = {name: dict(reversed(list(value.items()))) for name, value in reversed(list(req['documents'].items()))}
    assert compile_documents(shuffled, req['structure_bindings']) == rendered
    cases.append({'case': 'deterministic_order_from_reference', 'verdict': 'PASS'})
    # An independent literal expectation for the exact failure mode: 8 vs 9.
    data = rendered['03-data-model.md'].splitlines()
    for heading, columns in [('## 1. 总共有哪几张表', 8), ('## 3. 多维表格之间的 Link 及关系', 9)]:
        i = data.index(heading)
        separator = next(line for line in data[i + 1:] if line.startswith('| ---'))
        assert separator == '| ' + ' | '.join(['---'] * columns) + ' |'
    cases.append({'case': 'eight_and_nine_column_delimiters', 'verdict': 'PASS'})
    special = copy.deepcopy(req)
    special['documents']['01-concept.md']['角色边界']['tables'][0][0][2] = 'A | B\nC & <br> \\ D'
    escaped = compile_documents(special['documents'], special['structure_bindings'])
    assert 'A &#124; B<br>C &amp; &lt;br&gt; &#92; D' in escaped['01-concept.md']
    assert not validate(escaped, req['structure_bindings'])
    cases.append({'case': 'literal_cell_encoding_without_column_drift', 'verdict': 'PASS'})
    golden = root / 'golden'
    prepare(golden, special)
    for stage in ['acquire_sources', 'render_documents']:
        if stage == 'render_documents':
            save(root / 'execution/preview-fixture.json', prepare_review_fixture(golden))
        result = run_command(root, stage, [PACKAGE / 'scripts/run_meta_stages.py', '--stage', stage, '--run-dir', golden])
        assert result['exit_code'] == 0, result
    audit = run_command(root, 'golden-audit', [PACKAGE / 'scripts/audit.py', golden, '--all',
        '--contract', PACKAGE / 'assertions.json', '--manifest', golden / 'run_manifest.json', '--package', PACKAGE, '--json'])
    assert audit['exit_code'] == 0, audit
    cases.append({'case': 'real_pipeline_and_independent_readback', 'verdict': 'PASS'})

    mutations = {}
    bad = copy.deepcopy(req); bad['documents']['01-concept.md']['角色边界']['tables'][0][0].pop()
    mutations['short_row'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['03-data-model.md']['1. 总共有哪几张表']['tables'][0][0].append('多余值')
    mutations['long_row'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['01-concept.md']['概念(Glossary)']['text'] = '## 自行新增章节'
    mutations['injected_heading'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['01-concept.md']['概念(Glossary)']['text'] = '| A | B |\n| --- | --- |\n| a | b |'
    mutations['injected_table'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['01-concept.md']['概念(Glossary)']['header'] = '任意改表头'
    mutations['extra_slot'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['01-concept.md'].pop('角色边界')
    mutations['missing_section'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['03-data-model.md']['BF-01 / UC-01 完整业务']['steps'].pop('异常与人工决定')
    mutations['missing_flow_slot'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['09-implementation-roadmap.md']['1. 阶段A: 后端优先落地']['labels'].pop('完成门槛')
    mutations['missing_stage_slot'] = (bad, 2)
    bad = copy.deepcopy(req); bad['documents']['01-concept.md']['角色边界']['tables'][0][0][2] = '<<未确定内容>>'
    mutations['encoded_placeholder'] = (bad, 2)
    bad = copy.deepcopy(req); bad['schema_version'] = '1.0'
    mutations['legacy_whole_markdown_rejected'] = (bad, 2)
    mutations['blank_content'] = (template(req['structure_bindings']), 2)
    bad = template(req['structure_bindings']); bad['unresolved_questions'] = ['谁有审批权？']
    mutations['clarification_precedes_blank_content'] = (bad, 3)
    for label, (bad, expected) in mutations.items():
        run_dir = root / label
        prepare(run_dir, bad)
        result = run_command(root, label, [PACKAGE / 'scripts/run_meta_stages.py', '--stage', 'render_documents', '--run-dir', run_dir])
        assert result['exit_code'] == expected, result
        assert not (run_dir / 'design').exists() and not (run_dir / 'render_documents_receipt.json').exists()
        cases.append({'case': label, 'verdict': 'PASS', 'exit_code': expected, 'diagnostic': result['stderr']})

    for label, old, new, assertion in [
        ('resigned_content_corruption', '审批职责不存在', '被改写的职责', 'render.content'),
        ('resigned_structure_corruption', '## 概念(Glossary)', '## 自行改名', 'render.structure')]:
        target = root / label
        shutil.copytree(golden, target)
        path = target / 'design/01-concept.md'
        if label == 'resigned_content_corruption':
            old = 'A &#124; B<br>C &amp; &lt;br&gt; &#92; D'
        before = path.read_text(); assert old in before
        path.write_text(before.replace(old, new, 1))
        resign(target)
        result = run_command(root, label, [PACKAGE / 'scripts/audit.py', target, '--all', '--contract', PACKAGE / 'assertions.json', '--json'])
        report = json.loads(result['stdout'])
        assert result['exit_code'] == 1, result
        assert any(r['id'] == assertion and r['status'] == 'FAIL' for r in report['rows']), report
        cases.append({'case': label, 'verdict': 'PASS', 'rejected_by': assertion})

    if failed_draft:
        raw = Path(failed_draft).read_bytes()
        text = raw.decode(); lines = text.splitlines()
        replay = copy.deepcopy(req)
        widths = []
        for heading, width in [('1. 总共有哪几张表', 8), ('3. 多维表格之间的 Link 及关系', 9)]:
            start = lines.index('## ' + heading)
            hi = next(i for i in range(start + 1, len(lines)) if lines[i].startswith('|'))
            widths.append({'heading': heading, 'header': width,
                           'failed_separator': len(lines[hi + 1].strip('|').split('|'))})
            rows = []
            for line in lines[hi + 2:]:
                if not line.startswith('|'):
                    break
                rows.append([c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))])
            replay['documents']['03-data-model.md'][heading]['tables'] = [rows]
        compiled = compile_documents(replay['documents'], replay['structure_bindings'])
        assert not validate(compiled, replay['structure_bindings'])
        assert widths == [{'heading': '1. 总共有哪几张表', 'header': 8, 'failed_separator': 9},
                          {'heading': '3. 多维表格之间的 Link 及关系', 'header': 9, 'failed_separator': 8}], widths
        save(root / 'failed-table-replay.json', replay)
        (root / 'failed-table-replay.md').write_text(compiled['03-data-model.md'])
        assert Path(failed_draft).read_bytes() == raw
        cases.append({'case': 'actual_failed_table_rows_recompiled', 'verdict': 'PASS',
                      'source_sha256': hashlib.sha256(raw).hexdigest(), 'old_widths': widths,
                      'scope': 'Only both failed tables reused; no claim of business-semantic correction.'})
    output = {'verdict': 'PASS', 'engineering_fixture_only': True, 'cases': cases}
    save(root / 'result.json', output)
    return output


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--failed-draft')
    args = ap.parse_args()
    result = run(Path(args.run_dir), args.failed_draft)
    print(json.dumps({'verdict': result['verdict'], 'cases': len(result['cases'])}))
