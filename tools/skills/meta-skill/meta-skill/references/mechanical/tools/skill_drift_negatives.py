#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_drift_negatives.py — 五面漂移检查器自身的负例门。

`skill_drift.py` 是本轮新加的闸，闸自己没被证伪过就不构成检验（与
`contract_ir §9` 对审核器的要求同构，只是上移一层：被审对象是漂移检本身）。
每个负例只坏一处，判据是**被坏的那一处对应的那条理由报出来**，不是「跑出了
FAIL」——错的理由抓错的错等于没抓。

十八种坏法各挡一面：

  * `gate-cites-void`   闸声明一个 IR 里不存在的节 → 「闸指向空处」。
  * `skill-drops-cite`  SKILL.md 删掉某条判据源的引用 → 「规格书没承接它」。
                        这正是 v3.8 第二轮真实发生过的形态。
  * `skill-dead-ptr`    SKILL.md 指向 IR 里不存在的节 → 「死指针」。
  * `bare-section`      闸把判据源写成裸 `§n` → 声明面看着写了、链条上没挂。
                        本器实现期真栽过这一条。
  * `gate-drops-cites`  实际闸删除全部判据源声明 → 实际闸仍须被机械发现并拒。
  * `skill-unenforced`  SKILL 新增强制 requirement，却无 registry obligation / 闸。
  * `gate-body-stub`    闸的 id / obligation / 判据源全留，函数体改成恒 PASS 空壳。
  * `gate-unhooked`     闸函数与 registry 全留，但上层不再调用它。
  * `gate-dead-hook`    只把调用塞进 `if False`，源码有字样但入口不可达。
  * `helper-drift`      gate 自身不动，只改它可达 helper，传递实现指纹须报警。
  * `gate-resigned-stub` 在 gate 活体首行 return，再用同一 `body_hash()` 重签
                        candidate registry；静态登记面自洽，候选树外行为 witness 须拒。
  * `audit-family-unregistered` 往 FAMILIES 加一个新入口；结构发现须自动纳入实际闸。
  * `predicate-resigned-four` 四个低覆盖谓词族同时恒真并同源重签；逐族行为面须拒。
  * `audit-cause-collapse` 四个契约身份病因塌成一条超集消息并同源重签；精确病因组须拒。
  * `all-gate-cause-collapse` M7-M10 每闸全部诊断塌成同一条超集 cause code，
                              保留 FAIL/理由并同源重签；须拒。
  * `intra-cause-collapse` 同一 cause code 内的可分诊断继续塌缩，保持单码与 reason；
                           cause block diversity 基线须拒。
  * `diagnostic-content-collapse` 保持同码组块数与块间差异，只掏空逐 fixture 的结构
                                  事实；广义 diagnostic binding 须拒。
  * `m7-diagnostic-collapse` M7 保留 FAIL/理由、删掉行号与命令原文并同源重签；须拒。

另跑一条一字未改的正例对照：恒红的负例门与恒绿的断言是同一个病。

用法: python3 skill_drift_negatives.py [<skill_dir>]
退出码 0 = 完整正例 + 静态 PARTIAL 对照 + 十八负例全合格；1 = 有不合格项；2 = 用法错。
"""
import importlib.util
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DRIFT = os.path.join(HERE, "skill_drift.py")
PIPE_WRAPPER = os.path.join(HERE, "skill_drift_tail.sh")
GATE_MATRIX = os.path.join(HERE, "gate_matrix.py")
DEFAULT_SKILL = os.path.normpath(os.path.join(ROOT, "..", "v3.8-draft"))

_SPEC = importlib.util.spec_from_file_location("skill_drift_module", DRIFT)
_DRIFT_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_DRIFT_MODULE)


def _resign_all(d):
    """模拟主动攻击者：调用被测器自己的 body_hash 重签全部 candidate gate。"""
    reg_path = os.path.join(d, "references", "obligation_registry.json")
    registry = json.load(open(reg_path, encoding="utf-8"))
    parsed = {}
    for spec in registry["gates"].values():
        path = os.path.join(d, spec["file"])
        if path not in parsed:
            parsed[path] = _DRIFT_MODULE.parse_functions(path)
        tree, funcs = parsed[path]
        spec["implementation_sha256"] = _DRIFT_MODULE.body_hash(
            tree, funcs[spec["function"]])
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def n_gate_cites_void(d):
    """闸声明一个 IR 里没有的节。挑 §6.2 改成 §99——§99 不存在。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    s2 = s.replace("判据源 `contract_ir.md §6.2`", "判据源 `contract_ir.md §99`", 1)
    assert s2 != s, "锚点没命中——基线变了，负例失去附着点"
    open(p, "w", encoding="utf-8").write(s2)


