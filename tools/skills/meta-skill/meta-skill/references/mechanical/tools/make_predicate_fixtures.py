#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成四个此前零引用 audit family 的独立正例与定向负例。"""
import copy
import json
import os
import shutil
import sys


CONTRACT = {
    "contract_ir_version": "1.0",
    "stages": [{
        "stage": "predicate_probe",
        "operations": [{
            "op": "map",
            "artifact": "artifact.json",
            "source_reachability": "machine",
            "assertions": [
                {
                    "id": "predicate.field_function_replay",
                    "family": "field_function_replay",
                    "tier": 1,
                    "predicate": {
                        "collection": "mapped", "id_field": "id",
                        "source_field": "source", "target_field": "target",
                        "mapping": {"A": "Alpha"}, "default": "Unknown"
                    },
                    "derived_fields": [], "source_anchor": "predicate family witness",
                    "mutants": ["PF1-field-function-forged"]
                },
                {
                    "id": "predicate.existence", "family": "existence", "tier": 1,
                    "predicate": {"path": "present_value"}, "derived_fields": [],
                    "source_anchor": "predicate family witness",
                    "mutants": ["PF2-existence-missing"]
                },
                {
                    "id": "predicate.nonzero_rows", "family": "nonzero_rows", "tier": 1,
                    "predicate": {"collection": "rows"}, "derived_fields": [],
                    "source_anchor": "predicate family witness",
                    "mutants": ["PF3-zero-rows"]
                },
                {
                    "id": "predicate.file_present", "family": "file_present", "tier": 1,
                    "predicate": {"path": "present.txt"}, "derived_fields": [],
                    "source_anchor": "predicate family witness",
                    "mutants": ["PF4-file-missing"]
                }
            ]
        }]
    }]
}

BASE = {
    "mapped": [{"id": "r1", "source": "A", "target": "Alpha"}],
    "rows": [{"id": "r1"}],
    "present_value": "ok"
}

MUTANTS = {
    "PF1-field-function-forged": (
        "predicate.field_function_replay", "记FORGED/应Alpha",
        lambda art: art["mapped"][0].__setitem__("target", "FORGED")),
    "PF2-existence-missing": (
        "predicate.existence", "present_value 不存在",
        lambda art: art.pop("present_value")),
    "PF3-zero-rows": (
        "predicate.nonzero_rows", "rows 空集",
        lambda art: art.__setitem__("rows", [])),
    "PF4-file-missing": (
        "predicate.file_present", "present.txt 不在 run_dir 内", lambda art: None),
}


def _json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def expected():
    files = {"assertions.json": _json_bytes(CONTRACT)}
    files["golden/artifact.json"] = _json_bytes(BASE)
    files["golden/present.txt"] = b"present\n"
    for name, (target, reason, mutate) in MUTANTS.items():
        art = copy.deepcopy(BASE)
        mutate(art)
        files[f"{name}/artifact.json"] = _json_bytes(art)
        files[f"{name}/INJECTION.json"] = _json_bytes({
            "fixture_id": name, "must_be_rejected_by": target,
            "must_include_reason": reason
        })
        if name != "PF4-file-missing":
            files[f"{name}/present.txt"] = b"present\n"
    return files


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--check"):
        print("用法: make_predicate_fixtures.py <out_dir> [--check]", file=sys.stderr)
        return 2
    root = os.path.abspath(sys.argv[1])
    wanted = expected()
    if "--check" in sys.argv:
        actual = {}
        if os.path.isdir(root):
            for base, _dirs, names in os.walk(root):
                for name in names:
                    path = os.path.join(base, name)
                    actual[os.path.relpath(path, root)] = open(path, "rb").read()
        missing = sorted(set(wanted) - set(actual))
        extra = sorted(set(actual) - set(wanted))
        drift = sorted(k for k in set(wanted) & set(actual) if wanted[k] != actual[k])
        if missing or extra or drift:
            print(f"FAIL: predicate fixture 漂移 missing={missing} extra={extra} drift={drift}")
            return 1
        print(f"PASS: predicate fixture {len(wanted)} files 与生成器逐字一致")
        return 0
    if os.path.isdir(root):
        shutil.rmtree(root)
    for rel, data in wanted.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    print(f"built predicate fixtures: {len(wanted)} files → {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
