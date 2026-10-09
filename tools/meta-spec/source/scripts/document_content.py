#!/usr/bin/env python3
"""Fill reference-derived slots, then compile fixed Markdown syntax.

The CLI prints an empty content request. It never edits references or run files.
Business decisions remain with the author and chief architect.
"""
import argparse
import json
import re
from pathlib import Path

from document_structure import NAMES, ROOT, specification


FLOW_LABELS = ('触发与读取', '判断与动作', '状态与回读', '异常与人工决定')


def checked_specification(binding):
    # A changed reference must never silently become a new template.
    import hashlib
    contract = json.loads((ROOT / 'references/document-structure.json').read_text())
    for name in NAMES:
        path = ROOT / 'references/design' / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != contract['reference_sha256'][name]:
            raise ValueError('原参照指纹与结构契约不符: ' + name)
    expected = specification(binding)
    for name, sections in expected.items():
        titles = [s['title'] for s in sections]
        if len(set(titles)) != len(titles):
            raise ValueError(name + ': 项目名称与固定章节重名，须澄清绑定')
    return expected


def slot(section):
    value = {'text': ''}
    if section['tables']:
        value['tables'] = [[] for _ in section['tables']]
    if section['form'] in ('bullet', 'ordered'):
        value['items'] = []
    elif section['form'] == 'tree':
        value['tree'] = ''
    elif section['form'] == 'flow':
        value['steps'] = {label: '' for label in FLOW_LABELS}
    if section['labels']:
        value['labels'] = {label: '' for label in section['labels']}
    return value


def template(binding):
    return {'schema_version': '2.0', 'unresolved_questions': [],
            'structure_bindings': binding,
            'documents': {name: {s['title']: slot(s) for s in sections}
                          for name, sections in checked_specification(binding).items()}}


def _string(value, where, allow_empty=False):
    if not isinstance(value, str) or (not value.strip() and not allow_empty):
        raise ValueError(where + ': 须填写字符串内容')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(where + ': 含不支持的控制字符')
    return value.strip()


def _prose(value, where, allow_empty=False):
    value = _string(value, where, allow_empty)
    fence = None
    previous = ''
    for line in value.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not marker[2].strip():
                fence = None
            previous = ''
            continue
        if fence:
            continue
        if (re.match(r'^\s*#{1,6}(?:\s|$)', line)
                or re.search(r'<\s*/?\s*(?:h[1-6]|table|tr|td|th)\b', line, re.I)
                or ('|' in line and '|' in previous)
                or re.match(r'^\s*\|', line)
                or re.match(r'^\s*(?:=+|-{2,})\s*$', line)):
            raise ValueError(where + ': 标题、表格和结构分隔符由脚本生成，请只填正文')
        previous = line
    if fence:
        raise ValueError(where + ': 代码围栏未闭合')
    return value


def _inline(value, where):
    value = _prose(value, where)
    if '\n' in value or re.match(r'^(?:[-*+]\s|\d+[.)]\s|```|~~~)', value):
        raise ValueError(where + ': 只填单项正文，编号和项目符号由脚本生成')
    return value


def _cell(value, where):
    # Cells are literal strings, not pre-escaped Markdown. Encoding is reversible.
    value = _string(value, where)
    return (value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('\\', '&#92;').replace('|', '&#124;').replace('\n', '<br>'))


def _native_field_options(documents, binding):
    """Check the known FieldVO contract, without inventing project options/IDs."""
    known = {'text', 'textarea', 'number', 'datetime', 'boolean', 'select', 'status',
             'member', 'file', 'linkto', 'lookup', 'rollup', 'formula', 'serialnumber'}
    for table in binding['tables']:
        for index, row in enumerate(documents['03-data-model.md'][table]['tables'][0]):
            where = f'03-data-model.md / {table} / 字段 {row[1]} / 第 {index + 1} 行'
            kind = row[2].strip().strip('`')
            if kind not in known:
                raise ValueError(where + ': FieldVO 类型须采用原参照列出的已证实代码')
            if kind not in {'text', 'textarea', 'datetime', 'select'}:
                continue
            try:
                options = json.loads(row[7].strip().strip('`'))
            except (ValueError, TypeError) as exc:
                raise ValueError(where + ': 类型专属 options 列须填写 FieldVO.options 的 JSON 对象；证据写在已确认约束列') from exc
            if not isinstance(options, dict):
                raise ValueError(where + ': FieldVO.options 须为 JSON 对象')
            if kind == 'text' and options.get('type') != 'text':
                raise ValueError(where + ': text 须显式给出 options.type="text"')
            if kind == 'textarea' and not isinstance(options.get('html'), bool):
                raise ValueError(where + ': textarea 须显式给出 options.html 布尔值')
            if kind == 'datetime' and options.get('type') not in {'date', 'datetime'}:
                raise ValueError(where + ': datetime 须显式给出 options.type 为 date 或 datetime')
            if kind == 'select':
                selection = options.get('options')
                if not isinstance(selection, dict) or selection.get('mode') != 'custom':
                    raise ValueError(where + ': select 须给出 options.options.mode="custom"')
                items = selection.get('items')
                if not isinstance(items, list) or not items:
                    raise ValueError(where + ': select 须给出已明确的 options.options.items')
                seen = set()
                for item in items:
                    if (not isinstance(item, dict) or type(item.get('key')) is not int
                            or not isinstance(item.get('value'), str) or not item['value'].strip()):
                        raise ValueError(where + ': 每个 select item 须有整数 key 和非空 value；新字段可规划 item key')
                    if item['key'] in seen:
                        raise ValueError(where + ': select item key 重复')
                    seen.add(item['key'])


