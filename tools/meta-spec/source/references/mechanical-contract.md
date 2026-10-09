# 机械输入与落盘契约

本文件约束候选运行目录中的文件形状、原参照结构、路径边界与回执。它不定义业务架构结论、文档质量或人工审核结论。

## 路径边界

- 每次调用都必须显式传入 `--run-dir`。运行脚本只可在该目录写入。
- `input/` 是调用方输入区。脚本不修改其中任何文件。
- `working/` 可容纳源快照、AI 的中间草稿和本契约声明的机械回执。
- `design/` 只容纳最终九份 Markdown；回执和 manifest 不得写入该目录。
- 运行根在操作系统临时目录的既有父级别名会先规范化为物理路径；从该运行根向下，任何目标文件、输入清单、源文件或目录链发现符号链接即拒绝。相对路径不得越出其允许根。
- `acquire_sources` 不覆盖既有快照或回执；`render_documents` 不覆盖既有九份目标文档。需要重跑时使用新的候选运行目录。
- 内容草稿先在 `working/` 修订并预览。`--preview` 仅适用于 `render_documents`，不改变两个 canonical stage 或最终回执结构。

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

资料快照与业务分析完成后，先由 `scripts/document_content.py --bindings` 从原参照和项目绑定生成空请求，再用 JSON 序列化工具填写。它只输出 JSON，不改写任何文件；调用方将其保存到本次 `working/render_request.json`。

顶层恰为四键：`schema_version: "2.0"`、`unresolved_questions` 数组、`structure_bindings` 对象和 `documents` 对象。`documents` 恰有九个指定文件名；每个文件的值是“固定章节标题 → 内容槽位”对象。保留脚本生成的键集合，编排顺序取自原参照，不取 JSON 键顺序。

每节都有 `text` 字符串，用于补充说明。按该节原参照的表达形式，脚本额外提供以下槽位：

- `tables`：按原参照表格顺序排列的数组，每项是一组数据行，每行是原表头顺序的字符串数组。只填数据，不填表头或分隔行。每张表至少一行，列数必须匹配；单元格不适用时明确写原因，不用空字符串。
- `items`：项目符号列表或场景步骤的正文字符串数组，至少一项。每项一行，不自行加项目符号或编号。
- `tree`：树形纯文本；脚本添加 `text` 代码围栏。
- `steps`：03 业务流四个固定标签各自的正文，一项一行；脚本添加编号和粗体标签。
- `labels`：09 阶段固定标签各自的正文；脚本生成独立标签行，值可用段落或列表。

例如角色表的内容槽位为 `{"text":"职责来源说明", "tables":[[["业务主管","Workbench","审批职责"],["执行员","Workbench","登记职责"]]]}`。表头、分隔行和标题由脚本补齐，此例仅演示输入形状，不能用作项目事实。

规则：

- `unresolved_questions` 非空时优先写 `working/render_blocked.json` 并以 rc3 停在澄清；不检查未填内容，不创建 `design/` 或渲染回执。
- 内容必须非空；只有文件引言、父分组节或已有表/列表/树/标签内容的 `text` 可以为空。不适用的固定节仍保留，填写原因和依据。
- `text` 和标签正文可以用段落、列表和闭合代码块，不能嵌入额外标题、表格、HTML 标题/表格或结构分隔符。代码示例不会生成额外章节。
- 数据行列数不符时，报出文件、章节、表号和行号并拒绝；脚本不猜测、补齐或删除业务值。所有校验在最终文件写入前完成。
- 表格单元格为未经预转义的原始字符串。编排时裁去首尾空白；`& < > \ |` 编为对应 HTML 实体，换行编为 `<br>`；字符串中的字面 `<br>` 被编码为文字，避免与换行混淆。表格固定列数不受内容字符影响。
- 固定标题、层级、顺序、表头、分隔行、项目符号、步骤编号、树围栏与固定标签全部由脚本生成。项目变量仅来自规定的 `structure_bindings`；同一绑定和同一内容产生字节一致的九份 Markdown。
- 渲染结果不得含 `TODO`、`TBD`、`FIXME`、`XXX`、`待填`、`待补`、`请填写`、`请补充`、`此处填写`、`此处补充`、`占位`、双花括号或双尖括号模板残留。
- 原参照 SHA-256 与结构契约不符时停止，不能自动更新参照指纹。输入版本、槽位、内容或结构不合格返回 rc2；完成返回 rc0。
- 这份输入不代表人工审核、业务正确性或发布批准。

