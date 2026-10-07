#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ir_drift.py — contract_ir 的三面一致性检：MD ↔ JSON ↔ 解释器。

存在理由：contract_ir 有三份载体——`contract_ir.md`（给人读的条文）、
`contract_ir.json`（给闸读的词汇表）、`audit.py` 的 FAMILIES（真正跑得动的
求值器）。三面各自能改，改一面不改另两面不报任何错，于是：

  * JSON 声明了一个族而解释器没实现 → 契约写它，M9 覆盖判定认它满足了最低族，
    跑起来判「未知 family（契约错）」——闸在登记面放行，防线在执行面是空的；
  * MD 写了一条最低族而 JSON 没有 → 人按 MD 写契约，机械闸不要求它，
    少写不报错；
  * 反向的 JSON 有而 MD 无 → 人照 MD 写出来的契约永远过不了闸，且不知道为什么。

判据是**三面互相可达**，不是「某一面自洽」。归一化只去分隔符与大小写：
MD 写 `count/hash`、`source receipt`，JSON 写 `count_hash`、`source_receipt`，
这是排版差异不是漂移；`output_subset_input` 与 `output ⊆ input` 则必须两种
写法都在 MD 里出现——数学记号给人读，标识符给机器对。

MD 侧只认**反引号代码跨度**，不扫全文。扫全文是子串匹配：把族名表里的
`partition` 改成 `bucketize`，而 §4 散文里还提着 partition 这个词，全文扫描
照样"找得到"，漂移就此隐形——本器自检时正是栽在这一条上。名字出现在散文里
不构成条文登记，只有代码跨度才是。同理要求归一后**全等**：`count` 不因
`count_hash` 里含它而算数。

用法: python3 ir_drift.py [<ir_dir>] [<audit.py>]
退出码 0 = 三面一致；1 = 有漂移。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IR = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft", "references"))
DEFAULT_AUDIT = os.path.normpath(
    os.path.join(HERE, "..", "..", "v3.8-draft", "scripts", "audit.py"))


def norm(s):
    """归一到只剩小写字母：分隔符与大小写的差不是漂移。"""
    return re.sub(r"[^a-z]", "", s.lower())


def code_spans(md):
    """MD 里所有反引号代码跨度，归一形 → 原文。族名登记只认这里。

    不扫全文：全文扫描是子串匹配，族名从表里删掉、而散文别处还提着这个词，
    照样"找得到"。跨度集合又天然给出全等语义——`count` 不因 `counthash`
    含它而算数。"""
    out = {}
    for s in re.findall(r"`([^`\n]+)`", md):
        out.setdefault(norm(s), s)
    return out


def table_first_cells(md):
    """按表块切开，各块取首列的反引号裸标识符。

    分块而不是合并成一个大集合：families 表整行被删时，op 名还留在 vocabulary
    表里，合并集合看不出少了什么。逐块比对才能定位到是哪张表漏了。
    退出码表那种首列是 `0`/`1` 的块，裸标识符集为空，自然落选。"""
    blocks, cur = [], []
    for line in md.splitlines():
        if line.lstrip().startswith("|"):
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    out = []
    for b in blocks:
        cells = {}
        for line in b:
            m = re.match(r"\s*\|\s*`([a-z_]+)`\s*\|", line)
            if m:
                cells[norm(m.group(1))] = m.group(1)
        if cells:
            out.append(cells)
    return out


def main():
    ir_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IR
    audit_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_AUDIT

    j = json.load(open(os.path.join(ir_dir, "contract_ir.json"), encoding="utf-8"))
    md = open(os.path.join(ir_dir, "contract_ir.md"), encoding="utf-8").read()
    src = open(audit_path, encoding="utf-8").read()

    spans = code_spans(md)
    blocks = table_first_cells(md)
    # FAMILIES 表里真正挂上求值器的族名
    impl = set(re.findall(r'"([a-z_]+)": f_', src))

    ops = {norm(o): o for o in j["operations"]}
    declared, problems = set(), []

    # ---- operation 名：只认表首列，且认了就要求与 JSON **全等**
    # 阈值 2 而不是 1：某张不相干的表偶然以一个 op 名开头，不该被拖进来当 op 表。
    op_blocks = [b for b in blocks if len(set(b) & set(ops)) >= 2]
    if not op_blocks:
        problems.append("MD 里找不到以 operation 名为首列的表——无从比对，判漂移")
    for b in op_blocks:
        for k in sorted(set(b) - set(ops)):
            problems.append(f"MD 表首列的 `{b[k]}` 不在 JSON operations 里"
                            "——名漂移，或 MD 私自多出一个 operation")
        for k in sorted(set(ops) - set(b)):
            problems.append(f"operation `{ops[k]}` 在 JSON 有、MD 表首列无")

    for op, spec in sorted(j["operations"].items()):
        fams = list(spec["minimum_families"])
        for vs in spec.get("equivalent_families", {}).values():
            fams += list(vs)
        for f in fams:
            declared.add(f)
            if norm(f) not in spans:
                problems.append(f"`{op}` 的族 `{f}` 在 JSON 有、MD 无")
    for f in j["weak_families"]["members"]:
        declared.add(f)
        if norm(f) not in spans:
            problems.append(f"弱族 `{f}` 在 JSON 有、MD 无")
    # T2 专用族也是 IR 的族声明：family↔tier 预检按它判，漏进 declared 会让
    # 「IR 声明 26 / 实现 28」这种差恒定存在，而恒定的差等于这条检查关掉了。
    for f in j["tier2_families"]["members"]:
        declared.add(f)
        if norm(f) not in spans:
            problems.append(f"T2 专用族 `{f}` 在 JSON 有、MD 无")

    for f in sorted(declared - impl):
        problems.append(f"族 `{f}` 在 IR 声明、解释器 FAMILIES 里无实现"
                        "——契约写它即在登记面过闸、执行面判「未知 family」")
    # 反向：解释器跑得动、IR 一字未提。契约里写它 → M9 判「不在词汇表」，
    # 却又真能求值，于是这个族的去留取决于谁先跑到——而 IR 应当是唯一
    # 可执行权威。三面互相可达，不是两面可达加一面单向。
    for f in sorted(impl - declared):
        problems.append(f"族 `{f}` 解释器有实现、IR 一字未声明"
                        "——IR 不再是唯一权威，该族的效力取决于走哪条路径")

    print(f"IR 声明族 {len(declared)} 个；解释器实现 {len(impl)} 个")
    print(f"总判定: {'PASS' if not problems else 'FAIL'}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
