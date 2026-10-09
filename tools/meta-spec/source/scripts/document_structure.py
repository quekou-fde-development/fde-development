"""Reference-derived Markdown structure; business values remain author supplied.

Only explicitly named repetitions vary. Fixed headings, column names and block
forms are read from the unchanged design references, never from generated text.
"""
import argparse
import json
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = tuple(p.name for p in sorted((ROOT / 'references/design').glob('*.md')))
LIST_KEYS = ('roles', 'surfaces', 'api_groups', 'tables', 'scenarios', 'flows')


def clean(value):
    return re.sub(r'\s+', ' ', value.replace('`', '').strip())


def cells(line):
    values = re.split(r'(?<!\\)\|', line.strip())
    if values and not values[0].strip():
        values.pop(0)
    if values and not values[-1].strip():
        values.pop()
    return [clean(html.unescape(v.replace('\\|', '|'))) for v in values]


def parse(text):
    """Parse the deliberately small Markdown subset used by the references."""
    sections, current, fence, yaml = [], None, None, False
    lines = text.splitlines()
    table_errors = []
    for index, line in enumerate(lines):
        if index == 0 and line == '---':
            yaml = True
            continue
        if yaml:
            if line == '---':
                yaml = False
            continue
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            token, lang = marker.groups()
            if fence is None:
                fence = token
                if current is not None:
                    current['fences'].append(lang.strip())
                    current['body'].append(line)
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
                if current is not None:
                    current['body'].append(line)
            continue
        if fence:
            if current is not None:
                current['body'].append(line)
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if heading:
            current = {'level': len(heading[1]), 'title': heading[2],
                       'line': index + 1, 'tables': [], 'fences': [], 'body': []}
            sections.append(current)
            continue
        if current is not None:
            current['body'].append(line)
            if '|' in line and index + 1 < len(lines):
                separators = cells(lines[index + 1])
                if separators and all(re.fullmatch(r':?-+:?', v) for v in separators):
                    header = cells(line)
                    if len(header) != len(separators):
                        replacement = '| ' + ' | '.join('---' for _ in header) + ' |'
                        table_errors.append(f'第 {index + 1} 行表头有 {len(header)} 列，第 {index + 2} 行分隔行有 {len(separators)} 列；仅将第 {index + 2} 行改为 {replacement}')
                    rows = []
                    for row_index, row in enumerate(lines[index + 2:], index + 3):
                        if '|' not in row or not row.strip():
                            break
                        values = cells(row)
                        if len(values) != len(header):
                            table_errors.append(f'第 {index + 1} 行表头有 {len(header)} 列，第 {row_index} 行数据有 {len(values)} 列；核对单元格，不自动补删内容')
                        rows.append(values)
                    if not rows:
                        table_errors.append(f'第 {index + 1} 行表格没有内容行')
                    current['tables'].append(header)
    if fence or yaml:
        raise ValueError('未闭合的代码围栏或 YAML')
    if table_errors:
        raise ValueError('\n'.join(table_errors))
    return sections


def bindings(value):
    expected = {'project', 'special_topic', 'sources', *LIST_KEYS}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('structure_bindings 须含 project、special_topic、sources、' + '、'.join(LIST_KEYS))
    def label(item):
        return (isinstance(item, str) and item.strip() == item and bool(item)
                and len(item) <= 120 and not re.search(r'[\r\n#|<>`]', item))
    if not all(label(value[k]) for k in ('project', 'special_topic')):
        raise ValueError('project / special_topic 须为单行名称')
    for key in LIST_KEYS:
        values = value[key]
        if (not isinstance(values, list) or not 1 <= len(values) <= 100
                or not all(label(v) for v in values) or len(set(values)) != len(values)):
            raise ValueError(f'{key} 须为有序、非空、不重复的项目名称数组')
    if not isinstance(value['sources'], dict) or set(value['sources']) != expected - {'sources'}:
        raise ValueError('sources 须逐项给出上述项目绑定的来源/设计推导锚点')
    if not all(isinstance(v, str) and v.strip() for v in value['sources'].values()):
        raise ValueError('来源锚点不得为空')
    return value


def specification(value):
    b = bindings(value)
    contract = json.loads((ROOT / 'references/document-structure.json').read_text())
    result = {}
    for name, nodes in contract['documents'].items():
        reference = parse((ROOT / 'references/design' / name).read_text())
        expected = []
        for rule in nodes:
            original = next(s for s in reference if s['title'] == rule['reference_heading'])
            items = b[rule['repeat']] if rule.get('repeat') else [None]
            for i, item in enumerate(items, 1):
                slots = dict(b, item=item, index=i, api_index=i+2, api_end=len(b['api_groups'])+3)
                title = rule.get('title', original['title']).format(**slots)
                expected.append({'level':original['level'], 'title':title,
                    'tables':rule.get('tables', original['tables']), 'form':rule.get('form'),
                    'labels':rule.get('labels', []),
                    'source':f'references/design/{name}:{original["line"]}'})
        result[name] = expected
    return result


