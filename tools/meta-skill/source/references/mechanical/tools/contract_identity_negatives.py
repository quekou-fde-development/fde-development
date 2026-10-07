#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审核器契约身份键负例：重复/空 stage 与 assertion id 必须在运行前 rc2。"""
import copy
import json
import os
import subprocess
import sys
import tempfile

from gate_behavior import _cause_codes, _exact_cause

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
AUDIT = os.path.normpath(os.path.join(ROOT, "..", "v3.8-draft", "scripts", "audit.py"))
GOOD = os.path.join(ROOT, "gate-fixtures", "G0-good")
REGISTRY = os.path.join(ROOT, "gate_behavior_registry.json")


def run(contract_path):
    p = subprocess.run([
        sys.executable, AUDIT, os.path.join(GOOD, "fixtures", "golden"),
        "--contract", contract_path, "--all", "--json"
    ], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    base_path = os.path.join(GOOD, "assertions.json")
    base = json.load(open(base_path, encoding="utf-8"))
    problems = []

    rc, _out, err = run(base_path)
    ok = rc == 0
    print(f"identity-baseline       rc={rc}  {'[OK]' if ok else '[BAD]'}")
    if not ok:
        problems.append(f"未改契约须 rc0，实为 rc{rc}: {err[-300:]}")

    specs = json.load(open(REGISTRY, encoding="utf-8"))["gates"]["audit.run"]["cases"]
    cases = []
    for name, spec in specs.items():
        contract = copy.deepcopy(base)
        if name == "empty-stage":
            contract["stages"][0]["stage"] = ""
        elif name == "duplicate-stage":
            contract["stages"][1]["stage"] = contract["stages"][0]["stage"]
        elif name == "empty-id":
            contract["stages"][0]["operations"][0]["assertions"][0]["id"] = ""
        elif name == "duplicate-id":
            rows = contract["stages"][0]["operations"][0]["assertions"]
            rows[1]["id"] = rows[0]["id"]
        else:
            problems.append(f"registry 含未知身份负例 {name}")
            continue
        cases.append((name, contract, spec["reason"], spec["cause_group"]))

    with tempfile.TemporaryDirectory(prefix="contract_identity_") as td:
        for name, contract, reason, expected_cause in cases:
            path = os.path.join(td, name + ".json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(contract, f, ensure_ascii=False, indent=1)
            rc, out, err = run(path)
            diagnostic = out + err
            hit = reason in diagnostic
            cause_hit = _exact_cause(diagnostic, expected_cause)
            ok = rc == 2 and hit and cause_hit
            print(f"{name:<23} rc={rc}  理由={hit} 病因组={cause_hit}  "
                  f"{'[OK]' if ok else '[BAD]'}")
            if not ok:
                problems.append(f"{name}: 须 rc2、理由含「{reason}」且病因组精确为 "
                                f"{expected_cause}，实为 rc{rc}/"
                                f"{sorted(_cause_codes(diagnostic))}: {diagnostic[-300:]}")

    print(f"总判定: {'PASS' if not problems else 'FAIL'}")
    for problem in problems:
        print("  ! " + problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