def n_skill_drops_cite(d):
    """SKILL.md 不再引用 §6.2（M8 段入口绑定）。闸照判，规格书装不知道。

    这里替换**全部**出现处而不是第一处：§6.2 在 SKILL.md 里被引了两次
    （6A 正文一次、M8 闸表一次），只删一处时引用集不变，漂移检照样绿，
    负例于是恒不成立而看起来像是「检查器漏了」。「删掉这条引用」这个动作
    的单位是引用本身，不是它的某一次出现。
    """
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s2 = re.sub(r"`(?:references/)?contract_ir\.md §6\.2`", "上文", s)
    assert s2 != s, "锚点没命中——基线变了，负例失去附着点"
    open(p, "w", encoding="utf-8").write(s2)


def n_skill_dead_ptr(d):
    """SKILL.md 指一个 IR 里不存在的节。"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s2 = re.sub(r"(`(?:references/)?contract_ir\.md §)6\.1(`)", r"\g<1>6.7\2", s, count=1)
    assert s2 != s, "锚点没命中——基线变了，负例失去附着点"
    open(p, "w", encoding="utf-8").write(s2)


def n_bare_section(d):
    """闸把判据源写成裸 §n：严格前缀判据会静静漏掉它。"""
    p = os.path.join(d, "scripts", "audit.py")
    s = open(p, encoding="utf-8").read()
    s2 = s.replace("`contract_ir.md §8.0`", "`§8.0`", 1)
    assert s2 != s, "锚点没命中——基线变了，负例失去附着点"
    open(p, "w", encoding="utf-8").write(s2)


def n_gate_drops_all_cites(d):
    """删掉 _check_stage_binding 的全部判据源声明，函数本体仍在。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    s2 = s.replace("    判据源 `contract_ir.md §6.2`。本函数不内联复制该节语义，只做机械比对；\n"
                   "    §6.2 与本实现的同步由 `skill_drift.py` 的第四面锁住。\n",
                   "    判据源声明已删除。\n", 1)
    assert s2 != s, "锚点没命中——基线变了，负例失去附着点"
    open(p, "w", encoding="utf-8").write(s2)


def n_skill_adds_unenforced(d):
    """SKILL 新增强制 requirement 与 OBL id，registry 没有它。"""
    p = os.path.join(d, "SKILL.md")
    s = open(p, encoding="utf-8").read()
    s += "\n新增强制要求：每段再写一份副本（`contract_ir.md §10.1` [OBL:UNENFORCED.TEST]）。\n"
    open(p, "w", encoding="utf-8").write(s)


def n_gate_body_stub(d):
    """保留 M7 全部声明，用后定义覆盖成恒 PASS 空壳。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    marker = "\ndef main():\n"
    stub = '''
def check_m7(text, persistent=False):
    """Gate-ID: validate.M7
    Obligations: STAGE.DECLARATION
    判据源 `contract_ir.md §6.3`。
    """
    return True, "M7 PASS: 恒绿空壳"

'''
    assert marker in s, "main 锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(marker, "\n" + stub + "def main():\n", 1))


def n_gate_unhooked(d):
    """保留 stage-binding 函数与 registry，解除 check_m8 对它的调用。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    old = ("        _check_stage_binding(scripts_dir, exec_names, assertions, "
           "contract_path, errs)\n")
    assert old in s, "调用锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(old, "        pass  # gate unhooked\n", 1))


