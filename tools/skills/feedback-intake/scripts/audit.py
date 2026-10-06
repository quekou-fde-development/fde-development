#!/usr/bin/env python3
"""Independent audit for feedback-intake's handoff receipt contract."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


TYPE_MAP = {
    "str": str,
    "int": int,
    "float": (int, float),
    "bool": bool,
    "number": (int, float),
    "list": list,
    "dict": dict,
}
FAMILIES = {"artifact_hash", "schema_conformance", "receiver_receipt"}


def sha16(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def read_document(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def nested_value(value, path):
    current = value
    for piece in path.split("."):
        if isinstance(current, list):
            current = current[int(piece)]
        else:
            current = current[piece]
    return current


def safe_file(run_dir, relative):
    if (not isinstance(relative, str) or not relative or os.path.isabs(relative)
            or "\\" in relative or ".." in relative.split("/")):
        raise ValueError("artifact path is not a run-dir relative path")
    base = os.path.realpath(run_dir)
    target = os.path.realpath(os.path.join(base, relative))
    if os.path.commonpath([base, target]) != base or target == base:
        raise ValueError("artifact path escapes run-dir")
    return target


def result(stage, spec, status, detail=""):
    return {
        "stage": stage,
        "id": spec["id"],
        "family": spec["family"],
        "tier": spec["tier"],
        "status": status,
        "detail": detail,
    }


def audit_hash(run_dir, receipt, spec):
    predicate = spec["predicate"]
    path = safe_file(run_dir, predicate["artifact_path"])
    if not os.path.isfile(path):
        return False, "preview artifact is missing"
    declared = nested_value(receipt, predicate["declared_hash"])
    actual = sha16(path)
    return actual == declared, f"computed={actual} declared={declared}"


def audit_schema(receipt, spec):
    predicate = spec["predicate"]
    rows = nested_value(receipt, predicate["collection"])
    if not isinstance(rows, list):
        return False, "delivery collection is not a list"
    required = predicate["required_fields"]
    field_types = predicate["field_types"]
    if set(required) - set(field_types):
        return False, "required fields lack declared types"
    failures = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            failures.append(f"delivery[{index}] is not an object")
            continue
        for field in required:
            if field not in row:
                failures.append(f"delivery[{index}] missing {field}")
                continue
            expected = TYPE_MAP.get(field_types[field])
            if expected is None:
                failures.append(f"delivery[{index}] has unknown type {field_types[field]}")
            elif isinstance(row[field], bool) and field_types[field] in {"int", "float", "number"}:
                failures.append(f"delivery[{index}].{field} is bool")
            elif not isinstance(row[field], expected):
                failures.append(f"delivery[{index}].{field} has wrong type")
    return not failures, "; ".join(failures[:6])


def audit_receipt(receipt, spec):
    missing = [key for key in spec["predicate"]["required_keys"]
               if not receipt.get(key)]
    return not missing, "missing=" + ",".join(missing) if missing else ""


def evaluate(run_dir, contract, selected):
    stages = contract.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("contract has no stages")
    names = [stage.get("stage") for stage in stages]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ValueError("contract stage identity is invalid")
    unknown = selected - set(names)
    if unknown:
        raise ValueError("unknown stage: " + ",".join(sorted(unknown)))
    rows, ids = [], set()
    for stage_spec in stages:
        stage = stage_spec["stage"]
        if selected and stage not in selected:
            continue
        operations = stage_spec.get("operations")
        if not isinstance(operations, list) or not operations:
            raise ValueError("stage has no operations")
        for operation in operations:
            artifact = safe_file(run_dir, operation["artifact"])
            receipt = read_document(artifact) if os.path.isfile(artifact) else None
            assertions = operation.get("assertions")
            if not isinstance(assertions, list) or not assertions:
                raise ValueError("operation has no assertions")
            for spec in assertions:
                if not isinstance(spec.get("id"), str) or not spec["id"] or spec["id"] in ids:
                    raise ValueError("assertion identity is invalid")
                ids.add(spec["id"])
                family, tier = spec.get("family"), spec.get("tier")
                if family not in FAMILIES or tier not in {0, 1, 2}:
                    rows.append(result(stage, spec, "FAIL", "unsupported assertion declaration"))
                    continue
                if receipt is None:
                    rows.append(result(stage, spec, "FAIL", "handoff receipt is missing"))
                    continue
                try:
                    if family == "artifact_hash":
                        ok, detail = audit_hash(run_dir, receipt, spec)
                    elif family == "schema_conformance":
                        ok, detail = audit_schema(receipt, spec)
                    else:
                        ok, detail = audit_receipt(receipt, spec)
                except (KeyError, TypeError, ValueError, IndexError) as error:
                    ok, detail = False, f"{type(error).__name__}: {error}"
                rows.append(result(stage, spec, "PASS" if ok else "FAIL", detail))
    return rows


def write_manifest(path, run_dir, contract_path, package, contract, rows, source):
    counts = {
        "passed": sum(row["status"] == "PASS" for row in rows),
        "failed": sum(row["status"] == "FAIL" for row in rows),
        "unverified": 0,
    }
    verdict = "FAIL" if counts["failed"] else "PASS"
    stages = []
    for stage in contract["stages"]:
        stage_rows = [row for row in rows if row["stage"] == stage["stage"]]
        stage_counts = {
            "passed": sum(row["status"] == "PASS" for row in stage_rows),
            "failed": sum(row["status"] == "FAIL" for row in stage_rows),
            "unverified": 0,
        }
        stages.append({
            "stage": stage["stage"],
            "operations": [{
                "op": operation["op"],
                "artifact": operation["artifact"],
                "source_reachability": operation.get("source_reachability", "machine"),
            } for operation in stage["operations"]],
            "audit_tiers_run": sorted({row["tier"] for row in stage_rows}),
            "assertions": stage_counts,
            "verdict": "FAIL" if stage_counts["failed"] else "PASS",
            "unresolved_coverage": [],
        })
    document = {
        "run_id": Path(run_dir).name,
        "package_hash": sha16(os.path.join(package, "assertions.json")),
        "contract_hash": sha16(contract_path),
        "run_dir_resolved": os.path.realpath(run_dir),
        "run_dir_source": source,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stages": stages,
        "final_verdict": verdict,
        "retention": "always",
    }
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--contract", default=None)
    parser.add_argument("--stage", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--source")
    parser.add_argument("--manifest")
    parser.add_argument("--package", default=str(Path(__file__).parents[1]))
    parser.add_argument("--run-dir-source", default="explicit_arg",
                        choices=["explicit_arg", "env", "default"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if bool(args.stage) == bool(args.all) or len(args.stage) != len(set(args.stage)):
        parser.error("choose one unique --stage or --all")
    try:
        if args.contract:
            contract_path = args.contract
            contract = read_document(contract_path)
        else:
            contract_path = "assertions.json"
            with open("assertions.json", encoding="utf-8") as contract_stream:
                contract = json.load(contract_stream)
        if contract.get("contract_ir_version") != "1.0":
            raise ValueError("unsupported contract_ir_version")
        rows = evaluate(args.run_dir, contract, set(args.stage))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print(f"contract or input error: {type(error).__name__}: {error}", file=os.sys.stderr)
        return 2
    if args.manifest:
        write_manifest(args.manifest, args.run_dir, contract_path, args.package,
                       contract, rows, args.run_dir_source)
    payload = {
        "rows": rows,
        "counts": {
            "passed": sum(row["status"] == "PASS" for row in rows),
            "failed": sum(row["status"] == "FAIL" for row in rows),
            "unverified": 0,
            "warned": 0,
        },
        "verdict": "FAIL" if any(row["status"] == "FAIL" for row in rows) else "PASS",
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['status']} {row['stage']}/{row['id']}: {row['detail']}")
    return 1 if payload["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
