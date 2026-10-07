#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_gate_fixtures.py — 为 validate.py 的 M7-M11 五闸各造定向 mutant 包。

存在理由：M7-M11 是新加的闸，闸自己没被证伪过就不构成检验（同 contract_ir §9
对审核器的要求，此处上移一层——被审对象是编译器的机械闸本身）。v3.8-draft
自身跑 validate 时 M8-M10 恒 SKIP（编译器不是数据流水线、无 assertions.json），
所以必须另造一个持久 Skill 包形态的正例，再逐闸做定向 mutant。

G0 是正例：五闸全过。G1-G11 各从 G0 复制后定点坏一处，声明必须被哪个闸拒。

用法: python3 make_gate_fixtures.py <out_root>
"""
import copy
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.normpath(os.path.join(HERE, "..", "fixture_registry.json"))

GOOD_SKILL = """---
name: gate-fixture-good
description: 造一份持久 Skill 包形态的正例，供 validate.py M7-M11 五闸做假阳性对照。用户要求验机械闸时调用。
metadata:
  updated: 2026-08-07
  workflow_mode: artifact
---

# gate-fixture-good

按第 1→2 步顺序执行，不得跳步。

## 第 1 步 · 取数

1. **动作：** 读入订单导出表 **副作用：** run_dir_only **依据：** 本文 §取数规则 **产出：** s1_export.json 落 `runs/<run-id>/` **值域：** rows[] 非空；page_total ∈ 非负整数

## 第 2 步 · 筛单

1. **动作：** 从 s1 删掉非中国发货单 **副作用：** run_dir_only **依据：** 本文 §保留规则 **产出：** s2_filtered.json 落 `runs/<run-id>/` **值域：** orders[].country ∈ {中国发货}

执行段：s1_export
动作：从订单面板逐页取全并落盘
副作用：run_dir_only
可达接口：`python3 scripts/run_stages.py --stage s1_export --run-dir runs/<run-id>`
依据：本文 §取数规则
产出：s1_export.json（source_id + fetched_at + page_total + rows_sha256 + rows[]）
值域：rows[].id / country ∈ 字符串；page_total ∈ 非负整数
断言：s1.receipt / s1.schema / s1.count_hash
执行段：s2_filtered
动作：按 country 逐行判去留，留下的原样写出，不改字段
副作用：run_dir_only
可达接口：`python3 scripts/run_stages.py --stage s2_filtered --run-dir runs/<run-id>`
依据：本文 §保留规则
产出：s2_filtered.json（orders[] + deleted_us）
值域：orders[].country ∈ {中国发货}；deleted_us ∈ 非负整数
断言：s2.subset / s2.predicate_replay / s2.excluded_count

## 取数规则

按导出面板勾选全部字段，逐页取全，不截断。

## 保留规则

country 字段等于「中国发货」的留下，其余删除。

## 非命令与教学围栏对照

配置键 `config/python_settings.yaml`、属性 `node.children` 与标识符 `make_target`
均不是命令。下列 tilde 围栏只作教学示例，不进入真实执行段或占位残留检查：

~~~bash
python3 scripts/example.py
TODO
~~~
"""

GOOD_ASSERTIONS = {
    "package": "gate-fixture-good",
    "contract_ir_version": "1.0",
    "stages": [
        {
            "stage": "s1_export",
            "operations": [{
                "op": "acquire",
                "artifact": "s1_export.json",
                "source_reachability": "machine",
                "assertions": [
                    {"id": "s1.receipt", "family": "source_receipt", "tier": 1,
                     "predicate": {"required_keys": ["source_id", "fetched_at"]},
                     "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                     "mutants": ["G-none"]},
                    {"id": "s1.schema", "family": "schema_conformance", "tier": 1,
                     "predicate": {"collection": "rows",
                                   "required_fields": ["id", "country"],
                                   "field_types": {"id": "str", "country": "str"}},
                     "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                     "mutants": ["M-demo"]},
                    {"id": "s1.count_hash", "family": "count_hash", "tier": 1,
                     "predicate": {"collection": "rows",
                                   "declared_count": "page_total",
                                   "declared_hash": "rows_sha256"},
                     "derived_fields": [], "source_anchor": "SKILL.md §取数规则",
                     "mutants": ["M-demo"]},
                ],
            }],
        },
        {
            "stage": "s2_filtered",
            "operations": [{
                "op": "filter",
                "artifact": "s2_filtered.json",
                "source_reachability": "machine",
                "assertions": [
                    {"id": "s2.subset", "family": "output_subset_input", "tier": 1,
                     "predicate": {"input": {"stage": "s1_export", "collection": "rows"},
                                   "output": {"collection": "orders"}},
                     "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                     "mutants": ["G-none"]},
                    {"id": "s2.predicate_replay", "family": "predicate_replay", "tier": 1,
                     "predicate": {"collection": "orders",
                                   "rule": {"field": "country", "op": "eq",
                                            "value": "中国发货"}},
                     "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                     "mutants": ["G-none"]},
                    {"id": "s2.excluded_count", "family": "excluded_count_set", "tier": 1,
                     "predicate": {"input": {"stage": "s1_export", "collection": "rows"},
                                   "output": {"collection": "orders"},
                                   "excluded_counts": ["deleted_us"]},
                     "derived_fields": [], "source_anchor": "SKILL.md §保留规则",
                     "mutants": ["G-none"]},
                ],
            }],
        },
    ],
}

AUDIT_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit.py — 薄封装：把 assertions.json 交给通用断言解释器。

不含业务计算：断言是数据，解释器是代码。故意不 import 执行脚本的任何函数。
"""
import os
import argparse
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
INTERP = os.environ.get("CONTRACT_INTERPRETER")
if not INTERP:
    sys.stderr.write("缺 CONTRACT_INTERPRETER（通用断言解释器路径）\n")
    sys.exit(2)

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--contract", default=None)
opts, rest = ap.parse_known_args()
contract_path = opts.contract or os.path.join(PKG, "assertions.json")
cmd = [sys.executable, INTERP] + rest + [
    "--contract", contract_path, "--package", PKG]