def n_gate_dead_hook(d):
    """解除真实调用，只在常量假分支保留同名调用诱饵。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    old = ("        _check_stage_binding(scripts_dir, exec_names, assertions, "
           "contract_path, errs)\n")
    decoy = ("        if False:\n"
             "            _check_stage_binding(scripts_dir, exec_names, assertions, "
             "contract_path, errs)\n")
    assert old in s, "调用锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(old, decoy, 1))


def n_helper_drift(d):
    """只改 M7 可达 helper；gate 函数正文与声明均不动。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    old = '    return None if not m else m.group(1).strip()\n'
    new = '    return None if not m else "helper-drift"\n'
    assert old in s, "helper 锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))


def n_gate_resigned_stub(d):
    """掏空 stage-binding 活体，再用被测漂移器同源 body_hash 重签 registry。"""
    p = os.path.join(d, "scripts", "validate.py")
    lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
    tree, funcs = _DRIFT_MODULE.parse_functions(p)
    fn = funcs["_check_stage_binding"]
    doc = fn.body[0]
    assert isinstance(doc, _DRIFT_MODULE.ast.Expr), "stage-binding docstring 锚点失效"
    lines.insert(doc.end_lineno, "    return []  # forged live stub; old body remains dead\n")
    open(p, "w", encoding="utf-8").writelines(lines)

    tree, funcs = _DRIFT_MODULE.parse_functions(p)
    forged_hash = _DRIFT_MODULE.body_hash(tree, funcs["_check_stage_binding"])
    reg_path = os.path.join(d, "references", "obligation_registry.json")
    registry = json.load(open(reg_path, encoding="utf-8"))
    registry["gates"]["validate.M8.stage_binding"]["implementation_sha256"] = forged_hash
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def n_audit_family_unregistered(d):
    """FAMILIES 增加源码入口；不得靠 audit 函数名白名单漏掉。"""
    p = os.path.join(d, "scripts", "audit.py")
    s = open(p, encoding="utf-8").read()
    marker = "\nFAMILIES = {\n"
    injected = '''
def f_injected_family(art, spec, ctx):
    """结构发现探针。

    Gate-ID: audit.family.injected
    Obligations: AUDIT.FAMILY.FALSIFIABILITY
    判据源：`contract_ir.md §9`。
    """
    return False, "injected"

FAMILIES = {
    "injected": f_injected_family,
'''
    assert marker in s, "FAMILIES 锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(marker, "\n" + injected, 1))


def n_predicate_families_resigned(d):
    """四个低覆盖 family 同时恒真，再用同源 body_hash 重签 candidate registry。"""
    names = ["f_field_function_replay", "f_existence", "f_nonzero_rows", "f_file_present"]
    p = os.path.join(d, "scripts", "audit.py")
    lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
    _tree, funcs = _DRIFT_MODULE.parse_functions(p)
    for name in sorted(names, key=lambda x: funcs[x].lineno, reverse=True):
        fn = funcs[name]
        doc = fn.body[0]
        assert isinstance(doc, _DRIFT_MODULE.ast.Expr), f"{name} docstring 锚点失效"
        lines.insert(doc.end_lineno, "    return True, 'forged'  # old body remains dead\n")
    open(p, "w", encoding="utf-8").writelines(lines)

    tree, funcs = _DRIFT_MODULE.parse_functions(p)
    reg_path = os.path.join(d, "references", "obligation_registry.json")
    registry = json.load(open(reg_path, encoding="utf-8"))
    for name in names:
        family = name.removeprefix("f_")
        registry["gates"][f"audit.family.{family}"]["implementation_sha256"] = \
            _DRIFT_MODULE.body_hash(tree, funcs[name])
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def n_audit_cause_collapse(d):
    """四个身份病因仍全拒绝，但诊断统一塞入全部 cause code。"""
    p = os.path.join(d, "scripts", "audit.py")
    s = open(p, encoding="utf-8").read()
    causes = [f"[CAUSE:AUDIT.CONTRACT.{name}]" for name in
              ("STAGE_NAME_EMPTY", "STAGE_NAME_DUPLICATE",
               "ASSERTION_ID_EMPTY", "ASSERTION_ID_DUPLICATE")]
    assert all(cause in s for cause in causes), "audit 身份病因码缺失，负例不能附着"
    # Mutate only the diagnostic tags; retain new empty-contract and stage guards.
    pattern = "|".join(re.escape(cause) for cause in causes)
    changed = re.sub(pattern, lambda _: "".join(causes), s)
    open(p, "w", encoding="utf-8").write(changed)
    _resign_all(d)


