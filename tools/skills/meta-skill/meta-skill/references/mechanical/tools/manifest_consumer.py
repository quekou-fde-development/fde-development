#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""manifest_consumer.py — run manifest 的**消费方**测试（IR §7）。

存在理由：manifest 是交接件。审核器写它、下游读它，而两端从不对质——写的
一方自测「我写出来了」，读的一方拿到什么形状全凭运气。IR §7 那条注解说得很
具体：`source_reachability` 逐 operation 报、不设段级字段，因为一段挂两个
operation 时两者可以不同；压成段级标量则「另一个源不可机械重读」从交接件上
消失，改报数组则同一字段时而是枚举值时而是数组，按 schema 解析必错。

这条注解此前只是**散文**——没有任何一方在读，改成段级也不会有任何东西变红。
本器就是缺的那个消费方：严格按 §7 声明的形状读 manifest，读不通即报。

判据分三档，逐档收紧：
  1. 形状——键在位、类型对、枚举值在声明的取值域内；
  2. 与契约对账——每段的 operation 清单须与契约里该段的 operation **一一对应**
     （按产物名配对）。只数字段个数抓不到"清单被截断成第一项"：截断后每一项
     的字段依然齐全，形状是合法的，少的是**条目**。要抓它只能拿契约比；
  3. 三值判定自洽——`unverified > 0` 而报 `PASS` 即把三值压成了二值，
     交接时「有面没验」就此隐形。

**本器不看审核器的源码**，只吃它落盘的 manifest：消费方要是照着生产方的实现
写，就成了同因自证，生产方改形状、消费方跟着改，永远对得上。

用法:
  python3 manifest_consumer.py <manifest.json> <contract.json>   # 单件校
  python3 manifest_consumer.py --self-test                       # 正负例自检
