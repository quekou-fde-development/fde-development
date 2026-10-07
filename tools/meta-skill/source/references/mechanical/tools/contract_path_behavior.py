#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验 `validate.py --contract` 的唯一发现、schema 边界与诊断分层。"""

import json
import os
import shutil
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOOD = os.path.join(ROOT, "gate-fixtures", "G0-good")
VALIDATE = os.path.normpath(
    os.path.join(ROOT, "..", "v3.8-draft", "scripts", "validate.py"))


def run(pkg, *args):
    return subprocess.run(
        [sys.executable, VALIDATE, pkg, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")


def copy_good(root, name):
    pkg = os.path.join(root, name)
    shutil.copytree(GOOD, pkg)
    return pkg


def move_contract(pkg, name="meta_contract.json"):
    dst = os.path.join(pkg, "fixtures", name)
    shutil.move(os.path.join(pkg, "assertions.json"), dst)
    return dst


def require(case, proc, rc, includes=(), excludes=()):
    problems = []
    if proc.returncode != rc:
        problems.append(f"rc={proc.returncode}，期望 {rc}")
    for needle in includes:
        if needle not in proc.stdout:
            problems.append(f"缺输出 {needle!r}")
    for needle in excludes:
        if needle in proc.stdout:
            problems.append(f"不应出现 {needle!r}")
    if problems:
        print(f"FAIL {case}: {'；'.join(problems)}")
        print(proc.stdout[-5000:])
        if proc.stderr:
            print(proc.stderr[-1000:], file=sys.stderr)
        return False
    print(f"PASS {case}: rc={proc.returncode}")
    return True


def main():
    if not os.path.isdir(GOOD):
        print(f"缺正例 fixture: {GOOD}", file=sys.stderr)
        return 2
    checks = []
    with tempfile.TemporaryDirectory(prefix="contract_path_") as tmp:
        pkg = copy_good(tmp, "external-good")
        move_contract(pkg)
        p = run(pkg, "--persistent", "--contract", "fixtures/meta_contract.json")
        checks.append(require(
            "显式包内 canonical contract 可通过", p, 0,
            includes=("contract=fixtures/meta_contract.json", "M9 PASS", "M10 PASS")))

        pkg = copy_good(tmp, "explicit-wins")
        move_contract(pkg)
        with open(os.path.join(pkg, "assertions.json"), "w", encoding="utf-8") as f:
            json.dump({"_about": "native regression", "assertions": []}, f)
        p = run(pkg, "--persistent", "--contract=fixtures/meta_contract.json")
        checks.append(require(
            "显式契约优先于包根同名原生回归件", p, 0,
            includes=("contract=fixtures/meta_contract.json",)))

        pkg = copy_good(tmp, "missing-default")
        move_contract(pkg)
        p = run(pkg, "--persistent")
        checks.append(require(
            "未显式指定时不隐式搜索 fixtures", p, 1,
            includes=("M8 FAIL:", "缺 assertions.json（默认 canonical contract 不存在）",
                      "M9 NOT_RUN (FAIL-CLOSED)", "M10 NOT_RUN (FAIL-CLOSED)"),
            excludes=("M9 FAIL:", "M10 FAIL:")))

        pkg = copy_good(tmp, "native-flat")
        move_contract(pkg, "canonical.json")
        flat = os.path.join(pkg, "fixtures", "assertions.json")
        with open(flat, "w", encoding="utf-8") as f:
            json.dump({"_about": "native regression", "assertions": [
                {"id": "A01", "op": "file_exists", "pred": "eq"}]}, f)
        p = run(pkg, "--persistent", "--contract", "fixtures/assertions.json")
        checks.append(require(
            "原生扁平回归件不可冒充 canonical contract", p, 1,
            includes=("契约形状不兼容", "M9 NOT_RUN (FAIL-CLOSED)",
                      "M10 NOT_RUN (FAIL-CLOSED)"),
            excludes=("M9 PASS", "M10 PASS")))

        pkg = copy_good(tmp, "semantic-bad")
        path = move_contract(pkg)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["stages"][0]["operations"][0]["assertions"].pop(0)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        p = run(pkg, "--persistent", "--contract", "fixtures/meta_contract.json")
        checks.append(require(
            "canonical 契约已读后语义缺口归 M9 FAIL", p, 1,
            includes=("M9 FAIL:", "最低强断言族缺"),
            excludes=("M9 NOT_RUN (FAIL-CLOSED)",)))

        pkg = copy_good(tmp, "outside")
        outside = os.path.join(tmp, "outside.json")
        shutil.copy2(os.path.join(pkg, "assertions.json"), outside)
        os.remove(os.path.join(pkg, "assertions.json"))
        p = run(pkg, "--persistent", "--contract", outside)
        checks.append(require(
            "契约路径不得逃出包根", p, 1,
            includes=("解析后逃出包根", "M9 NOT_RUN (FAIL-CLOSED)",
                      "M10 NOT_RUN (FAIL-CLOSED)")))

    ok = all(checks)
    print(f"总判定: {'PASS' if ok else 'FAIL'} ({sum(checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