def n_all_gate_cause_collapse(d):
    """M7-M10 仍逐件拒绝且保留理由，但每个失败块都发射全域 cause 超集。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    registry = json.load(open(os.path.join(ROOT, "gate_behavior_registry.json"),
                              encoding="utf-8"))
    codes = sorted({code for suite in registry["directed_causes"].values()
                    for code in suite.values() if not code.startswith("M11.")})
    superset = "][CAUSE:".join(codes)
    anchor = '    clean = [CAUSE_TAG_RE.sub("", str(error)).strip() for error in errors]\n'
    injected = (anchor + '    if gate in {"M7", "M8", "M9", "M10"}:\n'
                f'        return "{superset}", clean\n')
    assert anchor in s, "统一 cause 发射点锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(anchor, injected, 1))
    _resign_all(d)


def n_intra_cause_collapse(d):
    """DISPATCH_UNBOUND 组三个 fixture 保持同码/FAIL/reason，整体压成一块。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    anchor = '    blob = "\\n".join(clean)\n'
    injected = (anchor + '    if gate == "M8" and "两旗标齐" in blob:\n'
                '        return "M8.STAGE_BINDING.DISPATCH_UNBOUND", ["无执行入口"]\n')
    assert anchor in s, "统一诊断发射点锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(anchor, injected, 1))
    _resign_all(d)


