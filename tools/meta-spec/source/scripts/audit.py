#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用断言解释器 —— 读 assertions.json，跑断言，出 PASS/FAIL 退出码。

设计约束（来源 references/contract_ir.md）：
  * 本器跨包复用，不逐包重写。逐包变化的只有 assertions.json 与被审产物。
    生产脚本与本器不得从同一段散文自由生成（共因错误）。
  * 弱断言只能 WARN，不能单独满足段闸。
  * T2 不可跑时标 UNVERIFIED，不得改判 PASS，不得省略。
  * derived_fields 非空的断言不计入该字段的最低谓词族覆盖（守恒式反解禁则）。

谓词一律声明式：解释器不 eval 任何东西。未知 family / 未知 op / 未知规则类型
一律报错判 FAIL（契约错），不静默通过。

用法：
  python3 audit.py <run_dir> --contract <assertions.json> --stage <段标识>
  python3 audit.py <run_dir> --contract <assertions.json> --all
  python3 audit.py <run_dir> --contract <assertions.json> --all --source <源文件>

退出码（三判定各占一码，不压成二值）：
  0 = PASS                 全部 tier 跑齐、零失败
  1 = FAIL                 任一断言 FAIL
  2 = 用法 / 契约本身错     参数缺失、契约文件读不出或解析不了
  3 = PASS_WITH_UNVERIFIED 无 FAIL，但存在 UNVERIFIED（源不可达的 T2 未跑）
                           **仅 --all 末端复核时返回**；--stage 段闸下同一判定返回 0

3 与 0 分开是因为「验过且全对」与「有面没验」是两种交接状态：压成同一个 0 时，
调用方（排程 / 上游流水线 / 交付闸）拿到的信号里「哪些面没验」这一位消失了，
而这正是 T2 不可跑时 manifest 要报的那件事。

3 只在 --all 出现，是因为两种调用的职责不同：--stage 是 fail-fast 段闸，它的
输出只回答「下游能不能走」——源不可达不是产物错，不得阻断 T0/T1，故返回 0；
--all 是末端交付判定，「有面没验」必须进退出码。段闸下的 UNVERIFIED 并未丢失，
逐条在 stdout / --json 的 rows 里，且落进 manifest 的 unresolved_coverage。

2 与 1 分开同理——契约本身写错时断言根本没跑过，与「跑了且拒了」不是一回事，
把它并进 1 会让「闸拒了」与「闸没跑」在退出码上不可分。
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
IR_PATH = os.path.join(HERE, "..", "references", "contract_ir.json")


def load_ir():
    with open(IR_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()[:16]


def sha256_package(root):
    """包内容指纹：按相对路径排序，逐件把「路径 + 内容」喂进同一个 hash。

    路径也进 hash——只喂内容的话，改文件名或搬目录不改指纹，包就成了
    「一堆字节」而不是「一个结构」。跳过 runs/ 与 __pycache__：前者是本次
    运行的产物（自指），后者是解释器缓存，都不属包的声明面。
    """
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in ("runs", "__pycache__", ".git"))
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            h.update(rel.replace(os.sep, "/").encode("utf-8"))
            with open(full, "rb") as f:
                for blk in iter(lambda: f.read(65536), b""):
                    h.update(blk)
    return h.hexdigest()[:16]


class Report:
    def __init__(self):
        self.rows = []

    def add(self, stage, aid, family, tier, status, detail=""):
        self.rows.append({"stage": stage, "id": aid, "family": family,
                          "tier": tier, "status": status, "detail": detail})

    def counts(self, stage=None):
        rows = [r for r in self.rows if stage is None or r["stage"] == stage]
        return {
            "passed": sum(1 for r in rows if r["status"] == "PASS"),
            "failed": sum(1 for r in rows if r["status"] == "FAIL"),
            "unverified": sum(1 for r in rows if r["status"] == "UNVERIFIED"),
            "warned": sum(1 for r in rows if r["status"] == "WARN"),
        }


# ---------------------------------------------------------------- 取值与规则

# 解释器实际读过的产物路径。输出字段覆盖只认它——「字段名在谓词里出现过」
# 不算证据（往任意谓词塞一个 "note": "n_claimed" 就能把 n_claimed 标成已覆盖，
# 而没有任何求值器读过它）。每条断言求值前清空，求值后并入该 operation 的账。
#
# 只记**本 operation 自己那份产物**的读取：断言常同时读上游产物（如
# key_row_preservation 两侧都读 rows[].id），两份产物字段同名是常态，
# 不按产物区分就会出现「读了上游的 total，算成本件的 total 被覆盖了」。
_READS = set()
_DEEP = set()
_CUR_ART = None


def _reads_reset(art=None):
    global _CUR_ART
    _READS.clear()
    _DEEP.clear()
    _CUR_ART = art


def _touch(art, *paths):
    """显式登记一次读取。行内字段用 `coll[].field` 形态。"""
    if art is not _CUR_ART:
        return
    for p in paths:
        if p:
            _READS.add(p)


def _touch_rows(art, coll, fields):
    if art is not _CUR_ART:
        return
    for f in fields:
        if f:
            _READS.add(f"{coll}[].{f}")


def _touch_members(art, path):
    """登记一次**标量清单的成员值比对**（集合 / 多重集相等），记作 `path[]`。

    与只取 `len` 的读取区分：清单长度相等不约束成员是谁，改一个成员名长度
    一动不动。故 detail_recomputation 那种只比长度的读取不授予成员面覆盖。
    """
    if art is not _CUR_ART:
        return
    if path:
        _READS.add(f"{path}[]")


def _touch_deep(art, path):
    """登记一次**整块比对**：该路径下每片叶子都被这次比较约束住了。

    与 _touch 分开记，因为覆盖判定对两者的传递性不同：读过 `rows` 不覆盖
    `rows[].fee`（取出集合后比了哪几列由 family 自己决定），而整块相等覆盖。
    """
    if art is not _CUR_ART:
        return
    if path:
        _DEEP.add(path)


def _get(art, path):
    """按点号路径取值。缺路径抛 KeyError，不返回 None 冒充空值。

    读到的路径记进 _READS——输出字段覆盖只认解释器实际读过的东西，
    不认「字段名在谓词里出现过」。登记时把跨列表的一段改写成 `coll[].field`：
    `_get(art,"rows.fee")` 读的是每行的 fee，与 `_touch_rows` 登记的是同一面，
    两种写法必须归一，否则同一次读取按调用点不同记成两个不同路径。
    """
    cur, rec = art, ""
    for part in path.split("."):
        if isinstance(cur, list):
            rec = f"{rec}[].{part}"
            cur = [c[part] for c in cur]
        else:
            rec = f"{rec}.{part}" if rec else part
            cur = cur[part]
    if art is _CUR_ART:
        _READS.add(rec)
    return cur


def _test(value, t):
    """单字段测试：{"op":"eq|ne|in|not_in|contains", "value"|"values": …}"""
    op = t["op"]
    if op == "eq":
        return value == t["value"]
    if op == "ne":
        return value != t["value"]
    if op == "in":
        return value in t["values"]
    if op == "not_in":
        return value not in t["values"]
    if op == "contains":
        return t["value"] in str(value)
    raise ValueError(f"未知谓词 op: {op}")


def _when(item, when):
    """一个 case 的条件：字段名 → 测试，字段间取合取。"""
    return all(_test(item[f], t) for f, t in when.items())


def _eval_rule(item, rule, art=None):
    """声明式规则求值。三型：lookup / date_offset / match。

    match 型按 cases 顺序求值取首个命中——多字段合取的分桶函数（如
    「查无 且 委外 → continue；查无 且 自制 → 无工单」）靠它表达。
    """
    kind = rule["type"]
    if kind == "lookup":
        return rule["table"].get(str(item[rule["field"]]), rule.get("default"))
    if kind == "date_offset":
        # 按自然日差归组，不按滑窗。bands 逐条 [下界, 上界, 桶名]，上界 null = 无穷
        d = date.fromisoformat(str(item[rule["field"]])[:10])
        if rule.get("base_path") is not None:
            base_raw = _get(art, rule["base_path"])
        elif rule.get("base_field") is not None:
            base_raw = item[rule["base_field"]]
        else:
            base_raw = rule["base"]
        base = date.fromisoformat(str(base_raw)[:10])
        delta = (base - d).days
        if delta < 0:
            return rule.get("future_default")
        for lo, hi, name in rule["bands"]:
            if delta >= lo and (hi is None or delta <= hi):
                return name
        return rule.get("default")
    if kind == "match":
        for case in rule["cases"]:
            if _when(item, case["when"]):
                return case["then"]
        return rule.get("default")
    raise ValueError(f"未知规则类型: {kind}")


def _id_set(art, spec):
    """从 {collection,id_field} 或 {ids} 取一个 id 集合，可选 filter 过滤。"""
    if "ids" in spec:
        _touch_members(art, spec["ids"])
        return list(_get(art, spec["ids"]))
    coll = spec["collection"]
    items = _get(art, coll)
    flt = spec.get("filter")
    if flt:
        _touch_rows(art, coll, [flt["field"]])
        items = [it for it in items if _test(it[flt["field"]], flt)]
    idf = spec.get("id_field", "id")
    _touch_rows(art, coll, [idf])
    return [it[idf] for it in items]