sys.exit(subprocess.run(cmd).returncode)
'''

RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 执行脚本：取数与筛单，逐段落盘。只执行，不自检。

段由 --stage 选定：一个 runner 覆盖多段是允许的形态（contract_ir §2 切分粒度），
但每段必须能被单独调起——否则「本段落盘后立即跑 T1」的链形无处落脚。
"""
import argparse
import hashlib
import json
import os
import sys

ROWS = [
    {"id": "EF260805000001", "country": "中国发货"},
    {"id": "EF260805000002", "country": "中国发货"},
    {"id": "EF260805000007", "country": "美国发货"},
]

# G0 正例同时固定静态传播的保守边界：参数会遮蔽模块常量，解构赋值会
# 使先前的局部常量失效；两者都不得让真实写盘被误裁。
MODULE_ENABLED = False


def content_hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def s1_export(run_dir, MODULE_ENABLED=True):
    local_enabled = False
    local_enabled, = (True,)
    imported_enabled = False
    import os as imported_enabled
    callable_enabled = False
    def callable_enabled():
        return True
    art = {"source_id": "orders-panel-2026W32",
           "fetched_at": "2026-08-07T10:00:00",
           "page_total": len(ROWS), "rows_sha256": content_hash(ROWS),
           "rows": ROWS}
    if MODULE_ENABLED and local_enabled and imported_enabled and callable_enabled:
        write(run_dir, "s1_export.json", art)


def s2_filtered(run_dir):
    with open(os.path.join(run_dir, "s1_export.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    keep = [r for r in rows if r["country"] == "中国发货"]
    art = {"orders": keep, "deleted_us": len(rows) - len(keep)}
    write(run_dir, "s2_filtered.json", art)


def write(run_dir, name, obj):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


STAGES = {"s1_export": s1_export, "s2_filtered": s2_filtered}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    STAGES[a.stage](a.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

# G0 的 golden 与定向 mutant：M10 要真跑它们，不能只验登记面。
GOLDEN_S1_ROWS = [
    {"id": "EF260805000001", "country": "中国发货"},
    {"id": "EF260805000002", "country": "中国发货"},
    {"id": "EF260805000007", "country": "美国发货"},
]


def _hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def golden_run():
    keep = [r for r in GOLDEN_S1_ROWS if r["country"] == "中国发货"]
    return {
        "s1_export.json": {"source_id": "orders-panel-2026W32",
                           "fetched_at": "2026-08-07T10:00:00",
                           "page_total": len(GOLDEN_S1_ROWS),
                           "rows_sha256": _hash(GOLDEN_S1_ROWS),
                           "rows": copy.deepcopy(GOLDEN_S1_ROWS)},
        "s2_filtered.json": {"orders": keep,
                             "deleted_us": len(GOLDEN_S1_ROWS) - len(keep)},
    }


def demo_mutant_run():
    """定向 mutant：声明行数漂移。必须被 s1.count_hash 拒。"""
    r = golden_run()
    r["s1_export.json"]["page_total"] += 1
    return r


# ---- 逐条强断言的定向 mutant ----------------------------------------
#
# 每个只冲一条断言，旁落项按设计为零：一个 mutant 同时触发三条时，
# 「被指名那条拒了」这句话不再携带信息——换成别的断言也会拒。
# 下面每个坏法的选型都受这条约束，注释里写明为什么这么坏而不是那么坏。

def m_receipt():
    """删掉取数时刻。只冲 s1.receipt——行内容没动，指纹与行数照旧。"""
    r = golden_run()
    del r["s1_export.json"]["fetched_at"]
    return r


def m_schema():
    """把**被删那一行**的 country 改成整数。只冲 s1.schema。

    改的是 007（美国发货，s2 不保留它）：改保留行会让 s2.subset 的
    行内容保全一并报错，旁落即失去指名意义。改完重盖指纹——要留住的是
    类型错，不是指纹不一致，否则这条又变成 count_hash 的第二个 mutant。
    """
    r = golden_run()
    r["s1_export.json"]["rows"][2]["country"] = 42
    r["s1_export.json"]["rows_sha256"] = _hash(r["s1_export.json"]["rows"])
    return r


def m_subset():
    """把一个保留单号换成上游没有的号。只冲 s2.subset。

    换而不是加：加一条则出集 2→3，删除计数配平式随之破，excluded_count
    旁落。替换后出集仍是 2 条，配平式 2+1=3 照旧成立；换上的号 country
    仍是中国发货，谓词重跑照旧成立。只剩「凭空多出」这一处。
    """
    r = golden_run()
    r["s2_filtered.json"]["orders"][0] = {"id": "EF999999999999",
                                          "country": "中国发货"}
    return r


def m_predicate():
    """保留了一条美国发货单（换掉一条中国发货单）。只冲 s2.predicate_replay。

    换上的 007 逐字取自上游，故子集与行内容保全都成立；出集仍 2 条，
    配平式成立。唯一破的是「保留项须满足谓词」。
    """
    r = golden_run()
    r["s2_filtered.json"]["orders"][1] = copy.deepcopy(GOLDEN_S1_ROWS[2])
    return r


def m_excluded():
    """删除计数虚报一条。只冲 s2.excluded_count——出集一行未动。"""
    r = golden_run()
    r["s2_filtered.json"]["deleted_us"] += 1
    return r


# mutant_id → (必须被哪条断言拒, 构造函数)
GOOD_MUTANTS = {
    "M-demo": ("s1.count_hash", demo_mutant_run),
    "M-receipt": ("s1.receipt", m_receipt),
    "M-schema": ("s1.schema", m_schema),
    "M-subset": ("s2.subset", m_subset),
    "M-predicate": ("s2.predicate_replay", m_predicate),
    "M-excluded": ("s2.excluded_count", m_excluded),
}


def build_good(root):
    d = os.path.join(root, "G0-good")
    os.makedirs(os.path.join(d, "scripts"))
    os.makedirs(os.path.join(d, "fixtures", "golden"))
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(GOOD_SKILL)
    # 每条强断言登记指名它的那个 mutant——登记面与料面同一份来源，
    # 两边各写一份就会漂移，而漂移正是 M10 要拒的东西。
    by_assertion = {aid: mid for mid, (aid, _) in GOOD_MUTANTS.items()}
    spec = copy.deepcopy(GOOD_ASSERTIONS)
    for st in spec["stages"]:
        for op in st["operations"]:
            for a in op["assertions"]:
                a["mutants"] = [by_assertion[a["id"]]]
    with open(os.path.join(d, "assertions.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "scripts", "audit.py"), "w", encoding="utf-8") as f:
        f.write(AUDIT_PY)
    with open(os.path.join(d, "scripts", "run_stages.py"), "w", encoding="utf-8") as f:
        f.write(RUN_PY)
    for fn, obj in golden_run().items():
        with open(os.path.join(d, "fixtures", "golden", fn), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "fixtures", "golden", "run_manifest.json"),
              "w", encoding="utf-8") as f:
        json.dump({"stages": [{"stage": "s1_export"},
                              {"stage": "s2_filtered"}]},
                  f, ensure_ascii=False, indent=1)
    for mid, (want, build) in GOOD_MUTANTS.items():
        md = os.path.join(d, "fixtures", mid)
        os.makedirs(md)
        for fn, obj in build().items():
            with open(os.path.join(md, fn), "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
        with open(os.path.join(md, "INJECTION.json"), "w", encoding="utf-8") as f:
            json.dump({"mutant_id": mid, "baseline": "golden",
                       "must_be_rejected_by": want,
                       "doc": (build.__doc__ or "").strip().splitlines()[0]},
                      f, ensure_ascii=False, indent=1)
    return d


# ---- 各闸的定向坏法 -------------------------------------------------

def g1(d, a):
    """M8 · 审核脚本缺失——源不可达也不豁免审核脚本，缺件即 fail"""
    os.remove(os.path.join(d, "scripts", "audit.py"))


def g2(d, a):
    """M9 · operation 在封闭词汇表外，且未走 custom 三条件"""
    a["stages"][1]["operations"][0]["op"] = "cleanup"


def g3(d, a):
    """M9 · 最低强断言族缺条（filter 缺 predicate_replay，只剩两条守恒式）"""
    ops = a["stages"][1]["operations"][0]
    ops["assertions"] = [x for x in ops["assertions"] if x["id"] != "s2.predicate_replay"]


def g4(d, a):
    """M10 · 强断言 mutants 为空——未经证伪，不构成检验"""
    a["stages"][0]["operations"][0]["assertions"][2]["mutants"] = []


def g5(d, a):
    """M11 · 模板占位残留（成品里留未填的 TODO 产物名）"""
    p = os.path.join(d, "SKILL.md")
    t = open(p, encoding="utf-8").read()
    t = t.replace("s2_filtered.json 落", "TODO.json 落")
    open(p, "w", encoding="utf-8").write(t)


def g6(d, a):
    """M7 · 编号执行步缺值域槽"""
    p = os.path.join(d, "SKILL.md")
    t = open(p, encoding="utf-8").read()
    t = t.replace(" **值域：** orders[].country ∈ {中国发货}", "")
    open(p, "w", encoding="utf-8").write(t)


def g5b_selftest(d, a):
    """M4 · 杂物闸自测：G 系 fixture 顶层多一个 GATE_INJECTION.json，
    本身会触发 M4 WARN。WARN 不计入退出码，故不单列为 mutant，此处仅存证。
    """


def g7(d, a):
    """M9 · 守恒式反解：断言登记 derived_fields，不得计入族覆盖

    excluded_count 的 deleted_us 由「入集 − 出集」反解得出，该断言对它零约束。
    登记 derived_fields 后 filter 族即缺一条，M9 必须判 fail——这条验的是
    contract_ir §4 总禁则真的接进了覆盖判定，不是写在文档里好看。
    """
    ops = a["stages"][1]["operations"][0]
    for x in ops["assertions"]:
        if x["id"] == "s2.excluded_count":
            x["derived_fields"] = ["deleted_us"]


def g8(d, a):
    """M8 · fixtures/ 缺失——审核器验收料不在位，无从做假阳性对照"""
    shutil.rmtree(os.path.join(d, "fixtures"))


def g9(d, a):
    """M10 · 登记面齐全但 mutant 拒不住——把 golden 的料塞进 mutant 目录

    这条验的是 M10 的**执行面**：`assertions.json` 的 mutants、
    `INJECTION.json` 的 must_be_rejected_by、目录在位，登记面三样全绿，
    而那份料根本没坏，指名的断言在它上面判 PASS。只验登记面的 M10 会放行。
    """
    src = os.path.join(d, "fixtures", "golden", "s1_export.json")
    shutil.copyfile(src, os.path.join(d, "fixtures", "M-receipt", "s1_export.json"))


def g10(d, a):
    """M10 · 正例上闸也拒——假阳性对照不成立

    把 golden 的声明行数改掉。mutant 侧一个没动、照样全被拒，若只看
    「mutant 都拒住了」这一半，闸恒 FAIL 与闸有判别力不可分。
    """
    p = os.path.join(d, "fixtures", "golden", "s1_export.json")
    with open(p, encoding="utf-8") as f:
        art = json.load(f)
    art["page_total"] = 99
    with open(p, "w", encoding="utf-8") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)


UNVERIFIED_AUDIT_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit.py — 真读契约、遍历全部断言，然后一条也不判：全部报 UNVERIFIED。

契约按规矩读进来了（`--contract` 可覆盖，缺省走包内 assertions.json），
断言也逐条列全了，输出格式与真审核器一模一样。缺的只有中间那一步：
没有任何求值。UNVERIFIED 在报告里不是红的，`PASS_WITH_UNVERIFIED` 也不是
FAIL，于是「六条断言一条没判过」在颜色上与「六条全过」难分。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--contract", default=None)
    ap.add_argument("--stage", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--source", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # 缺省契约走普通变量再汇流，不塞进 argparse 的 default——
    # 数据流要在语法树上看得见：这条路径确实进了 open()。
    default_contract = os.path.join(PKG, "assertions.json")
    contract_path = args.contract or default_contract
    with open(contract_path, encoding="utf-8") as f:
        contract = json.load(f)

    rows = []
    for st in contract["stages"]:
        for op in st["operations"]:
            for a in op["assertions"]:
                rows.append({"stage": st["stage"], "id": a["id"],
                             "family": a["family"], "tier": a["tier"],
                             "status": "UNVERIFIED",
                             "detail": "本审核器不做求值"})
    counts = {"passed": 0, "failed": 0, "warned": 0, "unverified": len(rows)}
    verdict = "PASS_WITH_UNVERIFIED"
    if args.json:
        print(json.dumps({"rows": rows, "counts": counts, "verdict": verdict},
                         ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"[UNVR] {r['stage']}/{r['id']} ({r['family']}, T{r['tier']})"
                  f" — {r['detail']}")
        print(f"\n{verdict}  pass=0 fail=0 unverified={len(rows)} warn=0")
    return 3 if args.all else 0


if __name__ == "__main__":
    sys.exit(main())
'''


