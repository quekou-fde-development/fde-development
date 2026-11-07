#!/usr/bin/env python3
"""公开仓库链接检查：正文中的相对 .md 链接必须能从所在文件解析到真实文件。

用法（从 repository/ 根目录执行）：
    python3 handbook/04-development/build/check_links.py
    python3 handbook/04-development/build/check_links.py handbook/03-architecture

退出码 0 = 全部可达；1 = 存在断链（逐条打印）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINK = re.compile(r"\]\(<?([^)>\s#]+)")
SCAN_EXT = (".md",)


def walk(base):
    for root, _, files in os.walk(base):
        for name in sorted(files):
            if name.endswith(SCAN_EXT):
                yield os.path.join(root, name)


def check(base):
    broken, total = [], 0
    for path in walk(base):
        here = os.path.dirname(path)
        text = open(path, encoding="utf-8").read()
        for m in LINK.finditer(text):
            target = m.group(1)
            total += 1
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not target.endswith(SCAN_EXT):
                continue
            resolved = os.path.normpath(os.path.join(here, target))
            if not os.path.exists(resolved):
                broken.append((os.path.relpath(path, base), target))
    return total, broken


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else ROOT
    total, broken = check(base)
    print(f"链接 {total} 处，断链 {len(broken)} 处")
    for path, target in broken:
        print(f"  {path} -> {target}")
    sys.exit(1 if broken else 0)
