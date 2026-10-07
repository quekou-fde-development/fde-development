#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锁住 SKILL / contract IR / obligation registry / 实际机械闸 / 独立行为证据五面。

用法: python3 skill_drift.py [<skill_dir>] [--static-only]
退出码 0 = 五面一致；1 = 有漂移或行为 witness 失败；2 = 文件缺失或不可解析；
3 = 静态登记面一致但行为面未跑，只可作局部诊断，不构成验收 PASS。
"""
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SKILL = os.path.normpath(os.path.join(HERE, "..", "..", "v3.8-draft"))
BEHAVIOR_RUNNER = os.path.join(HERE, "gate_behavior.py")
BEHAVIOR_REGISTRY = os.path.normpath(os.path.join(HERE, "..", "gate_behavior_registry.json"))
SRC_DECL = re.compile(r"contract_ir(?:\.md)?\s*§\s*([0-9]+(?:\.[0-9]+)*)")
ANY_SEC = re.compile(r"§\s*([0-9]+(?:\.[0-9]+)*)")
OBL_REF = re.compile(r"\[OBL:([A-Z0-9_.-]+)\]")
GATE_ID = re.compile(r"^\s*Gate-ID:\s*([A-Za-z0-9_.-]+)\s*$", re.M)
GATE_OBL = re.compile(r"^\s*Obligations:\s*(.+?)\s*$", re.M)


def ir_sections(md):
    out = set()
    for line in md.splitlines():
        m = re.match(r"#{2,4}\s+([0-9]+(?:\.[0-9]+)*)\s*·?\s", line)
        if m:
            out.add(m.group(1))
    return out


def parse_functions(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    return tree, {n.name: n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def effective_body(node):
    """去掉 docstring 后的实际 gate 函数体。"""
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and \
            isinstance(body[0].value, ast.Constant) and \
            isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def body_hash(tree, node):
    """与排版/行号无关的 gate + 本地可达 helper 实现体承诺。"""
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    seen, todo, chunks = set(), [node.name], []
    while todo:
        name = todo.pop()
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        fn = funcs[name]
        mod = copy.deepcopy(ast.Module(body=effective_body(fn), type_ignores=[]))
        # Python 3.12 adds empty type_params to nested function/class AST nodes.
        # It carries no semantics when empty; normalize it to the 3.9–3.11 form.
        # Preserve nonempty type parameters and every executable node/field.
        for child in ast.walk(mod):
            if 'type_params' in child._fields and not child.type_params:
                child._fields = tuple(field for field in child._fields if field != 'type_params')
        chunks.append(name + ":" + ast.dump(mod, annotate_fields=True,
                                            include_attributes=False))
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and \
                    n.func.id in funcs and n.func.id not in seen:
                todo.append(n.func.id)
    raw = "\n".join(sorted(chunks))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _constantish(node):
    if node is None or isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_constantish(x) for x in node.elts)
    if isinstance(node, ast.Dict):
        return all(_constantish(x) for x in node.keys + node.values)
    return False


def degenerate_body(node):
    """拒绝 pass / 恒返回常量或空容器的 gate 空壳。"""
    body = effective_body(node)
    if not body:
        return True
    return all(isinstance(st, ast.Pass) or
               (isinstance(st, ast.Return) and _constantish(st.value)) or
               (isinstance(st, ast.Expr) and _constantish(st.value))
               for st in body)


def _prune_dead_stmts(stmts):
    """裁掉常量假分支和终止语句后的源码；死调用不构成 gate 接线。"""
    out = []
    for st in stmts:
        if isinstance(st, ast.If) and isinstance(st.test, ast.Constant):
            out.extend(_prune_dead_stmts(st.body if bool(st.test.value) else st.orelse))
            continue
        if isinstance(st, ast.While) and isinstance(st.test, ast.Constant) and \
                not bool(st.test.value):
            out.extend(_prune_dead_stmts(st.orelse))
            continue
        node = copy.deepcopy(st)
        for field in ("body", "orelse", "finalbody"):
            if hasattr(node, field):
                setattr(node, field, _prune_dead_stmts(getattr(node, field)))
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                handler.body = _prune_dead_stmts(handler.body)
        out.append(node)
        if isinstance(st, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            break
    return out


def reachable_functions(tree):
    """从模块顶层真实调用根出发，沿本地函数调用边求可达集合。"""
    funcs = {n.name: n for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bindings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, []).append(node.value)
    module_stmts = [n for n in tree.body
                    if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.ClassDef))]

    def referenced_functions(stmts):
        mod = ast.Module(body=_prune_dead_stmts(stmts), type_ignores=[])
        refs = {n.func.id for n in ast.walk(mod)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        # `FAMILIES = {"x": handler}` 后由可达函数索引并调用，是常见的稳定
        # 解释器 dispatch。只有绑定名在可达函数中被读取时，才把表里的 handler
        # 纳入；盘在模块顶层却从未读取的诱饵表仍不算接线。
        loaded = {n.id for n in ast.walk(mod)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for name in loaded & set(bindings):
            for value in bindings[name]:
                refs |= {n.id for n in ast.walk(value)
                         if isinstance(n, ast.Name) and n.id in funcs}
        return refs

    seen, todo = set(), list(referenced_functions(module_stmts) & set(funcs))
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for callee in referenced_functions(effective_body(funcs[name])) & set(funcs):
            if callee not in seen:
                todo.append(callee)
    return seen


def called_outside(tree, target_name, target_node):
    """gate 须从模块程序入口可达；死函数 / if False 里的调用不算接线。"""
    return target_name in reachable_functions(tree)


def family_dispatch(tree):
    """从 audit.py 的 FAMILIES 值域机械发现全部谓词族入口。"""
    tables = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(t, ast.Name) and t.id == "FAMILIES" for t in node.targets):
            tables.append(node.value)
    problems, mapping = [], {}
    if len(tables) != 1:
        return {}, [f"audit.py 须恰有一份 FAMILIES dispatch，实为 {len(tables)}"]
    table = tables[0]
    if not isinstance(table, ast.Dict):
        return {}, ["audit.py 的 FAMILIES 须为静态 dict，动态构造无法闭合谓词族"]
    for key, value in zip(table.keys, table.values):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str) or not key.value:
            problems.append("FAMILIES family key 须为非空字符串字面量")
            continue
        if not isinstance(value, ast.Name):
            problems.append(f"FAMILIES[{key.value!r}] 须直指本地函数名")
            continue
        if key.value in mapping:
            problems.append(f"FAMILIES family 重复 {key.value!r}")
        mapping[key.value] = value.id
    handlers = list(mapping.values())
    duplicate_handlers = sorted({name for name in handlers if handlers.count(name) > 1})
    if duplicate_handlers:
        problems.append(f"FAMILIES 多族共用同一入口 {duplicate_handlers}——逐族 Gate-ID 无法唯一")
    return mapping, problems


def is_gate(filename, function, audit_family_functions):
    if filename == "scripts/validate.py":
        return bool(re.fullmatch(r"check_m\d+", function) or function.startswith("_check_"))
    return filename == "scripts/audit.py" and function in (
        {"_compare_paths", "run_audit"} | set(audit_family_functions))


def doc_contract(doc):
    gid = GATE_ID.search(doc)
    obl = GATE_OBL.search(doc)
    obligations = ({x.strip() for x in obl.group(1).split(",") if x.strip()}
                   if obl else set())
    sources = set(SRC_DECL.findall(doc))
    dropped = set(ANY_SEC.findall(doc)) - sources
    return (gid.group(1) if gid else None), obligations, sources, dropped


def main():
    args = sys.argv[1:]
    static_only = "--static-only" in args
    args = [arg for arg in args if arg != "--static-only"]
    if len(args) > 1:
        print("用法: skill_drift.py [<skill_dir>] [--static-only]", file=sys.stderr)
        return 2
    skill_dir = args[0] if args else DEFAULT_SKILL
    paths = {
        "SKILL.md": os.path.join(skill_dir, "SKILL.md"),
        "contract_ir.md": os.path.join(skill_dir, "references", "contract_ir.md"),
        "registry": os.path.join(skill_dir, "references", "obligation_registry.json"),
        "scripts/validate.py": os.path.join(skill_dir, "scripts", "validate.py"),
        "scripts/audit.py": os.path.join(skill_dir, "scripts", "audit.py"),
    }
    missing = [k for k, p in paths.items() if not os.path.isfile(p)]
    if missing:
        print(f"用法错：{skill_dir} 下找不到 {missing}——静态登记面缺面。")
        return 2
    try:
        skill = open(paths["SKILL.md"], encoding="utf-8").read()
        ir_md = open(paths["contract_ir.md"], encoding="utf-8").read()
        registry = json.load(open(paths["registry"], encoding="utf-8"))
        parsed = {name: parse_functions(paths[name])
                  for name in ("scripts/validate.py", "scripts/audit.py")}
    except (OSError, ValueError, SyntaxError) as e:
        print(f"用法错：静态登记面不可解析——{type(e).__name__}: {e}")
        return 2

    problems = []
    have_sections = ir_sections(ir_md)
    obligations = registry.get("obligations", {})
    gates = registry.get("gates", {})

    audit_dispatch, dispatch_problems = family_dispatch(parsed["scripts/audit.py"][0])
    problems.extend(dispatch_problems)
    audit_functions = parsed["scripts/audit.py"][1]
    for family, fn in sorted(audit_dispatch.items()):
        if fn not in audit_functions:
            problems.append(f"FAMILIES[{family!r}] 指向不存在函数 {fn}")
    expected_family_gid = {fn: f"audit.family.{family}"
                           for family, fn in audit_dispatch.items()}

    # registry 的双向引用先自洽。
    for oid, spec in obligations.items():
        source = str(spec.get("source_section", ""))
        if source not in have_sections:
            problems.append(f"obligation {oid} 指向 contract_ir.md §{source}，IR 无此节")
        owners = set(spec.get("enforced_by", []))
        if not owners:
            problems.append(f"obligation {oid} 无闸执行")
        for gid in owners:
            if gid not in gates:
                problems.append(f"obligation {oid} 指向未登记闸 {gid}——无闸执行")
            elif oid not in gates[gid].get("obligations", []):
                problems.append(f"obligation {oid} → {gid}，但闸未反向登记该 obligation")

    # 机械发现源码实际闸；删掉所有判据源声明也不会令闸从审计面消失。
    actual = {}
    for filename, (tree, fns) in parsed.items():
        for fn, node in fns.items():
            if not is_gate(filename, fn, set(audit_dispatch.values())):
                continue
            doc = ast.get_docstring(node) or ""
            gid, obs, sources, dropped = doc_contract(doc)
            owner = f"{filename}:{fn}"
            if not gid:
                problems.append(f"实际闸 {owner} 缺 Gate-ID")
                continue
            if filename == "scripts/audit.py" and fn in expected_family_gid and \
                    gid != expected_family_gid[fn]:
                problems.append(f"FAMILIES 入口 {fn} 的 Gate-ID 须为 "
                                f"{expected_family_gid[fn]}，实为 {gid}")
            if gid in actual:
                problems.append(f"Gate-ID {gid} 被多个源码函数占用")
            actual[gid] = (filename, fn, obs, sources, dropped, node,
                           called_outside(tree, fn, node))

    registry_ids = set(gates)
    actual_ids = set(actual)
    for gid in sorted(actual_ids - registry_ids):
        problems.append(f"实际闸 {gid} 未进入 obligation registry")
    for gid in sorted(registry_ids - actual_ids):
        problems.append(f"registry 闸 {gid} 在源码中不存在或缺 Gate-ID")

    for gid in sorted(registry_ids & actual_ids):
        filename, fn, obs, sources, dropped, node, hooked = actual[gid]
        spec = gates[gid]
        if filename != spec.get("file") or fn != spec.get("function"):
            problems.append(f"{gid} owner 漂移：源码={filename}:{fn}，"
                            f"registry={spec.get('file')}:{spec.get('function')}")
        if degenerate_body(node):
            problems.append(f"{gid} 闸函数体为空壳——pass/恒返回不构成执行")
        if not hooked:
            problems.append(f"{gid} 闸函数未接入调用链——registry 与 docstring 在，"
                            "但没有外部加载该 gate")
        expected_hash = spec.get("implementation_sha256")
        got_hash = body_hash(parsed[filename][0], node)
        if not expected_hash:
            problems.append(f"{gid} registry 缺 implementation_sha256——实现体无承诺")
        elif expected_hash != got_hash:
            problems.append(f"{gid} 实现体指纹漂移：registry={expected_hash[:16]}，"
                            f"source={got_hash[:16]}")
        expected_obs = set(spec.get("obligations", []))
        unknown = sorted(expected_obs - set(obligations))
        if unknown:
            problems.append(f"{gid} 登记未知 obligation {unknown}——无闸执行")
        if obs != expected_obs:
            problems.append(f"{gid} obligation 声明漂移：缺 {sorted(expected_obs-obs)}，"
                            f"多 {sorted(obs-expected_obs)}")
        expected_sources = {str(obligations[o]["source_section"])
                            for o in expected_obs if o in obligations}
        if not sources:
            problems.append(f"{gid} 该闸未声明判据源——删除全部 cite 不得令闸消失")
        elif sources != expected_sources:
            problems.append(f"{gid} 判据源漂移：缺 {sorted(expected_sources-sources)}，"
                            f"多 {sorted(sources-expected_sources)}")
        for sec in sorted(dropped):
            problems.append(f"{gid} docstring 有裸 §{sec}，判据源须带 contract_ir.md 前缀")
        for oid in expected_obs:
            if gid not in set(obligations.get(oid, {}).get("enforced_by", [])):
                problems.append(f"{gid} → {oid}，但 obligation 未反向登记该闸")

    # SKILL 引用 obligation，且每条 IR 强制引用须在同一行标出执行它的 obligation。
    cited_obs = set(OBL_REF.findall(skill))
    for oid in sorted(cited_obs - set(obligations)):
        problems.append(f"SKILL.md 新增要求 [OBL:{oid}]，registry 无登记——无闸执行")
    for oid in sorted(set(obligations) - cited_obs):
        problems.append(f"obligation {oid} 未被 SKILL.md 承接")
    for lineno, line in enumerate(skill.splitlines(), 1):
        refs = set(SRC_DECL.findall(line))
        line_obs = set(OBL_REF.findall(line))
        for sec in sorted(refs - have_sections):
            problems.append(f"SKILL.md L{lineno} 引用 contract_ir.md §{sec}，"
                            "IR 里无此节——死指针")
        for sec in refs:
            matching = {oid for oid in line_obs
                        if oid in obligations and str(obligations[oid]["source_section"]) == sec}
            if not matching:
                problems.append(f"SKILL.md L{lineno} 引用 contract_ir.md §{sec}，"
                                "同一行无对应 [OBL:id]——条文要求无闸执行")
        for oid in line_obs & set(obligations):
            source = str(obligations[oid]["source_section"])
            if source not in refs:
                problems.append(f"SKILL.md L{lineno} 的 [OBL:{oid}] 未在同一行引用"
                                f"判据源 contract_ir.md §{source}——规格书没承接它")

    behavior_ids = set()
    if not static_only:
        try:
            behavior_registry = json.load(open(BEHAVIOR_REGISTRY, encoding="utf-8"))
            behavior_ids = set(behavior_registry.get("gates", {}))
        except (OSError, ValueError) as e:
            problems.append(f"候选树外行为 registry 不可解析——{type(e).__name__}: {e}")
        else:
            if behavior_ids != actual_ids:
                problems.append(f"独立行为 witness 集与源码实际 gate 不闭合："
                                f"缺 {sorted(actual_ids - behavior_ids)}，"
                                f"多 {sorted(behavior_ids - actual_ids)}")
            if not os.path.isfile(BEHAVIOR_RUNNER):
                problems.append("缺候选树外 gate_behavior.py——静态自洽不得替代行为证据")
            else:
                # 每个行为 witness 自己的 validate 子进程已有 120s fail-closed
                # 上限；这里不再给整批另套墙钟总限。stage-binding 现在会分别跑
                # runner 与可信断言重放，整批耗时随 witness 数线性增长；外层总限
                # 还会把机器休眠计入，造成子项都在推进却被无 stdout 杀掉的假红。
                p = subprocess.run([sys.executable, BEHAVIOR_RUNNER, skill_dir, "--json"],
                                   capture_output=True, text=True)
                try:
                    behavior = json.loads(p.stdout)
                except (ValueError, TypeError):
                    problems.append("独立行为 witness 跑不出 JSON："
                                    f"rc={p.returncode} stderr={p.stderr[-300:]}")
                else:
                    if set(behavior.get("witness_ids", [])) != behavior_ids:
                        problems.append("行为 runner 实跑集合与外部 registry 漂移")
                    for gid, result in behavior.get("results", {}).items():
                        if result.get("problems"):
                            problems.append(f"{gid} 独立行为 witness 失败（正例须 PASS；"
                                            "定向负例须目标闸 FAIL + 指定理由）："
                                            + "；".join(result["problems"]))
                    if p.returncode != (0 if not behavior.get("problems") else 1):
                        problems.append(f"行为 runner 退出码与 problems 不一致：rc={p.returncode}")

    print(f"源码实际闸 {len(actual_ids)}（其中 audit 谓词族 {len(audit_dispatch)}）；"
          f"registry 闸 {len(registry_ids)}；"
          f"obligation {len(obligations)}；SKILL 引用 {len(cited_obs)}；"
          f"独立行为 witness {len(behavior_ids) if not static_only else 'SKIP'}")
    verdict = ("FAIL" if problems else
               "PARTIAL（未跑行为面，不构成候选验收）" if static_only else "PASS")
    print(f"总判定: {verdict}")
    for problem in problems:
        print("  ! " + problem)
    if problems:
        return 1
    return 3 if static_only else 0


if __name__ == "__main__":
    sys.exit(main())