def g11(d, a):
    """M10 · 审核器真读契约、遍历全部断言，却一条也不判——全 UNVERIFIED 不是背书

    契约**一个字节都没改**（与 G0 同 SHA-256）。换掉的只有包内 `scripts/audit.py`：
    它按规矩解析 `--contract`、把契约路径真送进 `open()` + `json.load()`、把六条
    断言逐条列出来，然后全部标 UNVERIFIED，`--all` 回 rc3。

    M8 三件事它全做到了：审核脚本在位、真消费契约、不与执行脚本共因——所以
    M8 PASS，M9 也 PASS（契约没动）。唯一拒得住它的是 M10 的执行面：正例上
    每条断言都得 PASS，UNVERIFIED（压根没跑过）与 WARN（弱断言）都不是
    「这条断言在正例上成立」的证据。

    与旧形态的分工：改 tier 那种做法把契约改坏了，M9/M10 从登记面就红，
    验不到「读了契约但不判断」这一层。本例把包做到只剩最后一道防线可拒，
    验的就是那道防线本身。

    旁落声明：mutant 支同样跑这个坏 audit，六个 mutant 都拒不出 FAIL，
    M10 的 mutant 支一并报错。两支同属 M10，跨闸旁落为零。
    """
    p = os.path.join(d, "scripts", "audit.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(UNVERIFIED_AUDIT_PY)


# 逐段绑定的两个负例料。放在这里而不是内联进 g12/g13，是为了让「坏在哪」
# 一眼可读：两份脚本与 RUN_PY 的差只有一处。
NO_STAGE_RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 一趟从头跑到尾，中途无处切入。"""
import argparse
import hashlib
import json
import os
import sys

ROWS = [
    {"id": "EF260805000001", "country": "中国发货"},
    {"id": "EF260805000002", "country": "中国发货"},
    {"id": "EF260805000007", "country": "美国发货"},
]


def content_hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def write(run_dir, name, obj):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    write(a.run_dir, "s1_export.json",
          {"source_id": "orders-panel-2026W32",
           "fetched_at": "2026-08-07T10:00:00",
           "page_total": len(ROWS), "rows_sha256": content_hash(ROWS),
           "rows": ROWS})
    keep = [r for r in ROWS if r["country"] == "中国发货"]
    write(a.run_dir, "s2_filtered.json",
          {"orders": keep, "deleted_us": len(ROWS) - len(keep)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

STUB_RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 认得两个段名，一份产物也不落。"""
import argparse
import sys

STAGES = ["s1_export", "s2_filtered"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    print(f"[run] stage={a.stage} 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def g12(d, a):
    """M8 · 共用 runner 不认 --stage——中间段无从单独调起

    脚本在位、契约在位、产物照落，只是必须一趟跑完。契约的链形是「本段落盘
    → 立刻跑本段断言 → 过了才进下一段」；无处切入时这条链只剩首尾两点，中间
    段的断言全部退化成事后追认——错在第二段而第四段才发现，那时前三段的产物
    已互相污染，定位不回去。故「有执行脚本」不等于「每段都绑到入口」。
    """
    p = os.path.join(d, "scripts", "run_stages.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(NO_STAGE_RUN_PY)


def g13(d, a):
    """M8 · 入口是空壳——认得段名，一份产物也不落

    `--stage` 在、两个段名都在 choices 里，「共用 runner 认得 --stage 且段名
    可达」这一关全绿。而它什么也不产出：段与入口的绑定是登记面上的，执行面
    是空的。把段名写进 choices 是零成本的，故只验段名可达的闸拦不住这一形态
    ——必须再验该段声明的 artifact 真的流进了写文件调用。

    与 G12 咬同一条判据的两端：G12 是入口不认段，G13 是入口认段不干活。
    旁落为零：审核脚本、契约、fixtures 一律没动，M10 照常 PASS。
    """
    p = os.path.join(d, "scripts", "run_stages.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(STUB_RUN_PY)


DOCSTRING_DECOY_RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 按 --stage 跑 s1_export 段或 s2_filtered 段，产物落 run_dir。

两段都由本脚本负责：s1_export 取数落 s1_export.json，s2_filtered 筛单落
s2_filtered.json。段名在这段说明里写全了，dispatch 里只有一个。
"""
import argparse
import hashlib
import json
import os
import sys

ROWS = [
    {"id": "EF260805000001", "country": "中国发货"},
    {"id": "EF260805000002", "country": "中国发货"},
    {"id": "EF260805000007", "country": "美国发货"},
]


def content_hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def write(run_dir, name, obj):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def export(run_dir):
    write(run_dir, "s1_export.json",
          {"source_id": "orders-panel-2026W32",
           "fetched_at": "2026-08-07T10:00:00",
           "page_total": len(ROWS), "rows_sha256": content_hash(ROWS),
           "rows": ROWS})
    keep = [r for r in ROWS if r["country"] == "中国发货"]
    write(run_dir, "s2_filtered.json",
          {"orders": keep, "deleted_us": len(ROWS) - len(keep)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    {"s1_export": export}[a.stage](a.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def g14(d, a):
    """M8 · 段名只在 docstring 里——散文不构成认领

    `--stage` 在、两个段名在文件里都出现了、两份产物也都真落了盘，唯一的问题
    是 dispatch 里只有 `s1_export`：`--stage s2_filtered` 直接 KeyError。
    s2_filtered 这个名字只活在文档串里。

    这是 M8 拒空壳 audit.py 那条判据的同构形态——「源码里出现过这个词」不算
    消费契约，同理不算认领段。段名写进 docstring 是零成本的，认散文则「这个段
    绑到了入口」退化成「文件里提过这个段名」，闸的判别力归零。

    与 G13 的分工：G13 是认了段名不落产物，本例是产物照落而段名压根没进
    dispatch——两条都能让 `--stage <某段>` 跑不起来，坏在数据流的两端。
    """
    p = os.path.join(d, "scripts", "run_stages.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(DOCSTRING_DECOY_RUN_PY)


UNRELATED_STUB_RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stub.py — 与本包两个段都无关的脚本，两个旗标一个也不认。"""
import sys


def main():
    print("[run] nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

PRINT_ONLY_DISPATCH_RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_stages.py — 两个旗标齐、段名字典齐，就是不拿它选路。"""
import argparse
import hashlib
import json
import os
import sys

ROWS = [
    {"id": "EF260805000001", "country": "中国发货"},
    {"id": "EF260805000002", "country": "中国发货"},
    {"id": "EF260805000007", "country": "美国发货"},
]


def content_hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def write(run_dir, name, obj):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def s1_export(run_dir):
    write(run_dir, "s1_export.json",
          {"source_id": "orders-panel-2026W32",
           "fetched_at": "2026-08-07T10:00:00",
           "page_total": len(ROWS), "rows_sha256": content_hash(ROWS),
           "rows": ROWS})


def s2_filtered(run_dir):
    keep = [r for r in ROWS if r["country"] == "中国发货"]
    write(run_dir, "s2_filtered.json",
          {"orders": keep, "deleted_us": len(ROWS) - len(keep)})


STAGES = {"s1_export": s1_export, "s2_filtered": s2_filtered}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    print(f"[run] stage={a.stage} 已登记于 {sorted(STAGES)}")
    s1_export(a.run_dir)
    s2_filtered(a.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def g15(d, a):
    """M8 · 执行脚本与本包的段全无关系——两个旗标一个也不认

    `run*.py` 在位，M8 的「有执行脚本」那一关照过。而它既不叫 `run_<段名>.py`，
    也不认 `--stage` / `--run-dir`：包里两个段都没有任何入口可调起，产物由谁
    落、落在哪都不由调用方决定。

    存在理由：G12/G13/G14 三条都预设了"脚本至少在试着认领这些段"，坏在认领的
    某一环。本例把下限补齐——一个跟本包毫无关系的脚本摆进 scripts/，「有执行
    脚本」这条最低门槛仍然成立。判据若停在文件名匹配 `run*.py`，此形态直接过。
    """
    os.remove(os.path.join(d, "scripts", "run_stages.py"))
    with open(os.path.join(d, "scripts", "run_stub.py"), "w", encoding="utf-8") as f:
        f.write(UNRELATED_STUB_RUN_PY)


def g16(d, a):
    """M8 · 旗标齐、段名字典齐，字典却没被用来选路——声明一张表不是绑定

    `--stage` 与 `--run-dir` 都真注册了，`STAGES` 字典两个段名都在，choices
    也是从它取的，两份产物还都真落了盘。唯一缺的是那一步：`a.stage` 从没被
    用来索引 `STAGES`——main 里只把它打印出来，然后两段无条件顺跑。
    `--stage s1_export` 与 `--stage s2_filtered` 的行为完全一样，段选择器是
    个摆设。

    这是登记面/执行面之分在 M8 上的最后一处：前面三条各缺一件东西（旗标、
    产物、字典键），本例什么都不缺，缺的是它们之间的那条数据流。判据若停在
    「旗标在 ∧ 段名在字典键里」，本形态全绿——而它恰恰是「一趟跑到尾」
    （G12）换了层包装。
    """
    p = os.path.join(d, "scripts", "run_stages.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(PRINT_ONLY_DISPATCH_RUN_PY)


def g17(d, a):
    """M7 · 卡片式执行段缺「值域」一槽——单点，只打卡片式那一支

    G0 同时带两条编号步与一张 `执行段：s2_filtered` 六槽卡。本例只删卡片里
    的 `值域：` 那一行，别的什么都不动：编号步照旧四槽齐全，脚本、契约、
    fixtures 一律没碰。

    存在理由：M7 对卡片式的判定此前只有临时人工探针作证。编号式有 G6 常驻
    负例，卡片式没有——两支共用一个闸名，编号式那支绿着，报告上就是「M7
    PASS」，卡片式的六槽契约从未被证伪过。单点删一行，落点唯一，验的正是
    `执行段卡「s2_filtered」缺槽 ['值域']` 这一条。

    与 G6 的分工：G6 删编号步的值域，本例删卡片的值域。两条咬同一句要求的
    两种书写形态，跨闸旁落均为零。
    """
    p = os.path.join(d, "SKILL.md")
    with open(p, encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    kept = [ln for ln in lines
            if not re.match(r"^值域：orders\[\]\.country", ln)]
    assert len(kept) == len(lines) - 1, "card-negative 须恰好删掉一行"
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(kept)


def g18(d, a):
    """M7 · 裸 shell 命令编号步未标动作，旧 M7 完全看不见"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s = s.replace("执行段：s1_export",
                  "3. python3 scripts/run_stages.py --stage s1_export --run-dir runs/demo\n\n"
                  "执行段：s1_export", 1)
    open(p, "w", encoding="utf-8").write(s)


def g19(d, a):
    """M8 · assertions 少声明 s2，四面 stage 集必须精确闭合"""
    a["stages"] = [s for s in a["stages"] if s["stage"] != "s2_filtered"]


def g20(d, a):
    """M7 · 只有围栏内教学卡，持久包的真实执行段集合为空"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    start = s.index("执行段：s1_export")
    end = s.index("\n## 取数规则")
    s = s[:start] + "```text\n" + s[start:end] + "```\n" + s[end:]
    open(p, "w", encoding="utf-8").write(s)


def g21(d, a):
    """M7 · 普通散文句内嵌反引号命令，命令不在行首也须落四槽"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s = s.replace("执行段：s1_export",
                  "收尾时跑 `python3 scripts/archive.py --out archive/` 打包归档。\n\n"
                  "执行段：s1_export", 1)
    open(p, "w", encoding="utf-8").write(s)


def g22(d, a):
    """M7 · 编号散文前缀后嵌反引号命令，前置说明不得绕过四槽闸"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s = s.replace("执行段：s1_export",
                  "7. 归档结果：`python3 scripts/archive.py --out archive/`\n\n"
                  "执行段：s1_export", 1)
    open(p, "w", encoding="utf-8").write(s)


def _insert_unstructured(d, line):
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s = s.replace("执行段：s1_export", line + "\n\n执行段：s1_export", 1)
    open(p, "w", encoding="utf-8").write(s)


def g23(d, a):
    """M7 · git 行内命令不在旧白名单，仍须落四槽"""
    _insert_unstructured(d, "收尾运行 `git status --short`。")


def g24(d, a):
    """M7 · curl 行内命令不在旧白名单，仍须落四槽"""
    _insert_unstructured(d, "取数运行 `curl -fsSL https://example.invalid/data`。")


def g25(d, a):
    """M7 · 相对路径脚本命令须落四槽"""
    _insert_unstructured(d, "验收运行 `./x.sh --dry-run`。")


def g26(d, a):
    """M7 · poetry wrapper 命令须落四槽"""
    _insert_unstructured(d, "测试运行 `poetry run pytest`。")


def g27(d, a):
    """M7 · pnpm 项目命令须落四槽"""
    _insert_unstructured(d, "构建运行 `pnpm test`。")


def g28(d, a):
    """M7 · 环境变量前缀命令须落四槽"""
    _insert_unstructured(d, "调试运行 `MODE=test python3 scripts/x.py`。")


def g29(d, a):
    """M7 · 绝对解释器路径命令须落四槽"""
    _insert_unstructured(d, "执行 `/usr/bin/python3 scripts/x.py`。")


def g30(d, a):
    """M7 · 无反引号裸编号 git 命令须落四槽"""
    _insert_unstructured(d, "7. git status --short")


def g31(d, a):
    """M7 · 四空格缩进命令块须落四槽"""
    _insert_unstructured(d, "    git status --short")


def g32(d, a):
    """M7 · 四槽标签在但前三槽为空，不构成结构化执行步"""
    _insert_unstructured(
        d, "**动作：** **依据：** **产出：** **值域：** 非空；运行 `git status --short`")


def g33(d, a):
    """M8 · 死函数写产物诱饵不可替代 stage handler 可达写盘"""
    p = os.path.join(d, "scripts", "run_stages.py")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"def s1_export\([^\n]*\):",
               "def dead_s1_export_decoy(run_dir):", s, count=1)
    s = s.replace("STAGES = {\"s1_export\": s1_export,",
                  "def s1_export(run_dir):\n    return None\n\n\n"
                  "STAGES = {\"s1_export\": s1_export,", 1)
    open(p, "w", encoding="utf-8").write(s)


ORACLE_AUDIT_PY = r'''#!/usr/bin/env python3
"""读取 fixture 注入答案并伪造逐条状态的作弊审核器。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
CONTRACT = os.path.join(PKG, "assertions.json")
run_dir = sys.argv[1]
with open(CONTRACT, encoding="utf-8") as f:
    contract = json.load(f)
ids = [a["id"] for s in contract["stages"] for o in s["operations"]
       for a in o["assertions"]]
named = set()
inj = os.path.join(run_dir, "INJECTION.json")
if os.path.isfile(inj):
    with open(inj, encoding="utf-8") as f:
        named = set(str(json.load(f).get("must_be_rejected_by", "")).split("/"))
rows = [{"id": aid, "status": "FAIL" if aid in named else "PASS"} for aid in ids]
print(json.dumps({"rows": rows}))
sys.exit(1 if named else 0)
'''


def g34(d, a):
    """M10 · 审核器偷读 INJECTION 答案，原矩阵看似全对也须拒绝"""
    with open(os.path.join(d, "scripts", "audit.py"), "w", encoding="utf-8") as f:
        f.write(ORACLE_AUDIT_PY)


def _replace_s1_handler(d, body):
    p = os.path.join(d, "scripts", "run_stages.py")
    s = open(p, encoding="utf-8").read()
    start = s.index("def s1_export(")
    end = s.index("\n\ndef s2_filtered", start)
    s = s[:start] + body + s[end:]
    open(p, "w", encoding="utf-8").write(s)


def g35(d, a):
    """M8 · if False 常量死分支里的写盘不构成 stage 产出"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    if False:\n'
           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g36(d, a):
    """M8 · return 后不可达写盘不构成 stage 产出"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    return None\n'
           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g46(d, a):
    """M8 · 模块级常量绑定后的假分支仍不可达"""
    _replace_s1_handler(
        d, 'S1_ENABLED = False\n\n\n'
           'def s1_export(run_dir):\n'
           '    if S1_ENABLED:\n'
           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g47(d, a):
    """M8 · 函数内常量绑定后的假分支仍不可达"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    enabled = False\n'
           '    if enabled:\n'
           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g48(d, a):
    """M8 · 一元 not 组成的静态假分支仍不可达"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    if not True:\n'
           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g49(d, a):
    """M8 · 布尔短路中含必假项的分支仍不可达"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    if run_dir and False:\n'
           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g50(d, a):
    """M8 · 比较式假分支由隔离真跑兜住，不依赖静态枚举"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if 1 == 2:\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g51(d, a):
    """M8 · 空列表假分支由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if []:\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g52(d, a):
    """M8 · 空字典假分支由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if {}:\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g53(d, a):
    """M8 · 空元组假分支由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if ():\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g54(d, a):
    """M8 ·纯函数 len 假值由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if len([]):\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g55(d, a):
    """M8 · 纯函数 bool 假值由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    if bool(0):\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g56(d, a):
    """M8 · while 比较式假分支由隔离真跑兜住"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    while 1 > 2:\n'
                           '        write(run_dir, "s1_export.json", {"decoy": True})\n')


def g57(d, a):
    """M8 · assert 终止导致的运行崩溃须 fail-closed"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    assert False\n'
                           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g58(d, a):
    """M8 · 真跑探针须禁止 run-dir 外写入"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    with open("/dev/null", "w") as f:\n'
                           '        f.write("sandbox-probe")\n'
                           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g59(d, a):
    """M8 · 真跑探针须禁止网络能力"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    import socket\n'
                           '    sock = socket.socket()\n'
                           '    sock.bind(("127.0.0.1", 0))\n'
                           '    sock.close()\n'
                           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g60(d, a):
    """M8 · 真跑探针须禁止向沙箱外进程发信号"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    import os\n'
                           '    os.kill(os.getppid(), 0)\n'
                           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g61(d, a):
    """M8 · 真跑探针须禁止 fork 与后台进程逃逸"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    import subprocess\n'
                           '    subprocess.run(["/usr/bin/true"], check=True)\n'
                           '    write(run_dir, "s1_export.json", {"decoy": True})\n')


def g62(d, a):
    """M8 · 从上游照抄一份文件不能冒充本段产物"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    with open(os.path.join(run_dir, "s2_filtered.json"),\n'
                           '              encoding="utf-8") as f:\n'
                           '        copied = json.load(f)\n'
                           '    write(run_dir, "s1_export.json", copied)\n')


def g63(d, a):
    """M8 · 零字节普通文件不构成 stage 产物"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    open(os.path.join(run_dir, "s1_export.json"), "wb").close()\n')


def g64(d, a):
    """M8 · 扩展名为 JSON 的垃圾文本不能冒充 stage 产物"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    with open(os.path.join(run_dir, "s1_export.json"),\n'
                           '              "w", encoding="utf-8") as f:\n'
                           '        f.write("not json at all")\n')


def g65(d, a):
    """M8 · 可解析的空壳 JSON 仍须通过本段声明断言"""
    _replace_s1_handler(d, 'def s1_export(run_dir):\n'
                           '    write(run_dir, "s1_export.json", {})\n')


def g66(d, a):
    """M8 · 本段 runner 不得篡改预置的其他 stage 输入"""
    _replace_s1_handler(
        d, 'def s1_export(run_dir):\n'
           '    with open(os.path.join(run_dir, "s2_filtered.json"),\n'
           '              "w", encoding="utf-8") as f:\n'
           '        json.dump({"tampered": True}, f)\n'
           '    art = {"source_id": "orders-panel-2026W32",\n'
           '           "fetched_at": "2026-08-07T10:00:00",\n'
           '           "page_total": len(ROWS), "rows_sha256": content_hash(ROWS),\n'
           '           "rows": ROWS}\n'
           '    write(run_dir, "s1_export.json", art)\n')


AUDIT_REWRITE_TEMPLATE = r'''#!/usr/bin/env python3
"""委托真实解释器后篡改控制信号/逐条输出，供 M10 定向负例。"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
INTERP = os.environ.get("CONTRACT_INTERPRETER")
cmd = [sys.executable, INTERP] + sys.argv[1:] + [
    "--contract", os.path.join(PKG, "assertions.json"), "--package", PKG]
p = subprocess.run(cmd, capture_output=True, text=True)
payload = json.loads(p.stdout)
%s
print(json.dumps(payload, ensure_ascii=False))
sys.exit(%s)
'''


def _rewrite_audit(d, body, exit_expr="p.returncode"):
    p = os.path.join(d, "scripts", "audit.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(AUDIT_REWRITE_TEMPLATE % (body, exit_expr))


def g37(d, a):
    """M10 · rows 明示 FAIL 却返回 rc0，控制信号与证据互相矛盾"""
    _rewrite_audit(d, "# 保留真实 rows，只把退出码恒改为 0", "0")


def g38(d, a):
    """M8 · assertions.json 断言 id 重复，结果映射会覆盖前一条"""
    assertions = a["stages"][0]["operations"][0]["assertions"]
    assertions[1]["id"] = assertions[0]["id"]


def g39(d, a):
    """M7 · SKILL 两张执行段卡重名，set 闭包会吞掉重复声明"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s = s.replace("执行段：s2_filtered", "执行段：s1_export", 1)
    open(p, "w", encoding="utf-8").write(s)


def g40(d, a):
    """M8 · assertions.json 两个 stage 重名，set 闭包会吞掉重复声明"""
    a["stages"][1]["stage"] = a["stages"][0]["stage"]


def g41(d, a):
    """M8 · golden manifest 两个 stage 重名，set 闭包会吞掉重复声明"""
    p = os.path.join(d, "fixtures", "golden", "run_manifest.json")
    manifest = json.load(open(p, encoding="utf-8"))
    manifest["stages"][1]["stage"] = manifest["stages"][0]["stage"]
    with open(p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


def g42(d, a):
    """M7 · `1)` 编号动作行缺三槽且没有命令，不能靠编号变体绕过"""
    _insert_unstructured(d, "7) **动作：** 归档本轮结果")


def g43(d, a):
    """M7 · bullet 动作行缺三槽且没有命令，列表形态同样须四槽"""
    _insert_unstructured(d, "- **动作：** 归档本轮结果")


def g44(d, a):
    """M10 · 审核输出夹带契约未声明的 ghost 断言"""
    _rewrite_audit(d, 'payload["rows"].append({"id": "ghost.assertion", "status": "PASS"})')


def g45(d, a):
    """M10 · 审核输出重复第一条 id，dict 映射会吞掉一条"""
    _rewrite_audit(d, 'payload["rows"].append(dict(payload["rows"][0]))')


def g67(d, a):
    """M10 · 审核器实跑时向验收探针外写副作用，判定本身仍可全绿"""
    p = os.path.join(d, "scripts", "audit.py")
    s = open(p, encoding="utf-8").read()
    needle = "import os\n"
    side_effect = (
        'import sys\n'
        'sys.stderr.write("M10_AUDIT_EXTERNAL_WRITE\\n")\n'
        'open("/private/tmp/metaskill_m10_auditor_escape", "a", '
        'encoding="utf-8").write("escaped\\n")\n')
    if needle not in s:
        raise RuntimeError("G67 找不到 audit.py 注入点")
    open(p, "w", encoding="utf-8").write(s.replace(needle, side_effect + needle, 1))


def g68(d, a):
    """M10 · 审核器实跑时读取验收探针外的主机文件，rows 仍可全绿"""
    p = os.path.join(d, "scripts", "audit.py")
    s = open(p, encoding="utf-8").read()
    needle = "import os\n"
    side_effect = (
        'import sys\n'
        'sys.stderr.write("M10_AUDIT_EXTERNAL_READ\\n")\n'
        'open("/etc/passwd", encoding="utf-8").read()\n')
    if needle not in s:
        raise RuntimeError("G68 找不到 audit.py 注入点")
    open(p, "w", encoding="utf-8").write(s.replace(needle, side_effect + needle, 1))


def g69(d, a):
    """M8 · runner 预植后续审计 stdout/stderr symlink，父进程不得跟随截断"""
    victim = os.path.join(d, "SYMLINK_VICTIM.txt")
    with open(victim, "w", encoding="utf-8") as f:
        f.write("ORIGINAL_VICTIM_CONTENT\n")
    p = os.path.join(d, "scripts", "run_stages.py")
    s = open(p, encoding="utf-8").read()
    needle = "def s1_export(run_dir, MODULE_ENABLED=True):\n"
    helper = (
        'def plant_capture_symlinks(run_dir):\n'
        '    probe_root = os.path.dirname(os.path.abspath(run_dir))\n'
        '    victim = os.path.join(probe_root, "package", "SYMLINK_VICTIM.txt")\n'
        '    for label in ("stage_audit_stdout.txt", "stage_audit_stderr.txt"):\n'
        '        link = os.path.join(probe_root, label)\n'
        '        if os.path.lexists(link):\n'
        '            os.unlink(link)\n'
        '        os.symlink(victim, link)\n\n\n'
        'def s1_export(run_dir, MODULE_ENABLED=True):\n'
        '    plant_capture_symlinks(run_dir)\n')
    if needle not in s:
        raise RuntimeError("G69 找不到 s1 handler 注入点")
    # s1 植入后续 stage_audit 捕获路径；s2 也须独立命中同一边界。
    s = s.replace(needle, helper, 1)
    s = s.replace("def s2_filtered(run_dir):\n",
                  "def s2_filtered(run_dir):\n    plant_capture_symlinks(run_dir)\n", 1)
    open(p, "w", encoding="utf-8").write(s)


MUTANTS = [
    ("G1-no-audit-script", "M8", g1),
    ("G2-op-outside-vocab", "M9", g2),
    ("G3-family-coverage-gap", "M9", g3),
    ("G4-assertion-no-mutant", "M10", g4),
    ("G5-placeholder-residue", "M11", g5),
    ("G6-slot-missing-value-domain", "M7", g6),
    ("G7-backsolve-not-discounted", "M9", g7),
    ("G8-no-fixtures-dir", "M8", g8),
    ("G9-mutant-not-actually-rejected", "M10", g9),
    ("G10-golden-fails-on-positive", "M10", g10),
    ("G11-golden-all-unverified", "M10", g11),
    ("G12-runner-no-stage-flag", "M8", g12),
    ("G13-stage-entrypoint-stub", "M8", g13),
    ("G14-stage-name-docstring-only", "M8", g14),
    ("G15-runner-unrelated-to-stages", "M8", g15),
    ("G16-dispatch-declared-not-used", "M8", g16),
    ("G17-card-missing-value-domain", "M7", g17),
    ("G18-unmarked-exec-command", "M7", g18),
    ("G19-assertions-omits-stage", "M8", g19),
    ("G20-fenced-example-only", "M7", g20),
    ("G21-inline-command-in-prose", "M7", g21),
    ("G22-numbered-prefix-inline-command", "M7", g22),
    ("G23-git-inline-command", "M7", g23),
    ("G24-curl-inline-command", "M7", g24),
    ("G25-relative-script-command", "M7", g25),
    ("G26-poetry-wrapper-command", "M7", g26),
    ("G27-pnpm-command", "M7", g27),
    ("G28-env-prefixed-command", "M7", g28),
    ("G29-absolute-path-command", "M7", g29),
    ("G30-bare-numbered-command", "M7", g30),
    ("G31-indented-command-block", "M7", g31),
    ("G32-empty-slot-shell", "M7", g32),
    ("G33-dead-write-decoy", "M8", g33),
    ("G34-auditor-reads-test-answer", "M10", g34),
    ("G35-constant-dead-write", "M8", g35),
    ("G36-post-return-write", "M8", g36),
    ("G37-audit-exit-row-mismatch", "M10", g37),
    ("G38-duplicate-assertion-id", "M8", g38),
    ("G39-duplicate-skill-stage", "M7", g39),
    ("G40-duplicate-contract-stage", "M8", g40),
    ("G41-duplicate-manifest-stage", "M8", g41),
    ("G42-paren-numbered-missing-slots", "M7", g42),
    ("G43-bullet-action-missing-slots", "M7", g43),
    ("G44-audit-unknown-row", "M10", g44),
    ("G45-audit-duplicate-row", "M10", g45),
    ("G46-module-bound-constant-dead-write", "M8", g46),
    ("G47-local-bound-constant-dead-write", "M8", g47),
    ("G48-not-true-dead-write", "M8", g48),
    ("G49-short-circuit-dead-write", "M8", g49),
    ("G50-compare-dead-write", "M8", g50),
    ("G51-empty-list-dead-write", "M8", g51),
    ("G52-empty-dict-dead-write", "M8", g52),
    ("G53-empty-tuple-dead-write", "M8", g53),
    ("G54-len-empty-dead-write", "M8", g54),
    ("G55-bool-zero-dead-write", "M8", g55),
    ("G56-while-compare-dead-write", "M8", g56),
    ("G57-assert-false-dead-write", "M8", g57),
    ("G58-runtime-external-write", "M8", g58),
    ("G59-runtime-network", "M8", g59),
    ("G60-runtime-signal", "M8", g60),
    ("G61-runtime-fork", "M8", g61),
    ("G62-runtime-copy-upstream", "M8", g62),
    ("G63-runtime-empty-artifact", "M8", g63),
    ("G64-runtime-invalid-json", "M8", g64),
    ("G65-runtime-hollow-json", "M8", g65),
    ("G66-runtime-upstream-mutation", "M8", g66),
    ("G67-auditor-external-write", "M10", g67),
    ("G68-auditor-external-read", "M10", g68),
    ("G69-runner-capture-symlink", "M8", g69),
]

REASONS = {
    "G1-no-audit-script": "缺 scripts/audit.py",
    "G2-op-outside-vocab": "operation 不在封闭词汇表",
    "G3-family-coverage-gap": "最低强断言族缺",
    "G4-assertion-no-mutant": "mutants 为空",
    "G5-placeholder-residue": "TODO",
    "G6-slot-missing-value-domain": "编号步缺槽",
    "G7-backsolve-not-discounted": "最低强断言族缺",
    "G8-no-fixtures-dir": "缺 fixtures/",
    "G9-mutant-not-actually-rejected": "未判 FAIL",
    "G10-golden-fails-on-positive": "正例上",
    "G11-golden-all-unverified": "UNVERIFIED",
    "G12-runner-no-stage-flag": "无执行入口",
    "G13-stage-entrypoint-stub": "无执行入口",
    "G14-stage-name-docstring-only": "无执行入口",
    "G15-runner-unrelated-to-stages": "无执行入口",
    "G16-dispatch-declared-not-used": "无执行入口",
    "G17-card-missing-value-domain": "执行段卡「s2_filtered」缺槽",
    "G18-unmarked-exec-command": "围栏外行内可执行命令未落四槽",
    "G19-assertions-omits-stage": "stage 集不闭合",
    "G20-fenced-example-only": "围栏外无真实",
    "G21-inline-command-in-prose": "围栏外行内可执行命令未落四槽",
    "G22-numbered-prefix-inline-command": "围栏外行内可执行命令未落四槽",
    "G23-git-inline-command": "围栏外行内可执行命令未落四槽",
    "G24-curl-inline-command": "围栏外行内可执行命令未落四槽",
    "G25-relative-script-command": "围栏外行内可执行命令未落四槽",
    "G26-poetry-wrapper-command": "围栏外行内可执行命令未落四槽",
    "G27-pnpm-command": "围栏外行内可执行命令未落四槽",
    "G28-env-prefixed-command": "围栏外行内可执行命令未落四槽",
    "G29-absolute-path-command": "围栏外行内可执行命令未落四槽",
    "G30-bare-numbered-command": "围栏外行内可执行命令未落四槽",
    "G31-indented-command-block": "围栏外行内可执行命令未落四槽",
    "G32-empty-slot-shell": "围栏外行内可执行命令未落四槽",
    "G33-dead-write-decoy": "不可达真实写盘",
    "G34-auditor-reads-test-answer": "审核判定依赖 fixture 名称或 INJECTION.json",
    "G35-constant-dead-write": "不可达真实写盘",
    "G36-post-return-write": "不可达真实写盘",
    "G37-audit-exit-row-mismatch": "退出码与逐条状态不一致",
    "G38-duplicate-assertion-id": "断言 id 重复",
    "G39-duplicate-skill-stage": "执行段卡名称重复",
    "G40-duplicate-contract-stage": "assertions.json stage 名重复",
    "G41-duplicate-manifest-stage": "stage 名重复",
    "G42-paren-numbered-missing-slots": "编号步缺槽",
    "G43-bullet-action-missing-slots": "列表步缺槽",
    "G44-audit-unknown-row": "审核输出含未声明断言",
    "G45-audit-duplicate-row": "审核输出断言 id 重复",
    "G46-module-bound-constant-dead-write": "不可达真实写盘",
    "G47-local-bound-constant-dead-write": "不可达真实写盘",
    "G48-not-true-dead-write": "不可达真实写盘",
    "G49-short-circuit-dead-write": "不可达真实写盘",
    "G50-compare-dead-write": "隔离真跑未产出",
    "G51-empty-list-dead-write": "隔离真跑未产出",
    "G52-empty-dict-dead-write": "隔离真跑未产出",
    "G53-empty-tuple-dead-write": "隔离真跑未产出",
    "G54-len-empty-dead-write": "隔离真跑未产出",
    "G55-bool-zero-dead-write": "隔离真跑未产出",
    "G56-while-compare-dead-write": "隔离真跑未产出",
    "G57-assert-false-dead-write": "隔离真跑未产出",
    "G58-runtime-external-write": "隔离真跑未产出",
    "G59-runtime-network": "隔离真跑未产出",
    "G60-runtime-signal": "隔离真跑未产出",
    "G61-runtime-fork": "隔离真跑未产出",
    "G62-runtime-copy-upstream": "现跑产物未通过本段断言",
    "G63-runtime-empty-artifact": "现跑产物未通过本段断言",
    "G64-runtime-invalid-json": "现跑产物未通过本段断言",
    "G65-runtime-hollow-json": "现跑产物未通过本段断言",
    "G66-runtime-upstream-mutation": "现跑产物未通过本段断言",
    "G67-auditor-external-write": "审核脚本写入探针外",
    "G68-auditor-external-read": "审核脚本读取探针外",
    "G69-runner-capture-symlink": "输出捕获拒绝",
}


def _registry_spec():
    with open(REGISTRY, encoding="utf-8") as f:
        spec = json.load(f)["suites"]["gate-fixtures"]
    actual = {name: [gate, REASONS[name]] for name, gate, _fn in MUTANTS}
    if actual != spec["directed"] or spec["positive"] != "G0-good":
        raise RuntimeError("fixture_registry.json 与 make_gate_fixtures.MUTANTS/REASONS 漂移")
    return spec


def main():
    root = sys.argv[1]
    spec = _registry_spec()  # 先核权威登记，再碰生成目录
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    good = build_good(root)
    print("built G0-good  (正例 · 五闸须全过)")
    for name, gate, fn in MUTANTS:
        d = os.path.join(root, name)
        shutil.copytree(good, d)
        with open(os.path.join(d, "assertions.json"), encoding="utf-8") as f:
            a = json.load(f)
        fn(d, a)
        with open(os.path.join(d, "assertions.json"), "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False, indent=1)
        with open(os.path.join(d, "GATE_INJECTION.json"), "w", encoding="utf-8") as f:
            json.dump({"fixture_id": name, "must_be_rejected_by": gate,
                       "must_include_reason": REASONS[name],
                       "positive_control": "G0-good",
                       "doc": (fn.__doc__ or "").strip()}, f, ensure_ascii=False, indent=1)
        print(f"built {name}  must_reject={gate}")
    with open(os.path.join(root, "_fixture_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"suite": "gate-fixtures", "positive": spec["positive"],
                   "directed": sorted(spec["directed"])}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
