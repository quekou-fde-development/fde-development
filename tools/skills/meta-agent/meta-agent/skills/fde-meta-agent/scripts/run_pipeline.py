#!/usr/bin/env python3
"""fde-meta-agent 生产段执行器。

每段是 run-dir 输入的纯函数：读 run-dir 下的输入与上游回执，写本段回执。
网络调用一律由 agent 先行执行并落 `handoff/*.json`，本脚本只校验与出回执——
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

# 内嵌目录在提示词里的标记。s4 回执据它回读自己编出的正文，从而让
# 「这一席到底内嵌了没有」成为可核事实，而不是转抄 s2 的布尔值。
DIRECTORY_MARK = "【现役员工目录】"
SEGMENT_IDS = ["identity", "responsibility", "domain", "seat_specific",
               "boundary", "common"]
SKELETON_LABELS = ["表征", "取证", "行动", "输出"]
NINE_KEYS = ["prompt", "bio", "toolkit", "model_thinking", "access_policy",
             "kb_paths", "workspace_access", "reporting_line", "team_skills"]
ROUTING_ROLES = ["parent", "quick_lookup", "escalation", "out_of_domain",
                 "approval"]


class StageError(RuntimeError):
    """段内不可继续的错误。以失败码起头，便于汇报直接引用。"""


def require(cond: bool, code: str, detail: str = "") -> None:
    if not cond:
        raise StageError(f"{code}{': ' + detail if detail else ''}")


def canon(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def hash_obj(value: object, size: int = 16) -> str:
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()[:size]


def hash_file(path: Path, size: int = 16) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()[:size]


def hash_text(text: str, size: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:size]


def read_json(path: Path, code: str) -> dict:
    require(path.exists(), code, f"缺输入件 {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StageError(f"{code}: {path.name} 非合法 JSON（{exc}）") from exc


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- 契约解析
# 六段模板的权威源是 references/prompt-segments.md，段内按标记解析，不复制正文。
# 复制正文会与权威源漂移；解析则漂移即刻报错。

def contract_text(name: str) -> str:
    path = REFS / name
    require(path.exists(), "CONTRACT_MISSING", name)
    return path.read_text(encoding="utf-8")


def parse_common_paragraphs(text: str) -> list[str]:
    """取 §四 三段 common 正文。标记是 `**（N）**` 后的首个引用块。"""
    out = []
    for mark in ("（1）", "（2）", "（3）"):
        anchor = text.find(f"**{mark}**")
        require(anchor > 0, "CONTRACT_DRIFT", f"prompt-segments.md 缺 {mark} 标记")
        quote = re.search(r"^> (.+)$", text[anchor:], re.M)
        require(quote is not None, "CONTRACT_DRIFT", f"{mark} 后无引用块正文")
        out.append(quote.group(1).strip())
    return out


def parse_nonduty(text: str) -> str:
    anchor = text.find("**非职责声明**")
    require(anchor > 0, "CONTRACT_DRIFT", "prompt-segments.md 缺非职责声明标记")
    quote = re.search(r"^> (.+)$", text[anchor:], re.M)
    require(quote is not None, "CONTRACT_DRIFT", "非职责声明后无引用块正文")
    return quote.group(1).strip()


def parse_directory_skill(text: str) -> str:
    """取 §五 表里那一行声明的挂载技能名。

    技能名不写死在脚本里：它是 prompt-segments.md §五 的决定，写死就会在
    权威源改名时留下一个还在找旧名字的推导，把「可达」误判成「不可达」。
    """
    row = re.search(r"^\| 现役员工目录 \|.*?挂载团队技能 `([^`]+)`", text, re.M)
    require(row is not None, "CONTRACT_DRIFT",
            "prompt-segments.md §五 缺现役员工目录的挂载技能行")
    return row.group(1).strip()


def parse_reply_targets_clause(text: str) -> str:
    marker = "**reply-targets 为会话级平台能力"
    anchor = text.find(marker)
    require(anchor > 0, "CONTRACT_DRIFT", "prompt-segments.md 缺 reply-targets 原句")
    line = text[anchor:text.find("\n", anchor)]
    return line.replace("**", "").strip()


def parse_skeleton_labels(text: str) -> list[str]:
    """骨架四位标签在 §三 表内加粗。解析出的集合须与常量相等，否则契约已漂移。"""
    found = [lab for lab in SKELETON_LABELS if f"**{lab}**" in text]
    require(found == SKELETON_LABELS, "CONTRACT_DRIFT",
            f"骨架四位标签解析得 {found}")
    return found


def parse_readback_items(text: str) -> list[dict]:
    """取 outputs.md §三 十六项回读表。表行形如 `| 1 | 员工存在 | … | CODE |`。"""
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        if not re.fullmatch(r"[A-Z_]+", cells[3].strip("`")):
            continue
        rows.append({"id": f"R{int(cells[0]):02d}", "name": cells[1],
                     "code_on_fail": cells[3].strip("`")})
    require(len(rows) == 16, "CONTRACT_DRIFT",
            f"outputs.md §三 解析得 {len(rows)} 项，应 16 项")
    return rows


# ---------------------------------------------------------------- 段 1
def stage_freeze_spec(run_dir: Path) -> dict:
    spec_path = run_dir / "input" / "seat.json"
    spec = read_json(spec_path, "SPEC_INCOMPLETE")

    blocks = []
    for name in ("identity", "function", "permissions", "face", "environment"):
        body = spec.get(name)
        blocks.append({"id": name, "present": isinstance(body, dict) and bool(body),
                       "sha256": hash_obj(body) if body else ""})
    missing = [b["id"] for b in blocks if not b["present"]]
    require(not missing, "SPEC_INCOMPLETE", f"缺块 {missing}")

    identity = spec["identity"]
    permissions = spec["permissions"]
    keys = []
    for key in NINE_KEYS:
        entry = permissions.get(key) or {}
        carrier = str(entry.get("carrier", "")).strip()
        keys.append({"id": key, "carrier": carrier,
                     "has_carrier": bool(carrier),
                     "source": str(entry.get("source", ""))})
    no_carrier = [k["id"] for k in keys if not k["has_carrier"]]
    require(not no_carrier, "NO_CARRIER_FOR_KEY", f"无写路由 {no_carrier}")

    # face.rule 必须随回执往下走：只存块哈希的话，accept_images 手里没有
    # 任何可对照的规格值，QA 回执自称什么规则就是什么规则（已实测可穿透）。
    face = spec["face"]
    face_rule = str(face.get("rule", "")).strip()
    require(face_rule in ("reuse", "generate"), "SPEC_INCOMPLETE",
            f"face.rule 取值非法 {face_rule!r}")
    face_local_copy = ""
    if face_rule == "reuse":
        face_local_copy = str((face.get("reuse") or {}).get("local_copy", "")).strip()
        require(bool(face_local_copy), "FACE_REUSE_UNVERIFIED",
                "复用路径未给 local_copy")

    params = spec["function"].get("params") or {}
    dims = []
    for dim in ("templates", "landing_tables", "relation_gates",
                "signing_roles", "kb_prefix", "workspace"):
        value = params.get(dim)
        dims.append({"id": dim, "present": value not in (None, "", [], {}),
                     "sha256": hash_obj(value) if value is not None else ""})
    absent = [d["id"] for d in dims if not d["present"]]
    require(not absent, "SPEC_INCOMPLETE", f"参数包缺维 {absent}")

    routing_src = spec["function"].get("routing") or {}
    routing = []
    for role in ROUTING_ROLES:
        target = routing_src.get(role)
        require(isinstance(target, str) and target,
                "SPEC_INCOMPLETE", f"routing.{role} 未给逻辑键")
        routing.append({"role": role, "target": target})

    readback_items = parse_readback_items(contract_text("outputs.md"))

    receipt = {
        "source_id": f"sha256:{hash_file(spec_path, 64)}",
        "fetched_at": spec["environment"]["frozen_at"],
        "source_relpath": "input/seat.json",
        "logical_id": identity["logical_id"],
        "code": identity["code"],
        "display_name": identity["display_name"],
        "kind": identity["kind"],
        "tier": identity["tier"],
        "human_facing": bool(identity["human_facing"]),
        "blocks": blocks,
        "block_count": len(blocks),
        "face_rule": face_rule,
        "face_local_copy": face_local_copy,
        "blocks_sha256": hash_obj(blocks),
        "keys": keys,
        "key_count": len(keys),
        "keys_sha256": hash_obj(keys),
        "params_dims": dims,
        "dim_count": len(dims),
        "dims_sha256": hash_obj(dims),
        "routing": routing,
        "routing_count": len(routing),
        "routing_sha256": hash_obj(routing),
        "readback_items": readback_items,
        "readback_item_count": len(readback_items),
        "readback_items_sha256": hash_obj(readback_items),
        "contract_sha256": hash_file(REFS / "outputs.md"),
    }
    write_json(run_dir / "s1_spec_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 2
def stage_accept_environment(run_dir: Path) -> dict:
    probe_path = run_dir / "handoff" / "environment_probe.json"
    probe = read_json(probe_path, "ENVIRONMENT_UNREADABLE")
    spec = read_json(run_dir / "s1_spec_receipt.json", "ENVIRONMENT_UNREADABLE")

    probes = []
    for row in probe.get("probes", []):
        probes.append({"id": str(row["id"]), "endpoint": str(row["endpoint"]),
                       "http_status": int(row["http_status"]),
                       "item_count": int(row["item_count"])})
    require(probes, "ENVIRONMENT_UNREADABLE", "探针清单为空")
    bad = [p["id"] for p in probes if p["http_status"] != 200]
    require(not bad, "ENVIRONMENT_UNREADABLE", f"探针非 200：{bad}")

    directory = []
    for row in probe.get("live_directory", []):
        directory.append({"logical_id": str(row["logical_id"]),
                          "employee_id": str(row["employee_id"]),
                          "code": str(row["code"]),
                          "display_name": str(row["display_name"])})
    seen = {d["logical_id"] for d in directory}
    require(len(seen) == len(directory), "ENVIRONMENT_UNREADABLE", "目录逻辑键重复")

    # 目录机制从探针证据推导，不收探针的自报值。
    # 自报的问题：填这份件的人得先把判断段 3.3 的结论算好写进来，判断段就成了
    # 补记录的摆设；而「挂载技能可不可达」在同一份件里本来就有可核的证据——
    # 技能目录里有没有这个技能。探针非 200 是另一回事：那是连世界是什么样都
    # 没读到，没有依据可推导，按 ENVIRONMENT_UNREADABLE 硬停（上面已拦）。
    catalog = [str(row["id"]) for row in probe.get("skill_catalog", [])]
    mount_target = parse_directory_skill(contract_text("prompt-segments.md"))
    mounted = mount_target in catalog
    mechanism = "mounted_skill" if mounted else "prompt_embedded"
    fallback = not mounted

    # 探针仍可自报机制，但它只能与推导一致，不能替代推导。不一致说明填件的人
    # 与探针证据说的不是一回事，停手而不是二选一。
    declared_mech = str(probe.get("directory_mechanism", ""))
    if declared_mech:
        require(declared_mech == mechanism, "ENVIRONMENT_UNREADABLE",
                f"探针自报机制 {declared_mech!r}，但技能目录里"
                f"{'有' if mounted else '没有'} {mount_target!r}，推导为 {mechanism!r}")

    receipt = {
        "source_id": f"sha256:{hash_file(probe_path, 64)}",
        "fetched_at": probe["probed_at"],
        "source_relpath": "handoff/environment_probe.json",
        "release": str(probe["release"]),
        "team_id": str(probe["team_id"]),
        "logical_id": spec["logical_id"],
        "directory_mechanism": mechanism,
        "directory_fallback": fallback,
        "directory_skill": mount_target,
        "directory_skill_present": mounted,
        "skill_catalog_ids": catalog,
        "probes": probes,
        "probe_count": len(probes),
        "probes_sha256": hash_obj(probes),
        "live_directory": directory,
        "directory_count": len(directory),
        "directory_sha256": hash_obj(directory),
        "model_catalog_count": len(probe.get("model_catalog", [])),
        "skill_catalog_count": len(catalog),
    }
    write_json(run_dir / "s2_environment_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 3
def stage_resolve_routing(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_spec_receipt.json", "DIRECTORY_UNRESOLVED")
    env = read_json(run_dir / "s2_environment_receipt.json", "DIRECTORY_UNRESOLVED")

    table = {row["logical_id"]: row for row in env["live_directory"]}
    resolved, unresolved = [], []
    for item in spec["routing"]:
        hit = table.get(item["target"])
        if hit is None:
            unresolved.append(item["role"])
            continue
        resolved.append({"role": item["role"], "target": item["target"],
                         "employee_id": hit["employee_id"],
                         "code": hit["code"],
                         "display_name": hit["display_name"]})

    receipt = {
        "logical_id": spec["logical_id"],
        "release": env["release"],
        "resolved": resolved,
        "resolved_count": len(resolved),
        "resolved_sha256": hash_obj(resolved),
        "unresolved_ids": unresolved,
        "unresolved_count": len(unresolved),
        "left_count": len(spec["routing"]),
    }
    write_json(run_dir / "s3_routing_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 4
def compose_segments(spec_in: dict, spec: dict, routing: dict,
                     env: dict) -> list[tuple[str, str]]:
    """六段编译。模板骨架取自 references/prompt-segments.md 与 职能席.md。"""
    text = contract_text("prompt-segments.md")
    common_paras = parse_common_paragraphs(text)
    nonduty = parse_nonduty(text)
    reply_clause = parse_reply_targets_clause(text)
    labels = parse_skeleton_labels(text)

    identity = spec_in["identity"]
    function = spec_in["function"]
    permissions = spec_in["permissions"]
    domain = function.get("domain") or {}
    params = function.get("params") or {}
    routed = {row["role"]: row for row in routing["resolved"]}

    def target_line(role: str) -> str:
        row = routed.get(role)
        if row is None:
            return f"{role}：UNRESOLVED"
        return f"{role}：{row['code']} · {row['display_name']} · {row['employee_id']}"

    parent_row = routed.get("parent")
    parent_name = (f"{parent_row['code']} · {parent_row['display_name']}"
                   if parent_row else "直属企业大脑")

    seg1 = (f"{identity['code']} · {identity['display_name']}"
            f"（{identity['function_label']}）。上级：{parent_name}。")

    seg2 = (f"{function['responsibility']}\n"
            "工作方式：先复述问题与请求方身份，再按本域证据作答；"
            "证据不足时停在 UNVERIFIED，不补白。")

    kb_read = "、".join(permissions["kb_paths"]["value"]) or "无"
    kb_write = "、".join(permissions["kb_paths"].get("write_value", [])) or "无"
    workspace = domain.get("workspace") or {}
    tables = (params.get("landing_tables") or {}).get("domain_owned", [])
    table_lines = "；".join(
        f"{t['name']}（{t['app_id']} / {t['table_id']}，必填 "
        f"{'、'.join(t['required_fields'])}）" for t in tables) or "无"
    seg3 = (
        f"【本域】{domain.get('label', '')}（{domain.get('slug', '')}）。"
        f"本体角色 {domain.get('role_id', '')}。\n"
        f"【知识库】读：{kb_read}。写：{kb_write}（只写本域）。\n"
        f"【工作区】{workspace.get('display_name', '')}"
        f"（{workspace.get('ident', '')}，{workspace.get('uuid', '')}），"
        f"权限 {workspace.get('permission', '')}：登记本域产物，不覆盖他人已登记内容。\n"
        f"【落表】{table_lines}\n"
        "【快反三闸】条目存在 · 条目与问题匹配 · 条目带引用。"
        "三闸全过才作答；任一不过标 UNVERIFIED。三闸全过不推出可动真人世界，"
        "涉真人另走审批。\n"
        f"【升级路由】{target_line('escalation')}；须深度推理 → C1D；"
        f"{target_line('out_of_domain')}；{target_line('quick_lookup')}；"
        f"{target_line('approval')}。\n"
        f"【上级】{parent_name}：组织归属、汇报去向、冲突裁决三义同归。")

    if identity["kind"] == "restricted_domain":
        seg4 = ("本席只对访问策略内主体作答；非主体询问一律回复无权限并转 "
                f"{routed.get('out_of_domain', {}).get('code', 'UNRESOLVED')}；"
                "不透露域内条目存在与否。")
    else:
        seg4 = ("本席对全团队开放咨询；域外问题先转 "
                f"{routed.get('out_of_domain', {}).get('code', 'UNRESOLVED')} 再答。")

    arcu_lines = "；".join(f"{t['name']}（{t['app_id']} / {t['table_id']}，写）"
                           for t in tables) or "无"
    seg5 = ("【允许回报目标】\n"
            + "\n".join(target_line(role) for role in ROUTING_ROLES)
            + f"\n【ArcuBase】{arcu_lines}\n{reply_clause}")

    # 目录机制在这里落地，这是判断段 3.3 的唯一消费点。
    # 按 prompt-segments.md §五：挂载机制下提示词只留本席涉及的目标（上面那段
    # 就是），回退机制下目录回到提示词尾部。不接这一步的话两条分支编出的字节
    # 完全相同——回退被登记、被汇报、但对提示词没有任何作用，等于判断白做。
    if env["directory_fallback"]:
        roster = json.dumps(
            [{"logical_id": d["logical_id"], "employee_id": d["employee_id"],
              "code": d["code"], "display_name": d["display_name"]}
             for d in env["live_directory"]],
            ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        seg5 += f"\n{DIRECTORY_MARK}{roster}"

    human_extra = ("\n面向真人的回复先过三闸再过审批路由。"
                   if identity["human_facing"] else "")
    seg6 = ("\n\n".join(common_paras) + human_extra
            + "\n【思考骨架】"
            + f"{labels[0]}：先复述问题与请求方身份。"
            + f"{labels[1]}：取证先于结论，证据须带引用。"
            + f"{labels[2]}：动作限定在本域与本权限面内。"
            + f"{labels[3]}：输出结构固定，缺证据标 UNVERIFIED。\n"
            + nonduty)

    return list(zip(SEGMENT_IDS, [seg1, seg2, seg3, seg4, seg5, seg6]))


def stage_compile_prompt(run_dir: Path) -> dict:
    spec_in = read_json(run_dir / "input" / "seat.json", "SPEC_INCOMPLETE")
    spec = read_json(run_dir / "s1_spec_receipt.json", "SPEC_INCOMPLETE")
    env = read_json(run_dir / "s2_environment_receipt.json", "SPEC_INCOMPLETE")
    routing = read_json(run_dir / "s3_routing_receipt.json", "SPEC_INCOMPLETE")

    pairs = compose_segments(spec_in, spec, routing, env)
    body = "\n\n".join(text for _, text in pairs)

    segments = [{"id": sid, "chars": len(text), "sha256": hash_text(text)}
                for sid, text in pairs]

    text_full = contract_text("prompt-segments.md")
    nonduty = parse_nonduty(text_full)
    reply_clause = parse_reply_targets_clause(text_full)
    skeleton = [{"label": lab, "present": f"{lab}：" in body}
                for lab in SKELETON_LABELS]
    absent = [row["label"] for row in skeleton if not row["present"]]
    require(not absent, "SKELETON_MISSING", f"骨架标签未出现 {absent}")

    text_checks = [
        {"id": "nonduty_declaration", "present": nonduty in body},
        {"id": "reply_targets_clause", "present": reply_clause in body},
    ]
    bad = [row["id"] for row in text_checks if not row["present"]]
    require(not bad, "PROMPT_DRIFT", f"必出现原句缺失 {bad}")

    # 从自己编出的正文回读「内嵌了没有」，再与 s2 推导的机制对齐。
    # 回读而不是转抄 s2 的布尔值：转抄的话这一项永远与 s2 相等，钉不住
    # 「登记了回退但正文里没有目录」这件事——那正是本项要防的空转。
    embedded = DIRECTORY_MARK in body
    require(embedded == bool(env["directory_fallback"]), "DIRECTORY_FALLBACK_UNAPPLIED",
            f"环境段定的机制 {env['directory_mechanism']} 与提示词实况不符："
            f"正文{'含' if embedded else '不含'}内嵌目录")

    responsibility = spec_in["function"]["responsibility"]
    bio = responsibility.split("。")[0] + "。"
    require(len(bio) <= 120, "BIO_DRIFT", f"简介 {len(bio)} 字，超 120")
    require(body.find(responsibility) >= 0, "BIO_DRIFT", "职责句未进提示词")

    prompt_rel = "desired/effective-prompt.json"
    bio_rel = "desired/bio.json"
    write_json(run_dir / prompt_rel,
               {"logical_id": spec["logical_id"], "text": body})
    write_json(run_dir / bio_rel,
               {"logical_id": spec["logical_id"], "bio": bio})

    artifacts = []
    for name, rel in (("effective_prompt", prompt_rel), ("bio", bio_rel)):
        path = run_dir / rel
        artifacts.append({"id": name, "path": rel,
                          "bytes": path.stat().st_size,
                          "sha256": hash_file(path)})

    receipt = {
        "logical_id": spec["logical_id"],
        "release": env["release"],
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
        "directory_mechanism": env["directory_mechanism"],
        "directory_embedded": embedded,
        "text_check_count": len(text_checks),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifacts_sha256": hash_obj(artifacts),
    }
    write_json(run_dir / "s4_prompt_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 5
def stage_accept_images(run_dir: Path) -> dict:
    qa_path = run_dir / "handoff" / "image_qa.json"
    qa = read_json(qa_path, "IMAGE_NOT_REVIEWED")
    spec = read_json(run_dir / "s1_spec_receipt.json", "IMAGE_NOT_REVIEWED")

    require(qa.get("status") == "PASS", "IMAGE_NOT_REVIEWED",
            f"QA 闸状态 {qa.get('status')!r}")
    reviewer = str(qa.get("reviewer", ""))
    require(reviewer and reviewer != qa.get("generator"),
            "IMAGE_NOT_REVIEWED", "复核者缺失或与出图执行体同一")

    assets = []
    for name, rel in (("avatar", "images/avatar.png"), ("bio", "images/bio.png")):
        row = (qa.get("assets") or {}).get(name)
        require(isinstance(row, dict), "IMAGE_NOT_REVIEWED", f"缺 {name} 资产行")
        path = run_dir / rel
        require(path.exists(), "IMAGE_NOT_REVIEWED", f"缺图像件 {rel}")
        require(path.read_bytes()[1:4] == b"PNG", "IMAGE_NOT_REVIEWED",
                f"{rel} 非 PNG")
        local = hash_file(path)
        assets.append({
            "id": name, "path": rel,
            "width": int(row["width"]), "height": int(row["height"]),
            "approved": bool(row["approved"]),
            "sha256": local,
            "server_pixel_sha256": str(row["server_pixel_sha256"]),
            "local_pixel_sha256": str(row["local_pixel_sha256"]),
            "pixel_match": row["server_pixel_sha256"] == row["local_pixel_sha256"],
        })

    # QA 回执自报的面孔规则必须等于规格冻结的那个。不比的话，规格说复用、
    # 回执说生成也能过闸——两份文件各说各话，没有一处发现它们不一致。
    declared = str(spec.get("face_rule", ""))
    require(str(qa.get("face_rule", "")) == declared, "FACE_REUSE_UNVERIFIED",
            f"QA 回执面孔规则 {qa.get('face_rule')!r} 与规格 {declared!r} 不等")

    # 复用路径：规格指名的本地副本必须真的在盘上，且其字节哈希等于本段
    # 核过的头像件。缺这一条，local_copy 可以指向一个不存在的文件而全链绿。
    target_verified = declared == "generate"
    if declared == "reuse":
        rel = str(spec.get("face_local_copy", ""))
        copy_path = run_dir / rel
        require(rel and copy_path.exists(), "FACE_REUSE_UNVERIFIED",
                f"规格指名的复用件不在盘上：{rel!r}")
        copy_hash = hash_file(copy_path)
        require(copy_hash == assets[0]["sha256"], "FACE_REUSE_UNVERIFIED",
                f"复用件哈希 {copy_hash} 与头像件 {assets[0]['sha256']} 不等")
        target_verified = True

    require(len(assets) == int(qa["asset_count"]), "COUNT_MISMATCH",
            f"资产 {len(assets)} / QA 记 {qa['asset_count']}")
    unapproved = [a["id"] for a in assets if not a["approved"]]
    require(not unapproved, "IMAGE_NOT_REVIEWED", f"未勾 approved：{unapproved}")

    receipt = {
        "source_id": f"sha256:{hash_file(qa_path, 64)}",
        "logical_id": spec["logical_id"],
        "face_rule": str(qa["face_rule"]),
        "qa_status": str(qa["status"]),
        "reviewer": reviewer,
        "received_at": str(qa["reviewed_at"]),
        "receiver": str(qa["receiver"]),
        "target_verified": target_verified,
        "assets": assets,
        "asset_count": len(assets),
        "assets_sha256": hash_obj(assets),
        "avatar_sha256": assets[0]["sha256"],
        "bio_image_sha256": assets[1]["sha256"],
    }
    write_json(run_dir / "s5_image_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 6
def stage_apply_config(run_dir: Path) -> dict:
    log_path = run_dir / "handoff" / "config_writes.json"
    log = read_json(log_path, "CONFIG_WRITE_INCOMPLETE")
    spec = read_json(run_dir / "s1_spec_receipt.json", "CONFIG_WRITE_INCOMPLETE")

    spec_in = read_json(run_dir / "input" / "seat.json", "CONFIG_WRITE_INCOMPLETE")
    env = read_json(run_dir / "s2_environment_receipt.json", "CONFIG_WRITE_INCOMPLETE")

    # 声明要挂的技能必须真的在探针查到的技能目录里。
    # 不核的话，这一键可以声明挂载一个平台上不存在的技能、写记录自报 200 与
    # 回读相等，全链绿——两份数据可以永远互相矛盾而没有任何断言看得见。
    # 目录不可达时更要核：此时 live-directory 本就不在目录里，按 §3.3 走内嵌，
    # 它不该出现在挂载清单里。
    wanted = [str(s) for s in (spec_in["permissions"]["team_skills"].get("value") or [])]
    catalog = set(env.get("skill_catalog_ids") or [])
    absent = [s for s in wanted if s not in catalog]
    require(not absent, "SKILL_DRIFT",
            f"声明挂载的技能不在探针目录里：{absent}（目录 {sorted(catalog)}）")

    rows = {str(row["key"]): row for row in log.get("writes", [])}
    declared = {key["id"] for key in spec["keys"]}
    missing = sorted(declared - set(rows))
    require(not missing, "CONFIG_WRITE_INCOMPLETE", f"九键缺写记录 {missing}")
    alien = sorted(set(rows) - declared)
    require(not alien, "CONFIG_WRITE_INCOMPLETE", f"写记录含非九键 {alien}")

    keys, written, reused, failed = [], [], [], []
    for key in spec["keys"]:
        row = rows[key["id"]]
        status = int(row["http_status"])
        verified = bool(row["readback_equal"])
        if verified and status in (200, 201):
            bucket = "written"
        elif verified and status == 0:
            bucket = "reused"
        else:
            bucket = "failed"
        keys.append({"id": key["id"], "carrier": key["carrier"],
                     "http_status": status, "readback_equal": verified,
                     "bucket": bucket})
        {"written": written, "reused": reused, "failed": failed}[bucket].append(key["id"])

    employee_id = str(log["employee_id"])
    require(employee_id.startswith("de_"), "EMPLOYEE_MISSING",
            f"员工 id 形态非法：{employee_id!r}")

    receipt = {
        "logical_id": spec["logical_id"],
        "employee_id": employee_id,
        "create_mode": str(log["create_mode"]),
        "keys": keys,
        "key_count": len(keys),
        "keys_sha256": hash_obj(keys),
        "written": written, "written_count": len(written),
        "reused": reused, "reused_count": len(reused),
        "failed": failed, "failed_count": len(failed),
        # 核过的挂载清单落盘，供回读第 12 项「挂载清单相等」对账。
        "team_skills_declared": wanted,
    }
    write_json(run_dir / "s6_config_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 7
def stage_verify_readback(run_dir: Path) -> dict:
    probe_path = run_dir / "handoff" / "readback_probe.json"
    probe = read_json(probe_path, "READBACK_INCOMPLETE")
    spec = read_json(run_dir / "s1_spec_receipt.json", "READBACK_INCOMPLETE")
    config = read_json(run_dir / "s6_config_receipt.json", "READBACK_INCOMPLETE")
    image = read_json(run_dir / "s5_image_receipt.json", "READBACK_INCOMPLETE")

    # 两张图的回读项判的就是 accept_images 判过的那件事，只是换了时间点：
    # 那一段核上传前、这一段核落地后。不把两端拴住的话，探针自报 PASS 就是
    # PASS——它可以对一张根本不是本席的图说「相等」，本段照单全收。
    # 拴法：本地哈希必须等于 accept_images 实际哈希过的那份（同一个文件，
    # 换时间点不改字节）；自称 PASS 则两侧哈希必须真的相等，否则它在自打嘴巴。
    pixel_anchor = {"R13": image["assets"][0], "R14": image["assets"][1]}

    observed = {str(row["id"]): row for row in probe.get("items", [])}
    items, passed, failed, fallback = [], [], [], []
    for decl in spec["readback_items"]:
        row = observed.get(decl["id"])
        require(row is not None, "READBACK_INCOMPLETE", f"缺回读项 {decl['id']}")
        status = str(row["status"])
        require(status in ("PASS", "FAIL", "FALLBACK"), "READBACK_INCOMPLETE",
                f"{decl['id']} 状态非法 {status!r}")
        if status == "FALLBACK":
            require(decl["id"] == "R16", "READBACK_INCOMPLETE",
                    f"{decl['id']} 不允许 FALLBACK 态")
        anchor = pixel_anchor.get(decl["id"])
        if anchor is not None:
            local = str(row.get("local_pixel_sha256", ""))
            server = str(row.get("server_pixel_sha256", ""))
            require(bool(local) and bool(server), decl["code_on_fail"],
                    f"{decl['id']} 未给两侧像素哈希，无法与 accept_images 对账")
            require(local == anchor["local_pixel_sha256"], decl["code_on_fail"],
                    f"{decl['id']} 本地像素哈希 {local} 与 accept_images 核过的 "
                    f"{anchor['local_pixel_sha256']} 不等")
            require(status != "PASS" or server == local, decl["code_on_fail"],
                    f"{decl['id']} 自称 PASS 但服务端 {server} 与本地 {local} 不等")
        items.append({"id": decl["id"], "name": decl["name"], "status": status,
                      "code": "" if status == "PASS" else decl["code_on_fail"],
                      "evidence": str(row["evidence"]),
                      "local_pixel_sha256": str(row.get("local_pixel_sha256", "")),
                      "server_pixel_sha256": str(row.get("server_pixel_sha256", ""))})
        {"PASS": passed, "FAIL": failed, "FALLBACK": fallback}[status].append(decl["id"])

    receipt = {
        "logical_id": spec["logical_id"],
        "employee_id": config["employee_id"],
        "items": items,
        "item_count": len(items),
        "items_sha256": hash_obj(items),
        "pass_ids": passed, "pass_count": len(passed),
        "fail_ids": failed, "fail_count": len(failed),
        "fallback_ids": fallback, "fallback_count": len(fallback),
        # 探针自报的两张图本地哈希，按 R13/R14 序落盘，供契约钉到 accept_images
        # 实际哈希过的那两件。只钉本地侧：服务端侧不等本就是 R13 要报的失败，
        # 钉上去会把一个受支持的失败态变成审核崩溃。
        "pixel_local": [str(observed[i].get("local_pixel_sha256", ""))
                        for i in ("R13", "R14")],
        "config_pass": not failed,
    }
    write_json(run_dir / "s7_readback_receipt.json", receipt)
    return receipt


# ---------------------------------------------------------------- 段 8
def stage_finalize_delivery(run_dir: Path) -> dict:
    spec = read_json(run_dir / "s1_spec_receipt.json", "DELIVERY_INCOMPLETE")
    env = read_json(run_dir / "s2_environment_receipt.json", "DELIVERY_INCOMPLETE")
    prompt = read_json(run_dir / "s4_prompt_receipt.json", "DELIVERY_INCOMPLETE")
    image = read_json(run_dir / "s5_image_receipt.json", "DELIVERY_INCOMPLETE")
    config = read_json(run_dir / "s6_config_receipt.json", "DELIVERY_INCOMPLETE")
    readback = read_json(run_dir / "s7_readback_receipt.json", "DELIVERY_INCOMPLETE")

    gates = [
        {"id": "spec_complete", "passed": spec["block_count"] == 5},
        {"id": "carrier_complete",
         "passed": all(k["has_carrier"] for k in spec["keys"])},
        {"id": "environment_readable",
         "passed": all(p["http_status"] == 200 for p in env["probes"])},
        {"id": "image_qa", "passed": image["qa_status"] == "PASS"},
        {"id": "config_written", "passed": config["failed_count"] == 0},
        {"id": "readback_green", "passed": bool(readback["config_pass"])},
    ]
    blocked = [g["id"] for g in gates if not g["passed"]]

    readback_rel = "delivery/readback.json"
    manifest_rel = "delivery/manifest.json"
    write_json(run_dir / readback_rel, {
        "schema_version": "meta-agent-readback-09.20.1",
        "logical_id": readback["logical_id"],
        "employee_id": readback["employee_id"],
        "items": readback["items"],
    })
    write_json(run_dir / manifest_rel, {
        "schema_version": "meta-agent-manifest-09.20.1",
        "release": env["release"],
        "surface": "fde",
        "logical_id": spec["logical_id"],
        "employee_id": config["employee_id"],
        "seat_count": 1,
        "created": 1 if config["create_mode"] == "created" else 0,
        "reused": 1 if config["create_mode"] == "existing" else 0,
        "readback": {"pass": readback["pass_count"], "fail": readback["fail_count"],
                     "rows": "delivery/readback.json"},
        "images": {"requested": image["asset_count"],
                   "approved": image["asset_count"],
                   "qa": "handoff/image_qa.json"},
        # 目录机制回退是环境面的事，不是出图面的事。原先它挂在 images.fallback 上，
        # 与该块另外三键（请求数/通过数/QA 件）说的不是同一件事，交付面读到 1
        # 无从分辨「图重出过」还是「目录回退了」——两者处置完全不同。
        "directory_fallback": bool(env["directory_fallback"]),
        "config_completeness": round(
            (config["written_count"] + config["reused_count"]) / config["key_count"], 6),
        "blockers": blocked,
    })

    artifacts = []
    for name, rel in (("readback", readback_rel), ("manifest", manifest_rel)):
        path = run_dir / rel
        artifacts.append({"id": name, "path": rel,
                          "bytes": path.stat().st_size,
                          "sha256": hash_file(path)})

    receipt = {
        "logical_id": spec["logical_id"],
        "release": env["release"],
        "employee_id": config["employee_id"],
        "prompt_sha256": prompt["artifacts"][0]["sha256"],
        "avatar_sha256": image["avatar_sha256"],
        "gates": gates,
        "gate_count": len(gates),
        "gates_sha256": hash_obj(gates),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifacts_sha256": hash_obj(artifacts),
    }
    write_json(run_dir / "s8_delivery_receipt.json", receipt)
    return receipt


STAGES = {
    "freeze_spec": stage_freeze_spec,
    "accept_environment": stage_accept_environment,
    "resolve_routing": stage_resolve_routing,
    "compile_prompt": stage_compile_prompt,
    "accept_images": stage_accept_images,
    "apply_config": stage_apply_config,
    "verify_readback": stage_verify_readback,
    "finalize_delivery": stage_finalize_delivery,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="fde-meta-agent 生产段执行器")
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

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
        print(f"[FAIL] {args.stage}: 输入件字段缺失或类型不符（{exc}）",
              file=sys.stderr)
        return 1
    print(f"[OK] {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
