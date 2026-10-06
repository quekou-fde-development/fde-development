#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_e2e_package.py — 造一个真实持久 Skill 包，跑通完整链，验第五道运行期交付闸。

存在理由：M7-M11 全是**登记面**闸（验声明齐不齐），第五道验的是**运行期**——
每段落盘后 T1 立即跑、非 0 立即停、末端 audit --all、manifest 落盘字段齐、
三值判定不被压成二值。没跑过真 run，第五道就只有条文没有证据。

本器造三个臂，都用同一份包：
  A-clean       两段都对 → 末端 PASS，manifest final_verdict=PASS
  B-failfast    第 1 段就坏 → 段级 audit 非 0，第 2 段不得执行（fail-fast 生效）
  C-unverified  源不可达 → T2 标 UNVERIFIED，末端须 PASS_WITH_UNVERIFIED，禁报 PASS

三个**臂**验的是运行期行为，落 `runs-e2e/`。包内 `fixtures/` 是另一回事：
那是 M10 的正负例料，须逐条断言各有定向 mutant。此前 fixtures 下只有一个
`B-failfast` 目录、里面只有 INJECTION.json 一份收据，`must_be_rejected_by`
一口气指名全部 7 条——空目录令所有断言因「产物不在」而 FAIL，看上去 7 条全
拒住了。M10 的执行面把这一层揭开：那不是断言拒的，是闸恒 FAIL。故本器另造
`golden` 与 E1–E7 七个定向 mutant，每条断言各归其一。

用法: python3 make_e2e_package.py <out_root>
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft", "scripts", "audit.py"))

SKILL_MD = """---
name: e2e-orders-probe
description: 端到端探针 skill：取订单表、按发货国筛单，两段各自落盘并跑段级审核。用户要验运行期交付闸时调用。
metadata:
  updated: 2026-08-07
  workflow_mode: artifact
---

# e2e-orders-probe

按第 1→2 步顺序执行，段级审核非 0 立即停，不进下一段。

## 第 1 步 · 取数

1. **动作：** 读订单源表落 s1_export.json **副作用：** run_dir_only **依据：** 本文 §取数规则 **产出：** `s1_export.json` 落 run 目录 **值域：** rows[] 每行含 id/country（均为字符串）；page_total ∈ 非负整数；rows_sha256 ∈ 16 位十六进制

## 第 2 步 · 筛单

1. **动作：** 从 s1 删掉非中国发货单落 s2_filtered.json **副作用：** run_dir_only **依据：** 本文 §保留规则 **产出：** `s2_filtered.json` 落 run 目录 **值域：** orders[].country ∈ {中国发货}；deleted_us ∈ 非负整数

执行段：s1_export
动作：读订单源表并落取数账本
副作用：run_dir_only
可达接口：`python3 scripts/run_stages.py --stage s1_export --run-dir runs/<run-id>`
依据：本文 §取数规则
产出：s1_export.json（source_id + fetched_at + page_total + rows_sha256 + rows[]）
值域：rows[].id / country / sku ∈ 字符串；page_total ∈ 非负整数
断言：s1.receipt / s1.schema / s1.count_hash / s1.source_readback
执行段：s2_filtered
动作：从 s1 删掉非中国发货单并落筛单账本
副作用：run_dir_only
可达接口：`python3 scripts/run_stages.py --stage s2_filtered --run-dir runs/<run-id>`
依据：本文 §保留规则
产出：s2_filtered.json（orders[] + deleted_us）
值域：orders[].country ∈ {中国发货}；deleted_us ∈ 非负整数
断言：s2.subset / s2.predicate_replay / s2.excluded_count

## 取数规则

逐页取全，不截断。page_total 记录声明总行数，须等于实际 rows 行数；
rows_sha256 记录 rows 的内容指纹（规范化 JSON 的 sha256 前 16 位），
同行数改内容时由它抓。

## 保留规则

country 等于「中国发货」的留下，其余删除并计入 deleted_us。
"""

# T2 的源。C 臂不传 --source，即模拟源不可机械重读。
SOURCE_MD = """# 订单源

## 表 A · 订单发货国

| 单号 | 发货国 |
|---|---|
| A001 | 中国发货 |
| A002 | 中国发货 |
| A003 | 美国发货 |
| A004 | 中国发货 |
| A005 | 美国发货 |
"""

