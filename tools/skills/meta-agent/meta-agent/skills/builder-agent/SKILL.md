---
name: builder-agent
description: 按一份产品定义在 builder.autostaff.cn 市场面上架单个 Builder 产品，产出产品 worker、已发布版本与七项回读证据。用户交来产品定义或市场化请求并要求上架、建产品、建版本、发布、重新发布或改市场 worker 配置时调用；需要做租户无关性 lint、编译市场侧提示词、写 hasInitPhase 与 initSkill 与 promptSpec 与 quickStartPrompts 与 toolkitKeys 这五键、上传并扫描技能包、定秘密级别、发布版本或出升级计划时调用；需要把一个内部团队席位改写成可对外售卖的市场产品时调用。只管单产品单版本，批量由外层循环驱动；团队私有数字员工的编制与九键写入不在本 skill。
metadata:
  version: v1.0.0
  updated: 2026-09-20
  workflow_mode: artifact
---

# builder-agent

## 运行守卫

为每个产品建立独立 run 目录，把产品定义写入 `input/product.json`，把 run 目录绝对路径导出为 `BUILDER_RUN_DIR`；包外的席位规格与图谱保持只读。

一次运行只处理一个产品的一个版本。批量是外层对产品清单的循环，本 skill 不接受产品数组，也不在段内跨产品读写。

所有平台网络调用由你在段外先行执行，响应原样落 `handoff/` 下对应文件；段脚本只读落盘件、只做校验与出回执。段内禁止发起网络请求：隔离实跑会断网并摘掉夹具，段内留有外部依赖即当场失败。

段内不取墙钟。时间戳一律从输入件读取，保证同一份输入重跑得到同样的字节。

按下列主链执行，不得换序或跳段：

```text
freeze_definition
→ tenant_lint
→ compile_prompt
→ accept_worker
→ accept_version
→ accept_package_scan
→ accept_publish
→ finalize_delivery
```

序内两条硬依赖。其一，lint 必须早于编译：命中即停手交人改定义，先编译再删词会改变语义，且被删的词已经进过提示词副本。其二，写五键必须早于回读五键：回读的对照端是 compile_prompt 编译出的定义载荷，编译前它不存在，回读也就无从比对。两条来自 `references/builder-product.md §四 · 命令序列`，违反即回读第 1 项或第 2 项必失败。

每段落盘后立即审这一段，退出码 1 时阻断下游并保留失败原件，退出码 2 时修契约或调用方式，不重试覆盖。同一条确定性断言连续两次失败即停手，交出原因与证据，不进入第三次。计数按「段名 + 断言 id + 失败明细」三元组算，同一 run 目录内累计，不跨 run。一条断言覆盖多个键时按键分别计：同一键连续两次不符即停手，换了键的失败重新起算——两次都是同一个键说明改的方式不对，换了键说明是新问题。

## 一 · 输入准备

产品定义五块齐备才进入上架，顶层键逐字为 `identity`、`definition`、`package`、`publish`、`environment`。缺任一块即报 `SPEC_INCOMPLETE`；五块齐而 `definition` 内五键缺项报 `DEFINITION_INCOMPLETE`。两者都停在 freeze_definition 之前。lint 面不是输入块——它由身份三字段与定义两字段派生，见下条。五键的字段与类型见 `references/builder-product.md §二 · 五键定义`。

五键的 schema 归服务端所有。本 skill 先写后读，以平台回读为准，不在本地猜 schema、不在本地预校验字段名。写入被拒即报，不改写字段名重试。

lint 面是提交给市场的全部文本：六段提示词的取用段、欢迎词、快速起手词。逐行进 `lint_targets`，每行带稳定 id。lint 是 fail-closed 闸，命中即停，判据见 `references/builder-product.md §三 · 提示词编译（Builder 侧）`。

