# -*- coding: utf-8 -*-
"""
validate.py — meta-skill 的机械层审计器。

大白话契约（给不懂代码的人看）：
  这个脚本只查"死的、确定的"东西，不做任何需要判断的事。
  用法：  python validate.py "<skill 文件夹路径>"
  例如：  python validate.py "/path/to/skills/daily-review"
  它会读这个文件夹里的 SKILL.md，跑 12 项检查，打印 PASS/FAIL 报告。
  全 PASS → 退出码 0；有 FAIL → 退出码 1。
  它不修改被审包：结构检查只读；M8 会把包复制到临时中性目录，在 OS sandbox
  内真跑每个 stage，临时产物随探针清理。无可靠隔离后端时 fail-closed。

  十二项检查：
    M1 frontmatter 能解析（开头 --- 紧跟 name:，中间没有空行）
    M2 必填字段齐：name / description / metadata.updated
    M3 死链：正文里写到的本地文件路径，文件真的存在吗（§ 节锚点只列出来给人工抽查）
    M4 杂物：文件夹里有没有孤儿文件 / 残留备份（.bak、副本、~ 结尾、_old、备份 等）
    M5 description 非空、且不长到不像触发句（>600 字提醒）
    M6 网络节点三键契约（条件闸）：同目录有 _spec_in.md 或 metadata 出现三键任一
       → 机械验 topology_version 标量齐全 + edges_in/edges_out 行内式 [id:hash] 合规；
       非网络节点（无 _spec_in.md 且无三键）→ SKIP，不影响退出码。
    M7 执行步四槽：每条编号执行步须含 动作 / 依据 / 产出 / 值域，值域非空。
       对全部 skill 生效——v3.7 曾把本闸限定在网络节点（代码内 `M7 SKIP: 非网络节点`），
       普通 skill 从未生效；v3.8 解除限定。
    M8 两类脚本 + assertions.json 在位；逐 stage 隔离真跑并以可信解释器核本段断言
    M9 operation 在封闭词汇表内 + 该 operation 最低强断言族全覆盖
    M10 每条强断言登记 mutants（T0 除外）；mutant 目录声明 must_be_rejected_by
    M11 模板占位残留 fail-closed（<...> / TODO / TBD / 待填 / FIXME / XXX）
    M12 workflow_mode 与 stateful_contract：副作用边界、恢复、耐久证据与故障注入声明齐

  M8-M11 只在「持久 Skill 包」上生效，判定 = 命令行给 --persistent，或包内已有
  assertions.json（有即视为已声明为持久包）。一次性任务在 MetaSkill 第 1 步入口
  诊断即被拒，不该走到这里。

  判据源：references/contract_ir.md（operation 词汇表 §2 / 最低谓词族 §3 /
  assertions schema §6）。本脚本不内联复制该表的语义，只做机械比对。
"""
import ast
import copy
import errno
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文报告变乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from eval_common import parse_description
IR_PATH = os.path.normpath(os.path.join(HERE, "..", "references", "contract_ir.json"))


def load_ir():
    """读 contract IR 机读投影。读不到 = M9/M10 无判据，fail-closed。"""
    with open(IR_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_skill_md(folder):
    p = os.path.join(folder, "SKILL.md")
    if not os.path.isfile(p):
        return None, p
    with open(p, encoding="utf-8") as f:
        return f.read(), p


def check_frontmatter(text):
    """返回 (fail 列表, 解析出的 meta dict)。覆盖 M1。"""
    fails = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["M1 FAIL: 文件没有以 --- 开头的 frontmatter"], {}
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return ["M1 FAIL: frontmatter 没有闭合的 ---"], {}
    if lines[1].strip() == "":
        fails.append("M1 FAIL: 开头 --- 和第一个字段之间有空行（YAML 会读不到字段）")
    meta = {}
    current_mapping = None
    for i in range(1, close):
        line = lines[i]
        if line.strip() == "":
            continue
        nested = re.match(r"^  ([A-Za-z_][\w-]*):\s*(.*)$", line)
        if nested and current_mapping:
            meta[current_mapping][nested.group(1)] = nested.group(2).strip()
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value == "":
                meta[key] = {}
                current_mapping = key
            else:
                meta[key] = value
                current_mapping = None
            continue
        if line[:1].isspace():
            # 折叠/字面字符串的续行、allowed-tools 列表与更深层 metadata
            # 交给 parse_description / host validator；本无依赖解析器只取一层 metadata。
            continue
        fails.append(f"M1 FAIL: frontmatter 第 {i + 1} 行无法解析: {line}")
    allowed_top = {"name", "description", "license", "allowed-tools", "metadata"}
    unexpected = sorted(set(meta) - allowed_top)
    if unexpected:
        fails.append(f"M1 FAIL: 顶层字段不合 system Skill 规范: {unexpected}")
    if "metadata" in meta and not isinstance(meta["metadata"], dict):
        fails.append("M1 FAIL: metadata 须为映射")
    if "description" in meta:
        try:
            meta["description"] = parse_description(text)
        except ValueError as error:
            fails.append(f"M1 FAIL: description YAML 无效：{error}")
            meta["description"] = ""
    return fails, meta


BASE_SLOTS = ("动作", "依据", "产出", "值域")
# 卡片式必是执行段卡（由 `执行段：` 锚定），故按执行段六槽契约验：
# 总则四槽 + 可达接口（动作可不可执行）+ 断言（机械覆盖的登记面）。
CARD_SLOTS = ("动作", "可达接口", "依据", "产出", "值域", "断言")


def _outside_fences(lines):
    """保留 Markdown 围栏外的行；支持 backtick / tilde 围栏并维持原行号。"""
    out, fence_char, fence_len = [], None, 0
    for line in lines:
        m = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence_char is None and m:
            fence_char, fence_len = m.group(1)[0], len(m.group(1))
            out.append("")
        elif fence_char is not None and m and m.group(1)[0] == fence_char \
                and len(m.group(1)) >= fence_len:
            fence_char, fence_len = None, 0
            out.append("")
        else:
            out.append("" if fence_char is not None else line)
    return out


_CLI_HEADS = {
    "ansible", "awk", "bash", "bun", "cargo", "cat", "curl", "docker",
    "find", "gh", "git", "go", "gradle", "grep", "helm", "java", "javac",
    "jq", "kubectl", "make", "mvn", "node", "npm", "npx", "perl", "php",
    "pip", "pip3", "pnpm", "poetry", "podman", "powershell", "pwsh", "python",
    "python3", "rg", "rsync", "ruby", "rustc", "scp", "sed", "sh", "ssh",
    "tar", "terraform", "unzip", "uv", "wget", "yarn", "zip", "zsh",
}
_CLI_WRAPPERS = {"command", "env", "exec", "nohup", "sudo", "time"}
_LANGUAGE_HEADS = {
    "class", "const", "def", "else", "for", "from", "if", "import", "let",
    "return", "select", "var", "while", "with",
}
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
_SHELL_WORD = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]*$")
_GENERIC_CLI = re.compile(r"^[a-z][a-z0-9_+-]*$")


def _inline_code_spans(line):
    """取 Markdown 行内代码跨度；单/双/多 backtick delimiter 均支持。"""
    return [m.group(2).strip() for m in
            re.finditer(r"(?<!`)(`+)(.+?)\1(?!`)", line) if m.group(2).strip()]


def _command_tokens(code):
    """把 shell-like 代码跨度拆 token；解析失败即不猜。"""
    s = code.strip()
    if s.startswith("$ "):
        s = s[2:].lstrip()
    try:
        tokens = shlex.split(s, posix=True)
    except ValueError:
        return [], 0
    i = 0
    while i < len(tokens) and _ENV_ASSIGN.match(tokens[i]):
        i += 1
    while i < len(tokens) and tokens[i] in _CLI_WRAPPERS:
        i += 1
        while i < len(tokens) and (tokens[i].startswith("-") or
                                   _ENV_ASSIGN.match(tokens[i])):
            i += 1
    return tokens, i


def _looks_like_command(code, generic=True):
    """识别命令形态，不把规则绑死在一张命令白名单上。

    明确命令头、环境/包装前缀、相对/绝对可执行路径直接命中；行内代码还允许
    「命令词 + 参数/子命令」的通用 shell 形态，从而覆盖项目自带 CLI。单 token
    的属性名、配置路径与标识符不命中。
    """
    tokens, i = _command_tokens(code)
    if i >= len(tokens):
        return False
    cmd = tokens[i]
    low = cmd.lower()
    rest = tokens[i + 1:]
    if low in _CLI_HEADS:
        return True
    if cmd.startswith(("./", "../", "/")):
        base = os.path.basename(cmd)
        return ("/bin/" in cmd or base.endswith((".sh", ".py", ".pl", ".rb", ".ps1"))
                or bool(rest))
    if not generic or not rest or low in _LANGUAGE_HEADS:
        return False
    script_head = low.endswith((".sh", ".py", ".pl", ".rb", ".ps1"))
    generic_head = bool(_GENERIC_CLI.fullmatch(cmd))
    ascii_arg = bool(_SHELL_WORD.fullmatch(rest[0])) or rest[0].startswith("-")
    if not script_head and not (generic_head and ascii_arg):
        return False
    # 典型编程表达式不是 shell argv；其余 shell-like 多 token 形态 fail-closed。
    if rest[0] in {"=", "==", "!=", ":=", "->", "+", "-", "*", "/"}:
        return False
    return True


def _plain_command(line):
    """识别围栏外的整行/Markdown 前缀后裸命令及四空格缩进命令。"""
    indent = len(line) - len(line.lstrip(" "))
    s = line.lstrip()
    original = s
    # blockquote / list / numbered prefix 可叠加。
    for _ in range(3):
        s2 = re.sub(r"^(?:>\s*|[-+*]\s+|\d+[.)]\s+)", "", s, count=1)
        if s2 == s:
            break
        s = s2.lstrip()
    prefixed = s != original
    # 「7. 归档结果：git status」：说明前缀不构成豁免。
    for sep in ("：", ": "):
        if sep in s:
            tail = s.rsplit(sep, 1)[1].strip()
            if _looks_like_command(tail, generic=False):
                return tail
    generic = indent >= 4 or prefixed
    if _looks_like_command(s, generic=generic):
        return s
    return None


def _slot_value(line, slot):
    m = re.search(rf"\*\*{slot}[：:]\*\*\s*(.*?)(?=\*\*[^*]+[：:]\*\*|$)", line)
    return None if not m else m.group(1).strip()


def _card_blocks(lines):
    """切出卡片式执行段块。锚点是 `执行段：<名>`，块到空行 / 围栏 / 下一张卡为止。

    锚在 `执行段：` 而不是「有 `动作：` 行」——后者会把第 3 步那张**槽位模板**
    也当成真执行步来验。模板是在教怎么填，不是填好的步。
    """
    out, i, n = [], 0, len(lines)
    while i < n:
        m = re.match(r"^\s*执行段[：:]\s*(.+?)\s*$", lines[i])
        if not m:
            i += 1
            continue
        start, name, blk = i + 1, m.group(1), []
        i += 1
        while i < n:
            ln = lines[i]
            if not ln.strip() or ln.strip().startswith("```") or \
                    re.match(r"^\s*执行段[：:]", ln):
                break
            blk.append(ln)
            i += 1
        out.append((start, name, blk))
    return out


def check_m7(text, persistent=False):
    """M7 · 执行步四槽契约（动作 / 依据 / 产出 / 值域）。

    Gate-ID: validate.M7
    Obligations: STAGE.DECLARATION
    判据源 `contract_ir.md §6.3`。

    对全部 skill 生效，两种形态都验，不是只验编号式：
      * 编号式  `1. **动作：** …**依据：**…**产出：**…**值域：**…`
      * 卡片式  `执行段：<名>` 下的 `动作：` / `可达接口：` / `依据：` /
                `产出：` / `值域：` / `断言：` 行（执行段六槽）
    只验编号式会留一个洞：编译器自身与它编出的卡片式包全部 SKIP，而 SKIP
    在报告里与 PASS 同样是「没红」，等于四槽契约对卡片式从未生效过。
    Markdown 围栏内只算教学示例，不算本包的真实执行段。围栏外任意位置的
    反引号代码跨度，只要首 token 命中可执行命令白名单，就必须落在编号四槽步
    或六槽卡内；命令前有散文、编号前缀均不豁免。持久包找不到围栏外执行段卡
    时 FAIL；非持久、纯判断段 skill 才可 SKIP。
    """
    lines = _outside_fences(text.splitlines())
    errs = []

    structured = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^\s*(\d+[.)]|[-+*])\s+.*\*\*动作[：:]\*\*", line)
        if m:
            structured.append((i, line, "编号步" if m.group(1)[0].isdigit() else "列表步"))
    numbered = [(i, line) for i, line, kind in structured if kind == "编号步"]
    for lineno, line, kind in structured:
        missing = [s for s in BASE_SLOTS if not re.search(rf"\*\*{s}[：:]\*\*", line)]
        if missing:
            errs.append(f"L{lineno} {kind}缺槽 {missing}")
            continue
        empty = [s for s in BASE_SLOTS if not _slot_value(line, s)]
        if empty:
            errs.append(f"L{lineno} {kind}槽为空 {empty}")

    cards = _card_blocks(lines)
    card_names = [name.strip() for _lineno, name, _blk in cards]
    dup_cards = sorted({name for name in card_names if card_names.count(name) > 1})
    if dup_cards:
        errs.append(f"执行段卡名称重复 {dup_cards}——重复声明会被 set 吞掉，"
                    "不构成唯一 stage 身份")
    card_lines = set()
    for lineno, _name, blk in cards:
        card_lines.update(range(lineno, lineno + len(blk) + 1))

    # 可直接执行的命令只要出现在围栏外正文，就必须归入四槽编号步或六槽卡。
    # 行内代码按 shell 形态识别，不把覆盖面锁死在命令白名单；裸命令只认整行、
    # Markdown 前缀后或缩进代码形态，避免把普通散文误拆成 argv。
    unmarked = []
    for i, line in enumerate(lines, 1):
        if i in card_lines:
            continue
        commands = [code for code in _inline_code_spans(line)
                    if _looks_like_command(code)]
        plain = _plain_command(line)
        if plain:
            commands.insert(0, plain)
        if not commands:
            continue

        # 「写了动作二字」本身不是结构化：命令所在行须四槽全齐且值域非空。
        # 这也覆盖非编号的四槽说明行；编号行的细粒度缺槽错误由上段另报。
        complete = all(_slot_value(line, slot) for slot in BASE_SLOTS)
        if complete:
            continue
        unmarked.append((i, commands[0]))
    for lineno, command in unmarked:
        errs.append(f"L{lineno} 围栏外行内可执行命令未落四槽: `{command}`")

    for lineno, name, blk in cards:
        missing, empty = [], []
        for slot in CARD_SLOTS:
            hit = None
            for ln in blk:
                m = re.match(rf"^\s*{slot}[：:]\s*(.*)$", ln)
                if m:
                    hit = m.group(1).strip()
                    break
            if hit is None:
                missing.append(slot)
            elif not hit:
                empty.append(slot)
        if missing:
            errs.append(f"L{lineno} 执行段卡「{name}」缺槽 {missing}")
        if empty:
            errs.append(f"L{lineno} 执行段卡「{name}」槽为空 {empty}")

    if persistent and not cards:
        errs.append("持久 Skill 包在 Markdown 围栏外无真实 `执行段：<名>` 卡；"
                    "围栏内教学示例不得充当本包执行段")
    if errs:
        return False, errs
    if not structured and not cards:
        return None, "M7 SKIP: 未找到执行步（纯判断段 skill）"
    return True, (f"M7 PASS: 列表/编号步 {len(structured)} 条、执行段卡 {len(cards)} 张，"
                  f"四槽/六槽契约均合规")


CAUSE_TAG_RE = re.compile(r"\[CAUSE:[A-Z0-9_.-]+\]\s*")

# 人读诊断可以有多行，但每个失败闸块只发射一个机器病因码。病因取自最具体的
# 失败机制；后续明细不再携码，避免把多条解释误当成多个独立根因。外部 witness
# 对每个定向 fixture 绑定这个码，超集消息无法冒充多个判据仍然存在。
_GATE_CAUSE_RULES = {
    "M7": [
        (r"围栏外行内可执行命令未落四槽", "M7.COMMAND.UNSLOTTED"),
        (r"执行段卡名称重复", "M7.STAGE_CARD.DUPLICATE_NAME"),
        (r"执行段卡「.*」缺槽", "M7.STAGE_CARD.MISSING_SLOT"),
        (r"执行段卡「.*」槽为空", "M7.STAGE_CARD.EMPTY_SLOT"),
        (r"列表步缺槽", "M7.LIST_STEP.MISSING_SLOT"),
        (r"列表步槽为空", "M7.LIST_STEP.EMPTY_SLOT"),
        (r"编号步缺槽", "M7.NUMBERED_STEP.MISSING_SLOT"),
        (r"编号步槽为空", "M7.NUMBERED_STEP.EMPTY_SLOT"),
        (r"围栏外无真实", "M7.STAGE_CARD.NO_REAL_CARD"),
    ],
    "M8": [
        (r"assertions\.json stage 名为空", "M8.CONTRACT.STAGE_NAME_EMPTY"),
        (r"assertions\.json stage 名重复", "M8.CONTRACT.STAGE_NAME_DUPLICATE"),
        (r"assertions\.json 断言 id 为空", "M8.CONTRACT.ASSERTION_ID_EMPTY"),
        (r"assertions\.json 断言 id 重复", "M8.CONTRACT.ASSERTION_ID_DUPLICATE"),
        (r"run_manifest\.json stage 名重复", "M8.STAGE_CLOSURE.MANIFEST_STAGE_DUPLICATE"),
        (r"outcome=upstream_mutated", "M8.STAGE_BINDING.RUNTIME_OUTPUT.UPSTREAM_MUTATED"),
        (r"outcome=empty_artifact", "M8.STAGE_BINDING.RUNTIME_OUTPUT.EMPTY"),
        (r"outcome=invalid_json", "M8.STAGE_BINDING.RUNTIME_OUTPUT.INVALID_JSON"),
        (r"outcome=copied_upstream", "M8.STAGE_BINDING.RUNTIME_OUTPUT.COPIED_UPSTREAM"),
        (r"outcome=assertions_failed", "M8.STAGE_BINDING.RUNTIME_OUTPUT.ASSERTIONS_FAILED"),
        (r"outcome=capture_preoccupied", "M8.STAGE_BINDING.RUNTIME_OUTPUT.CAPTURE_PREOCCUPIED"),
        (r"outcome=audit_error", "M8.STAGE_BINDING.RUNTIME_OUTPUT.AUDIT_ERROR"),
        (r"隔离真跑未产出", "M8.STAGE_BINDING.RUNTIME_PROBE_FAILED"),
        (r"不可达真实写盘", "M8.STAGE_BINDING.UNREACHABLE_ARTIFACT_WRITE"),
        (r"未注册 `--stage`", "M8.STAGE_BINDING.MISSING_STAGE_FLAG"),
        (r"未注册 `--run-dir`", "M8.STAGE_BINDING.MISSING_RUN_DIR"),
        (r"两旗标齐", "M8.STAGE_BINDING.DISPATCH_UNBOUND"),
        (r"无执行入口", "M8.STAGE_BINDING.NO_RECOGNIZED_ENTRY"),
        (r"stage 集不闭合", "M8.STAGE_CLOSURE.SET_MISMATCH"),
        (r"缺 assertions\.json|缺执行段断言契约", "M8.CONTRACT.MISSING"),
        (r"缺 scripts/audit\.py", "M8.AUDITOR.MISSING"),
        (r"缺 fixtures/", "M8.FIXTURES.MISSING"),
        (r"缺 scripts/ 目录", "M8.SCRIPTS.MISSING"),
        (r"scripts/ 无 run\*\.py", "M8.RUNNER.MISSING"),
        (r"未消费 assertions\.json", "M8.AUDITOR.CONTRACT_UNCONSUMED"),
        (r"未注册 --contract", "M8.AUDITOR.CONTRACT_OVERRIDE_UNBOUND"),
        (r"import 了执行脚本|复制了执行脚本实现", "M8.AUDITOR.COMMON_CAUSE"),
        (r"SKILL 面为空", "M8.STAGE_CLOSURE.SKILL_EMPTY"),
    ],
    "M9": [
        (r"family↔tier 不符", "M9.FAMILY_TIER.MISMATCH"),
        (r"operation 不在封闭词汇表", "M9.OPERATION.OUTSIDE_VOCAB"),
        (r"最低强断言族缺", "M9.FAMILY.MINIMUM_MISSING"),
        (r"golden 与 mutant 载荷指纹相同", "M9.CUSTOM.PAYLOAD_COLLISION"),
        (r"解析后逃出包外", "M9.CUSTOM.PATH_ESCAPE"),
        (r"source_anchor.*不存在", "M9.CUSTOM.SOURCE_FILE_MISSING"),
        (r"source_anchor.*没有标题", "M9.CUSTOM.SOURCE_HEADING_MISSING"),
        (r"mutant 上 .* 未判 FAIL", "M9.CUSTOM.MUTANT_NOT_REJECTED"),
        (r"custom operation 缺启用条件", "M9.CUSTOM.ENABLEMENT_MISSING"),
        (r"mutant 缺 INJECTION\.json|mutant 未声明", "M9.CUSTOM.MUTANT_UNDIRECTED"),
    ],
    "M10": [
        (r"审核脚本写入探针外", "M10.AUDITOR.SANDBOX_WRITE"),
        (r"审核脚本读取探针外", "M10.AUDITOR.SANDBOX_READ"),
        (r"审核脚本越出隔离边界", "M10.AUDITOR.SANDBOX_BOUNDARY"),
        (r"审核脚本隔离.*失败|审核脚本无 --json 逐条输出",
         "M10.AUDITOR.RUNTIME_FAILED"),
        (r"审核输出含未声明断言", "M10.AUDIT_ROW.UNKNOWN_ID"),
        (r"审核输出断言 id 重复", "M10.AUDIT_ROW.DUPLICATE_ID"),
        (r"退出码与逐条状态不一致", "M10.AUDIT_ROW.EXIT_STATUS_MISMATCH"),
        (r"审核判定依赖 fixture 名称或 INJECTION\.json", "M10.AUDITOR.TEST_ANSWER_DEPENDENCY"),
        (r"正例上 .*?=UNVERIFIED", "M10.GOLDEN.UNVERIFIED"),
        (r"正例上", "M10.GOLDEN.NON_PASS"),
        (r"mutants 为空", "M10.ASSERTION.MUTANTS_EMPTY"),
        (r"缺 source_anchor", "M10.ASSERTION.SOURCE_ANCHOR_MISSING"),
        (r"指名的断言 .* 未判 FAIL", "M10.MUTANT.NOT_REJECTED"),
        (r"缺 must_be_rejected_by", "M10.MUTANT.UNDIRECTED"),
        (r"无 golden", "M10.GOLDEN.MISSING"),
    ],
    "M11": [
        (r"TODO|TBD|FIXME|XXX|占位|待填|待补|<", "M11.PLACEHOLDER.RESIDUE"),
    ],
}


def _normalize_gate_failure(gate, errors):
    """返回单一病因码 + 去掉历史内嵌码的明细；未分类即 fail-closed。"""
    clean = [CAUSE_TAG_RE.sub("", str(error)).strip() for error in errors]
    blob = "\n".join(clean)
    for pattern, code in _GATE_CAUSE_RULES[gate]:
        if re.search(pattern, blob):
            return code, clean
    return f"{gate}.DIAGNOSTIC.OTHER", clean


def _py_module_names(scripts_dir):
    """scripts/ 下可被 import 的模块名（不含 audit 自己）。"""
    return {os.path.splitext(n)[0] for n in os.listdir(scripts_dir)
            if n.endswith(".py") and n != "audit.py"}


def _str_constants(node):
    """节点子树里的全部字符串常量。"""
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _bindings(tree):
    """名字 → 它被赋过的表达式节点们。用来跟一跳变量。

    argv 与路径常常先落在变量里再传出去（`cmd = [..., "--contract", p]`
    然后 `subprocess.run(cmd)`）。只看调用实参的子树会全部漏掉，
    把真实的薄封装形态误杀成"未消费契约"。
    """
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(n.value)
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and \
                isinstance(n.target, ast.Name) and n.value is not None:
            out.setdefault(n.target.id, []).append(n.value)
    return out


def _reachable_strings(node, bindings, depth=3, seen=None):
    """节点子树里可达的字符串常量，沿变量绑定最多跟 depth 跳。"""
    if depth < 0:
        return []
    seen = seen or set()
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
        elif isinstance(n, ast.Name) and n.id in bindings and n.id not in seen:
            for val in bindings[n.id]:
                out += _reachable_strings(val, bindings, depth - 1, seen | {n.id})
    return out


def _call_name(n):
    if isinstance(n.func, ast.Attribute):
        return n.func.attr
    if isinstance(n.func, ast.Name):
        return n.func.id
    return ""


def _flows_to_open(tree, bindings):
    """契约路径是否真的流进了读文件的调用——open() / json.load() / read_text()。

    路径可以是字面量，也可以先拼进变量再传（跟绑定解析）；散在别处、
    不进任何读调用的诱饵字符串则抓不到。这正是要的区分。
    """
    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if _call_name(n) not in ("open", "load", "read_text", "read_bytes", "loads"):
            continue
        for arg in list(n.args) + [kw.value for kw in n.keywords]:
            if any("assertions.json" in s
                   for s in _reachable_strings(arg, bindings)):
                hits.append(f"{_call_name(n)}() 读 assertions.json")
    return hits


def _flows_to_subprocess(tree, bindings):
    """契约路径是否被交给子进程——薄封装转交通用解释器的形态。

    判据是**同一条 argv 里同时出现** `--contract` 与契约路径。只出现 --contract
    可能是散文或注释里的字样，只出现路径可能是没用上的常量；两者同在一条
    argv 上，才说明这次调用真的把契约传出去了。
    """
    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if _call_name(n) not in ("run", "Popen", "call", "check_call", "check_output",
                                 "execv", "execvp", "execvpe"):
            continue
        for arg in list(n.args) + [kw.value for kw in n.keywords]:
            strs = _reachable_strings(arg, bindings)
            if any("--contract" in s for s in strs) and \
                    any("assertions.json" in s for s in strs):
                hits.append(f"{_call_name(n)}() argv 携 --contract + 契约路径")
    return hits


