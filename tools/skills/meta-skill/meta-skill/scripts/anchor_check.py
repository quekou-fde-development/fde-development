# -*- coding: utf-8 -*-
"""
anchor_check.py — meta-skill 第 7 步 A2（指针有效性）+ A1（复制体）候选扫描。

大白话契约（给不懂代码的人看）：
  这个脚本只读、只打印，绝不改任何文件。无外部依赖，python3 直接跑。
  它替肉眼干两件死活的事——肉眼审最容易在这两件事上滑标准：
    A2 指针有效性：skill 里写的每个「某文件 §某节」，那个节在那个文件里真存在吗？
    A1 复制体候选：skill 正文里有没有抄死阈值数值（疑似把别处判据内联进来了）？

  用法：
    python anchor_check.py "<SKILL.md 路径>"           只跑 A2
    python anchor_check.py "<SKILL.md 路径>" --inline   额外跑 A1 候选扫描

  A2 判定（每个 §锚点）：
    在正文里找它最近的前置文件路径当目标文件，去该文件找标题行（# 开头）。
    取锚点文字（去掉 §），按空格切词，从全词到只剩首词逐步缩短，
    找最长的、能被某条标题文字包含的前缀——
      FOUND  命中恰好 1 条标题
      AMBIG  命中 >1 条标题（锚点不唯一，A2 fail）
      DEAD   命中 0 条 → 死指针，A2 fail
      NOFILE 锚点前面找不到文件路径 / 路径文件不存在 → 无法解析
    有任何 AMBIG / DEAD / NOFILE → 退出码 1；否则 0。

  A1（--inline）只列「疑似内联的阈值数值」候选行，不判 fail：
    归属要人核——有家（权威源里能找到）= fail，该改指针；无家 = extract 内联，合法。
"""
import os
import re
import sys

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文报告变乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 文件路径：Windows 绝对路径。允许目录名含空格 / 中文（如 "Meta Zone"、"01 Projects"），
# 靠 文件扩展名 或 目录尾反斜杠 锚定结尾 + 前瞻边界，避免在空格处被截断（旧版 \s 截断 bug）。
PATH_RE = re.compile(
    r"[A-Za-z]:\\"
    r"[^\r\n`\"<>|*?]*?"
    r"(?:\.(?:md|py|json|html|txt|csv|ya?ml|ps1|bat|ini|cfg|toml)|\\)"
    r"(?=[\s`\"，。；、）)」』,;]|$)"
)
# 相对路径 / 裸文件名：以 .md / .py 结尾（如 references/verification.md、storage-agent.md）
RELPATH_RE = re.compile(r"(?<![A-Za-z]:\\)(?<![\\/\w])[\w./\\-]+\.(?:md|py)\b")
# 锚点：§ 起，到标点 / 反引号 / 换行为止（允许中间空格，故多词节名也能整段抓出）
ANCHOR_RE = re.compile(r"§[^，,。；;、/）)」』（(`\n]+")


def resolve_file(raw, base_dir):
    """把抓到的路径 token 落成可判存在的绝对路径。绝对→原样；相对→拼 base_dir。"""
    if re.match(r"^[A-Za-z]:\\", raw):
        return raw
    norm = raw.replace("\\", os.sep).replace("/", os.sep)
    return os.path.normpath(os.path.join(base_dir, norm))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def headings_of(path):
    """返回目标文件所有标题行的纯文字（去掉 # 和首尾空白）。文件不存在返回 None。"""
    if not os.path.isfile(path):
        return None
    out = []
    for line in read_text(path).splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            out.append(m.group(1).strip())
    return out


def resolve(anchor_text, headings):
    """最长前缀包含匹配。返回 (matched_text, [命中标题])。"""
    tokens = anchor_text.split()
    for end in range(len(tokens), 0, -1):
        cand = " ".join(tokens[:end])
        hits = [h for h in headings if cand in h]
        if hits:
            return cand, hits
    return anchor_text, []


def _short(raw):
    return os.path.basename(raw.rstrip("\\/")) if raw else raw


def collect_events(text):
    """收集 路径 / 锚点 事件，按出现顺序。
    相对路径若落在某绝对路径区间内则跳过（防 C:\\... 内部被 RELPATH 二次误匹配）。
    单个拉丁字母锚点（如示例里的 §X）视为占位符，不收。"""
    abs_spans = [(m.start(), m.end()) for m in PATH_RE.finditer(text)]
    events = []
    for m in PATH_RE.finditer(text):
        events.append((m.start(), "path", m.group().rstrip(".·、")))
    for m in RELPATH_RE.finditer(text):
        if any(s <= m.start() < e for s, e in abs_spans):
            continue
        events.append((m.start(), "path", m.group()))
    for m in ANCHOR_RE.finditer(text):
        raw = m.group().lstrip("§").strip()
        if raw and not re.fullmatch(r"[A-Za-z]", raw):
            events.append((m.start(), "anchor", raw))
    events.sort(key=lambda e: e[0])
    return events


