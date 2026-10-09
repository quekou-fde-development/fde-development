#!/usr/bin/env python3
"""Mechanical artifact stages for meta-spec.

This module snapshots sources and compiles supplied business-content slots into
reference-derived Markdown. It does not decide or approve architecture content.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from document_structure import validate as validate_document_structure
from document_content import compile_documents
from datetime import datetime, timezone


DOCUMENT_NAMES = (
    "01-concept.md",
    "02-use-cases.md",
    "03-data-model.md",
    "04-security-privacy.md",
    "05-site-architecture.md",
    "06-page-layout.md",
    "07-api.md",
    "08-tech-stack-and-directory.md",
    "09-implementation-roadmap.md",
)
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
PLACEHOLDER_PATTERNS = (
    re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b", re.IGNORECASE),
    re.compile(r"(?:待填|待补|请填写|请补充|此处填写|此处补充|占位)"),
    re.compile(r"\{\{[^{}\n]+\}\}"),
    re.compile(r"<<[^<>\n]+>>"),
)


class ContractError(RuntimeError):
    """The supplied run directory does not satisfy the mechanical contract."""


class RenderBlocked(ContractError):
    """Questions remain for the chief architect; no final design files are written."""


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _short_file_hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:16]


def _content_hash(rows):
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(raw)[:16]


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2,
                       sort_keys=False) + "\n").encode("utf-8")


def _normal_absolute(value, label, must_exist=False, allow_parent_symlinks=False):
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} 必须为非空路径字符串")
    lexical = os.path.abspath(os.path.normpath(value))
    if not os.path.isabs(lexical):
        raise ContractError(f"{label} 解析后不是绝对路径")
    path = os.path.realpath(lexical)
    if not allow_parent_symlinks and path != lexical:
        raise ContractError(f"{label} 含符号链接: {lexical}")
    if must_exist and not os.path.exists(path):
        raise ContractError(f"{label} 不存在: {path}")
    return path


def _is_under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _relative_child(run_dir, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or os.path.isabs(relative) or ".." in relative.split("/")):
        raise ContractError(f"运行产物须为 run-dir 内相对路径: {relative!r}")
    target = os.path.abspath(os.path.normpath(os.path.join(run_dir, relative)))
    if not _is_under(target, run_dir) or target == run_dir:
        raise ContractError(f"运行产物路径越界: {relative}")
    _normal_absolute(target, f"运行产物 {relative}")
    return target


def _ensure_directory(path, label):
    _normal_absolute(path, label)
    missing = []
    cursor = path
    while not os.path.exists(cursor):
        missing.append(cursor)
        parent = os.path.dirname(cursor)
        if parent == cursor:
            raise ContractError(f"无法建立 {label}: {path}")
        cursor = parent
    if not os.path.isdir(cursor) or os.path.islink(cursor):
        raise ContractError(f"{label} 的既有父路径不是普通目录: {cursor}")
    for directory in reversed(missing):
        os.mkdir(directory)
        if os.path.islink(directory) or not os.path.isdir(directory):
            raise ContractError(f"{label} 建立后不是普通目录: {directory}")


def _ensure_relative_directory(run_dir, relative):
    path = _relative_child(run_dir, relative)
    _ensure_directory(path, f"目录 {relative}")
    return path


def _assert_regular(path, label):
    _normal_absolute(path, label, must_exist=True)
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ContractError(f"{label} 必须是普通文件: {path}")


def _read_bytes(path, label):
    _assert_regular(path, label)
    with open(path, "rb") as handle:
        return handle.read()


def _read_json(path, label):
    raw = _read_bytes(path, label)
    try:
        return json.loads(raw.decode("utf-8")), raw
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"{label} 不是有效 UTF-8 JSON: {error}") from error


def _write_new_or_identical(run_dir, relative, data):
    target = _relative_child(run_dir, relative)
    _ensure_directory(os.path.dirname(target), f"父目录 {relative}")
    if os.path.lexists(target):
        _assert_regular(target, f"既有产物 {relative}")
        if _read_bytes(target, f"既有产物 {relative}") == data:
            return False
        raise ContractError(f"拒绝覆盖内容不同的既有产物: {relative}")
    temporary = os.path.join(os.path.dirname(target),
                             f".{os.path.basename(target)}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temporary, "xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.lexists(target):
            raise ContractError(f"目标在写入期间出现，拒绝覆盖: {relative}")
        os.replace(temporary, target)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)
    _assert_regular(target, f"新产物 {relative}")
    return True


def _prepare_run_dir(run_dir):
    path = _normal_absolute(run_dir, "--run-dir", allow_parent_symlinks=True)
    _ensure_directory(path, "--run-dir")
    return _normal_absolute(path, "--run-dir", must_exist=True)


def _parse_source_path(value, base, label):
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} 必须为非空路径字符串")
    if "\\" in value:
        raise ContractError(f"{label} 不接受反斜杠路径")
    if os.path.isabs(value):
        raw = value
    else:
        if ".." in value.split("/"):
            raise ContractError(f"{label} 不接受上溯路径")
        raw = os.path.join(base, value)
    return _normal_absolute(raw, label, must_exist=True)


def _source_manifest(run_dir):
    input_dir = _ensure_relative_directory(run_dir, "input")
    path = _relative_child(run_dir, "input/source_manifest.json")
    _assert_regular(path, "input/source_manifest.json")
    manifest, raw = _read_json(path, "input/source_manifest.json")
    if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "source_roots", "sources"}:
        raise ContractError("source_manifest.json 须只含 schema_version、source_roots、sources")
    if manifest.get("schema_version") != "1.0":
        raise ContractError("source_manifest.json 的 schema_version 必须为 1.0")
    roots_value = manifest.get("source_roots")
    if (not isinstance(roots_value, list) or not roots_value
            or not all(isinstance(v, str) and v for v in roots_value)):
        raise ContractError("source_roots 必须为非空字符串数组")
    roots = []
    for index, root_value in enumerate(roots_value):
        root = _parse_source_path(root_value, input_dir, f"source_roots[{index}]")
        if not os.path.isdir(root) or os.path.islink(root):
            raise ContractError(f"source_roots[{index}] 必须指向普通目录: {root}")
        roots.append(root)
    rows = manifest.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ContractError("sources 必须为非空数组")
    sources, ids = [], set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"id", "path", "kind"}:
            raise ContractError(f"sources[{index}] 须只含 id、path、kind")
        source_id = row.get("id")
        if not isinstance(source_id, str) or not ID_RE.fullmatch(source_id):
            raise ContractError(f"sources[{index}].id 不符合安全文件名规则")
        if source_id in ids:
            raise ContractError(f"sources 的 id 重复: {source_id}")
        ids.add(source_id)
        if not isinstance(row.get("kind"), str) or not row["kind"].strip():
            raise ContractError(f"sources[{index}].kind 必须为非空字符串")
        source_path = _parse_source_path(row.get("path"), input_dir,
                                         f"sources[{index}].path")
        if not any(_is_under(source_path, root) for root in roots):
            raise ContractError(f"sources[{index}] 不在声明的 source_roots 中")
        if source_path == path:
            raise ContractError("source_manifest.json 不能把自身列为源资料")
        if _is_under(source_path, run_dir) and not _is_under(source_path, input_dir):
            raise ContractError("run-dir 内源资料只允许位于 input/，拒绝读取 working/ 或 design/")
        _assert_regular(source_path, f"sources[{index}].path")
        sources.append({"id": source_id, "path": source_path,
                        "declared_path": row["path"], "kind": row["kind"]})
    return path, raw, sources


def acquire_sources(run_dir):
    manifest_path, manifest_raw, sources = _source_manifest(run_dir)
    snapshot_rows = []
    snapshots = []
    for source in sources:
        raw = _read_bytes(source["path"], f"源资料 {source['id']}")
        rel = f"working/sources/{source['id']}.bin"
        snapshot_rows.append({
            "id": source["id"],
            "source_path_sha256": _sha256_bytes(source["declared_path"].encode("utf-8")),
            "content_sha256": _sha256_bytes(raw),
            "byte_count": len(raw),
            "snapshot_path": rel,
        })
        snapshots.append((rel, raw))
    snapshot = {
        "schema_version": "1.0",
        "source_manifest_sha256": _sha256_bytes(manifest_raw),
        "sources": snapshot_rows,
    }
    snapshot_bytes = _json_bytes(snapshot)
    # Validate all planned paths before creating any new artifact.
    planned = [("working/source_snapshot.json", snapshot_bytes), *snapshots]
    for rel, data in planned:
        target = _relative_child(run_dir, rel)
        if os.path.lexists(target):
            _assert_regular(target, f"既有快照 {rel}")
            if _read_bytes(target, f"既有快照 {rel}") != data:
                raise ContractError(f"拒绝覆盖内容不同的既有快照: {rel}")
    receipt_path = _relative_child(run_dir, "acquire_sources_receipt.json")
    if os.path.lexists(receipt_path):
        raise ContractError("acquire_sources_receipt.json 已存在；请使用新的候选运行目录")
    for rel, data in planned:
        _write_new_or_identical(run_dir, rel, data)
    outputs = []
    for rel, _data in planned:
        outputs.append({"id": rel, "kind": "file", "sha256": _short_file_hash(
            _relative_child(run_dir, rel))})
    receipt = {
        "stage": "acquire_sources",
        "source_id": "sha256:" + _sha256_bytes(manifest_raw),
        "fetched_at": _utc_now(),
        "source_count": len(sources),
        "output_count": len(outputs),
        "outputs_sha256": _content_hash(outputs),
        "outputs": outputs,
    }
    _write_new_or_identical(run_dir, "acquire_sources_receipt.json", _json_bytes(receipt))
    return {"stage": "acquire_sources", "status": "SNAPSHOT_COMPLETE",
            "source_count": len(sources), "output_count": len(outputs),
            "source_manifest": os.path.relpath(manifest_path, run_dir)}


def _render_request(run_dir):
    path = _relative_child(run_dir, "working/render_request.json")
    _assert_regular(path, "working/render_request.json")
    request, raw = _read_json(path, "working/render_request.json")
    if not isinstance(request, dict) or set(request) != {
            "schema_version", "unresolved_questions", "documents", "structure_bindings"}:
        raise ContractError("render_request.json 须只含 schema_version、unresolved_questions、documents、structure_bindings")
    if request.get("schema_version") != "2.0":
        raise ContractError("render_request.json 的 schema_version 必须为 2.0；正文须为结构化内容槽位")
    if not isinstance(request.get("unresolved_questions"), list):
        raise ContractError("unresolved_questions 必须为数组")
    documents = request.get("documents")
    if not isinstance(documents, dict):
        raise ContractError("documents 必须为九份文件的内容对象")
    if set(documents) != set(DOCUMENT_NAMES):
        missing = sorted(set(DOCUMENT_NAMES) - set(documents))
        extra = sorted(set(documents) - set(DOCUMENT_NAMES))
        raise ContractError(f"documents 文件名必须恰为九份目标；缺 {missing}，多 {extra}")
    return path, raw, request


def _table_cells(line):
    """Split GFM pipe cells, retaining escaped pipes inside a cell."""
    cells, current, escaped = [], [], False
    for char in line.strip():
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    if len(cells) > 1 and cells[0] == "":
        cells.pop(0)
    if len(cells) > 1 and cells[-1] == "":
        cells.pop()
    return cells


def _check_markdown_tables(name, body):
    previous = ""
    fence = None
    for number, line in enumerate(body.splitlines(), 1):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            previous = ""
            continue
        if fence is not None or line.startswith("    "):
            previous = ""
            continue
        cells = _table_cells(line)
        if ("|" in line and "|" in previous and cells
                and all(re.fullmatch(r":?-+:?", cell) for cell in cells)):
            header = _table_cells(previous)
            if len(header) != len(cells):
                raise ContractError(
                    f"documents.{name} 第 {number} 行 Markdown 表格分隔行为 {len(cells)} 列，"
                    f"表头为 {len(header)} 列；请修正分隔行后重新渲染")
        previous = line


def compile_request(request):
    """Compile and validate candidate bytes without writing a final artifact."""
    if request["unresolved_questions"]:
        raise RenderBlocked("存在未决问题；不能生成完整候选预览或最终文档")
    def reject_placeholders(value, where):
        if isinstance(value, str):
            if any(pattern.search(value) for pattern in PLACEHOLDER_PATTERNS):
                raise ContractError(where + " 含常见待填占位残留，不能作为最终文档")
        elif isinstance(value, dict):
            for key, item in value.items():
                reject_placeholders(item, where + "/" + str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                reject_placeholders(item, where + "/" + str(index))
    reject_placeholders(request["documents"], "documents")
    try:
        rendered = compile_documents(request["documents"], request["structure_bindings"])
    except (ValueError, TypeError, KeyError, OSError) as error:
        raise ContractError(str(error)) from error
    for name, body in rendered.items():
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(body):
                raise ContractError(f"documents.{name} 含常见待填占位残留，不能作为最终文档")
    errors = validate_document_structure(rendered, request["structure_bindings"])
    if errors:
        raise ContractError("文档结构不符合参照：\n" + "\n".join(errors))
    # Reject malformed tables before writing any final document or receipt.
    for name in DOCUMENT_NAMES:
        _check_markdown_tables(name, rendered[name])
    return rendered


def _full_content_hash(value):
    return _sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8"))


def _preview_material(request_raw, rendered):
    prefix = "working/previews/" + _sha256_bytes(request_raw)
    documents = []
    for filename in DOCUMENT_NAMES:
        data = rendered[filename].encode("utf-8")
        rel = prefix + "/design/" + filename
        documents.append({"id": filename, "path": rel,
                          "sha256": _sha256_bytes(data), "byte_count": len(data)})
    receipt = {
        "schema_version": "1.0",
        "kind": "CONTENT_REVIEW_PREVIEW",
        "status": "DRAFT_PREVIEW_NOT_REVIEWED",
        "source_id": "working/render_request.json",
        "request_sha256": _sha256_bytes(request_raw),
        "document_count": len(documents),
        "documents": documents,
        "documents_sha256": _full_content_hash(documents),
        "limits": "Mechanical compilation only. Content review, business semantics, chief architect approval and implementation are not evaluated.",
    }
    receipt_path = prefix + "/preview_receipt.json"
    planned = [(item["path"], rendered[item["id"]].encode("utf-8")) for item in documents]
    planned.append((receipt_path, _json_bytes(receipt)))
    return receipt_path, receipt, planned


def _preflight_writes(run_dir, planned):
    for rel, data in planned:
        target = _relative_child(run_dir, rel)
        cursor = target
        while not os.path.lexists(cursor):
            cursor = os.path.dirname(cursor)
        if cursor != target and not os.path.isdir(cursor):
            raise ContractError(f"产物父路径不是目录: {rel}")
        if os.path.lexists(target):
            if _read_bytes(target, f"既有产物 {rel}") != data:
                raise ContractError(f"拒绝覆盖内容不同的既有产物: {rel}")


def preview_documents(run_dir):
    """Compile an immutable working preview; do not certify business content."""
    for rel in ("render_input_receipt.json", "render_documents_receipt.json"):
        if os.path.lexists(_relative_child(run_dir, rel)):
            raise ContractError("最终渲染回执已存在；新的内容修订须使用新的候选运行目录")
    request_path, request_raw, request = _render_request(run_dir)
    rendered = compile_request(request)
    receipt_path, receipt, planned = _preview_material(request_raw, rendered)
    _preflight_writes(run_dir, planned)
    if _read_bytes(request_path, "working/render_request.json") != request_raw:
        raise ContractError("编译期间内容请求发生变化；未写预览，请核对请求后重试")
    for rel, data in planned:
        _write_new_or_identical(run_dir, rel, data)
    return {"status": "DRAFT_PREVIEW_NOT_REVIEWED", "document_count": receipt["document_count"],
            "preview_receipt": receipt_path, "request_sha256": receipt["request_sha256"]}


def _check_content_review(run_dir, request_raw, request, rendered):
    """Validate review bindings and declared fields, not the reviewer's judgment."""
    proof_path = _relative_child(run_dir, "working/content_review_proof.json")
    proof, proof_raw = _read_json(proof_path, "working/content_review_proof.json")
    keys = {"schema_version", "decision", "scope", "reviewer", "reviewed_at",
            "render_request_sha256", "preview_receipt_path", "preview_documents_sha256",
            "source_snapshot_sha256", "coverage_path", "coverage_sha256", "field_checks"}
    if not isinstance(proof, dict) or set(proof) != keys:
        raise ContractError("content_review_proof.json 键集合不符合机械合同")
    if (proof["schema_version"] != "1.0" or proof["decision"] != "CONTENT_REVIEW_COMPLETED"
            or proof["scope"] != "CONTENT_ONLY"):
        raise ContractError("需要本版内容复核完成声明；不能用总架构师批准或机械通过代替")
    if not isinstance(proof["reviewer"], str) or not proof["reviewer"].strip():
        raise ContractError("reviewer 须为非空的复核者声明")
    try:
        reviewed_at = datetime.fromisoformat(proof["reviewed_at"].replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None or reviewed_at > datetime.now(timezone.utc):
            raise ValueError("复核时间须带时区且不晚于当前时间")
    except (ValueError, TypeError, AttributeError) as error:
        raise ContractError("reviewed_at 须为实际已发生的带时区时间") from error
    receipt_path, receipt, planned = _preview_material(request_raw, rendered)
    if (proof["render_request_sha256"] != receipt["request_sha256"]
            or proof["preview_receipt_path"] != receipt_path
            or proof["preview_documents_sha256"] != receipt["documents_sha256"]):
        raise ContractError("内容复核声明与当前请求或预览不一致；重新预览并复核")
    # Recompile above and compare every preview byte. Never copy a preview into final design/.
    frozen_inputs = [(proof_path, proof_raw)]
    for rel, expected in planned:
        path = _relative_child(run_dir, rel)
        actual = _read_bytes(path, f"已复核预览 {rel}")
        if actual != expected:
            raise ContractError(f"已复核预览与当前编译结果不符: {rel}")
        frozen_inputs.append((path, actual))
    snapshot_path = _relative_child(run_dir, "working/source_snapshot.json")
    snapshot, snapshot_raw = _read_json(snapshot_path, "working/source_snapshot.json")
    if proof["source_snapshot_sha256"] != _sha256_bytes(snapshot_raw):
        raise ContractError("内容复核声明与来源快照不一致")
    frozen_inputs.append((snapshot_path, snapshot_raw))
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("sources"), list) or not snapshot["sources"]:
        raise ContractError("来源快照缺 sources")
    for row in snapshot["sources"]:
        if not isinstance(row, dict) or not isinstance(row.get("snapshot_path"), str):
            raise ContractError("来源快照条目格式错误")
        rel = row["snapshot_path"]
        if not rel.startswith("working/sources/"):
            raise ContractError("来源快照路径须在 working/sources/ 内")
        path = _relative_child(run_dir, rel)
        raw = _read_bytes(path, "原始来源快照")
        if _sha256_bytes(raw) != row.get("content_sha256") or len(raw) != row.get("byte_count"):
            raise ContractError("原始来源快照的字节与声明不符")
        frozen_inputs.append((path, raw))
    manifest_path, manifest_raw, sources = _source_manifest(run_dir)
    expected_sources = []
    for source in sources:
        original = _read_bytes(source["path"], f"实际来源 {source['id']}")
        expected_sources.append({
            "id": source["id"],
            "source_path_sha256": _sha256_bytes(source["declared_path"].encode("utf-8")),
            "content_sha256": _sha256_bytes(original), "byte_count": len(original),
            "snapshot_path": f"working/sources/{source['id']}.bin",
        })
        frozen_inputs.append((source["path"], original))
    if snapshot != {"schema_version": "1.0", "source_manifest_sha256": _sha256_bytes(manifest_raw),
                    "sources": expected_sources}:
        raise ContractError("内容复核来源快照与实际 source_manifest 或原始资料不一致")
    frozen_inputs.append((manifest_path, manifest_raw))
    acquired_path = _relative_child(run_dir, "acquire_sources_receipt.json")
    acquired, acquired_raw = _read_json(acquired_path, "acquire_sources_receipt.json")
    expected_outputs = [{"id": "working/source_snapshot.json", "kind": "file",
                         "sha256": _sha256_bytes(snapshot_raw)[:16]}]
    expected_outputs.extend({"id": row["snapshot_path"], "kind": "file",
                             "sha256": row["content_sha256"][:16]} for row in expected_sources)
    if (not isinstance(acquired, dict)
            or set(acquired) != {"stage", "source_id", "fetched_at", "source_count", "output_count", "outputs_sha256", "outputs"}
            or acquired.get("stage") != "acquire_sources"
            or acquired.get("source_id") != "sha256:" + _sha256_bytes(manifest_raw)
            or acquired.get("source_count") != len(expected_sources)
            or acquired.get("output_count") != len(expected_outputs)
            or acquired.get("outputs") != expected_outputs
            or acquired.get("outputs_sha256") != _content_hash(expected_outputs)
            or not isinstance(acquired.get("fetched_at"), str) or not acquired["fetched_at"].strip()):
        raise ContractError("内容复核来源与 acquire_sources 回执不一致")
    frozen_inputs.append((acquired_path, acquired_raw))
    rel = proof["coverage_path"]
    if (not isinstance(rel, str) or not rel.startswith("working/")
            or rel.startswith(("working/previews/", "working/sources/"))
            or rel in {"working/render_request.json", "working/source_snapshot.json", "working/content_review_proof.json"}):
        raise ContractError("coverage_path 须指向 working/ 内独立的来源逐项复核记录")
    path = _relative_child(run_dir, rel)
    raw = _read_bytes(path, "来源逐项复核记录")
    if not raw.strip() or _sha256_bytes(raw) != proof["coverage_sha256"]:
        raise ContractError("来源逐项复核记录为空或已变化")
    try:
        coverage_text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("来源逐项复核记录须为 UTF-8 文本") from error
    frozen_inputs.append((path, raw))
    checks = proof["field_checks"]
    if not isinstance(checks, list):
        raise ContractError("field_checks 须为数组；原生元数据等无字段项的依据写入覆盖记录")
    for index, check in enumerate(checks):
        if (not isinstance(check, dict) or set(check) != {"table", "field_key", "source_anchor"}
                or not all(isinstance(v, str) and v.strip() for v in check.values())):
            raise ContractError(f"field_checks[{index}] 须含非空 table、field_key、source_anchor")
        table = check["table"]
        if table not in request["structure_bindings"]["tables"]:
            raise ContractError(f"field_checks[{index}] 引用了未声明的表: {table}")
        rows = request["documents"]["03-data-model.md"][table]["tables"][0]
        if check["field_key"] not in {row[1].strip() for row in rows}:
            raise ContractError(f"field_checks[{index}] 声明的必要事实没有对应字段: {table}.{check['field_key']}")
        if any(check[key] not in coverage_text for key in ("table", "field_key", "source_anchor")):
            raise ContractError(f"field_checks[{index}] 的表、字段或来源位置未出现在本版逐项复核记录中")
    return frozen_inputs


