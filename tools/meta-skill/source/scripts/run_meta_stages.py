#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run deterministic helper fixtures; never report these as model evaluations."""
import argparse
import hashlib
import json
import os
import runpy
import shutil
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)


def _fixture_inputs():
    with open(os.path.join(PACKAGE, "assets", "self_check_inputs.json"), encoding="utf-8") as f:
        return json.load(f)


def _run(argv):
    """同进程执行确定性 helper；M8 sandbox 明确禁止 fork/后台遗留。"""
    script, args = argv[1], argv[2:]
    old_argv = sys.argv[:]
    try:
        sys.argv = [script, *args]
        runpy.run_path(script, run_name="__main__")
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else (0 if error.code is None else 1)
        if code:
            raise RuntimeError(f"helper {os.path.basename(script)} rc={code}")
    finally:
        sys.argv = old_argv


def _file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _content_hash(rows):
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _write_receipt(run_dir, name, source_id, paths):
    # Freeze the files observed at this stage; later helpers may update the workspace.
    stage = name.removesuffix("_receipt.json")
    observation = uuid.uuid4().hex
    snapshots = []
    for path in paths:
        dest = os.path.join(run_dir, "stage_outputs", stage, observation, os.path.relpath(path, run_dir))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        snapshots.append(dest)
    outputs = [{"id": os.path.relpath(path, run_dir).replace(os.sep, "/"),
                "kind": "file", "sha256": _file_hash(path)} for path in snapshots]
    receipt = {"source_id": source_id, "fetched_at": "deterministic-self-check",
               "output_count": len(outputs), "outputs_sha256": _content_hash(outputs),
               "outputs": outputs, "evidence_kind": "deterministic_fixture"}
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)


def init_eval_workspace(run_dir):
    root = os.path.join(run_dir, "workspace")
    _run([sys.executable, os.path.join(HERE, "init_eval_workspace.py"),
          "meta-skill-self", "--root", root])
    ws = os.path.join(root, "meta-skill-self")
    paths = [os.path.join(ws, "evals", "evals.json"),
             os.path.join(ws, "trigger_eval", "trigger_set.json"),
             os.path.join(ws, "history.json")]
    _write_receipt(run_dir, "init_eval_workspace_receipt.json",
                   "scripts/init_eval_workspace.py", paths)


def run_trigger_eval(run_dir):
    root = os.path.join(run_dir, "workspace")
    ws = os.path.join(root, "meta-skill-self")
    if not os.path.isdir(ws):
        _run([sys.executable, os.path.join(HERE, "init_eval_workspace.py"),
              "meta-skill-self", "--root", root])
    trigger_path = os.path.join(ws, "trigger_eval", "trigger_set.json")
    inputs = _fixture_inputs()
    trigger_set = inputs["trigger_cases"]
    with open(trigger_path, "w", encoding="utf-8") as f:
        json.dump(trigger_set, f, ensure_ascii=False, indent=2)
    _run([sys.executable, os.path.join(HERE, "run_trigger_eval.py"), "prepare",
          "--skill", "meta-skill-self", "--root", root,
          "--skill-path", PACKAGE, "--runs", "1"])
    judging = os.path.join(ws, "trigger_eval", "judging", "original")
    with open(os.path.join(judging, "_prepared.json"), encoding="utf-8") as f:
        prepared = json.load(f)
    with open(os.path.join(judging, "run1.json"), "w", encoding="utf-8") as f:
        json.dump({"run": 1, "eval_fingerprint": prepared["eval_fingerprint"],
                   "verdicts": inputs["trigger_votes"]}, f,
                  ensure_ascii=False, indent=2)
    _run([sys.executable, os.path.join(HERE, "run_trigger_eval.py"), "score",
          "--skill", "meta-skill-self", "--root", root])
    paths = [os.path.join(ws, "trigger_eval", "_split.json"),
             os.path.join(ws, "trigger_eval", "_judge_card.md"),
             os.path.join(ws, "trigger_eval", "result.json")]
    _write_receipt(run_dir, "run_trigger_eval_receipt.json",
                   "scripts/run_trigger_eval.py", paths)


def aggregate_benchmark(run_dir):
    root = os.path.join(run_dir, "workspace")
    ws = os.path.join(root, "meta-skill-self")
    if not os.path.isdir(ws):
        _run([sys.executable, os.path.join(HERE, "init_eval_workspace.py"),
              "meta-skill-self", "--root", root])
    _run([sys.executable, os.path.join(HERE, "init_eval_workspace.py"),
          "meta-skill-self", "--root", root, "--iteration", "1", "--runs", "1"])
    iteration = os.path.join(ws, "iteration-1")
    for name in os.listdir(iteration):
        if not name.startswith("eval-"):
            continue
        eval_type = "route_convergence" if name.startswith("eval-1-") else "end_state"
        grading = _fixture_inputs()["gradings"][eval_type]
        with open(os.path.join(iteration, name, "grading.json"), "w", encoding="utf-8") as f:
            json.dump(grading, f, ensure_ascii=False, indent=2)
    _run([sys.executable, os.path.join(HERE, "aggregate_benchmark.py"), iteration,
          "--skill-name", "meta-skill-self"])
    paths = [os.path.join(iteration, "benchmark", "benchmark.json"),
             os.path.join(iteration, "benchmark", "benchmark.md")]
    _write_receipt(run_dir, "aggregate_benchmark_receipt.json",
                   "scripts/aggregate_benchmark.py", paths)


STAGES = {"init_eval_workspace": init_eval_workspace,
          "run_trigger_eval": run_trigger_eval,
          "aggregate_benchmark": aggregate_benchmark}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    STAGES[args.stage](args.run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