## 工作区预览

执行 `python3 scripts/run_meta_stages.py --stage render_documents --preview --run-dir RUN_DIR`。与最终写出使用同一个编译函数，执行内容槽、占位残留、原参照结构、已知原生字段和 Markdown 表格检查。未决问题仍返回 rc3；其余不合格输入返回 rc2，任何预览文件写入前先校验全部输入和目标路径。

成功后只在 `working/previews/<本次 render_request 原始字节的完整 SHA-256>/` 写出 `design/` 九份预览和 `preview_receipt.json`。同版重复调用只接受已存在的相同字节；内容请求改变后使用新哈希目录，保留旧预览。最终渲染回执已存在时拒绝新预览。

预览回执为确定性 JSON，包含 `schema_version: "1.0"`、`kind: "CONTENT_REVIEW_PREVIEW"`、`status: "DRAFT_PREVIEW_NOT_REVIEWED"`、`source_id`、`request_sha256`、`document_count`、`documents`、`documents_sha256` 和能力限制 `limits`。documents 按固定九件顺序列出 `id/path/sha256/byte_count`，使用完整 SHA-256；documents_sha256 为该清单按 UTF-8、ensure_ascii=false、sort_keys=true、分隔符逗号和冒号序列化后的完整 SHA-256。回执没有自动生成的内容审核、业务正确性、总架构师批准或实施结论。

## `working/content_review_proof.json`

完整读取本版九份预览，并逐条回查原始要求、对象/事件/持久事实和跨文件一致性后，由实际复核者填写此 JSON。它是复核声明及其字节绑定，仍需总架构师审核。工程回归脚本中的合成声明仅用于机械夹具，不得用于真实项目。

顶层恰为以下十二键：

- `schema_version`：`"1.0"`。
- `decision`：`"CONTENT_REVIEW_COMPLETED"`。
- `scope`：`"CONTENT_ONLY"`。
- `reviewer`：实际复核者的非空身份声明。
- `reviewed_at`：实际复核完成时刻，带时区的 ISO 8601 字符串，不得晚于当前时间。
- `render_request_sha256`：当前 `working/render_request.json` 原始字节的完整 SHA-256。
- `preview_receipt_path`：本版预览回执的运行目录内相对路径。
- `preview_documents_sha256`：该预览回执的 documents_sha256。
- `source_snapshot_sha256`：`working/source_snapshot.json` 原始字节的完整 SHA-256。
- `coverage_path`：本次来源逐项复核记录的运行目录内相对路径，位于 `working/`；不能指向请求本身、声明本身、来源快照或预览文件。
- `coverage_sha256`：上述复核记录原始字节的完整 SHA-256。复核记录可在已有分析文件内，无须另造文档格式；写出每项原文位置、适用对象/事件、实际预览落点、结论，持久事实另写 field key 或已确认原生元数据、授权及写入/回读/验证位置。
- `field_checks`：数组；来源要求持久保存且采用业务字段承载的每个事实都对应一个条目。每项恰含非空 `table`（03 的实际表小节名）、`field_key`（该表字段行的稳定 key）、`source_anchor`（该事实的原始来源位置）。采用有证据的原生元数据时在复核记录中写明名称、语义及证据；没有此类业务字段时数组可为空，依据仍须留在复核记录。

