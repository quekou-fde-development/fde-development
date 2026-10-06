#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_custom_fixtures.py — custom operation 三条件闸 + 持久包判定的定向料。

存在理由：三条件（独立 golden / 定向 mutant / 来源锚）此前只验「三个键非空」，
填三个字符串就能开一个 custom operation，默认 FAIL 的设定当场失效。加固后的
闸要验实物与实跑，故必须有一组真能跑起来的料来证伪它——闸自己没被证伪过，
就只是条文。

C0 是正例：真 golden 真 PASS、真 mutant 被它指名的那条断言真 FAIL、
来源锚解析到 SKILL.md 里真实存在的标题。C1-C6 各从 C0 复制后定点坏一处。
P1 验的是另一回事：持久包判定——包里既无 assertions.json 也无两类脚本时，
带 --persistent 跑必须被拒，不得整体 SKIP 成退出码 0。

用法: python3 make_custom_fixtures.py <out_root>
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.normpath(os.path.join(HERE, "..", "fixture_registry.json"))

SKILL_MD = """---
name: custom-gate-probe
description: custom operation 三条件闸的定向验收料。验 golden 真 PASS、mutant 真被指名断言拒、来源锚真解析。
metadata:
  updated: 2026-08-07
  workflow_mode: artifact
---

# custom-gate-probe

## 第 1 步 · 配平

1. **动作：** 按配平规则算每桶余量落 c1_balance.json **副作用：** run_dir_only **依据：** 本文 §配平规则 **产出：** `c1_balance.json` 落 run 目录 **值域：** residuals 每桶 ∈ 实数；checksum ∈ 非负整数

执行段：c1_balance
动作：按配平规则逐桶计算余量并落盘
副作用：run_dir_only
可达接口：`python3 scripts/run_c1_balance.py --run-dir runs/<run-id>`
依据：本文 §配平规则
产出：c1_balance.json（residuals + checksum + buckets）
值域：residuals 各值 ∈ 实数；checksum ∈ 非负整数；buckets[].name / inflow_observed ∈ 字符串
断言：c1.balance / c1.inflow_source

## 配平规则

每桶 `residual = inflow − outflow`。全桶 residual 之和须等于 `checksum`
声明的值；不等即账不平。本规则是 `c1.balance` 断言的判据出处——断言不能自证，
「按什么判」这一问必须能指回一份人写的规则文。

## 桶枚举规则

`residuals` 里每个桶都要能被独立枚举出成员名单，只给数字不给名单的桶不算数。

## 入库源表

`buckets[].inflow_observed` 是从下表逐格抄下来的观测值，回源比对以本表为准。

| 桶 | 入库量 |
|---|---|
| 自制 | 12 |
| 委外 | 8 |
| 外购 | 4 |
"""

# 源件（fixtures/source_buckets.md）——T2 回源族的比对对象。
# 顶层标题不能以小节名「入库」开头：`_pick_section` 用 startswith 认小节，
# 「入库源表」会先命中，取回一个没有表的小节，于是每个键都查不到。
SOURCE_MD = """# 桶入库观测源

## 入库

| 桶 | 入库量 |
|---|---|
| 自制 | 12 |
| 委外 | 8 |
| 外购 | 4 |
"""

# 一个真能跑的 custom operation。family 用解释器已有的 total_reconciliation：
# custom 说的是 operation 形态在封闭词汇表外，不是断言族可以现编。
ASSERTIONS = {
    "package": "custom-gate-probe",
    "contract_ir_version": "1.0",
    "stages": [
        {"stage": "c1_balance", "operations": [{
            "op": "custom:bucket_balance",
            "artifact": "c1_balance.json",
            "source_reachability": "machine",
            "custom_enablement": {
                "independent_golden": "fixtures/golden-custom",
                "directed_mutant": "fixtures/M-custom-imbalance",
                "source_anchor": "SKILL.md §配平规则",
            },
            "assertions": [
                {"id": "c1.balance", "family": "total_reconciliation", "tier": 1,
                 "predicate": {"declared_total": "checksum",
                               "parts": ["residuals.自制", "residuals.委外",
                                         "residuals.外购"]},
                 "derived_fields": [], "source_anchor": "SKILL.md §配平规则",
                 "mutants": ["M-custom-imbalance"]},
                # T2 回源族。C8 就地把它降成 T1 来验 family↔tier 预检：
                # 这一族真读源，标 T1 后无源时会判 FAIL 而不是 UNVERIFIED，
                # 把「没法验」谎报成「验过了、不成立」。
                {"id": "c1.inflow_source", "family": "source_readback", "tier": 2,
                 "predicate": {"collection": "buckets", "key_field": "name",
                               "id_field": "name", "observed_field": "inflow_observed",
                               "source": {"format": "markdown_table",
                                          "section": "入库", "key_col": 0,
                                          "value_col": 1}},
                 "derived_fields": [], "source_anchor": "SKILL.md §入库源表",
                 "mutants": ["M-custom-imbalance"]},
            ]}]},
    ],
}