def _resolve_artifact(ctx, spec):
    """把一条上游引用解析成唯一一份产物。歧义即拒，不猜。

    寻址按 (段, 产物名) 双键。只给段名时：该段恰好挂一个 operation 才认，
    挂两个及以上直接报错——「取第一个」是在契约没说清的地方替它做主，
    而它做的主恰好是产物覆盖 bug 的同一个错：断言照跑，跑在没指定的那份上。
    段名对不上契约同样报错，不静默当作「产物未落盘」。

    歧义是**契约**的属性不是 run 目录的属性：第二份产物没落盘时引用照样歧义，
    故按契约声明的 operation 数判，不按已载入的产物数判。
    """
    stage = spec["stage"]
    declared = ctx["stage_ops"].get(stage)
    if declared is None:
        raise KeyError(f"上游引用的段不在契约里: {stage}")
    name = spec.get("artifact")
    if name is None:
        if len(declared) != 1:
            raise KeyError(
                f"上游引用有歧义: 段「{stage}」挂了 {len(declared)} 个 operation "
                f"（{declared}），只给段名无法确定指哪一份产物，须补 artifact 字段")
        name = declared[0]
    elif name not in declared:
        raise KeyError(f"段「{stage}」下没有声明产物 {name}（有 {declared}）")
    art = ctx["artifacts"].get((stage, name))
    if art is None:
        raise KeyError(f"上游产物未载入: {(stage, name)}")
    return art


def _upstream(ctx, spec):
    """取上游产物的 id 集合。"""
    return _id_set(_resolve_artifact(ctx, spec), spec)


# ---------------------------------------------------------------- 源适配器
# T2 需要机械重读源。源格式适配器是封闭集合，与 family 一样不逐包新写。

def _read_markdown_tables(path):
    """读 markdown 的 `## 表 X` 小节为行列表。

    **全空行是数据不是格式**：只丢掉分隔线（全为连字符的行）与表头，
    保留全空单元格行。诊断源：本 harness 初版把表 A 的空白行当分隔线丢弃，
    造成 golden 假阳性 2 条——与被审对象「静默丢空白行」同构的错。
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    tables, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            tables[cur] = []
            continue
        if cur is None or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        nonempty = [c for c in cells if c]
        if nonempty and all(re.fullmatch(r"-+:?|:?-+:?", c) for c in nonempty):
            continue  # 分隔线
        tables[cur].append(cells)
    return {k: (v[1:] if v else []) for k, v in tables.items()}  # 丢表头


def _pick_section(tables, want):
    for head, rows in tables.items():
        if head.startswith(want) or head.split("·")[0].strip().startswith(want):
            return rows
    raise KeyError(f"源中无小节: {want}")


def _normalize(value, rules):
    """声明式字符串归一：按序取首个命中；末条可给 {"else": …} 兜底。"""
    if not rules:
        return value
    for r in rules:
        if "else" in r:
            return r["else"]
        if r["contains"] in str(value):
            return r["to"]
    return value


def _source_map(ctx, spec):
    """把源读成 {key: value} 查找表。"""
    if spec["format"] != "markdown_table":
        raise ValueError(f"未知源格式: {spec['format']}")
    rows = _pick_section(_read_markdown_tables(ctx["source"]), spec["section"])
    out = {}
    for r in rows:
        if len(r) <= max(spec["key_col"], spec["value_col"]):
            continue
        k = r[spec["key_col"]]
        if not k:
            continue
        out[k] = r[spec["value_col"]]
    return out


# ---------------------------------------------------------------- 谓词实现
# 每个 family 一个求值器。签名统一 (art, spec, ctx) -> (bool, detail)。

def _canon(obj):
    """内容指纹用的规范化序列化：键排序，无空白，不转义非 ASCII。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _content_hash(rows):
    return hashlib.sha256(_canon(rows).encode("utf-8")).hexdigest()[:16]


def _multiset(items):
    """把 id 列表转成计数字典。用它而不是 set——重数是数据，set 会把它抹掉。"""
    c = {}
    for it in items:
        c[it] = c.get(it, 0) + 1
    return c


def _ms_diff(a, b):
    """多重集差：返回 a 比 b 多出的部分（含重数）。"""
    out = {}
    for k, n in a.items():
        d = n - b.get(k, 0)
        if d > 0:
            out[k] = d
    return out


def _ms_fmt(d):
    return sorted(f"{k}×{n}" if n > 1 else str(k) for k, n in d.items())


_TYPES = {"str": str, "int": int, "float": (int, float), "bool": bool,
          "number": (int, float), "list": list, "dict": dict}


def f_count_hash(art, spec, ctx):
    """行数**与内容指纹**双落账。

    Gate-ID: audit.family.count_hash
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    只比 len 时，改一行的值而行数不变即全绿——「取回来的还是那批数据」这一问
    没有被回答过。IR 的 operation 最低族表写的是「行数与内容指纹落账」，两样都得有：故未声明
    `declared_hash` 时本条 fail-closed，不当作只验行数的简版放行。
    """
    p = spec["predicate"]
    rows = _get(art, p["collection"])
    got, want = len(rows), _get(art, p["declared_count"])
    if got != want:
        return False, f"实到 {got} / 声明 {want}"
    if "declared_hash" not in p:
        return False, ("count_hash 只声明了行数、未声明内容指纹（declared_hash）"
                       "——同行数改内容即无声通过")
    for r in rows:
        if isinstance(r, dict):
            _touch_rows(art, p["collection"], sorted(r.keys()))
    h_got = _content_hash(rows)
    h_want = _get(art, p["declared_hash"])
    if h_got != h_want:
        return False, f"行数 {got} 相符但内容指纹 {h_got} / 声明 {h_want}"
    binding = p.get("file_bindings")
    if binding is not None:
        if not isinstance(binding, dict) or set(binding) != {"path_field", "hash_field"}:
            return False, "file_bindings 须声明 path_field 与 hash_field"
        if not rows:
            return False, "文件回执不能为空"
        seen = set()
        for row in rows:
            rel = row[binding["path_field"]]
            path = contained_file(ctx["run_dir"], rel)
            if path in seen:
                return False, f"文件回执重复: {rel}"
            seen.add(path)
            wanted = row[binding["hash_field"]]
            if not isinstance(wanted, str) or not re.fullmatch(r"[0-9a-f]{16}", wanted):
                return False, f"文件指纹格式错误: {rel}"
            if not os.path.isfile(path) or sha256_file(path) != wanted:
                return False, f"文件不存在或内容指纹不符: {rel}"
    return True, f"实到 {got} / 声明 {want}；指纹 {h_got}"


def contained_file(root, relative):
    """Resolve a declared artifact only inside its run directory."""
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or os.path.isabs(relative) or re.match(r"^[A-Za-z]:", relative)
            or ".." in relative.split("/")):
        raise ValueError(f"产物须为 run-dir 内相对路径: {relative!r}")
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, relative))
    if os.path.commonpath([base, path]) != base or path == base:
        raise ValueError(f"产物路径逃逸: {relative}")
    return path


from pathlib import Path

STRUCTURE_PACKAGE = Path(__file__).resolve().parent.parent


def _structure_norm(text):
    return ' '.join(text.replace('`', '').split())


def _structure_columns(line):
    import html
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|') and not line.endswith('\\|'):
        line = line[:-1]
    return [_structure_norm(html.unescape(c.replace('\\|', '|'))) for c in re.split(r'(?<!\\)\|', line)]


def _structure_outline(text):
    lines = text.splitlines()
    start = 0
    if lines and lines[0] == '---':
        try:
            start = lines.index('---', 1) + 1
        except ValueError:
            raise ValueError('YAML 未闭合')
    heads, fence = [], None
    for i in range(start, len(lines)):
        m = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)', lines[i])
        if m:
            if fence is None:
                fence = m[1]
            elif m[1][0] == fence[0] and len(m[1]) >= len(fence):
                fence = None
            continue
        if fence is None:
            m = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', lines[i])
            if m:
                heads.append((i, len(m[1]), m[2]))
    if fence:
        raise ValueError('代码围栏未闭合')
    result = []
    for j, (line, level, title) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(lines)
        body = '\n'.join(lines[line + 1:end]).strip()
        visible = re.sub(r'(?ms)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1\s*$', '', body)
        tables, data = [], visible.splitlines()
        for k in range(1, len(data)):
            if '|' not in data[k] or '|' not in data[k - 1]:
                continue
            sep = _structure_columns(data[k])
            if sep and all(re.fullmatch(r':?-+:?', c) for c in sep):
                header = _structure_columns(data[k - 1])
                if len(sep) != len(header):
                    raise ValueError(f'{title}: 表格分隔行错误')
                count = 0
                for row in data[k + 1:]:
                    if not row.strip() or '|' not in row:
                        break
                    count += 1
                    if len(_structure_columns(row)) != len(header):
                        raise ValueError(f'{title}: 数据行列数错误')
                if count == 0:
                    raise ValueError(f'{title}: 空表')
                tables.append(header)
        result.append({'level': level, 'title': title, 'tables': tables,
                       'body': body, 'visible': visible, 'line': line + 1})
    return result


