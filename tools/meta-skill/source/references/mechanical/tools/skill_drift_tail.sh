#!/usr/bin/env bash
# 受支持的尾部查看入口：管道在本脚本内部，pipefail 保留 skill_drift.py 的失败码。
set -o pipefail
LINES="${SKILL_DRIFT_TAIL_LINES:-20}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/skill_drift.py" "$@" | tail -n "$LINES"
