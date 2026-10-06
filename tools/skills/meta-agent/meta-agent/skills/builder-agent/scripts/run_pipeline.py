#!/usr/bin/env python3
"""builder-agent 生产段执行器。

每段是 run-dir 输入的纯函数：读 run-dir 下的输入与上游回执，写本段回执。
CLI 调用一律由 agent 先行执行并落 `handoff/*.json`，本脚本只校验与出回执——
隔离实跑会断网并摘掉 fixtures/，段内不得有任何外部依赖。

段内不取墙钟：时间戳一律取自输入件，保证同输入同字节。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"

SEGMENT_IDS = ["identity", "responsibility", "seat_specific", "common"]
SKELETON_LABELS = ["表征", "取证", "行动", "输出"]
FIVE_KEYS = ["hasInitPhase", "initSkill", "promptSpec", "quickStartPrompts",
             "toolkitKeys"]
KEY_TYPES = {"hasInitPhase": "bool", "initSkill": "str", "promptSpec": "dict",
             "quickStartPrompts": "list", "toolkitKeys": "list"}
# FDE 面的合法实体，在 Builder 面须改写为角色称谓。判据见
# references/prompt-segments.md §四 末段与 references/builder-product.md §三。
# 契约只点名 ⑥ 段的张启山与 M4R；§三 非职责声明里的 M3N / C1D 是同一类席位代号，
# 按同一条理由一并改写——市场产品里出现租户席位代号与出现人名是同一个泄露面。
# 〔本轮裁定，记于 _compile/compile-record-builder-agent.md §第 5 步〕
ROLE_REWRITES = {"张启山": "入口席", "M4R": "知识库写席",
                 "M3N": "判断席", "C1D": "深度推理席"}

# 可由审核器独立重算的字面量模式：`contains` 在断言词汇表内。
# P1 的 `(de_|dw_|…)[a-f0-9]` 带前导边界组，正则不在词汇表内——见 SKILL.md §七。
LITERAL_HITS = {"hit_kb": "/kb/", "hit_tenant": "缺口",
                "hit_brand": "White_Matter", "hit_brand_cn": "白质"}
IMAGE_HOST = "pub.autostaff.cn"


class StageError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


# ---------------------------------------------------------------- 哈希与读写
def canon(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def hash_obj(value, size: int = 16) -> str:
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()[:size]


def hash_text(text: str, size: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:size]


def hash_file(path: Path, size: int = 16) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()[:size]


def read_json(path: Path):
    if not path.is_file():
        raise StageError("INPUT_MISSING", str(path.name))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StageError("INPUT_UNPARSEABLE", f"{path.name}: {exc}") from exc


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


# ---------------------------------------------------------------- 契约解析
# 契约 .md 是唯一权威源。标记或行数一旦移动即 CONTRACT_DRIFT，不按记忆里的旧值走。
def _read_ref(name: str) -> str:
    path = REFS / name
    if not path.is_file():
        raise StageError("CONTRACT_MISSING", name)
    return path.read_text(encoding="utf-8")


def parse_lint_patterns() -> list[dict]:
    """取 builder-product.md §三 的 lint 模式串块，逐行转 Python 正则。"""
    text = _read_ref("builder-product.md")
    marker = "**租户无关性 lint**"
    idx = text.find(marker)
    if idx < 0:
        raise StageError("CONTRACT_DRIFT", "builder-product.md 缺 lint 模式串标记")
    block = re.search(r"```\n(.*?)```", text[idx:], re.S)
    if not block:
        raise StageError("CONTRACT_DRIFT", "lint 模式串块不在标记后")
    out = []
    for i, raw in enumerate(block.group(1).strip().splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        m = re.match(r"^/(.*)/([a-z]*)$", raw)
        if not m:
            raise StageError("CONTRACT_DRIFT", f"lint 模式串第 {i} 行不是 /re/flags")
        out.append({"id": f"P{i}", "regex": m.group(1).replace("\\/", "/"),
                    "flags": m.group(2)})
    if not out:
        raise StageError("CONTRACT_DRIFT", "lint 模式串块为空")
    return out


def compile_lint(patterns: list[dict]) -> list[tuple[str, re.Pattern]]:
    out = []
    for p in patterns:
        flags = re.I if "i" in p["flags"] else 0
        out.append((p["id"], re.compile(p["regex"], flags)))
    return out


def parse_skeleton_labels() -> list[str]:
    text = _read_ref("prompt-segments.md")
    missing = [lab for lab in SKELETON_LABELS if f"**{lab}**" not in text]
    if missing:
        raise StageError("CONTRACT_DRIFT", f"骨架标签缺 {missing}")
    return list(SKELETON_LABELS)


def apply_rewrites(text: str) -> str:
    """把 FDE 面的席位实体改写为角色称谓，顺带吸掉代号前的空格。

    源文里代号前有空格（「须判断交 M3N」）；直replace 会留下「交 判断席」。
    """
    for src_name, dst in ROLE_REWRITES.items():
        text = re.sub(r"[ \u3000]?" + re.escape(src_name), dst, text)
    return text


def parse_nonduty() -> str:
    text = _read_ref("prompt-segments.md")
    idx = text.find("**非职责声明**")
    if idx < 0:
        raise StageError("CONTRACT_DRIFT", "prompt-segments.md 缺非职责声明标记")
    m = re.search(r"^> (.+)$", text[idx:], re.M)
    if not m:
        raise StageError("CONTRACT_DRIFT", "非职责声明后无引用块")
    return m.group(1).strip()


def parse_common_paragraphs() -> list[str]:
    """取 §四 的三段 common 正文：**（N）** 后的首个 `^> ` 引用块。"""
    text = _read_ref("prompt-segments.md")
    out = []
    for n in ("（1）", "（2）", "（3）"):
        idx = text.find(f"**{n}**")
        if idx < 0:
            raise StageError("CONTRACT_DRIFT", f"common 缺 {n} 段")
        m = re.search(r"^> (.+)$", text[idx:], re.M)
        if not m:
            raise StageError("CONTRACT_DRIFT", f"common {n} 段后无引用块")
        out.append(m.group(1).strip())
    return out


def parse_readback_items() -> list[dict]:
    """取 outputs.md §四 的 Builder 侧七项回读表。"""
    text = _read_ref("outputs.md")
    idx = text.find("## 四 · Builder 侧回读")
    if idx < 0:
        raise StageError("CONTRACT_DRIFT", "outputs.md 缺 §四 Builder 侧回读")
    tail = text[idx:]
    end = tail.find("\n## ", 3)
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|",
                      tail[:end if end > 0 else len(tail)], re.M)
    items = [{"id": f"B{int(n):02d}", "name": name.strip()} for n, name in rows]
    if len(items) != 7:
        raise StageError("CONTRACT_DRIFT",
                         f"Builder 回读表应 7 行，实得 {len(items)}")
    return items


# ---------------------------------------------------------------- 段 1
def stage_freeze_definition(run_dir: Path) -> dict:
    product = read_json(run_dir / "input" / "product.json")
    whoami = read_json(run_dir / "handoff" / "auth_whoami.json")

    for block in ("identity", "definition", "package", "publish", "environment"):
        if block not in product:
            raise StageError("SPEC_INCOMPLETE", f"缺 {block} 块")
    if not whoami.get("author_id") or not whoami.get("team_id"):
        raise StageError("AUTH_UNREADABLE", "whoami 缺 author_id 或 team_id")

    definition = product["definition"]
    keys = []
    for name in FIVE_KEYS:
        if name not in definition:
            raise StageError("DEFINITION_INCOMPLETE", f"五键缺 {name}")
        value = definition[name]
        keys.append({"id": name, "type_name": KEY_TYPES[name],
                     "type_ok": _type_ok(value, KEY_TYPES[name]),
                     "sha256": hash_obj(value)})
    bad_type = [k["id"] for k in keys if not k["type_ok"]]
    if bad_type:
        raise StageError("DEFINITION_TYPE", f"类型不符 {bad_type}")

    # lint 扫描面 = 人写的源字段。promptSpec.text 由 compile_prompt 合成，
    # 合成结果另有 compile_prompt 的 no_tenant_entity 闸复扫，两道不重不漏。
    targets = []
    identity = product["identity"]
    for field in ("positioning", "responsibility", "seat_specific"):
        _collect_lines(targets, field, identity[field])
    _collect_lines(targets, "initSkill", definition["initSkill"])
    for i, q in enumerate(definition["quickStartPrompts"], 1):
        _collect_lines(targets, f"quickStart{i}", q)

    files = []
    for entry in product["package"]["files"]:
        files.append({"id": entry["path"], "bytes": int(entry["bytes"]),
                      "sha256": entry["sha256"]})

    readback_items = parse_readback_items()
    blocks = []
    for name in ("identity", "definition", "package", "publish", "environment"):
        blocks.append({"id": name, "present": True,
                       "sha256": hash_obj(product[name])})

    receipt = {
        "source_id": hash_obj(product, 64),
        "product_id": product["identity"]["product_id"],
        "release": product["environment"]["release"],
        "declared_secret_level": product["publish"]["secret_level"],
        "author_id": whoami["author_id"],
        "team_id": whoami["team_id"],
        "blocks": blocks,
        "block_count": len(blocks),
        "blocks_sha256": hash_obj(blocks),
        "keys": keys,
        "key_count": len(keys),
        "keys_sha256": hash_obj(keys),
        "lint_targets": targets,
        "lint_target_count": len(targets),
        "lint_targets_sha256": hash_obj(targets),
        "package_files": files,
        "package_file_count": len(files),
        "package_files_sha256": hash_obj(files),
        "readback_items": readback_items,
        "readback_item_count": len(readback_items),
        "readback_items_sha256": hash_obj(readback_items),
    }
    write_json(run_dir / "s1_definition_receipt.json", receipt)
    return receipt


def _type_ok(value, type_name: str) -> bool:
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "str":
        return isinstance(value, str)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "dict":
        return isinstance(value, dict)
    return False


def _collect_lines(out: list, surface: str, text: str) -> None:
    for i, line in enumerate(text.splitlines() or [""], 1):
        out.append({"id": f"{surface}:L{i}", "surface": surface,
                    "line_no": i, "text": line})


# ---------------------------------------------------------------- 段 2
def stage_tenant_lint(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    patterns = parse_lint_patterns()
    compiled = compile_lint(patterns)

    decisions, clean, hit_ids = [], [], []
    for row in spec["lint_targets"]:
        hit = ""
        for pid, rx in compiled:
            if rx.search(row["text"]):
                hit = pid
                break
        # 逐字面量单独落账：这四个字段审核器能自己用 contains 重算，
        # 不靠本脚本的正则自证。hit_pattern 是本脚本的判定，两者须一致。
        decision = {"id": row["id"], "text": row["text"],
                    "hit_pattern": hit, "clean": not hit}
        for field, literal in LITERAL_HITS.items():
            decision[field] = literal in row["text"]
        decisions.append(decision)
        if hit:
            hit_ids.append(row["id"])
        else:
            clean.append(dict(row))

    receipt = {
        "source_id": spec["source_id"],
        "product_id": spec["product_id"],
        "patterns": patterns,
        "pattern_count": len(patterns),
        "patterns_sha256": hash_obj(patterns),
        "decisions": decisions,
        "decision_count": len(decisions),
        "decisions_sha256": hash_obj(decisions),
        "clean_lines": clean,
        "clean_count": len(clean),
        "clean_sha256": hash_obj(clean),
        "hit_ids": hit_ids,
        "hit_count": len(hit_ids),
    }
    write_json(run_dir / "s2_lint_receipt.json", receipt)
    if hit_ids:
        raise StageError("TENANT_ENTITY_FOUND",
                         f"{len(hit_ids)} 行命中租户实体：{hit_ids[:5]}")
    return receipt


# ---------------------------------------------------------------- 段 3
def stage_compile_prompt(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    read_json(run_dir / "s2_lint_receipt.json")  # 顺序闸：lint 必须先过
    product = read_json(run_dir / "input" / "product.json")

    segments = compose_segments(product)
    body = "\n\n".join(seg["text"] for seg in segments)

    labels = parse_skeleton_labels()
    skeleton = [{"label": lab, "present": f"{lab}：" in body} for lab in labels]
    missing = [s["label"] for s in skeleton if not s["present"]]
    if missing:
        raise StageError("SKELETON_MISSING", f"骨架标签缺 {missing}")

    compiled = compile_lint(parse_lint_patterns())
    tenant_hits = [pid for pid, rx in compiled if rx.search(body)]
    text_checks = [
        {"id": "nonduty", "present": apply_rewrites(parse_nonduty()) in body},
        {"id": "no_tenant_entity", "present": not tenant_hits},
        {"id": "no_seat_code", "present": all(
            k not in body for k in ROLE_REWRITES)},
        {"id": "role_rewritten", "present": all(
            v in body for v in ROLE_REWRITES.values())},
    ]
    failed = [c["id"] for c in text_checks if not c["present"]]
    if failed:
        raise StageError("PROMPT_DRIFT", f"文本闸未过 {failed}")

    definition = dict(product["definition"])
    definition["promptSpec"] = {"type": "static", "text": body}
    write_json(run_dir / "desired" / "definition.json",
               {"definitionPayload": definition})
    write_json(run_dir / "desired" / "prompt.json",
               {"product_id": spec["product_id"], "text": body,
                "sha256": hash_text(body)})

    artifacts = []
    for aid, rel in (("definition", "desired/definition.json"),
                     ("prompt", "desired/prompt.json")):
        path = run_dir / rel
        artifacts.append({"id": aid, "path": rel,
                          "bytes": path.stat().st_size,
                          "sha256": hash_file(path)})

    receipt = {
        "product_id": spec["product_id"],
        "release": spec["release"],
        "segments": segments,
        "segment_count": len(segments),
        "segments_sha256": hash_obj(segments),
        # 正文体积按 UTF-8 字节，不按字符：中文一字三字节，按 len(str) 记会把
        # 3.6 KB 的正文记成 1.7 K，读者对着 prompt-segments.md §六 的 KB 阈值
        # 永远看不出已经超了。本字段是软闸的读数口，没有断言拦它——谓词词汇表
        # 无数值比较 op，故 §六 的「超 3 KB 人工复核」只能由人执行，不由段闸执行。
        "prompt_bytes": len(body.encode("utf-8")),
        "skeleton": skeleton,
        "skeleton_count": len(skeleton),
        "text_checks": text_checks,
        "text_check_count": len(text_checks),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifacts_sha256": hash_obj(artifacts),
    }
    write_json(run_dir / "s3_prompt_receipt.json", receipt)
    return receipt


def compose_segments(product: dict) -> list[dict]:
    """六段取 ①②④⑥，去 ③⑤；⑥ 段把席位人名与代号改写为角色称谓。

    判据：references/builder-product.md §三、references/prompt-segments.md §四。
    """
    identity = product["identity"]
    texts = {
        "identity": f"你是{identity['name']}。{identity['positioning']}",
        "responsibility": identity["responsibility"],
        "seat_specific": identity["seat_specific"],
    }
    common = apply_rewrites("\n\n".join(parse_common_paragraphs()))
    # 目录段是 FDE 面的租户实体面，Builder 面整句删
    common = re.sub(r"通过现役员工目录[^。]*。", "", common)
    skeleton_block = "\n".join(
        f"{lab}：{req}" for lab, req in zip(
            SKELETON_LABELS,
            ["先复述问题与请求方身份",
             "取证先于结论，证据须带引用",
             "动作限定在本域与本权限面内",
             "输出结构固定，缺证据标 UNVERIFIED"]))
    texts["common"] = (f"{common}\n\n{skeleton_block}\n\n"
                       f"{apply_rewrites(parse_nonduty())}")

    segments = []
    for sid in SEGMENT_IDS:
        text = texts[sid]
        segments.append({"id": sid, "text": text, "chars": len(text),
                         "sha256": hash_text(text)})
    return segments


# ---------------------------------------------------------------- 段 4
def stage_accept_worker(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    created = read_json(run_dir / "handoff" / "worker_create.json")
    qa = read_json(run_dir / "handoff" / "image_qa.json")

    if not created.get("worker_id"):
        raise StageError("WORKER_MISSING", "worker_create 缺 worker_id")
    if qa.get("status") != "PASS":
        raise StageError("IMAGE_NOT_REVIEWED", f"QA status={qa.get('status')}")
    if not qa.get("reviewer"):
        raise StageError("IMAGE_NOT_REVIEWED", "QA 缺复核者")
    if qa.get("reviewer") == qa.get("generator"):
        raise StageError("IMAGE_NOT_REVIEWED", "复核者不得是出图执行体自己")

    assets = []
    for aid, rel in (("avatar", "images/avatar.png"), ("bio", "images/bio.png")):
        path = run_dir / rel
        if not path.is_file():
            raise StageError("IMAGE_MISSING", rel)
        if path.read_bytes()[1:4] != b"PNG":
            raise StageError("IMAGE_NOT_PNG", rel)
        row = qa["assets"][aid]
        url = created["images"][aid]["url"]
        assets.append({
            "id": aid, "path": rel, "bytes": path.stat().st_size,
            "sha256": hash_file(path),
            "approved": bool(row["approved"]),
            "pixel_match": row["server_pixel_sha256"] == row["local_pixel_sha256"],
            "url_host": url.split("/")[2] if "//" in url else "",
        })
    bad = [a["id"] for a in assets if not a["approved"] or not a["pixel_match"]]
    if bad:
        raise StageError("IMAGE_READBACK_MISMATCH", f"未过 {bad}")
    bad_host = [a["id"] for a in assets if a["url_host"] != IMAGE_HOST]
    if bad_host:
        raise StageError("IMAGE_HOST_UNEXPECTED", f"{bad_host}")

    receipt = {
        "source_id": hash_obj([created, qa], 64),
        "product_id": spec["product_id"],
        "worker_id": created["worker_id"],
        "author_id": spec["author_id"],
        "reviewer": qa["reviewer"],
        "create_mode": created["create_mode"],
        "assets": assets,
        "asset_count": len(assets),
        "assets_sha256": hash_obj(assets),
    }
    write_json(run_dir / "s4_worker_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 5
def stage_accept_version(run_dir: Path) -> dict:
    worker = read_json(run_dir / "s4_worker_receipt.json")
    config = read_json(run_dir / "handoff" / "version_config.json")
    desired = read_json(run_dir / "desired" / "definition.json")

    if config.get("worker_id") != worker["worker_id"]:
        raise StageError("WORKER_MISMATCH",
                         f"{config.get('worker_id')} != {worker['worker_id']}")
    if not config.get("version_id"):
        raise StageError("VERSION_MISSING", "version_config 缺 version_id")

    payload = desired["definitionPayload"]
    keys = []
    for name in FIVE_KEYS:
        row = config["readback"][name]
        keys.append({
            "id": name, "type_name": KEY_TYPES[name],
            "written_equal": row["value_sha256"] == hash_obj(payload[name]),
            "http_status": int(row["http_status"]),
        })
    drift = [k["id"] for k in keys if not k["written_equal"]]
    if drift:
        raise StageError("DEFINITION_DRIFT", f"五键回读不符 {drift}")

    versions = [{"id": v["version_id"], "role": v["role"]}
                for v in config["versions"]]
    if not any(v["role"] == "current" for v in versions):
        raise StageError("VERSION_ROLE", "版本清单无 current")

    receipt = {
        "source_id": hash_obj(config, 64),
        "product_id": worker["product_id"],
        "worker_id": worker["worker_id"],
        "version_id": config["version_id"],
        "keys": keys,
        "key_count": len(keys),
        "keys_sha256": hash_obj(keys),
        "versions": versions,
        "version_count": len(versions),
        "versions_sha256": hash_obj(versions),
    }
    write_json(run_dir / "s5_version_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 6
def stage_accept_package_scan(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    version = read_json(run_dir / "s5_version_receipt.json")
    scan = read_json(run_dir / "handoff" / "package_scan.json")

    if scan.get("version_id") != version["version_id"]:
        raise StageError("VERSION_MISMATCH",
                         f"{scan.get('version_id')} != {version['version_id']}")
    files = [{"id": f["path"], "bytes": int(f["bytes"]), "sha256": f["sha256"]}
             for f in scan["files"]]
    if len(files) != int(scan["file_count"]):
        raise StageError("SCAN_COUNT_MISMATCH",
                         f"清单 {len(files)} != file_count {scan['file_count']}")
    if len(files) != spec["package_file_count"]:
        raise StageError("SCAN_COUNT_MISMATCH",
                         f"扫描 {len(files)} != 上传 {spec['package_file_count']}")
    # 只配平计数的话，十个全然不同的路径配十个假哈希照样过闸——上架的包和声明的包
    # 可以毫无关系。逐件指纹本来两侧都已落盘，缺的只是这一句比对。
    if hash_obj(files) != spec["package_files_sha256"]:
        raise StageError("SCAN_FILES_MISMATCH",
                         f"{hash_obj(files)} != {spec['package_files_sha256']}")

    receipt = {
        "source_id": hash_obj(scan, 64),
        "worker_id": version["worker_id"],
        "version_id": version["version_id"],
        "package_sha256": scan["package_sha256"],
        "files": files,
        "file_count": len(files),
        "files_sha256": hash_obj(files),
    }
    write_json(run_dir / "s6_scan_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 7
def stage_accept_publish(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    version = read_json(run_dir / "s5_version_receipt.json")
    state = read_json(run_dir / "handoff" / "publish_state.json")

    roles = {v["id"]: v["role"] for v in version["versions"]}
    observed = {v["version_id"]: v["state"] for v in state["versions"]}
    versions = []
    for vid, role in roles.items():
        if vid not in observed:
            raise StageError("VERSION_STATE_MISSING", vid)
        versions.append({"id": vid, "role": role, "state": observed[vid]})

    if state.get("listed_version_id") != version["version_id"]:
        raise StageError("LISTED_VERSION_DRIFT",
                         f"{state.get('listed_version_id')} != {version['version_id']}")
    if state.get("secret_level") != spec["declared_secret_level"]:
        raise StageError("SECRET_LEVEL_DRIFT",
                         f"{state.get('secret_level')} != {spec['declared_secret_level']}")

    receipt = {
        "source_id": hash_obj(state, 64),
        "worker_id": version["worker_id"],
        "versions": versions,
        "version_count": len(versions),
        "versions_sha256": hash_obj(versions),
        "listed_version_id": state["listed_version_id"],
        "secret_level": state["secret_level"],
        "declared_secret_level": spec["declared_secret_level"],
    }
    write_json(run_dir / "s7_publish_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 8
def stage_finalize_delivery(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_definition_receipt.json")
    lint = read_json(run_dir / "s2_lint_receipt.json")
    prompt = read_json(run_dir / "s3_prompt_receipt.json")
    worker = read_json(run_dir / "s4_worker_receipt.json")
    version = read_json(run_dir / "s5_version_receipt.json")
    scan = read_json(run_dir / "s6_scan_receipt.json")
    publish = read_json(run_dir / "s7_publish_receipt.json")
    hired = read_json(run_dir / "handoff" / "hired_instances.json")

    gates = [
        {"id": "lint_clean", "passed": not lint["hit_ids"]},
        {"id": "five_keys_equal",
         "passed": all(k["written_equal"] for k in version["keys"])},
        {"id": "scan_count_equal",
         "passed": scan["file_count"] == spec["package_file_count"]},
        {"id": "images_approved",
         "passed": all(a["approved"] and a["pixel_match"]
                       for a in worker["assets"])},
        {"id": "listed_is_current",
         "passed": publish["listed_version_id"] == version["version_id"]},
        {"id": "prior_superseded",
         "passed": all(v["state"] == "superseded" for v in publish["versions"]
                       if v["role"] == "prior")},
    ]

    plan = [{"team_id": r["team_id"], "employee_id": r["employee_id"],
             "from_version": r["from_version"],
             "to_version": version["version_id"],
             "action": "builder-upgrade", "executed": False}
            for r in hired["instances"]]

    statuses = {
        "B01": gates[0]["passed"], "B02": gates[1]["passed"],
        "B03": gates[2]["passed"], "B04": gates[3]["passed"],
        "B05": gates[4]["passed"] and gates[5]["passed"],
        "B06": publish["secret_level"] == spec["declared_secret_level"],
        "B07": True,
    }
    readback = [{"id": it["id"], "status": "PASS" if statuses[it["id"]] else "FAIL"}
                for it in spec["readback_items"]]
    blocked = [r["id"] for r in readback if r["status"] != "PASS"]

    write_json(run_dir / "delivery" / "readback.json",
               {"product_id": spec["product_id"], "items": readback})
    write_json(run_dir / "delivery" / "upgrade-plan.json",
               {"worker_id": worker["worker_id"],
                "to_version": version["version_id"], "instances": plan})
    write_json(run_dir / "delivery" / "manifest.json", {
        "schema_version": "meta-agent-manifest-09.20.1",
        "surface": "builder", "release": spec["release"],
        "product_id": spec["product_id"], "worker_id": worker["worker_id"],
        "version_id": version["version_id"],
        "package_sha256": scan["package_sha256"],
        "secret_level": publish["secret_level"],
        "readback": {"pass": len(readback) - len(blocked),
                     "fail": len(blocked), "rows": "delivery/readback.json"},
        "upgrade_plan": {"instances": len(plan), "executed": 0,
                         "rows": "delivery/upgrade-plan.json"},
        "gate_pass": not blocked, "blockers": blocked,
    })

    artifacts = []
    for aid, rel in (("readback", "delivery/readback.json"),
                     ("upgrade_plan", "delivery/upgrade-plan.json"),
                     ("manifest", "delivery/manifest.json")):
        path = run_dir / rel
        artifacts.append({"id": aid, "path": rel, "bytes": path.stat().st_size,
                          "sha256": hash_file(path)})

    receipt = {
        "product_id": spec["product_id"],
        "worker_id": worker["worker_id"],
        "version_id": version["version_id"],
        "package_sha256": scan["package_sha256"],
        "prompt_sha256": prompt["artifacts"][1]["sha256"],
        "gates": gates,
        "gate_count": len(gates),
        "gates_sha256": hash_obj(gates),
        "readback": readback,
        "readback_count": len(readback),
        "readback_sha256": hash_obj(readback),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifacts_sha256": hash_obj(artifacts),
    }
    write_json(run_dir / "s8_delivery_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 入口
STAGES = {
    "freeze_definition": stage_freeze_definition,
    "tenant_lint": stage_tenant_lint,
    "compile_prompt": stage_compile_prompt,
    "accept_worker": stage_accept_worker,
    "accept_version": stage_accept_version,
    "accept_package_scan": stage_accept_package_scan,
    "accept_publish": stage_accept_publish,
    "finalize_delivery": stage_finalize_delivery,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="builder-agent 段执行器")
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"[FAIL] run-dir 不存在: {run_dir}", file=sys.stderr)
        return 2
    try:
        STAGES[args.stage](run_dir)
    except StageError as exc:
        print(f"[FAIL] {args.stage}: {exc}", file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError) as exc:
        print(f"[FAIL] {args.stage}: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 1
    print(f"[OK] {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
