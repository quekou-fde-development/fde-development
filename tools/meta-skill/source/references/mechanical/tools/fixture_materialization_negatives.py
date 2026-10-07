#!/usr/bin/env python3
"""证明 fixture registry / generator manifest / 盘上实物三面闭合。

正例用现有 gate-fixtures；负例只从临时复制体删除一条已登记 fixture。判据是
gate_matrix 必须 rc=1 且指名实物集合缺该 id。目录缺一条仍报 PASS，说明矩阵只
统计“眼前还有什么”，没有验证“本应有什么”。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
MATRIX = os.path.join(HERE, "gate_matrix.py")
VALIDATE = os.path.normpath(os.path.join(ROOT, "..", "v3.8-draft", "scripts",
                                         "validate.py"))
BASE = os.path.join(ROOT, "gate-fixtures")
VICTIM = "G22-numbered-prefix-inline-command"


def run(root, out):
    return subprocess.run([sys.executable, MATRIX, root, VALIDATE, out],
                          capture_output=True, text=True)


def main():
    problems = []
    with tempfile.TemporaryDirectory(prefix="fixture_materialization_") as td:
        p0 = run(BASE, os.path.join(td, "baseline.json"))
        ok0 = p0.returncode == 0
        print(f"materialization-baseline rc={p0.returncode}  {'[OK]' if ok0 else '[BAD]'}")
        if not ok0:
            problems.append("未改动 gate-fixtures 正例控制未通过")

        mutant = os.path.join(td, "gate-fixtures")
        shutil.copytree(BASE, mutant)
        shutil.rmtree(os.path.join(mutant, VICTIM))
        p1 = run(mutant, os.path.join(td, "missing.json"))
        reason = "fixture 实物集合不闭合" in p1.stdout and VICTIM in p1.stdout
        ok1 = p1.returncode == 1 and reason
        print(f"materialization-missing  rc={p1.returncode}  理由指名={reason}  "
              f"{'[OK]' if ok1 else '[BAD]'}")
        if not ok1:
            problems.append("删除已登记 fixture 后未由实物闭包指名拒绝")

    print("正例 1 + 定向负例 1；负例核退出码与指定缺件理由")
    print(f"总判定: {'PASS' if not problems else 'FAIL'}")
    for p in problems:
        print("  ! " + p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