退出码 0 = 可消费；1 = 有不可消费项；2 = 用法错。
"""
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIT = os.path.normpath(os.path.join(ROOT, "..", "v3.8-draft", "scripts", "audit.py"))
IR_JSON = os.path.normpath(
    os.path.join(ROOT, "..", "v3.8-draft", "references", "contract_ir.json"))

VERDICTS = ("PASS", "FAIL", "PASS_WITH_UNVERIFIED")
REACH = ("machine", "human_handoff")
TOP_KEYS = ("run_id", "package_hash", "contract_hash", "run_dir_resolved",
            "run_dir_source", "started_at", "stages", "final_verdict", "retention")
STAGE_KEYS = ("stage", "operations", "audit_tiers_run", "assertions", "verdict",
              "unresolved_coverage")
COUNT_KEYS = ("passed", "failed", "unverified")


def consume(mf, contract, vocab):
    """按 §7 声明的形状读一份 manifest。返回不可消费项清单（空 = 可消费）。"""
    p = []

    # ---- 档 1 · 形状
    for k in TOP_KEYS:
        if k not in mf:
            p.append(f"顶层缺 `{k}`")
    if mf.get("run_dir_source") not in ("explicit_arg", "env", "default"):
        p.append(f"`run_dir_source` 取值 {mf.get('run_dir_source')!r} 不在声明域内")
    if mf.get("final_verdict") not in VERDICTS:
        p.append(f"`final_verdict` 取值 {mf.get('final_verdict')!r} 不在三值域内")
    if mf.get("retention") not in ("always", "on_failure", "never"):
        p.append(f"`retention` 取值 {mf.get('retention')!r} 不在声明域内")
    if not isinstance(mf.get("stages"), list):
        p.append("`stages` 不是数组——无从逐段消费")
        return p

    by_stage = {st["stage"]: st for st in contract.get("stages", [])}
    for s in mf["stages"]:
        tag = f"段 {s.get('stage', '<无名>')}"
        for k in STAGE_KEYS:
            if k not in s:
                p.append(f"{tag}: 缺 `{k}`")
        if "source_reachability" in s:
            p.append(f"{tag}: `source_reachability` 出现在**段级**——可达性是 "
                     "operation 的属性，压成段级标量时一段两个 operation 只能"
                     "报一个，另一个「源不可机械重读」在交接件上消失（IR §7）")
        if not isinstance(s.get("audit_tiers_run"), list) or \
                not all(isinstance(t, int) for t in s.get("audit_tiers_run", [])):
            p.append(f"{tag}: `audit_tiers_run` 不是整数数组")
        if s.get("verdict") not in VERDICTS:
            p.append(f"{tag}: `verdict` 取值 {s.get('verdict')!r} 不在三值域内")
        c = s.get("assertions")
        if not isinstance(c, dict) or any(not isinstance(c.get(k), int)
                                          for k in COUNT_KEYS):
            p.append(f"{tag}: `assertions` 缺三个整数计数")
            c = {k: 0 for k in COUNT_KEYS}
        if not isinstance(s.get("unresolved_coverage"), list) or \
                not all(isinstance(x, str) for x in s.get("unresolved_coverage", [])):
            p.append(f"{tag}: `unresolved_coverage` 不是字符串数组")

        ops = s.get("operations")
        if not isinstance(ops, list) or not ops:
            p.append(f"{tag}: `operations` 不是非空数组")
            continue
        for o in ops:
            if not isinstance(o, dict):
                p.append(f"{tag}: operation 条目不是对象")
                continue
            if o.get("op") not in vocab:
                p.append(f"{tag}: operation `{o.get('op')}` 不在封闭词汇表内")
            if not isinstance(o.get("artifact"), str):
                p.append(f"{tag}: operation `{o.get('op')}` 的 `artifact` 不是字符串")
            r = o.get("source_reachability")
            if isinstance(r, list):
                p.append(f"{tag}/{o.get('artifact')}: `source_reachability` 报成了"
                         "数组——同一字段时而枚举值时而数组，消费方按 schema 解析必错")
            elif r not in REACH:
                p.append(f"{tag}/{o.get('artifact')}: `source_reachability` 取值 "
                         f"{r!r} 不在 {REACH} 内")

        # ---- 档 2 · 与契约逐 operation 对账
        cst = by_stage.get(s.get("stage"))
        if cst is None:
            p.append(f"{tag}: 契约里没有这一段")
        else:
            want = {o.get("artifact"): o for o in cst.get("operations", [])}
            got = {o.get("artifact"): o for o in ops if isinstance(o, dict)}
            for a in sorted(set(want) - set(got)):
                p.append(f"{tag}: 契约声明的 operation（产物 {a}）在 manifest 上"
                         "没有条目——清单被截断，交接件少了一整个面")
            for a in sorted(set(got) - set(want)):
                p.append(f"{tag}: manifest 多报了产物 {a} 的 operation，契约里没有")
            for a in sorted(set(want) & set(got)):
                w = want[a].get("source_reachability", "machine")
                g = got[a].get("source_reachability")
                if isinstance(g, str) and g != w:
                    p.append(f"{tag}/{a}: 可达性契约声明 {w}、manifest 报 {g}"
                             "——人做的那段被记成机器可重读，交接时无人再去补验")
                if got[a].get("op") != want[a].get("op"):
                    p.append(f"{tag}/{a}: operation 名与契约不符")

    # ---- 档 3 · 三值判定自洽
    for s in mf["stages"]:
        c = s.get("assertions") or {}
        tag = f"段 {s.get('stage', '<无名>')}"
        if not isinstance(c.get("unverified"), int):
            continue
        if c.get("failed"):
            want = "FAIL"
        elif c["unverified"]:
            want = "PASS_WITH_UNVERIFIED"
        else:
            want = "PASS"
        if s.get("verdict") != want:
            p.append(f"{tag}: 计数 {dict(c)} 应判 {want}、实报 {s.get('verdict')}"
                     "——三值压成二值，「有面没验」在交接件上消失")
        if c["unverified"] and not s.get("unresolved_coverage"):
            p.append(f"{tag}: unverified={c['unverified']} 而 "
                     "`unresolved_coverage` 为空——说了有面没验，没说是哪一面")

    vs = [s.get("verdict") for s in mf["stages"]]
    if "FAIL" in vs:
        want = "FAIL"
    elif "PASS_WITH_UNVERIFIED" in vs:
        want = "PASS_WITH_UNVERIFIED"
    else:
        want = "PASS"
    if mf.get("final_verdict") != want:
        p.append(f"`final_verdict` 按各段应为 {want}、实报 {mf.get('final_verdict')}"
                 "（IR §7 生成规则）")
    return p


# ---------------------------------------------------------------- 自检
def _emit(run_dir, contract, out, source=None):
    """真跑一次审核器，拿它落盘的 manifest。不手搓样件——手搓的是我以为的形状。"""
    cmd = [sys.executable, AUDIT, run_dir, "--contract", contract, "--all",
           "--manifest", out, "--run-dir-source", "explicit_arg"]
    if source:
        cmd += ["--source", source]
    subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def _d_stage_level(m):
    """把可达性提到段级（IR §7 点名禁的那一种）"""
    for s in m["stages"]:
        s["source_reachability"] = s["operations"][0]["source_reachability"]
        for o in s["operations"]:
            o.pop("source_reachability", None)
    return m


def _d_truncate(m):
    """一段两个 operation 时只报第一个——每一项字段仍齐全，少的是条目"""
    for s in m["stages"]:
        del s["operations"][1:]
    return m


def _d_polymorphic(m):
    """标量枚举改报数组"""
    m["stages"][0]["operations"][0]["source_reachability"] = list(REACH)
    return m


def _d_reach_normalized(m):
    """human_handoff 被静默归一成 machine"""
    for s in m["stages"]:
        for o in s["operations"]:
            o["source_reachability"] = "machine"
    return m


def _d_two_valued(m):
    """PASS_WITH_UNVERIFIED 压成 PASS（三值压二值）"""
    for s in m["stages"]:
        if s["verdict"] == "PASS_WITH_UNVERIFIED":
            s["verdict"] = "PASS"
    if m["final_verdict"] == "PASS_WITH_UNVERIFIED":
        m["final_verdict"] = "PASS"
    return m


def _d_silent_unresolved(m):
    """说了有面没验，但不说是哪一面"""
    for s in m["stages"]:
        s["unresolved_coverage"] = []
    return m


def _d_out_of_vocab(m):
    """operation 名出封闭词汇表"""
    m["stages"][0]["operations"][0]["op"] = "reconcile"
    return m


def self_test():
    vocab = set(json.load(open(IR_JSON, encoding="utf-8"))["operations"])
    fx = os.path.join(ROOT, "fixtures")
    cases = [
        # (标签, run_dir, 契约, 是否给 --source, 该件要验的形态)
        ("multiop-golden", "runs-multiop/golden-multiop", "assertions_multiop.json",
         False, "一段挂两个 operation"),
        ("jh-golden", "runs-jh/golden-jh", "assertions_jh.json",
         False, "带 human_handoff 的段"),
        ("oaq-no-source", "runs/golden-task1", "assertions_oaq.json",
         False, "T2 无源件 → UNVERIFIED 三值"),
    ]
    reals, bad = {}, 0
    print("== 正例：审核器真落盘的 manifest 应当可消费 ==")
    for tag, rd, cf, src, why in cases:
        cpath = os.path.join(fx, cf)
        m = _emit(rd, cpath, f"/tmp/mc_{tag}.json")
        probs = consume(m, json.load(open(cpath, encoding="utf-8")), vocab)
        reals[tag] = (m, json.load(open(cpath, encoding="utf-8")))
        ok = not probs
        bad += 0 if ok else 1
        print(f"  [{'✓' if ok else '✗'}] {tag:16s} {why}  "
              f"final={m['final_verdict']}")
        for x in probs[:3]:
            print(f"        ! {x}")

    degradations = [
        ("D1 可达性提到段级", "multiop-golden", _d_stage_level),
        ("D2 operation 清单截断", "multiop-golden", _d_truncate),
        ("D3 枚举值改报数组", "multiop-golden", _d_polymorphic),
        ("D4 human_handoff 归一成 machine", "jh-golden", _d_reach_normalized),
        ("D5 三值压成二值", "oaq-no-source", _d_two_valued),
        ("D6 未验面不列清单", "oaq-no-source", _d_silent_unresolved),
        ("D7 operation 名出词汇表", "multiop-golden", _d_out_of_vocab),
    ]
    print("\n== 负例：以下每一种降级都必须被拒 ==")
    for label, base, fn in degradations:
        m, c = reals[base]
        probs = consume(fn(copy.deepcopy(m)), c, vocab)
        ok = bool(probs)
        bad += 0 if ok else 1
        print(f"  [{'✓' if ok else '✗ 未检出'}] {label}")
        for x in probs[:2]:
            print(f"        ! {x}")

    print(f"\n总判定: {'PASS' if bad == 0 else f'FAIL（{bad} 项不合）'}")
    return 0 if bad == 0 else 1


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return self_test()
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-4])
        return 2
    vocab = set(json.load(open(IR_JSON, encoding="utf-8"))["operations"])
    mf = json.load(open(sys.argv[1], encoding="utf-8"))
    contract = json.load(open(sys.argv[2], encoding="utf-8"))
    probs = consume(mf, contract, vocab)
    print(f"总判定: {'可消费' if not probs else 'FAIL'}")
    for x in probs:
        print("  ! " + x)
    return 0 if not probs else 1


if __name__ == "__main__":
    sys.exit(main())