def compile_documents(documents, binding):
    expected = checked_specification(binding)
    if not isinstance(documents, dict) or set(documents) != set(NAMES):
        raise ValueError('documents 必须恰有九个指定文件名')
    rendered = {}
    for name, sections in expected.items():
        content = documents[name]
        if not isinstance(content, dict) or set(content) != {s['title'] for s in sections}:
            raise ValueError(name + ': 章节内容键与原参照不符；请使用脚本输出的内容骨架')
        chunks = []
        for index, section in enumerate(sections):
            title = section['title']
            where = name + ' / ' + title
            value = content[title]
            if not isinstance(value, dict) or set(value) != set(slot(section)):
                raise ValueError(where + ': 内容槽位不符，应为 ' + ', '.join(slot(section)))
            blocks = []
            text = _prose(value['text'], where + '.text', allow_empty=True)
            if text:
                blocks.append(text)
            if 'items' in value:
                items = value['items']
                if not isinstance(items, list) or not items:
                    raise ValueError(where + '.items: 须有至少一项')
                blocks.append('\n'.join(
                    ('- ' if section['form'] == 'bullet' else str(i) + '. ')
                    + _inline(item, where + '.items[' + str(i - 1) + ']')
                    for i, item in enumerate(items, 1)))
            if 'tree' in value:
                tree = _string(value['tree'], where + '.tree')
                if '`' in tree or '~' in tree:
                    raise ValueError(where + '.tree: 只填树形文本，围栏由脚本生成')
                blocks.append('```text\n' + tree + '\n```')
            if 'steps' in value:
                steps = value['steps']
                if not isinstance(steps, dict) or set(steps) != set(FLOW_LABELS):
                    raise ValueError(where + '.steps: 须保留原参照四个步骤槽位')
                blocks.append('\n'.join(str(i) + '. **' + label + '：**'
                    + _inline(steps[label], where + '.steps.' + label)
                    for i, label in enumerate(FLOW_LABELS, 1)))
            if 'labels' in value:
                labels = value['labels']
                if not isinstance(labels, dict) or set(labels) != set(section['labels']):
                    raise ValueError(where + '.labels: 须保留原参照阶段标签')
                for label in section['labels']:
                    blocks.append(label + '：\n\n' + _prose(labels[label], where + '.labels.' + label))
            if 'tables' in value:
                tables = value['tables']
                if not isinstance(tables, list) or len(tables) != len(section['tables']):
                    raise ValueError(where + '.tables: 表格数量与原参照不符')
                for ti, (rows, header) in enumerate(zip(tables, section['tables'])):
                    if not isinstance(rows, list) or not rows:
                        raise ValueError(where + '.tables: 须填写数据行')
                    table = ['| ' + ' | '.join(header) + ' |',
                             '| ' + ' | '.join('---' for _ in header) + ' |']
                    for ri, row in enumerate(rows):
                        position = f'{where}.tables[{ti}][{ri}]'
                        if not isinstance(row, list) or len(row) != len(header):
                            raise ValueError(position + f': 原参照为 {len(header)} 列；请核对数据，脚本不补删单元格')
                        table.append('| ' + ' | '.join(_cell(cell, position + f'[{ci}]')
                                                      for ci, cell in enumerate(row)) + ' |')
                    blocks.append('\n'.join(table))
            group = index + 1 < len(sections) and sections[index + 1]['level'] > section['level']
            if not blocks and section['level'] > 1 and not group:
                raise ValueError(where + ': 章节尚无内容；不适用时填写原因及依据')
            chunks.append('#' * section['level'] + ' ' + title
                          + ('\n\n' + '\n\n'.join(blocks) if blocks else ''))
        rendered[name] = '\n\n'.join(chunks) + '\n'
    _native_field_options(documents, binding)
    return rendered


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bindings', required=True)
    args = ap.parse_args()
    try:
        value = template(json.loads(Path(args.bindings).read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, str(exc) + '\n')
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