def _audit_consumes_contract(tree):
    """审核脚本是否真的消费 assertions.json——验数据流，不是验出现过这个词。

    两种合法形态任一成立即算消费：
      a) 契约路径流进读文件调用（自己解释断言）
      b) 契约路径连同 --contract 流进子进程 argv（转交通用解释器）
    **不认「源码里出现过 assertions.json 字符串」**：docstring 里写一句、
    或 `x = "contract"` 摆个诱饵，再 `print("PASS")`，就能骗过纯字面量检测。
    那正是本闸最该拒的空壳形态。
    """
    b = _bindings(tree)
    return _flows_to_open(tree, b) + _flows_to_subprocess(tree, b)


def _audit_imports_exec(src, exec_modules):
    """审核脚本是否 import 了执行脚本——共因防线第二条。

    审核器复制/引用被审对象的实现，两者就共因：执行错了，审核用同一段错代码
    算一遍，照样"对得上"。故 import 执行模块即 fail，无论 import 还是 from-import。
    """
    bad = []
    for node in ast.walk(src):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in exec_modules:
                    bad.append(root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in exec_modules:
                bad.append(root)
    return sorted(set(bad))


def _normalize_fn(node):
    """把函数规范化成「同体判定」用的指纹：α-等价 + 去文档串。

    抄代码的人会改函数名、改形参名、改局部变量名、补一段自己的 docstring。
    只比原样语法树会全部漏掉。故：
      * 丢 docstring（不是实现的一部分）
      * 函数名、形参名、**局部绑定名**统一改写成 v0/v1/…（按首次出现定序）
      * 自由名（open / json / os 这些外部引用）**不改**——改了会把
        「调两个外部函数」的任意两段代码判成同体，造假阳性
    返回 (指纹, 节点数)；节点数用来滤掉琐碎函数。
    """
    clone = ast.parse(ast.unparse(node)).body[0]
    clone.name = "_fn"

    # 收集局部绑定：形参 + 赋值目标 + for/with/except/推导式目标
    bound, order = set(), []

    def bind(name):
        if name and name not in bound:
            bound.add(name)
            order.append(name)

    for a in list(clone.args.args) + list(clone.args.kwonlyargs) + list(clone.args.posonlyargs):
        bind(a.arg)
    if clone.args.vararg:
        bind(clone.args.vararg.arg)
    if clone.args.kwarg:
        bind(clone.args.kwarg.arg)
    for n in ast.walk(clone):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            bind(n.id)
        elif isinstance(n, ast.ExceptHandler):
            bind(n.name)
        elif isinstance(n, ast.alias):
            bind(n.asname or n.name.split(".")[0])

    ren = {name: f"v{i}" for i, name in enumerate(order)}
    for a in list(clone.args.args) + list(clone.args.kwonlyargs) + list(clone.args.posonlyargs):
        a.arg = ren.get(a.arg, a.arg)
    if clone.args.vararg:
        clone.args.vararg.arg = ren.get(clone.args.vararg.arg, clone.args.vararg.arg)
    if clone.args.kwarg:
        clone.args.kwarg.arg = ren.get(clone.args.kwarg.arg, clone.args.kwarg.arg)
    for n in ast.walk(clone):
        if isinstance(n, ast.Name) and n.id in ren:
            n.id = ren[n.id]
        elif isinstance(n, ast.ExceptHandler) and n.name in ren:
            n.name = ren[n.name]

    body = clone.body
    if body and isinstance(body[0], ast.Expr) and \
            isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]          # 丢 docstring
    clone.body = body or [ast.Pass()]
    return ast.dump(clone), sum(1 for _ in ast.walk(clone))


# 同体判定的节点数下限。低于此值的函数（一两行的取值 / 包装）在任何两份
# 脚本里都可能长得一样，算作"抄"是假阳性。
SHARED_FN_MIN_NODES = 25


def _shared_function_bodies(audit_path, exec_paths):
    """审核脚本与执行脚本是否有同体函数——共因防线第二条的复制粘贴形态。

    比的是 α-等价的语法树，不是文本：改函数名、改形参名、改局部变量名、
    加注释、补 docstring 都躲不掉。
    """
    def fingerprints(path):
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError):
            return {}
        out = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                try:
                    fp, size = _normalize_fn(node)
                except (SyntaxError, ValueError):
                    continue
                if size >= SHARED_FN_MIN_NODES:
                    out[node.name] = fp
        return out

    a = fingerprints(audit_path)
    shared = []
    for ep in exec_paths:
        rev = {}
        for name, fp in fingerprints(ep).items():
            rev.setdefault(fp, []).append(name)
        for aname, afp in a.items():
            if afp in rev:
                shared.append(f"{aname}() 与 {os.path.basename(ep)}::"
                              f"{'/'.join(rev[afp])}() 同体")
    return shared


def _local_funcs(tree):
    """本文件里定义的函数名 → 定义节点。跨调用跟一跳时用。"""
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _is_write_call(n):
    """这个调用是不是在往文件里写。

    `open` 只有带写模式才算——`open(p)` 是读，把它算成写则任何读文件的
    脚本都能冒充产出方。
    """
    name = _call_name(n)
    if name in ("write_text", "write_bytes", "writelines"):
        return True
    if name != "open":
        return False
    modes = []
    if len(n.args) > 1:
        modes += _str_constants(n.args[1])
    modes += [s for kw in n.keywords if kw.arg == "mode"
              for s in _str_constants(kw.value)]
    # ``+`` upgrades every read-looking mode (notably ``r+b``) to read/write.
    return any(set("wax+") & set(m) for m in modes)


def _is_mutating_io_call(node):
    """薄 adapter 禁止的文件系统 mutation，含高低层 API。"""
    if _is_write_call(node):
        return True
    name = _call_name(node)
    if name in {"write", "replace", "rename", "remove", "unlink", "mkdir", "makedirs",
                "rmdir", "removedirs", "truncate", "touch", "mmap", "flush", "resize",
                "copy", "copy2", "copyfile", "copytree", "move", "rmtree"}:
        return True
    if name == "open" and isinstance(node.func, ast.Attribute):
        flags = {item.attr for arg in node.args[1:] for item in ast.walk(arg)
                 if isinstance(item, ast.Attribute)}
        return bool(flags & {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"})
    return False


def _has_mutating_adapter_io(tree):
    """Reject adapter-owned filesystem/mmap mutation, including slice assignment.

    A thin verification adapter may delegate to production code, but it may not
    repair or replace that code's artifact after the call.  ``mmap`` writes do not
    contain a normal ``write()`` call, so track mmap-derived names and their
    subscript/attribute stores explicitly.
    """
    if any(isinstance(node, ast.Call) and _is_mutating_io_call(node)
           for node in ast.walk(tree)):
        return True
    tainted = set()
    for _ in range(4):
        grew = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            source_names = ({item.id for item in ast.walk(value)
                             if isinstance(item, ast.Name)}
                            if value is not None else set())
            mmap_source = (isinstance(value, ast.Call) and
                           _call_name(value) in {"mmap", "memoryview"} and
                           (_call_name(value) == "mmap" or bool(source_names & tainted)))
            if mmap_source or source_names & tainted:
                for target in targets:
                    for item in ast.walk(target):
                        if isinstance(item, ast.Name) and item.id not in tainted:
                            tainted.add(item.id)
                            grew = True
        if not grew:
            break
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, (ast.Subscript, ast.Attribute)):
                roots = {item.id for item in ast.walk(target.value)
                         if isinstance(item, ast.Name)}
                if roots & tainted:
                    return True
    return False


def _tainted_names(fn, seed):
    """函数体内由 seed 名派生出来的名字集合（沿赋值传播到不动点）。

    形参常常先落进局部变量再用（`p = os.path.join(d, name)`），只认形参
    本身出现在写调用实参里，这一形态就会漏。
    """
    binds = _bindings(fn)
    taint = set(seed)
    for _ in range(4):
        grew = False
        for name, vals in binds.items():
            if name in taint:
                continue
            if any({x.id for x in ast.walk(v) if isinstance(x, ast.Name)} & taint
                   for v in vals):
                taint.add(name)
                grew = True
        if not grew:
            break
    return taint


def _writes_artifact(tree, bindings, artifact):
    """产物名是否真的流进了写文件调用——验数据流，不是验出现过这个词。

    两种形态都认：
      a) 直接——`open(os.path.join(d, "s1_export.json"), "w")`；
      b) 跟一跳——产物名作实参传给本文件内定义的辅助函数，那个函数里写盘
         （`write(run_dir, "s1_export.json", art)` → `write` 内 `open(..., "w")`）。
    b 是完全正常的 Python 写法，不认它的检器会把规矩脚本误杀，于是只能靠
    豁免清单救，而豁免清单同时豁免空壳。
    """
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _is_write_call(n):
            for arg in list(n.args) + [kw.value for kw in n.keywords]:
                if any(artifact in s for s in _reachable_strings(arg, bindings)):
                    return True
    funcs = _local_funcs(tree)
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or _call_name(n) not in funcs:
            continue
        fn = funcs[_call_name(n)]
        params = [a.arg for a in fn.args.args]
        hit = set()
        for i, arg in enumerate(n.args):
            if i < len(params) and \
                    any(artifact in s for s in _reachable_strings(arg, bindings)):
                hit.add(params[i])
        for kw in n.keywords:
            if kw.arg in params and \
                    any(artifact in s for s in _reachable_strings(kw.value, bindings)):
                hit.add(kw.arg)
        if not hit:
            continue
        taint = _tainted_names(fn, hit)
        for m in ast.walk(fn):
            if isinstance(m, ast.Call) and _is_write_call(m):
                for arg in list(m.args) + [kw.value for kw in m.keywords]:
                    if {x.id for x in ast.walk(arg) if isinstance(x, ast.Name)} & taint:
                        return True
    return False


def _takes_flag(tree, bindings, flag):
    """脚本的 argv 里是否**真注册**了某个旗标。

    判据是 `add_argument("--stage")` 这类注册调用的位置实参全等该旗标，
    不是「源码里出现过 `--stage` 这个词」——后者在 docstring、用法示例、
    注释里都会出现，而那些位置上的字样不构成「调得起来」。
    """
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n) in ("add_argument", "add_option"):
            for arg in n.args:
                if any(s == flag for s in _reachable_strings(arg, bindings)):
                    return True
    return False


