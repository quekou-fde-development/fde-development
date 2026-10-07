#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐族实跑 audit.py FAMILIES：正例成立，定向坏例由该 family 行指名拒绝。"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REGISTRY = os.path.join(ROOT, "predicate_family_registry.json")
FIXTURE_GENERATOR = os.path.join(HERE, "make_predicate_fixtures.py")


def _run_audit(skill_dir, suite, run_dir):
    cmd = [sys.executable, os.path.join(skill_dir, "scripts", "audit.py"), run_dir,
           "--contract", os.path.join(ROOT, suite["contract"]), "--all", "--json"]
    if suite.get("source"):
        cmd += ["--source", os.path.join(ROOT, suite["source"])]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        report = json.loads(p.stdout)
    except json.JSONDecodeError:
        report = {"rows": [], "verdict": "ERROR"}
    return p, report


def _dispatch(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    tables = [n.value for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "FAMILIES" for t in n.targets)]
    if len(tables) != 1 or not isinstance(tables[0], ast.Dict):
        return {}, [f"FAMILIES 须恰有一份静态 dict，实为 {len(tables)}"]
    out, problems = {}, []
    for key, value in zip(tables[0].keys, tables[0].values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str) or \
                not isinstance(value, ast.Name):
            problems.append("FAMILIES 须为字符串 family → 本地函数名")
            continue
        if key.value in out:
            problems.append(f"FAMILIES family 重复 {key.value}")
        out[key.value] = value.id
    return out, problems