def _audit_document_structure(run_dir):
    root = Path(run_dir).resolve()
    def read(path):
        for parent in [path, *path.parents]:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError('结构审核拒绝符号链接')
        if root not in path.resolve().parents or not path.is_file():
            raise ValueError('结构审核文件缺失或路径越界')
        return path.read_text()
    try:
        contract = json.loads((STRUCTURE_PACKAGE / 'references/document-structure.json').read_text())
        request = json.loads(read(root / 'working/render_request.json'))
        binding = request['structure_bindings']
        list_keys = ['roles', 'surfaces', 'api_groups', 'tables', 'scenarios', 'flows']
        keys = {'project', 'special_topic', 'sources', *list_keys}
        if set(binding) != keys or set(binding['sources']) != keys - {'sources'}:
            raise ValueError('项目绑定键集合错误')
        for key in list_keys:
            values = binding[key]
            if (not isinstance(values, list) or not values or len(values) > 100
                    or not all(isinstance(v, str) and v.strip() and not re.search(r'[\r\n#|<>`]', v) for v in values)
                    or len(set(values)) != len(values)):
                raise ValueError('项目重复绑定非法: ' + key)
        if not all(isinstance(v, str) and v.strip() for v in binding['sources'].values()):
            raise ValueError('项目绑定缺来源')
        if {p.name for p in (root / 'design').glob('*.md')} != set(contract['documents']):
            raise ValueError('最终文件名集合不等于九份契约')
        errors = []
        for name, rules in contract['documents'].items():
            ref = STRUCTURE_PACKAGE / 'references/design' / name
            if hashlib.sha256(ref.read_bytes()).hexdigest() != contract['reference_sha256'][name]:
                raise ValueError('原参照指纹与结构契约不符: ' + name)
            source = {s['title']: s for s in _structure_outline(ref.read_text())}
            expected = []
            for rule in rules:
                prototype = source[rule['reference_heading']]
                values = binding[rule['repeat']] if 'repeat' in rule else [None]
                for index, item in enumerate(values, 1):
                    slots = {**binding, 'item': item, 'index': index,
                             'api_index': index + 2, 'api_end': len(binding['api_groups']) + 3}
                    expected.append({**prototype,
                        'title': rule.get('title', prototype['title']).format_map(slots),
                        'tables': rule.get('tables', prototype['tables']),
                        'form': rule.get('form'), 'fixed_labels': rule.get('labels', [])})
            actual = _structure_outline(read(root / 'design' / name))
            if [(s['level'], _structure_norm(s['title'])) for s in actual] != [(s['level'], _structure_norm(s['title'])) for s in expected]:
                errors.append(name + ': 标题树与原参照结构不符')
                continue
            for index, (got, want) in enumerate(zip(actual, expected)):
                where = name + ':' + str(got['line'])
                if got['tables'] != want['tables']:
                    errors.append(where + ': 表格列名/顺序/数量不符')
                group = index + 1 < len(actual) and actual[index + 1]['level'] > got['level']
                if got['level'] > 1 and not got['body'] and not group:
                    errors.append(where + ': 空章节')
                form = want['form']
                if form == 'tree' and not re.search(r'(?m)^```text\s*$', got['body']):
                    errors.append(where + ': 缺少 text 树')
                if form == 'bullet' and not re.search(r'(?m)^\s*[-*+]\s+\S', got['visible']):
                    errors.append(where + ': 缺少项目符号列表')
                if form in ('flow', 'ordered') and not re.search(r'(?m)^\s*1[.)]\s+\S', got['visible']):
                    errors.append(where + ': 缺少编号流程')
                if form == 'flow':
                    for label in ['触发与读取', '判断与动作', '状态与回读', '异常与人工决定']:
                        if not re.search(r'(?m)^\s*\d[.)]\s+\*\*' + label + r'[:：]\*\*', got['visible']):
                            errors.append(where + ': 缺流程标签 ' + label)
                for label in want['fixed_labels']:
                    if not re.search(r'(?m)^' + re.escape(label) + r'[:：]\s*$', got['visible']):
                        errors.append(where + ': 缺阶段标签 ' + label)
            if name in ('01-concept.md', '05-site-architecture.md'):
                section = next(s for s in actual if s['title'] == '角色边界')
                rows = [_structure_columns(line) for line in section['visible'].splitlines() if line.strip().startswith('|')]
                key = 'roles' if name.startswith('01') else 'surfaces'
                if [row[0] for row in rows[2:]] != binding[key]:
                    errors.append(name + ': 清单与项目角色/端绑定不一致')
        use_cases = {}
        for block in _structure_outline(read(root / 'design/02-use-cases.md')):
            if block['tables'] != [['编号', '用例', '主流程', '验收']]:
                continue
            lines = [line for line in block['visible'].splitlines() if line.lstrip().startswith('|')]
            for line in lines[2:]:
                record = _structure_columns(line)
                ident, title = record[0], record[1]
                if not re.fullmatch(r'UC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', ident) or ident in use_cases or not title:
                    errors.append('02: 用例编号或名称无效/重复')
                use_cases[ident] = title
        for title in binding['flows']:
            refs = re.findall(r'UC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', title)
            if not refs:
                errors.append('03: 业务流未引用用例')
            for ident in refs:
                if ident not in use_cases or use_cases[ident] not in _structure_norm(title):
                    errors.append('03: 用例编号/完整名称与 02 用例表错位: ' + ident)
        return errors
    except (OSError, KeyError, ValueError, TypeError, StopIteration) as exc:
        return ['结构审核未通过: ' + str(exc)]



def _audit_document_content(run_dir):
    """Independent literal replay from the frozen content slots and references.

    Do not import the producer. Receipt hashes alone cannot detect a producer
    that dropped or changed a business cell before signing its output.
    """
    try:
        root = Path(run_dir).resolve()
        request = json.loads(Path(contained_file(root, 'working/render_request.json')).read_text())
        if request.get('schema_version') != '2.0' or request.get('unresolved_questions') != []:
            raise ValueError('须使用问题清零的 2.0 内容请求')
        contract = json.loads((STRUCTURE_PACKAGE / 'references/document-structure.json').read_text())
        binding = request['structure_bindings']
        if set(request['documents']) != set(contract['documents']):
            raise ValueError('内容请求须恰有九份')
        errors = []
        for name, rules in contract['documents'].items():
            refs = {s['title']: s for s in _structure_outline(
                (STRUCTURE_PACKAGE / 'references/design' / name).read_text())}
            expected = []
            for rule in rules:
                prototype = refs[rule['reference_heading']]
                for i, item in enumerate(binding[rule['repeat']] if 'repeat' in rule else [None], 1):
                    title = rule.get('title', prototype['title']).format_map({**binding,
                        'item': item, 'index': i, 'api_index': i + 2,
                        'api_end': len(binding['api_groups']) + 3})
                    expected.append((title, rule.get('tables', prototype['tables']),
                                     rule.get('form'), rule.get('labels', [])))
            values = request['documents'][name]
            actual = _structure_outline(Path(contained_file(root, 'design/' + name)).read_text())
            if (not isinstance(values, dict) or set(values) != {s[0] for s in expected}
                    or [s['title'] for s in actual] != [s[0] for s in expected]):
                errors.append(name + ': 内容槽位与落盘章节不对应')
                continue
            for got, (title, headers, form, labels) in zip(actual, expected):
                value = values[title]
                keys = {'text'}
                blocks = []
                prose = value['text'].strip()
                if prose:
                    blocks.append(prose)
                if form in ('bullet', 'ordered'):
                    keys.add('items')
                    blocks.append('\n'.join(('- ' if form == 'bullet' else f'{i}. ')
                        + text.strip() for i, text in enumerate(value['items'], 1)))
                if form == 'tree':
                    keys.add('tree')
                    blocks.append('```text\n' + value['tree'].strip() + '\n```')
                if form == 'flow':
                    keys.add('steps')
                    step_labels = ['触发与读取', '判断与动作', '状态与回读', '异常与人工决定']
                    if set(value['steps']) != set(step_labels):
                        raise ValueError(name + ': 业务流槽位改变')
                    blocks.append('\n'.join(f'{i}. **{label}：**' + value['steps'][label].strip()
                                            for i, label in enumerate(step_labels, 1)))
                if labels:
                    keys.add('labels')
                    if set(value['labels']) != set(labels):
                        raise ValueError(name + ': 阶段标签槽位改变')
                    blocks.extend(label + '：\n\n' + value['labels'][label].strip() for label in labels)
                if headers:
                    keys.add('tables')
                    if len(value['tables']) != len(headers):
                        raise ValueError(name + ': 表格槽位数量改变')
                    for header, rows in zip(headers, value['tables']):
                        lines = ['| ' + ' | '.join(header) + ' |',
                                 '| ' + ' | '.join(['---'] * len(header)) + ' |']
                        if not rows:
                            raise ValueError(name + ': 缺数据行')
                        for row in rows:
                            if len(row) != len(header):
                                raise ValueError(name + ': 内容数据列数不符')
                            encoded = []
                            for cell in row:
                                # Literal per-character codec, separately implemented.
                                escapes = {'&': '&amp;', '<': '&lt;', '>': '&gt;',
                                           '\\': '&#92;', '|': '&#124;', '\n': '<br>'}
                                encoded.append(''.join(escapes.get(c, c) for c in cell.strip()))
                            lines.append('| ' + ' | '.join(encoded) + ' |')
                        blocks.append('\n'.join(lines))
                if set(value) != keys or got['body'] != '\n\n'.join(blocks):
                    errors.append(name + ' / ' + title + ': 落盘正文与冻结内容槽位不一致')
        return errors
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return ['内容回读未通过: ' + str(exc)]