def _is_stage_selector(node):
    """这棵子树是不是「段选择器」——运行期由 --stage 决定的那个值。

    认四种写法：`a.stage` / `args.stage` / `opts["stage"]` / 裸名 `stage`。
    选择器的作用是把控制流分到某一段去；不由它索引的字典只是一张表，
    表在不等于表被用来选路。
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and n.attr == "stage":
            return True
        if isinstance(n, ast.Name) and n.id == "stage":
            return True
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) \
                and n.slice.value == "stage":
            return True
    return False


def _dict_keys_of(node, bindings, depth=2):
    """取一个表达式可达的字典字面量键集（沿变量绑定跟几跳）。"""
    out = set()
    if depth < 0:
        return out
    if isinstance(node, ast.Dict):
        return {k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    if isinstance(node, ast.Name):
        for val in bindings.get(node.id, []):
            out |= _dict_keys_of(val, bindings, depth - 1)
    return out


def _dispatch_dict_keys(tree, bindings):
    """被段选择器**实际索引并调用**的那个字典的键集。

    要的是「这张表真的把控制流分了出去」，三件事同时成立才算：
      1. 有一个 Subscript，被索引的是字典（字面量或变量，跟绑定）；
      2. 索引用的是段选择器（`STAGES[a.stage]`），不是别的键；
      3. 取出来的东西被调用——直接 `STAGES[a.stage](...)`，或先落到变量
         再调（`fn = STAGES[a.stage]` 然后 `fn(...)`）。

    三件缺一都放行的话，`STAGES = {"s1": s1, "s2": s2}` 摆在文件里、
    main 里只 `print(a.stage)`，段名就"可达"了——那正是 07:17 原型里
    「旗标 + 段名字典均在、但只打印不 dispatch」的诱饵形态。声明一张表
    是零成本的，把控制流交给它才是绑定。

    只认字典 dispatch，不认 `if a.stage == "s1": ...` 比较链：字典的值就是
    要调的那个可调用对象，「索引到并调用」即证明这一支有实体；比较链的分支
    体是任意语句，`if a.stage == "s1_export": print("ok")` 与真干活的分支在
    这一层不可分，判别力回落到诱饵那一档。代价是比较链写法的包须改成字典，
    这是 07:17 定的最小规则的已知边界，不是遗漏。
    """
    dispatched = set()          # 被段选择器索引的字典表达式（尚未确认被调用）
    called_names = set()        # 被调用过的裸名
    named_dispatch = {}         # 变量名 → 它绑定的段选择器索引表达式

    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Subscript) and _is_stage_selector(n.func.slice):
                dispatched |= _dict_keys_of(n.func.value, bindings)
            elif isinstance(n.func, ast.Name):
                called_names.add(n.func.id)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and isinstance(n.value, ast.Subscript) \
                        and _is_stage_selector(n.value.slice):
                    named_dispatch.setdefault(t.id, set())
                    named_dispatch[t.id] |= _dict_keys_of(n.value.value, bindings)
    for name, keys in named_dispatch.items():
        if name in called_names:
            dispatched |= keys
    return dispatched


def _dict_target_map(node, bindings, depth=2):
    """取 dispatch 字典的 stage → 本地 handler 名映射。"""
    if depth < 0:
        return {}
    if isinstance(node, ast.Dict):
        out = {}
        for key, val in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and \
                    isinstance(val, ast.Name):
                out.setdefault(key.value, set()).add(val.id)
        return out
    if isinstance(node, ast.Name):
        out = {}
        for val in bindings.get(node.id, []):
            for stage, targets in _dict_target_map(val, bindings, depth - 1).items():
                out.setdefault(stage, set()).update(targets)
        return out
    return {}


def _dispatch_targets(tree, bindings):
    """只取被 `--stage` 选择器索引并调用的 stage → handler 映射。"""
    out, named, called = {}, {}, set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Subscript) and _is_stage_selector(n.func.slice):
                for stage, targets in _dict_target_map(n.func.value, bindings).items():
                    out.setdefault(stage, set()).update(targets)
            elif isinstance(n.func, ast.Name):
                called.add(n.func.id)
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Subscript) \
                and _is_stage_selector(n.value.slice):
            mapping = _dict_target_map(n.value.value, bindings)
            for target in n.targets:
                if isinstance(target, ast.Name):
                    named[target.id] = mapping
    for name in called & set(named):
        for stage, targets in named[name].items():
            out.setdefault(stage, set()).update(targets)
    return out


def _argparse_callback_dispatch(tree, bindings):
    """识别生产 CLI 常见的 argparse subparser callback 路由，仅用于诊断。

    这种路由形如 ``add_parser("cmd").set_defaults(function=handler)``，随后
    ``args.function(args)``。它证明生产命令确实有 callback dispatch，却不满足
    M8 的 canonical ``--stage``/``--run-dir`` verification surface；调用方应生成
    薄 adapter，不能误报成“补 assertions 即可”。
    """
    parser_commands = {}
    callback_attrs = set()
    mappings = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and \
                _call_name(node.value) == "add_parser":
            commands = {s for arg in node.value.args
                        for s in _reachable_strings(arg, bindings)}
            for target in node.targets:
                if isinstance(target, ast.Name):
                    parser_commands.setdefault(target.id, set()).update(commands)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "set_defaults":
            continue
        handlers = {kw.arg: kw.value.id for kw in node.keywords
                    if kw.arg and isinstance(kw.value, ast.Name)}
        if not handlers:
            continue
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
        commands = set()
        if isinstance(receiver, ast.Call) and _call_name(receiver) == "add_parser":
            commands |= {s for arg in receiver.args
                         for s in _reachable_strings(arg, bindings)}
        elif isinstance(receiver, ast.Name):
            commands |= parser_commands.get(receiver.id, set())
        for attr, handler in handlers.items():
            for command in commands:
                mappings.setdefault(command, set()).add(handler)
            callback_attrs.add(attr)

    invoked_attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            invoked_attrs.add(node.func.attr)
    if not callback_attrs & invoked_attrs:
        return {}
    return mappings


def _runner_binding_rows(package_root, callback_files, errs):
    """生产 callback router 存在时，读取 canonical adapter → 真实实现绑定。"""
    if not callback_files:
        return []
    path = os.path.join(package_root, "runner_binding.json")
    if not os.path.isfile(path):
        errs.append("[CAUSE:M8.STAGE_BINDING.ADAPTER_UNBOUND] 检出 production callback "
                    "router，但缺 runner_binding.json；无法证明 canonical adapter 调用真实实现")
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errs.append(f"runner_binding.json 不可读: {error}")
        return []
    if not isinstance(data, dict) or data.get("runner_binding_version") != "1.0" or \
            not isinstance(data.get("bindings"), list):
        errs.append("runner_binding.json 须为 version=1.0 且 bindings 为数组")
        return []
    rows = data["bindings"]
    identities = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errs.append(f"runner_binding.bindings[{index}] 须为对象")
            continue
        required = ("stage", "adapter", "production_path", "production_sha256", "mechanism")
        missing = [key for key in required
                   if not isinstance(row.get(key), str) or not row[key].strip()]
        if missing:
            errs.append(f"runner_binding.bindings[{index}] 缺非空字段 {missing}")
        identities.append((row.get("stage"), row.get("adapter")))
    duplicates = sorted({identity for identity in identities if identities.count(identity) > 1})
    if duplicates:
        errs.append(f"runner_binding stage/adapter 身份重复 {duplicates}")
    return rows


def _adapter_closure_mutations(package_root, adapter_full, roots,
                               production_full, production_symbols):
    """Follow package-local adapter helpers; only production symbols may mutate."""
    package_root = os.path.realpath(package_root)
    production_key = os.path.realpath(production_full)
    todo = [(os.path.realpath(adapter_full), root) for root in roots]
    seen, cache, hits = set(), {}, []
    while todo:
        path, symbol = todo.pop()
        key = (os.path.realpath(path), symbol)
        if key in seen:
            continue
        seen.add(key)
        if key[0] == production_key and symbol in production_symbols:
            continue
        if path not in cache:
            try:
                with open(path, encoding="utf-8") as handle:
                    cache[path] = ast.parse(handle.read())
            except (OSError, SyntaxError) as error:
                hits.append(f"unparseable:{os.path.relpath(path, package_root)}::{error}")
                continue
        tree = cache[path]
        funcs = _local_funcs(tree)
        fn = funcs.get(symbol)
        if fn is None:
            hits.append(f"missing:{os.path.relpath(path, package_root)}::{symbol}")
            continue
        live = _live_function(fn, _module_static_env(tree))
        sub = ast.Module(body=[live], type_ignores=[])
        rel = os.path.relpath(path, package_root).replace(os.sep, "/")
        if _has_mutating_adapter_io(sub):
            hits.append(f"{rel}::{symbol}")
        higher_order = set()
        for node in ast.walk(sub):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            dynamic_value = (isinstance(value, (ast.Lambda, ast.Attribute)) or
                             (isinstance(value, ast.Call) and _call_name(value) in {
                                 "partial", "partialmethod", "methodcaller", "attrgetter",
                                 "itemgetter", "getattr", "import_module", "__import__"}))
            if dynamic_value:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                higher_order |= {item.id for target in targets for item in ast.walk(target)
                                 if isinstance(item, ast.Name)}
        if any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
               node.func.id in higher_order for node in ast.walk(sub)):
            hits.append(f"{rel}::{symbol}->higher_order_callable")

        imports, direct = {}, {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name.split(".", 1)[0]] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name != "*":
                        direct[alias.asname or alias.name] = (node.module, alias.name)
        for call in (node for node in ast.walk(sub) if isinstance(node, ast.Call)):
            call_name = _call_name(call)
            if call_name in {"import_module", "__import__", "getattr", "setattr",
                             "__getattribute__", "vars", "dir", "attrgetter", "itemgetter",
                             "partial", "partialmethod", "methodcaller",
                             "eval", "exec", "compile", "globals", "locals"} or \
                    not isinstance(call.func, (ast.Name, ast.Attribute)):
                hits.append(f"{rel}::{symbol}->dynamic_route:{call_name or 'indirect_callee'}")
                continue
            target_path = target_symbol = None
            if isinstance(call.func, ast.Name):
                if call.func.id in funcs:
                    target_path, target_symbol = path, call.func.id
                elif call.func.id in direct:
                    module, target_symbol = direct[call.func.id]
                    target_path = _resolve_package_module(package_root, path, module)
            elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                module = imports.get(call.func.value.id)
                if module:
                    target_path = _resolve_package_module(package_root, path, module)
                    target_symbol = call.func.attr
            if target_path and target_symbol:
                todo.append((target_path, target_symbol))
    return sorted(set(hits))


def _adapter_binding_errors(package_root, stage, candidates, parsed, rows):
    """验证 adapter 的真实生产调用可达；只出现路径/复制业务逻辑均不放行。"""
    errors = []
    candidate_names = {candidate[0] for candidate in candidates}
    selected = [row for row in rows
                if isinstance(row, dict) and row.get("stage") == stage and
                os.path.basename(row.get("adapter", "")) in candidate_names]
    if not selected:
        return [f"[CAUSE:M8.STAGE_BINDING.ADAPTER_UNBOUND] 段 {stage} 的 canonical adapter "
                f"{sorted(candidate_names)} 没有 runner_binding.json 生产绑定"]
    valid = False
    for row in selected:
        adapter_rel = row["adapter"].replace("\\", "/")
        production_rel = row["production_path"].replace("\\", "/")
        adapter_full, adapter_inside = _contained(package_root, adapter_rel)
        production_full, production_inside = _contained(package_root, production_rel)
        if not adapter_inside or not production_inside or not os.path.isfile(production_full):
            errors.append(f"段 {stage} 的 adapter/production_path 不在包内或生产文件不存在")
            continue
        if os.path.realpath(adapter_full) == os.path.realpath(production_full):
            errors.append(f"段 {stage} 的 adapter 与 production_path 不得是同一文件")
            continue
        if row.get("production_sha256") != _file_sha256(production_full):
            errors.append(f"段 {stage} 的 production_sha256 与 {production_rel} 不符")
            continue
        try:
            with open(production_full, encoding="utf-8") as handle:
                production_tree = ast.parse(handle.read())
        except (OSError, SyntaxError) as error:
            errors.append(f"段 {stage} 的 production_path 不可解析: {error}")
            continue
        production_callbacks = _argparse_callback_dispatch(
            production_tree, _bindings(production_tree))
        commands = row.get("production_commands", [])
        symbols = row.get("symbols", [])
        if production_callbacks:
            if (not isinstance(commands, list) or not commands or
                    not all(isinstance(command, str) and command for command in commands) or
                    len(set(commands)) != len(commands)):
                errors.append(f"段 {stage} 绑定 callback router 时须声明唯一非空 production_commands")
                continue
            unknown = sorted(set(commands) - set(production_callbacks))
            expected_symbols = set().union(
                *(production_callbacks[command] for command in commands
                  if command in production_callbacks))
            if unknown:
                errors.append(f"段 {stage} 的 production_commands 不在真实 callback topology: {unknown}")
                continue
            if not isinstance(symbols, list) or set(symbols) != expected_symbols or \
                    len(symbols) != len(set(symbols)):
                errors.append(f"段 {stage} 的 symbols 必须精确等于 callback handlers "
                              f"{sorted(expected_symbols)}，不得绑定无害 helper")
                continue
            if stage in production_callbacks and set(commands) != {stage}:
                errors.append(f"段 {stage} 与 production command 同名时必须一对一绑定该 command")
                continue
        name = os.path.basename(adapter_rel)
        if name not in parsed:
            errors.append(f"段 {stage} 的 adapter {adapter_rel} 不在 M8 执行脚本集合")
            continue
        tree, _bindings_map, _has_stage, _has_rundir, dispatch, _callbacks = parsed[name]
        roots = dispatch.get(stage, set())
        if not roots:
            errors.append(f"段 {stage} 的 adapter {adapter_rel} 没有可达 stage handler")
            continue
        mechanism = row.get("mechanism")
        if mechanism == "runpy":
            funcs = _local_funcs(tree)
            module_env = _module_static_env(tree)
            reachable = _reachable_local_functions(tree, roots)
            sub = ast.Module(body=[_live_function(funcs[item], module_env)
                                   for item in sorted(reachable)], type_ignores=[])
            has_runpy = any(isinstance(node, ast.Call) and _call_name(node) == "run_path"
                            for node in ast.walk(sub))
            basename = os.path.basename(production_rel)
            mentions_path = basename in _str_constants(sub)
            if not has_runpy or not mentions_path:
                errors.append(f"段 {stage} 的 adapter 未从 handler 可达 runpy.run_path({production_rel})")
                continue
            if production_callbacks and not set(commands).issubset(set(_str_constants(sub))):
                errors.append(f"段 {stage} 的 adapter 未从 handler 可达全部 production_commands {commands}")
                continue
        elif mechanism == "module_call":
            if not symbols:
                errors.append(f"段 {stage} 的 module_call 须声明 production symbols")
                continue
            fact_errors = []
            facts = _runner_binding_facts(
                adapter_full,
                [{"path": production_rel, "sha256": row["production_sha256"],
                  "symbols": symbols}], fact_errors, require_full_coverage=False)
            if fact_errors or not facts:
                errors.extend(f"段 {stage}: {error}" for error in fact_errors)
                continue
            # _runner_binding_facts 验全文件；再要求调用位于本 stage 可达 handler。
            module = os.path.splitext(os.path.basename(production_rel))[0]
            funcs = _local_funcs(tree)
            module_env = _module_static_env(tree)
            reachable = _reachable_local_functions(tree, roots)
            sub = ast.Module(body=[_live_function(funcs[item], module_env)
                                   for item in sorted(reachable)], type_ignores=[])
            imported_modules = {}
            imported_symbols = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules[alias.asname or alias.name.split(".", 1)[0]] = alias.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        if alias.name != "*":
                            imported_symbols[alias.asname or alias.name] = (node.module, alias.name)
            calls = [node.func for node in ast.walk(sub) if isinstance(node, ast.Call)]
            reachable_symbols = {
                symbol for symbol in symbols if any(
                    (isinstance(func, ast.Name) and func.id in imported_symbols and
                     imported_symbols[func.id][0].split(".")[-1] == module and
                     imported_symbols[func.id][1] == symbol) or
                    (isinstance(func, ast.Attribute) and func.attr == symbol and
                     isinstance(func.value, ast.Name) and func.value.id in imported_modules and
                     imported_modules[func.value.id].split(".")[-1] == module)
                    for func in calls)}
            if reachable_symbols != set(symbols):
                errors.append(f"段 {stage} 的生产 symbol 调用不在本 stage handler 可达路径")
                continue
        else:
            errors.append(f"段 {stage} 的 runner binding mechanism 仅允许 runpy/module_call")
            continue
        # 任何 callback-router adapter 都必须保持薄委派：真实 handler 直接收到
        # 调用方 run-dir，adapter 及其包内 helper 不得另写业务产物。stage 名可与
        # production command 不同，不能用命名差异逃过这条约束。
        if production_callbacks:
            if mechanism != "module_call":
                errors.append(f"段 {stage} 的一对一 callback adapter 必须用 module_call 直接委派")
                continue
            if _has_mutating_adapter_io(sub):
                errors.append(f"段 {stage} 的薄 adapter 自己包含写盘；业务产物须由真实 callback handler 生成")
                continue
            closure_mutations = _adapter_closure_mutations(
                package_root, adapter_full, roots, production_full, set(symbols))
            if closure_mutations:
                errors.append(f"段 {stage} 的薄 adapter 包内 helper 闭包包含写盘 "
                              f"{closure_mutations}；只允许绑定的真实 callback 生成业务产物")
                continue
            root_params = {
                arg.arg for root in roots if root in funcs
                for arg in (list(funcs[root].args.posonlyargs) + list(funcs[root].args.args) +
                            list(funcs[root].args.kwonlyargs))
                if "run_dir" in arg.arg or arg.arg in {"output_dir", "work_dir"}}
            direct_forward = False
            for node in ast.walk(sub):
                if not isinstance(node, ast.Call):
                    continue
                callee = node.func
                is_production = (
                    isinstance(callee, ast.Name) and callee.id in imported_symbols and
                    imported_symbols[callee.id][1] in symbols) or (
                    isinstance(callee, ast.Attribute) and callee.attr in symbols and
                    isinstance(callee.value, ast.Name) and callee.value.id in imported_modules)
                if not is_production:
                    continue
                direct_values = list(node.args) + [kw.value for kw in node.keywords]
                for value in direct_values:
                    if isinstance(value, ast.Name) and value.id in root_params:
                        direct_forward = True
                    if isinstance(value, ast.Call):
                        for keyword in value.keywords:
                            if keyword.arg in {"run_dir", "output_dir", "work_dir"} and \
                                    isinstance(keyword.value, ast.Name) and keyword.value.id in root_params:
                                direct_forward = True
            if not direct_forward:
                errors.append(f"段 {stage} 的真实 callback 未直接收到调用方 run-dir；禁止改写到丢弃目录")
                continue
        if production_callbacks:
            aggregate = set()
            for binding in rows:
                if isinstance(binding, dict) and \
                        binding.get("production_path", "").replace("\\", "/") == production_rel:
                    aggregate.update(binding.get("symbols", []))
            all_handlers = set().union(*production_callbacks.values())
            if aggregate != all_handlers:
                errors.append(f"production router {production_rel} 的跨 stage symbols 合集须精确覆盖 "
                              f"{sorted(all_handlers)}，实为 {sorted(aggregate)}")
                continue
        valid = True
    if not valid and not errors:
        errors.append(f"段 {stage} 没有有效生产实现绑定")
    return errors


def _static_truth(node, env, depth=4, seen=None):
    """安全求一个表达式的静态真假；未知返回 None。

    这里只实现控制流裁剪所需的小子集，不执行任意 Python：字面量、单次绑定、
    ``not`` 与 ``and/or`` 的真假短路。后两类允许在部分操作数未知时仍推出必然
    结果，例如 ``run_dir and False`` 必为假。
    """
    if depth < 0:
        return None
    seen = seen or set()
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, ast.Name) and node.id in env and node.id not in seen:
        value = env[node.id]
        if isinstance(value, bool):
            return value
        return _static_truth(value, env, depth - 1, seen | {node.id})
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _static_truth(node.operand, env, depth - 1, seen)
        return None if value is None else not value
    if isinstance(node, ast.BoolOp):
        values = [_static_truth(value, env, depth - 1, seen)
                  for value in node.values]
        if isinstance(node.op, ast.And):
            if any(value is False for value in values):
                return False
            return True if all(value is True for value in values) else None
        if isinstance(node.op, ast.Or):
            if any(value is True for value in values):
                return True
            return False if all(value is False for value in values) else None
    return None


def _record_static_binding(stmt, env):
    """把顺序执行后仍可静态判真的简单名字绑定写入 env。"""
    # 先清掉本语句会绑定的全部名字；解构等不能静态求值的重绑定也不能让
    # 旧常量继续越过当前位置。
    _invalidate_assigned(stmt, env)
    targets, value = [], None
    if isinstance(stmt, ast.Assign):
        targets, value = stmt.targets, stmt.value
    elif isinstance(stmt, ast.AnnAssign):
        targets, value = [stmt.target], stmt.value
    elif isinstance(stmt, ast.AugAssign):
        targets = [stmt.target]
    names = [target.id for target in targets if isinstance(target, ast.Name)]
    if not names:
        return
    truth = _static_truth(value, env) if value is not None else None
    for name in names:
        if truth is None:
            env.pop(name, None)
        else:
            env[name] = truth


def _bound_names(node):
    """取一个语句在当前作用域绑定的名字，不钻进嵌套函数/类的函数体。"""
    names = set()

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, item):
            if isinstance(item.ctx, (ast.Store, ast.Del)):
                names.add(item.id)

        def _visit_signature(self, item):
            values = list(item.args.defaults)
            values += [value for value in item.args.kw_defaults if value is not None]
            values += list(item.decorator_list)
            if item.returns is not None:
                values.append(item.returns)
            for value in values:
                self.visit(value)

        def visit_FunctionDef(self, item):
            names.add(item.name)
            self._visit_signature(item)

        def visit_AsyncFunctionDef(self, item):
            names.add(item.name)
            self._visit_signature(item)

        def visit_ClassDef(self, item):
            names.add(item.name)
            for value in list(item.bases) + list(item.decorator_list):
                self.visit(value)
            for keyword in item.keywords:
                self.visit(keyword.value)

        def visit_Lambda(self, item):
            values = list(item.args.defaults)
            values += [value for value in item.args.kw_defaults if value is not None]
            for value in values:
                self.visit(value)

        def visit_Import(self, item):
            for alias in item.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])

        def visit_ImportFrom(self, item):
            for alias in item.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)

        def visit_ExceptHandler(self, item):
            if item.name:
                names.add(item.name)
            if item.type is not None:
                self.visit(item.type)
            for child in item.body:
                self.visit(child)

        def visit_MatchAs(self, item):
            if item.name:
                names.add(item.name)
            if item.pattern is not None:
                self.visit(item.pattern)

        def visit_MatchStar(self, item):
            if item.name:
                names.add(item.name)

    Visitor().visit(node)
    return names


def _invalidate_assigned(node, env):
    """当前作用域内出现过的绑定名一律退回未知，避免旧常量越界传播。"""
    for name in _bound_names(node):
        env.pop(name, None)


def _function_static_env(fn, inherited):
    """移除会被参数/局部名遮蔽的模块常量，只保留函数入口可见值。"""
    env = dict(inherited or {})
    args = list(fn.args.posonlyargs) + list(fn.args.args) + list(fn.args.kwonlyargs)
    if fn.args.vararg is not None:
        args.append(fn.args.vararg)
    if fn.args.kwarg is not None:
        args.append(fn.args.kwarg)
    local = {arg.arg for arg in args}
    globals_, nonlocals = set(), set()

    class Declarations(ast.NodeVisitor):
        def visit_Global(self, item):
            globals_.update(item.names)

        def visit_Nonlocal(self, item):
            nonlocals.update(item.names)

        # 嵌套作用域的 global/nonlocal 不属于当前函数。
        def visit_FunctionDef(self, item):
            return

        def visit_AsyncFunctionDef(self, item):
            return

        def visit_ClassDef(self, item):
            return

        def visit_Lambda(self, item):
            return

    declarations = Declarations()
    for stmt in fn.body:
        local |= _bound_names(stmt)
        declarations.visit(stmt)
    for name in (local - globals_) | nonlocals:
        env.pop(name, None)
    return env


def _module_static_env(tree):
    """模块顶层、按源码顺序可静态判真的简单常量绑定。"""
    env = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            _record_static_binding(stmt, env)
        else:
            _invalidate_assigned(stmt, env)
    return env


def _reachable_local_functions(tree, roots):
    """从给定本地函数根沿直接调用边求可达函数集合。"""
    funcs = _local_funcs(tree)
    module_env = _module_static_env(tree)
    seen, todo = set(), [name for name in roots if name in funcs]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for n in ast.walk(_live_function(funcs[name], module_env)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and \
                    n.func.id in funcs and n.func.id not in seen:
                todo.append(n.func.id)
    return seen


def _prune_dead_stmts(stmts, inherited=None):
    """裁掉静态假分支与 return/raise 后语句，供静态可达性判定。

    条件可沿模块/函数内的简单绑定跟四跳，并识别 ``not`` 与布尔短路；因此
    ``enabled=False; if enabled`` 与 ``if run_dir and False`` 不会退化成可达。
    """
    env = dict(inherited or {})
    out = []
    for st in stmts:
        truth = _static_truth(st.test, env) if isinstance(st, (ast.If, ast.While)) else None
        if isinstance(st, ast.If) and truth is not None:
            chosen = st.body if truth else st.orelse
            out.extend(_prune_dead_stmts(chosen, env))
            for child in chosen:
                _invalidate_assigned(child, env)
            continue
        if isinstance(st, ast.While) and truth is False:
            out.extend(_prune_dead_stmts(st.orelse, env))
            for child in st.orelse:
                _invalidate_assigned(child, env)
            continue
        node = copy.deepcopy(st)
        for field in ("body", "orelse", "finalbody"):
            if hasattr(node, field):
                setattr(node, field, _prune_dead_stmts(getattr(node, field), env))
        if isinstance(node, ast.Try):
            for h in node.handlers:
                h.body = _prune_dead_stmts(h.body, env)
        if hasattr(ast, "Match") and isinstance(node, ast.Match):
            for case in node.cases:
                case.body = _prune_dead_stmts(case.body, env)
        out.append(node)
        if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            _record_static_binding(st, env)
        else:
            _invalidate_assigned(st, env)
        if isinstance(st, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            break
    return out


def _live_function(fn, inherited=None):
    node = copy.deepcopy(fn)
    node.body = _prune_dead_stmts(node.body, _function_static_env(fn, inherited))
    return node


def _writes_artifact_reachable(tree, artifact, roots):
    """产物写调用须从本段 handler/main 可达；死函数里的诱饵不计。"""
    funcs = _local_funcs(tree)
    module_env = _module_static_env(tree)
    reachable = _reachable_local_functions(tree, roots)
    if not reachable:
        return False
    sub = ast.Module(body=[_live_function(funcs[name], module_env)
                           for name in sorted(reachable)],
                     type_ignores=[])
    return _writes_artifact(sub, _bindings(sub), artifact)


def _calls_write_artifact(node, artifact, funcs):
    """子树里是否有调用把产物名交给真实写调用或本地写 helper。"""
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        args = list(call.args) + [kw.value for kw in call.keywords]
        mentions = any(artifact in value for arg in args
                       for value in _str_constants(arg))
        if not mentions:
            continue
        callee = funcs.get(_call_name(call))
        helper_writes = callee is not None and any(
            isinstance(inner, ast.Call) and _is_write_call(inner)
            for inner in ast.walk(callee))
        if _is_write_call(call) or helper_writes:
            return True
    return False


def _false_branch_mechanism(test):
    """给可静态判假的条件一个稳定、与 fixture 名无关的机制名。"""
    if isinstance(test, ast.Constant):
        return "常量假分支"
    if isinstance(test, ast.Name):
        return "绑定常量假分支"
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return "一元取反假分支"
    if isinstance(test, ast.BoolOp):
        return "逻辑短路假分支"
    return "静态常量假分支"


def _dead_artifact_shapes_in_stmts(stmts, artifact, funcs, inherited=None):
    """从语句序列提取常量死分支与终止语句后的产物诱饵。"""
    env = dict(inherited or {})
    shapes = set()
    for index, stmt in enumerate(stmts):
        truth = _static_truth(stmt.test, env) if isinstance(stmt, ast.If) else None
        if isinstance(stmt, ast.If) and truth is not None:
            discarded = stmt.orelse if truth else stmt.body
            if any(_calls_write_artifact(item, artifact, funcs) for item in discarded):
                shapes.add(_false_branch_mechanism(stmt.test))
        for field in ("body", "orelse", "finalbody"):
            child = getattr(stmt, field, None)
            if isinstance(child, list):
                shapes |= _dead_artifact_shapes_in_stmts(child, artifact, funcs, env)
        if isinstance(stmt, ast.Try):
            for handler in stmt.handlers:
                shapes |= _dead_artifact_shapes_in_stmts(
                    handler.body, artifact, funcs, env)
        if hasattr(ast, "Match") and isinstance(stmt, ast.Match):
            for case in stmt.cases:
                shapes |= _dead_artifact_shapes_in_stmts(
                    case.body, artifact, funcs, env)
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            _record_static_binding(stmt, env)
        else:
            _invalidate_assigned(stmt, env)
        if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            tail = stmts[index + 1:]
            if any(_calls_write_artifact(item, artifact, funcs) for item in tail):
                shapes.add("return 后语句" if isinstance(stmt, ast.Return)
                           else "终止语句后")
            break
    return shapes


def _dead_artifact_shapes(tree, artifact, roots):
    """给不可达写盘失败生成与 fixture 名无关的稳定机制说明。"""
    funcs = _local_funcs(tree)
    module_env = _module_static_env(tree)
    reachable = _reachable_local_functions(tree, roots)
    shapes = set()
    if any(name not in reachable and _calls_write_artifact(fn, artifact, funcs)
           for name, fn in funcs.items()):
        shapes.add("死函数诱饵")
    for name in reachable:
        shapes |= _dead_artifact_shapes_in_stmts(
            funcs[name].body, artifact, funcs,
            _function_static_env(funcs[name], module_env))
    return sorted(shapes) or ["无写盘调用"]


def _sandbox_probe_command(cmd, probe_root, allow_children=False):
    """把候选代码包进 OS 隔离器；无可靠后端就 fail-closed。

    stage runner 必须单进程；audit 薄封装允许在同一沙箱内 fork/exec 可信解释器。
    两种形态都只读探针输入、只写探针根，子进程不会越过同一 OS 边界。
    """
    if sys.platform == "darwin" and os.path.isfile("/usr/bin/sandbox-exec"):
        def quote(value):
            return value.replace("\\", "\\\\").replace('"', '\\"')
        # sandbox-exec canonicalizes the path being authorized, but a ``subpath``
        # predicate written with a symlink alias (notably /tmp -> /private/tmp)
        # is not reliably canonicalized the same way.  Keeping both aliases can
        # therefore make the broad /tmp deny override the probe carve-out.  Emit
        # only real, deduplicated roots for both sides of the policy.
        probe_reads = sorted({os.path.realpath(probe_root)})
        writable = "".join(
            f'(allow file-write* (subpath "{quote(path)}"))'
            for path in probe_reads)
        protected_reads = {
            os.path.realpath(path)
            for path in {"/Users", "/Volumes", "/private/tmp", "/tmp", "/var/tmp",
                         "/etc", "/private/etc", "/private/var/db",
                         "/Library/Keychains", tempfile.gettempdir()}
        }
        # sandbox-exec gives a matching deny precedence over a later allow. A
        # probe rooted below /tmp therefore needs the exact probe roots carved
        # out of each broad deny predicate.
        read_rules = "".join(
            '(deny file-read* (require-all '
            f'(subpath "{quote(path)}")'
            + "".join(
                f'(require-not (subpath "{quote(probe)}"))'
                for probe in probe_reads)
            + '))'
            for path in sorted(protected_reads))
        read_rules += "".join(
            f'(allow file-read* (subpath "{quote(path)}"))'
            for path in probe_reads)
        # A bundled interpreter needs its own stdlib and dynamic libraries under
        # the user's cache. Grant only that runtime, never its user-directory parent.
        runtime_root = os.path.realpath(sys.base_prefix)
        if runtime_root in {"/", "/Users", os.path.realpath(os.path.expanduser("~"))}:
            return None, "Python runtime 根过宽，不能加入沙箱读白名单"
        read_rules += f'(allow file-read* (subpath "{quote(runtime_root)}"))'
        for executable in {cmd[0], os.path.realpath(cmd[0])}:
            read_rules += f'(allow file-read* (literal "{quote(executable)}"))'
        process_rule = '' if allow_children else '(deny process-fork)'
        profile = ('(version 1)(allow default)(deny network*)(deny file-write*)'
                   + process_rule +
                   '(deny signal (target others))'
                   '(deny process-info*)(allow process-info* (target self))'
                   '(deny mach-lookup)'
                   + writable
                   + read_rules)
        return ["/usr/bin/sandbox-exec", "-p", profile, *cmd], "macOS sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("bwrap"):
        hardened, reason = _linux_probe_command(
            cmd, probe_root, shutil.which("bwrap"), allow_children=allow_children)
        if hardened:
            return hardened, "Linux bubblewrap+seccomp"
        return None, reason
    return None, "无可用 OS 隔离后端（macOS sandbox-exec / Linux bubblewrap）"


def _linux_seccomp_launcher(cmd, probe_root):
    """生成先装 seccomp 再 runpy 的 Linux 启动器；拒绝 fork、网络与信号 syscall。"""
    machine = os.uname().machine.lower()
    policy = {
        "x86_64": [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 53, 54, 55,
                   56, 57, 58, 59, 62, 200, 234, 288, 322, 435],
        "amd64": [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 53, 54, 55,
                  56, 57, 58, 59, 62, 200, 234, 288, 322, 435],
        "aarch64": [129, 130, 131, 198, 199, 200, 201, 202, 203, 204,
                    205, 206, 207, 208, 209, 210, 211, 212, 220, 221, 242,
                    281, 435],
        "arm64": [129, 130, 131, 198, 199, 200, 201, 202, 203, 204,
                  205, 206, 207, 208, 209, 210, 211, 212, 220, 221, 242,
                  281, 435],
    }.get(machine)
    audit_arch = {"x86_64": 0xC000003E, "amd64": 0xC000003E,
                  "aarch64": 0xC00000B7, "arm64": 0xC00000B7}.get(machine)
    if not policy or audit_arch is None:
        return None, f"Linux 架构 {machine} 无已登记 seccomp syscall 表"
    launcher = os.path.join(probe_root, "linux_probe_bootstrap.py")
    source = f'''# generated inside the disposable M8 probe root
import ctypes
import errno
import runpy
import sys

class SockFilter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]

class SockFprog(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort),
                ("filter", ctypes.POINTER(SockFilter))]

denied = {policy!r}
rules = [SockFilter(0x20, 0, 0, 4),
         SockFilter(0x15, 1, 0, {audit_arch}),
         SockFilter(0x06, 0, 0, 0x80000000),
         SockFilter(0x20, 0, 0, 0)]
for number in denied:
    rules.append(SockFilter(0x15, 0, 1, number))
    rules.append(SockFilter(0x06, 0, 0, 0x00050000 | errno.EPERM))
rules.append(SockFilter(0x06, 0, 0, 0x7fff0000))
array = (SockFilter * len(rules))(*rules)
program = SockFprog(len(rules), array)
libc = ctypes.CDLL(None, use_errno=True)
libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                       ctypes.c_ulong, ctypes.c_ulong]
if libc.prctl(38, 1, 0, 0, 0) != 0:
    raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
program_ptr = ctypes.cast(ctypes.byref(program), ctypes.c_void_p).value
if libc.prctl(22, 2, program_ptr, 0, 0) != 0:
    raise OSError(ctypes.get_errno(), "PR_SET_SECCOMP")
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
'''
    try:
        with open(launcher, "w", encoding="utf-8") as handle:
            handle.write(source)
    except OSError as error:
        return None, f"Linux seccomp 启动器生成失败: {error}"
    return [cmd[0], launcher, *cmd[1:]], None


def _linux_probe_command(cmd, probe_root, bwrap, allow_children=False):
    """构造空根 bubblewrap + PID/网络 namespace + 进程内 seccomp 的 Linux 探针。"""
    executable = os.path.realpath(cmd[0])
    sensitive = ("/home", "/root", "/Users", "/media", "/mnt")
    if executable == "/" or any(
            executable == root or executable.startswith(root + os.sep)
            for root in sensitive):
        return None, "Linux 探针 Python 位于敏感用户路径，拒绝把该路径挂入沙箱"
    if allow_children:
        # audit.py may be a thin wrapper that execs the trusted interpreter.
        # PID/network namespaces + empty mount root + RLIMIT_NPROC retain the
        # boundary; the stage path keeps seccomp's fork/exec denial.
        launcher_cmd = cmd
    else:
        launcher_cmd, error = _linux_seccomp_launcher(cmd, probe_root)
        if not launcher_cmd:
            return None, error

    roots = []
    for path in ("/usr", "/bin", "/lib", "/lib64",
                 sys.base_prefix, sys.prefix):
        real = os.path.realpath(path)
        if real != "/" and os.path.exists(real) and real not in roots:
            roots.append(real)
    if not any(executable == root or executable.startswith(root + os.sep)
               for root in roots):
        return None, "Linux 探针 Python 不在可安全只读挂载的系统运行时根内"

    command = [bwrap, "--die-with-parent", "--new-session", "--unshare-all",
               "--disable-userns", "--cap-drop", "ALL", "--proc", "/proc",
               "--dir", "/dev"]
    # 空 mount namespace 只暴露解释器/动态链接运行时；不再 ro-bind 主机根目录。
    for root in sorted(roots):
        command += ["--ro-bind", root, root]
    for path in ("/etc/ld.so.cache", "/etc/ld.so.conf", "/etc/ld.so.conf.d",
                 "/dev/null", "/dev/random", "/dev/urandom"):
        if os.path.exists(path):
            command += ["--ro-bind", path, path]
    command += ["--bind", probe_root, probe_root,
                "--chdir", os.path.join(probe_root, "package"),
                "--", *launcher_cmd]
    return command, None


def _uid_process_limit():
    """给当前 uid 已有进程数留 32 个探针余量；取不到就不碰 RLIMIT_NPROC。"""
    try:
        output = subprocess.check_output(
            ["/bin/ps", "-U", str(os.getuid()), "-o", "pid="],
            text=True, timeout=5)
        return max(32, len(output.splitlines()) + 32)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _probe_limits(nproc_limit=None):
    """限制真跑探针的 CPU、单文件与进程数；失败时仍由 OS sandbox 兜边界。"""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024,
                                                   16 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        if nproc_limit is not None and hasattr(resource, "RLIMIT_NPROC"):
            _soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            limit = min(nproc_limit, hard) if hard != resource.RLIM_INFINITY else nproc_limit
            resource.setrlimit(resource.RLIMIT_NPROC, (limit, limit))
    except (ImportError, OSError, ValueError):
        pass


def _tail_text(path, limit=600):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit))
            return f.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _open_probe_capture(probe_root, filename):
    """由父进程在 probe_root 内原子新建捕获文件，不跟随任何既有路径。

    候选 runner 能写 probe_root；若它预植 symlink/普通文件，常规 ``open(...,
    "wb")`` 会跟随或截断。目录 fd + O_EXCL + O_NOFOLLOW 把“路径不存在”和
    “创建并打开”合为一个原子动作，且后续只从这个已打开 fd 回读。
    """
    if filename != os.path.basename(filename):
        raise OSError(errno.EINVAL, "capture name must be a basename")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OSError(errno.ENOTSUP, "O_NOFOLLOW unavailable")
    root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    root_fd = os.open(probe_root, root_flags)
    try:
        fd = os.open(
            filename,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
            dir_fd=root_fd,
        )
    finally:
        os.close(root_fd)
    return os.fdopen(fd, "w+b")


def _capture_text(handle, limit=None):
    """只从父进程持有的捕获 fd 回读，拒绝退出后按路径重开。"""
    handle.flush()
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    if limit is None:
        handle.seek(0)
        data = handle.read(2 * 1024 * 1024)
    else:
        handle.seek(max(0, size - limit))
        data = handle.read(limit)
    return data.decode("utf-8", errors="replace").strip()


def _isolated_command(cmd, probe_root, cwd, env, label, timeout=30,
                      allow_children=False):
    """在同一探针边界内跑一条命令；返回 (rc, 稳定说明, stdout)。"""
    sandboxed, backend = _sandbox_probe_command(
        cmd, probe_root, allow_children=allow_children)
    if not sandboxed:
        return None, backend, ""
    stdout_path = os.path.join(probe_root, f"{label}_stdout.txt")
    stderr_path = os.path.join(probe_root, f"{label}_stderr.txt")
    try:
        stdout = _open_probe_capture(probe_root, os.path.basename(stdout_path))
        try:
            stderr = _open_probe_capture(probe_root, os.path.basename(stderr_path))
        except OSError:
            stdout.close()
            raise
    except OSError as exc:
        kind = ("preoccupied_or_symlink"
                if exc.errno in {errno.EEXIST, errno.ELOOP} else
                "secure_capture_unavailable")
        return None, f"{backend}:输出捕获拒绝 kind={kind}", ""
    with stdout, stderr:
        nproc_limit = _uid_process_limit()
        try:
            process = subprocess.Popen(
                sandboxed, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                start_new_session=True,
                preexec_fn=lambda: _probe_limits(nproc_limit))
        except OSError as exc:
            return None, f"{backend}:探针启动失败 kind={type(exc).__name__}", ""
        try:
            rc = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                process.kill()
            process.wait()
            return None, f"{backend}:运行超时 {timeout}s", ""
        # 主进程退出后不允许遗留同组后台任务。
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        # runner 可在执行中 unlink/relink 捕获路径；只读仍由父进程持有的 fd，
        # 不按名字重开，因而不会跟随它退出前植入的新 symlink。
        output = _capture_text(stdout)
        detail = _capture_text(stderr, 600) or _capture_text(stdout, 600)
    return rc, f"{backend}:{detail}" if detail else backend, output


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_file_hashes(root):
    """给探针输入做不可变快照；symlink 也进入身份，不被静默跟随。"""
    rows = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            rows[rel] = ("symlink:" + os.readlink(path) if os.path.islink(path)
                         else _file_sha256(path))
    return rows


def _runtime_stage_assertions(probe_root, run_dir, stage, assertion_specs,
                              contract_path, env, source_path=None):
    """用验证器自带解释器重放本段断言，不执行包内 audit.py。"""
    trusted = os.path.join(probe_root, "trusted_stage_audit")
    scripts = os.path.join(trusted, "scripts")
    refs = os.path.join(trusted, "references")
    os.makedirs(scripts)
    os.makedirs(refs)
    audit_copy = os.path.join(scripts, "audit.py")
    contract_copy = os.path.join(trusted, "assertions.json")
    shutil.copyfile(os.path.join(HERE, "audit.py"), audit_copy)
    shutil.copyfile(IR_PATH, os.path.join(refs, "contract_ir.json"))
    shutil.copyfile(contract_path, contract_copy)
    cmd = [sys.executable, audit_copy, run_dir, "--stage", stage,
           "--contract", contract_copy, "--json"]
    if source_path and os.path.isfile(source_path):
        source_copy = os.path.join(trusted, "source.md")
        shutil.copyfile(source_path, source_copy)
        cmd += ["--source", source_copy]
    rc, detail, output = _isolated_command(
        cmd, probe_root, trusted, env, "stage_audit")
    if rc is None:
        if "输出捕获拒绝" in detail:
            return False, f"outcome=capture_preoccupied {detail}"
        return False, f"outcome=audit_error {detail}"
    try:
        payload = json.loads(output)
        rows = payload["rows"]
    except (ValueError, KeyError, TypeError):
        return False, f"outcome=audit_error rc={rc} 可信解释器无合法 JSON 输出"
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return False, "outcome=audit_error 可信解释器 rows 非对象数组"
    expected = {spec["id"]: spec.get("tier") for spec in assertion_specs}
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        return False, ("outcome=audit_error 可信解释器断言身份不闭合 "
                       f"expected={sorted(expected)} actual={sorted(str(x) for x in ids)}")
    statuses = {row["id"]: row.get("status") for row in rows}
    bad = []
    for aid, tier in expected.items():
        status = statuses.get(aid)
        # 没有独立 source 时，T2 的 UNVERIFIED 是如实披露；T0/T1 必须 PASS。
        if status != "PASS" and not (tier == 2 and not source_path and
                                      status == "UNVERIFIED"):
            bad.append(f"{aid}={status}")
    if rc != 0 or bad:
        return False, (f"outcome=assertions_failed rc={rc} "
                       f"non_pass={sorted(bad)}")
    return True, "assertions=PASS"


def _runtime_failure_kind(detail):
    """把动态 traceback 压成稳定机制，避免临时路径污染诊断 witness。"""
    if "AssertionError" in detail:
        return "assertion_error"
    if "/dev/null" in detail and ("PermissionError" in detail or
                                  "Read-only file system" in detail or
                                  "OSError" in detail):
        return "sandbox_file_write_denied"
    if "PermissionError" in detail and ("socket.socket" in detail or "sock.bind" in detail):
        return "sandbox_network_denied"
    if "PermissionError" in detail and "os.kill" in detail:
        return "sandbox_signal_denied"
    if "PermissionError" in detail and ("subprocess" in detail or "fork_exec" in detail):
        return "sandbox_fork_denied"
    if "PermissionError" in detail:
        return "sandbox_denied"
    matches = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\b", detail)
    return (matches[-1] if matches else "nonzero_exit").lower()


def _runtime_stage_probe(folder, candidate, stage, artifacts, assertion_specs,
                         contract_path):
    """隔离真跑一段，并验输入不可变、产物可解析及本段 T0/T1 断言。"""
    name, _tree, _roots, mode = candidate
    try:
        with tempfile.TemporaryDirectory(prefix="m8_stage_probe_") as probe_root:
            package = os.path.join(probe_root, "package")
            shutil.copytree(
                folder, package,
                ignore=shutil.ignore_patterns("GATE_INJECTION.json", "INJECTION.json",
                                              "__pycache__", "*.pyc"))
            run_dir = os.path.join(probe_root, "run")
            os.makedirs(run_dir)
            goldens = sorted(path for path in glob.glob(
                os.path.join(package, "fixtures", "golden*")) if os.path.isdir(path))
            if goldens:
                shutil.copytree(goldens[0], run_dir, dirs_exist_ok=True)
            # manifest 是验收元数据，不是某段的上游输入。
            manifest = os.path.join(run_dir, "run_manifest.json")
            if os.path.lexists(manifest):
                os.unlink(manifest)
            # source/contract/解释器都在 runner 退出后才复制进探针；候选进程
            # 因而拿不到、也改不了可信重放材料。
            sources = sorted(glob.glob(os.path.join(folder, "fixtures", "source*.md")))
            source_path = sources[0] if len(sources) == 1 else None
            targets = []
            run_real = os.path.realpath(run_dir)
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact:
                    return False, f"产物路径非法 {artifact!r}"
                target = os.path.join(run_dir, artifact)
                target_real = os.path.realpath(target)
                if os.path.commonpath([run_real, target_real]) != run_real:
                    return False, f"产物路径逃出 run-dir: {artifact}"
                if os.path.lexists(target):
                    if os.path.isdir(target) and not os.path.islink(target):
                        shutil.rmtree(target)
                    else:
                        os.unlink(target)
                targets.append((artifact, target))

            # runner 只拿运行输入，不拿 golden/mutant 答案；否则可直接抄标准答案。
            fixtures_dir = os.path.join(package, "fixtures")
            if os.path.isdir(fixtures_dir):
                shutil.rmtree(fixtures_dir)
            upstream_before = _tree_file_hashes(run_dir)

            script = os.path.join(package, "scripts", name)
            cmd = [sys.executable, script]
            if mode == "shared":
                cmd += ["--stage", stage]
            cmd += ["--run-dir", run_dir]
            sandboxed, backend = _sandbox_probe_command(cmd, probe_root)
            if not sandboxed:
                return False, backend
            env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TZ")
                   if key in os.environ}
            env.update({"HOME": os.path.join(probe_root, "home"),
                        "TMPDIR": os.path.join(probe_root, "tmp"),
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
            os.makedirs(env["HOME"])
            os.makedirs(env["TMPDIR"])
            rc, detail, _output = _isolated_command(
                cmd, probe_root, package, env, "stage_runner")
            if rc is None:
                return False, detail
            if rc != 0:
                kind = _runtime_failure_kind(detail)
                return False, f"{backend}:运行失败 rc={rc} kind={kind}"

            after_hashes = _tree_file_hashes(run_dir)
            upstream_after = {rel: after_hashes.get(rel) for rel in upstream_before}
            mutated = sorted(rel for rel, digest in upstream_before.items()
                             if upstream_after.get(rel) != digest)
            if mutated:
                return False, f"{backend}:outcome=upstream_mutated files={mutated}"
            missing = [artifact for artifact, target in targets
                       if not os.path.isfile(target) or os.path.islink(target)]
            if missing:
                return False, f"{backend}:rc=0 但产物缺失 {missing}"
            empty = [artifact for artifact, target in targets
                     if os.path.getsize(target) == 0]
            if empty:
                return False, f"{backend}:outcome=empty_artifact files={empty}"
            invalid = []
            for artifact, target in targets:
                if artifact.lower().endswith(".json"):
                    try:
                        with open(target, encoding="utf-8") as handle:
                            json.load(handle)
                    except (OSError, UnicodeError, ValueError):
                        invalid.append(artifact)
            if invalid:
                return False, f"{backend}:outcome=invalid_json files={invalid}"

            assertions_ok, assertion_detail = _runtime_stage_assertions(
                probe_root, run_dir, stage, assertion_specs, contract_path, env,
                source_path)
            if not assertions_ok:
                upstream_hashes = set(upstream_before.values())
                copied = sorted(artifact for artifact, target in targets
                                if _file_sha256(target) in upstream_hashes)
                if copied:
                    return False, (f"{backend}:outcome=copied_upstream files={copied}; "
                                   f"{assertion_detail}")
                return False, f"{backend}:{assertion_detail}"
            return True, f"{backend}:rc=0、输入未变且本段断言 PASS"
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return False, f"隔离探针自身失败 {type(error).__name__}: {error}"


def _check_stage_binding(scripts_dir, exec_names, assertions, contract_path, errs):
    """M8 逐段绑定：每个机器段须有能**单独调起**它的入口，且该入口真落该段产物。

    Gate-ID: validate.M8.stage_binding
    Obligations: STAGE.ENTRY_BINDING
    判据源 `contract_ir.md §6.2`。本函数不内联复制该节语义，只做机械比对；
    §6.2 与本实现的同步由 `skill_drift.py` 的第四面锁住。

    为什么要能单独调起：契约的链形是「本段落盘 → 立刻跑本段断言 → 过了再进
    下一段」。一个 runner 从头跑到尾、中途无处切入，这条链就只剩首尾两点，
    中间段的断言全部退化成事后追认——错在第二段，第四段才发现，而那时前三段
    的产物已经互相污染，定位不回去。故共用 runner 必须认 `--stage`。

    为什么还要验产物：`--stage` 的 choices 里把段名写全是零成本的。
    `ap.add_argument("--stage", choices=[...]); print("ok")` 这个空壳照样过
    「认得 --stage」那一关，而它什么也没产出，段与入口的绑定是假的。故段名
    可达之外，须在中性副本 + OS sandbox 内真跑、确认输入未变，并让验证器自带
    的可信解释器重放本段断言；仅看到 artifact 文件存在不放行。静态写调用只
    负责在真跑失败后给出不可达机制，不再独自决定放行。

    两种合法绑定（二选一，无第三条兜底）：
      a) 专用脚本——文件名恰为 `run_<段名>.py`，且 AST 里真注册 `--run-dir`；
      b) 共用 runner——AST 里真注册 `--stage` 与 `--run-dir`，且存在一个被
         段选择器**实际索引并调用**的显式字典 dispatch，其键含该段名。

    三处不算：docstring / 常量里出现段名不算；只注册两个旗标不算；声明了
    STAGES 字典但没被段选择器索引调用也不算（详 `_dispatch_dict_keys`）。

    曾有第三条「单段包且只有一个执行脚本 → 自动认领」的兜底。它把判据从
    「这个入口能单独调起这一段」换成了「这个包只有一段，所以随便哪个脚本
    都算」——单段包因此永远免检，`run_stages.py` 里一段也不认也过。段数是
    包的属性，不是入口的证据。改用规则 a：单段包把脚本改名成 `run_<段名>.py`
    即合规，成本一次改名，换来的是「入口按段名认领」这条判据无例外。

    handoff 段不入本闸：那段的产出由人做，本流程内没有执行脚本可绑。
    """
    machine = []
    for st in assertions.get("stages", []):
        ops = [o for o in st.get("operations", []) if o.get("op") != "handoff"]
        arts = [o.get("artifact") for o in ops if o.get("artifact")]
        assertion_specs = [a for op in ops for a in op.get("assertions", [])]
        if arts:
            machine.append((st.get("stage", "<无名段>"), arts, assertion_specs))
    if not machine:
        return

    parsed = {}
    for name in exec_names:
        path = os.path.join(scripts_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError) as e:
            errs.append(f"scripts/{name} 不可解析: {e}")
            continue
        b = _bindings(tree)
        parsed[name] = (tree, b,
                        _takes_flag(tree, b, "--stage"),
                        _takes_flag(tree, b, "--run-dir"),
                        _dispatch_targets(tree, b),
                        _argparse_callback_dispatch(tree, b))
    if not parsed:
        return
    callback_files = sorted(name for name, values in parsed.items() if values[5])
    binding_rows = _runner_binding_rows(os.path.dirname(scripts_dir), callback_files, errs)

    for stage, arts, assertion_specs in machine:
        cands, why, why_codes = [], [], set()
        for name, (tree, b, has_stage, has_rundir, dispatch, callbacks) in sorted(parsed.items()):
            stem = os.path.splitext(name)[0]
            if stem == f"run_{stage}":                       # a) 专用脚本
                if has_rundir:
                    roots = {"main"} if "main" in _local_funcs(tree) else {stage}
                    cands.append((name, tree, roots, "dedicated"))
                else:
                    why_codes.add("M8.STAGE_BINDING.MISSING_RUN_DIR")
                    why.append(f"{name} 按段名专属，但未注册 `--run-dir`，"
                               "落盘位置不由调用方给，无从单独调起")
                continue
            if has_stage and has_rundir and stage in dispatch:   # b) 共用 runner
                cands.append((name, tree, dispatch[stage], "shared"))
                continue
            if has_stage and has_rundir:
                why_codes.add("M8.STAGE_BINDING.DISPATCH_UNBOUND")
                why.append(f"{name} 两旗标齐，但段名不在被 `--stage` 索引并调用的"
                           "字典 dispatch 键内——声明一张表不等于把控制流交给它")
            elif callbacks:
                why_codes.add("M8.STAGE_BINDING.DISPATCH_UNBOUND")
                why.append(f"{name} 使用 argparse callback production router "
                           f"{sorted(callbacks)}；它不等于 canonical `--stage`/"
                           "`--run-dir` 入口，须增加调用真实 handler/API 的薄 verification adapter")
            elif has_stage or has_rundir:
                lack = "--run-dir" if has_stage else "--stage"
                why_codes.add("M8.STAGE_BINDING.MISSING_RUN_DIR" if has_stage else
                              "M8.STAGE_BINDING.MISSING_STAGE_FLAG")
                why.append(f"{name} 未注册 `{lack}`")
            else:
                why_codes.add("M8.STAGE_BINDING.NO_RECOGNIZED_ENTRY")
        if not cands:
            tail = ("；" + "；".join(why)) if why else ""
            causes = "".join(f"[CAUSE:{code}]" for code in sorted(why_codes or {
                "M8.STAGE_BINDING.NO_RECOGNIZED_ENTRY"}))
            errs.append(f"{causes} 段 {stage} 无执行入口——脚本 {sorted(parsed)} 里没有一个"
                        f"按 `run_{stage}.py`(+--run-dir) 或 canonical `--stage` 字典 dispatch "
                        f"认领它{tail}")
            continue
        if callback_files:
            errs.extend(_adapter_binding_errors(
                os.path.dirname(scripts_dir), stage, cands, parsed, binding_rows))
        runtime = [(name, *_runtime_stage_probe(os.path.dirname(scripts_dir), candidate,
                                                stage, arts, assertion_specs,
                                                contract_path))
                   for candidate in cands for name in [candidate[0]]]
        runtime_ok = any(ok for _name, ok, _detail in runtime)
        if runtime_ok:
            continue
        for art in arts:
            static_ok = any(_writes_artifact_reachable(tree, art, roots)
                            for _, tree, roots, _mode in cands)
            if not static_ok:
                mechanisms = sorted(
                    f"{name}:{shape}"
                    for name, tree, roots, _mode in cands
                    for shape in _dead_artifact_shapes(tree, art, roots))
                errs.append("[CAUSE:M8.STAGE_BINDING.UNREACHABLE_ARTIFACT_WRITE] "
                            f"段 {stage} 的入口 {[c[0] for c in cands]} 不产出 "
                            f"{art}——从本段 handler 不可达真实写盘；"
                            f"不可达机制 {mechanisms}；隔离真跑 {runtime}")
            else:
                joined = " ".join(detail for _name, _ok, detail in runtime)
                outcome_causes = (
                    ("outcome=upstream_mutated",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.UPSTREAM_MUTATED"),
                    ("outcome=empty_artifact",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.EMPTY"),
                    ("outcome=invalid_json",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.INVALID_JSON"),
                    ("outcome=copied_upstream",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.COPIED_UPSTREAM"),
                    ("outcome=assertions_failed",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.ASSERTIONS_FAILED"),
                    ("outcome=capture_preoccupied",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.CAPTURE_PREOCCUPIED"),
                    ("outcome=audit_error",
                     "M8.STAGE_BINDING.RUNTIME_OUTPUT.AUDIT_ERROR"),
                )
                cause = next((code for marker, code in outcome_causes
                              if marker in joined),
                             "M8.STAGE_BINDING.RUNTIME_PROBE_FAILED")
                if ".RUNTIME_OUTPUT." in cause:
                    errs.append(f"[CAUSE:{cause}] 段 {stage} 现跑产物未通过本段断言 "
                                f"{art}——候选结果 {runtime}")
                else:
                    errs.append(f"[CAUSE:{cause}] 段 {stage} 隔离真跑未产出 {art}——"
                                f"候选结果 {runtime}")


def _skill_stage_names(text):
    """取围栏外真实执行段卡名。教学示例不进入 stage 闭包。"""
    return {name.strip() for _line, name, _blk in
            _card_blocks(_outside_fences(text.splitlines()))}


def _manifest_stage_sets(folder, errs):
    """读取每份 golden manifest 的 stage 集；缺 manifest 即闭包缺面。"""
    out = []
    golden_dirs = sorted(p for p in glob.glob(os.path.join(folder, "fixtures", "golden*"))
                         if os.path.isdir(p))
    if not golden_dirs:
        errs.append("stage 闭包缺 fixtures/golden* 正例目录")
        return out
    for gd in golden_dirs:
        path = os.path.join(gd, "run_manifest.json")
        rel = os.path.relpath(path, folder)
        if not os.path.isfile(path):
            errs.append(f"stage 闭包缺 {rel}")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
            stage_list = [s["stage"] for s in manifest.get("stages", [])]
            duplicates = sorted({s for s in stage_list if stage_list.count(s) > 1})
            if duplicates:
                errs.append(f"{rel} stage 名重复 {duplicates}——manifest stage 须唯一")
            stages = set(stage_list)
        except (OSError, ValueError, KeyError, TypeError) as e:
            errs.append(f"{rel} 无法解析 stage 集: {e}")
            continue
        out.append((rel, stages))
    return out


def _contract_identity_errors(assertions, errs):
    """契约身份键须非空且全局唯一；不得先丢进 set/dict 再比较。"""
    stages = assertions.get("stages", [])
    stage_names = [s.get("stage") for s in stages]
    missing_stages = [i for i, name in enumerate(stage_names) if not name]
    if missing_stages:
        errs.append(f"assertions.json stage 名为空，索引 {missing_stages}")
    duplicate_stages = sorted({s for s in stage_names if s and stage_names.count(s) > 1})
    if duplicate_stages:
        errs.append(f"assertions.json stage 名重复 {duplicate_stages}——stage 身份须唯一")

    assertion_ids = [a.get("id") for st in stages for op in st.get("operations", [])
                     for a in op.get("assertions", [])]
    missing_ids = [i for i, aid in enumerate(assertion_ids) if not aid]
    if missing_ids:
        errs.append(f"assertions.json 断言 id 为空，索引 {missing_ids}")
    duplicate_ids = sorted({aid for aid in assertion_ids
                            if aid and assertion_ids.count(aid) > 1})
    if duplicate_ids:
        errs.append(f"assertions.json 断言 id 重复 {duplicate_ids}——"
                    "重复 id 会被结果映射覆盖，断言身份须全局唯一")


def _check_stage_closure(folder, text, scripts_dir, exec_names, assertions, errs):
    """M8 四面 stage 闭包：SKILL / assertions / runner / golden manifest 精确相等。

    Gate-ID: validate.M8.stage_closure
    Obligations: STAGE.CLOSURE
    判据源 `contract_ir.md §6.3`。
    """
    skill_stages = _skill_stage_names(text)
    assertion_stages = {s.get("stage") for s in assertions.get("stages", [])
                        if s.get("stage")}
    declared = skill_stages | assertion_stages
    runner_stages = set()
    for name in exec_names:
        path = os.path.join(scripts_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError):
            continue
        bindings = _bindings(tree)
        runner_stages |= _dispatch_dict_keys(tree, bindings)
        stem = os.path.splitext(name)[0]
        if stem.startswith("run_") and stem[4:] in declared and \
                _takes_flag(tree, bindings, "--run-dir"):
            runner_stages.add(stem[4:])

    faces = [("SKILL 执行段卡", skill_stages),
             ("assertions.json", assertion_stages),
             ("runner dispatch", runner_stages)]
    faces.extend((rel, stages) for rel, stages in _manifest_stage_sets(folder, errs))
    if not skill_stages:
        errs.append("stage 闭包的 SKILL 面为空——围栏内示例不算真实执行段")
        return
    expected = skill_stages
    for label, stages in faces[1:]:
        if stages != expected:
            errs.append(f"stage 集不闭合：{label} 缺 {sorted(expected - stages)}，"
                        f"多 {sorted(stages - expected)}；SKILL={sorted(expected)}")


def check_m8(folder, text, assertions, contract_path=None, contract_issue=None,
             contract_override=False):
    """M8 · 两类脚本 + assertions.json 在位，且审核脚本真消费契约、不与执行脚本共因。

    Gate-ID: validate.M8
    Obligations: CONTRACT.DATA, STAGE.ENTRY_BINDING, STAGE.CLOSURE
    判据源 `contract_ir.md §6`、`contract_ir.md §6.2`、`contract_ir.md §6.3`。

    执行脚本与审核脚本分离：审核脚本无条件强制；执行脚本在有非 handoff
    operation 时强制（handoff 段的动作由人做，本流程内无执行脚本可写）。

    在位只是最低门槛。只验在位，一个 `print("PASS")` 的空壳 audit.py 就能过闸，
    而它恰恰是最该被拒的形态。故本闸再验三件机械可判的事：
      1. 审核脚本真的消费 assertions.json（语法树里有契约路径 / --contract /
         CONTRACT_INTERPRETER），否则断言是数据这条就没落地；
      2. 审核脚本不 import、不复制执行脚本的实现（共因防线第二条）；
      3. 每个机器段都绑到一个能单独调起、且真落该段产物的入口
         （详 `_check_stage_binding`）。
    """
    errs = []
    if assertions:
        _contract_identity_errors(assertions, errs)
    scripts_dir = os.path.join(folder, "scripts")
    if contract_issue:
        errs.append(contract_issue)
    elif not contract_path or not os.path.isfile(contract_path):
        errs.append("缺执行段断言契约（默认 assertions.json，或显式 --contract <包内路径>）")
    if not os.path.isdir(scripts_dir):
        errs.append("缺 scripts/ 目录")
        return False, errs
    names = os.listdir(scripts_dir)
    audit_path = os.path.join(scripts_dir, "audit.py")
    if "audit.py" not in names:
        errs.append("缺 scripts/audit.py（审核脚本无条件强制，源不可达也不豁免）")
    exec_names = [n for n in names if re.match(r"^run.*\.py$", n)]
    if assertions:
        ops = [o for st in assertions.get("stages", []) for o in st.get("operations", [])]
        machine_ops = [o for o in ops if o.get("op") != "handoff"]
        if machine_ops and not exec_names:
            errs.append(f"有 {len(machine_ops)} 个非 handoff operation，但 scripts/ 无 run*.py 执行脚本")
    if not os.path.isdir(os.path.join(folder, "fixtures")):
        errs.append("缺 fixtures/（审核器验收料：golden + 定向 mutant）")

    # ---- 内容面：消费契约 + 不与执行脚本共因
    if os.path.isfile(audit_path):
        try:
            with open(audit_path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError) as e:
            errs.append(f"scripts/audit.py 不可解析: {e}")
        else:
            bindings = _bindings(tree)
            if not _audit_consumes_contract(tree):
                errs.append("scripts/audit.py 未消费 assertions.json"
                            "（契约路径既未流进 open/json.load，也未随 --contract 进子进程 argv）"
                            "——断言必须是数据，不得硬编进审核器；"
                            "源码里出现过这个词不算消费")
            if contract_override and not _takes_flag(tree, bindings, "--contract"):
                errs.append("选用了显式 --contract，但 scripts/audit.py 未注册 --contract"
                            "——validate 找到契约不等于运行期审核器会消费同一份契约")
            imported = _audit_imports_exec(tree, _py_module_names(scripts_dir))
            if imported:
                errs.append(f"scripts/audit.py import 了执行脚本 {imported}"
                            "——审核器与被审对象共因，错一起错")
            shared = _shared_function_bodies(
                audit_path, [os.path.join(scripts_dir, n) for n in exec_names])
            for s in shared:
                errs.append(f"审核脚本复制了执行脚本实现: {s}——共因防线第二条")

    # ---- 逐段绑定：每个机器段都要有能单独调起、且真落该段产物的入口
    if assertions and exec_names and os.path.isdir(os.path.join(folder, "fixtures")):
        _check_stage_binding(scripts_dir, exec_names, assertions, contract_path, errs)
        _check_stage_closure(folder, text, scripts_dir, exec_names, assertions, errs)

    if errs:
        return False, errs
    rel = os.path.relpath(contract_path, os.path.realpath(folder)).replace(os.sep, "/")
    return True, ("M8 PASS: audit.py（消费契约、不与执行脚本共因）+ 执行脚本"
                  f"（逐段可单独调起、隔离真跑、输入未变且本段断言 PASS）"
                  f" + contract={rel} + fixtures/ 齐")


# 元数据件：登记面的东西，不是料本身。比对指纹时必须排除——
# mutant 按规定就得带 INJECTION.json 而 golden 不带，把它算进去的话
# 两份料永远「不同」，同料换目录名这一形态就永远抓不到。
_META_FILES = {"INJECTION.json", "GATE_INJECTION.json", "RECEIPT.json",
               "run_manifest.json", "README.md"}


def _payload_fingerprint(path):
    """料的**载荷**指纹：相对路径 + 内容一起喂进 sha256，排除元数据件。

    比「路径不同」强的地方：同一份载荷复制成两个目录名，指纹相同，当场识破。
    路径也进 hash——只喂内容的话，改文件名不改指纹。
    """
    h = hashlib.sha256()
    if os.path.isfile(path):
        h.update(os.path.basename(path).encode("utf-8"))
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:16]
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            if name in _META_FILES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, path).replace(os.sep, "/")
            h.update(rel.encode("utf-8"))
            with open(full, "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:16]


def _contained(folder, rel):
    """解析包内相对路径，返回 (真实路径, 是否仍在包内)。

    `..` 与绝对路径与符号链接都在这里被拦——包外的料不受本包审核约束，
    拿它当三条件的实物等于把判据托管给了包外的、随时可变的东西。
    """
    base = os.path.realpath(folder)
    full = os.path.realpath(os.path.join(folder, rel))
    return full, full == base or full.startswith(base + os.sep)


def _norm_heading(s):
    """标题规范化：去 # 前缀、去两端空白、全角空格折成半角、压缩连续空白。

    只做排版层归一，不做语义归一——`§配平规则` 不该匹配上 `§配平规则补遗`。
    """
    s = s.lstrip("#").strip().replace("　", " ")
    return re.sub(r"\s+", " ", s)


def _anchor_resolves(folder, anchor):
    """source_anchor 必须解析到「包内真实文件」的「真实存在的标题」。

    形如 `SKILL.md §保留规则`。旧判据是 `"§" not in anchor and ".md" not in
    anchor` —— 用 and 连接两个否定，只要沾上其中一样就过：裸 `bogus.md`
    过，裸 `§` 也过，两样都不存在也过。返回 (ok, 原因)。

    标题比对取**规范化后全等**，不取子串包含：子串会让 `§配平` 匹配上
    `§配平规则的反例`，锚点指向哪一节就变得不确定，而锚点的全部作用
    就是把断言钉到某一节具体条文上。
    """
    if not isinstance(anchor, str) or "§" not in anchor:
        return False, "缺 §节 部分（须形如 `SKILL.md §某节`）"
    fpart, _, hpart = anchor.partition("§")
    fpart, hpart = fpart.strip(), _norm_heading(hpart)
    if not fpart or not hpart:
        return False, "文件部分或节名部分为空"
    full, inside = _contained(folder, fpart)
    if not inside:
        return False, f"文件 {fpart} 逃出包外"
    if not os.path.isfile(full):
        return False, f"文件 {fpart} 不存在"
    try:
        with open(full, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        return False, f"文件 {fpart} 不可读 ({e})"
    # 标题须真的是标题行（markdown # 开头），且规范化后与锚点全等
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") and _norm_heading(s) == hpart:
            return True, ""
    return False, f"{fpart} 里没有标题「{hpart}」（须规范化后全等，不认子串）"


def _run_audit(folder, run_dir, source=None, contract_path=None):
    """跑包自己的审核脚本，取回逐条断言状态。

    为什么必须真跑：目录在位、INJECTION.json 字段齐，两个塞满垃圾的目录
    照样过闸——而三条件要的是「golden 真的 PASS、mutant 真的被那条断言
    FAIL」。收据可以手写，跑出来的判定不能。

    `source` 非空时随 `--source` 传下去：T2 族要回源比对，不给源则恒
    UNVERIFIED，指名 T2 断言的 mutant 就永远拒不了——那是「源不可达」，
    不是「断言拒了」，两者不能混。

    返回 (rows, 出错原因)。跑不动、逐条输出身份不唯一、状态非法，或退出码与
    逐条状态不一致时 rows=None，按 fail-closed 处理。
    """
    source_audit = os.path.join(folder, "scripts", "audit.py")
    if not os.path.isfile(source_audit):
        return None, "缺 scripts/audit.py，无从执行"
    try:
        with tempfile.TemporaryDirectory(prefix="m10_audit_") as probe_root:
            probe_package = os.path.join(probe_root, "package")
            # 验收料只给当前 case；其余 fixtures（尤其答案元数据）不应成为
            # 审核器的旁路输入。包的规则、references 与脚本仍完整复制。
            shutil.copytree(
                folder, probe_package, symlinks=True,
                ignore=lambda _root, names: (["fixtures"] if "fixtures" in names else []))
            probe_case = os.path.join(probe_root, "case")
            if os.path.isdir(run_dir):
                shutil.copytree(run_dir, probe_case, symlinks=True)
            else:
                os.makedirs(probe_case)
                shutil.copy2(run_dir, os.path.join(probe_case,
                                                    os.path.basename(run_dir)))

            trusted_root = os.path.join(probe_root, "trusted")
            trusted_scripts = os.path.join(trusted_root, "scripts")
            trusted_references = os.path.join(trusted_root, "references")
            os.makedirs(trusted_scripts)
            os.makedirs(trusted_references)
            trusted_audit = os.path.join(trusted_scripts, "audit.py")
            shutil.copy2(os.path.join(HERE, "audit.py"), trusted_audit)
            shutil.copy2(os.path.join(os.path.dirname(HERE), "references",
                                     "contract_ir.json"),
                         os.path.join(trusted_references, "contract_ir.json"))

            def probe_path(path, name):
                if not path:
                    return None
                real_folder = os.path.realpath(folder)
                real_path = os.path.realpath(path)
                try:
                    inside = os.path.commonpath([real_folder, real_path]) == real_folder
                except ValueError:
                    inside = False
                if inside:
                    rel = os.path.relpath(real_path, real_folder)
                    candidate = os.path.join(probe_package, rel)
                    if os.path.exists(candidate):
                        return candidate
                target = os.path.join(probe_root, name)
                if os.path.isdir(real_path):
                    shutil.copytree(real_path, target, symlinks=True)
                else:
                    shutil.copy2(real_path, target)
                return target

            probe_source = probe_path(source, "source")
            probe_contract = probe_path(contract_path, "contract.json")
            audit_path = os.path.join(probe_package, "scripts", "audit.py")
            env = dict(os.environ)
            # 外部环境不得把解释器换回探针外或换成另一份实现。
            env["CONTRACT_INTERPRETER"] = trusted_audit
            cmd = [sys.executable, audit_path, probe_case, "--all", "--json"]
            if probe_contract:
                cmd += ["--contract", probe_contract]
            if probe_source:
                cmd += ["--source", probe_source]
            rc, detail, stdout = _isolated_command(
                cmd, probe_root, probe_package, env, "m10_audit", timeout=120,
                allow_children=True)
    except (OSError, shutil.Error) as e:
        return None, ("[CAUSE:M10.AUDITOR.RUNTIME_FAILED] "
                      f"审核脚本隔离探针建立失败: {e}")
    if rc is None:
        return None, ("[CAUSE:M10.AUDITOR.RUNTIME_FAILED] "
                      f"审核脚本隔离执行失败: {detail}")
    try:
        rows = json.loads(stdout)["rows"]
    except (ValueError, KeyError, TypeError):
        denied = ("Operation not permitted" in detail or
                  "Permission denied" in detail or
                  "Read-only file system" in detail)
        if denied and "M10_AUDIT_EXTERNAL_WRITE" in detail:
            cause, label = "M10.AUDITOR.SANDBOX_WRITE", "审核脚本写入探针外"
        elif denied and "M10_AUDIT_EXTERNAL_READ" in detail:
            cause, label = "M10.AUDITOR.SANDBOX_READ", "审核脚本读取探针外"
        elif denied:
            cause, label = "M10.AUDITOR.SANDBOX_BOUNDARY", "审核脚本越出隔离边界"
        else:
            cause, label = "M10.AUDITOR.RUNTIME_FAILED", "审核脚本无 --json 逐条输出"
        return None, f"[CAUSE:{cause}] {label}（{detail[-300:]}）"
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return None, "审核输出 rows 须为对象数组"
    ids = [row.get("id") for row in rows]
    if any(not isinstance(aid, str) or not aid for aid in ids):
        return None, "审核输出存在空或非字符串断言 id"
    duplicates = sorted({aid for aid in ids if ids.count(aid) > 1})
    if duplicates:
        return None, f"审核输出断言 id 重复 {duplicates}——逐条结果身份须唯一"
    allowed = {"PASS", "FAIL", "WARN", "UNVERIFIED"}
    invalid = sorted({str(row.get("status")) for row in rows
                      if row.get("status") not in allowed})
    if invalid:
        return None, f"审核输出含非法 status {invalid}"
    expected_rc = (1 if any(row.get("status") == "FAIL" for row in rows)
                   else 3 if any(row.get("status") == "UNVERIFIED" for row in rows)
                   else 0)
    if rc != expected_rc:
        return None, (f"审核脚本退出码与逐条状态不一致：rc={rc}，"
                      f"按 rows 应为 {expected_rc}")
    return rows, ""


def _run_audit_neutralized(folder, run_dir, source=None, contract_path=None):
    """同一载荷改成中性目录名并剥掉注入答案，再跑审核器。"""
    try:
        with tempfile.TemporaryDirectory(prefix="m10_neutral_") as root:
            neutral = os.path.join(root, "case")
            shutil.copytree(run_dir, neutral,
                            ignore=shutil.ignore_patterns("INJECTION.json",
                                                          "GATE_INJECTION.json"))
            return _run_audit(folder, neutral, source, contract_path)
    except OSError as e:
        return None, f"中性副本建立失败: {e}"


def _row_statuses(rows, ids):
    return {r.get("id"): r.get("status") for r in rows if r.get("id") in ids}


def _audit_row_identity_error(rows, declared_ids):
    """审核器只能为本契约声明的断言出结果；额外 id 也是伪造面。"""
    unknown = sorted({r.get("id") for r in rows if r.get("id") not in declared_ids})
    return (f"审核输出含未声明断言 {unknown}" if unknown else "")


def _check_custom(folder, op, tag, ir, errs, contract_path=None):
    """custom operation 三条件 · 验实物与实跑，不验字段在位。

    Gate-ID: validate.M9.custom
    Obligations: CUSTOM.EVIDENCE
    判据源 `contract_ir.md §5`。

    `contract_ir §5` 的三条件说的是**东西**不是**键**：独立 golden 是一份该断言
    必须 PASS 的输入输出对，定向 mutant 是一份该断言必须 FAIL 的错误样本，
    来源锚是判据出处。只验三个键非空，填三个字符串就能开一个 custom
    operation——默认 FAIL 的设定当场失效。故本闸落到实物与实跑上：

      1. 两条路径解析后仍在包内（`..`／绝对路径／符号链接逃逸一律拒）；
      2. 路径存在，目录非空；
      3. golden 与 mutant **内容指纹不同**——不是「路径不同」。同一份料
         复制成两个目录名，正例反例同源，不构成对照；
      4. mutant 带 INJECTION.json，其 must_be_rejected_by 指名本 op 名下
         真实存在的断言 id，且本 op 每条断言都被指名；
      5. source_anchor 解析到包内真实文件的真实标题——文件在、标题在；
      6. **真跑**：golden 零 FAIL，mutant 被它指名的那条断言 FAIL。
         「跑出 FAIL」不算——错的断言抓错的错，等于没抓。
    """
    need = ir["custom_operation_policy"]["enable_requires"]
    have = op.get("custom_enablement", {})
    miss = [k for k in need if not have.get(k)]
    if miss:
        errs.append(f"{tag}: custom operation 缺启用条件 {miss}（默认 FAIL）")
        return
    if not folder:
        errs.append(f"{tag}: 无包路径，三条件无从验实物（fail-closed）")
        return

    aids = {a.get("id") for a in op.get("assertions", []) if a.get("id")}
    if not aids:
        errs.append(f"{tag}: custom operation 无断言，三条件无所附丽")
        return

    # ---- 1-3. 路径包内、实物在位、两份料内容不同
    fps, resolved = {}, {}
    for key in ("independent_golden", "directed_mutant"):
        rel = have.get(key)
        if not isinstance(rel, str):
            errs.append(f"{tag}: {key} 须是包内相对路径")
            continue
        full, inside = _contained(folder, rel)
        if not inside:
            errs.append(f"{tag}: {key}「{rel}」解析后逃出包外——包外的料不受本包审核约束")
            continue
        if not os.path.exists(full):
            errs.append(f"{tag}: {key} 指向的 {rel} 不存在——三条件要的是实物不是字段")
            continue
        if os.path.isdir(full) and not os.listdir(full):
            errs.append(f"{tag}: {key} 目录 {rel} 是空的")
            continue
        resolved[key] = full
        fps[key] = _payload_fingerprint(full)

    if len(fps) == 2 and fps["independent_golden"] == fps["directed_mutant"]:
        errs.append(f"{tag}: golden 与 mutant 载荷指纹相同（{fps['independent_golden']}）"
                    "——同一份料换个目录名／只改元数据，正例反例同源，不构成对照")

    # ---- 4. 定向指名
    named = set()
    mut_full = resolved.get("directed_mutant")
    if mut_full:
        inj = (os.path.join(mut_full, "INJECTION.json")
               if os.path.isdir(mut_full) else mut_full)
        if not os.path.exists(inj):
            errs.append(f"{tag}: mutant 缺 INJECTION.json（须声明 must_be_rejected_by）")
        else:
            try:
                with open(inj, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                errs.append(f"{tag}: mutant 的 INJECTION.json 不可读 ({e})")
            else:
                named = {x.strip() for x in
                         str(data.get("must_be_rejected_by", "")).split("/") if x.strip()}
                if not named:
                    errs.append(f"{tag}: mutant 未声明 must_be_rejected_by——"
                                "「跑出 FAIL」不算，须指名被哪条断言拒")
                bad = sorted(named - aids)
                if bad:
                    errs.append(f"{tag}: mutant 指名的断言 {bad} 不在本 operation 内")
                naked = sorted(aids - named)
                if naked:
                    errs.append(f"{tag}: 断言 {naked} 无定向 mutant 指名——未经证伪")

    # ---- 5. 来源锚解析到文件 + 标题
    ok, why = _anchor_resolves(folder, have.get("source_anchor", ""))
    if not ok:
        errs.append(f"{tag}: source_anchor「{have.get('source_anchor')}」不成立——{why}")

    # ---- 6. 真跑：golden 上本 op 每条断言都 PASS，mutant 被指名的那条拒
    #
    # 与 M10 同样把包内源件传下去。不传的话，含 T2 断言的 custom operation
    # 永远跑成 UNVERIFIED——而本条判据是「每条都 PASS」，于是这类包被判死，
    # 死因还写成「正例没背书」。M10 一直传，此处不传，是判据不齐不是设计。
    src = _find_source(folder, errs)
    if "independent_golden" in resolved:
        rows, why = _run_audit(folder, resolved["independent_golden"], src,
                               contract_path)
        if rows is None:
            errs.append(f"{tag}: golden 跑不出审核结果——{why}")
        else:
            # 判据是「每条都 PASS」，不是「没有 FAIL」：UNVERIFIED 是没跑，
            # WARN 是弱断言不满足段闸，两者都不是「这条断言在正例上成立」的证据。
            # 只拒 FAIL 的话，一份全 UNVERIFIED 的料就能冒充 golden。
            seen = {r["id"]: r.get("status") for r in rows if r["id"] in aids}
            bad = sorted(f"{i}={s}" for i, s in seen.items() if s != "PASS")
            absent = sorted(aids - set(seen))
            if bad:
                errs.append(f"{tag}: golden 上本 op 断言 {bad} 非 PASS——"
                            "正例须每条都 PASS，UNVERIFIED／WARN 不是成立的证据")
            if absent:
                errs.append(f"{tag}: golden 跑不到本 op 断言 {absent}——"
                            "没判过的断言不构成正例背书")
    if mut_full and named:
        rows, why = _run_audit(folder, mut_full, src, contract_path)
        if rows is None:
            errs.append(f"{tag}: mutant 跑不出审核结果——{why}")
        else:
            f_ids = {r["id"] for r in rows if r.get("status") == "FAIL"}
            if not (named & f_ids):
                errs.append(f"{tag}: mutant 上 {sorted(named)} 未判 FAIL"
                            f"（实际 FAIL={sorted(f_ids)}）——指名的那条没拒，"
                            "定向 mutant 名不副实")


def check_m9(assertions, ir, folder=None, contract_path=None):
    """M9 · operation 在封闭词汇表 + 最低强断言族全覆盖 + family↔tier 相符。

    Gate-ID: validate.M9
    Obligations: OPERATION.VOCAB, ASSERTION.MINIMUM, ASSERTION.NO_BACKSOLVE, FAMILY.TIER
    判据源 `contract_ir.md §2`、`contract_ir.md §3`、`contract_ir.md §4`、
    `contract_ir.md §8.0`。

    覆盖判定扣除 derived_fields：字段由守恒式反解得出时，含该字段的断言
    不计入该字段的族覆盖（contract_ir §4 总禁则）。

    family↔tier 在此也验一道，与解释器同判据（IR `tier2_families`）。两处都验
    不是冗余：解释器只在**跑到**这条断言时才发现不符，而登记面的错该在编译期
    就红——包交出去时没人跑过它，闸却说过了。
    """
    vocab = ir["operations"]
    weak = set(ir["weak_families"]["members"])
    t2_only = set(ir["tier2_families"]["members"])
    errs = []
    n_ops = 0
    for st in assertions.get("stages", []):
        for op in st.get("operations", []):
            n_ops += 1
            name = op.get("op", "")
            tag = f"{st.get('stage')}/{name}"
            for a in op.get("assertions", []):
                fam, tier = a.get("family"), a.get("tier")
                if fam is None or tier is None:
                    continue  # 缺键由 schema 闸管，不在这里重复报
                # 非 T2 族标 T2 = 借「源不可达 → UNVERIFIED」把机械可判的断言
                # 变成从不判且不变红；T2 族标 T0/T1 = 无源时判 FAIL 而非
                # UNVERIFIED，把「没法验」谎报成「验过了、不成立」。
                if (tier == 2) != (fam in t2_only):
                    want = "2" if fam in t2_only else "0/1"
                    errs.append(f"{tag}/{a.get('id')}: family↔tier 不符——"
                                f"{fam} 须 T{want}，实为 T{tier}")
            if name.startswith("custom"):
                _check_custom(folder, op, tag, ir, errs, contract_path)
                continue
            if name not in vocab:
                errs.append(f"{tag}: operation 不在封闭词汇表 {sorted(vocab)}")
                continue
            declared = set()
            for a in op.get("assertions", []):
                if a.get("family") in weak:
                    continue
                if a.get("derived_fields"):
                    continue  # 反解得出的值，本断言不计入覆盖
                declared.add(a.get("family"))
            # 等价族：同一防线在该 operation 上的另一种声明形态（IR 显式列出，
            # 不是这里推断的）。只单向认——声明的等价族顶替最低族，反之不成立，
            # 免得等价表变成降级通道。
            equiv = vocab[name].get("equivalent_families", {})
            missing = [f for f in vocab[name]["minimum_families"]
                       if f not in declared and not (set(equiv.get(f, [])) & declared)]
            if missing:
                errs.append(f"{tag}: 最低强断言族缺 {missing}")
    if errs:
        return False, errs
    return True, f"M9 PASS: {n_ops} 个 operation 均在词汇表内且最低谓词族全覆盖"


def _find_source(folder, errs):
    """找包内自带的源件（T2 回源比对用）。约定 `fixtures/source*.md`。

    找不到就返回 None——此时 T2 族跑成 UNVERIFIED，是「源不可机械重读」的
    正确表现，不是错误。但指名了 T2 断言的 mutant 会因此拒不住，M10 的
    执行面会把它报出来：包想用 T2 断言当防线，就得把源件带在身边。

    认前缀而不是死认 `source.md`：源件叫什么是包的事，`source_orders.md`
    与 `source.md` 在「这是本包的源件」这件事上没有差别。死认一个名字时，
    包只要换个名，T2 就整片静默转 UNVERIFIED——而 UNVERIFIED 不报错，
    防线掉了没有任何东西变红。

    多于一份则**不猜**，报错并返回 None：审核器只吃一份源件，两份里挑一份
    等于替包决定哪份才算数，挑错了则 T2 全片对着错的源比对、照样报 PASS。
    """
    cands = sorted(glob.glob(os.path.join(folder, "fixtures", "source*.md")))
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        errs.append(f"fixtures/ 下有 {len(cands)} 份 source*.md "
                    f"{[os.path.basename(c) for c in cands]}——审核器只吃一份，"
                    "无从判定哪份是 T2 的比对基准，不猜")
    return None


def check_m10(folder, assertions, ir, contract_path=None):
    """M10 · 每条强断言须有定向 mutant 指名它，**且真跑证明它拒得住**。

    Gate-ID: validate.M10
    Obligations: AUDITOR.EVIDENCE, CUSTOM.EVIDENCE
    判据源 `contract_ir.md §9`、`contract_ir.md §5`。

    判据是「被它自己拒绝」，不是「跑出 FAIL」——错的断言抓错的错，
    覆盖率虚高而防线是空的。本闸两段，都必须过：

      A. 登记面——声明侧 `mutants` 非空 + `source_anchor` 在位，
         fixtures 侧 `must_be_rejected_by` 指名真实存在的断言，两侧对齐。
      B. 执行面——`fixtures/golden*` 跑出零 FAIL；每个带 `INJECTION.json`
         的 mutant 目录跑出「被它指名的那条断言 FAIL」。

    只验 A 的话，两个塞满垃圾的目录 + 一份字段齐全的 INJECTION.json 就能
    过闸：登记面全绿，而没有任何东西证明那条断言在那份料上真的拒得住。
    contract_ir §9 要的三样（正例 golden、定向 mutant、假阳性对照）全是
    **跑出来的判定**，不是登记表上的字段。`contract_ir.md §5` 的 custom
    三条件早就落到实跑（`_check_custom` 第 6 条），词汇表内的 operation
    反而只验登记面——
    同一条要求对 custom 严、对内建松，是判据本身的漏洞，不是设计。

    T0 除外：终态守恒断言以 golden 对照背书，不单独要求 mutant。
    """
    weak = set(ir["weak_families"]["members"])
    errs = []
    declared, tiers, n = {}, {}, 0
    for st in assertions.get("stages", []):
        for op in st.get("operations", []):
            for a in op.get("assertions", []):
                if a.get("family") in weak:
                    continue
                n += 1
                aid = a.get("id", "<无 id>")
                declared[aid] = a.get("mutants", [])
                tiers[aid] = a.get("tier")
                if a.get("tier") == 0:
                    continue
                if not a.get("mutants"):
                    errs.append(f"{aid}: mutants 为空——未经证伪，不构成检验")
                if not a.get("source_anchor"):
                    errs.append(f"{aid}: 缺 source_anchor（判据出处）")

    # ---- A. fixtures 侧：每个 mutant 目录声明它必须被哪条断言拒绝，且该断言真实存在
    fx = os.path.join(folder, "fixtures")
    named, mut_dirs, golden_dirs = set(), {}, []
    if os.path.isdir(fx):
        for root, _dirs, files in sorted(os.walk(fx)):
            if os.path.basename(root).startswith("golden") and root != fx:
                golden_dirs.append(root)
            if "INJECTION.json" not in files:
                continue
            base = os.path.basename(root)
            try:
                with open(os.path.join(root, "INJECTION.json"), encoding="utf-8") as f:
                    inj = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                errs.append(f"{base}: INJECTION.json 不可读 ({e})")
                continue
            want = inj.get("must_be_rejected_by", "")
            if not want:
                errs.append(f"{base}: 缺 must_be_rejected_by")
                continue
            want_ids = {x.strip() for x in str(want).split("/") if x.strip()}
            named |= want_ids
            bad = sorted(want_ids - set(declared))
            if bad:
                errs.append(f"{base}: 指名的断言 {bad} 不在 assertions.json 内")
            mut_dirs[root] = (base, want_ids - set(bad))
    uncovered = [aid for aid, muts in declared.items() if aid not in named and muts]
    for aid in uncovered:
        errs.append(f"{aid}: assertions.json 登记了 mutant，但 fixtures/ 无 mutant 指名它")

    # ---- B. 执行面：真跑 golden 与每个 mutant
    #
    # 跑不动一律 fail-closed。「审核脚本跑不出来」与「断言拒住了」在证据上
    # 相距最远，不能因为拿不到结果就当作没问题——那正是把空壳放行的路径。
    if not golden_dirs:
        if mut_dirs or any(declared.values()):
            errs.append("fixtures/ 下无 golden* 目录——无正例即无假阳性对照，"
                        "「mutant 被拒」无从与「闸恒 FAIL」区分")
    src = _find_source(folder, errs)
    for gd in golden_dirs:
        rows, why = _run_audit(folder, gd, src, contract_path)
        if rows is None:
            errs.append(f"{os.path.relpath(gd, folder)}: golden 跑不出审核结果——{why}")
            continue
        row_identity = _audit_row_identity_error(rows, set(declared))
        if row_identity:
            errs.append(f"{os.path.relpath(gd, folder)}: {row_identity}")
        neutral_rows, neutral_why = _run_audit_neutralized(
            folder, gd, src, contract_path)
        if neutral_rows is None:
            errs.append(f"{os.path.relpath(gd, folder)}: golden 中性副本跑不出审核结果"
                        f"——{neutral_why}")
        elif _row_statuses(rows, set(declared)) != \
                _row_statuses(neutral_rows, set(declared)):
            errs.append(f"{os.path.relpath(gd, folder)}: 审核判定依赖 fixture 名称或 "
                        "INJECTION.json 元数据——同载荷改名/去答案后状态漂移")
        # 判据是「每条都 PASS」，不是「没有 FAIL」。UNVERIFIED 是压根没跑过
        # （T2 无源），WARN 是弱断言不满足段闸，两者都不是「这条断言在正例上
        # 成立」的证据。只拒 FAIL 的话，一份全 UNVERIFIED 的料就能冒充 golden，
        # 而 golden 的全部作用就是给出那条背书。custom 侧（_check_custom 第 6 条）
        # 一直是这个判据，内建 operation 反而松一档，是判据不齐不是设计。
        seen = {r["id"]: r.get("status") for r in rows if r["id"] in declared}
        rel = os.path.relpath(gd, folder)
        bad = sorted(f"{i}={s}" for i, s in seen.items() if s != "PASS")
        if bad:
            errs.append(f"{rel}: 正例上 {bad}——正例须每条都 PASS，"
                        "UNVERIFIED（没跑过）与 WARN（弱断言）都不是成立的证据")
        absent = sorted(set(declared) - set(seen))
        if absent:
            errs.append(f"{rel}: golden 跑不到断言 {absent}"
                        "——没判过的断言不构成正例背书")
    for md, (base, want_ids) in sorted(mut_dirs.items()):
        if not want_ids:
            continue
        # T0 断言不强制 mutant，但一旦指名了就同样要跑——登记了就得兑现
        rows, why = _run_audit(folder, md, src, contract_path)
        if rows is None:
            errs.append(f"{base}: mutant 跑不出审核结果——{why}")
            continue
        row_identity = _audit_row_identity_error(rows, set(declared))
        if row_identity:
            errs.append(f"{base}: {row_identity}")
        neutral_rows, neutral_why = _run_audit_neutralized(
            folder, md, src, contract_path)
        if neutral_rows is None:
            errs.append(f"{base}: mutant 中性副本跑不出审核结果——{neutral_why}")
        elif _row_statuses(rows, set(declared)) != \
                _row_statuses(neutral_rows, set(declared)):
            errs.append(f"{base}: 审核判定依赖 fixture 名称或 INJECTION.json 元数据"
                        "——同载荷改名/去答案后状态漂移")
        f_ids = {r["id"] for r in rows if r.get("status") == "FAIL"}
        miss = sorted(want_ids - f_ids)
        if miss:
            errs.append(f"{base}: 指名的断言 {miss} 未判 FAIL"
                        f"（实际 FAIL={sorted(f_ids) or '无'}）——"
                        "「跑出 FAIL」不算，得是它自己拒的")
    if errs:
        return False, errs
    n_mut = len([1 for _, (_, w) in mut_dirs.items() if w])
    return True, (f"M10 PASS: {n} 条强断言均有 source_anchor 与定向 mutant；"
                  f"实跑 {len(golden_dirs)} 份 golden 零 FAIL、"
                  f"{n_mut} 个 mutant 均被指名的断言拒")


# 占位残留的**标记形态**，不是「谈论占位」的词。裸词 `占位` 不入表：
# 任何记录本闸的文档都会在散文里写到这个词，用裸词做检测器则本闸恒 FAIL，
# 只能靠豁免清单救，而豁免清单会同时豁免真残留。标记形态自身不出现在散文里。
PLACEHOLDER_RE = re.compile(
    r"<[a-zA-Z_一-鿿][\w\s一-鿿·/|-]{0,40}>"   # <name> / <段标识>
    r"|\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX\b"
    r"|【[^】]{0,20}(?:占位|待填|待补)[^】]{0,20}】"             # 【占位】【此处待填】
    r"|(?:占位|待填|待补)\s*[:：]"                              # 占位： 待填:
    r"|(?:待填|待补)(?![写补充])"                               # 裸标记 待填 / 待补
)


def check_m11(folder, text, contract_path=None):
    """M11 · 模板占位残留 fail-closed。

    Gate-ID: validate.M11
    Obligations: PLACEHOLDER.FAIL_CLOSED
    判据源 `contract_ir.md §6.4`。

    占位符留在成品里 = 该处从未真正填写。fail-closed：宁可误报也不放行，
    误报的修法是把占位改成实值或改写措辞，成本远低于带占位上线。
    代码块内的 <path> 形态示例不算残留——用 backtick / tilde 围栏与行内代码排除。
    """
    hits = []
    contract_bodies = []
    if contract_path and os.path.isfile(contract_path):
        label = os.path.relpath(contract_path, folder).replace(os.sep, "/")
        with open(contract_path, encoding="utf-8") as f:
            contract_bodies.append((label, f.read()))
    stateful_path = os.path.join(folder, "stateful_contract.json")
    if os.path.isfile(stateful_path):
        with open(stateful_path, encoding="utf-8") as f:
            contract_bodies.append(("stateful_contract.json", f.read()))
    for label, body in [("SKILL.md", text)] + contract_bodies:
        for i, line in enumerate(_outside_fences(body.splitlines()), 1):
            if not line:
                continue
            stripped = re.sub(r"(?<!`)(`+).*?\1(?!`)", "", line)  # 去行内代码
            m = PLACEHOLDER_RE.search(stripped)
            if m:
                hits.append(f"{label} L{i}: {m.group(0)}  —  {line.strip()[:60]}")
    if hits:
        return False, hits
    return True, "M11 PASS: 无模板占位残留"


STATEFUL_FAULT_POINTS = {
    "after_intent_before_effect",
    "after_effect_before_receipt",
    "after_receipt_before_commit",
    "during_unlock",
}
STATEFUL_SCENARIOS = {
    "duplicate_attempt",
    "unknown_external_state",
    "stale_lock",
    "backlog_retry",
    "evidence_missing",
    "cross_target_isolation",
}


STATEFUL_ACTION_RE = re.compile(
    r"(?:\b(?:transfer|pay|charge|refund|send|email|message|post|upload|publish|"
    r"deploy|schedule|cron|lock|lease|fence|backfill|database|shared state)\b|"
    r"转账|付款|扣款|退款|金融机构|资金划拨|资产划拨|清算柜台|远端确认|发送|发信|发消息|上传|发布|部署|排程|定时|锁|租约|围栏|"
    r"补跑|记忆池|共享状态|外部系统|数据库)", re.I)
EFFECT_SCOPES = {"run_dir_only", "shared_state", "external_system", "scheduler", "lock"}
STATEFUL_INTERFACE_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_./-]+\.py::[A-Za-z_][A-Za-z0-9_]*)")
STATEFUL_ENTRY_ARGS = [
    "logical_target", "evidence_revision", "attempt_id", "fence_token", "adapter",
]


def _stateful_action_evidence(text):
    """只从真实执行段的动作/接口槽取副作用信号，避开教学散文误报。"""
    if not text:
        return []
    lines = _outside_fences(text.splitlines())
    evidence = []
    for lineno, name, block in _card_blocks(lines):
        for offset, line in enumerate(block, 1):
            match = re.match(r"^\s*(?:动作|可达接口)[：:]\s*(.+)$", line)
            if match and STATEFUL_ACTION_RE.search(match.group(1)):
                evidence.append(f"L{lineno + offset} 执行段 {name}: {match.group(1).strip()}")
    for lineno, line in enumerate(lines, 1):
        action = _slot_value(line, "动作")
        if action and STATEFUL_ACTION_RE.search(action):
            evidence.append(f"L{lineno} 编号/列表动作: {action}")
    return evidence


def _effect_scope_declarations(text):
    """返回 (stage→scope, errors)；让副作用分类成为显式结构，不靠同义词猜。"""
    scopes, errors = {}, []
    if not text:
        return scopes, errors
    lines = _outside_fences(text.splitlines())
    for lineno, name, block in _card_blocks(lines):
        values = []
        for offset, line in enumerate(block, 1):
            match = re.match(r"^\s*副作用[：:]\s*(\S+)\s*$", line)
            if match:
                values.append((lineno + offset, match.group(1)))
        if len(values) != 1:
            errors.append(f"执行段 {name} 须恰有一行 副作用:<scope>")
            continue
        line, scope = values[0]
        if scope not in EFFECT_SCOPES:
            errors.append(f"L{line} 执行段 {name} 副作用 scope 非法 {scope}; 允许 {sorted(EFFECT_SCOPES)}")
            continue
        scopes[name] = scope
    for lineno, line in enumerate(lines, 1):
        if not re.match(r"^\s*(?:\d+[.)]|[-+*])\s+.*\*\*动作[：:]\*\*", line):
            continue
        scope = _slot_value(line, "副作用")
        if not scope:
            errors.append(f"L{lineno} 编号/列表执行步须含非空 **副作用：** <scope>")
            continue
        if scope not in EFFECT_SCOPES:
            errors.append(f"L{lineno} 编号/列表执行步副作用 scope 非法 {scope}; "
                          f"允许 {sorted(EFFECT_SCOPES)}")
            continue
        scopes[f"@L{lineno}"] = scope
    return scopes, errors


def _stateful_card_interfaces(text, scopes):
    """Bind each non-local execution card to one concrete production symbol."""
    refs, errors = set(), []
    if not text:
        return refs, errors
    lines = _outside_fences(text.splitlines())
    for lineno, name, block in _card_blocks(lines):
        if scopes.get(name) == "run_dir_only":
            continue
        values = []
        for offset, line in enumerate(block, 1):
            match = re.match(r"^\s*可达接口[：:]\s*(.+)$", line)
            if match:
                values.append((lineno + offset, match.group(1)))
        if len(values) != 1:
            errors.append(f"执行段 {name} 的 stateful 可达接口须恰有一行")
            continue
        line, value = values[0]
        found = STATEFUL_INTERFACE_REF_RE.findall(value)
        if len(found) != 1:
            errors.append(f"L{line} 执行段 {name} 的 stateful 可达接口须含唯一 path.py::symbol")
            continue
        refs.add(found[0].replace("\\", "/"))
    for lineno, line in enumerate(lines, 1):
        if not re.match(r"^\s*(?:\d+[.)]|[-+*])\s+.*\*\*动作[：:]\*\*", line):
            continue
        if scopes.get(f"@L{lineno}") == "run_dir_only":
            continue
        value = _slot_value(line, "可达接口")
        found = STATEFUL_INTERFACE_REF_RE.findall(value or "")
        if len(found) != 1:
            errors.append(f"L{lineno} stateful 编号/列表执行步须含唯一 "
                          "**可达接口：** path.py::symbol")
            continue
        refs.add(found[0].replace("\\", "/"))
    return refs, errors


def _call_targets_symbol(call, tree, symbol, module_name=None):
    """Whether one call expression resolves to a local/imported target symbol."""
    imports, direct = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    direct[alias.asname or alias.name] = (node.module, alias.name)
    func = call.func
    if isinstance(func, ast.Name):
        if func.id == symbol and symbol in _local_funcs(tree):
            return True
        return (func.id in direct and direct[func.id][1] == symbol and
                (module_name is None or direct[func.id][0].split(".")[-1] == module_name))
    return (isinstance(func, ast.Attribute) and func.attr == symbol and
            isinstance(func.value, ast.Name) and func.value.id in imports and
            (module_name is None or imports[func.value.id].split(".")[-1] == module_name))


def _forwards_stateful_identity(call):
    """Require the same target/revision/attempt/fence/adapter names at the kernel call."""
    positional = list(call.args[:len(STATEFUL_ENTRY_ARGS)])
    if len(positional) == len(STATEFUL_ENTRY_ARGS) and all(
            isinstance(value, ast.Name) and value.id == expected
            for value, expected in zip(positional, STATEFUL_ENTRY_ARGS)):
        return True
    keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
    return all(isinstance(keywords.get(name), ast.Name) and keywords[name].id == name
               for name in STATEFUL_ENTRY_ARGS)


def _attribute_root_and_chain(node):
    chain = []
    while isinstance(node, ast.Attribute):
        chain.append(node.attr)
        node = node.value
    return (node.id, list(reversed(chain))) if isinstance(node, ast.Name) else (None, [])


def _safe_import_call(module, qualified):
    """Small pure-call allowlist for stateful entry/kernel orchestration code."""
    base = module.split(".", 1)[0]
    last = qualified.rsplit(".", 1)[-1]
    if base in {"math", "statistics", "decimal", "fractions", "hashlib", "re",
                "itertools", "collections"}:
        return last not in {"attrgetter", "itemgetter"}
    if base == "functools":
        return last in {"reduce", "lru_cache", "cache", "wraps"}
    if base == "json":
        return last in {"loads", "dumps"}
    if base == "datetime":
        return True
    if qualified.startswith("os.path."):
        return last in {"join", "split", "dirname", "basename", "normpath", "abspath",
                        "realpath", "relpath", "commonpath", "commonprefix", "isabs",
                        "expanduser", "expandvars", "splitext"}
    return False


def _higher_order_callable_routes(call, imports, direct):
    """Reject callable arguments consumed by allowlisted higher-order APIs.

    A stateful closure must not smuggle an effectful callable through an API such
    as ``map`` while the verifier sees only the harmless outer call.  The rule is
    deliberately structural: these APIs execute a caller-supplied callable, so
    their use belongs behind the declared adapter/kernel boundary instead.
    """
    name = _call_name(call)
    qualified = name or ""
    root, chain = _attribute_root_and_chain(call.func)
    if root in imports:
        qualified = ".".join([imports[root], *chain])
    elif root in direct:
        module, symbol = direct[root]
        qualified = ".".join([module, symbol, *chain])

    positional_sinks = {
        "map": 0,
        "filter": 0,
        "functools.reduce": 0,
        "reduce": 0,
        "itertools.starmap": 0,
        "itertools.dropwhile": 0,
        "itertools.takewhile": 0,
        "itertools.filterfalse": 0,
        "iter": 0,
    }
    keyword_sinks = {
        "sorted": {"key"},
        "min": {"key"},
        "max": {"key"},
        "json.load": {"object_hook", "object_pairs_hook", "parse_float",
                      "parse_int", "parse_constant"},
        "json.loads": {"object_hook", "object_pairs_hook", "parse_float",
                       "parse_int", "parse_constant"},
    }
    labels = []
    sink = qualified if qualified in positional_sinks or qualified in keyword_sinks else name
    needs_callable = sink in positional_sinks
    # One-argument iter(object) is ordinary iteration; the two-argument form
    # repeatedly invokes a callable until the sentinel is returned.
    if sink == "iter" and len(call.args) < 2:
        needs_callable = False
    if needs_callable and len(call.args) > positional_sinks[sink]:
        labels.append(f"higher_order_callable:{sink}")
    watched = keyword_sinks.get(sink, set())
    if any(keyword.arg in watched for keyword in call.keywords):
        labels.append(f"higher_order_callable:{sink}")
    # re.sub/subn execute a callable replacement supplied as the second arg.
    if sink in {"re.sub", "re.subn", "sub", "subn"} and len(call.args) > 1 and \
            not isinstance(call.args[1], (ast.Constant, ast.JoinedStr)):
        labels.append(f"higher_order_callable:{sink}")
    return labels


def _callable_argument_aliases(sub, local_callables, imports, direct):
    """Track simple aliases that carry callable values into another call."""
    aliases = set()

    def contains(node):
        if isinstance(node, ast.Lambda):
            return True
        if isinstance(node, ast.Name):
            return node.id in local_callables or node.id in direct or node.id in aliases
        if isinstance(node, ast.Attribute):
            root, _ = _attribute_root_and_chain(node)
            return root in imports or root in direct
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return any(contains(item) for item in node.elts)
        if isinstance(node, ast.Dict):
            return any(contains(item) for item in [*node.keys, *node.values] if item)
        return False

    changed = True
    while changed:
        changed = False
        for node in ast.walk(sub):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not contains(node.value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {item.id for target in targets for item in ast.walk(target)
                     if isinstance(item, ast.Name)}
            before = len(aliases)
            aliases.update(names)
            changed = changed or len(aliases) != before
    return aliases, contains


def _direct_effect_calls(tree, sub, kernel_symbol, allow_adapter_methods=False,
                         package_root=None, current_file=None):
    """Find effectful routes reachable before/around the transaction kernel."""
    imports, direct = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    direct[alias.asname or alias.name] = (node.module, alias.name)
    effect_modules = {"subprocess", "requests", "httpx", "socket", "smtplib", "ftplib", "boto3"}
    effect_names = re.compile(
        r"(?:^|_)(?:transfer|pay|charge|refund|send|post|upload|publish|deploy|schedule|"
        r"delete|unlink|rename|replace|execute|commit|rollback|system|popen|"
        r"spawn[a-z0-9_]*|exec[a-z0-9_]*)(?:_|$)", re.I)
    hits = []
    local_functions = set(_local_funcs(tree))
    local_classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    local_callables = local_functions | local_classes
    pure_builtins = {"abs", "all", "any", "bool", "bytes", "dict", "enumerate",
                     "filter", "float", "frozenset", "int", "isinstance", "issubclass",
                     "iter", "len", "list", "map", "max", "min", "next", "range",
                     "repr", "reversed", "round", "set", "sorted", "str", "sum",
                     "tuple", "type", "zip"}
    callable_aliases, contains_callable = _callable_argument_aliases(
        sub, local_callables, imports, direct)
    # Callable values stored behind attributes/subscripts can be invoked by
    # implicit protocols without another visible Call node (for example,
    # ``defaultdict.default_factory`` on a missing-key read).  Callable values
    # returned/yielded from the declared closure likewise escape the audited
    # call surface.  Stateful orchestration keeps both routes fail-closed.
    for binding in ast.walk(sub):
        if isinstance(binding, (ast.Assign, ast.AnnAssign)):
            targets = binding.targets if isinstance(binding, ast.Assign) else [binding.target]
            if contains_callable(binding.value) and any(
                    isinstance(target, (ast.Attribute, ast.Subscript))
                    for target in targets):
                hits.append("callable_binding_route")
        elif isinstance(binding, ast.NamedExpr) and contains_callable(binding.value):
            hits.append("callable_binding_route")
        elif isinstance(binding, (ast.Return, ast.Yield, ast.YieldFrom)) and \
                binding.value is not None and contains_callable(binding.value):
            hits.append("callable_escape_route")
    for node in ast.walk(sub):
        if not isinstance(node, ast.Call):
            continue
        hits.extend(_higher_order_callable_routes(node, imports, direct))
        for argument in [*node.args, *(kw.value for kw in node.keywords)]:
            if contains_callable(argument):
                hits.append("callable_argument_route")
        if allow_adapter_methods and isinstance(node.func, ast.Attribute) and \
                isinstance(node.func.value, ast.Name) and node.func.value.id == "adapter":
            continue
        name = _call_name(node)
        if name == kernel_symbol:
            continue
        module = ""
        qualified = name or ""
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module = imports.get(node.func.value.id, "").split(".", 1)[0]
        elif isinstance(node.func, ast.Name) and node.func.id in direct:
            module = direct[node.func.id][0].split(".", 1)[0]
        root, chain = _attribute_root_and_chain(node.func)
        imported_module = ""
        if root in imports:
            imported_module = imports[root]
            qualified = ".".join([imported_module, *chain])
        elif root in direct:
            imported_module, imported_symbol = direct[root]
            qualified = ".".join([imported_module, imported_symbol, *chain])
        local_import = (bool(imported_module and package_root and current_file) and
                        _resolve_package_module(package_root, current_file,
                                                imported_module) is not None)
        unsafe_import = (bool(imported_module) and not local_import and
                         not _safe_import_call(imported_module, qualified))
        unknown_callable = False
        if isinstance(node.func, ast.Name):
            unknown_callable = (node.func.id not in local_callables and
                                node.func.id not in direct and
                                node.func.id not in pure_builtins and
                                node.func.id not in callable_aliases)
        elif isinstance(node.func, ast.Attribute):
            unknown_callable = not bool(imported_module)
        else:
            unknown_callable = True
        if (name in local_classes or module in effect_modules or effect_names.search(name or "") or
                _is_mutating_io_call(node) or unsafe_import or unknown_callable):
            hits.append(name or ast.dump(node.func, include_attributes=False))
    return sorted(set(hits))


def _module_import_routes(tree):
    """Find executable routes hidden in definitions at module import time."""
    hits = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.decorator_list:
                hits.append(f"decorated_definition:{node.name}")
            expressions = [*node.args.defaults,
                           *(value for value in node.args.kw_defaults if value),
                           node.returns,
                           *(arg.annotation for arg in [*node.args.posonlyargs,
                                                        *node.args.args,
                                                        *node.args.kwonlyargs]
                             if arg.annotation),
                           node.args.vararg.annotation if node.args.vararg else None,
                           node.args.kwarg.annotation if node.args.kwarg else None]
            if any(any(isinstance(child, ast.Call) for child in ast.walk(expr))
                   for expr in expressions if expr is not None):
                hits.append(f"definition_expression:{node.name}")
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and \
                isinstance(node.value.value, str):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and _constantish(node.value):
            continue
        hits.append(f"module_route:{type(node).__name__}")
    return sorted(set(hits))


def _resolve_package_module(folder, current_file, module):
    """Resolve a normal Python module import only when it stays inside the package."""
    if not module:
        return None
    folder = os.path.realpath(folder)
    current_file = os.path.realpath(current_file)
    rel = module.replace(".", os.sep) + ".py"
    candidates = [os.path.join(os.path.dirname(current_file), rel),
                  os.path.join(folder, rel)]
    for candidate in candidates:
        full, inside = _contained(folder, os.path.relpath(candidate, folder))
        if inside and os.path.isfile(full):
            return full
    return None


def _production_closure_effects(folder, entry_rel, entry_symbol, kernel_ref,
                                include_kernel=False):
    """Follow package-local imported helpers and find any effect route outside kernel."""
    kernel_rel, _, kernel_symbol = kernel_ref.partition("::")
    kernel_full = os.path.realpath(os.path.join(folder, kernel_rel))
    start = os.path.realpath(os.path.join(folder, entry_rel))
    todo, seen, effects = [(start, entry_symbol)], set(), []
    cache = {}
    while todo:
        path, symbol = todo.pop()
        key = (os.path.realpath(path), symbol)
        if key in seen or (key == (kernel_full, kernel_symbol) and not include_kernel):
            continue
        seen.add(key)
        if path not in cache:
            try:
                with open(path, encoding="utf-8") as handle:
                    cache[path] = ast.parse(handle.read())
            except (OSError, SyntaxError) as error:
                effects.append(f"unparseable:{os.path.relpath(path, folder)}::{error}")
                continue
        tree = cache[path]
        rel = os.path.relpath(path, folder).replace(os.sep, "/")
        for route in _module_import_routes(tree):
            effects.append(f"{rel}::{route}")
        funcs = _local_funcs(tree)
        fn = funcs.get(symbol)
        if fn is None:
            effects.append(f"missing:{os.path.relpath(path, folder)}::{symbol}")
            continue
        live = _live_function(fn, _module_static_env(tree))
        sub = ast.Module(body=[live], type_ignores=[])
        dynamic_route_calls = set()
        for node in ast.walk(sub):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in {"import_module", "__import__", "getattr", "setattr",
                        "__getattribute__", "vars", "dir", "attrgetter", "itemgetter",
                        "eval", "exec", "compile", "globals", "locals"} or \
                    not isinstance(node.func, (ast.Name, ast.Attribute)):
                dynamic_route_calls.add(name or "indirect_callee")
        for name in sorted(dynamic_route_calls):
            effects.append(f"{rel}::{symbol}->dynamic_route:{name}")
        for hit in _direct_effect_calls(
                tree, sub, kernel_symbol,
                allow_adapter_methods=(key == (kernel_full, kernel_symbol)),
                package_root=folder, current_file=path):
            effects.append(f"{rel}::{symbol}->{hit}")

        imports, direct = {}, {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name.split(".", 1)[0]] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name != "*":
                        direct[alias.asname or alias.name] = (node.module, alias.name)
        for call in (node for node in ast.walk(sub) if isinstance(node, ast.Call)):
            target_path = target_symbol = None
            if isinstance(call.func, ast.Name):
                if call.func.id in funcs:
                    target_path, target_symbol = path, call.func.id
                elif call.func.id in direct:
                    module, target_symbol = direct[call.func.id]
                    target_path = _resolve_package_module(folder, path, module)
            elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                module = imports.get(call.func.value.id)
                if module:
                    target_path = _resolve_package_module(folder, path, module)
                    target_symbol = call.func.attr
            if target_path and target_symbol:
                todo.append((target_path, target_symbol))
    return sorted(set(effects))


def _production_entrypoint_facts(folder, rows, trusted_ref, declared_refs, errs):
    """Verify documented live routes reach the one kernel and forward all identities."""
    if not isinstance(rows, list) or not rows:
        errs.append("production_entrypoints 须为非空数组")
        return []
    facts = []
    kernel_path, _, kernel_symbol = trusted_ref.partition("::")
    kernel_module = os.path.splitext(os.path.basename(kernel_path))[0]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errs.append(f"production_entrypoints[{index}] 须为对象")
            continue
        rel, symbol = row.get("path"), row.get("symbol")
        declared_hash, kernel = row.get("sha256"), row.get("kernel")
        if not all(isinstance(value, str) and value.strip()
                   for value in (rel, symbol, declared_hash, kernel)):
            errs.append(f"production_entrypoints[{index}] 缺 path/sha256/symbol/kernel")
            continue
        normalized = rel.replace("\\", "/").strip("/")
        ref = f"{normalized}::{symbol}"
        full, inside = _contained(folder, rel)
        if not inside or not os.path.isfile(full):
            errs.append(f"production_entrypoints[{index}].path 不在包内或不存在: {rel}")
            continue
        if declared_hash != _file_sha256(full):
            errs.append(f"production_entrypoints[{index}].sha256 与生产入口文件不符")
        if kernel != trusted_ref:
            errs.append(f"production_entrypoints[{index}].kernel 必须绑定唯一 trusted kernel")
        try:
            with open(full, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
        except (OSError, SyntaxError) as error:
            errs.append(f"production entrypoint {ref} 不可解析: {error}")
            continue
        public_functions = {
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
            not node.name.startswith("_")}
        if public_functions != {symbol}:
            errs.append(f"production entrypoint 文件 {normalized} 的公共函数须精确为 "
                        f"{symbol}，实为 {sorted(public_functions)}")
        callbacks = _argparse_callback_dispatch(tree, _bindings(tree))
        callback_symbols = set().union(*callbacks.values()) if callbacks else set()
        if callback_symbols and callback_symbols != {symbol}:
            errs.append(f"production entrypoint 文件 {normalized} 存在未登记 callback "
                        f"{sorted(callback_symbols - {symbol})}")
        unsafe_top = _module_import_routes(tree)
        if unsafe_top:
            errs.append(f"production entrypoint 文件 {normalized} 含 import 时可执行的模块级路径 "
                        f"{sorted(set(unsafe_top))}；CLI/__main__ 须移入另一个受验入口")
        fn = _local_funcs(tree).get(symbol)
        if fn is None:
            errs.append(f"production entrypoint 未定义 {ref}")
            continue
        args = [arg.arg for arg in list(fn.args.posonlyargs) + list(fn.args.args)]
        if args[:len(STATEFUL_ENTRY_ARGS)] != STATEFUL_ENTRY_ARGS:
            errs.append(f"production entrypoint {ref} 前五个参数须为 {','.join(STATEFUL_ENTRY_ARGS)}")
            continue
        if ref == trusted_ref:
            facts.append({"path": normalized, "sha256": _file_sha256(full),
                          "symbol": symbol, "kernel": kernel})
            continue
        reachable = _reachable_local_functions(tree, {symbol})
        funcs = _local_funcs(tree)
        module_env = _module_static_env(tree)
        sub = ast.Module(body=[_live_function(funcs[name], module_env)
                               for name in sorted(reachable)], type_ignores=[])
        kernel_calls = [node for node in ast.walk(sub) if isinstance(node, ast.Call) and
                        _call_targets_symbol(node, tree, kernel_symbol, kernel_module)]
        if not kernel_calls:
            errs.append(f"production entrypoint {ref} 未调用唯一 transaction kernel")
        elif not any(_forwards_stateful_identity(call) for call in kernel_calls):
            errs.append(f"production entrypoint {ref} 未把同一 target/revision/attempt/fence/adapter 传入 kernel")
        direct_effects = _production_closure_effects(
            folder, normalized, symbol, trusted_ref)
        if direct_effects:
            errs.append(f"production entrypoint {ref} 存在绕过 kernel 的 effect 路由 {direct_effects}")
        facts.append({"path": normalized, "sha256": _file_sha256(full),
                      "symbol": symbol, "kernel": kernel})
    identities = [f"{row['path']}::{row['symbol']}" for row in facts]
    if len(identities) != len(set(identities)):
        errs.append("production_entrypoints path::symbol 不得重复")
    if declared_refs and set(identities) != set(declared_refs):
        errs.append(f"SKILL.md stateful 可达接口与 production_entrypoints 不闭合: "
                    f"declared={sorted(declared_refs)} contract={sorted(set(identities))}")
    return facts


def _runner_binding_facts(runner_path, bindings, errs, require_full_coverage=True):
    """验 production binding 在包内、哈希匹配，且 runner 静态 import 并调用。"""
    try:
        with open(runner_path, encoding="utf-8") as handle:
            runner_tree = ast.parse(handle.read())
    except (OSError, SyntaxError) as error:
        errs.append(f"tests.runner 不可解析: {error}")
        return []

    forbidden = []
    for node in ast.walk(runner_tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ""])
            if any(name.split(".", 1)[0] == "ctypes" for name in modules):
                forbidden.append("ctypes")
        if isinstance(node, ast.Call) and _call_name(node) in {"settrace", "setprofile"}:
            forbidden.append(_call_name(node))
    if forbidden:
        errs.append(f"tests.runner 禁止关闭/绕过可信调用轨迹: {sorted(set(forbidden))}")

    imports = {}
    direct_imports = {}
    for node in ast.walk(runner_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name != "*":
                    direct_imports[alias.asname or alias.name] = (node.module, alias.name)
    calls = [node.func for node in ast.walk(runner_tree) if isinstance(node, ast.Call)]

    facts = []
    for index, row in enumerate(bindings):
        if not isinstance(row, dict):
            errs.append(f"tests.implementation_bindings[{index}] 须为对象")
            continue
        rel, declared_hash, symbols = row.get("path"), row.get("sha256"), row.get("symbols")
        if not isinstance(rel, str) or not rel.strip():
            errs.append(f"tests.implementation_bindings[{index}].path 须为非空相对路径")
            continue
        full, inside = _contained(os.path.dirname(os.path.dirname(runner_path)), rel)
        normalized = rel.replace("\\", "/").strip("/")
        runner_rel = os.path.relpath(runner_path, os.path.dirname(os.path.dirname(runner_path))).replace(os.sep, "/")
        if not inside or not os.path.isfile(full):
            errs.append(f"tests.implementation_bindings[{index}].path 不在包内或不存在: {rel}")
            continue
        if normalized == runner_rel or normalized.startswith("tests/") or normalized.startswith("fixtures/"):
            errs.append(f"tests.implementation_bindings[{index}].path 必须指向生产实现，不能是 runner/tests/fixtures")
        actual_hash = _file_sha256(full)
        if not isinstance(declared_hash, str) or declared_hash != actual_hash:
            errs.append(f"tests.implementation_bindings[{index}].sha256 与生产文件不符")
        if (not isinstance(symbols, list) or not symbols or
                not all(isinstance(symbol, str) and symbol for symbol in symbols) or
                len(set(symbols)) != len(symbols)):
            errs.append(f"tests.implementation_bindings[{index}].symbols 须为唯一非空字符串数组")
            continue
        try:
            with open(full, encoding="utf-8") as handle:
                production_tree = ast.parse(handle.read())
        except (OSError, SyntaxError) as error:
            errs.append(f"生产实现 {rel} 不可解析: {error}")
            continue
        defined = set(_local_funcs(production_tree))
        missing = sorted(set(symbols) - defined)
        if missing:
            errs.append(f"生产实现 {rel} 未定义绑定 symbols {missing}")
        callbacks = _argparse_callback_dispatch(production_tree, _bindings(production_tree))
        required_symbols = (set().union(*callbacks.values()) if callbacks else
                            {name for name in defined if not name.startswith("_") and name != "main"})
        if require_full_coverage and set(symbols) != required_symbols:
            errs.append(f"生产实现 {rel} 的 symbols 必须精确覆盖可执行入口 "
                        f"{sorted(required_symbols)}，不得只绑定 benign helper")

        module = os.path.splitext(os.path.basename(rel))[0]
        for symbol in symbols:
            called = any(
                (isinstance(func, ast.Name) and func.id in direct_imports and
                 direct_imports[func.id][0].split(".")[-1] == module and
                 direct_imports[func.id][1] == symbol) or
                (isinstance(func, ast.Attribute) and func.attr == symbol and
                 isinstance(func.value, ast.Name) and func.value.id in imports and
                 imports[func.value.id].split(".")[-1] == module)
                for func in calls)
            if not called:
                errs.append(f"tests.runner 未 import 并调用 {rel}::{symbol}")
        facts.append({"path": normalized, "sha256": actual_hash, "symbols": list(symbols)})
    return facts


def _run_trusted_effect_protocol(probe_root, package, data, env, production_facts=None):
    """由验证器自带 adapter 注入崩溃；候选 runner 无权生成这份 verdict。"""
    errors = []
    entry = data["tests"]["trusted_entrypoint"]
    entry_path = os.path.join(package, entry["path"])
    trusted_run = os.path.join(probe_root, "trusted_stateful_run")
    os.makedirs(trusted_run)
    harness = os.path.join(probe_root, "trusted_effect_protocol.py")
    source = r'''import importlib.util, json, os, sys
entry_path, symbol, run_dir, contract_path, package = sys.argv[1:6]
with open(contract_path, encoding="utf-8") as f: contract=json.load(f)
sys.path[:0]=[package, os.path.dirname(entry_path)]
spec = importlib.util.spec_from_file_location("stateful_production", entry_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
entry = getattr(module, symbol)

class InjectedCrash(RuntimeError): pass
class Adapter:
    def __init__(self, fault=None, unknown=False):
        self.fault=fault; self.unknown=unknown; self.injected=False
        self.events=[]; self.applied=set(); self.effect_calls=0
    def _inject(self, point):
        if self.fault == point and not self.injected:
            self.injected=True; raise InjectedCrash(point)
    def intent(self, key):
        self.events.append("INTENT"); self._inject("after_intent_before_effect")
    def effect(self, key):
        self.effect_calls += 1
        if key not in self.applied: self.applied.add(key)
        self.events.append("EFFECT"); self._inject("after_effect_before_receipt")
    def receipt(self, key):
        self.events.append("RECEIPT"); self._inject("after_receipt_before_commit")
    def readback(self, key):
        self.events.append("READBACK")
        if self.unknown and key not in self.applied: return "UNKNOWN"
        return "APPLIED" if key in self.applied else "ABSENT"
    def commit(self, key): self.events.append("COMMIT")
    def unlock(self, key):
        self.events.append("UNLOCK"); self._inject("during_unlock")

WITH_EFFECT=["INTENT","READBACK","EFFECT","RECEIPT","READBACK","COMMIT","UNLOCK"]
WITHOUT_EFFECT=["INTENT","READBACK","RECEIPT","READBACK","COMMIT","UNLOCK"]
CRASH_TRACE={
    "after_intent_before_effect":["INTENT"],
    "after_effect_before_receipt":["INTENT","READBACK","EFFECT"],
    "after_receipt_before_commit":["INTENT","READBACK","EFFECT","RECEIPT"],
    "during_unlock":WITH_EFFECT,
}
RECOVERY_TRACE={
    "after_intent_before_effect":WITH_EFFECT,
    "after_effect_before_receipt":WITHOUT_EFFECT,
    "after_receipt_before_commit":WITHOUT_EFFECT,
    "during_unlock":WITHOUT_EFFECT,
}

faults=["after_intent_before_effect","after_effect_before_receipt",
        "after_receipt_before_commit","during_unlock"]
rows=[]
for fault in faults:
    case_dir=os.path.join(run_dir,fault); os.makedirs(case_dir)
    adapter=Adapter(fault=fault); crashed=False
    start=len(adapter.events)
    try: entry(fault,"fixture-revision","fixture-attempt",1,adapter,fault,case_dir)
    except InjectedCrash: crashed=True
    crash_trace=adapter.events[start:]
    adapter.fault=None
    start=len(adapter.events)
    result=entry(fault,"fixture-revision","fixture-attempt",1,adapter,None,case_dir)
    recovery_trace=adapter.events[start:]
    state=result.get("state") if isinstance(result,dict) else None
    ok=(crashed and state=="COMMITTED" and len(adapter.applied)==1 and
        adapter.effect_calls==1 and crash_trace==CRASH_TRACE[fault] and
        recovery_trace==RECOVERY_TRACE[fault])
    rows.append({"id":fault,"status":"PASS" if ok else "FAIL",
                 "events":adapter.events,"applied":len(adapter.applied),
                 "effect_calls":adapter.effect_calls,"state":state,"crashed":crashed,
                 "crash_trace":crash_trace,"recovery_trace":recovery_trace})

scenario_rows=[]
for case_id in ("unknown_external_state","evidence_missing"):
    case_dir=os.path.join(run_dir,case_id); os.makedirs(case_dir)
    adapter=Adapter(unknown=True); result=entry(case_id,"fixture-revision","fixture-attempt",1,adapter,None,case_dir)
    state=result.get("state") if isinstance(result,dict) else None
    ok=(state=="RECONCILE_REQUIRED" and not adapter.applied and
        adapter.effect_calls==0 and adapter.events==["INTENT","READBACK"])
    scenario_rows.append({"id":case_id,"status":"PASS" if ok else "FAIL",
                          "events":adapter.events,"state":state,"applied":len(adapter.applied),
                          "effect_calls":adapter.effect_calls})
case_dir=os.path.join(run_dir,"duplicate_attempt"); os.makedirs(case_dir)
adapter=Adapter(); start=len(adapter.events)
first=entry("duplicate_attempt","fixture-revision","fixture-attempt",1,adapter,None,case_dir)
first_trace=adapter.events[start:]; start=len(adapter.events)
second=entry("duplicate_attempt","fixture-revision","fixture-attempt-2",2,adapter,None,case_dir)
second_trace=adapter.events[start:]
state2=second.get("state") if isinstance(second,dict) else None
ok=(len(adapter.applied)==1 and adapter.effect_calls==1 and state2=="COMMITTED" and
    first_trace==WITH_EFFECT and second_trace==WITHOUT_EFFECT)
scenario_rows.append({"id":"duplicate_attempt","status":"PASS" if ok else "FAIL",
                      "events":adapter.events,"state":state2,"applied":len(adapter.applied),
                      "effect_calls":adapter.effect_calls,"first_trace":first_trace,
                      "second_trace":second_trace})
production_rows=[]
kernel_key=(os.path.realpath(entry_path),symbol)
for index,row in enumerate(contract.get("production_entrypoints",[])):
    live_path=os.path.realpath(os.path.join(package,row["path"]))
    live_symbol=row["symbol"]
    seen=set()
    def trace(frame,event,arg):
        if event=="call":
            key=(os.path.realpath(frame.f_code.co_filename),frame.f_code.co_name)
            if key==kernel_key: seen.add(key)
        return trace
    live_spec=importlib.util.spec_from_file_location("stateful_live_"+str(index),live_path)
    live_module=importlib.util.module_from_spec(live_spec)
    sys.path.insert(0,os.path.dirname(live_path))
    live_spec.loader.exec_module(live_module)
    live=getattr(live_module,live_symbol)
    direct_effect_calls=[]; live_checks=[]; state=None; applied=0
    import subprocess
    patched=[]
    def blocked_direct_effect(*args,**kwargs):
        direct_effect_calls.append("blocked_api")
        raise RuntimeError("production entrypoint bypassed transaction kernel")
    for owner,names in ((subprocess,("run","Popen","call","check_call","check_output")),
                        (os,("system","popen","spawnl","spawnle","spawnlp","spawnlpe",
                             "spawnv","spawnve","spawnvp","spawnvpe","execl","execle",
                             "execlp","execlpe","execv","execve","execvp","execvpe"))):
        for name in names:
            if hasattr(owner,name):
                patched.append((owner,name,getattr(owner,name)))
                setattr(owner,name,blocked_direct_effect)
    sys.settrace(trace)
    try:
        for fault_index,fault in enumerate(faults,1):
            adapter=Adapter(fault=fault); crashed=False
            target="live-"+fault
            start=len(adapter.events)
            try: live(target,"live-revision","live-attempt",fault_index,adapter)
            except InjectedCrash: crashed=True
            crash_trace=adapter.events[start:]
            adapter.fault=None
            start=len(adapter.events)
            result=live(target,"live-revision","live-attempt-2",fault_index+100,adapter)
            recovery_trace=adapter.events[start:]
            state=result.get("state") if isinstance(result,dict) else None
            live_checks.append(crashed and state=="COMMITTED" and
                               len(adapter.applied)==1 and adapter.effect_calls==1 and
                               crash_trace==CRASH_TRACE[fault] and
                               recovery_trace==RECOVERY_TRACE[fault])
        adapter=Adapter(unknown=True)
        result=live("live-unknown","live-revision","live-attempt",201,adapter)
        state=result.get("state") if isinstance(result,dict) else None
        live_checks.append(state=="RECONCILE_REQUIRED" and not adapter.applied and
                           adapter.effect_calls==0 and adapter.events==["INTENT","READBACK"])
        adapter=Adapter()
        start=len(adapter.events)
        live("live-duplicate","live-revision","live-attempt",301,adapter)
        first_trace=adapter.events[start:]; start=len(adapter.events)
        result=live("live-duplicate","live-revision","live-attempt-2",302,adapter)
        second_trace=adapter.events[start:]
        state=result.get("state") if isinstance(result,dict) else None
        applied=len(adapter.applied)
        live_checks.append(state=="COMMITTED" and applied==1 and
                           adapter.effect_calls==1 and first_trace==WITH_EFFECT and
                           second_trace==WITHOUT_EFFECT)
    except RuntimeError:
        state="DIRECT_EFFECT_BLOCKED"; live_checks.append(False)
    finally:
        sys.settrace(None)
        for owner,name,original in patched: setattr(owner,name,original)
    ok=(kernel_key in seen and all(live_checks) and not direct_effect_calls)
    production_rows.append({"id":row["path"]+"::"+live_symbol,
                            "status":"PASS" if ok else "FAIL","state":state,
                            "kernel_seen":kernel_key in seen,"applied":applied,
                            "recovery_checks":live_checks,
                            "direct_effect_calls":direct_effect_calls})
all_rows=rows+scenario_rows+production_rows
payload={"status":"PASS" if all(r["status"]=="PASS" for r in all_rows) else "FAIL",
         "fault_points":rows,"scenarios":scenario_rows,"production_entrypoints":production_rows}
print(json.dumps(payload,ensure_ascii=False,sort_keys=True))
'''
    with open(harness, "w", encoding="utf-8") as handle:
        handle.write(source)
    contract_path = os.path.join(package, "stateful_contract.json")
    command = [sys.executable, harness, entry_path, entry["symbol"], trusted_run,
               contract_path, package]
    rc, detail, output = _isolated_command(
        command, probe_root, package, env, "trusted_effect_protocol", timeout=120)
    if rc is None or rc != 0:
        return [f"可信 effect protocol 未完成: rc={rc} {detail}"]
    try:
        payload = json.loads(output)
    except (ValueError, TypeError):
        return ["可信 effect protocol 未输出合法 JSON"]
    if payload.get("status") != "PASS":
        errors.append(f"可信 effect adapter / fault injection FAIL: {payload}")
    expected_faults = STATEFUL_FAULT_POINTS
    actual_faults = {row.get("id") for row in payload.get("fault_points", [])
                     if isinstance(row, dict) and row.get("status") == "PASS"}
    if actual_faults != expected_faults:
        errors.append(f"可信 fault injection 未闭合: {sorted(actual_faults)}")
    required_scenarios = {"duplicate_attempt", "unknown_external_state", "evidence_missing"}
    actual_scenarios = {row.get("id") for row in payload.get("scenarios", [])
                        if isinstance(row, dict) and row.get("status") == "PASS"}
    if actual_scenarios != required_scenarios:
        errors.append(f"可信 recovery scenarios 未闭合: {sorted(actual_scenarios)}")
    expected_production = {f"{row['path']}::{row['symbol']}"
                           for row in (production_facts or [])}
    actual_production = {row.get("id") for row in payload.get("production_entrypoints", [])
                         if isinstance(row, dict) and row.get("status") == "PASS"}
    if actual_production != expected_production:
        errors.append(f"可信 production entrypoint 动态链未闭合: {sorted(actual_production)}")
    return errors


def _run_stateful_probe(folder, contract_path, data, runner_full, binding_facts,
                        production_facts):
    """在可信 harness + OS sandbox 内真跑 recovery runner，并核独立调用轨迹。"""
    errors = []
    try:
        with tempfile.TemporaryDirectory(prefix="m12_stateful_probe_") as probe_root:
            package = os.path.join(probe_root, "package")
            shutil.copytree(folder, package,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            run_dir = os.path.join(probe_root, "run")
            os.makedirs(run_dir)
            runner_rel = os.path.relpath(runner_full, folder)
            probe_runner = os.path.join(package, runner_rel)
            probe_contract = os.path.join(package, os.path.relpath(contract_path, folder))
            target_path = os.path.join(probe_root, "trace_targets.json")
            trace_path = os.path.join(run_dir, "trusted_execution_trace.json")
            with open(target_path, "w", encoding="utf-8") as handle:
                json.dump(binding_facts, handle, ensure_ascii=False, sort_keys=True)
            harness = os.path.join(probe_root, "trusted_stateful_harness.py")
            harness_source = '''import json, os, runpy, sys\n'''
            harness_source += '''runner, target_file, trace_file = sys.argv[1:4]\n'''
            harness_source += '''runner_args = sys.argv[4:]\n'''
            harness_source += '''with open(target_file, encoding="utf-8") as f: targets = json.load(f)\n'''
            harness_source += '''root = os.path.realpath(os.path.dirname(os.path.dirname(runner)))\n'''
            harness_source += '''wanted = {(os.path.realpath(os.path.join(root, row["path"])), symbol) for row in targets for symbol in row["symbols"]}\n'''
            harness_source += '''seen = set()\n'''
            harness_source += '''def trace(frame, event, arg):\n'''
            harness_source += '''    if event == "call":\n'''
            harness_source += '''        key = (os.path.realpath(frame.f_code.co_filename), frame.f_code.co_name)\n'''
            harness_source += '''        if key in wanted: seen.add(key)\n'''
            harness_source += '''    return trace\n'''
            harness_source += '''code = 0\n'''
            harness_source += '''old = sys.argv[:]\n'''
            harness_source += '''try:\n'''
            harness_source += '''    sys.argv = [runner, *runner_args]\n'''
            harness_source += '''    sys.settrace(trace)\n'''
            harness_source += '''    runpy.run_path(runner, run_name="__main__")\n'''
            harness_source += '''except SystemExit as exc:\n'''
            harness_source += '''    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)\n'''
            harness_source += '''finally:\n'''
            harness_source += '''    sys.settrace(None)\n'''
            harness_source += '''    sys.argv = old\n'''
            harness_source += '''payload = [{"path": os.path.relpath(path, root).replace(os.sep, "/"), "symbol": symbol} for path, symbol in sorted(seen)]\n'''
            harness_source += '''flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL\n'''
            harness_source += '''if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW\n'''
            harness_source += '''fd = os.open(trace_file, flags, 0o600)\n'''
            harness_source += '''with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(payload, f, ensure_ascii=False, sort_keys=True)\n'''
            harness_source += '''raise SystemExit(code)\n'''
            with open(harness, "w", encoding="utf-8") as handle:
                handle.write(harness_source)

            before = _tree_file_hashes(package)
            env = dict(os.environ)
            env.update({"HOME": os.path.join(probe_root, "home"),
                        "TMPDIR": os.path.join(probe_root, "tmp"),
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
            os.makedirs(env["HOME"])
            os.makedirs(env["TMPDIR"])
            command = [sys.executable, harness, probe_runner, target_path, trace_path,
                       "--contract", probe_contract, "--run-dir", run_dir, "--json"]
            rc, detail, output = _isolated_command(
                command, probe_root, package, env, "stateful_runner", timeout=120)
            after = _tree_file_hashes(package)
            if before != after:
                errors.append("stateful runner 修改了冻结包输入")
            if rc is None:
                errors.append(f"stateful runner 未完成可信隔离执行: {detail}")
                return errors
            if rc != 0:
                errors.append(f"stateful runner 返回非零 rc={rc}: {detail}")
                return errors
            try:
                stdout_report = json.loads(output)
            except (ValueError, TypeError):
                errors.append("stateful runner stdout 不是单一合法 JSON 报告")
                return errors
            report_path = os.path.join(run_dir, "stateful_test_report.json")
            if os.path.islink(report_path) or not os.path.isfile(report_path):
                errors.append("stateful runner 未在 run-dir 写普通文件 stateful_test_report.json")
                return errors
            try:
                with open(report_path, encoding="utf-8") as handle:
                    file_report = json.load(handle)
                with open(trace_path, encoding="utf-8") as handle:
                    trace = json.load(handle)
            except (OSError, ValueError, TypeError) as error:
                errors.append(f"stateful 报告/可信轨迹不可读: {error}")
                return errors
            if stdout_report != file_report:
                errors.append("stdout 与 stateful_test_report.json 内容不一致")
                return errors
            expected_hash = _file_sha256(probe_contract)
            if file_report.get("status") != "PASS":
                errors.append("stateful_test_report.status 须为 PASS")
            if file_report.get("contract_sha256") != expected_hash:
                errors.append("stateful_test_report 未绑定 contract 全量 SHA-256")
            if file_report.get("implementation_bindings") != binding_facts:
                errors.append("stateful_test_report.implementation_bindings 与 contract/生产文件不一致")

            def evidence_payload(row, key):
                evidence = row.get("evidence")
                if not isinstance(evidence, dict):
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence 须为 path+sha256 对象")
                    return None
                rel, sha = evidence.get("path"), evidence.get("sha256")
                if not isinstance(rel, str) or not isinstance(sha, str):
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence 缺 path/sha256")
                    return None
                full, inside = _contained(run_dir, rel)
                if not inside or os.path.islink(full) or not os.path.isfile(full):
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence 文件越界/缺失")
                    return None
                if _file_sha256(full) != sha:
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence hash 不符")
                    return None
                try:
                    with open(full, encoding="utf-8") as handle:
                        payload = json.load(handle)
                except (OSError, ValueError, TypeError) as error:
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence 不可读: {error}")
                    return None
                if not isinstance(payload, dict) or payload.get("id") != row.get("id"):
                    errors.append(f"stateful_test_report.{key}::{row.get('id')} evidence 身份不闭合")
                    return None
                return payload

            def check_rows(key, expected):
                rows = file_report.get(key)
                if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                    errors.append(f"stateful_test_report.{key} 须为对象数组")
                    return
                ids = [row.get("id") for row in rows]
                if len(ids) != len(set(ids)) or set(ids) != set(expected):
                    errors.append(f"stateful_test_report.{key} 未精确覆盖 contract 声明")
                for row in rows:
                    if row.get("status") != "PASS":
                        errors.append(f"stateful_test_report.{key}::{row.get('id')} 缺 PASS")
                    payload = evidence_payload(row, key)
                    if payload is None:
                        continue
                    effect_count = payload.get("effect_count")
                    if not isinstance(effect_count, int) or isinstance(effect_count, bool) or \
                            effect_count < 0 or effect_count > 1:
                        errors.append(f"stateful_test_report.{key}::{row.get('id')} effect_count > 1")
                    if key == "fault_points":
                        events = payload.get("events")
                        valid = ["INTENT", "READBACK", "EFFECT", "RECEIPT",
                                 "READBACK", "COMMIT", "UNLOCK"]
                        valid_reconcile = ["INTENT", "READBACK", "RECEIPT",
                                           "READBACK", "COMMIT", "UNLOCK"]
                        if events not in (valid, valid_reconcile):
                            errors.append(f"stateful_test_report.{key}::{row.get('id')} 事件顺序未闭合")
                    if row.get("id") == "unknown_external_state" and \
                            (payload.get("terminal_state") != "RECONCILE_REQUIRED" or
                             payload.get("replayed") is not False):
                        errors.append("unknown_external_state 必须停在 RECONCILE_REQUIRED 且不重放")
                    if row.get("id") in {"duplicate_attempt", "stale_lock"} and \
                            payload.get("winner_count") != 1:
                        errors.append(f"{row.get('id')} 必须只有一个有效 winner")
                    if row.get("id") == "stale_lock" and payload.get("old_fence_write_rejected") is not True:
                        errors.append("stale_lock 必须拒绝旧 fence 写入")
                    if row.get("id") == "backlog_retry" and \
                            (payload.get("reselected") is not True or
                             payload.get("permanent_suppression") is not False):
                        errors.append("backlog_retry 必须可重选且不得永久抑制")
                    if row.get("id") == "evidence_missing" and \
                            payload.get("terminal_state") != "RECONCILE_REQUIRED":
                        errors.append("evidence_missing 必须进入 RECONCILE_REQUIRED")
                    if row.get("id") == "cross_target_isolation" and \
                            payload.get("cross_target_collision") is not False:
                        errors.append("cross_target_isolation 必须证明无跨目标碰撞")
            check_rows("fault_points", data["tests"]["fault_points"])
            check_rows("scenarios", data["tests"]["scenarios"])
            boundary_rows = file_report.get("boundary_results")
            expected_boundaries = {row["id"]: row["implementation_symbols"]
                                   for row in data["effect_boundaries"]}
            if not isinstance(boundary_rows, list) or \
                    {row.get("id") for row in boundary_rows if isinstance(row, dict)} != set(expected_boundaries):
                errors.append("stateful_test_report.boundary_results 未精确覆盖 effect boundaries")
            else:
                for row in boundary_rows:
                    if row.get("status") != "PASS" or row.get("implementation_symbols") != expected_boundaries[row["id"]]:
                        errors.append(f"boundary_results::{row.get('id')} 状态/symbol 映射不符")
                    payload = evidence_payload(row, "boundary_results")
                    if payload is None:
                        continue
                    events = payload.get("events", [])
                    exact = ["INTENT", "READBACK", "EFFECT", "RECEIPT",
                             "READBACK", "COMMIT", "UNLOCK"]
                    if events != exact or payload.get("effect_count") != 1:
                        errors.append(f"boundary_results::{row.get('id')} 未证明严格有序且仅一次的 effect 链")
            observed = {(row.get("path"), row.get("symbol")) for row in trace
                        if isinstance(row, dict)} if isinstance(trace, list) else set()
            expected_calls = {(row["path"], symbol) for row in binding_facts
                              for symbol in row["symbols"]}
            if observed != expected_calls:
                errors.append(f"可信 harness 未观察到全部生产 symbol 调用: missing={sorted(expected_calls-observed)} extra={sorted(observed-expected_calls)}")
            errors.extend(_run_trusted_effect_protocol(
                probe_root, package, data, env, production_facts))
            final_package = _tree_file_hashes(package)
            if final_package != before:
                errors.append("可信 stateful protocol 修改了冻结包输入")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        errors.append(f"stateful 动态探针自身失败 {type(error).__name__}: {error}")
    return errors


def validate_stateful_contract(folder, metadata, text=""):
    """M12 · workflow 分类、恢复契约与隔离故障注入行为闸。"""
    folder = os.path.realpath(folder)
    mode = metadata.get("workflow_mode", "") if isinstance(metadata, dict) else ""
    path = os.path.join(folder, "stateful_contract.json")
    scopes, scope_errors = _effect_scope_declarations(text)
    declared_interfaces, interface_errors = _stateful_card_interfaces(text, scopes)
    if mode not in ("artifact", "stateful"):
        return False, ["metadata.workflow_mode 须为 artifact 或 stateful"]
    if scope_errors:
        return False, scope_errors
    if mode == "artifact":
        if os.path.exists(path):
            return False, ["workflow_mode=artifact 却存在 stateful_contract.json，分类互相矛盾"]
        evidence = _stateful_action_evidence(text)
        if evidence:
            return False, ["workflow_mode=artifact 的真实执行动作命中外部/共享副作用信号；须改为 stateful",
                           *evidence[:8]]
        nonlocal_scopes = {stage: scope for stage, scope in scopes.items()
                           if scope != "run_dir_only"}
        if nonlocal_scopes:
            return False, [f"workflow_mode=artifact 只允许 run_dir_only，实为 {nonlocal_scopes}"]
        return True, "M12 PASS: workflow_mode=artifact，无状态恢复契约"
    if not os.path.isfile(path):
        return False, ["workflow_mode=stateful 但缺 stateful_contract.json"]
    if text and scopes and all(scope == "run_dir_only" for scope in scopes.values()):
        return False, ["workflow_mode=stateful 但全部执行段均声明 run_dir_only；分类互相矛盾"]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        return False, [f"stateful_contract.json 不可读: {e}"]
    if not isinstance(data, dict):
        return False, ["stateful_contract.json 顶层须为对象"]

    errs = list(interface_errors)
    if data.get("stateful_contract_version") != "1.0":
        errs.append("stateful_contract_version 须为 1.0")
    identity_keys = ("logical_target_key", "evidence_revision_key", "attempt_key", "fence_key")
    for key in identity_keys:
        if not isinstance(data.get(key), str) or not data[key].strip():
            errs.append(f"{key} 须为非空字符串")
    identities = [data.get(key) for key in identity_keys if data.get(key)]
    if len(identities) != len(set(identities)):
        errs.append("logical_target_key / evidence_revision_key / attempt_key / fence_key 必须四者分离")

    states = data.get("states")
    terminals = data.get("terminal_states")
    if not isinstance(states, list) or not states or not all(isinstance(x, str) and x for x in states):
        errs.append("states 须为非空字符串数组")
        state_set = set()
    else:
        state_set = set(states)
        if len(state_set) != len(states):
            errs.append("states 不得重复")
    if not isinstance(terminals, list) or not terminals or not all(isinstance(x, str) and x for x in terminals):
        errs.append("terminal_states 须为非空字符串数组")
    elif not set(terminals).issubset(state_set):
        errs.append("terminal_states 必须是 states 子集")

    boundaries = data.get("effect_boundaries")
    boundary_keys = {
        "id", "action", "authority", "precondition", "idempotency_key",
        "checkpoint_before", "receipt_after", "readback", "unknown_state",
        "retry_rule", "compensation",
    }
    ids = []
    boundary_symbol_refs = []
    if not isinstance(boundaries, list) or not boundaries:
        errs.append("effect_boundaries 须为非空数组")
    else:
        for i, row in enumerate(boundaries):
            if not isinstance(row, dict):
                errs.append(f"effect_boundaries[{i}] 须为对象")
                continue
            missing = sorted(k for k in boundary_keys
                             if not isinstance(row.get(k), str) or not row[k].strip())
            if missing:
                errs.append(f"effect_boundaries[{i}] 缺非空字段 {missing}")
            ids.append(row.get("id"))
            if row.get("unknown_state") != "halt_and_reconcile":
                errs.append(f"effect_boundaries[{i}].unknown_state 须为 halt_and_reconcile")
            if row.get("retry_rule") != "reconcile_before_retry":
                errs.append(f"effect_boundaries[{i}].retry_rule 须为 reconcile_before_retry")
            symbols = row.get("implementation_symbols")
            if (not isinstance(symbols, list) or not symbols or
                    not all(isinstance(symbol, str) and re.fullmatch(
                        r"[A-Za-z0-9_./-]+\.py::[A-Za-z_][A-Za-z0-9_]*", symbol)
                            for symbol in symbols) or len(set(symbols)) != len(symbols)):
                errs.append(f"effect_boundaries[{i}].implementation_symbols 须为唯一 path.py::symbol 数组")
            else:
                boundary_symbol_refs.extend(symbols)
        if len([x for x in ids if x]) != len(set(x for x in ids if x)):
            errs.append("effect_boundaries[].id 不得重复")

    required_groups = {
        "recovery": {
            "lock_owner_identity", "fencing_rule", "stale_lock_rule", "resume_selector",
            "no_progress_rule", "commit_rule", "unlock_rule",
        },
        "durability": {"journal", "commit_receipt", "evidence_retention"},
    }
    for group, keys in required_groups.items():
        obj = data.get(group)
        if not isinstance(obj, dict):
            errs.append(f"{group} 须为对象")
            continue
        missing = sorted(k for k in keys if not isinstance(obj.get(k), str) or not obj[k].strip())
        if missing:
            errs.append(f"{group} 缺非空字段 {missing}")

    tests = data.get("tests")
    runner_full = None
    binding_facts = []
    if not isinstance(tests, dict):
        errs.append("tests 须为对象")
    else:
        runner = tests.get("runner")
        if not isinstance(runner, str) or not runner.strip():
            errs.append("tests.runner 须为包内相对路径")
        else:
            full, inside = _contained(folder, runner)
            if not inside or not os.path.isfile(full):
                errs.append("tests.runner 必须指向包内现存文件")
            else:
                runner_full = full
        fault_points = tests.get("fault_points")
        if not isinstance(fault_points, list):
            errs.append("tests.fault_points 须为数组")
        else:
            missing = sorted(STATEFUL_FAULT_POINTS - set(fault_points))
            if missing:
                errs.append(f"tests.fault_points 缺 {missing}")
        scenarios = tests.get("scenarios")
        if not isinstance(scenarios, list):
            errs.append("tests.scenarios 须为数组")
        else:
            missing = sorted(STATEFUL_SCENARIOS - set(scenarios))
            if missing:
                errs.append(f"tests.scenarios 缺 {missing}")
        bindings = tests.get("implementation_bindings")
        if not isinstance(bindings, list) or not bindings:
            errs.append("tests.implementation_bindings 须为非空数组")
        elif runner_full:
            binding_facts = _runner_binding_facts(runner_full, bindings, errs)
        entry = tests.get("trusted_entrypoint")
        if not isinstance(entry, dict):
            errs.append("tests.trusted_entrypoint 须为 path+symbol 对象")
        else:
            entry_path, entry_symbol = entry.get("path"), entry.get("symbol")
            if not isinstance(entry_path, str) or not isinstance(entry_symbol, str):
                errs.append("tests.trusted_entrypoint 缺非空 path/symbol")
            else:
                full, inside = _contained(folder, entry_path)
                if not inside or not os.path.isfile(full):
                    errs.append("tests.trusted_entrypoint.path 不在包内或不存在")
                elif f"{entry_path.replace(chr(92), '/')}::{entry_symbol}" not in {
                        f"{row['path']}::{symbol}" for row in binding_facts
                        for symbol in row["symbols"]}:
                    errs.append("tests.trusted_entrypoint 必须指向 implementation_bindings 内生产 symbol")
                else:
                    try:
                        with open(full, encoding="utf-8") as handle:
                            entry_tree = ast.parse(handle.read())
                        fn = _local_funcs(entry_tree).get(entry_symbol)
                        args = [] if fn is None else [arg.arg for arg in
                            list(fn.args.posonlyargs) + list(fn.args.args)]
                        expected_args = STATEFUL_ENTRY_ARGS + ["fault_point", "run_dir"]
                        if args[:len(expected_args)] != expected_args:
                            errs.append("trusted entrypoint 前七个参数须为 " +
                                        ",".join(expected_args))
                        elif fn is not None:
                            adapter_methods = {
                                node.func.attr for node in ast.walk(fn)
                                if isinstance(node, ast.Call) and
                                isinstance(node.func, ast.Attribute) and
                                isinstance(node.func.value, ast.Name) and
                                node.func.value.id == "adapter"}
                            required_methods = {"intent", "effect", "receipt", "readback",
                                                "commit", "unlock"}
                            if not required_methods.issubset(adapter_methods):
                                errs.append("trusted entrypoint 必须直接通过注入 adapter 调用 "
                                            f"{sorted(required_methods)}；不得另写 test-only 状态机")
                    except (OSError, SyntaxError) as error:
                        errs.append(f"tests.trusted_entrypoint 不可解析: {error}")

    bound_symbol_refs = [f"{row['path']}::{symbol}" for row in binding_facts
                         for symbol in row["symbols"]]
    trusted = tests.get("trusted_entrypoint", {}) if isinstance(tests, dict) else {}
    trusted_ref = (f"{str(trusted.get('path', '')).replace(chr(92), '/')}::"
                   f"{trusted.get('symbol', '')}")
    if len(bound_symbol_refs) != 1:
        errs.append("stateful verification 只允许一个公共 transaction kernel；"
                    "support/helper 须私有，全部 boundary 经该 kernel dispatch")
    if bound_symbol_refs and trusted_ref != bound_symbol_refs[0]:
        errs.append("tests.trusted_entrypoint 必须就是唯一公共 transaction kernel")
    if boundary_symbol_refs and any(symbol != trusted_ref for symbol in boundary_symbol_refs):
        errs.append("每个 effect boundary 的 implementation_symbols 必须只绑定唯一 trusted transaction kernel")

    if trusted_ref and "::" in trusted_ref:
        kernel_rel, _, kernel_symbol = trusted_ref.partition("::")
        kernel_full, kernel_inside = _contained(folder, kernel_rel)
        if kernel_inside and os.path.isfile(kernel_full):
            kernel_effects = _production_closure_effects(
                folder, kernel_rel, kernel_symbol, trusted_ref, include_kernel=True)
            if kernel_effects:
                errs.append(f"trusted transaction kernel 存在 adapter 之外的直接 effect 路由 "
                            f"{kernel_effects}")

    production_facts = _production_entrypoint_facts(
        folder, data.get("production_entrypoints"), trusted_ref,
        declared_interfaces, errs)

    if errs:
        return False, errs
    dynamic_errors = _run_stateful_probe(
        folder, path, data, runner_full, binding_facts, production_facts)
    if dynamic_errors:
        return False, dynamic_errors
    return True, (f"M12 PASS: stateful 恢复契约与隔离故障注入通过（{len(boundaries)} 个 effect boundary；"
                  f"{len(tests['fault_points'])} 个故障点；{len(tests['scenarios'])} 个场景；"
                  f"{sum(len(row['symbols']) for row in binding_facts)} 个 kernel symbol；"
                  f"{len(production_facts)} 个 production entrypoint 动态命中）")


def _parse_cli(argv):
    """解析 folder / --persistent / --contract；未知或歧义参数 fail-closed。"""
    folder = None
    persistent = False
    contract = None
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--persistent":
            persistent = True
            i += 1
            continue
        if token == "--contract":
            if contract is not None:
                return None, None, None, "--contract 只能给一次"
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return None, None, None, "--contract 后缺路径"
            contract = argv[i + 1]
            i += 2
            continue
        if token.startswith("--contract="):
            if contract is not None:
                return None, None, None, "--contract 只能给一次"
            contract = token.split("=", 1)[1]
            if not contract:
                return None, None, None, "--contract 后缺路径"
            i += 1
            continue
        if token.startswith("--"):
            return None, None, None, f"未知参数 {token}"
        if folder is not None:
            return None, None, None, f"多余位置参数 {token}"
        folder = token
        i += 1
    return folder, persistent, contract, ""


def _resolve_contract(folder, contract_arg):
    """选定唯一 canonical contract；显式路径须解析后仍留在包根内。"""
    rel = contract_arg or "assertions.json"
    full, inside = _contained(folder, rel)
    if not inside:
        return None, f"契约路径 {rel} 解析后逃出包根（只接受包内契约）"
    if not os.path.isfile(full):
        if contract_arg:
            return None, f"显式契约 {rel} 不存在"
        return None, "缺 assertions.json（默认 canonical contract 不存在）"
    return full, ""


def _load_canonical_contract(path, ir):
    """只判 dialect/container；具体 operation 与断言语义留给 M8-M10。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        return None, f"契约不可读: {e}"
    except json.JSONDecodeError as e:
        return None, f"契约 JSON 无法解析: {e}"
    if not isinstance(data, dict):
        return None, "契约形状不兼容：顶层须为对象"
    expected = str(ir.get("contract_ir_version", ""))
    actual = str(data.get("contract_ir_version", ""))
    if not actual or actual != expected:
        return None, ("契约形状不兼容：contract_ir_version "
                      f"须为 {expected or '<IR 未声明>'}，实为 {actual or '<缺失>'}")
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        return None, ("契约形状不兼容：须为 canonical stages[].operations[].assertions[]；"
                      "普通包内回归 assertions[] 不能冒充执行账本契约")
    for i, stage in enumerate(stages):
        if not isinstance(stage, dict) or not isinstance(stage.get("operations"), list):
            return None, f"契约形状不兼容：stages[{i}].operations 须为数组"
        for j, op in enumerate(stage["operations"]):
            if not isinstance(op, dict) or not isinstance(op.get("assertions"), list):
                return None, (f"契约形状不兼容：stages[{i}].operations[{j}].assertions "
                              "须为数组")
    return data, ""


