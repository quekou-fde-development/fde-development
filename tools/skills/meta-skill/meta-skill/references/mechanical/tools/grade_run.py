#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grade_run.py — Part 2 盲跑评分器（B 包账本自动评；A 包无账本，人工从回复文本评后手填 json 再跑本器）。

用法: python3 grade_run.py <golden.json> <s8_summary.json 或同构 json>
比对七桶集合 + N。输出逐桶 diff。
"""
import json
import sys

BUCKETS = ["生产异常", "质检异常", "物流异常", "属性异常", "无工单", "状态待判", "正常"]


def main():
    golden_path, run_path = sys.argv[1:3]
    with open(golden_path, encoding="utf-8") as f:
        g = json.load(f)
    with open(run_path, encoding="utf-8") as f:
        r = json.load(f)
    ok = True
    n_r = r.get("N_claimed", r.get("N"))
    if n_r != g["N"]:
        print(f"N: FAIL run={n_r} golden={g['N']}")
        ok = False
    else:
        print(f"N: ok ({g['N']})")
    for b in BUCKETS:
        gs = set(g["lists"][b])
        rs = set(r["lists"].get(b) or [])
        if gs == rs:
            print(f"{b}: ok ({len(gs)})")
        else:
            ok = False
            print(f"{b}: FAIL 缺{sorted(gs - rs)} 多{sorted(rs - gs)}")
    print("VERDICT:", "MATCH" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