def _audit_native_fields(run_dir):
    """Read actual Markdown cells and check native options independently."""
    import html
    errors = []
    try:
        root = Path(run_dir).resolve()
        request = json.loads(Path(contained_file(root, 'working/render_request.json')).read_text())
        document = Path(contained_file(root, 'design/03-data-model.md')).read_text()
        sections = {s['title']: s for s in _structure_outline(document)}
        allowed = ('text', 'textarea', 'number', 'datetime', 'boolean', 'select',
                   'status', 'member', 'file', 'linkto', 'lookup', 'rollup', 'formula', 'serialnumber')
        for table in request['structure_bindings']['tables']:
            section = sections[table]
            lines = section['body'].splitlines()
            header = next(i for i, line in enumerate(lines) if line.startswith('|'))
            rows = []
            for line in lines[header + 2:]:
                if not line.startswith('|'):
                    break
                rows.append([html.unescape(cell.replace('<br>', '\n')).strip()
                             for cell in line.strip()[1:-1].split('|')])
            if not rows:
                raise ValueError(table + ': 无原生字段行')
            for row in rows:
                if len(row) != 11:
                    raise ValueError(table + ': 字段行须为十一列')
                label = '03 / ' + table + ' / ' + row[1]
                native_type = row[2].strip('`')
                if native_type not in allowed:
                    errors.append(label + ': 未知 FieldVO 类型')
                    continue
                if native_type not in ('text', 'textarea', 'datetime', 'select'):
                    continue
                try:
                    value = json.loads(row[7].strip('`'))
                    if not isinstance(value, dict):
                        raise ValueError('options 不是对象')
                    if native_type == 'text' and value.get('type') != 'text':
                        raise ValueError('缺 text 原生选项')
                    if native_type == 'textarea' and type(value.get('html')) is not bool:
                        raise ValueError('缺 textarea 原生选项')
                    if native_type == 'datetime' and value.get('type') not in ('date', 'datetime'):
                        raise ValueError('缺 datetime 原生选项')
                    if native_type == 'select':
                        config = value.get('options', {})
                        if not isinstance(config, dict) or config.get('mode') != 'custom':
                            raise ValueError('select 固定选项须为 custom')
                        choices = config.get('items')
                        if not isinstance(choices, list) or len(choices) == 0:
                            raise ValueError('select 缺 items')
                        keys = []
                        for choice in choices:
                            if not isinstance(choice, dict):
                                raise ValueError('select item 不是对象')
                            if type(choice.get('key')) != int or not isinstance(choice.get('value'), str) or not choice['value'].strip():
                                raise ValueError('select 须有整数 item key 和非空 value')
                            keys.append(choice['key'])
                        if len(keys) != len(set(keys)):
                            raise ValueError('select item key 重复')
                except (ValueError, TypeError) as exc:
                    errors.append(label + ': ' + str(exc))
        return errors
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        return ['原生字段回读未通过: ' + str(exc)]


def f_schema_conformance(art, spec, ctx):
    """字段集**与声明类型**双验。

    Gate-ID: audit.family.schema_conformance
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    只验键在不在时，`amount: "10"`（字符串冒充数值）一路绿灯到汇总才炸，
    且炸在别处。IR 的 operation 最低族表写的是「字段集与类型符声明」，故 `field_types` 缺失
    fail-closed，不退化成只验键名。
    """
    p = spec["predicate"]
    required = set(p["required_fields"])
    types = p.get("field_types")
    if types is None:
        return False, ("schema_conformance 未声明字段类型（field_types）"
                       "——类型漂移无声通过")
    unspec = required - set(types)
    if unspec:
        return False, f"字段 {sorted(unspec)} 只声明了存在、未声明类型"
    unknown = [t for t in types.values() if t not in _TYPES]
    if unknown:
        return False, f"未知类型名 {sorted(set(unknown))}（可用 {sorted(_TYPES)}）"
    _touch_rows(art, p["collection"], sorted(required))
    bad = []
    for i, it in enumerate(_get(art, p["collection"])):
        absent = required - set(it.keys())
        if absent:
            bad.append(f"[{i}]缺{sorted(absent)}")
            continue
        for fld, tname in types.items():
            if fld not in it:
                continue
            exp = _TYPES[tname]
            v = it[fld]
            # bool 是 int 的子类，声明 int 时不能把 True 当 1 放过
            if tname in ("int", "float", "number") and isinstance(v, bool):
                bad.append(f"[{i}].{fld}=bool 冒充 {tname}")
            elif not isinstance(v, exp):
                bad.append(f"[{i}].{fld}={type(v).__name__} 应 {tname}")
    if p.get("reference_structure"):
        bad.extend(_audit_document_structure(ctx["run_dir"]))
    if p.get("native_field_options"):
        bad.extend(_audit_native_fields(ctx["run_dir"]))
    return not bad, "; ".join(bad[:5])


def f_source_receipt(art, spec, ctx):
    """核验取源回执必填键。

    Gate-ID: audit.family.source_receipt
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    _touch(art, *p["required_keys"])
    missing = [k for k in p["required_keys"] if k not in art or art[k] in (None, "")]
    return not missing, f"回执缺字段 {missing}" if missing else ""


def f_output_subset_input(art, spec, ctx):
    """出集 ⊆ 入集，**按多重集**，且保留行内容不得被改。

    Gate-ID: audit.family.output_subset_input
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    两处此前失守：
    1. set 化把重数抹掉——把一条保留行复制一份，出集仍是入集子集，全绿。
    2. 只比 id——把保留行的某个非谓词字段改掉（改 sku 而 country 仍合规），
       子集成立、谓词重跑成立、删除计数成立，三条最低族全过。filter 的语义
       是「筛选」，保留行原样通过；改内容的已经不是 filter 了。
    """
    p = spec["predicate"]
    out = _multiset(_id_set(art, p["output"]))
    inp = _multiset(_upstream(ctx, p["input"]))
    extra = _ms_diff(out, inp)
    if extra:
        return False, f"出集凭空多出 {_ms_fmt(extra)}（含重数）"
    # 行内容保全：按 id 逐行比对整行载荷
    up = _resolve_artifact(ctx, p["input"])
    icol, ocol = p["input"].get("collection"), p["output"].get("collection")
    if icol and ocol:
        idf = p["output"].get("id_field", p["input"].get("id_field", "id"))
        drop = set(p.get("allow_dropped_fields", []))
        src = {r[idf]: r for r in _get(up, icol)}
        bad = []
        for r in _get(art, ocol):
            _touch_rows(art, ocol, [k for k in r if k not in drop])
            o = src.get(r[idf])
            if o is None:
                continue  # 多出项已由上面的多重集差报出
            want = {k: v for k, v in o.items() if k not in drop}
            got = {k: v for k, v in r.items() if k not in drop}
            if got != want:
                diff = sorted(set(want) | set(got))
                diff = [k for k in diff if want.get(k) != got.get(k)]
                bad.append(f"{r[idf]}:保留行被改 {diff}")
        if bad:
            return False, "; ".join(bad[:5])
    return True, ""


def f_excluded_count_set(art, spec, ctx):
    """被删项落账。清单式优先；仅有计数时退到计数配平式。

    Gate-ID: audit.family.excluded_count_set
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    计数式：入集数 = 出集数 + 各删除计数之和。E3（静默丢单、删除计数未变）
    正是靠它检出——出集少一单而账本删除计数不动，等式立刻破。

    按多重集算：set 化后「删一条、又把另一条复制一份」两错相消，等式恒真。
    """
    p = spec["predicate"]
    inp = _multiset(_upstream(ctx, p["input"]))
    out = _multiset(_id_set(art, p["output"]))
    n_in = sum(inp.values())
    n_out = sum(out.values())
    if p.get("excluded_ids"):
        _touch_members(art, p["excluded_ids"])
        declared = _multiset(_get(art, p["excluded_ids"]))
        actual = _ms_diff(inp, out)
        if actual != declared:
            return False, (f"实删 {_ms_fmt(actual)} / 账本记删 {_ms_fmt(declared)}")
        return True, ""
    parts = [_get(art, c) for c in p["excluded_counts"]]
    total = n_out + sum(parts)
    return total == n_in, f"出集 {n_out} + 删除 {parts} = {total} / 入集 {n_in}"


def f_predicate_replay(art, spec, ctx):
    """重跑保留谓词。

    Gate-ID: audit.family.predicate_replay
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    两形态：账本逐元素记了保留裁决（decision_field）时与裁决比对；
    只落保留侧（过滤后集合）时，验每个保留项都满足谓词。
    """
    p = spec["predicate"]
    rule, bad = p["rule"], []
    idf = p.get("id_field", "id")
    _touch_rows(art, p["collection"], [rule["field"], p.get("decision_field"), idf])
    for it in _get(art, p["collection"]):
        expect = _test(it[rule["field"]], rule)
        if "decision_field" in p:
            actual = it[p["decision_field"]]
            if actual != expect:
                bad.append(f"{it.get(idf)}:记{actual}/应{expect}")
        elif not expect:
            bad.append(f"{it.get(idf)}:{rule['field']}={it[rule['field']]} 不满足保留谓词")
    return not bad, "; ".join(bad[:5])


def f_key_row_preservation(art, spec, ctx):
    """键集**与行数**都不变。族名写的就是 key/row，两样都要。

    Gate-ID: audit.family.key_row_preservation
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    set 比较只管键集：把一行复制一份，键集不变、行数变了，全绿。IR 的 operation 最低族表中该族
    挡的是「元素丢失或增生」——增生正是重数变化，用 set 恰好看不见。
    """
    p = spec["predicate"]
    src = _multiset(_upstream(ctx, p["input"]))
    dst = _multiset(_id_set(art, p["output"]))
    if src != dst:
        lost, extra = _ms_diff(src, dst), _ms_diff(dst, src)
        return False, f"缺{_ms_fmt(lost)} 多{_ms_fmt(extra)}"
    return True, ""


def f_field_function_replay(art, spec, ctx):
    """逐元素重算映射函数：声明式查表 {源字段值: 目标字段值}。

    Gate-ID: audit.family.field_function_replay
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    table, default = p["mapping"], p.get("default")
    idf = p.get("id_field", "id")
    _touch_rows(art, p["collection"], [p["source_field"], p["target_field"], idf])
    bad = []
    for it in _get(art, p["collection"]):
        src_v = it[p["source_field"]]
        want = table.get(str(src_v), default)
        got = it[p["target_field"]]
        if got != want:
            bad.append(f"{it.get(idf)}:{src_v}→记{got}/应{want}")
    return not bad, "; ".join(bad[:5])


