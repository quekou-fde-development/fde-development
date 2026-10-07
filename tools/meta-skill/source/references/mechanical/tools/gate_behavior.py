#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选树外的 gate 行为承诺：每道实际闸须保留正例与定向拒绝能力集。"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REGISTRY = os.path.join(ROOT, "gate_behavior_registry.json")
FIXTURE_REGISTRY = os.path.join(ROOT, "fixture_registry.json")
PREDICATE_RUNNER = os.path.join(HERE, "predicate_family_behavior.py")
GATES = ("M7", "M8", "M9", "M10", "M11")
CAUSE_RE = re.compile(r"\[CAUSE:([A-Z0-9_.-]+)\]")
M7_COMMAND_RE = re.compile(
    r"L(\d+)\s+围栏外行内可执行命令未落四槽:\s+`([^`]+)`")
M7_MISSING_SLOTS_RE = re.compile(
    r"L(\d+)\s+(编号步|列表步)缺槽\s+\[([^\]]*)\]")
M8_DISPATCH_UNBOUND_RE = re.compile(
    r"段\s+(\S+)\s+无执行入口.*?；(\S+)\s+两旗标齐，但段名不在被 "
    r"`--stage` 索引并调用的字典 dispatch 键内——声明一张表不等于把控制流交给它")
M8_UNREACHABLE_WRITE_RE = re.compile(
    r"段\s+(\S+)\s+的入口\s+\[[^\]]*\]\s+不产出\s+(\S+)"
    r"——从本段 handler 不可达真实写盘；不可达机制\s+\[([^\]]*)\]")
M8_RUNTIME_PROBE_RE = re.compile(
    r"段\s+(\S+)\s+隔离真跑未产出\s+(\S+)——候选结果\s+(.+)")
M9_PAYLOAD_COLLISION_RE = re.compile(
    r"(\S+/custom:\S+): golden 与 mutant 载荷指纹相同（([0-9a-f]+)）"
    r"——同一份料换个目录名／只改元数据，正例反例同源，不构成对照")
M9_MINIMUM_FAMILIES_RE = re.compile(
    r"(\S+/\S+): 最低强断言族缺\s+\[([^\]]*)\]")
M9_FAMILY_TIER_RE = re.compile(
    r"(\S+/\S+/\S+): family↔tier 不符——(\S+) 须 T(\S+)，实为 T(\d+)")
M9_SOURCE_HEADING_RE = re.compile(
    r"(\S+/custom:\S+): source_anchor「([^」]+)」不成立——(\S+) 里没有标题"
    r"「([^」]+)」（须规范化后全等，不认子串）")


def _run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


def _validate(skill_dir, fixture, extra=()):
    p = _run([sys.executable, os.path.join(skill_dir, "scripts", "validate.py"),
              fixture, *extra])
    status = {}
    for line in p.stdout.splitlines():
        m = re.match(r"^(M\d+) (PASS|FAIL|SKIP|WARN|NOTE)", line)
        if m and m.group(1) not in status:
            status[m.group(1)] = m.group(2)
    return p, status


def _gate_block(stdout, target_gate):
    """只取目标 M 闸自己的首行与缩进 detail；别处回显不算指定理由。"""
    lines, block, active = stdout.splitlines(), [], False
    header = re.compile(r"^(M\d+)\s+(PASS|FAIL|SKIP|WARN|NOTE):?")
    for line in lines:
        match = header.match(line)
        if match:
            if active:
                break
            active = match.group(1) == target_gate
        if active:
            block.append(line)
    return "\n".join(block)


def _cause_codes(text):
    """返回诊断中的机器病因集合；重复同码允许，跨组超集不允许。"""
    return set(CAUSE_RE.findall(text))


def _exact_cause(text, expected):
    return _cause_codes(text) == {expected}


def _block_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _m7_command_diagnostics(text):
    return {(int(line), command) for line, command in M7_COMMAND_RE.findall(text)}


