#!/usr/bin/env python3
"""跑一段生产段并立即审这一段；最后一段额外做全量审。

段内审核紧跟段内落盘——把失败钉在造成它的那一段，而不是等全链跑完再回溯。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_pipeline.py"
AUDIT = ROOT / "scripts" / "audit.py"
CONTRACT = ROOT / "assertions.json"
STAGES = [
    "freeze_spec",
    "accept_environment",
    "resolve_routing",
    "compile_prompt",
    "accept_images",
    "apply_config",
    "verify_readback",
    "finalize_delivery",
]
LAST = STAGES[-1]


def call(parts: list[str]) -> int:
    return subprocess.run(parts).returncode


def declared_artifacts(stage: str) -> list[str]:
    """从 contract 取这一段声明的产物名。两处共用同一份声明，不会漂。"""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for st in contract["stages"]:
        if st["stage"] == stage:
            return [op["artifact"] for op in st["operations"]]
    raise SystemExit(f"[usage] 契约里没有这一段：{stage}")


def clear_artifacts(run_dir: Path, stage: str) -> None:
    """跑这一段之前先删掉它自己的旧产物。

    不删的话：这一段上次跑成功留下回执，这次跑失败不落新回执也不删旧的，
    审核器读到的是上一次那份，于是给一个刚硬失败的段判 PASS——实测可穿透。
    段只读上游回执，从不读自己的，故删自己的产物不破坏续跑语义。
    """
    for name in declared_artifacts(stage):
        target = run_dir / name
        if target.exists():
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = str(Path(args.run_dir).resolve())
    manifest = str(Path(run_dir) / "run_manifest.json")
    clear_artifacts(Path(run_dir), args.stage)
    rc = call([sys.executable, str(RUNNER), "--stage", args.stage,
               "--run-dir", run_dir])
    if rc != 0:
        # 段硬失败也要在 manifest 上留痕：产物已在跑之前清掉，审核器会以
        # 「产物缺失」逐条判 FAIL 并写出 final_verdict=FAIL 的 manifest。
        # 不补这一步的话，manifest 停在上一段成功时的样子，自称 PASS。
        call([
            sys.executable, str(AUDIT), run_dir, "--contract", str(CONTRACT),
            "--stage", args.stage, "--manifest", manifest,
            "--package", str(ROOT), "--run-dir-source", "explicit_arg",
        ])
        return rc
    rc = call([
        sys.executable, str(AUDIT), run_dir, "--contract", str(CONTRACT),
        "--stage", args.stage, "--manifest", manifest,
        "--package", str(ROOT), "--run-dir-source", "explicit_arg",
    ])
    if rc != 0:
        return rc
    if args.stage == LAST:
        return call([
            sys.executable, str(AUDIT), run_dir, "--contract", str(CONTRACT),
            "--all", "--manifest", manifest,
            "--package", str(ROOT), "--run-dir-source", "explicit_arg",
        ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
