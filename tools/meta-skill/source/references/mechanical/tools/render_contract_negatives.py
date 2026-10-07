#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_contract_negatives.py — `compare_paths` 三条写法负例的永久门。

与 mutant 语料的分工：mutant 坏的是**产物**（数据错了，断言该抓），本器坏的是
**契约**（断言自己写坏了，解释器该拒）。两者都要有——一条恒真的断言在任何
mutant 上都不会露头，因为它压根不判什么，产物再对它也照样绿。

三种坏法各挡一面：

  * `cp-empty`      compare_paths: [] —— 逐项遍历零次即返回真。恒真断言登记在
                    册比不登记更坏：它占着 render 的最低族名额，M9 覆盖判定认它
                    满足了，而它对成品件零约束。
  * `cp-no-input` / `cp-no-output`
                    只给一端。让解释器"按同名去对侧找"就是把对应关系交给命名
                    巧合——OAQ 里两端本就不同名（`lists_public.<桶>` ↔
                    `lists.<桶>`），上游改名时同名推断会安静地配错一对。
  * `cp-dual-idiom` compare_paths 与 compare_map 并存。同一条断言两种口径时，
                    判据取哪个由实现里 if 的先后决定——那就不是判据。

判据同 accept_matrix：不是「跑出 FAIL 就算过」，而是**被坏的那条自己拒掉**，
理由指向被坏的那一处。

`final.output_field_coverage` 一并报是**真实依赖不是旁落**：坏掉的这条断言承载
七条直连路径的读取，它不求值则那些路径无人读过，覆盖那条本就该红。旁落为零反倒
说明覆盖没在看。故判据写成「FAIL 集恰为 {被坏的那条, 覆盖那条}」——把覆盖从预期
里删掉会让这个门在覆盖失灵时照样绿。

另跑一条未改动的正例对照，防止本器因为别的原因恒红（恒红的负例门与恒绿的断言
是同一个病）。

用法: python3 render_contract_negatives.py [<runs_root> <contract> <source>]
退出码 0 = 五例全合格；1 = 有不合格项。
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
AUDIT = os.path.normpath(os.path.join(ROOT, "..", "v3.8-draft", "scripts", "audit.py"))

TARGET = "final.render_source_replay"
COVERAGE = "final.output_field_coverage"
GOLDEN = "golden-task1"
# 被坏的那条不求值 → 它承载的七条直连路径无人读过 → 覆盖那条必红。这是依赖，
# 不是判据松动：把 COVERAGE 从预期里去掉，本门在覆盖失灵时照样判合格。
WANT_FAILS = {TARGET, COVERAGE}


def _find(con, aid):
    for st in con["stages"]:
        for op in st["operations"]:
            for a in op["assertions"]:
                if a["id"] == aid:
                    return a
    raise KeyError(f"契约里没有断言 {aid}——基线变了，负例失去附着点")


def n_empty(a):
    a["predicate"]["compare_paths"] = []


def n_no_input(a):
    a["predicate"]["compare_paths"][0].pop("input")


def n_no_output(a):
    a["predicate"]["compare_paths"][0].pop("output")


def n_dual(a):
    a["predicate"]["compare_map"] = "counts"


NEGATIVES = [
    ("cp-empty", n_empty, "为空或非列表"),
    ("cp-no-input", n_no_input, "须同时显式声明"),
    ("cp-no-output", n_no_output, "须同时显式声明"),
    ("cp-dual-idiom", n_dual, "同时声明"),
]


def audit(run_dir, contract, source):
    cmd = [sys.executable, AUDIT, run_dir, "--contract", contract, "--all", "--json"]
    if source:
        cmd += ["--source", source]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(p.stdout), p.returncode
    except json.JSONDecodeError:
        return {"rows": [], "verdict": "ERROR", "stderr": p.stderr[-600:]}, p.returncode


def main():
    runs_root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "runs")
    con_path = (sys.argv[2] if len(sys.argv) > 2
                else os.path.join(ROOT, "fixtures", "assertions_oaq.json"))
    source = (sys.argv[3] if len(sys.argv) > 3
              else os.path.join(ROOT, "fixtures", "mock-task1.md"))
    base = json.load(open(con_path, encoding="utf-8"))
    run_dir = os.path.join(runs_root, GOLDEN)

    problems = []
    tmp = tempfile.mkdtemp(prefix="cp_neg_")

    # 正例对照：契约一字未改，须全 PASS。恒红的负例门不构成检验。
    rep, rc = audit(run_dir, con_path, source)
    fails = [r["id"] for r in rep["rows"] if r["status"] == "FAIL"]
    ok0 = rc == 0 and not fails
    print(f"{'cp-baseline':<16} rc={rc} verdict={rep.get('verdict')} "
          f"FAIL={fails or '无'}  {'[OK]' if ok0 else '[BAD]'}")
    if not ok0:
        problems.append(f"cp-baseline: 未改动的契约本该全 PASS，实为 rc={rc} FAIL={fails}")

    for name, fn, want_sub in NEGATIVES:
        con = copy.deepcopy(base)
        fn(_find(con, TARGET))
        path = os.path.join(tmp, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(con, f, ensure_ascii=False, indent=1)
        rep, rc = audit(run_dir, path, source)
        rows = {r["id"]: r for r in rep["rows"]}
        fails = {i for i, r in rows.items() if r["status"] == "FAIL"}
        detail = rows.get(TARGET, {}).get("detail", "")
        ok = (rc == 1 and fails == WANT_FAILS and want_sub in detail)
        print(f"{name:<16} rc={rc} FAIL={sorted(fails)}  理由含「{want_sub}」="
              f"{want_sub in detail}  {'[OK]' if ok else '[BAD]'}")
        if not ok:
            if fails != WANT_FAILS:
                problems.append(f"{name}: FAIL 集须为 {sorted(WANT_FAILS)}，"
                                f"实为 {sorted(fails)}")
            if want_sub not in detail:
                problems.append(f"{name}: 拒绝理由未含「{want_sub}」，实为「{detail}」")
            if rc != 1:
                problems.append(f"{name}: 退出码须 1（FAIL），实为 {rc}")

    print(f"\n总判定: {'PASS' if not problems else 'FAIL'}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
