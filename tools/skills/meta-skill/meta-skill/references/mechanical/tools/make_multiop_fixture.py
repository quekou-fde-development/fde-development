#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_multiop_fixture.py — 一段挂两个 operation 的回归料。

存在理由：`assertions.json` 的 schema 明写 `operations` 是数组，而解释器
曾按 `artifacts[stage] = ...` 存产物——同段第二个 operation 的产物会把第一个
覆盖掉，两个 operation 于是都拿最后那份产物受审。断言全跑了、全 PASS，
跑在错的东西上。manifest 的 source_reachability 同理只报 operations[0]。

现有料每段都只挂一个 operation，这个洞永远碰不到。回归料的作用就是让
「以后仍然只有一个 operation」不再是防线的隐含前提。

三样东西各自受验：
  1. 同段两个 operation 各自按自己的产物受审（X1/X2 各只坏一个）
  2. 下游断言按 (段,产物) 双键**跨段引用第二份产物**（y.from_right / X3）
  3. 只给段名的引用在多 operation 段上是歧义——须 FAIL，不得退回取第一份

左右两账的 id 集合故意不同：下游若错取第一份产物，id 集合对不上立刻现形。
若两边同料，「取错了产物」与「取对了产物」在结果上不可分，回归料就是摆设。

五个 run + 两份契约：
  golden-multiop        三样全对                → 全 PASS
  X1-second-op-broken   只坏右账的声明行数      → 只有 x.right_count FAIL
  X2-first-op-broken    只坏左账的声明行数      → 只有 x.left_count FAIL
                        （按段覆盖取最后一份时，这个错完全看不见）
  X3-downstream-drop    下游漏掉右账的一行      → 只有 y.from_right FAIL
  assertions_multiop_ambiguous.json
                        与正契约逐字相同，只把下游引用的 artifact 字段删掉，
                        跑同一份 golden 数据 → 须 FAIL 于「引用有歧义」

用法: python3 make_multiop_fixture.py <runs_root> <contract_out>
      歧义契约写在 <contract_out> 同目录，文件名后缀 _ambiguous.json
"""
import copy
import hashlib
import json
import os
import shutil
import sys

# 左右两账的 id 集合与行数都不同——下游取错产物时必须能看出来。
LEFT_ROWS = [{"id": "L001", "amount": 10}, {"id": "L002", "amount": 20},
             {"id": "L003", "amount": 30}]
RIGHT_ROWS = [{"id": "R001", "amount": 11}, {"id": "R002", "amount": 22},
              {"id": "R003", "amount": 33}, {"id": "R004", "amount": 44}]


def content_hash(rows):
    """与 audit.py 的 _content_hash 同算法：规范化 JSON 后 sha256 取前 16 位。"""
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]

RULES_MD = """# 双账对账规则（multiop 套件判据源）

本文是 `fixtures/assertions_multiop.json` 里各条 `source_anchor` 指向的判据出处。

## 双账对账规则

同一段对账动作下并列两本账：左账与右账各自落一份产物，各自记自己的
`page_total`。两本账的核对彼此独立——左账的声明行数只由左账的实到行数验证，
拿右账去验左账不构成验证，哪怕右账恰好是对的。

