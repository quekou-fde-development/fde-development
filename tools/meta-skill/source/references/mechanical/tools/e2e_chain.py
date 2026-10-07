#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""e2e_chain.py — 跑真实持久包的完整链，验第五道运行期交付闸。

链形照 SKILL.md 第 6 步 6A：
    run 段 → audit --stage <段>  非 0 立即停，不进下一段
    → 下一段 → … → audit --all 末端全量复核 → manifest 落盘

三臂，判据各不相同（判据跑前写定，不迁就实现）：
  A-clean      两段全对 + 给 --source  → 末端 rc 0 / PASS；两段产物齐；manifest 字段齐
  B-failfast   第 1 段注 count-drift    → 段级 audit rc 1；**第 2 段不得执行**；
                                          s2 产物必须不存在（fail-fast 的物证）
  C-unverified 两段全对但不给 --source  → T2 标 UNVERIFIED；末端 **rc 3** /
                                          PASS_WITH_UNVERIFIED；禁报 PASS、禁 rc 0

C 臂要 rc 3 而不是 rc 0：交付信号必须在退出码上与「全验过且全对」可分。压成
同一个 0 时，调用方只有解析 stdout 才知道「有面没验」——闸的判定退化成文本比对。

用法: python3 e2e_chain.py <package_dir> <out_root> <result_json>
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INTERP = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft", "scripts", "audit.py"))
STAGES = ["s1_export", "s2_filtered"]
ARTIFACT = {"s1_export": "s1_export.json", "s2_filtered": "s2_filtered.json"}