上架前先跑身份探针并把响应落 `handoff/auth_whoami.json`，取 `author_id` 与 `team_id`。探针的命令形态见 `references/builder-product.md §四 · 命令序列`。读不到即报 `AUTH_UNREADABLE`，不回落为写死值。

面孔件按 `references/image-handoff.md §二 · 请求单结构` 出请求单交 Codex，取回的成对 PNG 落 `images/`。出图执行体是 Codex，本 skill 不出图。视觉复核结论写入 `handoff/image_qa.json`，复核者字段必须是出图执行体以外的主体。

平台响应逐件落盘：建体响应写 `handoff/worker_create.json`，五键回读写 `handoff/version_config.json`，技能包扫描写 `handoff/package_scan.json`，发布状态写 `handoff/publish_state.json`，已雇实例清单写 `handoff/hired_instances.json`。

## 二 · 执行段（八段）

执行段：freeze_definition
动作：读 `input/product.json` 与 `handoff/auth_whoami.json`，冻结五块定义，逐块计哈希，展开五键、lint 逐行面、技能包文件清单与七项回读清单。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage freeze_definition --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/builder-product.md §二 · 五键定义` 与 `references/outputs.md §四 · Builder 侧回读（七项）`。
产出：`s1_definition_receipt.json` 写入 run 根。
值域：`source_id` 与 `product_id` 与 `author_id` 与 `team_id` 非空；`block_count` 为 5；`key_count` 为 5；`lint_target_count` 与 `package_file_count` 为正整数；`readback_item_count` 为 7；`declared_secret_level` 取自发布块；各 `sha256` 为 16 位小写十六进制。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + 五键类型 predicate replay(T1)。

执行段：tenant_lint
动作：把 lint 逐行面过租户无关性模式表，出集为零命中行，删除集为命中行并逐条登记 id，另逐字面量单独落账供审核器独立重算。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage tenant_lint --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/builder-product.md §三 · 提示词编译（Builder 侧）` 与 `s1_definition_receipt.json`。
产出：`s2_lint_receipt.json` 写入 run 根。
值域：`pattern_count` 为 4；`decision_count` 等于 freeze_definition 冻结的 `lint_target_count`；`clean_count` 与 `hit_count` 之和等于 `decision_count`；`hit_ids` 逐条可枚举且与 `clean_lines` 的 id 集不相交；零命中时 `hit_ids` 为空数组。
断言：output subset input(T1) + 逐字面量 predicate replay(T1) + 命中登记 predicate replay(T1) + excluded count set(T1) + count/hash(T1)。

执行段：compile_prompt
动作：取六段里的身份头、职责、席位特段与公共段四段，删域段与边约束，删目录句，把席位实体改写为角色称谓，附思考骨架与非职责声明，落定义载荷与提示词的权威副本。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage compile_prompt --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/prompt-segments.md §一 · 六段结构` 与 `references/prompt-segments.md §四 · 公共段 common 正文`。
产出：`s3_prompt_receipt.json` 写入 run 根；`desired/definition.json` 与 `desired/prompt.json` 写入 run 目录。
值域：`segment_count` 为 4 且段 id 为 identity、responsibility、seat_specific、common；`skeleton_count` 为 4 且四个骨架标签逐字出现；`text_check_count` 为 4 且 nonduty 与 no_tenant_entity 与 no_seat_code 与 role_rewritten 逐项为真；`artifact_count` 为 2；`prompt_bytes` 为正文的 UTF-8 字节数，是供人读的软闸读数、不设机器阈值——`references/prompt-segments.md §六` 的 3 KB 复核线没有段闸执行，超线不停手。
断言：row/column/sheet reconciliation(T1) + summary reconciliation(T1) + schema conformance(T1) + count/hash 与文件重读(T1) + 骨架与文本 predicate replay(T1) + output field coverage(T1)。

执行段：accept_worker
动作：读 `handoff/worker_create.json` 与 `handoff/image_qa.json` 与 `images/` 下成对 PNG，校验 worker 建体回执、逐张 approved、像素哈希两侧相等与图床主机。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_worker --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/image-handoff.md §五 · QA 闸` 与 `references/image-handoff.md §6.2 Builder 面`。
产出：`s4_worker_receipt.json` 写入 run 根。
值域：`worker_id` 非空且前缀为 bworker_；`author_id` 与 freeze_definition 逐字相等；`reviewer` 非空且不等于出图执行体；`asset_count` 为 2 且逐张 `approved` 与 `pixel_match` 为真；逐张 `url_host` 为 pub.autostaff.cn；逐件 `sha256` 为 16 位小写十六进制。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + approved 与像素相等 predicate replay(T1) + 图床主机 predicate replay(T1)。