def validate(documents, value):
    errors = []
    try:
        expected = specification(value)
    except (ValueError, OSError, StopIteration) as exc:
        return [f'结构规则/绑定不可用: {exc}']
    if not isinstance(documents, dict) or set(documents) != set(NAMES):
        return ['结构检查须提供精确九份文档']
    for name, wanted in expected.items():
        try:
            got = parse(documents[name])
        except (ValueError, TypeError) as exc:
            errors.append(f'{name}: {exc}')
            continue
        signature = lambda seq: [(s['level'], clean(s['title'])) for s in seq]
        if signature(got) != signature(wanted):
            errors.append(f'{name}: 标题层级/顺序/名称不符；期望 {signature(wanted)}；实际 {signature(got)}')
            continue
        for actual, spec in zip(got, wanted):
            label = f'{name}:{actual["line"]} {actual["title"]}'
            if actual['tables'] != spec['tables']:
                errors.append(f'{label}: 表格数量/列名/列顺序不符；期望 {spec["tables"]}；实际 {actual["tables"]}')
            body = '\n'.join(actual['body']).strip()
            # Group headings may introduce their H3 children without prose.
            at = got.index(actual)
            group = at + 1 < len(got) and got[at + 1]['level'] > actual['level']
            if actual['level'] > 1 and not body and not group:
                errors.append(f'{label}: 章节为空')
            for tag in spec.get('labels', []):
                if not re.search(r'^' + re.escape(tag) + r'[:：]\s*$', body, re.M):
                    errors.append(f'{label}: 缺少原参照的段内标签 {tag}')
            form = spec['form']
            if form == 'tree' and 'text' not in actual['fences']:
                errors.append(f'{label}: 缺少原参照的 text 关系/路由/目录树')
            if form == 'bullet' and not re.search(r'^\s*[-*+]\s+\S', body, re.M):
                errors.append(f'{label}: 缺少原参照的项目符号列表')
            if form in ('ordered', 'flow') and not re.search(r'^\s*1[.)]\s+\S', body, re.M):
                errors.append(f'{label}: 缺少原参照的编号流程')
            if form == 'flow':
                for text in ('触发与读取', '判断与动作', '状态与回读', '异常与人工决定'):
                    if not re.search(r'^\s*\d[.)]\s+\*\*' + text + r'[:：]\*\*', body, re.M):
                        errors.append(f'{label}: 缺少四步业务流标签 {text}')
    # The role/surface inventories bind repeated headings to actual table rows.
    for name, column, key in [('01-concept.md', 0, 'roles'), ('05-site-architecture.md', 0, 'surfaces')]:
        try:
            sections = parse(documents[name])
        except (ValueError, TypeError):
            continue
        section = next((s for s in sections if s['title'] == '角色边界'), None)
        if section:
            rows = [cells(line) for line in section['body'] if line.strip().startswith('|')]
            actual = [row[column] for row in rows[2:]]
            if actual != value[key]:
                errors.append(f'{name}: 角色/端清单须按 structure_bindings.{key} 的同一顺序展开')
    # Flow references must retain the ID/name pairing of the actual use-case
    # table. A valid-looking UC number alone does not establish that pairing.
    cases = {}
    try:
        for section in parse(documents['02-use-cases.md']):
            if ['编号', '用例', '主流程', '验收'] not in section['tables']:
                continue
            rows = [cells(line) for line in section['body'] if line.strip().startswith('|')][2:]
            for row in rows:
                ident, name = row[:2]
                if not re.fullmatch(r'UC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', ident) or ident in cases or not name:
                    errors.append('02-use-cases.md: 用例编号须唯一，且每个编号对应一个非空用例名')
                cases[ident] = name
        for flow in value['flows']:
            ids = re.findall(r'UC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', flow)
            if not ids:
                errors.append('03-data-model.md: 业务流标题缺少实际用例编号: ' + flow)
            for ident in ids:
                if ident not in cases or cases[ident] not in clean(flow):
                    errors.append(f'03-data-model.md: {ident} 须与 02 的完整用例名一起引用；实际业务流: {flow}；用例名: {cases.get(ident, "不存在")}')
    except (ValueError, TypeError):
        errors.append('02-use-cases.md: 无法读取业务流引用的用例清单')
    return errors


def validate_run(run_dir):
    root = Path(run_dir).resolve()
    def read(relative):
        path = root / relative
        if path.is_symlink() or not path.is_file() or root not in path.resolve().parents:
            raise ValueError('结构校验文件缺失或路径非法: ' + relative)
        return path.read_text()
    request = json.loads(read('working/render_request.json'))
    docs = {name: read('design/' + name) for name in NAMES}
    return validate(docs, request.get('structure_bindings'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bindings', help='输出预期标题与表头，供起草前使用')
    ap.add_argument('--document', choices=NAMES)
    ap.add_argument('--run-dir', help='重新读取最终九份文件并校验')
    args = ap.parse_args()
    if bool(args.bindings) == bool(args.run_dir):
        ap.error('须且只能选择 --bindings 或 --run-dir')
    if args.bindings:
        spec = specification(json.loads(Path(args.bindings).read_text()))
        print(json.dumps({args.document: spec[args.document]} if args.document else spec, ensure_ascii=False, indent=2))
        return 0
    errors = validate_run(args.run_dir)
    print(json.dumps({'verdict': 'FAIL' if errors else 'PASS', 'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
