#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_matrix.py — validate.py M7-M11 五闸的验收矩阵。

判据三条（同 accept_matrix.py，上移一层用于编译器自身的机械闸）：
  1. 正例 G0：五闸零 FAIL，退出码 0。闸不能恒 FAIL，否则「拒绝」不携带信息。
  2. 定向 fixture：每个 G_n 必须**被它登记的那个闸**判 FAIL。
     只要「退出码非 0」不算过——别的闸报错等于这个闸没被检验。
  3. 覆盖：M7-M11 每个闸都至少有一个 fixture 指名它。

fixture 声明的 `needs_persistent_flag` 必须照传。不传等于把被测闸调进 SKIP
分支再宣布它没拒——validate.py 对无 assertions.json 的包默认「非持久 Skill 包」
而跳过 M8-M10，于是 P1 这种「带持久标记但空壳」的负例永远打不到闸上，矩阵还
报一个 `[BAD]`：既没检验到闸，又制造了假警报。**调用姿势属于 fixture 定义的
一部分**，不是运行者可省的细节。

正例靠发现不靠硬编码：各 root 的正例名不同（`G0-good` / `C0-good`），写死一个
名字时，换个 root 就悄悄没有正例对照——假阳性防线整片消失，而输出只显示一行
「退出码 2」，像是正例坏了，不像是正例不存在。找不到或找到多个都判问题，不猜。