def f_key_coverage(art, spec, ctx):
    """核验左键均进入连接结果或未匹配清单。

    Gate-ID: audit.family.key_coverage
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    left = set(_upstream(ctx, p["input"]))
    joined = set(_id_set(art, p["output"]))
    if p.get("unmatched_ids"):
        _touch_members(art, p["unmatched_ids"])
        unmatched = set(_get(art, p["unmatched_ids"]))
    else:
        unmatched = set()
    uncovered = left - joined - unmatched
    return not uncovered, f"左集未覆盖也未登记未匹配 {sorted(uncovered)}" if uncovered else ""


def f_cardinality(art, spec, ctx):
    """连接基数符声明。未知 expect **fail-closed**。

    Gate-ID: audit.family.cardinality
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    此前 `return True` 兜底：`expect` 写错一个字（"1:1"、"onetoone"）或写了
    尚未实现的形态，本条恒真——一条永远为真的断言在报告上与真验过无法区分。
    """
    p = spec["predicate"]
    _touch_rows(art, p["collection"], [p["key_field"]])
    keys = [it[p["key_field"]] for it in _get(art, p["collection"])]
    exp = p["expect"]
    if exp == "one_to_one":
        cnt = _multiset(keys)
        dup = {k: n for k, n in cnt.items() if n > 1}
        return not dup, f"应一对一但键重复 {_ms_fmt(dup)}" if dup else ""
    if exp == "one_to_many":
        # 一对多允许右侧放大，但左键必须全部出现，且放大倍数须落账
        maxn = p.get("max_per_key")
        if maxn is None:
            return False, "one_to_many 未声明 max_per_key——放大无上界等于不验基数"
        cnt = _multiset(keys)
        over = {k: n for k, n in cnt.items() if n > maxn}
        return not over, f"超出声明上界 {maxn}: {_ms_fmt(over)}" if over else ""
    return False, (f"未知的 cardinality expect「{exp}」"
                   f"（可用 one_to_one / one_to_many）——不认识即拒，不放行")


def f_unmatched_set(art, spec, ctx):
    """两侧未匹配项清单落账，且**与按键重算的应未匹配集逐项相等**。

    Gate-ID: audit.family.unmatched_set
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    三层，每层挡一种此前放行的形态：
    1. 字段在不在——只答了「登记了没有」。
    2. 与已连接键不相交、且都出自左集——挡「把已连接的键塞进未匹配清单」。
    3. **按左右两侧的连接键重算应未匹配集，与账本记的多重集全等**——挡反向：
       把一个右表**确实有**匹配的键从 joined 里挪进 unmatched_ids。此时
       key_coverage 仍覆盖它（未匹配也算覆盖）、cardinality 只看 joined、
       第 2 层的不相交与左集成员资格全部成立，joined_value_replay 只管
       还留在 joined 里的行——一条被谎报未匹配的已匹配行，前面每一条都放行。

    第 3 层要求声明 `right`（右表）。缺它时 fail-closed：不重算就只是登记核对，
    而登记核对无法区分「真没匹配上」与「有匹配但被写成没有」。
    """
    p = spec["predicate"]
    fld = p["field"]
    if fld not in art:
        return False, f"未登记未匹配集合字段 {fld}"
    _touch_members(art, fld)
    unmatched = _multiset(_get(art, fld))
    if p.get("output"):
        joined = _multiset(_id_set(art, p["output"]))
        both = {k: n for k, n in unmatched.items() if k in joined}
        if both:
            return False, (f"登记为未匹配、却出现在已连接集里 {_ms_fmt(both)}"
                           "——未匹配清单须与已连接键不相交")
    if p.get("input"):
        left = _multiset(_upstream(ctx, p["input"]))
        alien = {k: n for k, n in unmatched.items() if k not in left}
        if alien:
            return False, f"未匹配清单里有不在左集的键 {_ms_fmt(alien)}"
    if not p.get("input") or not p.get("right"):
        return False, ("unmatched_set 须同时声明 input（左集）与 right（右表）"
                       "以重算应未匹配集——只核对登记无法识别「有匹配却记成未匹配」")
    right = _resolve_artifact(ctx, p["right"])
    rkey = p["right"].get("key_field", "id")
    rkeys = {r[rkey] for r in _get(right, p["right"]["collection"])}
    # 连接键与被登记的标识可以不是同一个字段：左表按 sku 连接、未匹配名单记 id。
    left_art = _resolve_artifact(ctx, p["input"])
    jk = p.get("join_key")
    idf = p["input"].get("id_field", "id")
    if jk:
        expect = _multiset([r[idf] for r in _get(left_art, p["input"]["collection"])
                            if r[jk] not in rkeys])
    else:
        expect = _multiset([k for k in _upstream(ctx, p["input"]) if k not in rkeys])
    if expect != unmatched:
        lost, extra = _ms_diff(expect, unmatched), _ms_diff(unmatched, expect)
        return False, (f"应未匹配集重算不符：账本漏记 {_ms_fmt(lost)}；"
                       f"账本多记（右表其实有匹配）{_ms_fmt(extra)}")
    return True, ""


def f_joined_value_replay(art, spec, ctx):
    """连接后取值重算：逐键回右表查值，与产物落的值比对。

    Gate-ID: audit.family.joined_value_replay
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    key_coverage + cardinality + unmatched_set 三条合起来只证明**键形状**对：
    左键都被覆盖、没有放大、未匹配都登记了。把两个已连接键的右表载荷互换，
    键形状一字未动，三条全绿——「连对了行」与「取对了值」正交。
    """
    p = spec["predicate"]
    right = _resolve_artifact(ctx, p["right"])
    rkey = p["right"].get("key_field", "id")
    table = {r[rkey]: r for r in _get(right, p["right"]["collection"])}
    idf = p.get("key_field", "id")
    jk = p.get("join_key", idf)
    _touch_rows(art, p["collection"], [idf, jk] + list(p["value_fields"]))
    bad = []
    for it in _get(art, p["collection"]):
        k = it[jk]
        r = table.get(k)
        if r is None:
            bad.append(f"{it[idf]}:右表无键 {k} 却出现在已连接集里")
            continue
        for out_f, right_f in p["value_fields"].items():
            if it.get(out_f) != r.get(right_f):
                bad.append(f"{it[idf]}.{out_f}=记{it.get(out_f)}/右表{r.get(right_f)}")
    return not bad, "; ".join(bad[:5])


def f_union_completeness(art, spec, ctx):
    """各桶并集 = 入集。

    Gate-ID: audit.family.union_completeness
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    桶两种给法：显式 id 清单路径（buckets），或按字段分组（output）。
    入集可带 filter——上游漏斗只把 continue 项放行时，入集是上游的子集。
    """
    p = spec["predicate"]
    inp = set(_upstream(ctx, p["input"]))
    if p.get("buckets"):
        union = set()
        for b in p["buckets"]:
            union |= set(_get(art, b))
    else:
        union = set(_id_set(art, p["output"]))
    if union != inp:
        return False, f"并集缺{sorted(inp-union)} 多{sorted(union-inp)}"
    return True, ""


def f_pairwise_disjoint(art, spec, ctx):
    """桶间两两不交。显式清单式，或按字段分组式（同 id 重复出现即相交）。

    Gate-ID: audit.family.pairwise_disjoint
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    if p.get("buckets"):
        seen, dup = set(), set()
        for b in p["buckets"]:
            s = list(_get(art, b) or [])
            for x in s:
                if x in seen:
                    dup.add(x)
                seen.add(x)
        return not dup, f"跨桶重复 {sorted(dup)}" if dup else ""
    ids = _id_set(art, p["output"])
    dup = {x for x in ids if ids.count(x) > 1}
    return not dup, f"同一元素落多桶 {sorted(dup)}" if dup else ""


def f_assignment_rule_replay(art, spec, ctx):
    """逐元素按声明的分桶函数重算，与账本裁决值比对。

    Gate-ID: audit.family.assignment_rule_replay
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    partition 的第三条强断言：并集完整 + 两两互斥都恒真时，分桶规则本身
    仍可整体坏死（08-05 TODAY_START 真 bug 即此形态）。

    两种谓词形态：
      * 段内式 {collection, bucket_field, rule} —— 分桶函数是本段字段的纯函数。
      * 重建式 {lists, sources} —— 分桶依据在上游各段的裁决里（漏斗「首个拦截
        者得」型），按各桶声明的上游来源集重建成员，与账本自报清单比对。
        缺了它，计数对、和对、互斥对、可枚举对，而两个桶的成员互换仍全绿。
    """
    p = spec["predicate"]
    if "sources" in p:
        bad = []
        for bucket, list_path in p["lists"].items():
            claimed = _get(art, list_path)
            if claimed is None:
                bad.append(f"{bucket}:清单为 null")
                continue
            _touch_members(art, list_path)
            rebuilt = set()
            for src in p["sources"][bucket]:
                rebuilt |= set(_upstream(ctx, src))
            if set(claimed) != rebuilt:
                bad.append(f"{bucket}:自报{sorted(set(claimed)-rebuilt)}多/"
                           f"{sorted(rebuilt-set(claimed))}缺")
        return not bad, "; ".join(bad[:6])
    idf = p.get("id_field", "id")
    _touch_rows(art, p["collection"],
                [p["bucket_field"], idf, p["rule"].get("field"),
                 p["rule"].get("base_field")])
    bad = []
    for it in _get(art, p["collection"]):
        got = it[p["bucket_field"]]
        want = _eval_rule(it, p["rule"], art)
        if got != want:
            bad.append(f"{it.get(idf)}:记{got}/应{want}")
    return not bad, "; ".join(bad[:5])