def render_documents(run_dir):
    request_path, request_raw, request = _render_request(run_dir)
    questions = request["unresolved_questions"]
    if questions:
        blocked = {
            "status": "WAITING_FOR_CLARIFICATION",
            "reason": "UNRESOLVED_QUESTIONS",
            "source_id": "working/render_request.json",
            "unresolved_questions": questions,
        }
        _write_new_or_identical(run_dir, "working/render_blocked.json", _json_bytes(blocked))
        raise RenderBlocked("存在未决问题；已写 working/render_blocked.json，未写 design/")
    rendered = compile_request(request)
    review_inputs = _check_content_review(run_dir, request_raw, request, rendered)
    documents = []
    planned = []
    for name in DOCUMENT_NAMES:
        body = rendered[name].encode("utf-8")
        rel = f"design/{name}"
        documents.append({"id": name, "path": rel, "kind": "markdown",
                          "sha256": _sha256_bytes(body)[:16], "byte_count": len(body)})
        planned.append((rel, body))
    # The input receipt freezes the request before any final document is created.
    input_receipt = {
        "stage": "render_documents",
        "source_id": "working/render_request.json",
        "fetched_at": _utc_now(),
        "request_sha256": _sha256_bytes(request_raw)[:16],
        "document_count": len(documents),
        "documents_sha256": _content_hash(documents),
        "unresolved_questions_count": 0,
        "documents": documents,
    }
    output_receipt = {
        "stage": "render_documents",
        "source_id": "working/render_request.json",
        "fetched_at": _utc_now(),
        "document_count": len(documents),
        "documents_sha256": _content_hash(documents),
        "unresolved_questions_count": 0,
        "review_status": "PENDING_CHIEF_ARCHITECT_REVIEW",
        "documents": documents,
    }
    # Check every eventual write first. Existing byte-identical final documents are
    # accepted for resumable verification but are never rewritten.
    _preflight_writes(run_dir, planned)
    for rel in ("render_input_receipt.json", "render_documents_receipt.json"):
        if os.path.lexists(_relative_child(run_dir, rel)):
            raise ContractError(f"{rel} 已存在；请使用新的候选运行目录")
    for path, raw in [(request_path, request_raw), *review_inputs]:
        if _read_bytes(path, "写入前输入复查") != raw:
            raise ContractError("写入前输入已变化；停止最终渲染")
    for rel, data in planned:
        _write_new_or_identical(run_dir, rel, data)
    _write_new_or_identical(run_dir, "render_input_receipt.json", _json_bytes(input_receipt))
    _write_new_or_identical(run_dir, "render_documents_receipt.json", _json_bytes(output_receipt))
    return {"stage": "render_documents", "status": "PENDING_CHIEF_ARCHITECT_REVIEW",
            "document_count": len(documents),
            "request": os.path.relpath(request_path, run_dir)}


STAGES = {
    "acquire_sources": acquire_sources,
    "render_documents": render_documents,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    if args.preview and args.stage != "render_documents":
        parser.error("--preview 只用于 render_documents")
    try:
        run_dir = _prepare_run_dir(args.run_dir)
        if args.preview:
            result = preview_documents(run_dir)
        else:
            result = STAGES[args.stage](run_dir)
    except RenderBlocked as error:
        print(str(error), file=sys.stderr)
        return 3
    except ContractError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