用法: python3 gate_matrix.py <fixtures_root>... <validate.py 路径> <out_json>
退出码 0 = 全过；1 = 有不合格项；2 = 参数不足。
"""
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

GATES = ["M7", "M8", "M9", "M10", "M11"]
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.normpath(os.path.join(HERE, "..", "fixture_registry.json"))
BEHAVIOR_REGISTRY = os.path.normpath(os.path.join(HERE, "..", "gate_behavior_registry.json"))
from gate_behavior import (_block_digest, _cause_codes, _diagnostic_features,
                           _exact_diagnostic_binding, _gate_block)


def fixture_contract(root, problems):
    """闭合 registry → generator manifest → 盘上 fixture，少一条即红。"""
    mp = os.path.join(root, "_fixture_manifest.json")
    if not os.path.isfile(mp):
        problems.append(f"{root} 缺 _fixture_manifest.json——生成器登记与盘上实物未闭合")
        return None
    try:
        manifest = json.load(open(mp, encoding="utf-8"))
        registry = json.load(open(REGISTRY, encoding="utf-8"))["suites"]
        spec = registry[manifest["suite"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        problems.append(f"{root} fixture manifest/registry 不可解析: {e}")
        return None
    if manifest.get("positive") != spec.get("positive") or \
            set(manifest.get("directed", [])) != set(spec.get("directed", {})):
        problems.append(f"{root} generator manifest 与 fixture_registry.json 漂移")
    return spec


def find_positive(root, problems):
    """本 root 的正例目录，约定 `*0-good`。"""
    cands = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "*0-good")))
    if len(cands) == 1:
        return cands[0]
    problems.append(f"{root} 下有 {len(cands)} 个 `*0-good` 正例目录 {cands}"
                    "——正例对照是假阳性防线的全部，缺了或多了都不猜")
    return None


def run_validate(validate, folder, extra=()):
    p = subprocess.run([sys.executable, validate, folder, *extra],
                       capture_output=True, text=True)
    status = {}
    for line in p.stdout.splitlines():
        m = re.match(r"^(M\d+) (PASS|FAIL|SKIP|WARN|NOTE)", line)
        if m and m.group(1) not in status:   # 取每闸首行结论
            status[m.group(1)] = m.group(2)
    return status, p.returncode, p.stdout


def probe_capture_contract(validate, problems):
    """独立验证候选父进程不会跟随预植/运行中替换的捕获路径。"""
    result = {"preplanted_symlink": False, "relinked_after_open": False}
    try:
        spec = importlib.util.spec_from_file_location("v38_capture_validator", validate)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        acceptance_root = os.path.normpath(os.path.join(HERE, ".."))
        with tempfile.TemporaryDirectory(prefix=".capture_probe_",
                                         dir=acceptance_root) as base:
            victim = os.path.join(base, "victim.txt")
            original = b"ORIGINAL_VICTIM_CONTENT\n"
            with open(victim, "wb") as handle:
                handle.write(original)

            pre = os.path.join(base, "preplanted")
            os.makedirs(pre)
            os.symlink(victim, os.path.join(pre, "attack_stdout.txt"))
            rc, detail, _ = module._isolated_command(
                [sys.executable, "-c", "print('must not run')"],
                pre, pre, dict(os.environ), "attack")
            result["preplanted_symlink"] = (
                rc is None and "preoccupied_or_symlink" in detail and
                open(victim, "rb").read() == original)

            relink = os.path.join(base, "relinked")
            os.makedirs(relink)
            capture = os.path.join(relink, "attack_stdout.txt")
            code = ("import os,sys; p,v=sys.argv[1:3]; os.unlink(p); "
                    "os.symlink(v,p); print('FD_SAFE')")
            rc, _detail, output = module._isolated_command(
                [sys.executable, "-c", code, capture, victim],
                relink, relink, dict(os.environ), "attack")
            result["relinked_after_open"] = (
                rc == 0 and output == "FD_SAFE" and
                os.path.islink(capture) and open(victim, "rb").read() == original)
    except (OSError, AttributeError, ImportError) as exc:
        result["error"] = type(exc).__name__
    if not all(result.get(key) for key in
               ("preplanted_symlink", "relinked_after_open")):
        problems.append(f"父进程输出捕获 symlink 边界未闭合: {result}")
    return result


def main():
    *roots, validate, out_path = sys.argv[1:]
    if not roots:
        print("用法: gate_matrix.py <root>... <validate.py> <out_json>", file=sys.stderr)
        return 2
    results, problems = {}, []
    capture_boundary = probe_capture_contract(validate, problems)
    try:
        behavior = json.load(open(BEHAVIOR_REGISTRY, encoding="utf-8"))
        cause_registry = behavior["directed_causes"]
        block_baselines = behavior["cause_block_baselines"]
        diagnostic_registry = behavior["directed_diagnostics"]
        cause_groups = {}
        for suite_causes in cause_registry.values():
            overlap = set(cause_groups) & set(suite_causes)
            if overlap:
                raise ValueError(f"directed cause fixture 重名: {sorted(overlap)}")
            cause_groups.update(suite_causes)
        diagnostic_bindings = {}
        for suite_diagnostics in diagnostic_registry.values():
            overlap = set(diagnostic_bindings) & set(suite_diagnostics)
            if overlap:
                raise ValueError(f"directed diagnostic fixture 重名: {sorted(overlap)}")
            diagnostic_bindings.update(suite_diagnostics)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"cause group registry 不可解析: {e}", file=sys.stderr)
        return 2

    all_directed = set()
    active_expected = set()
    for root in roots:
        # ---- 1. 每个 root 各自的正例假阳性对照
        # 逐 root 而不是全局一个：正例证明的是「这一批 fixture 的公共形状不会
        # 无故触闸」，换了 root 就换了公共形状，别处的正例不替它作证。
        spec = fixture_contract(root, problems)
        if spec:
            active_expected.update(spec.get("directed", {}))
        pos = find_positive(root, problems)
        if spec and pos != spec.get("positive"):
            problems.append(f"{root}: 盘上正例 {pos!r} 与 registry "
                            f"{spec.get('positive')!r} 不同")
        if pos:
            st, ec, _ = run_validate(validate, os.path.join(root, pos))
            bad = [g for g in GATES if st.get(g) == "FAIL"]
            skipped = [g for g in GATES if st.get(g) == "SKIP"]
            results[pos] = {"kind": "positive", "root": root, "exit": ec, "gates": st,
                            "failed_gates": bad, "skipped_gates": skipped}
            if bad:
                problems.append(f"{pos}: 正例出现假阳性，闸 {bad} 判 FAIL")
            if skipped:
                problems.append(f"{pos}: 闸 {skipped} 在正例上 SKIP——未被执行，不构成检验")
            if ec != 0:
                problems.append(f"{pos}: 退出码 {ec}，正例须为 0")

        # ---- 2. 定向 fixture 须被登记的那个闸拒绝
        actual_directed = set()
        for name in sorted(os.listdir(root)):
            inj_path = os.path.join(root, name, "GATE_INJECTION.json")
            if not os.path.isfile(inj_path):
                continue
            actual_directed.add(name)
            all_directed.add(name)
            with open(inj_path, encoding="utf-8") as f:
                inj = json.load(f)
            if name in results:
                problems.append(f"{name}: 多个 root 下同名 fixture，判定互相覆盖")
            want = inj["must_be_rejected_by"]
            extra = ["--persistent"] if inj.get("needs_persistent_flag") else []
            st, ec, stdout = run_validate(validate, os.path.join(root, name), extra)
            hit = st.get(want) == "FAIL"
            reason = inj.get("must_include_reason", "")
            target_block = _gate_block(stdout, want)
            reason_hit = bool(reason) and reason in target_block
            expected_cause = cause_groups.get(name)
            actual_causes = _cause_codes(target_block)
            cause_hit = expected_cause is not None and actual_causes == {expected_cause}
            expected_diagnostic = diagnostic_bindings.get(name)
            diagnostic_hit = (expected_diagnostic is None or
                              _exact_diagnostic_binding(target_block,
                                                        expected_diagnostic))
            positive_control = inj.get("positive_control")
            control_hit = bool(pos and positive_control == pos)
            others = [g for g in GATES if g != want and st.get(g) == "FAIL"]
            results[name] = {"kind": "directed", "root": root, "exit": ec, "gates": st,
                             "must_be_rejected_by": want, "hit": hit, "argv_extra": extra,
                             "must_include_reason": reason, "reason_hit": reason_hit,
                             "expected_cause": expected_cause, "cause_hit": cause_hit,
                             "target_block_sha256": _block_digest(target_block),
                             "expected_diagnostic": expected_diagnostic,
                             "diagnostic_hit": diagnostic_hit,
                             "positive_control": positive_control, "control_hit": control_hit,
                             "collateral_fails": others, "doc": inj.get("doc", "")}
            if not hit:
                problems.append(
                    f"{name}: 应由 {want} 拒绝，实际 {want}={st.get(want)}，"
                    f"全部 FAIL 闸={[g for g in GATES if st.get(g)=='FAIL']}")
            if ec == 0:
                problems.append(f"{name}: 退出码 0——坏件放行")
            if not reason:
                problems.append(f"{name}: 未登记 must_include_reason——泛 FAIL 不构成定向命中")
            elif not reason_hit:
                problems.append(f"{name}: 指定失败理由未命中「{reason}」")
            if expected_cause is None:
                problems.append(f"{name}: 未登记 directed cause")
            elif not cause_hit:
                problems.append(f"{name}: 病因组须精确为 {expected_cause}，"
                                f"实为 {sorted(actual_causes)}")
            if expected_diagnostic and not diagnostic_hit:
                problems.append(f"{name}: 结构诊断绑定须精确为 "
                                f"{expected_diagnostic.get('expected')}，实为 "
                                f"{_diagnostic_features(target_block, expected_diagnostic)}")
            if not control_hit:
                problems.append(f"{name}: positive_control={positive_control!r}，"
                                f"该 root 唯一正例为 {pos!r}")
            if spec:
                expected = spec.get("directed", {}).get(name)
                if expected is None:
                    problems.append(f"{name}: 盘上有定向 fixture，但 registry 未登记")
                elif [want, reason] != expected:
                    problems.append(f"{name}: 注入目标/理由与 registry 漂移："
                                    f"盘上={[want, reason]}，registry={expected}")
        if spec:
            expected_ids = set(spec.get("directed", {}))
            missing = sorted(expected_ids - actual_directed)
            extra = sorted(actual_directed - expected_ids)
            if missing or extra:
                problems.append(f"{root}: fixture 实物集合不闭合：缺 {missing}，多 {extra}")

    active_cause_names = set(cause_groups) & active_expected
    if all_directed != active_cause_names:
        problems.append("directed cause 与本矩阵定向 fixture 不闭合："
                        f"缺 {sorted(all_directed - active_cause_names)}，"
                        f"多 {sorted(active_cause_names - all_directed)}")

    grouped = {}
    for result in results.values():
        if result.get("kind") != "directed":
            continue
        key = f"{result['must_be_rejected_by']}|{result['expected_cause']}"
        grouped.setdefault(key, []).append(result)
    global_group_members = {}
    fixture_suites = json.load(open(REGISTRY, encoding="utf-8"))["suites"]
    for suite, suite_spec in fixture_suites.items():
        for name, (gate, _reason) in suite_spec.get("directed", {}).items():
            global_group_members.setdefault(f"{gate}|{cause_groups.get(name)}", set()).add(name)
    active_baselines = {group: count for group, count in block_baselines.items()
                        if global_group_members.get(group, set()).issubset(active_expected)}
    multi_groups = {key for key, members in grouped.items() if len(members) > 1}
    if multi_groups != set(active_baselines):
        problems.append("cause block baseline 与全部多成员病因组不闭合："
                        f"缺 {sorted(multi_groups - set(active_baselines))}，"
                        f"多 {sorted(set(active_baselines) - multi_groups)}")
    for group, expected_count in active_baselines.items():
        members = grouped.get(group, [])
        actual_count = len({member["target_block_sha256"] for member in members})
        if actual_count != expected_count:
            problems.append(f"{group} 组内诊断块数须为 {expected_count}，"
                            f"实为 {actual_count}")
    required_diagnostics = set().union(*(
        global_group_members.get(group, set()) for group, count in active_baselines.items()
        if count > 1)) if active_baselines else set()
    active_diagnostics = set(diagnostic_bindings) & active_expected
    if required_diagnostics != active_diagnostics:
        problems.append("逐 fixture 结构诊断绑定与可分多成员组不闭合："
                        f"缺 {sorted(required_diagnostics - active_diagnostics)}，"
                        f"多 {sorted(active_diagnostics - required_diagnostics)}")

    # ---- 3. 闸覆盖：全部 root 的并集
    # 覆盖是整套语料的属性，不是单个 root 的。custom-fixtures 专打 M8/M9，
    # 单独判它必因「M7/M10/M11 未覆盖」报红——那是分片的假象，不是缺口。
    named = {r["must_be_rejected_by"] for r in results.values()
             if r["kind"] == "directed"}
    uncovered = [g for g in GATES if g not in named]
    for g in uncovered:
        problems.append(f"闸 {g} 无定向 fixture——未经证伪，不构成检验")

    out = {"results": results, "capture_boundary": capture_boundary, "gate_coverage":
           {g: sorted(n for n, r in results.items()
                      if r["kind"] == "directed" and r["must_be_rejected_by"] == g)
            for g in GATES},
           "uncovered_gates": uncovered, "problems": problems,
           "overall": "PASS" if not problems else "FAIL"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for n, r in results.items():
        if r["kind"] == "positive":
            mark = "ok  " if not r["failed_gates"] and not r["skipped_gates"] else "BAD "
            print(f"[{mark}] {n:32s} exit={r['exit']}  五闸={[r['gates'].get(g) for g in GATES]}")
        else:
            mark = "ok  " if r["hit"] and r["reason_hit"] and r["cause_hit"] \
                and r["diagnostic_hit"] and r["control_hit"] else "BAD "
            col = f"  (旁落 {r['collateral_fails']})" if r["collateral_fails"] else ""
            print(f"[{mark}] {n:32s} exit={r['exit']}  须拒于 {r['must_be_rejected_by']}"
                  f" → 实为 {r['gates'].get(r['must_be_rejected_by'])}"
                  f"  理由={r['reason_hit']} 病因组={r['cause_hit']} "
                  f"诊断绑定={r['diagnostic_hit']} 对照={r['control_hit']}{col}")
    print("\n闸覆盖:")
    for g, fx in out["gate_coverage"].items():
        print(f"  {g:4s} {len(fx)} 个定向 fixture  {fx if fx else '← 未覆盖'}")
    print(f"\n总判定: {out['overall']}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
