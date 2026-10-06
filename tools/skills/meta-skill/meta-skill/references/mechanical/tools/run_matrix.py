#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_matrix.py — 对全部 run 跑 T0/T1/T2 三层审核，出检出率矩阵。

用法: python3 run_matrix.py <runs_root> <mock_task1> <mock_task3> <out_json>
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, "self_check.py")

TASK3_RUNS = {"golden-task3", "E8-outsource-route-reversal"}


def run_tier(run_dir, tier, source=None):
    cmd = [sys.executable, SC, run_dir, "--tier", str(tier)]
    if source:
        cmd += ["--source", source]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        rep = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"verdict": "ERROR", "stderr": p.stderr[-500:]}
    return rep


def main():
    root, src1, src3, out_path = sys.argv[1:5]
    matrix = {}
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        src = src3 if name in TASK3_RUNS else src1
        row = {}
        for tier in (0, 1, 2):
            rep = run_tier(d, tier, source=src if tier == 2 else None)
            row[f"T{tier}"] = {
                "verdict": rep.get("verdict"),
                "n_fail": rep.get("n_fail"),
                "n_asserts": rep.get("n_asserts"),
                "first_failures": [f["assert"] for f in rep.get("failures", [])][:4],
            }
        matrix[name] = row
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=1)

    # 摘要表
    print(f"{'run':<32}{'T0现役':<10}{'T1账本':<10}{'T2源读':<10}")
    for name, row in matrix.items():
        cells = []
        for t in ("T0", "T1", "T2"):
            v = row[t]["verdict"]
            mark = "CATCH" if v == "FAIL" else ("pass" if v == "PASS" else "ERR")
            cells.append(f"{mark}({row[t]['n_fail']})")
        print(f"{name:<32}{cells[0]:<10}{cells[1]:<10}{cells[2]:<10}")
    print(f"\nmatrix written to {out_path}")


if __name__ == "__main__":
    main()