AUDIT_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit.py — 薄封装：把 assertions.json 交给通用断言解释器。

不含业务计算：断言是数据，解释器是代码。故意不 import 执行脚本的任何函数。
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

RUN_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_c1_balance.py — 执行脚本：算每桶余量并落盘。只执行，不自检。

文件名即它认领的段（`run_<段名>.py`）。单段包不走 `--stage` 分发：只有一段
时字典 dispatch 是多余的一层，而「哪个脚本跑哪段」这件事仍须在机械面可判，
文件名就是那份声明。
"""
import argparse
import json
import os
import sys

BUCKETS = [{"name": "自制", "inflow": 12, "outflow": 5},
           {"name": "委外", "inflow": 8, "outflow": 3},
           {"name": "外购", "inflow": 4, "outflow": 4}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.run_dir, exist_ok=True)
    residuals = {b["name"]: b["inflow"] - b["outflow"] for b in BUCKETS}
    art = {"residuals": residuals, "checksum": sum(residuals.values()),
           # 逐桶明细：桶名 + 从源表逐格抄下来的入库量。回源族逐行取 key
           # 与观测字段，故须是 list-of-dict；观测值存字符串——源表读出来
           # 就是字符串，在账本侧先转成 int 等于把「抄写是否忠实」这一问
           # 提前答掉，回源比对就比不出抄错了。
           "buckets": [{"name": b["name"], "inflow_observed": str(b["inflow"])}
                       for b in BUCKETS]}
    with open(os.path.join(a.run_dir, "c1_balance.json"), "w", encoding="utf-8") as f:
        json.dump(art, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

GOLDEN = {"residuals": {"自制": 7, "委外": 5, "外购": 0}, "checksum": 12,
          "buckets": [{"name": "自制", "inflow_observed": "12"},
                      {"name": "委外", "inflow_observed": "8"},
                      {"name": "外购", "inflow_observed": "4"}]}

# 定向 mutant：checksum 与分项之和不符（c1.balance 拒），且「委外」入库量
# 与源表不符（c1.inflow_source 拒）。两条断言各有一处对应的错——
# `_check_custom` 要求本 op 每条断言都被指名，指名了就得真拒得动。
MUTANT = {"residuals": {"自制": 7, "委外": 5, "外购": 0}, "checksum": 14,
          "buckets": [{"name": "自制", "inflow_observed": "12"},
                      {"name": "委外", "inflow_observed": "9"},
                      {"name": "外购", "inflow_observed": "4"}]}


def build_good(root):
    d = os.path.join(root, "C0-good")
    os.makedirs(os.path.join(d, "scripts"))
    os.makedirs(os.path.join(d, "fixtures", "golden-custom"))
    os.makedirs(os.path.join(d, "fixtures", "M-custom-imbalance"))
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD)
    with open(os.path.join(d, "assertions.json"), "w", encoding="utf-8") as f:
        json.dump(ASSERTIONS, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "scripts", "audit.py"), "w", encoding="utf-8") as f:
        f.write(AUDIT_PY)
    with open(os.path.join(d, "scripts", "run_c1_balance.py"), "w", encoding="utf-8") as f:
        f.write(RUN_PY)
    with open(os.path.join(d, "fixtures", "golden-custom", "c1_balance.json"),
              "w", encoding="utf-8") as f:
        json.dump(GOLDEN, f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "fixtures", "golden-custom", "run_manifest.json"),
              "w", encoding="utf-8") as f:
        json.dump({"stages": [{"stage": "c1_balance"}]},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "fixtures", "M-custom-imbalance", "c1_balance.json"),
              "w", encoding="utf-8") as f:
        json.dump(MUTANT, f, ensure_ascii=False, indent=1)
    # 源件放 fixtures/source*.md：validate 的 _find_source 按此前缀找，
    # 找到才把 --source 传给实跑，T2 族才判得动而不是整片 UNVERIFIED。
    with open(os.path.join(d, "fixtures", "source_buckets.md"),
              "w", encoding="utf-8") as f:
        f.write(SOURCE_MD)
    with open(os.path.join(d, "fixtures", "M-custom-imbalance", "INJECTION.json"),
              "w", encoding="utf-8") as f:
        json.dump({"mutant_id": "M-custom-imbalance", "baseline": "golden-custom",
                   "operation": "custom:bucket_balance",
                   "must_be_rejected_by": "c1.balance/c1.inflow_source",
                   "doc": "checksum 与分项之和不符——账不平；且委外入库量与源表不符"},
                  f, ensure_ascii=False, indent=1)
    return d


# ---- 各条件的定向坏法 -----------------------------------------------

def c1(d, a):
    """M9 · golden/mutant 是塞满垃圾的非空目录——目录在位不等于料成立

    旧闸只验「目录存在且非空」，两个塞了随便什么文件的目录照样过。
    加固后 golden 必须真跑出零 FAIL，垃圾目录跑不出产物即被拒。
    """
    for sub in ("golden-custom", "M-custom-imbalance"):
        p = os.path.join(d, "fixtures", sub, "c1_balance.json")
        if os.path.exists(p):
            os.remove(p)
        with open(os.path.join(d, "fixtures", sub, "junk.txt"), "w",
                  encoding="utf-8") as f:
            f.write("这不是产物，只是让目录非空的东西\n")


def c2(d, a):
    """M9 · source_anchor 指向不存在的文件（裸 bogus.md）

    旧判据是 `"§" not in anchor and ".md" not in anchor`——两个否定用 and 连，
    沾上其中一样就过：裸 bogus.md 过，裸 § 也过，文件在不在从不解析。
    """
    a["stages"][0]["operations"][0]["custom_enablement"]["source_anchor"] = \
        "bogus.md §配平规则"


def c3(d, a):
    """M9 · source_anchor 的文件在、标题不在——锚点悬空"""
    a["stages"][0]["operations"][0]["custom_enablement"]["source_anchor"] = \
        "SKILL.md §从来没有这一节"


def c4(d, a):
    """M9 · 路径逃逸：golden 指到包外

    包外的料不受本包审核约束，随时可变；拿它当三条件的实物等于把判据托管出去。
    """
    a["stages"][0]["operations"][0]["custom_enablement"]["independent_golden"] = \
        "../C0-good/fixtures/golden-custom"


def c5(d, a):
    """M9 · 同料不同路径：mutant 是 golden 的逐字节副本

    旧闸比的是 normpath 后的路径串，两个目录名不同就算「不是同一份料」。
    实际内容一模一样时，正例反例同源，对照是假的。
    """
    src = os.path.join(d, "fixtures", "golden-custom", "c1_balance.json")
    dst = os.path.join(d, "fixtures", "M-custom-imbalance", "c1_balance.json")
    shutil.copyfile(src, dst)


def c6(d, a):
    """M9 · mutant 里的错不在被指名的那条断言上

    产物本身是干净的（账平），c1.balance 在它上面 PASS。「有个 mutant 目录」
    与「这条断言被证伪过」是两回事——判据是被它指名的那条拒。
    """
    p = os.path.join(d, "fixtures", "M-custom-imbalance", "c1_balance.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(GOLDEN, f, ensure_ascii=False, indent=1)
    # 与 C5 区分：改个无关字段，使内容指纹与 golden 不同，
    # 于是「同料」那条不触发，只剩「指名的断言没拒」这一条。
    with open(p, encoding="utf-8") as f:
        obj = json.load(f)
    obj["note"] = "内容与 golden 不同，但账仍然是平的"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def c7(d, a):
    """M9 · 同载荷不同元数据：mutant 载荷与 golden 逐字节相同，只多了 INJECTION.json

    指纹若把 INJECTION.json 一起算进去，两份料就永远「不同」——因为 mutant
    按规定必须带这个文件而 golden 不带。同料换目录名这一形态于是永远抓不到，
    指纹闸看着在跑，实际恒真。故比对必须只取**载荷**。
    """
    src = os.path.join(d, "fixtures", "golden-custom", "c1_balance.json")
    dst = os.path.join(d, "fixtures", "M-custom-imbalance", "c1_balance.json")
    shutil.copyfile(src, dst)
    # INJECTION.json 保留（元数据），载荷两边全等——只有排除元数据的指纹能识破


def c8(d, a):
    """M9 · 回源族被降成 T1——family↔tier 不符，且顺手废掉 UNVERIFIED 语义

    `source_readback` 真读源，IR 把它登记为 T2 专用族。降成 T1 后源不可达时
    它不再走 UNVERIFIED 短路，而是照常求值、判 FAIL——「没法验」被谎报成
    「验过了、不成立」。反向（把机械可判的族标成 T2）是另一半：借「源不可达
    → UNVERIFIED」让一条断言从不判又不变红。两个方向同一条预检拒。

    这条不与 C5/C6 撞车：料本身没动，坏的是契约的 family↔tier 登记面。
    """
    for asst in a["stages"][0]["operations"][0]["assertions"]:
        if asst["id"] == "c1.inflow_source":
            asst["tier"] = 1


def c9(d, a):
    """M9 · 来源锚只是某个真标题的子串——指向哪一节不确定

    SKILL.md 里有「配平规则」这一节。锚点写 `§配平` 时，子串匹配会认它成立，
    但读的人无从确定指的是哪一节；一旦再加一节「配平规则补遗」，同一个锚点
    同时匹配两节。锚点的全部作用是把断言钉到某一节具体条文上。
    """
    a["stages"][0]["operations"][0]["custom_enablement"]["source_anchor"] = \
        "SKILL.md §配平"


def c10(d, a):
    """M9 · 机械可判的族被标成 T2——借 UNVERIFIED 把断言从「须成立」降成「没判过」

    与 C8 反向，是这条预检更危险的那一半：`total_reconciliation` 不读源，
    标 T2 后只要不给 `--source`，它就走 UNVERIFIED 短路——不进 failed 计数、
    不阻断交付、退出码不变红。防线被摘掉，而摘的动作看起来是「更保守」。
    """
    for asst in a["stages"][0]["operations"][0]["assertions"]:
        if asst["id"] == "c1.balance":
            asst["tier"] = 2


MUTANTS = [
    ("C1-junk-artifacts", "M9", c1),
    ("C2-anchor-file-missing", "M9", c2),
    ("C3-anchor-heading-missing", "M9", c3),
    ("C4-path-escape", "M9", c4),
    ("C5-same-content-diff-path", "M9", c5),
    ("C6-mutant-not-rejected-by-named", "M9", c6),
    ("C7-same-payload-diff-metadata", "M9", c7),
    ("C8-t2-family-marked-t1", "M9", c8),
    ("C9-anchor-substring-only", "M9", c9),
    ("C10-strong-family-marked-t2", "M9", c10),
]

REASONS = {
    "C1-junk-artifacts": "golden 与 mutant 载荷指纹相同",
    "C2-anchor-file-missing": "bogus.md 不存在",
    "C3-anchor-heading-missing": "没有标题",
    "C4-path-escape": "解析后逃出包外",
    "C5-same-content-diff-path": "golden 与 mutant 载荷指纹相同",
    "C6-mutant-not-rejected-by-named": "未判 FAIL",
    "C7-same-payload-diff-metadata": "golden 与 mutant 载荷指纹相同",
    "C8-t2-family-marked-t1": "family↔tier 不符",
    "C9-anchor-substring-only": "没有标题",
    "C10-strong-family-marked-t2": "family↔tier 不符",
}


def _registry_spec():
    with open(REGISTRY, encoding="utf-8") as f:
        spec = json.load(f)["suites"]["custom-fixtures"]
    actual = {name: [gate, REASONS[name]] for name, gate, _fn in MUTANTS}
    actual["P1-persistent-but-empty"] = ["M8", "缺 assertions.json"]
    if actual != spec["directed"] or spec["positive"] != "C0-good":
        raise RuntimeError("fixture_registry.json 与 make_custom_fixtures.MUTANTS/REASONS 漂移")
    return spec


def build_persistence_negative(root):
    """P1 · 持久包判定：既无 assertions.json 也无两类脚本，带 --persistent 必须被拒。

    这条验的是 SKILL.md 第 8 步的调用形态：自动触发（「包内有 assertions.json
    才开 M8-M11」）把闸的判据接到了闸自己要求的那个文件上——文件不在时闸整体
    SKIP，退出码 0，最该被拒的形态反而放行。
    """
    d = os.path.join(root, "P1-persistent-but-empty")
    os.makedirs(d)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(SKILL_MD)
    with open(os.path.join(d, "GATE_INJECTION.json"), "w", encoding="utf-8") as f:
        json.dump({"fixture_id": "P1-persistent-but-empty",
                   "must_be_rejected_by": "M8",
                   "must_include_reason": "缺 assertions.json",
                   "positive_control": "C0-good",
                   "needs_persistent_flag": True,
                   "doc": build_persistence_negative.__doc__.strip().splitlines()[0]},
                  f, ensure_ascii=False, indent=1)
    print("built P1-persistent-but-empty  must_reject=M8  (须带 --persistent 跑)")


def main():
    root = sys.argv[1]
    spec = _registry_spec()  # 先核权威登记，再碰生成目录
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    good = build_good(root)
    print("built C0-good  (正例 · 三条件须全过)")
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
                       "positive_control": "C0-good",
                       "doc": (fn.__doc__ or "").strip().splitlines()[0]},
                      f, ensure_ascii=False, indent=1)
        print(f"built {name}  must_reject={gate}")
    build_persistence_negative(root)
    with open(os.path.join(root, "_fixture_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"suite": "custom-fixtures", "positive": spec["positive"],
                   "directed": sorted(spec["directed"])}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
