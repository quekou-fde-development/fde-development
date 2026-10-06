#!/usr/bin/env python3
"""Canonical verification adapter for the cross-skill public-preview handoff."""
import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def read_input(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".feedback-intake-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sha16(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def production_feedback_module(package_root):
    sibling_scripts = package_root.parent / "github-feedback-maintainer" / "scripts"
    source = sibling_scripts / "feedback.py"
    if not source.is_file():
        raise RuntimeError("sibling github-feedback-maintainer production module is unavailable")
    sys.path.insert(0, str(sibling_scripts))
    try:
        return importlib.import_module("feedback")
    finally:
        sys.path.pop(0)


def prepare_feedback(run_dir):
    package_root = Path(__file__).resolve().parents[1]
    draft = read_input(Path(run_dir) / "input" / "draft.json")
    production = production_feedback_module(package_root)
    preview = production.wrap_preview(production.render(draft))
    preview_path = Path(run_dir) / "stage_outputs" / "prepare_feedback" / "preview.json"
    write_json(preview_path, preview)
    receipt_id = hashlib.sha256(
        (preview["payload"]["request_id"] + preview["preview_sha256"]).encode("utf-8")
    ).hexdigest()[:16]
    delivery = {
        "request_id": preview["payload"]["request_id"],
        "receiver": "github-feedback-maintainer",
        "receiver_interface": "scripts/feedback.py::render+wrap_preview",
        "preview_path": "stage_outputs/prepare_feedback/preview.json",
        "preview_file_sha256": sha16(preview_path),
        "preview_sha256": preview["preview_sha256"],
        "receipt_id": receipt_id,
    }
    receipt = {
        "receiver": delivery["receiver"],
        "receiver_interface": delivery["receiver_interface"],
        "request_id": delivery["request_id"],
        "receipt_id": receipt_id,
        "delivery_status": "preview_generated",
        "preview_path": delivery["preview_path"],
        "preview_file_sha256": delivery["preview_file_sha256"],
        "preview_sha256": delivery["preview_sha256"],
        "deliveries": [delivery],
    }
    receipt_path = Path(run_dir) / "stage_outputs" / "prepare_feedback" / "handoff_receipt.json"
    write_json(receipt_path, receipt)
    return receipt


STAGES = {"prepare_feedback": prepare_feedback}


def audit_stage(package_root, run_dir, stage):
    command = [
        sys.executable,
        str(package_root / "scripts" / "audit.py"),
        str(run_dir),
        "--contract", str(package_root / "assertions.json"),
        "--stage", stage,
        "--manifest", str(Path(run_dir) / "run_manifest.json"),
        "--package", str(package_root),
        "--run-dir-source", "explicit_arg",
        "--json",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return json.loads(completed.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        parser.error("--run-dir must exist")
    STAGES[args.stage](run_dir)
    package_root = Path(__file__).resolve().parents[1]
    payload = audit_stage(package_root, run_dir, args.stage)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