执行段：accept_version
动作：读 `handoff/version_config.json`，逐键核五键写后即读，并接收本版与旧版的版本角色。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_version --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/builder-product.md §二 · 五键定义` 与 `desired/definition.json`。
产出：`s5_version_receipt.json` 写入 run 根。
值域：`version_id` 非空且前缀为 bwv_；`key_count` 为 5 且逐键 `written_equal` 为真、`http_status` 为 200；逐键 `type_name` 与五键类型表逐项相等；`version_count` 为正整数且 `role` 取 current 或 prior，current 恰有一条。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + 五键写读相等 predicate replay(T1) + 版本角色 predicate replay(T1)。

执行段：accept_package_scan
动作：读 `handoff/package_scan.json`，核技能包扫描的文件清单与计数，记录整包哈希。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_package_scan --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/builder-product.md §四 · 命令序列` 与 `s1_definition_receipt.json`。
产出：`s6_scan_receipt.json` 写入 run 根。
值域：`worker_id` 与 `version_id` 与上游回执逐字相等；`file_count` 等于 freeze_definition 冻结的 `package_file_count`；`files_sha256` 与 freeze_definition 的 `package_files_sha256` 逐字相等；`package_sha256` 非空。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + 文件清单 row/column/sheet reconciliation(T1)。

执行段：accept_publish
动作：读 `handoff/publish_state.json` 这份平台侧状态快照，把版本 id 集合按角色映射为挂牌态，核挂牌版指向本版、旧版已置 superseded、秘密级别等于声明值。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_publish --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/builder-product.md §六 · 升级语义` 与 `s5_version_receipt.json`。
产出：`s7_publish_receipt.json` 写入 run 根。
值域：出集版本 id 集合与 accept_version 的入集逐项相等；`state` 由 `role` 经查表映射，current 映 listed、prior 映 superseded；`listed_version_id` 等于本版 `version_id`；`secret_level` 与 `declared_secret_level` 相等且后者取自 freeze_definition。
断言：key row preservation(T1) + field function replay(T1) + count/hash(T1)。

执行段：finalize_delivery
动作：汇总七段回执出六道交付闸结论，落七项回读表、升级计划与整批 manifest，并把提示词与整包的哈希钉进交付回执。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage finalize_delivery --run-dir "$BUILDER_RUN_DIR"`。
依据：`references/outputs.md §四 · Builder 侧回读（七项）` 与 `references/outputs.md §五 · manifest`。
产出：`s8_delivery_receipt.json` 写入 run 根；`delivery/readback.json` 与 `delivery/upgrade-plan.json` 与 `delivery/manifest.json` 写入 run 目录。
值域：`gate_count` 为 6 且闸 id 为 lint_clean、five_keys_equal、scan_count_equal、images_approved、listed_is_current、prior_superseded；`readback_count` 为 7 且 id 为 B01 至 B07、`status` 取 PASS 或 FAIL；`prompt_sha256` 等于 compile_prompt 落的提示词件哈希；`package_sha256` 与 accept_package_scan 逐字相等；`artifact_count` 为 3。
断言：row/column/sheet reconciliation(T1) + summary reconciliation(T1) + count/hash 与文件重读(T1) + 闸位与回读 predicate replay(T1) + artifact hash(T1) + output field coverage(T1)。