def main():
    folder, persistent_flag, contract_arg, cli_error = _parse_cli(sys.argv[1:])
    if cli_error or not folder:
        print('用法: python validate.py "<skill 文件夹路径>" [--persistent] '
              '[--contract <包内相对路径>]')
        print('  --persistent  强制按持久 Skill 包验（跑 M8-M10 机械覆盖闸）；')
        print('                包根已有 assertions.json 或给 --contract 时自动生效。')
        print('  --contract    显式选择包内 canonical contract；不隐式搜索 fixtures/。')
        if cli_error:
            print(f'参数错: {cli_error}')
        sys.exit(2)
    if not os.path.isdir(folder):
        print(f"FAIL: 路径不是文件夹: {folder}")
        sys.exit(2)

    text, mdpath = load_skill_md(folder)
    if text is None:
        print(f"FAIL: 找不到 {mdpath}")
        sys.exit(1)

    report = []
    ok = True

    # M1 + frontmatter 解析
    fm_fails, meta = check_frontmatter(text)
    if fm_fails:
        report.extend(fm_fails)
        ok = False
    else:
        report.append("M1 PASS: frontmatter 结构正常")

    # M2 必填字段。宿主只允许 metadata 容纳扩展信息，updated 不得回到顶层。
    missing = [k for k in ("name", "description") if k not in meta or meta[k] == ""]
    metadata = meta.get("metadata", {}) if isinstance(meta.get("metadata"), dict) else {}
    if not metadata.get("updated"):
        missing.append("metadata.updated")
    if metadata.get("workflow_mode") not in ("artifact", "stateful"):
        missing.append("metadata.workflow_mode(artifact|stateful)")
    if missing:
        report.append(f"M2 FAIL: 缺字段 {missing}")
        ok = False
    else:
        report.append("M2 PASS: name/description/metadata.updated/workflow_mode 齐")

    # M5 description
    desc = meta.get("description", "")
    if not desc:
        report.append("M5 FAIL: description 空")
        ok = False
    elif len(desc) > 600:
        report.append(f"M5 WARN: description {len(desc)} 字，偏长——确认它是触发句不是摘要")
    else:
        report.append(f"M5 PASS: description {len(desc)} 字")

    # M3 死链：抓 Windows 绝对路径。允许目录名含空格 / 中文（"Meta Zone"、"01 Projects"），
    # 靠扩展名 / 尾反斜杠锚定 + 前瞻边界，避免空格截断误判（旧版 \s 截断 bug）。
    path_re = re.compile(
        r"[A-Za-z]:\\"
        r"[^\r\n`\"<>|*?]*?"
        r"(?:\.(?:md|py|json|html|txt|csv|ya?ml|ps1|bat|ini|cfg|toml)|\\)"
        r"(?=[\s`\"，。；、）)」』,;]|$)"
    )
    paths = path_re.findall(text)
    dead = []
    for p in sorted(set(paths)):
        p2 = p.rstrip(".·、")
        if not os.path.exists(p2):
            dead.append(p2)
    if dead:
        report.append("M3 FAIL: 下列路径不存在（死链）:")
        for d in dead:
            report.append(f"        {d}")
        ok = False
    else:
        report.append("M3 PASS: 正文里的本地文件路径都存在")
    anchors = sorted(set(re.findall(r"§[^\s`，,。；;）)」』]+", text)))
    if anchors:
        shown = anchors[:8]
        tail = " ..." if len(anchors) > 8 else ""
        report.append(f"M3 NOTE: {len(anchors)} 个 § 节锚点脚本不验，人工抽查: {shown}{tail}")

    # M4 杂物（v3.8：白名单补 assertions.json / fixtures / runs——v3.8 强制件与运行产物，非杂物）
    allowed_top = {"SKILL.md", "scripts", "references", "agents", "assets", "eval-viewer",
                   "_spec_in.md", "assertions.json", "stateful_contract.json",
                   "runner_binding.json", "fixtures", "runs"}
    junk = []
    for name in sorted(os.listdir(folder)):
        if name in allowed_top:
            continue
        if re.search(r"(\.bak$|~$|\bcopy\b|副本|_old|备份)", name, re.I):
            junk.append(name + "（疑似残留备份）")
        else:
            junk.append(name + "（非标准条目，确认是否该在）")
    if junk:
        report.append("M4 WARN: 文件夹里有非标准条目:")
        for j in junk:
            report.append(f"        {j}")
    else:
        report.append("M4 PASS: 文件夹干净")

    # M6 网络节点条件闸（v3.4-draft 新增）：
    # 触发 = 同目录存在 _spec_in.md（orchestrator 节点规格包）或 metadata 出现三键任一。
    # 格式依据 = orchestrator references/topology_schema.md §skill frontmatter 约定：
    #   topology_version 标量；edges_in/edges_out 为 [id:hash, ...] 行内式，hash = sha256 前 16 hex。
    net_keys = ("topology_version", "edges_in", "edges_out")
    has_spec_in = os.path.isfile(os.path.join(folder, "_spec_in.md"))
    has_any_key = any(k in metadata for k in net_keys)
    if has_spec_in or has_any_key:
        edge_re = re.compile(
            r"^\[\s*\]$"
            r"|^\[\s*[\w.-]+:[0-9a-f]{16}(?:\s*,\s*[\w.-]+:[0-9a-f]{16})*\s*\]$"
        )
        m6 = []
        tv = metadata.get("topology_version", "")
        if not tv:
            m6.append("缺 topology_version（标量，值转录自规格包）")
        elif tv.startswith("[") or tv.startswith("{"):
            m6.append(f"topology_version 须为标量，实为: {tv}")
        for k in ("edges_in", "edges_out"):
            v = metadata.get(k, "")
            if not v:
                m6.append(f"缺 {k}（[id:hash] 行内式；无边写 []）")
            elif not edge_re.match(v):
                m6.append(f"{k} 不合行内式 [id:hash16]（16 hex 小写）: {v}")
        trigger = "_spec_in.md 在目录" if has_spec_in else "frontmatter 含网络键"
        if m6:
            report.append(f"M6 FAIL: 网络节点模式（触发: {trigger}），frontmatter 机读契约不合规:")
            for x in m6:
                report.append(f"        {x}")
            ok = False
        else:
            report.append(f"M6 PASS: 网络节点三键合规（topology_version 标量 + edges_in/out 行内式；触发: {trigger}）")
    else:
        report.append("M6 SKIP: 非网络节点（无 _spec_in.md 且 metadata 无网络键）")

    # 持久性先判：M7 对持久包必须看到围栏外真实执行段卡，不许以教学示例代替。
    ap = os.path.join(folder, "assertions.json")
    persistent = persistent_flag or contract_arg is not None or os.path.isfile(ap)

    # M7 执行步四槽（全部 skill · v3.8 解除 v3.7 的网络节点限定）
    m7_ok, m7_out = check_m7(text, persistent)
    if m7_ok is None:
        report.append(m7_out)
    elif m7_ok:
        report.append(m7_out)
    else:
        m7_cause, m7_out = _normalize_gate_failure("M7", m7_out)
        report.append("M7 FAIL: 执行步四槽契约不合规:")
        report.append(f"        [CAUSE:{m7_cause}]")
        for x in m7_out:
            report.append(f"        {x}")
        ok = False

    # ---- M8-M10 持久 Skill 包机械覆盖闸
    assertions = None
    contract_path = None
    contract_issue = ""
    ir = None
    if persistent:
        try:
            ir = load_ir()
        except (OSError, ValueError, json.JSONDecodeError) as e:
            contract_issue = f"读不到 contract IR ({IR_PATH}): {e}"
        if not contract_issue:
            contract_path, contract_issue = _resolve_contract(folder, contract_arg)
        if contract_path and not contract_issue:
            assertions, contract_issue = _load_canonical_contract(contract_path, ir)

        m8_good, m8_out = check_m8(
            folder, text, assertions, contract_path, contract_issue,
            contract_override=contract_arg is not None)
        if m8_good:
            report.append(m8_out)
        else:
            m8_cause, m8_out = _normalize_gate_failure("M8", m8_out)
            report.append("M8 FAIL:")
            report.append(f"        [CAUSE:{m8_cause}]")
            for x in m8_out:
                report.append(f"        {x}")
            ok = False

        if assertions is None or ir is None:
            reason = contract_issue or "canonical contract 前置条件未成立"
            report.append(f"M9 NOT_RUN (FAIL-CLOSED): {reason}；未形成覆盖结论")
            report.append(f"M10 NOT_RUN (FAIL-CLOSED): {reason}；未形成证伪结论")
            ok = False
        else:
            audit_contract = contract_path if contract_arg is not None else None
            for tag, fn in (
                    ("M9", lambda: check_m9(assertions, ir, folder, audit_contract)),
                    ("M10", lambda: check_m10(folder, assertions, ir, audit_contract))):
                good, out = fn()
                if good:
                    report.append(out)
                else:
                    cause, out = _normalize_gate_failure(tag, out)
                    report.append(f"{tag} FAIL:")
                    report.append(f"        [CAUSE:{cause}]")
                    for x in out:
                        report.append(f"        {x}")
                    ok = False
    else:
        report.append("M8-M10 SKIP: 非持久 Skill 包（无 assertions.json 且未给 --persistent）")

    # M11 占位残留 fail-closed（全部 skill）
    m11_ok, m11_out = check_m11(
        folder, text, contract_path if assertions is not None else None)
    if m11_ok:
        report.append(m11_out)
    else:
        m11_cause, m11_out = _normalize_gate_failure("M11", m11_out)
        report.append("M11 FAIL: 模板占位残留（fail-closed）:")
        report.append(f"        [CAUSE:{m11_cause}]")
        for x in m11_out[:12]:
            report.append(f"        {x}")
        if len(m11_out) > 12:
            report.append(f"        …另 {len(m11_out) - 12} 处")
        ok = False

    # M12 副作用与恢复契约（全部 skill 必须先声明 workflow_mode）。
    m12_ok, m12_out = validate_stateful_contract(folder, metadata, text)
    if m12_ok:
        report.append(m12_out)
    else:
        report.append("M12 FAIL: workflow_mode / stateful 恢复契约不合规:")
        for x in m12_out:
            report.append(f"        {x}")
        ok = False

    bar = "=" * 56
    print(bar)
    print(f"validate.py 机械层报告 · {folder}")
    print(bar)
    for r in report:
        print(r)
    print(bar)
    print("结论:", "全部机械检查通过 [OK]" if ok else "有 FAIL，先修机械层再进判断层 [X]")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