def f_detail_recomputation(art, spec, ctx):
    """逐桶重算清单长度与声明计数。

    Gate-ID: audit.family.detail_recomputation
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    bad = []
    for bucket, cnt_path in p["counts"].items():
        lst = _get(art, p["lists"][bucket])
        if lst is None:
            bad.append(f"{bucket}:清单为 null")
            continue
        counted = _get(art, cnt_path)
        if len(lst) != counted:
            bad.append(f"{bucket}:清单{len(lst)}/计数{counted}")
    return not bad, "; ".join(bad)


def f_total_reconciliation(art, spec, ctx):
    """核验分项和与输入或声明总量相等。

    Gate-ID: audit.family.total_reconciliation
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    total = sum(_get(art, c) for c in p["parts"])
    if p.get("input"):
        want = len(_upstream(ctx, p["input"]))
    else:
        want = _get(art, p["declared_total"])
    return total == want, f"分项和 {total} / 应 {want}"


def f_each_bucket_independently_enumerable(art, spec, ctx):
    """每个桶必须有独立可追踪成员清单，任何一桶不得由减法得出。

    Gate-ID: audit.family.each_bucket_independently_enumerable
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    挡 E9：正常桶 = 总数 − 其余六类反推，守恒恒真且不可追踪。
    机械判据：每桶清单非 null、清单长 = 该桶计数、全桶成员并集 = 声明总量。
    """
    p = spec["predicate"]
    missing, all_members = [], set()
    for bucket, list_path in p["lists"].items():
        try:
            members = _get(art, list_path)
        except (KeyError, TypeError):
            missing.append(f"{bucket}:无独立清单")
            continue
        if members is None:
            missing.append(f"{bucket}:清单为 null（疑守恒反推）")
            continue
        cnt = _get(art, p["counts"][bucket])
        if len(members) != cnt:
            missing.append(f"{bucket}:清单{len(members)}≠计数{cnt}")
        if p.get("input"):
            _touch_members(art, list_path)
        all_members |= set(members)
    if p.get("input"):
        want = set(_upstream(ctx, p["input"]))
        if all_members != want:
            missing.append(f"成员并集缺{sorted(want-all_members)} 多{sorted(all_members-want)}")
    return not missing, "; ".join(missing[:6])


def _compare_paths(art, p, ctx):
    """`compare_paths`：一条断言逐路径钉住成品件与上游的多条对应关系。

    Gate-ID: audit.compare_paths
    Obligations: RENDER.COMPARE_PATHS
    判据源 `contract_ir.md §6.1`。

    形状是**每项显式两端**——`{"output": <成品件路径>, "input": {"stage","path"}}`，
    比对是该路径上的精确相等，覆盖按 `_touch_deep(output)` 记。三条都不能松：

    * 两端都要显式：只给 output 让解释器"按同名去上游找"，或只给 input 让它
      "落到同名输出字段"，都是把对应关系交给命名巧合。`lists_public.<桶>` 与
      `lists.<桶>` 名字本来就不同，一旦某个桶在上游改名，同名推断会安静地
      配错一对，而两边照样各自存在、比对照样"成立"。
    * 精确相等而非计数相等：清单成员换成一个等长的错号时，长度、计数全不动。
      按 len 比的那种口径在这一形态上恒真——「清单长度相等」不约束成员是谁。
    * 空表拒绝：`compare_paths: []` 逐项遍历零次、返回 True，是一条恒真断言。
      恒真断言登记在册比不登记更坏——它占着覆盖名额且永远绿。

    与 `compare_map` 的分工：后者是单路径整块比对，本函数是多路径。把七条链
    拆成七条断言也能比，但那样「成品件的哪些字段直连上游」这件事散落在七个
    id 里，加一个字段忘了加断言无人可查；合成一条则该断言自身就是链表。
    """
    items = p["compare_paths"]
    if not isinstance(items, list) or not items:
        return False, "compare_paths 为空或非列表——零项遍历恒真，不构成对账"
    bad = []
    for i, it in enumerate(items):
        out_path = it.get("output")
        ref = it.get("input")
        if not out_path or not isinstance(ref, dict) or not ref.get("stage") or not ref.get("path"):
            return False, (f"compare_paths[{i}] 须同时显式声明 output 与 "
                           f"input.{{stage,path}}（契约错）")
        _touch_deep(art, out_path)
        try:
            got = _get(art, out_path)
        except (KeyError, TypeError) as e:
            bad.append(f"{out_path}: 成品件无此路径（{type(e).__name__}）")
            continue
        up = _resolve_artifact(ctx, ref)
        try:
            want = _get(up, ref["path"])
        except (KeyError, TypeError) as e:
            bad.append(f"{out_path}: 上游 {ref['stage']}.{ref['path']} 无此路径"
                       f"（{type(e).__name__}）")
            continue
        if got != want:
            bad.append(f"{out_path}: 成品件 {got!r} / 上游 "
                       f"{ref['stage']}.{ref['path']} {want!r}")
    return not bad, ("; ".join(bad[:6]) if bad
                     else f"{len(items)} 条直连路径逐路径相等")


def f_row_column_sheet_reconciliation(art, spec, ctx):
    """成品件与数据源对账。支持逐路径直连、整块字典比对、标量/清单行数对账。

    Gate-ID: audit.family.row_column_sheet_reconciliation
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    # 用 `in` 不用 `get`：`compare_paths: []` 是假值，用 get 判会直接短路到下面的
    # compare_map / rendered_rows 分支，空表那条判定于是永远走不到——而空表正是
    # 这里最该拒的一种写法。声明了就得按它判，声明成空表是错，不是没声明。
    if "compare_paths" in p:
        if p.get("compare_map") or p.get("rendered_rows"):
            return False, ("compare_paths 与 compare_map/rendered_rows 同时声明"
                           "——同一条断言两种口径，判据取哪个由实现顺序决定（契约错）")
        passed, detail = _compare_paths(art, p, ctx)
        if p.get('content_readback'):
            errors = _audit_document_content(ctx['run_dir'])
            return passed and not errors, '; '.join([detail, *errors])
        return passed, detail
    if p.get("compare_map"):
        _touch_deep(art, p["compare_map"])
        got = _get(art, p["compare_map"])
        up = _resolve_artifact(ctx, p["input"])
        want = _get(up, p["input"]["path"])
        if got != want:
            diff = {k: (got.get(k), want.get(k)) for k in set(got) | set(want)
                    if got.get(k) != want.get(k)}
            return False, f"成品件与数据源不符 {diff}"
        return True, ""
    got = _get(art, p["rendered_rows"])
    want = len(_upstream(ctx, p["input"])) if p.get("input") else _get(art, p["declared_rows"])
    if isinstance(got, list):
        got = len(got)
    if isinstance(want, list):
        want = len(want)
    return got == want, f"成品件 {got} 行 / 数据源 {want} 行"


def f_summary_reconciliation(art, spec, ctx):
    """核验成品汇总清单与计数逐桶一致。

    Gate-ID: audit.family.summary_reconciliation
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    return f_detail_recomputation(art, spec, ctx)