## 三 · 判断段

判断段不进主链的机器审核面，结论由人或由独立复核者给出，落盘后再由执行段接收。

### 3.1 lint 命中处置

检索：读 `s2_lint_receipt.json` 的 `hit_ids`，逐条取原行文本、行 id 与命中的模式号。
整合：把命中分为租户资源代号、知识库路径与租户品牌名三类；三类在市场产品里是同一个泄露面，不按严重度分级。
生成：写命中清单，逐条给行 id、原文与命中模式，交人改产品定义。
审核：命中即 fail-closed，不自动删词——自动删改变语义，且改后的文本没有经过人对语义的确认；零命中才放行。
路由：命中则停手报 `TENANT_ENTITY_FOUND` 并回流定义端，改完从 freeze_definition 重跑；零命中则进 compile_prompt。

### 3.2 下沉技能包

检索：读六段原文与技能包清单，按「怎么做」与「是谁、边界在哪」两类逐段归类。
整合：长流程、步骤表、判据表属前者，下沉 `references/`；身份、职责、边界属后者，留提示词。
生成：提示词超 3 KB 时复核是否仍有可下沉段，并记录复核结论。超线由人读 compile_prompt 回执里的 `prompt_bytes`（正文 UTF-8 字节数）判定——没有断言拦这条线，段脚本不会因超线停手，不读就等于没复核。
审核：技能包正文由 meta-skill 编译，本 skill 只上传与扫描，不写包内容；越界写包即停手。
路由：复核通过则进 accept_package_scan；判为需重编包则退回 meta-skill，本 run 停在上传前。

### 3.3 视觉 QA 闸

检索：取本批请求单的目标计数与实际取回的资产计数，按逐张而非逐对读取图像。
整合：按身份与服装连续、配色、光线、品牌纹样、构图、有无可见文字六面逐张比对。
生成：写 `handoff/image_qa.json`，逐张给 `approved`，整体给 `status`。
审核：复核者不得是出图执行体自己；计数不符即 `COUNT_MISMATCH`；同一对里有一张不过即整对重出。
路由：全部 approved 且计数相符则进 accept_worker；任一不过则带原因重出，同一产品最多三轮；三轮不过升级人工，不得降低闸限放行。

### 3.4 回读失败处置

检索：分两种入口。主链中途硬停时（第 4、5、6 段各自可停），读 runner 打在 stderr 的失败码与该段 `handoff/` 原件——此时 `delivery/readback.json` 尚未产出，等它就是等一个不会来的文件；全链跑完在末段汇总报失败时，读 `delivery/readback.json` 的失败项。两入口取到的都是「失败码 + 原始响应」这一对，下面三相位不分入口。
整合：把失败项分为五键漂移、扫描计数不符、图像不符与发布态不符四类。
生成：写失败清单，逐项给失败码与保留的原件路径。
审核：任一项失败即整产品不判交付成功；失败原件保留，不重试覆盖。
路由：五键漂移退回 accept_version 重写该键并重新回读——重跑前把失败的 `handoff/version_config.json` 另存为 `handoff/version_config.<段名>-fail<n>.json`，再在原路径写新响应；段脚本只认原路径，留痕件不参与审核，两条规矩由此并存；扫描计数不符重传整包一次；图像不符重传一次，仍不等即报 `IMAGE_READBACK_MISMATCH` 并保留两份图；发布态不符即报 `LISTED_VERSION_DRIFT`，不自动补发布。

## 四 · 失败码与处置