下游合并件（`y_merged.json`）取的是**右账**的单号全集：右账每个 `id` 都要
出现在合并件里，一个都不能少。引用上游时必须写清取哪一份产物；一段挂了两份
产物而只给段名，指的是哪一份无从确定，此时不得代为选定。
"""


def golden():
    """同一段（对账）下两个 operation：左账与右账，各自一份产物。"""
    left = {"source_id": "ledger-left", "fetched_at": "2026-08-07T10:00:00",
            "page_total": len(LEFT_ROWS), "rows_sha256": content_hash(LEFT_ROWS),
            "rows": copy.deepcopy(LEFT_ROWS)}
    right = {"source_id": "ledger-right", "fetched_at": "2026-08-07T10:00:05",
             "page_total": len(RIGHT_ROWS), "rows_sha256": content_hash(RIGHT_ROWS),
             "rows": copy.deepcopy(RIGHT_ROWS)}
    # 下游合并件按右账的单号全集建，故意不是左账——取错产物即暴露。
    merged = {"rows": copy.deepcopy(RIGHT_ROWS)}
    return {"x_left.json": left, "x_right.json": right, "y_merged.json": merged}


def x1(run):
    """第二个 operation 的产物坏：右账声明行数漂移。"""
    run["x_right.json"]["page_total"] = 99


def x2(run):
    """第一个 operation 的产物坏：左账声明行数漂移。

    按段覆盖时 artifacts[stage] 是右账，左账的断言拿右账来验——右账是好的，
    于是这个错**完全看不见**。这条是覆盖 bug 最危险的形态。
    """
    run["x_left.json"]["page_total"] = 99


def x3(run):
    """下游漏掉右账的一行——验的是跨段引用真的落在第二份产物上。

    下游若错取同段第一份产物（左账），比的就是左账的 id 集合，这一行漏没漏
    根本影响不到结果。这条 FAIL 才说明 (段,产物) 双键寻址真的在工作。
    """
    run["y_merged.json"]["rows"] = run["y_merged.json"]["rows"][:-1]


def _restamp(art):
    """改过行内容后重打 rows_sha256，免得 count_hash 旁落把注入抢走。

    不重打时，任何动 rows 的注入都先撞上内容哈希——落点变成 count_hash，
    被测的那条断言（schema / receipt）依旧没被证伪。"""
    art["rows_sha256"] = content_hash(art["rows"])


def x4(run):
    """左账回执缺 source_id——只打 x.left_receipt，不碰 rows。"""
    del run["x_left.json"]["source_id"]


def x5(run):
    """左账 amount 由 int 漂成 str，重打哈希——只打 x.left_schema。

    改 amount 而不是 id：id 是键，动它会连带打到下游的键集比对；
    amount 不参与任何键集，落点因此只剩类型这一条。"""
    run["x_left.json"]["rows"][1]["amount"] = "20"
    _restamp(run["x_left.json"])


def x6(run):
    """右账回执缺 fetched_at——只打 x.right_receipt。"""
    del run["x_right.json"]["fetched_at"]


def x7(run):
    """右账 amount 由 int 漂成 str，重打哈希——只打 x.right_schema。

    下游 y.from_right 比的是 id 多重集（audit.py f_key_row_preservation），
    amount 不在其中，故这条不旁落到下游。"""
    run["x_right.json"]["rows"][0]["amount"] = "11"
    _restamp(run["x_right.json"])


# (mutant_id, 被它登记的那条断言, 注入函数)
MUTANTS = [
    ("X1-second-op-broken", "x.right_count", x1),
    ("X2-first-op-broken", "x.left_count", x2),
    ("X3-downstream-drop", "y.from_right", x3),
    ("X4-left-receipt-missing", "x.left_receipt", x4),
    ("X5-left-schema-type-drift", "x.left_schema", x5),
    ("X6-right-receipt-missing", "x.right_receipt", x6),
    ("X7-right-schema-type-drift", "x.right_schema", x7),
]

# operation 归属：x_reconcile 段两个 acquire，y_merge 段一个 map
_OP_OF = {mid: ("map" if mid.startswith("X3") else "acquire") for mid, _, _ in MUTANTS}

ANCHOR = "fixtures/multiop_rules.md §双账对账规则"


def contract(ambiguous=False):
    """正契约；ambiguous=True 时只把下游引用的 artifact 字段删掉，其余逐字相同。"""
    def a(aid, fam, pred, mutants):
        return {"id": aid, "family": fam, "tier": 1, "predicate": pred,
                "derived_fields": [], "source_anchor": ANCHOR, "mutants": mutants}

    # 每条断言各挂各的 mutant，不共用一份清单：三条断言同抄一个 mutant_id 时，
    # 「本条被证伪过」在登记面上成立，实际那个 mutant 只落在其中一条上——
    # 另外两条从未被拒过，而契约看起来是满的。
    def acquire_op(artifact, prefix, m_receipt, m_schema, m_count):
        return {"op": "acquire", "artifact": artifact,
                "source_reachability": "machine",
                "assertions": [
                    a(f"x.{prefix}_receipt", "source_receipt",
                      {"required_keys": ["source_id", "fetched_at"]}, [m_receipt]),
                    a(f"x.{prefix}_schema", "schema_conformance",
                      {"collection": "rows", "required_fields": ["id", "amount"],
                       "field_types": {"id": "str", "amount": "int"}},
                      [m_schema]),
                    a(f"x.{prefix}_count", "count_hash",
                      {"collection": "rows", "declared_count": "page_total",
                       "declared_hash": "rows_sha256"}, [m_count]),
                ]}

    # 跨段引用同段第二份产物。ambiguous 时删掉 artifact——只给段名，
    # 而该段挂了两个 operation，指哪一份无从确定。
    upstream = {"stage": "x_reconcile", "collection": "rows", "id_field": "id"}
    if not ambiguous:
        upstream["artifact"] = "x_right.json"

    merge_op = {"op": "map", "artifact": "y_merged.json",
                "source_reachability": "machine",
                "assertions": [
                    a("y.from_right", "key_row_preservation",
                      {"input": upstream,
                       "output": {"collection": "rows", "id_field": "id"}},
                      ["X3-downstream-drop"]),
                ]}

    return {
        "package": "multiop-suite",
        "contract_ir_version": "1.0",
        # 一个 stage，两个 operation——schema 明写允许，故必须被验到。
        "stages": [
            {"stage": "x_reconcile", "operations": [
                acquire_op("x_left.json", "left", "X4-left-receipt-missing",
                           "X5-left-schema-type-drift", "X2-first-op-broken"),
                acquire_op("x_right.json", "right", "X6-right-receipt-missing",
                           "X7-right-schema-type-drift", "X1-second-op-broken"),
            ]},
            {"stage": "y_merge", "operations": [merge_op]},
        ],
    }


def write_run(root, name, run):
    d = os.path.join(root, name)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for fn, obj in run.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    return d


def main():
    root, contract_out = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    write_run(root, "golden-multiop", golden())
    print("built golden-multiop")
    for mid, must, fn in MUTANTS:
        run = golden()
        fn(run)
        d = write_run(root, mid, run)
        with open(os.path.join(d, "INJECTION.json"), "w", encoding="utf-8") as f:
            json.dump({"mutant_id": mid, "baseline": "golden-multiop",
                       "operation": _OP_OF[mid],
                       "must_be_rejected_by": must,
                       "doc": fn.__doc__.strip().splitlines()[0]},
                      f, ensure_ascii=False, indent=1)
        print(f"built {mid}  must_reject={must}")

    fx = os.path.dirname(os.path.abspath(contract_out))
    with open(os.path.join(fx, "multiop_rules.md"), "w", encoding="utf-8") as f:
        f.write(RULES_MD)
    with open(contract_out, "w", encoding="utf-8") as f:
        json.dump(contract(), f, ensure_ascii=False, indent=1)
    print(f"contract → {contract_out}")
    amb = contract_out.replace(".json", "_ambiguous.json")
    with open(amb, "w", encoding="utf-8") as f:
        json.dump(contract(ambiguous=True), f, ensure_ascii=False, indent=1)
    print(f"ambiguous contract → {amb}  (跑 golden 须 FAIL 于「引用有歧义」)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
