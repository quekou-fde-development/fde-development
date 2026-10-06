# 机械输入与落盘契约

本文件只约束候选运行目录中的文件形状、路径边界与回执。它不定义业务架构结论、文档质量或人工审核结论。

## 路径边界

- 每次调用都必须显式传入 `--run-dir`。运行脚本只可在该目录写入。
- `input/` 是调用方输入区。脚本不修改其中任何文件。
- `working/` 可容纳源快照、AI 的中间草稿和本契约声明的机械回执。
- `design/` 只容纳最终九份 Markdown；回执和 manifest 不得写入该目录。
- 运行根在操作系统临时目录的既有父级别名会先规范化为物理路径；从该运行根向下，任何目标文件、输入清单、源文件或目录链发现符号链接即拒绝。相对路径不得越出其允许根。
- `acquire_sources` 不覆盖既有快照或回执；`render_documents` 不覆盖既有九份目标文档。需要重跑时使用新的候选运行目录。

## `input/source_manifest.json`

`acquire_sources` 读取这个 JSON。它必须是普通 UTF-8 JSON 文件，且位于 `run-dir/input/`。

```json
{
  "schema_version": "1.0",
  "source_roots": [
    "sources"
  ],
  "sources": [
    {
      "id": "market-brief",
      "path": "sources/market-brief.md",
      "kind": "markdown"
    }
  ]
}
```

规则：

- `schema_version` 必须为字符串 `1.0`。
- `source_roots` 为非空字符串数组。相对根按 `input/` 解析；绝对根可用于用户指定的只读资料目录。
- `sources` 为非空数组；每个 `id` 仅允许字母、数字、连字符和下划线，且在数组内唯一。
- 每个 `path` 为字符串。相对路径按 `input/` 解析，绝对路径直接解析；解析后必须位于一个声明的 `source_roots` 中，且必须是普通文件。
- `kind` 为非空描述字符串，只入回执，不参与内容判断。
- `source_manifest.json` 自身、`working/` 与 `design/` 中的文件不可作为源资料。

## acquire_sources receipt

成功后，脚本读取每份指定源文件的原始字节，并写入：

- `working/sources/{id}.bin`：原始字节快照；
- `working/source_snapshot.json`：每个源的实际路径哈希、内容 SHA-256、字节数和快照相对路径；
- `acquire_sources_receipt.json`：本阶段的文件清单、文件哈希、数量和取数时刻。

`working/source_snapshot.json` 的每条源记录包含 `id`、`source_path_sha256`、`content_sha256`、`byte_count` 与 `snapshot_path`。其中 `source_path_sha256` 是 manifest 内声明的原始 `path` 定位字符串的 SHA-256；脚本仍在解析后实际读取受允许根约束的普通文件。这样同一候选运行目录被隔离复制时，来源定位证据保持可重放，内容 SHA-256 继续锁定实际字节。`acquire_sources_receipt.json` 的 `outputs` 列出 `working/source_snapshot.json` 和每一个实际快照；其 `outputs_sha256` 是该清单的稳定内容哈希。

## `working/render_request.json`

在资料快照完成后，AI 可以在 `working/` 内准备草稿。只有下列 JSON 文件可作为最终渲染输入：

```json
{
  "schema_version": "1.0",
  "unresolved_questions": [],
  "documents": {
    "01-concept.md": "AI 已准备的原样 Markdown 正文",
    "02-use-cases.md": "AI 已准备的原样 Markdown 正文",
    "03-data-model.md": "AI 已准备的原样 Markdown 正文",
    "04-security-privacy.md": "AI 已准备的原样 Markdown 正文",
    "05-site-architecture.md": "AI 已准备的原样 Markdown 正文",
    "06-page-layout.md": "AI 已准备的原样 Markdown 正文",
    "07-api.md": "AI 已准备的原样 Markdown 正文",
    "08-tech-stack-and-directory.md": "AI 已准备的原样 Markdown 正文",
    "09-implementation-roadmap.md": "AI 已准备的原样 Markdown 正文"
  }
}
```

规则：

- `schema_version` 必须为字符串 `1.0`。
- `unresolved_questions` 必须为数组。数组非空时拒绝最终渲染，不创建或改写 `design/`；脚本只写 `working/render_blocked.json`，其中原样记录该数组并标记 `WAITING_FOR_CLARIFICATION`。
- `documents` 必须恰有上面九个文件名，不能少、不能多；每个值必须是字符串。
- 每个正文必须含有非空白字符，且不得含 `TODO`、`TBD`、`FIXME`、`XXX`、`待填`、`待补`、`请填写`、`请补充`、`此处填写`、`此处补充`、`占位`、双花括号占位或双尖括号占位。这个词法检查不评价正文的架构正确性。
- 文档正文按字符串原样写入目标文件，不补标题、表格、ID、治理文件、结尾换行或任何业务内容。
- 顶层、代码围栏外的 Markdown 管道表格，表头与分隔行的列数必须相同；转义的 `\|` 作为单元格正文。发现不匹配时，在写入任何九份文件或渲染回执前报出文件与行号，退出码为 2。修正对应分隔行后重新渲染；原文内容不由脚本自动改写。这项检查只覆盖表头与分隔行列数，不宣称完整 Markdown 语法检查。
- 这份输入只代表 AI 已准备的正文；它不代表人工审核、架构正确性或发布批准。

## render_documents receipt

在 `unresolved_questions` 为空时，脚本创建下列九个普通文件：

```text
design/01-concept.md
design/02-use-cases.md
design/03-data-model.md
design/04-security-privacy.md
design/05-site-architecture.md
design/06-page-layout.md
design/07-api.md
design/08-tech-stack-and-directory.md
design/09-implementation-roadmap.md
```

随后脚本写入两个根目录回执：

- `render_input_receipt.json`：冻结 `working/render_request.json` 的路径、哈希和九份正文的哈希清单；
- `render_documents_receipt.json`：列出九份实际写出的文件、字节数和哈希，并固定记录 `review_status: PENDING_CHIEF_ARCHITECT_REVIEW`。

回执只证明输入、文件名、数量和实际落盘字节之间的对应关系。它不充当人工交接或人审通过证据。

## 审核与 manifest

每个阶段完成后，调用稳定审核器：

```text
python3 scripts/audit.py RUN_DIR --stage acquire_sources --contract assertions.json
python3 scripts/audit.py RUN_DIR --stage render_documents --contract assertions.json
python3 scripts/audit.py RUN_DIR --all --contract assertions.json --manifest RUN_DIR/run_manifest.json --package .
```

`run_manifest.json` 由最终全量审核写在运行目录根部。它记录机械断言的 PASS、FAIL 或未验证状态；它不记录人审通过。