| 失败码 | 触发 | 处置 |
|---|---|---|
| `INPUT_MISSING` / `INPUT_UNPARSEABLE` / `CONTRACT_MISSING` | 输入件缺失、非合法 JSON，或权威源文件不在包内 | 补齐该件后重跑本段，不跳段续跑 |
| `CONTRACT_DRIFT` | 权威源里的标记或结构已移动 | 停手，不按记忆里的旧值继续 |
| `SPEC_INCOMPLETE` | 产品定义五块缺任一 | 停在上架前，回流定义生成端补块 |
| `AUTH_UNREADABLE` | 身份探针读不到 author 或 team | 停手，不回落写死的 author 与 team |
| `DEFINITION_INCOMPLETE` | 五键缺任一 | 回流定义端补键，不留空上架 |
| `DEFINITION_TYPE` | 五键类型与类型表不符 | 回流定义端改类型，不本地强转 |
| `TENANT_ENTITY_FOUND` | lint 任一命中 | fail-closed 停手，交人改定义，不自动删词 |
| `SKELETON_MISSING` | 四个骨架标签未逐字出现 | 退回 compile_prompt 重编，不手工补字 |
| `PROMPT_DRIFT` | 提示词与权威副本不逐字节相等 | 以权威副本重写，不改副本迁就平台 |
| `WORKER_MISSING` / `WORKER_MISMATCH` | 建体回执缺 worker id，或配置件指向别的 worker | 停手核对建体回执，不改对照端迁就配置 |
| `IMAGE_MISSING` / `IMAGE_NOT_PNG` | 图像件不在 `images/`，或不是 PNG | 补件后重跑本段，不以占位图顶替 |
| `IMAGE_NOT_REVIEWED` | QA 闸未过即上传 | 硬拒上传，回视觉 QA 闸 |
| `IMAGE_HOST_UNEXPECTED` | 图像 URL 主机非 pub.autostaff.cn | 停手，不接受第三方图床 |
| `IMAGE_READBACK_MISMATCH` | 像素哈希两侧不等 | 重传一次，仍不等即保留两份图交人 |
| `VERSION_MISSING` / `VERSION_ROLE` | 配置件缺 version id，或版本清单里没有 current | 停手核对建版回执，不自造版本号 |
| `DEFINITION_DRIFT` | 五键写读不等 | 退回该键重写并重新回读，不改对照端 |
| `SCAN_FILES_MISMATCH` | 扫描回执的逐件指纹与冻结的上传清单不等 | 停手核对实际上传了什么，不以计数相符放行 |
| `SPEC_INCOMPLETE` | 产品定义缺 `identity` / `definition` / `package` / `publish` / `environment` 五个顶层块之一 | 停在 freeze_definition，回流定义端补块 |
| `DEFINITION_DRIFT` | accept_version 回读的五键与冻结值不等 | 停手核平台实际存了什么，不以本地值覆盖回读值 |
| `WORKER_MISSING` / `WORKER_MISMATCH` | 建体回执缺 worker id，或与上游回执不同 | 停手核平台实际建出了什么，不用预期 id 顶替 |
| `VERSION_MISSING` / `VERSION_ROLE` | 版本回执缺 version id，或版本清单里没有 current | 停手核版本实际状态，不自造版本号 |
| `VERSION_STATE_MISSING` | 版本清单里某版没有 `state` 字段 | 停手，不把缺状态当作 `superseded` |
| `IMAGE_MISSING` / `IMAGE_NOT_PNG` | 图像件不在 `images/` 下，或不是 PNG | 停手补件，不跳过该件上传 |
| `CONTRACT_MISSING` | 依据文件不在包内 | 停手核包完整性，不按记忆里的旧值继续 |
| `INPUT_MISSING` / `INPUT_UNPARSEABLE` | 本段所需的输入件缺失或不是合法 JSON | 停手取件，不把读不到当空值续跑 |
| `VERSION_MISMATCH` | 技能包扫描指向的版本与本版不符 | 停手，对准本版重扫，不接受别版的扫描结论 |
| `SCAN_COUNT_MISMATCH` | `file_count` 与上传清单不符 | 重传整包一次，不部分补传 |
| `VERSION_STATE_MISSING` | 发布回执里缺某个版本的状态 | 停手重取发布回执，不按预期值填 |
| `LISTED_VERSION_DRIFT` | 挂牌版不指向本版 | 停手交人，不自动补发布 |
| `SECRET_LEVEL_DRIFT` | 秘密级别与发布策略不符 | 停手交人，不自动改级别 |

