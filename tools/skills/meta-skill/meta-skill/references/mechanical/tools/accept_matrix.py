#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""accept_matrix.py — 解释器验收：golden 假阳性对照 + 每条断言的定向 mutant 拒绝。

判据（contract_ir §9）三条，缺一即整体 FAIL：
  1. 正例 golden：全断言 PASS，零 FAIL。
  2. 定向 mutant：每个 mutant 必须**被它登记的那条断言**拒绝。
     只要「跑出 FAIL」不算过——错的断言抓错的错，等于没抓。
  3. 覆盖：assertions.json 里每条强断言都至少有一个 mutant 指名它。
  4. 词汇表覆盖：contract_ir 封闭词汇表里每个 operation 都有定向 mutant 料，
     否则该 operation 的最低谓词族从未被证伪（8/8，缺一即 FAIL）。

用法: python3 accept_matrix.py <runs_root> <contract> <src_task1> <src_task3> <out_json>
            [<extra_runs_root> <extra_contract>]...
附加套件成对给，可重复：主套件九段里没有 join / handoff / 多 operation 同段这
几种形态，各自另立契约与语料。写死「最多一对」时，第二套（runs-multiop）就没有
位置可挂——语料躺在盘上、矩阵不跑它，X1-X3 是死料而输出照样全绿。
退出码 0 = 全过；1 = 有不合格项。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft", "scripts", "audit.py"))
IR = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft", "references", "contract_ir.json"))

TASK3_RUNS = {"golden-task3", "E8-outsource-route-reversal"}
GOLDENS = ["golden-task1", "golden-task3"]

# E 族的预注册预期（fixtures/derivation.md，跑前写定，不迁就实现）
E_EXPECT = {
    "E1-whitelist-always-false": "s6.whitelist_rule_replay",
    "E2-today-start-shift": "s4.assignment_rule_replay",
    "E3-silent-row-drop": "s2.excluded_count",
    "E4-attr-route-contradiction": "s3.attr_rule_replay",
    "E5-pipeline-drop": "s5.key_preservation",
    "E6-whitelist-shrunk": "s6.whitelist_rule_replay",
    "E7-double-count": "s8.total_reconciliation",
    "E8-outsource-route-reversal": "s5.route_rule_replay",
    "E9-forced-balance": "s8.each_bucket_enumerable",
    "E10-observation-miscopy": "s6.source_readback",
}


def audit(run_dir, contract, source):
    cmd = [sys.executable, AUDIT, run_dir, "--contract", contract, "--all", "--json"]
    if source:
        cmd += ["--source", source]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(p.stdout), p.returncode
    except json.JSONDecodeError:
        return {"rows": [], "verdict": "ERROR", "stderr": p.stderr[-800:]}, p.returncode


def failed_ids(rep):
    return [r["id"] for r in rep["rows"] if r["status"] == "FAIL"]


def declared_of(contract_path):
    """契约里登记的全部断言 + 它们各自登记的 mutant。"""
    con = json.load(open(contract_path, encoding="utf-8"))
    out = {}
    for st in con["stages"]:
        for op in st["operations"]:
            for a in op["assertions"]:
                out[a["id"]] = {"family": a["family"], "tier": a["tier"],
                                "op": op["op"], "mutants": a.get("mutants", [])}
    return out


def run_suite(root, contract, results, problems, src=None):
    """跑一套「正例 golden + 定向 mutant」料。

    与主套件同判据：golden 零 FAIL；每个 mutant 被它 INJECTION.json 里
    登记的那条断言拒。旁落到别的断言不算过。

    「是不是 mutant」按 **INJECTION.json 在不在** 判，不按目录名前缀判。
    前缀白名单（曾写死 ("J","H")）会把不在名单里的 mutant 目录**静默跳过**：
    jh 套件后来加的 R1-R3 三个 acquire mutant 一条都没跑，矩阵照样报全绿——
    漏跑与全过在输出上不可分，正是这套矩阵存在要挡的那类错。
    """
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        inj_path = os.path.join(d, "INJECTION.json")
        if name.startswith("golden"):
            rep, ec = audit(d, contract, src)
            fails = failed_ids(rep)
            results[name] = {"kind": "golden", "verdict": rep["verdict"], "exit": ec,
                             "n_pass": rep.get("counts", {}).get("passed"), "failed": fails}
            if fails:
                problems.append(f"{name}: golden 出现假阳性 {fails}")
            continue
        if not os.path.isfile(inj_path):
            # 既不是 golden 又没有注入登记的目录：报出来，不静默略过
            problems.append(f"{root}/{name}: 目录既非 golden 又无 INJECTION.json——"
                            "无法判定它该被哪条断言拒，不计入覆盖")
            continue
        inj = json.load(open(inj_path, encoding="utf-8"))
        rep, ec = audit(d, contract, src)
        fails = failed_ids(rep)
        want = [w.strip() for w in inj["must_be_rejected_by"].split("/")]
        hit = any(w in fails for w in want)
        results[name] = {"kind": "M-directed", "operation": inj["operation"],
                         "verdict": rep["verdict"], "exit": ec,
                         "must_be_rejected_by": want, "hit": hit, "failed": fails,
                         "also_fails": inj.get("also_fails", [])}
        if not hit:
            problems.append(f"{name}: 应由 {want} 拒绝，实际 FAIL={fails}")