def _one_row(report, assertion_id):
    rows = [row for row in report.get("rows", []) if row.get("id") == assertion_id]
    return rows[0] if len(rows) == 1 else None, len(rows)


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--json"):
        print("用法: predicate_family_behavior.py <skill_dir> [--json]", file=sys.stderr)
        return 2
    skill_dir = os.path.abspath(sys.argv[1])
    as_json = "--json" in sys.argv[2:]
    try:
        registry = json.load(open(REGISTRY, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"predicate family registry 不可读：{e}", file=sys.stderr)
        return 2

    global_problems = []
    fixture_check = subprocess.run(
        [sys.executable, FIXTURE_GENERATOR, os.path.join(ROOT, "predicate-fixtures"), "--check"],
        capture_output=True, text=True)
    if fixture_check.returncode != 0:
        global_problems.append("predicate fixture 与生成器不闭合：" +
                               (fixture_check.stdout + fixture_check.stderr).strip())

    dispatch, dispatch_problems = _dispatch(os.path.join(skill_dir, "scripts", "audit.py"))
    global_problems.extend(dispatch_problems)
    declared = registry.get("families", {})
    if set(dispatch) != set(declared):
        global_problems.append(f"FAMILIES 与 predicate witness 不闭合："
                               f"缺 {sorted(set(dispatch)-set(declared))}，"
                               f"多 {sorted(set(declared)-set(dispatch))}")

    cache, results = {}, {}
    neutral_tmp = tempfile.TemporaryDirectory(prefix="predicate_family_neutral_")
    for family, spec in declared.items():
        problems = []
        expected_gid = f"audit.family.{family}"
        if spec.get("function") != dispatch.get(family):
            problems.append(f"函数 owner 漂移：dispatch={dispatch.get(family)}，"
                            f"registry={spec.get('function')}")
        if spec.get("gate_id") != expected_gid:
            problems.append(f"Gate-ID 须为 {expected_gid}，实为 {spec.get('gate_id')}")
        suite = registry.get("suites", {}).get(spec.get("suite"))
        if suite is None:
            problems.append(f"未知 suite {spec.get('suite')}")
            results[family] = {"gate_id": expected_gid, "positive_pass": False,
                               "witness_count": 0, "target_hit": False,
                               "reason_hit": False, "problems": problems}
            continue

        def reports_for(run_name):
            key = (spec["suite"], run_name)
            if key not in cache:
                source_dir = os.path.join(ROOT, suite["runs_root"], run_name)
                neutral_dir = os.path.join(neutral_tmp.name, f"run-{len(cache)}")
                shutil.copytree(source_dir, neutral_dir,
                                ignore=shutil.ignore_patterns("INJECTION.json"))
                cache[key] = (_run_audit(skill_dir, suite, source_dir),
                              _run_audit(skill_dir, suite, neutral_dir))
            return cache[key]

        (pp, prep), (npp, nprep) = reports_for(suite["golden"])
        prow, pn = _one_row(prep, spec["assertion"])
        nprow, npn = _one_row(nprep, spec["assertion"])
        positive_status = spec.get("positive_status", "PASS")
        positive_pass = (pp.returncode == 0 and npp.returncode == 0 and
                         pn == 1 and npn == 1 and prow is not None and nprow is not None and
                         prow.get("family") == family and nprow.get("family") == family and
                         prow.get("status") == positive_status and
                         nprow.get("status") == positive_status)
        if not positive_pass:
            problems.append(f"正例 {suite['golden']}/{spec['assertion']} 须在原名/中性名下"
                            f"唯一且为 {family}/{positive_status}，实为 "
                            f"rc={pp.returncode}/{npp.returncode} row={prow}/{nprow}")

        (bp, brep), (nbp, nbrep) = reports_for(spec["negative"])
        brow, bn = _one_row(brep, spec["assertion"])
        nbrow, nbn = _one_row(nbrep, spec["assertion"])
        target_hit = (bn == 1 and nbn == 1 and brow is not None and nbrow is not None and
                      brow.get("family") == family and nbrow.get("family") == family and
                      brow.get("status") == "FAIL" and nbrow.get("status") == "FAIL")
        reason_hit = bool(brow and nbrow and
                          spec["reason"] in str(brow.get("detail", "")) and
                          spec["reason"] in str(nbrow.get("detail", "")))
        original_status = {r.get("id"): r.get("status") for r in brep.get("rows", [])}
        neutral_status = {r.get("id"): r.get("status") for r in nbrep.get("rows", [])}
        metadata_independent = original_status == neutral_status
        if not target_hit:
            problems.append(f"负例 {spec['negative']}/{spec['assertion']} 未在原名/中性名下"
                            f"都由 {family} 行判 FAIL：rc={bp.returncode}/{nbp.returncode} "
                            f"row={brow}/{nbrow}")
        if not reason_hit:
            problems.append(f"负例 {spec['negative']} 的目标行未在原名/中性名下都命中"
                            f"理由「{spec['reason']}」")
        if bp.returncode != 1 or nbp.returncode != 1:
            problems.append(f"负例 {spec['negative']} 原名/中性名退出码须 1，"
                            f"实为 {bp.returncode}/{nbp.returncode}")
        if not metadata_independent:
            problems.append(f"负例 {spec['negative']} 改中性目录并剥 INJECTION 后逐条状态漂移")
        results[family] = {
            "gate_id": expected_gid, "positive_pass": positive_pass,
            "witness_count": 1, "target_hit": target_hit, "reason_hit": reason_hit,
            "metadata_independent": metadata_independent,
            "details": [{"negative": spec["negative"], "assertion": spec["assertion"],
                         "reason": spec["reason"], "target_hit": target_hit,
                         "reason_hit": reason_hit,
                         "metadata_independent": metadata_independent}], "problems": problems
        }

    neutral_tmp.cleanup()

    problems = list(global_problems)
    problems.extend(f"{family}: {problem}" for family, result in results.items()
                    for problem in result.get("problems", []))
    payload = {"family_ids": sorted(results), "results": results,
               "problems": problems, "verdict": "PASS" if not problems else "FAIL"}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for family, result in results.items():
            print(f"{family:<42} {'[OK]' if not result['problems'] else '[BAD]'}  "
                  f"positive={result['positive_pass']} target={result['target_hit']} "
                  f"reason={result['reason_hit']}")
        print(f"总判定: {payload['verdict']}（{len(results)}/28 family）")
        for problem in problems:
            print("  ! " + problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