## 五 · 人类汇报契约

每个产品上架结束向人汇报一次，顺序固定，不得换序：结果、影响、需要决定的问题、推荐项与理由、各选项后果、最短可复制回复、核验依据。无待决项时省略中间四项，直接给结果、影响与核验依据。

本次汇报依据的是真跑还是演练，写在首段第一句。演练指平台响应由人按形状自拟而非真实返回——此时故障是构造出来的，读者要决的是「这个缺陷排不排期修」而不是「这个产品现在上不上架」，两者不是同一个决定。把这句压进末尾核验依据，读者会按真故障批一个演练结果。

首段写这个产品上架了没有、市场上现在能看到什么、买家看到的是哪一版。执行未完成时首段必须写停在哪一段、已经在平台上留下了什么副作用、从哪里接着跑。

面向人的正文不出现状态码、字段名、哈希、回执名与段名。这些只进末尾核验依据；无法省略的术语在首次出现处用一句自然语言解释。

把技术件换成日常词时，换出来的词要带住那件东西管什么。提示词说成「开场白」就是换轻了：它是这个产品判断自己能做什么、不能做什么的依据，读者按寒暄去读，看不出改它等于改买家拿到手的那个东西的行为边界。术语解释与日常替换管的是同一件事——读者要能从正文里读出这件东西的分量，不能只读出它的名字。

待决项逐项写：问题是什么、推荐哪个、批准会发生什么、拒绝会发生什么、最短可复制的回复是什么。lint 命中与升级计划是最常见的两类待决项。

推荐项是「等」的时候，同一段里写清等什么条件成立、由谁判定成立、大致多久、等待期间有没有真实买家在等这个产品。只写「等恢复正常」读者批不下去：他批准的是一个没有终止条件的承诺，既排不了期也追不了责。

同时写清这次失败的影响面是本产品独有还是所有产品共有。共有而不写，读者按单产品处置，系统面的敞口就留在那里没人认领。

升级计划必须在正文里说清它是计划不是动作：发布新版不会自动升级已经雇了旧版的实例，升不升、什么时候升由租户自己定。把这一条写成既成事实即为错报。

末尾核验依据列出 run 目录路径、八段回执文件名、七项回读的通过与失败计数、提示词与整包的哈希前缀。机器层的枚举与人类层的汇报指向同一批事实，机器层不得替代人类层。

## 六 · 交付与批量

单产品交付物是一个市场 worker、一个已发布版本与完整回读证据。平台侧可见面是市场详情页的头像、亮相图、欢迎词、快速起手词与工具键。

`blockers` 非空即整批标未完成，已上架的产品不回滚。部分成功是正常态：一产品一版本的失败域就是本产品。

批量由外层驱动对产品清单循环调用本 skill，每产品一个 run 目录。同一 run 目录重跑即续跑，不新建目录；run 目录名含发布号，作幂等键成分。

已雇实例的升级动作归租户，本 skill 只出 `delivery/upgrade-plan.json`，逐实例一行且标记未执行。本 skill 不在租户侧执行升级。

## 七 · 夹具与未验证面

`fixtures/golden-market-product` 是一份市场产品的完整正例，由真跑八段产生，不是手写回执。其余目录各是该正例的整份副本改一处，每个带 `INJECTION.json` 指明它必须被哪条断言拒。

正例选的是租户中立的市场产品，因此它能过自己的 lint。lint 命中路径由定向 mutant 覆盖，不由正例覆盖。