def main():
    root, contract, src1, src3, out_path = sys.argv[1:6]
    rest = sys.argv[6:]
    if len(rest) % 2:
        print("附加套件须成对给：<runs_root> <contract>", file=sys.stderr)
        return 2
    extra_suites = list(zip(rest[0::2], rest[1::2]))
    results, problems = {}, []

    # 契约里登记的全部断言 + 它们各自登记的 mutant
    con = json.load(open(contract, encoding="utf-8"))
    declared = {}
    for st in con["stages"]:
        for op in st["operations"]:
            for a in op["assertions"]:
                declared[a["id"]] = {"family": a["family"], "tier": a["tier"],
                                     "op": op["op"], "mutants": a.get("mutants", [])}

    # ---- 1. golden 假阳性对照
    for g in GOLDENS:
        src = src3 if g in TASK3_RUNS else src1
        rep, ec = audit(os.path.join(root, g), contract, src)
        fails = failed_ids(rep)
        results[g] = {"kind": "golden", "verdict": rep["verdict"], "exit": ec,
                      "n_pass": rep.get("counts", {}).get("passed"), "failed": fails}
        if fails:
            problems.append(f"{g}: golden 出现假阳性 {fails}")

    # ---- 2. E 族按预注册预期
    for run, expect in sorted(E_EXPECT.items()):
        src = src3 if run in TASK3_RUNS else src1
        rep, ec = audit(os.path.join(root, run), contract, src)
        fails = failed_ids(rep)
        hit = expect in fails
        results[run] = {"kind": "E-injection", "verdict": rep["verdict"], "exit": ec,
                        "expect_assert": expect, "hit": hit, "failed": fails}
        if not hit:
            problems.append(f"{run}: 预注册应由 {expect} 检出，实际 FAIL={fails}")

    # ---- 3. M 族定向 mutant：必须被登记的那条断言拒绝
    for name in sorted(os.listdir(root)):
        if not name.startswith("M"):
            continue
        inj_path = os.path.join(root, name, "INJECTION.json")
        if not os.path.isfile(inj_path):
            continue
        inj = json.load(open(inj_path, encoding="utf-8"))
        src = src3 if name in TASK3_RUNS else src1
        rep, ec = audit(os.path.join(root, name), contract, src)
        fails = failed_ids(rep)
        want = [w.strip() for w in inj["must_be_rejected_by"].split("/")]
        hit = any(w in fails for w in want)
        results[name] = {"kind": "M-directed", "operation": inj["operation"],
                         "verdict": rep["verdict"], "exit": ec,
                         "must_be_rejected_by": want, "hit": hit, "failed": fails}
        if not hit:
            problems.append(f"{name}: 应由 {want} 拒绝，实际 FAIL={fails}")

    # ---- 4. 附加套件（各带独立契约，同判据）
    for x_root, x_contract in extra_suites:
        run_suite(x_root, x_contract, results, problems)
        declared.update(declared_of(x_contract))

    # ---- 5. 覆盖：每条强断言都得有 mutant 指名它
    all_mutant_targets = set()
    for r in results.values():
        if r["kind"] == "M-directed":
            all_mutant_targets |= set(r["must_be_rejected_by"])
        elif r["kind"] == "E-injection":
            all_mutant_targets.add(r["expect_assert"])
    uncovered = [aid for aid in declared if aid not in all_mutant_targets]
    for aid in uncovered:
        problems.append(f"断言 {aid} 无定向 mutant——未经证伪，不构成检验")

    # ---- operation 覆盖表
    by_op = {}
    for aid, meta in declared.items():
        by_op.setdefault(meta["op"], {"assertions": [], "mutants": set()})
        by_op[meta["op"]]["assertions"].append(aid)
        if aid in all_mutant_targets:
            by_op[meta["op"]]["mutants"].add(aid)
    op_table = {k: {"assertions": len(v["assertions"]),
                    "with_mutant": len(v["mutants"]),
                    "uncovered": sorted(set(v["assertions"]) - v["mutants"])}
                for k, v in sorted(by_op.items())}

    # ---- 6. 词汇表覆盖：封闭词汇表里每个 operation 都得有定向 mutant 料
    # 词汇表写了八类，验收矩阵只跑到六类的话，另两类的最低谓词族从未被证伪——
    # 声明存在但没被拒过的族不构成防线。故词汇表缺口本身就是 FAIL 项。
    vocab = sorted(json.load(open(IR, encoding="utf-8"))["operations"])
    exercised = sorted(k for k, v in op_table.items() if v["with_mutant"])
    vocab_gap = [op for op in vocab if op not in exercised]
    for op in vocab_gap:
        problems.append(f"operation「{op}」在封闭词汇表内但无定向 mutant 料——"
                        "该族最低谓词从未被证伪")
    vocab_cov = {"vocabulary": vocab, "exercised": exercised,
                 "missing": vocab_gap,
                 "ratio": f"{len(exercised)}/{len(vocab)}"}

    out = {"results": results, "operation_coverage": op_table,
           "vocabulary_coverage": vocab_cov,
           "uncovered_assertions": uncovered, "problems": problems,
           "overall": "PASS" if not problems else "FAIL"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for k, v in results.items():
        mark = "ok  " if (v.get("hit", True) and not (v["kind"] == "golden" and v["failed"])) else "BAD "
        extra = v.get("must_be_rejected_by") or v.get("expect_assert") or ""
        print(f"[{mark}] {k:34s} {v['verdict']:22s} {extra}")
    print("\noperation 覆盖:")
    for op, t in op_table.items():
        print(f"  {op:12s} 断言 {t['assertions']}  有定向 mutant {t['with_mutant']}"
              f"  {'未覆盖:' + str(t['uncovered']) if t['uncovered'] else ''}")
    print(f"\n总判定: {out['overall']}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