def n_diagnostic_content_collapse(d):
    """八个可分多成员组均保住块数/分区，只删除逐 fixture 结构事实。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    anchor = '    blob = "\\n".join(clean)\n'
    injected = (anchor +
                '    if gate == "M7" and "编号步缺槽" in blob:\n'
                '        variant = "A" if "L17" in blob else "B"\n'
                '        return "M7.NUMBERED_STEP.MISSING_SLOT", [f"编号步缺槽（{variant}）"]\n'
                '    if gate == "M8" and "两旗标齐" in blob:\n'
                '        variant = "A" if blob.count("无执行入口") > 1 else "B"\n'
                '        return "M8.STAGE_BINDING.DISPATCH_UNBOUND", [f"无执行入口（{variant}）"]\n'
                '    if gate == "M8" and "不可达真实写盘" in blob:\n'
                '        variant = ("A" if "死函数诱饵" in blob else '
                '"B" if "绑定常量假分支" in blob else '
                '"C" if "一元取反假分支" in blob else '
                '"D" if "逻辑短路假分支" in blob else '
                '"E" if "常量假分支" in blob else "F")\n'
                '        return "M8.STAGE_BINDING.UNREACHABLE_ARTIFACT_WRITE", [f"不可达真实写盘（{variant}）"]\n'
                '    if gate == "M8" and "隔离真跑未产出" in blob:\n'
                '        variant = ("A" if "kind=assertion_error" in blob else '
                '"B" if "kind=sandbox_file_write_denied" in blob else '
                '"C" if "kind=sandbox_network_denied" in blob else '
                '"D" if "kind=sandbox_signal_denied" in blob else '
                '"E" if "kind=sandbox_fork_denied" in blob else "F")\n'
                '        return "M8.STAGE_BINDING.RUNTIME_PROBE_FAILED", [f"隔离真跑未产出（{variant}）"]\n'
                '    if gate == "M9" and "golden 与 mutant 载荷指纹相同" in blob:\n'
                '        variant = "A" if "e0b91e8f365a1817" in blob else "B"\n'
                '        return "M9.CUSTOM.PAYLOAD_COLLISION", '
                '[f"golden 与 mutant 载荷指纹相同（{variant}）"]\n'
                '    if gate == "M9" and "最低强断言族缺" in blob:\n'
                '        variant = "A" if "predicate_replay" in blob else "B"\n'
                '        return "M9.FAMILY.MINIMUM_MISSING", [f"最低强断言族缺（{variant}）"]\n'
                '    if gate == "M9" and "family↔tier 不符" in blob:\n'
                '        variant = "A" if "source_readback" in blob else "B"\n'
                '        return "M9.FAMILY_TIER.MISMATCH", [f"family↔tier 不符（{variant}）"]\n'
                '    if gate == "M9" and "source_anchor" in blob and "没有标题" in blob:\n'
                '        variant = "A" if "从来没有这一节" in blob else "B"\n'
                '        return "M9.CUSTOM.SOURCE_HEADING_MISSING", [f"没有标题（{variant}）"]\n')
    assert anchor in s, "统一诊断发射点锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(anchor, injected, 1))
    _resign_all(d)


def n_m7_diagnostic_collapse(d):
    """M7 仍逐件 FAIL 且理由不变，但删掉定位行号与原始命令。"""
    p = os.path.join(d, "scripts", "validate.py")
    s = open(p, encoding="utf-8").read()
    old = '''    for lineno, command in unmarked:
        errs.append(f"L{lineno} 围栏外行内可执行命令未落四槽: `{command}`")
'''
    new = '''    if unmarked:
        errs.append("围栏外行内可执行命令未落四槽")
'''
    assert old in s, "M7 诊断块锚点没命中——基线变了"
    open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    _resign_all(d)


NEGATIVES = [
    ("gate-cites-void", n_gate_cites_void, "判据源漂移"),
    ("skill-drops-cite", n_skill_drops_cite, "规格书没承接它"),
    ("skill-dead-ptr", n_skill_dead_ptr, "死指针"),
    ("bare-section", n_bare_section, "docstring 有裸 §8.0"),
    ("gate-drops-cites", n_gate_drops_all_cites, "该闸未声明判据源"),
    ("skill-unenforced", n_skill_adds_unenforced, "无闸执行"),
    ("gate-body-stub", n_gate_body_stub, "闸函数体为空壳"),
    ("gate-unhooked", n_gate_unhooked, "闸函数未接入调用链"),
    ("gate-dead-hook", n_gate_dead_hook, "闸函数未接入调用链"),
    ("helper-drift", n_helper_drift, "实现体指纹漂移"),
    ("gate-resigned-stub", n_gate_resigned_stub,
     "validate.M8.stage_binding 独立行为 witness 失败", True),
    ("audit-family-unregistered", n_audit_family_unregistered,
     "实际闸 audit.family.injected 未进入 obligation registry"),
    ("predicate-resigned-four", n_predicate_families_resigned,
     "audit.family.field_function_replay 独立行为 witness 失败", True),
    ("audit-cause-collapse", n_audit_cause_collapse,
     "audit.run 独立行为 witness 失败", True),
    ("all-gate-cause-collapse", n_all_gate_cause_collapse,
     "validate.M7 独立行为 witness 失败", True, "病因组须精确为"),
    ("intra-cause-collapse", n_intra_cause_collapse,
     "M8|M8.STAGE_BINDING.DISPATCH_UNBOUND 组内诊断块数须为 2", True,
     "组内诊断块数须为 2"),
    ("diagnostic-content-collapse", n_diagnostic_content_collapse,
     "结构诊断绑定须精确为", True, "结构诊断绑定须精确为"),
    ("m7-diagnostic-collapse", n_m7_diagnostic_collapse,
     "validate.M7 独立行为 witness 失败", True, "结构诊断绑定须精确为"),
]


def drift(d, static_only=False):
    cmd = [sys.executable, DRIFT, d]
    if static_only:
        cmd.append("--static-only")
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill_dir', nargs='?', default=DEFAULT_SKILL)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 4:
        parser.error('--jobs must be between 1 and 4')
    skill_dir = args.skill_dir
    if not os.path.isdir(skill_dir):
        print(f"用法错：{skill_dir} 不是文件夹——一条都没比对过。")
        return 2

    problems = []

    rc, out = drift(skill_dir)
    ok0 = rc == 0
    print(f"{'sd-baseline':<18} rc={rc}  {'[OK]' if ok0 else '[BAD]'}")
    if not ok0:
        problems.append(f"sd-baseline: 未改动的五面本该一致，实为 rc={rc}\n{out}")

    rc, out = drift(skill_dir, static_only=True)
    partial_ok = rc == 3 and "PARTIAL（未跑行为面" in out and "总判定: PASS" not in out
    print(f"{'static-partial':<18} rc={rc}  {'[OK]' if partial_ok else '[BAD]'}")
    if not partial_ok:
        problems.append(f"static-partial: 静态隔离须 rc3 + PARTIAL 且不得输出 PASS，实为 rc={rc}\n{out}")

    def run_negative(case):
        # Each case owns a distinct temporary package; preserve every original
        # drift, pipefail, and matrix check while running independent cases together.
        problems, lines = [], []
        def record(value): lines.append(value)
        name, fn, want_sub = case[:3]
        full_behavior = bool(case[3]) if len(case) > 3 else False
        matrix_sub = case[4] if len(case) > 4 else None
        tmp = tempfile.mkdtemp(prefix="sd_neg_")
        d = os.path.join(tmp, "pkg")
        shutil.copytree(skill_dir, d)
        try:
            fn(d)
        except AssertionError as e:
            record(f"{name:<18} [BAD] {e}")
            problems.append(f"{name}: {e}")
            shutil.rmtree(tmp, ignore_errors=True)
            return problems, lines
        rc, out = drift(d, static_only=not full_behavior)
        hit = want_sub in out
        ok = rc == 1 and hit
        record(f"{name:<18} rc={rc}  理由含「{want_sub}」={hit}  "
              f"{'[OK]' if ok else '[BAD]'}")
        if not ok:
            if rc != 1:
                problems.append(f"{name}: 退出码须 1，实为 {rc}")
            if not hit:
                problems.append(f"{name}: 理由未含「{want_sub}」，实际输出:\n{out}")
        if full_behavior:
            piped = subprocess.run(["bash", PIPE_WRAPPER, d], capture_output=True, text=True)
            pipe_hit = want_sub in piped.stdout
            pipe_ok = piped.returncode == 1 and pipe_hit
            pipe_name = name + "-pipe"
            record(f"{pipe_name:<18} rc={piped.returncode}  "
                  f"理由含「{want_sub}」={pipe_hit}  {'[OK]' if pipe_ok else '[BAD]'}")
            if not pipe_ok:
                problems.append(f"{pipe_name}: 内置 pipefail 尾部入口未保留 rc=1 "
                                f"或理由，实为 rc={piped.returncode}\n{piped.stdout}")
        if matrix_sub:
            matrix_out = os.path.join(tmp, "gate_matrix.json")
            matrix = subprocess.run([
                sys.executable, GATE_MATRIX,
                os.path.join(ROOT, "gate-fixtures"),
                os.path.join(ROOT, "custom-fixtures"),
                os.path.join(d, "scripts", "validate.py"), matrix_out,
            ], capture_output=True, text=True)
            matrix_hit = matrix_sub in (matrix.stdout + matrix.stderr)
            matrix_ok = matrix.returncode == 1 and matrix_hit
            record(f"{name + '-matrix':<18} rc={matrix.returncode}  "
                  f"理由含「{matrix_sub}」={matrix_hit} "
                  f"{'[OK]' if matrix_ok else '[BAD]'}")
            if not matrix_ok:
                problems.append(f"{name}-matrix: gate_matrix 须 rc1 且命中指定绑定理由，"
                                f"实为 rc={matrix.returncode}\n{matrix.stdout}\n{matrix.stderr}")
        shutil.rmtree(tmp, ignore_errors=True)

        return problems, lines

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_negative, case): case[0] for case in NEGATIVES}
        for future in as_completed(futures):
            name = futures[future]
            try:
                errors, lines = future.result()
            except Exception as error:
                problems.append(f'{name}: execution error {type(error).__name__}: {error}')
                print(f'{name}: [BAD] {error}', flush=True)
            else:
                print('\n'.join(lines), flush=True)
                problems.extend(errors)

    print(f"\n正例 1 + 定向负例 {len(NEGATIVES)}；每条均核指定理由")
    print(f"总判定: {'PASS' if not problems else 'FAIL'}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