夹具里 `images/` 下的 PNG 是程序生成的极小图像，尺寸与现网的 1024×1024 头像和 1536×896 亮相图不同。审核面只校验 PNG 魔数、文件哈希与回执自洽，不校验像素内容，因此小图不削弱断言强度；但夹具不构成对真实出图质量的证据。

租户无关性 lint 的三条模式里，后两条是纯字面量：知识库路径一条，租户名与品牌名一条。展开共四个字面量，其中长租户名被短租户名覆盖。这四个字面量由审核器逐行独立重算，与执行脚本的判定互为对照，不靠脚本自证。

第一条是带前导边界组与十六进制后缀的正则。断言谓词的比较词汇表是封闭的，只有相等、不等、属于、不属于与包含五个算子，没有正则算子，审核器无法独立重算这一条——它的命中判定只由执行脚本给出，属未验证面，不得当作已被机器证伪的面写进汇报。

这条残留面的方向是可说清的。把六个前缀拆成六个包含判定能补上一半：审核器由此能抓住脚本**虚报**命中，抓不住脚本**漏报**命中，因为前缀在场不等于整条正则成立。而 lint 存在的理由是防漏报——漏一个租户代号，它就随产品进了公开市场；虚报一个只是让人白改一行，且那一行就摆在人眼前。故这半边补进来也补的是代价轻的那半边，本包不补，把整条列为未验证面交人。

五键的 schema 归服务端，本包只做写后即读的一致性核验，不核验服务端是否接受某个字段名。旧版在发布后立即转 superseded 是实现期假设，首次现网运行时必须核；回读不符即报，不自动补 unlist。

提示词体积是一条**没有机器执行体的软闸**。`references/prompt-segments.md §六` 写着「超 3 KB 触发人工复核」，判断段 3.2 也写着超 3 KB 时复核可下沉段，但断言谓词词汇表只有等值与集合运算，没有数值比较 op，这条阈值写不成断言；段脚本也不为它停手。compile_prompt 落 `prompt_bytes`（正文 UTF-8 字节数）供人读，且该值由段脚本自报、无任何族从盘上的正文重算核它——把它改成 999 全部断言照样绿。谁来读、超线怎么办，是人的事。

本包 golden 的产品正文 1923 字节（1.88 KB），在线内。FDE 侧同一套六段模板编出的域席正文已达 3.61 KB，故这条线在 Builder 面没被触发过，不等于模板不会越线——产品定义写长即会。

首发产品没有旧版可退，此时 `prior_superseded` 闸对空集成立，闸值为真但没有查过任何东西。它与「查过旧版、确已退市」在交付回执里长得一样。判读时按 `version_count` 区分：只有一版即首发，该闸这一轮不提供退市证据。旧版被上游漏报不走这条路——那由 `VERSION_STATE_MISSING` 在 accept_publish 拦下。

## 八 · 权威源指针

| 共享件 | 权威源 | 运行时解析 |
|---|---|---|
| 五键、命令序列与先例事实 | `references/builder-product.md` | ✓ |
| 六段模板与思考骨架 | `references/prompt-segments.md` | ✓ |
| 出图请求单与 QA 闸 | `references/image-handoff.md` | ✗ |
| 产物目录、七项回读与 manifest | `references/outputs.md` | ✓ |
| 系列风格块正文 | `references/series-style-09.20.json` | ✗ |

本 skill 不复制上述正文。上表「运行时解析」列标 ✓ 的件由段脚本在运行时解析取值，其中的标记或行数一旦移动即报 `CONTRACT_DRIFT` 并停手，不按记忆里的旧值继续。

标 ✗ 的件只由人或 agent 在段外读，没有任何机器闸盯着它们——改动这些件不会触发 `CONTRACT_DRIFT`，漂移要靠读的人自己发现。把它们当成有机器保护的权威源是错的：真要让某一条判据受机器约束，得先让某个段脚本去解析它。