def run_a2(text, base_dir):
    events = collect_events(text)
    all_files = []
    for _, kind, val in events:
        if kind == "path" and val not in all_files:
            all_files.append(val)
    refs = []
    current = None
    for _, kind, val in events:
        if kind == "path":
            current = val
        else:
            refs.append((val, current))
    if not refs:
        print("A2 NOTE: 正文没有 §锚点，无指针可验")
        return True

    cache = {}

    def heads_of_raw(raw):
        rf = resolve_file(raw, base_dir)
        if rf not in cache:
            cache[rf] = headings_of(rf)
        return cache[rf]

    rows = []
    ok = True
    seen = set()
    for anchor, near in refs:
        # 同名节在不同文件里是两个独立指针。只按 anchor 去重会让先出现的
        # 正常文件替后一份坏指针挡枪，形成跨文件 false PASS。
        identity = (anchor, near)
        if identity in seen:
            continue
        seen.add(identity)
        matched, hits, where, fallback = None, [], None, False
        # 先试最近绑定文件
        if near and heads_of_raw(near):
            matched, hits = resolve(anchor, heads_of_raw(near))
            if hits:
                where = near
        # 只有正文没给邻接文件时才允许全局消歧。已有邻接文件却去别的文件找
        # 同名节，会把 `dead.md §2` 错绑到 `good.md §2`，掩盖真实死指针。
        if not hits and not near:
            for raw in all_files:
                h = heads_of_raw(raw)
                if not h:
                    continue
                matched, hits = resolve(anchor, h)
                if hits:
                    where, fallback = raw, True
                    break
        if not hits:
            if not near:
                rows.append(("NOFILE", anchor, "(锚点前无文件路径)", ""))
            elif heads_of_raw(near) is None:
                rows.append(("NOFILE", anchor, _short(near), "目标文件不存在，他处亦无此节"))
            else:
                rows.append(("DEAD", anchor, _short(near), "所有被引文件均无此节名"))
            ok = False
        elif len(hits) > 1:
            rows.append(("AMBIG", anchor, _short(where), f"命中{len(hits)}条: {hits}"))
            ok = False
        else:
            notes = []
            if matched != anchor:
                notes.append(f"匹配前缀「{matched}」")
            if fallback:
                notes.append("(回退命中，非最近绑定)")
            rows.append(("FOUND", anchor, _short(where), " ".join(notes)))
    print("A2 指针有效性")
    print("-" * 56)
    for status, anchor, where, note in rows:
        line = f"  [{status:6}] §{anchor}  →  {where}"
        if note:
            line += f"   {note}"
        print(line)
    return ok


def run_a1_inline(text):
    """A1 候选：列疑似内联阈值数值的行。只列候选，归属人核。"""
    body = text
    # 跳过 frontmatter
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:]
    num_unit = re.compile(r"[≥≤<>＜＞]?\s*\d+\s*(个|次|条|天|周|周日|小时|分钟|秒|%|星|级|行|字|轮)")
    print()
    print("A1 复制体候选（疑似内联阈值数值，归属请人核）")
    print("-" * 56)
    hits = 0
    for i, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if num_unit.search(s):
            hits += 1
            tag = "  (本行含 §指针)" if "§" in s else "  (无指针，重点核)"
            print(f"  L{i}: {s[:70]}{tag}")
    if hits == 0:
        print("  未发现阈值数值候选")
    print(f"  共 {hits} 条候选——有家=fail 改指针；无家=extract 内联合法")


def main():
    if len(sys.argv) < 2:
        print('用法: python anchor_check.py "<SKILL.md 路径>" [--inline]')
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"FAIL: 找不到文件 {path}")
        sys.exit(2)
    text = read_text(path)
    base_dir = os.path.dirname(os.path.abspath(path))

    bar = "=" * 56
    print(bar)
    print(f"anchor_check.py · {path}")
    print(bar)

    ok = run_a2(text, base_dir)
    if "--inline" in sys.argv[2:]:
        run_a1_inline(text)

    print(bar)
    print("A2 结论:", "指针唯一可达 [OK]" if ok else "有 AMBIG/DEAD/NOFILE 指针，A2 fail [X]")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