用 JSON 序列化工具保存。内容请求或复核记录修订后，旧声明失效；应重新生成预览、完整核对受影响的要求及跨文件关系，再填写对应声明。不要通过更新哈希掩盖未重新复核的修订。

最终入口重新编译当前请求，核对声明与九份预览的每个实际字节、全部哈希、来源快照及复核记录；来源快照还须与实际 source_manifest、原始资料字节及 acquire_sources 回执一致。field_checks 引用的表和字段必须存在，其表名、field key 和 source_anchor 原样出现在本版逐项复核记录中。缺失、格式错误、越界、符号链接、陈旧或不一致时返回 rc2，停止创建最终文档。该检查无法证明自然语言要求登记的完整性、复核者确实读过内容、业务事实真伪或审核权限；这些仍由内容复核和独立测试负责。

写入前会检查全部目标路径；写入过程中发生 I/O 故障或并发冲突时可能留下部分文件，须保留失败记录并停止，不把残留文件视为成功候选。当前 artifact 流程要求单个执行者使用独立 run-dir，不提供多文件事务或并发写入承诺。

## render_documents receipt

在 `unresolved_questions` 为空、编译检查通过且本版内容复核声明与全部输入匹配时，脚本从当前请求重新编排并创建下列九个普通文件；不会直接复制预览作为答案：

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

- `render_input_receipt.json`：冻结 `working/render_request.json` 的路径、哈希和编排后九份正文的哈希清单；
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

## 结构检查

`render_documents` 在设计关键问题清零后、任何最终文件或渲染回执写入前，先由 `scripts/document_content.py` 按原参照编排固定格式，再由 `scripts/document_structure.py` 从随包原参照与 `structure_bindings` 生成预期结构。逐份检查固定标题、层级、顺序、重复单元、表格数量/表头/列序、所有表格行列数、必要树形代码块、列表和流程/阶段标签。结构错误返回具体文件与预期差异并阻断写出。

原参照和写作规则是结构权威；项目绑定只能替换规定的名称、重复项目和对应来源。禁止按已写出的正文反向修改绑定来消除差异。

全量审核中的 `render.structure` 会独立重读 `design/` 九份文件，以同一随包原参照和冻结渲染输入中的项目绑定重做结构检查；该断言不会用“与 AI 草稿相同”代替“与原参照结构相符”。结构不符返回 FAIL。正确字节落盘检查继续由现有断言负责。

## 内容回读

`render.content` 以冻结的 `working/render_request.json` 为内容依据，独立读取实际 `design/` 九份文件，逐节核对正文、列表项、树文本、流程步骤、阶段标签和表格数据行。审核器不导入生成器；它用独立实现按本契约的字面编码规则对账。内容被遗漏、错位、修改或新增，即使文件哈希和两份回执被一起重签，也必须返回 FAIL。

结构通过只能证明固定格式符合原参照；内容回读通过只能证明所填内容被保留。业务事实、权限决定、跨文件语义与平台行为继续由分析、澄清、总架构师审核及实施验证负责。

## 原生字段检查

03 的每张十一列字段表使用原参照已经列出的 FieldVO 类型代码。对已知的 `text`、`textarea`、`datetime`、`select` 类型，options 列填写 FieldVO.options 的 JSON 对象，来源文字放在该行的已确认约束列。text 的 type 为 text；textarea 显式给出布尔 html；datetime 的 type 为 date 或 datetime，并由业务要求决定精度；select 包含 options.mode=custom 与非空 options.items，每项含互不重复的整数 key 和非空文本 value。新 select 的选项键在设计时规划，既有字段按实读选项键保留。其他已证实类型的专属选项仍按来源与人工审核处理。

生成器在最终写入前检查这些约束，违反时返回 rc2 并定位表和字段。`render.native_fields` 独立解析实际 03 Markdown 的字段行和 JSON 选项；它不导入生成器，不依赖重新签署的文件哈希作为语义证明。不满足已知形状返回 FAIL；选项值是否符合业务、参数权限、默认值含义和真实平台行为仍需内容审核。
