#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证明指定理由只认目标 M 闸自己的 detail 块，不认输入或别闸回显。"""
from gate_behavior import _cause_codes, _exact_cause, _gate_block


CASES = [
    ("target-hit", "M10 FAIL:\n        UNVERIFIED 正例不得成立\nM11 PASS: ok",
     "M10", "UNVERIFIED", True),
    ("other-gate-echo", "M10 FAIL:\n        指名断言未拒绝\nM11 FAIL: UNVERIFIED",
     "M10", "UNVERIFIED", False),
    ("input-echo-before-target", "fixture payload: TODO\nM11 FAIL:\n        模板占位残留",
     "M11", "TODO", False),
]

CAUSE_CASES = [
    ("cause-exact", "[CAUSE:M8.STAGE_BINDING.MISSING_STAGE_FLAG] detail",
     "M8.STAGE_BINDING.MISSING_STAGE_FLAG", True),
    ("cause-wrong", "[CAUSE:M8.STAGE_BINDING.DISPATCH_UNBOUND] detail",
     "M8.STAGE_BINDING.MISSING_STAGE_FLAG", False),
    ("cause-super-set",
     "[CAUSE:M8.STAGE_BINDING.MISSING_STAGE_FLAG]"
     "[CAUSE:M8.STAGE_BINDING.DISPATCH_UNBOUND] detail",
     "M8.STAGE_BINDING.MISSING_STAGE_FLAG", False),
    ("cause-generic-only", "无执行入口",
     "M8.STAGE_BINDING.MISSING_STAGE_FLAG", False),
]


def main():
    problems = []
    for name, stdout, gate, reason, expected in CASES:
        got = reason in _gate_block(stdout, gate)
        ok = got == expected
        print(f"{name:<24} expected={expected} got={got} {'[OK]' if ok else '[BAD]'}")
        if not ok:
            problems.append(f"{name}: expected {expected}, got {got}")
    for name, diagnostic, cause, expected in CAUSE_CASES:
        got = _exact_cause(diagnostic, cause)
        ok = got == expected
        print(f"{name:<24} expected={expected} got={got} "
              f"codes={sorted(_cause_codes(diagnostic))} {'[OK]' if ok else '[BAD]'}")
        if not ok:
            problems.append(f"{name}: expected {expected}, got {got}")
    print(f"总判定: {'PASS' if not problems else 'FAIL'}")
    for problem in problems:
        print("  ! " + problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