ASSERTIONS = {
    "package": "e2e-orders-probe",
    "contract_ir_version": "1.0",
    "stages": [
        {"stage": "s1_export", "operations": [{
            "op": "acquire", "artifact": "s1_export.json",
            "source_reachability": "machine",
            "assertions": [
                {"id": "s1.receipt", "family": "source_receipt", "tier": 1,
                 "predicate": {"required_keys": ["source_id", "fetched_at"]},
                 "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                 "mutants": ["E1-receipt-key-missing"]},
                {"id": "s1.schema", "family": "schema_conformance", "tier": 1,
                 "predicate": {"collection": "rows",
                               "required_fields": ["id", "country"],
                               "field_types": {"id": "str", "country": "str"}},
                 "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                 "mutants": ["E2-schema-type-drift"]},
                {"id": "s1.count_hash", "family": "count_hash", "tier": 1,
                 "predicate": {"collection": "rows", "declared_count": "page_total",
                               "declared_hash": "rows_sha256"},
                 "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                 "mutants": ["E3-count-drift"]},
                {"id": "s1.source_readback", "family": "source_readback", "tier": 2,
                 "predicate": {"collection": "rows", "key_field": "id",
                               "observed_field": "country",
                               "source": {"format": "markdown_table", "section": "表 A",
                                          "key_col": 0, "value_col": 1}},
                 "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                 "mutants": ["E4-country-rewrite"]},
            ]}]},
        {"stage": "s2_filtered", "operations": [{
            "op": "filter", "artifact": "s2_filtered.json",
            "source_reachability": "machine",
            "assertions": [
                {"id": "s2.subset", "family": "output_subset_input", "tier": 1,
                 "predicate": {"input": {"stage": "s1_export", "collection": "rows"},
                               "output": {"collection": "orders"}},
                 "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                 "mutants": ["E5-subset-alien-row"]},
                {"id": "s2.predicate_replay", "family": "predicate_replay", "tier": 1,
                 "predicate": {"collection": "orders", "id_field": "id",
                               "rule": {"field": "country", "op": "eq", "value": "中国发货"}},
                 "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                 "mutants": ["E6-country-leak"]},
                {"id": "s2.excluded_count", "family": "excluded_count_set", "tier": 1,
                 "predicate": {"input": {"stage": "s1_export", "collection": "rows"},
                               "output": {"collection": "orders"},
                               "excluded_counts": ["deleted_us"]},
                 "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                 "mutants": ["E7-deleted-count-drift"]},
            ]}]},
    ],
}

# 执行脚本：真跑，不是占位。--inject 用于制造 B 臂的坏产物。
RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 执行脚本。按 --stage 跑一段，产物落 run_dir。

run_dir 三级优先级：--run-dir > 环境变量 E2E_RUN_DIR > 默认 ./runs/<run-id>/
本脚本只执行与落盘，不做任何自检——自证不构成检验，判 PASS/FAIL 是 audit.py 的事。
"""
import argparse
import hashlib
import json
import os
import sys

SRC = [
    {"id": "A001", "country": "中国发货", "sku": "10011"},
    {"id": "A002", "country": "中国发货", "sku": "10012"},
    {"id": "A003", "country": "美国发货", "sku": "10013"},
    {"id": "A004", "country": "中国发货", "sku": "10014"},
    {"id": "A005", "country": "美国发货", "sku": "10015"},
]


def resolve_run_dir(arg):
    if arg:
        return arg, "explicit_arg"
    env = os.environ.get("E2E_RUN_DIR")
    if env:
        return env, "env"
    return os.path.join("runs", "default-run"), "default"


def content_hash(rows):
    """与解释器 _content_hash 同算法：规范化 JSON 的 sha256 取前 16 位。"""
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def s1(run_dir, inject):
    rows = [dict(r) for r in SRC]
    total = len(rows)
    if inject == "count-drift":
        total += 1                      # 声明行数与实到漂移
    art = {"source_id": "mock-orders-v1", "fetched_at": "2026-08-07T04:00:00",
           "page_total": total, "rows_sha256": content_hash(rows), "rows": rows}
    with open(os.path.join(run_dir, "s1_export.json"), "w", encoding="utf-8") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)


def s2(run_dir, inject):
    with open(os.path.join(run_dir, "s1_export.json"), encoding="utf-8") as f:
        s1a = json.load(f)
    keep = [r for r in s1a["rows"] if r["country"] == "中国发货"]
    dropped = len(s1a["rows"]) - len(keep)
    if inject == "country-leak":
        keep = [dict(r) for r in s1a["rows"]]      # 谓词坏死：非中国发货混进来
        dropped = 0
    art = {"orders": keep, "deleted_us": dropped}
    with open(os.path.join(run_dir, "s2_filtered.json"), "w", encoding="utf-8") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--inject", default=None)
    a = ap.parse_args()
    run_dir, src = resolve_run_dir(a.run_dir)
    os.makedirs(run_dir, exist_ok=True)
    {"s1_export": s1, "s2_filtered": s2}[a.stage](run_dir, a.inject)
    print(f"[run] stage={a.stage} run_dir={run_dir} ({src})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

# 审核脚本：薄封装，把 assertions.json 交给通用解释器。
# 不复制执行脚本的实现（共因防线第二条），不从产物反推规则（第一条）。
AUDIT_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit.py — 审核脚本。读落盘产物 + assertions.json，交通用解释器判 PASS/FAIL。

本脚本不含任何业务计算：断言是数据（assertions.json），解释器是代码
（v3.8-draft/scripts/audit.py）。故意不 import run_stages 的任何函数——
复制执行脚本的实现会让审核器与被审对象共因，错一起错。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
INTERP = os.environ.get("CONTRACT_INTERPRETER")
if not INTERP:
    sys.stderr.write("缺 CONTRACT_INTERPRETER（通用断言解释器路径）\n")
    sys.exit(2)

cmd = [sys.executable, INTERP] + sys.argv[1:] + [
    "--contract", os.path.join(PKG, "assertions.json"), "--package", PKG]
sys.exit(subprocess.run(cmd).returncode)
'''


def _hash(rows):
    """与执行脚本、解释器同一算法。注入后重算指纹，令改动不被 count_hash
    顺手带走——旁落越少，"是哪条断言拒的"越说得清。"""
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _restamp(r):
    """改过 rows 之后把 s1 的自报量重新对齐（行数 + 指纹）。"""
    r["s1_export.json"]["page_total"] = len(r["s1_export.json"]["rows"])
    r["s1_export.json"]["rows_sha256"] = _hash(r["s1_export.json"]["rows"])


def e1(r):
    """acquire · 取数回执缺一个声明键（source_id 没落账）

    行内容一字未动，故指纹与行数照旧；缺的是「这批数从哪来」。
    """
    del r["s1_export.json"]["source_id"]


def e2(r):
    """acquire · 字段类型漂移：A003 的 country 落成整数

    required_fields 只问键在不在，键还在；坏的是类型。故 field_types
    是这一族不可省的一半——缺了它，本注入全绿通过。

    旁落声明：A003 的观测值随之与源表对不上，s1.source_readback（T2，
    有源件时）一并报。改一行的内容而要求回源比对看不见，等于要求 T2
    不看这一行——旁落为零反倒说明 T2 没在看。credit 只记 s1.schema。
    """
    r["s1_export.json"]["rows"][2]["country"] = 3
    _restamp(r)


def e3(r):
    """acquire · 声明行数与实到漂移（静默截断的自报侧）"""
    r["s1_export.json"]["page_total"] += 1


def e4(r):
    """acquire · 观测抄错：源表记 A004 中国发货，账本记美国发货

    下游同步配平——A004 依此从保留集里拿掉、删除计数加一。故账本从头到尾
    自洽：子集、谓词重跑、删除计数三条全绿。只有回源比对能看见这一处。
    这正是 T2 存在的理由：内部一致性对「抄没抄错」零约束。
    """
    r["s1_export.json"]["rows"][3]["country"] = "美国发货"
    _restamp(r)
    s2 = r["s2_filtered.json"]
    s2["orders"] = [o for o in s2["orders"] if o["id"] != "A004"]
    s2["deleted_us"] = 3


def e5(r):
    """filter · 出集凭空多出入集没有的单

    多出来的这单 country 是中国发货，谓词重跑照样成立；删除计数同步配平，
    excluded_count 也不报。只有「出集 ⊆ 入集」看得见。
    """
    r["s2_filtered.json"]["orders"].append(
        {"id": "A999", "country": "中国发货", "sku": "10099"})
    r["s2_filtered.json"]["deleted_us"] = 1


def e6(r):
    """filter · 谓词坏死：该删的美国发货单被留下

    留下的这行原样来自入集，故子集成立；删除计数同步配平。三条最低族里
    只有谓词重跑能抓——子集只问「有没有凭空多出」，不问「该不该留」。
    """
    alien = [x for x in r["s1_export.json"]["rows"] if x["id"] == "A003"][0]
    r["s2_filtered.json"]["orders"].append(dict(alien))
    r["s2_filtered.json"]["deleted_us"] = 1


def e7(r):
    """filter · 静默丢单：删了 2 单，删除计数报 0

    出集一行未动，子集与谓词重跑全绿。被删的去了哪里只有删除计数在管。
    """
    r["s2_filtered.json"]["deleted_us"] = 0


FIXTURE_MUTANTS = [
    ("E1-receipt-key-missing", "s1.receipt", e1),
    ("E2-schema-type-drift", "s1.schema", e2),
    ("E3-count-drift", "s1.count_hash", e3),
    ("E4-country-rewrite", "s1.source_readback", e4),
    ("E5-subset-alien-row", "s2.subset", e5),
    ("E6-country-leak", "s2.predicate_replay", e6),
    ("E7-deleted-count-drift", "s2.excluded_count", e7),
]

ARTIFACTS = ["s1_export.json", "s2_filtered.json"]


def build_fixtures(root):
    """造 M10 的料：一份 golden + 七个定向 mutant。

    golden 不手写，**真跑执行脚本**产出：手写的 golden 是「我以为它该长
    什么样」，跑出来的才是它实际长什么样。两者不一致时，前者会让 golden
    恒绿而线上恒红。
    """
    fx = os.path.join(root, "fixtures")
    gold = os.path.join(fx, "golden")
    os.makedirs(gold, exist_ok=True)
    for stage in ("s1_export", "s2_filtered"):
        subprocess.run([sys.executable, os.path.join(root, "scripts", "run_stages.py"),
                        "--stage", stage, "--run-dir", gold],
                       check=True, capture_output=True, text=True)
    with open(os.path.join(gold, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"stages": [{"stage": "s1_export"},
                              {"stage": "s2_filtered"}]},
                  f, ensure_ascii=False, indent=1)

    base = {a: json.load(open(os.path.join(gold, a), encoding="utf-8"))
            for a in ARTIFACTS}
    for mid, must, fn in FIXTURE_MUTANTS:
        d = os.path.join(fx, mid)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        run = copy.deepcopy(base)
        fn(run)
        for a in ARTIFACTS:
            with open(os.path.join(d, a), "w", encoding="utf-8") as f:
                json.dump(run[a], f, ensure_ascii=False, indent=1)
        with open(os.path.join(d, "INJECTION.json"), "w", encoding="utf-8") as f:
            json.dump({"mutant_id": mid, "baseline": "golden",
                       "must_be_rejected_by": must,
                       "doc": (fn.__doc__ or "").strip()},
                      f, ensure_ascii=False, indent=1)
        print(f"  fixture {mid}  must_reject={must}")


def build(root):
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(os.path.join(root, "scripts"))
    os.makedirs(os.path.join(root, "fixtures"))
    with open(os.path.join(root, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD)
    with open(os.path.join(root, "fixtures", "source_orders.md"), "w", encoding="utf-8") as f:
        f.write(SOURCE_MD)
    with open(os.path.join(root, "assertions.json"), "w", encoding="utf-8") as f:
        json.dump(ASSERTIONS, f, ensure_ascii=False, indent=1)
    with open(os.path.join(root, "scripts", "run_stages.py"), "w", encoding="utf-8") as f:
        f.write(RUN_PY)
    with open(os.path.join(root, "scripts", "audit.py"), "w", encoding="utf-8") as f:
        f.write(AUDIT_PY)
    build_fixtures(root)
    print(f"built package: {root}")


if __name__ == "__main__":
    build(sys.argv[1])