def sh(cmd, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(cmd, capture_output=True, text=True, env=e)
    return p.returncode, p.stdout + p.stderr


def run_chain(pkg, run_dir, source, inject_at=None, inject=None):
    """按 6A 链形跑。段级 audit 非 0 立即返回，不进下一段。"""
    os.makedirs(run_dir, exist_ok=True)
    audit_sh = os.path.join(pkg, "scripts", "audit.py")
    env = {"CONTRACT_INTERPRETER": INTERP}
    log, executed, halted_at = [], [], None

    for st in STAGES:
        cmd = [sys.executable, os.path.join(pkg, "scripts", "run_stages.py"),
               "--stage", st, "--run-dir", run_dir]
        if inject_at == st and inject:
            cmd += ["--inject", inject]
        rc, out = sh(cmd)
        executed.append(st)
        log.append({"step": f"run:{st}", "rc": rc, "out": out.strip()})
        if rc != 0:
            halted_at = st
            break

        # 段级审核：本段落盘后立即跑 T1
        acmd = [sys.executable, audit_sh, run_dir, "--stage", st]
        if source:
            acmd += ["--source", source]
        rc, out = sh(acmd, env)
        log.append({"step": f"audit:{st}", "rc": rc, "out": out.strip()})
        # 段闸只回答「下游能不能走」，非 0 即停。3（PASS_WITH_UNVERIFIED）按约定
        # 只在 --all 末端返回，段闸下不出现——真出现了说明 audit 的 --stage/--all
        # 分流坏了，此处显式登记，不当成普通失败混过去。
        if rc == 3:
            log.append({"step": f"audit:{st}", "rc": rc,
                        "out": "契约违例：段闸返回 3，rc 3 只应出现在 --all 末端"})
        if rc != 0:
            halted_at = st          # fail-fast：不进下一段
            break

    manifest_path = os.path.join(run_dir, "run_manifest.json")
    final = None
    if halted_at is None:
        acmd = [sys.executable, audit_sh, run_dir, "--all",
                "--manifest", manifest_path, "--run-dir-source", "explicit_arg"]
        if source:
            acmd += ["--source", source]
        rc, out = sh(acmd, env)
        log.append({"step": "audit:--all", "rc": rc, "out": out.strip()})
        final = rc
    return {"executed": executed, "halted_at": halted_at, "log": log,
            "final_rc": final, "manifest": manifest_path}


MANIFEST_KEYS = ["run_id", "package_hash", "contract_hash", "run_dir_resolved",
                 "run_dir_source", "started_at", "stages", "final_verdict", "retention"]
STAGE_KEYS = ["stage", "operations", "audit_tiers_run", "assertions",
              "verdict", "unresolved_coverage"]
OP_KEYS = ["op", "artifact", "source_reachability"]
REACH = ("machine", "human_handoff")


def check_manifest(path):
    """manifest 字段齐不齐——§7 schema 全字段，缺一即 fail。

    消费方测试：source_reachability 是 **operation** 级字段，取值必须是
    §7 声明的两个枚举值之一。段级不得再有同名字段——一段多 operation 时
    段级标量只能二选一，改报清单则同一字段两种类型，按 schema 解析必错。
    """
    if not os.path.isfile(path):
        return False, ["manifest 未落盘"]
    with open(path, encoding="utf-8") as f:
        m = json.load(f)
    bad = [f"缺顶层字段 {k}" for k in MANIFEST_KEYS if k not in m]
    for st in m.get("stages", []):
        sid = st.get("stage")
        bad += [f"{sid} 缺段字段 {k}" for k in STAGE_KEYS if k not in st]
        if "source_reachability" in st:
            bad.append(f"{sid} 段级仍有 source_reachability——该字段属 operation")
        for op in st.get("operations", []):
            bad += [f"{sid}/{op.get('artifact')} 缺 operation 字段 {k}"
                    for k in OP_KEYS if k not in op]
            r = op.get("source_reachability")
            if r is not None and r not in REACH:
                bad.append(f"{sid}/{op.get('artifact')} source_reachability={r!r}"
                           f" 不在枚举 {REACH} 内（清单/多态类型即拒）")
    return not bad, bad


def arm_a(pkg, out, src):
    r = run_chain(pkg, os.path.join(out, "A-clean"), src)
    ok, bad = check_manifest(r["manifest"])
    fails = []
    if r["halted_at"]:
        fails.append(f"清洁臂不应中断，实停在 {r['halted_at']}")
    if r["final_rc"] != 0:
        fails.append(f"末端 audit --all 退出码 {r['final_rc']}，应为 0")
    if not ok:
        fails += bad
    if ok:
        m = json.load(open(r["manifest"], encoding="utf-8"))
        if m["final_verdict"] != "PASS":
            fails.append(f"final_verdict={m['final_verdict']}，应为 PASS")
        if m["run_dir_source"] != "explicit_arg":
            fails.append(f"run_dir_source={m['run_dir_source']}，应为 explicit_arg")
        r["final_verdict"] = m["final_verdict"]
    return r, fails


def arm_b(pkg, out, src):
    run_dir = os.path.join(out, "B-failfast")
    r = run_chain(pkg, run_dir, src, inject_at="s1_export", inject="count-drift")
    fails = []
    if r["halted_at"] != "s1_export":
        fails.append(f"应在 s1_export 段级审核处停，实为 {r['halted_at']}")
    if "s2_filtered" in r["executed"]:
        fails.append("fail-fast 失效：第 1 段已 fail，第 2 段仍被执行")
    # 物证：下游产物必须不存在
    s2 = os.path.join(run_dir, ARTIFACT["s2_filtered"])
    if os.path.exists(s2):
        fails.append("fail-fast 失效：下游产物 s2_filtered.json 存在")
    seg = [x for x in r["log"] if x["step"] == "audit:s1_export"]
    # 判 rc == 1 而不是「非 0」：rc 2 是契约本身错（断言压根没跑过），
    # 拿它当「闸拒了」等于把「闸没跑」记成检出。
    if not seg:
        fails.append("段级审核未执行")
    elif seg[0]["rc"] != 1:
        fails.append(f"段级审核退出码 {seg[0]['rc']}，应为 1（FAIL）")
    else:
        r["rejected_by"] = [ln for ln in seg[0]["out"].splitlines()
                            if ln.startswith("[FAIL]")]
        if not any("count_hash" in ln for ln in r["rejected_by"]):
            fails.append("count-drift 未被 count_hash 断言拒——不是它登记的那条闸")
    return r, fails


def arm_c(pkg, out, src):
    """源不可机械重读：不传 --source。T2 须标 UNVERIFIED，末端禁报 PASS。

    退出码判据两条，缺一不可：
      · 段闸（--stage）须返回 0——源不可达不是产物错，不得阻断 T0/T1；
      · 末端（--all）须返回 3——「有面没验」必须落在退出码上，不得压成 0。
    """
    r = run_chain(pkg, os.path.join(out, "C-unverified"), None)
    ok, bad = check_manifest(r["manifest"])
    fails = list(bad) if not ok else []
    if r["halted_at"]:
        fails.append(f"源不可达不得阻断 T0/T1，实停在 {r['halted_at']}")
    for ln in r["log"]:
        if ln["step"].startswith("audit:") and ln["step"] != "audit:--all" \
                and ln["rc"] != 0:
            fails.append(f"{ln['step']} 退出码 {ln['rc']}，段闸下 UNVERIFIED 应为 0")
    if r["final_rc"] != 3:
        fails.append(f"末端 audit --all 退出码 {r['final_rc']}，"
                     "应为 3（PASS_WITH_UNVERIFIED 不得压成 0）")
    if ok:
        m = json.load(open(r["manifest"], encoding="utf-8"))
        r["final_verdict"] = m["final_verdict"]
        if m["final_verdict"] == "PASS":
            fails.append("三值被压成二值：T2 未跑仍报 PASS")
        elif m["final_verdict"] != "PASS_WITH_UNVERIFIED":
            fails.append(f"final_verdict={m['final_verdict']}，应为 PASS_WITH_UNVERIFIED")
        uv = sum(s["assertions"]["unverified"] for s in m["stages"])
        if uv == 0:
            fails.append("无 UNVERIFIED 计数——T2 被静默跳过而非登记")
        unres = [u for s in m["stages"] for u in s["unresolved_coverage"]]
        if not unres:
            fails.append("unresolved_coverage 为空——未覆盖面未显式登记")
        r["unverified"] = uv
        r["unresolved_coverage"] = unres
    return r, fails


def main():
    pkg, out, res = sys.argv[1], sys.argv[2], sys.argv[3]
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    src = os.path.join(pkg, "fixtures", "source_orders.md")

    results, overall = {}, True
    for name, fn in [("A-clean", arm_a), ("B-failfast", arm_b), ("C-unverified", arm_c)]:
        r, fails = fn(pkg, out, src)
        r["fails"] = fails
        r["ok"] = not fails
        overall &= r["ok"]
        results[name] = r
        mark = "ok  " if r["ok"] else "FAIL"
        extra = r.get("final_verdict") or f"halted@{r['halted_at']}"
        print(f"[{mark}] {name:<14} {extra}")
        for f in fails:
            print(f"         · {f}")

    os.makedirs(os.path.dirname(res), exist_ok=True)
    with open(res, "w", encoding="utf-8") as f:
        json.dump({"overall": "PASS" if overall else "FAIL", "arms": results},
                  f, ensure_ascii=False, indent=1)
    print(f"\n总判定: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
