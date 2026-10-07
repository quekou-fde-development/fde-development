"""Dependency-free input and path checks shared by the eval helpers."""
import hashlib
import json
import os
import re
import shlex


def workspace_root():
    return os.environ.get("META_SKILL_EVAL_ROOT") or os.path.join(os.getcwd(), "eval-workspaces")


def component(value):
    if not isinstance(value, str) or not value.strip() or value in (".", "..") or any(c in value for c in "/\\\0:"):
        raise ValueError("skill/version 须为单个目录名")
    return value


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"JSON 键重复: {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"JSON 非有限数: {value}")
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=pairs, parse_constant=constant)


def write_json(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = path + f".{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    os.replace(temporary, path)


def fingerprint(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def trigger_set(path):
    data = load_json(path)
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError("trigger_set 至少须有两条，以保持 train/test 不相交")
    seen = set()
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError("trigger_set 每条须为对象")
        row.setdefault("id", i)
        qid = row["id"]
        if type(qid) is not int or qid < 0 or qid in seen:
            raise ValueError(f"query id 非法或重复: {qid!r}")
        seen.add(qid)
        if type(row.get("should_trigger")) is not bool:
            raise ValueError("should_trigger 须为 JSON boolean")
        if not isinstance(row.get("query"), str) or not row["query"].strip():
            raise ValueError("query 须为非空字符串")
    return data


def description(path):
    with open(path, encoding="utf-8-sig") as f:
        return parse_description(f.read())


def parse_description(text):
    """Read conventional YAML string scalars; reject unsupported syntax explicitly.

    Supports plain, quoted, literal and folded block scalars (with chomping).
    Anchors, aliases, explicit indentation indicators and structured values are
    intentionally rejected, never silently treated as a description string.
    """
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md 缺 YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if end is None:
        raise ValueError("frontmatter 未闭合")
    indexes = [i for i in range(1, end) if re.match(r"^description\s*:", lines[i])]
    if len(indexes) != 1:
        raise ValueError("frontmatter 须有唯一 description")
    index = indexes[0]
    scalar = lines[index].split(":", 1)[1].strip()
    if re.fullmatch(r"[|>][+-]?(?:\s+#.*)?", scalar):
        indicator = scalar.split()[0]
        following = []
        for line in lines[index + 1:end]:
            if line and not line[0].isspace():
                break
            following.append(line)
        nonempty = [len(line) - len(line.lstrip(" ")) for line in following if line.strip()]
        if not nonempty:
            raise ValueError("description block 为空")
        indent = nonempty[0]
        if any(n < indent for n in nonempty):
            raise ValueError("description block 缩进无效")
        block = [line[indent:] if line.strip() else "" for line in following]
        if indicator[0] == "|":
            value = "\n".join(block) + "\n"
        else:
            occupied = [i for i, line in enumerate(block) if line]
            first = occupied[0]
            value = "\n" * first + block[first]
            for previous, current in zip(occupied, occupied[1:]):
                empty = current - previous - 1
                indented = block[previous].startswith(" ") or block[current].startswith(" ")
                separator = "\n" * (empty + 1) if indented else "\n" * empty if empty else " "
                value += separator + block[current]
            value += "\n" * (len(block) - occupied[-1])
        value = value.rstrip("\n") if "-" in indicator else value if "+" in indicator else value.rstrip("\n") + "\n"
    elif scalar.startswith('"'):
        # JSON-compatible double-quoted YAML strings; fail closed for other escapes.
        decoder = json.JSONDecoder()
        value, used = decoder.raw_decode(scalar)
        if scalar[used:].strip() and not scalar[used:].lstrip().startswith("#"):
            raise ValueError("description 引号后含非注释内容")
    elif scalar.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", scalar)
        if not match:
            raise ValueError("description 单引号未闭合")
        value = match.group(1).replace("''", "'")
    else:
        if not scalar or scalar[0] in "&*![{|>" or scalar in ("null", "~", "true", "false"):
            raise ValueError("description 使用未支持的 YAML 形式；使用字符串或 |/> block")
        value = re.split(r"\s+#", scalar, maxsplit=1)[0]
        continued = []
        for line in lines[index + 1:end]:
            if line and not line[0].isspace():
                break
            if line.strip():
                continued.append(line.strip())
        value = " ".join([value, *continued])
    if not isinstance(value, str) or not value.strip():
        raise ValueError("description 须为非空字符串")
    return value.strip()


def score_command(script, skill, root, version):
    return " ".join(shlex.quote(x) for x in ("python3", script, "score", "--skill", skill, "--root", os.path.abspath(root), "--version", version))