def _quoted_items(body):
    return re.findall(r"'([^']+)'", body)


def _diagnostic_features(text, binding):
    """从人读诊断抽出 registry 约束的结构事实；只认完整语义句式。"""
    kind = binding.get("kind")
    if kind == "m7_command":
        rows = [{"line": int(line), "command": command}
                for line, command in M7_COMMAND_RE.findall(text)]
    elif kind == "m7_missing_slots":
        rows = [{"line": int(line), "shape": shape,
                 "missing": _quoted_items(missing)}
                for line, shape, missing in M7_MISSING_SLOTS_RE.findall(text)]
    elif kind == "m8_dispatch_unbound":
        rows = [{"stage": stage, "script": script}
                for stage, script in M8_DISPATCH_UNBOUND_RE.findall(text)]
    elif kind == "m8_unreachable_write":
        rows = [{"stage": stage, "artifact": artifact,
                 "mechanisms": _quoted_items(mechanisms)}
                for stage, artifact, mechanisms in M8_UNREACHABLE_WRITE_RE.findall(text)]
    elif kind == "m8_runtime_probe":
        rows = []
        for stage, artifact, detail in M8_RUNTIME_PROBE_RE.findall(text):
            outcome = ("runtime_failed" if "运行失败 rc=" in detail
                       else "rc0_no_artifact" if "rc=0 但产物缺失" in detail
                       else "probe_unavailable")
            row = {"stage": stage, "artifact": artifact, "outcome": outcome}
            failure = re.search(r"\bkind=([a-z0-9_]+)", detail)
            if failure:
                row["failure"] = failure.group(1)
            rows.append(row)
    elif kind == "m9_payload_collision":
        rows = [{"operation": operation, "fingerprint": fingerprint}
                for operation, fingerprint in M9_PAYLOAD_COLLISION_RE.findall(text)]
    elif kind == "m9_minimum_families":
        rows = [{"operation": operation, "missing": _quoted_items(missing)}
                for operation, missing in M9_MINIMUM_FAMILIES_RE.findall(text)]
    elif kind == "m9_family_tier":
        rows = [{"assertion": assertion, "family": family,
                 "required_tier": required, "actual_tier": actual}
                for assertion, family, required, actual in M9_FAMILY_TIER_RE.findall(text)]
    elif kind == "m9_source_heading":
        rows = [{"operation": operation, "anchor": anchor,
                 "file": file_name, "heading": heading}
                for operation, anchor, file_name, heading in
                M9_SOURCE_HEADING_RE.findall(text)]
    else:
        return []
    return sorted(rows, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))