def _leaf_paths(obj, prefix=""):
    """枚举产物的输出字段面。

    列表里的字典按 `coll[].field` 记一条（逐行同构，不逐行展开）；
    标量与嵌套字典按点号路径记。这就是「这份成品件对外声称了哪些东西」。
    """
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _leaf_paths(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        fields = set()
        for it in obj:
            if isinstance(it, dict):
                fields |= set(it.keys())
        if fields:
            for f in sorted(fields):
                out.append(f"{prefix}[].{f}")
        else:
            out.append(f"{prefix}[]")
    else:
        out.append(prefix)
    return out


def _pred_strings(obj):
    """把一条谓词里出现的所有字符串收集起来。**只用于诊断，不作覆盖证据。**

    曾被用作「这条断言碰过哪些字段」——那是把「字段名在谓词里出现过」当成
    「字段被验过」。往任意一条断言里塞 `"note": "n_claimed"`，n_claimed 即被
    标成已覆盖，而没有任何求值器读过它。这与 M8 已经拒过的诱饵字面量同类。
    覆盖只认解释器**实际读过**的路径，见 _READS。
    """
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            out |= _pred_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _pred_strings(v)
    elif isinstance(obj, str):
        out.add(obj)
    return out


def _covers(reads, deep, path):
    """判一条输出字段路径是否被实际读取覆盖。

    三条通路，每条都要求解释器真的读过东西：
    1. 精确读过该路径；
    2. 某次**整块比对**（deep）的路径是它的祖先——整块相等蕴含每片叶子相等；
    3. 行内字段 `coll[].f`：只认 `_touch_rows` 登记的那一条。

    第 3 条不走祖先前缀：`_get(art,"rows")` 只是把整个集合取出来，取出来之后
    比了哪几个字段由各 family 自己决定——多数只比 id。让 `rows` 覆盖
    `rows[].fee` 等于把「读过这张表」当成「验过表里每一列」，改 fee 全绿。
    跨 `[]` 的祖先前缀只在 deep（整块相等）时成立。
    """
    if path in reads:
        return True
    for d in deep:
        if path == d or path.startswith(d + ".") or path.startswith(d + "["):
            return True
    if "[]." in path:
        return False
    # 纯字典嵌套：读过 `summary.total` 不覆盖 `summary`，反向也不覆盖——
    # 只有整块比对（deep）才向下传递。此处只认精确匹配，已在上面判过。
    return False


def f_output_field_coverage(art, spec, ctx):
    """成品件的每个输出字段都要被某条断言**实际读过**。

    Gate-ID: audit.family.output_field_coverage
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    守恒反解总禁则的同类缺口：M9 只验「族齐」，不验「族覆盖了产物实际声称的东西」。
    最低族全登记、全 PASS，而某个字段（比如成品件自报的 `n_claimed`）
    根本没有任何求值器碰过——把它改成 999，全绿。没有断言读过的字段
    等于没有被审过，「全 PASS」在它上面不成立任何结论。

    证据只取解释器求值时记录的读取路径（ctx["covered_fields"]），不取谓词
    字面量。后者可以伪造：往任意一条断言塞 `"note": "n_claimed"`，字段名就
    "出现过"了，而没有任何代码读它——与 M8 已经拒过的诱饵字面量同类。

    豁免必须逐条写理由（`exempt: {字段: 理由}`）：允许留白，但留白要留名。
    """
    p = spec["predicate"]
    exempt = p.get("exempt", {})
    if isinstance(exempt, list):
        return False, "exempt 须写成 {字段: 理由}，只给字段名不构成豁免理由"
    bad_ex = [k for k, v in exempt.items() if not (isinstance(v, str) and v.strip())]
    if bad_ex:
        return False, f"豁免字段 {sorted(bad_ex)} 未写理由"

    cov = ctx.get("covered_fields")
    if cov is None:
        return False, "解释器未提供读取记录——无读取记录即无覆盖证据"
    reads, deep = cov
    uncovered = [path for path in _leaf_paths(art)
                 if path not in exempt and not _covers(reads, deep, path)]
    if uncovered:
        return False, (f"成品件字段 {sorted(uncovered)} 无任何断言读过"
                       "——未被读过的字段不因「其余全 PASS」而成立")
    return True, ""


def f_artifact_hash(art, spec, ctx):
    """核验落盘件内容 hash 与账本声明一致。

    Gate-ID: audit.family.artifact_hash
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    path = contained_file(ctx["run_dir"], p["artifact_path"])
    if not os.path.exists(path):
        return False, f"交接物不存在: {p['artifact_path']}"
    got = sha256_file(path)
    want = _get(art, p["declared_hash"])
    return got == want, f"实算 {got} / 账本记 {want}"


def f_receiver_receipt(art, spec, ctx):
    """核验接收方回执必填键。

    Gate-ID: audit.family.receiver_receipt
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    _touch(art, *p["required_keys"])
    missing = [k for k in p["required_keys"] if not art.get(k)]
    return not missing, f"接收回执缺 {missing}" if missing else ""


def f_source_readback(art, spec, ctx):
    """T2：按键回源重读，与账本观测值逐条比对。

    Gate-ID: audit.family.source_readback
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    这是段内断言必然失明的那一面（E10 形态）：观测抄错而下游裁决与错误观测
    自洽，只有重读源能抓。源不可机械重读时本族标 UNVERIFIED，不得改判。
    """
    p = spec["predicate"]
    table = _source_map(ctx, p["source"])
    missing_as = p["source"].get("missing_as")
    norm = p["source"].get("normalize")
    idf = p.get("key_field", "id")
    _touch_rows(art, p["collection"],
                [idf, p.get("id_field"), p["observed_field"]])
    bad = []
    for it in _get(art, p["collection"]):
        raw = table.get(it[idf], missing_as)
        want = _normalize(raw, norm) if raw is not None else missing_as
        got = it[p["observed_field"]]
        if got != want:
            bad.append(f"{it.get(p.get('id_field', 'id'))}:账本记{got}/源为{want}")
    return not bad, "; ".join(bad[:5])


def f_source_row_match(art, spec, ctx):
    """T2：整表行多重集比对，抓静默截断与整行篡改。

    Gate-ID: audit.family.source_row_match
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    rows = _pick_section(_read_markdown_tables(ctx["source"]), p["source"]["section"])
    cols = p["source"]["columns"]
    src = sorted(tuple(r[c] if c < len(r) else "" for c in cols) for r in rows)
    _touch_rows(art, p["collection"], p["fields"])
    led = sorted(tuple(str(it[f]) for f in p["fields"]) for it in _get(art, p["collection"]))
    if src != led:
        only_src = [x for x in src if x not in led]
        only_led = [x for x in led if x not in src]
        return False, f"源独有{only_src[:3]} 账本独有{only_led[:3]}"
    return True, ""


def f_existence(art, spec, ctx):
    """弱断言 · 声明路径存在且值非 null。

    Gate-ID: audit.family.existence
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    p = spec["predicate"]
    path = p["path"]
    try:
        value = _get(art, path)
    except (KeyError, TypeError):
        return False, f"{path} 不存在"
    return value is not None, (f"{path} 存在（弱断言，仅 WARN）" if value is not None
                               else f"{path} 为 null")


def f_nonzero_rows(art, spec, ctx):
    """弱断言 · 集合非空。

    Gate-ID: audit.family.nonzero_rows
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    IR 的弱族表把它列进弱族：非空只证明产物没空手而归，不证明里面的东西对。
    故它恒 WARN、不满足段闸。但**必须真跑**——空集时判 FAIL 而不是 WARN：
    「弱」说的是这条断言的结论弱，不是它可以不判。声明了却判不出结果，
    与没声明的区别只在登记表上。
    """
    p = spec["predicate"]
    rows = _get(art, p["collection"])
    n = len(rows)
    return n > 0, (f"{p['collection']} 空集" if n == 0 else f"{n} 行（弱断言，仅 WARN）")


def f_file_present(art, spec, ctx):
    """弱断言 · 声明的文件真的落在 run_dir 里。

    Gate-ID: audit.family.file_present
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。

    同 nonzero_rows：结论弱（文件出生 ≠ 文件正确），但判定照跑，
    文件不在即 FAIL。
    """
    p = spec["predicate"]
    rel = p["path"]
    full = os.path.join(ctx["run_dir"], rel)
    ok = os.path.isfile(full)
    return ok, (f"{rel} 在（弱断言，仅 WARN）" if ok else f"{rel} 不在 run_dir 内")


FAMILIES = {
    "source_receipt": f_source_receipt,
    "schema_conformance": f_schema_conformance,
    "count_hash": f_count_hash,
    "output_subset_input": f_output_subset_input,
    "predicate_replay": f_predicate_replay,
    "excluded_count_set": f_excluded_count_set,
    "key_row_preservation": f_key_row_preservation,
    "field_function_replay": f_field_function_replay,
    "key_coverage": f_key_coverage,
    "cardinality": f_cardinality,
    "unmatched_set": f_unmatched_set,
    "union_completeness": f_union_completeness,
    "pairwise_disjoint": f_pairwise_disjoint,
    "assignment_rule_replay": f_assignment_rule_replay,
    "detail_recomputation": f_detail_recomputation,
    "total_reconciliation": f_total_reconciliation,
    "each_bucket_independently_enumerable": f_each_bucket_independently_enumerable,
    "row_column_sheet_reconciliation": f_row_column_sheet_reconciliation,
    "summary_reconciliation": f_summary_reconciliation,
    "artifact_hash": f_artifact_hash,
    "receiver_receipt": f_receiver_receipt,
    "joined_value_replay": f_joined_value_replay,
    "output_field_coverage": f_output_field_coverage,
    "source_readback": f_source_readback,
    "source_row_match": f_source_row_match,
    "existence": f_existence,
    "nonzero_rows": f_nonzero_rows,
    "file_present": f_file_present,
}


# ---------------------------------------------------------------- 主流程

def run_audit(run_dir, contract, ir, stages_filter, source, rep):
    """按契约逐段逐 operation 求值。

    Gate-ID: audit.run
    Obligations: CONTRACT.DATA, FAMILY.TIER, MANIFEST.SCHEMA, AUDIT.EXIT_CODES
    判据源：`contract_ir.md §6`（assertions schema）、`contract_ir.md §7`
    （manifest schema）、`contract_ir.md §8.0`（family↔tier 双向预检，排在
    T2 短路之前）、`contract_ir.md §8.1`（退出码三分）。
    """
    if not isinstance(contract, dict) or not isinstance(contract.get("stages"), list) or not contract["stages"]:
        raise ValueError("[CAUSE:AUDIT.CONTRACT.EMPTY] 契约须有非空 stages")
    stage_names = [st.get("stage") for st in contract["stages"]]
    if any(not isinstance(name, str) or not name for name in stage_names):
        raise ValueError("[CAUSE:AUDIT.CONTRACT.STAGE_NAME_EMPTY] stage 名须为非空字符串")
    duplicate_stages = sorted({name for name in stage_names
                               if stage_names.count(name) > 1})
    if duplicate_stages:
        raise ValueError("[CAUSE:AUDIT.CONTRACT.STAGE_NAME_DUPLICATE] "
                         f"stage 名重复 {duplicate_stages}")
    unknown = stages_filter - set(stage_names)
    if unknown:
        raise ValueError(f"[CAUSE:AUDIT.STAGE.UNKNOWN] 未声明 stage: {sorted(unknown)}")
    for st in contract["stages"]:
        if not isinstance(st.get("operations"), list) or not st["operations"]:
            raise ValueError(f"[CAUSE:AUDIT.CONTRACT.EMPTY] {st['stage']} 缺 operations")
        for op in st["operations"]:
            if not isinstance(op.get("assertions"), list) or not op["assertions"]:
                raise ValueError(f"[CAUSE:AUDIT.CONTRACT.EMPTY] {st['stage']} 缺 assertions")
    assertion_ids = [a.get("id") for st in contract.get("stages", [])
                     for op in st.get("operations", [])
                     for a in op.get("assertions", [])]
    if any(not isinstance(aid, str) or not aid for aid in assertion_ids):
        raise ValueError("[CAUSE:AUDIT.CONTRACT.ASSERTION_ID_EMPTY] "
                         "断言 id 须为非空字符串")
    duplicate_ids = sorted({aid for aid in assertion_ids
                            if assertion_ids.count(aid) > 1})
    if duplicate_ids:
        raise ValueError("[CAUSE:AUDIT.CONTRACT.ASSERTION_ID_DUPLICATE] "
                         f"断言 id 重复 {duplicate_ids}")

    weak = set(ir["weak_families"]["members"])
    t2_only = set(ir["tier2_families"]["members"])
    artifacts = {}
    # 契约声明的段→产物名清单。上游引用的歧义判定按它来，不按已载入的产物数：
    # 第二份产物没落盘时引用照样歧义。
    stage_ops = {st["stage"]: [op["artifact"] for op in st["operations"]]
                 for st in contract["stages"]}
    # 先全部载入，供跨段断言引用上游产物。
    #
    # 按 **段/产物** 双键存，不是只按段存：schema 允许一段挂多个 operation，
    # 只按段存的话后一个 operation 的产物会把前一个覆盖掉，两个 operation
    # 于是都拿最后那份产物受审——断言全跑了，跑在错的东西上。
    for st in contract["stages"]:
        for op in st["operations"]:
            path = contained_file(run_dir, op["artifact"])
            if os.path.exists(path):
                artifacts[(st["stage"], op["artifact"])] = load_json(path)

    ctx = {"run_dir": run_dir, "source": source, "artifacts": artifacts,
           "stage_ops": stage_ops}

    for st in contract["stages"]:
        stage = st["stage"]
        if stages_filter and stage not in stages_filter:
            continue
        for op in st["operations"]:
            reach = op.get("source_reachability", "machine")
            art = artifacts.get((stage, op["artifact"]))
            # 覆盖类断言排在最后跑：它要的是同 operation 下**其余断言实际读过**
            # 哪些路径，故必须等它们先跑完。谓词里出现过的字符串不作数。
            ordered = ([a for a in op["assertions"]
                        if a["family"] != "output_field_coverage"] +
                       [a for a in op["assertions"]
                        if a["family"] == "output_field_coverage"])
            covered = (set(), set())
            for a in ordered:
                fam, tier, aid = a["family"], a["tier"], a["id"]
                # family↔tier 预检：必须排在 T2 短路之前。
                # T2 短路遇上源不可达即判 UNVERIFIED 并 continue，而 UNVERIFIED
                # 不进 failed 计数、不阻断交付。于是把任一机械可判的族标成
                # tier 2 再不给源，这条断言就从「必须成立」变成「从未判过」，
                # 且没有任何东西变红——降级通道藏在一个看起来最保守的状态里。
                # 判据取 IR 的 tier2_families：T2 的定义是「读源与账本观测值
                # 比对」，故当且仅当该族真读源。两个方向都拒——非 T2 族标 T2 是
                # 上述降级；T2 族标 T0/T1 则让读源族在无源时判 FAIL 而不是
                # UNVERIFIED，把「没法验」谎报成「验过了、不成立」。
                if (tier == 2) != (fam in t2_only):
                    want = "2" if fam in t2_only else "0/1"
                    rep.add(stage, aid, fam, tier, "FAIL",
                            f"family↔tier 不符（契约错）：{fam} 须 T{want}，实为 T{tier}")
                    continue
                # T2 且源不可达 → UNVERIFIED，不得改判 PASS
                if tier == 2 and (reach == "human_handoff" or source is None):
                    rep.add(stage, aid, fam, tier, "UNVERIFIED",
                            "源不可机械重读" if reach == "human_handoff" else "未提供 --source")
                    continue
                if art is None:
                    rep.add(stage, aid, fam, tier, "FAIL", f"产物缺失: {op['artifact']}")
                    continue
                fn = FAMILIES.get(fam)
                if fn is None:
                    rep.add(stage, aid, fam, tier, "FAIL", f"未知 family（契约错）: {fam}")
                    continue
                ctx["covered_fields"] = covered
                _reads_reset(art)
                try:
                    ok, detail = fn(art, a, ctx)
                except Exception as e:  # 断言本身跑不动 = FAIL，不静默通过
                    rep.add(stage, aid, fam, tier, "FAIL", f"{type(e).__name__}: {e}")
                    continue
                finally:
                    # 只有真跑过（无论 PASS/FAIL）才算读过——异常中断时读到哪算到哪。
                    # 用 update 不用 |=：covered 是 tuple，`covered[0] |= …`
                    # 展开成对 tuple 元素赋值，抛 TypeError。
                    if fam != "output_field_coverage":
                        covered[0].update(_READS)
                        covered[1].update(_DEEP)
                if not ok:
                    rep.add(stage, aid, fam, tier, "FAIL", detail)
                elif fam in weak:
                    rep.add(stage, aid, fam, tier, "WARN", "弱断言不满足段闸")
                else:
                    rep.add(stage, aid, fam, tier, "PASS", detail)


def verdict_of(counts):
    if counts["failed"]:
        return "FAIL"
    if counts["unverified"]:
        return "PASS_WITH_UNVERIFIED"
    return "PASS"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--contract", default=None)
    ap.add_argument("--stage", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--source", default=None)
    ap.add_argument("--manifest", default=None, help="写 run manifest 到此路径")
    ap.add_argument("--package", default=None,
                    help="包根目录，用于算 manifest 的 package_hash")
    ap.add_argument("--run-dir-source", default="explicit_arg",
                    choices=["explicit_arg", "env", "default"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if bool(args.stage) == bool(args.all) or len(args.stage) != len(set(args.stage)):
        print("用法错：须给 --stage <段> 或 --all", file=sys.stderr)
        return 2

    # 契约 / IR 读不出或解析不了 = 断言一条都没跑过，属用法层的错，走 2。
    # 并进 1 会让「闸拒了」与「闸压根没跑」在退出码上不可分。
    try:
        ir = load_ir()
        default_contract = os.path.join(HERE, "..", "assertions.json")
        contract_path = args.contract or default_contract
        with open(contract_path, encoding="utf-8") as f:
            contract = json.load(f)
    except (OSError, ValueError) as e:
        print(f"契约错：{type(e).__name__}: {e}", file=sys.stderr)
        return 2
    rep = Report()
    try:
        run_audit(args.run_dir, contract, ir, set(args.stage), args.source, rep)
    except (KeyError, TypeError, ValueError) as e:
        print(f"契约错：{type(e).__name__}: {e}", file=sys.stderr)
        return 2

    total = rep.counts()
    final = verdict_of(total)

    if args.json:
        print(json.dumps({"rows": rep.rows, "counts": total, "verdict": final},
                         ensure_ascii=False, indent=2))
    else:
        for r in rep.rows:
            mark = {"PASS": "  ok", "FAIL": "FAIL", "WARN": "warn",
                    "UNVERIFIED": "UNVR"}[r["status"]]
            line = f"[{mark}] {r['stage']}/{r['id']} ({r['family']}, T{r['tier']})"
            if r["detail"] and r["status"] != "PASS":
                line += f" — {r['detail']}"
            print(line)
        print(f"\n{final}  pass={total['passed']} fail={total['failed']} "
              f"unverified={total['unverified']} warn={total['warned']}")

    if args.manifest:
        stages_out = []
        for st in contract["stages"]:
            if args.stage and st["stage"] not in set(args.stage):
                continue
            c = rep.counts(st["stage"])
            # 可达性是 **operation** 的属性，不是段的属性：一段挂两个
            # operation 时两者可以不同。压成一个段级字段就要么丢掉其中一个
            # （只报 operations[0]，「有一个 operation 源不可机械重读」从
            # manifest 上消失），要么把标量字段偷偷变成清单（未声明的多态类型，
            # 消费方按 schema 读到的是枚举值，拿到清单即解析错）。故逐 operation 报。
            ops_out = [{"op": op["op"], "artifact": op["artifact"],
                        "source_reachability": op.get("source_reachability",
                                                      "machine")}
                       for op in st["operations"]]
            tiers = sorted({r["tier"] for r in rep.rows
                            if r["stage"] == st["stage"] and r["status"] != "UNVERIFIED"})
            unresolved = [f"{r['id']}: {r['detail']}" for r in rep.rows
                          if r["stage"] == st["stage"] and r["status"] == "UNVERIFIED"]
            stages_out.append({
                "stage": st["stage"],
                "operations": ops_out,
                "audit_tiers_run": tiers,
                "assertions": {k: c[k] for k in ("passed", "failed", "unverified")},
                "verdict": verdict_of(c),
                "unresolved_coverage": unresolved,
            })
        manifest = {
            "run_id": os.path.basename(os.path.normpath(args.run_dir)),
            "package_hash": (sha256_package(args.package) if args.package
                             else "UNRECORDED（未给 --package）"),
            "contract_hash": sha256_file(contract_path),
            "run_dir_resolved": os.path.abspath(args.run_dir),
            "run_dir_source": args.run_dir_source,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "stages": stages_out,
            "final_verdict": final,
            "retention": "always",
        }
        with open(args.manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 三判定各占一码：PASS_WITH_UNVERIFIED 不并进 0，否则「有面没验」
    # 在退出码上消失，调用方只能靠解析 stdout 才知道——闸的信号退化成文本。
    #
    # 但 3 只在 --all（末端交付判定）返回。--stage 是 fail-fast 段闸，它只
    # 回答「下游能不能走」：源不可达不是产物错，不得阻断 T0/T1，故段闸下
    # PASS_WITH_UNVERIFIED 返回 0。UNVERIFIED 并未被吞——逐条在 stdout /
    # --json 的 rows 里，并落进 manifest 的 unresolved_coverage。
    if final == "PASS_WITH_UNVERIFIED":
        return 3 if args.all else 0
    return {"PASS": 0, "FAIL": 1}[final]


if __name__ == "__main__":
    sys.exit(main())