def _exact_diagnostic_binding(text, expected):
    want = sorted(expected.get("expected", []),
                  key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
    return _diagnostic_features(text, expected) == want


def _neutral_copy(source, parent, name):
    target = os.path.join(parent, name)
    shutil.copytree(source, target,
                    ignore=shutil.ignore_patterns("GATE_INJECTION.json"))
    return target


def _positive_control(skill_dir, suite, fixture_registry, positive_cache, neutral_root):
    positive = fixture_registry["suites"][suite]["positive"]
    key = (suite, positive)
    if key in positive_cache:
        return positive_cache[key]
    source = os.path.join(ROOT, suite, positive)
    neutral = _neutral_copy(source, neutral_root, f"positive-{len(positive_cache)}")
    pp, pst = _validate(skill_dir, source)
    np, nst = _validate(skill_dir, neutral)
    bad = [gate for gate in GATES if pst.get(gate) != "PASS"]
    neutral_bad = [gate for gate in GATES if nst.get(gate) != "PASS"]
    control = {
        "name": positive,
        "pass": pp.returncode == 0 and np.returncode == 0 and not bad and not neutral_bad,
        "rc": pp.returncode,
        "neutral_rc": np.returncode,
        "bad_gates": bad,
        "neutral_bad_gates": neutral_bad,
        "metadata_independent": pst == nst,
    }
    if not control["metadata_independent"]:
        control["pass"] = False
    positive_cache[key] = control
    return control


def _witness_specs(spec, fixture_registry):
    if spec.get("kind") == "validate_named":
        pairs = [tuple(x) for x in spec.get("witnesses", [])]
    else:
        pairs = []
        for suite in spec.get("suites", []):
            for name, (target, _reason) in \
                    fixture_registry["suites"][suite]["directed"].items():
                if target == spec.get("target_gate"):
                    pairs.append((suite, name))
    return pairs


def _validate_witness(skill_dir, gid, spec, fixture_registry, cause_registry,
                      block_baselines, diagnostic_registry, positive_cache):
    pairs = _witness_specs(spec, fixture_registry)
    problems, details = [], []
    if not pairs:
        problems.append("行为 registry 未选中任何定向负例")
    selected = {negative for _suite, negative in pairs}
    with tempfile.TemporaryDirectory(prefix="gate_behavior_validate_") as neutral_root:
        controls = {}
        for suite, _negative in pairs:
            control = _positive_control(skill_dir, suite, fixture_registry,
                                        positive_cache, neutral_root)
            controls[suite] = control
            if not control["pass"]:
                problems.append(f"{suite} 正例 {control['name']} 未在原名/中性名下全 PASS："
                                f"rc={control['rc']}/{control['neutral_rc']}，"
                                f"非 PASS={control['bad_gates']}/{control['neutral_bad_gates']}，"
                                f"状态同构={control['metadata_independent']}")

        for index, (suite, negative) in enumerate(pairs):
            expected = fixture_registry["suites"][suite]["directed"].get(negative)
            if not expected:
                problems.append(f"{suite}/{negative} 未进入 fixture_registry.json")
                continue
            target_gate, reason = expected
            source = os.path.join(ROOT, suite, negative)
            inj_path = os.path.join(source, "GATE_INJECTION.json")
            try:
                injection = json.load(open(inj_path, encoding="utf-8"))
            except (OSError, ValueError) as e:
                problems.append(f"{suite}/{negative} 注入声明不可读：{e}")
                continue
            if [injection.get("must_be_rejected_by"),
                    injection.get("must_include_reason")] != expected:
                problems.append(f"{suite}/{negative} 注入声明与 fixture registry 漂移")
            extra = ["--persistent"] if injection.get("needs_persistent_flag") else []
            neutral = _neutral_copy(source, neutral_root, f"negative-{index}")
            op, ost = _validate(skill_dir, source, extra)
            np, nst = _validate(skill_dir, neutral, extra)
            target_hit = ost.get(target_gate) == "FAIL" and nst.get(target_gate) == "FAIL"
            original_block = _gate_block(op.stdout, target_gate)
            neutral_block = _gate_block(np.stdout, target_gate)
            reason_hit = reason in original_block and reason in neutral_block
            expected_cause = cause_registry.get(suite, {}).get(negative)
            cause_hit = (expected_cause is not None and
                         _exact_cause(original_block, expected_cause) and
                         _exact_cause(neutral_block, expected_cause))
            expected_diagnostic = diagnostic_registry.get(suite, {}).get(negative)
            diagnostic_hit = (expected_diagnostic is None or
                              (_exact_diagnostic_binding(original_block,
                                                         expected_diagnostic) and
                               _exact_diagnostic_binding(neutral_block,
                                                         expected_diagnostic)))
            # GATE_INJECTION.json 本身按设计触发 M4 杂物 WARN；剥掉它后 M4 变化是
            # harness 元数据的预期差异。行为承诺只比较本器负责的 M7-M11 五闸。
            same_status = ({gate: ost.get(gate) for gate in GATES} ==
                           {gate: nst.get(gate) for gate in GATES})
            if not target_hit:
                problems.append(f"{suite}/{negative} 未在原名/中性名下都被 {target_gate} 拒绝："
                                f"status={ost.get(target_gate)}/{nst.get(target_gate)}")
            if not reason_hit:
                problems.append(f"{suite}/{negative} 目标闸 {target_gate} 自己的 detail 块"
                                f"未在原名/中性名下都命中理由「{reason}」")
            if expected_cause is None:
                problems.append(f"{suite}/{negative} 未登记 directed cause")
            elif not cause_hit:
                problems.append(f"{suite}/{negative} 目标闸 {target_gate} 病因组须精确为 "
                                f"{expected_cause}，实为 "
                                f"{sorted(_cause_codes(original_block))}/"
                                f"{sorted(_cause_codes(neutral_block))}")
            if expected_diagnostic and not diagnostic_hit:
                problems.append(f"{suite}/{negative} 结构诊断绑定须精确为 "
                                f"{expected_diagnostic.get('expected')}，实为 "
                                f"{_diagnostic_features(original_block, expected_diagnostic)}/"
                                f"{_diagnostic_features(neutral_block, expected_diagnostic)}")
            if op.returncode == 0 or np.returncode == 0:
                problems.append(f"{suite}/{negative} 原名/中性名有坏件退出码 0："
                                f"rc={op.returncode}/{np.returncode}")
            if not same_status:
                problems.append(f"{suite}/{negative} 改成中性包名并剥 GATE_INJECTION 后"
                                "五闸状态漂移——行为门依赖测试元数据")
            details.append({"suite": suite, "negative": negative,
                            "target_gate": target_gate, "target_hit": target_hit,
                            "reason": reason, "reason_hit": reason_hit,
                            "expected_cause": expected_cause, "cause_hit": cause_hit,
                            "expected_diagnostic": expected_diagnostic,
                            "diagnostic_hit": diagnostic_hit,
                            "original_block_sha256": _block_digest(original_block),
                            "neutral_block_sha256": _block_digest(neutral_block),
                            "metadata_independent": same_status})

    selected_pairs = {(d["suite"], d["negative"]) for d in details}
    all_members = {}
    for suite, suite_spec in fixture_registry.get("suites", {}).items():
        for negative, (target_gate, _reason) in suite_spec.get("directed", {}).items():
            cause = cause_registry.get(suite, {}).get(negative)
            all_members.setdefault(f"{target_gate}|{cause}", set()).add((suite, negative))
    for group, expected_count in block_baselines.items():
        members = all_members.get(group, set())
        if not members or not members.issubset(selected_pairs):
            continue
        group_details = [d for d in details
                         if (d["suite"], d["negative"]) in members]
        original_count = len({d["original_block_sha256"] for d in group_details})
        neutral_count = len({d["neutral_block_sha256"] for d in group_details})
        if original_count != expected_count or neutral_count != expected_count:
            problems.append(
                f"{group} 组内诊断块数须为 {expected_count}，"
                f"实为原名/中性名 {original_count}/{neutral_count}")
    return {"gate_id": gid, "positive_pass": all(c["pass"] for c in controls.values()),
            "witness_count": len(details),
            "target_hit": bool(details) and all(d["target_hit"] for d in details),
            "reason_hit": bool(details) and all(d["reason_hit"] for d in details),
            "cause_hit": bool(details) and all(d["cause_hit"] for d in details),
            "diagnostic_hit": bool(details) and
            all(d["diagnostic_hit"] for d in details),
            "metadata_independent": bool(details) and
            all(d["metadata_independent"] for d in details),
            "details": details, "problems": problems}


def _audit(skill_dir, run_dir, contract, source=None):
    cmd = [sys.executable, os.path.join(skill_dir, "scripts", "audit.py"), run_dir,
           "--contract", contract, "--all", "--json"]
    if source:
        cmd += ["--source", source]
    p = _run(cmd)
    try:
        payload = json.loads(p.stdout)
    except json.JSONDecodeError:
        payload = {"rows": [], "verdict": "ERROR"}
    return p, payload


def _compare_paths_witness(skill_dir, gid, spec):
    contract_path = os.path.join(ROOT, "fixtures", "assertions_oaq.json")
    run_dir = os.path.join(ROOT, "runs", "golden-task1")
    source = os.path.join(ROOT, "fixtures", "mock-task1.md")
    base = json.load(open(contract_path, encoding="utf-8"))
    pp, prep = _audit(skill_dir, run_dir, contract_path, source)
    positive_pass = pp.returncode == 0 and not any(
        row.get("status") == "FAIL" for row in prep.get("rows", []))

    problems = []
    def find_target(contract):
        for stage in contract["stages"]:
            for op in stage["operations"]:
                for assertion in op["assertions"]:
                    if assertion.get("id") == spec["target_assertion"]:
                        return assertion
        return None

    if find_target(base) is None:
        problems.append(f"基线契约缺断言 {spec['target_assertion']}")
        return {"gate_id": gid, "positive_pass": positive_pass, "problems": problems}
    if not positive_pass:
        problems.append(f"compare_paths 未改正例未 PASS：rc={pp.returncode}")

    cases = [
        ("empty", "为空或非列表"),
        ("no-input", "须同时显式声明"),
        ("no-output", "须同时显式声明"),
        ("dual-idiom", "同时声明"),
    ]
    details = []
    with tempfile.TemporaryDirectory(prefix="gate_behavior_cp_") as td:
        for name, reason in cases:
            contract = copy.deepcopy(base)
            target = find_target(contract)
            if name == "empty":
                target["predicate"]["compare_paths"] = []
            elif name == "no-input":
                target["predicate"]["compare_paths"][0].pop("input")
            elif name == "no-output":
                target["predicate"]["compare_paths"][0].pop("output")
            else:
                target["predicate"]["compare_map"] = "counts"
            bad_contract = os.path.join(td, name + ".json")
            with open(bad_contract, "w", encoding="utf-8") as f:
                json.dump(contract, f, ensure_ascii=False, indent=1)
            np, nrep = _audit(skill_dir, run_dir, bad_contract, source)
            rows = {row.get("id"): row for row in nrep.get("rows", [])}
            target_row = rows.get(spec["target_assertion"], {})
            target_hit = target_row.get("status") == "FAIL"
            reason_hit = reason in target_row.get("detail", "")
            if not target_hit:
                problems.append(f"compare_paths/{name}: {spec['target_assertion']} 未判 FAIL")
            if not reason_hit:
                problems.append(f"compare_paths/{name}: 指定理由未命中「{reason}」")
            if np.returncode != 1:
                problems.append(f"compare_paths/{name}: 坏契约退出码须 1，实为 {np.returncode}")
            details.append({"negative": name, "target_hit": target_hit,
                            "reason": reason, "reason_hit": reason_hit})
    return {"gate_id": gid, "positive_pass": positive_pass,
            "target_assertion": spec["target_assertion"], "witness_count": len(details),
            "target_hit": all(d["target_hit"] for d in details),
            "reason_hit": all(d["reason_hit"] for d in details),
            "details": details, "problems": problems}


def _audit_identity_witness(skill_dir, gid, spec):
    good = os.path.join(ROOT, "gate-fixtures", "G0-good")
    contract_path = os.path.join(good, "assertions.json")
    run_dir = os.path.join(good, "fixtures", "golden")
    pp, prep = _audit(skill_dir, run_dir, contract_path)
    positive_pass = pp.returncode == 0 and not any(
        row.get("status") == "FAIL" for row in prep.get("rows", []))
    problems = []
    if not positive_pass:
        problems.append(f"audit.run 未改正例未 PASS：rc={pp.returncode}")
    base = json.load(open(contract_path, encoding="utf-8"))
    details = []
    cases = spec.get("cases", {})
    if not cases:
        problems.append("audit.run 未登记身份病因 cases")
    with tempfile.TemporaryDirectory(prefix="gate_behavior_identity_") as td:
        for name, case in cases.items():
            reason = case["reason"]
            expected_cause = case["cause_group"]
            contract = copy.deepcopy(base)
            if name == "empty-stage":
                contract["stages"][0]["stage"] = ""
            elif name == "duplicate-stage":
                contract["stages"][1]["stage"] = contract["stages"][0]["stage"]
            elif name == "duplicate-id":
                assertions = contract["stages"][0]["operations"][0]["assertions"]
                assertions[1]["id"] = assertions[0]["id"]
            elif name == "empty-id":
                contract["stages"][0]["operations"][0]["assertions"][0]["id"] = ""
            else:
                problems.append(f"audit.run registry 含未知身份负例 {name}")
                continue
            bad_contract = os.path.join(td, name + ".json")
            with open(bad_contract, "w", encoding="utf-8") as f:
                json.dump(contract, f, ensure_ascii=False, indent=1)
            np, _nrep = _audit(skill_dir, run_dir, bad_contract)
            target_hit = np.returncode == 2
            diagnostic = np.stdout + np.stderr
            reason_hit = reason in diagnostic
            cause_hit = _exact_cause(diagnostic, expected_cause)
            if not target_hit:
                problems.append(f"{name}: 契约退出码须 2，实为 {np.returncode}")
            if not reason_hit:
                problems.append(f"{name}: 指定理由未命中「{reason}」")
            if not cause_hit:
                problems.append(f"{name}: 病因组须精确为 {expected_cause}，"
                                f"实为 {sorted(_cause_codes(diagnostic))}")
            details.append({"negative": name, "target_hit": target_hit,
                            "reason": reason, "reason_hit": reason_hit,
                            "expected_cause": expected_cause, "cause_hit": cause_hit})
    return {"gate_id": gid, "positive_pass": positive_pass,
            "witness_count": len(details),
            "target_hit": all(d["target_hit"] for d in details),
            "reason_hit": all(d["reason_hit"] for d in details),
            "cause_hit": all(d["cause_hit"] for d in details),
            "details": details, "problems": problems}


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--json"):
        print("用法: gate_behavior.py <skill_dir> [--json]", file=sys.stderr)
        return 2
    skill_dir = os.path.abspath(sys.argv[1])
    as_json = "--json" in sys.argv[2:]
    try:
        registry = json.load(open(REGISTRY, encoding="utf-8"))
        fixture_registry = json.load(open(FIXTURE_REGISTRY, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"行为 registry 不可读：{e}", file=sys.stderr)
        return 2

    results, positive_cache = {}, {}
    cause_registry = registry.get("directed_causes", {})
    block_baselines = registry.get("cause_block_baselines", {})
    diagnostic_registry = registry.get("directed_diagnostics", {})
    registry_problems = []
    for suite, suite_spec in fixture_registry.get("suites", {}).items():
        expected = set(suite_spec.get("directed", {}))
        actual = set(cause_registry.get(suite, {}))
        if expected != actual:
            registry_problems.append(
                f"{suite} directed cause 与 fixture 集不闭合："
                f"缺 {sorted(expected - actual)}，多 {sorted(actual - expected)}")
    extra_suites = sorted(set(cause_registry) - set(fixture_registry.get("suites", {})))
    if extra_suites:
        registry_problems.append(f"directed cause 含未知 suites: {extra_suites}")
    cause_members = {}
    for suite, suite_spec in fixture_registry.get("suites", {}).items():
        for negative, (gate, _reason) in suite_spec.get("directed", {}).items():
            cause = cause_registry.get(suite, {}).get(negative)
            cause_members.setdefault(f"{gate}|{cause}", set()).add((suite, negative))
    multi_groups = {group for group, members in cause_members.items() if len(members) > 1}
    if multi_groups != set(block_baselines):
        registry_problems.append(
            "cause block baseline 与全部多成员病因组不闭合："
            f"缺 {sorted(multi_groups - set(block_baselines))}，"
            f"多 {sorted(set(block_baselines) - multi_groups)}")
    for group, expected_count in block_baselines.items():
        if not isinstance(expected_count, int) or not 1 <= expected_count <= \
                len(cause_members.get(group, ())):
            registry_problems.append(
                f"{group} block baseline 非法: {expected_count}，"
                f"成员数={len(cause_members.get(group, ()))}")
    required_diagnostics = set().union(*(
        cause_members.get(group, set()) for group, count in block_baselines.items()
        if count > 1)) if block_baselines else set()
    actual_diagnostics = {(suite, negative)
                          for suite, bindings in diagnostic_registry.items()
                          for negative in bindings}
    if required_diagnostics != actual_diagnostics:
        registry_problems.append(
            "逐 fixture 结构诊断绑定与可分多成员组不闭合："
            f"缺 {sorted(required_diagnostics - actual_diagnostics)}，"
            f"多 {sorted(actual_diagnostics - required_diagnostics)}")
    predicate_payload, predicate_global_problems = None, []
    if any(spec.get("kind") == "audit_family" for spec in registry.get("gates", {}).values()):
        p = _run([sys.executable, PREDICATE_RUNNER, skill_dir, "--json"])
        try:
            predicate_payload = json.loads(p.stdout)
        except json.JSONDecodeError:
            predicate_payload = {"results": {}, "problems": [
                f"predicate family runner 跑不出 JSON：rc={p.returncode} {p.stderr[-300:]}"
            ]}
        predicate_global_problems.extend(predicate_payload.get("problems", []))
        expected_rc = 0 if not predicate_payload.get("problems") else 1
        if p.returncode != expected_rc:
            predicate_global_problems.append(
                f"predicate family runner 退出码与 problems 不一致：rc={p.returncode}")
    for gid, spec in registry.get("gates", {}).items():
        if spec.get("kind") in {"validate_registered", "validate_named"}:
            result = _validate_witness(skill_dir, gid, spec, fixture_registry,
                                       cause_registry, block_baselines,
                                       diagnostic_registry, positive_cache)
        elif spec.get("kind") == "audit_compare_paths":
            result = _compare_paths_witness(skill_dir, gid, spec)
        elif spec.get("kind") == "audit_contract_identity":
            result = _audit_identity_witness(skill_dir, gid, spec)
        elif spec.get("kind") == "audit_family":
            family = spec.get("family")
            source = (predicate_payload or {}).get("results", {}).get(family)
            if source is None:
                result = {"gate_id": gid, "positive_pass": False,
                          "witness_count": 0, "target_hit": False,
                          "reason_hit": False,
                          "problems": [f"predicate family witness 缺 {family}"]}
            else:
                result = copy.deepcopy(source)
                if result.get("gate_id") != gid:
                    result.setdefault("problems", []).append(
                        f"predicate family Gate-ID 漂移：runner={result.get('gate_id')} registry={gid}")
                result["gate_id"] = gid
        else:
            result = {"gate_id": gid, "problems": [f"未知 witness kind {spec.get('kind')}"]}
        results[gid] = result

    problems = list(registry_problems) + list(predicate_global_problems)
    problems.extend(f"{gid}: {problem}" for gid, result in results.items()
                    for problem in result.get("problems", []))
    payload = {"witness_ids": sorted(results), "results": results,
               "problems": problems, "verdict": "PASS" if not problems else "FAIL"}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for gid, result in results.items():
            print(f"{gid:<28} {'[OK]' if not result.get('problems') else '[BAD]'}  "
                  f"positive={result.get('positive_pass')} "
                  f"negative={result.get('witness_count', 0)} "
                  f"target={result.get('target_hit')} reason={result.get('reason_hit')} "
                  f"cause={result.get('cause_hit', 'n/a')} "
                  f"diagnostic={result.get('diagnostic_hit', 'n/a')} "
                  f"metadata_independent={result.get('metadata_independent', 'n/a')}")
        print(f"总判定: {payload['verdict']}")
        for problem in problems:
            print("  ! " + problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
