---
name: fde-meta-agent
description: 按一份席位规格在 fde.autostaff.cn 团队面编制单个团队私有数字员工，产出员工实体与十六项回读证据；回读留证是本 skill 的固定产物，用户不必单独提出。用户交来席位规格、图谱节点或域参数包并要求建号、编制、配置、上线、重建或补配数字员工时调用；需要写入或补写提示词、简介、工具键、模型与思考、访问策略、KB 读写路径、工作区授权、汇报线、团队技能这九键中任意一项时调用，无论用户有没有明说要留证；需要给某一席配面孔件时调用，含复用旧头像、收下 Codex 出的头像与亮相图、过视觉 QA 闸、核对上传前后的像素哈希；需要把 09.16 的旧席位重编为新发布号身体时调用。只管单席单体，批量由外层循环驱动；出图本身由 Codex 执行，市场侧 Builder 产品与版本发布也不在本 skill。
metadata:
  version: v1.0.0
  updated: 2026-09-20
  workflow_mode: artifact
---

# fde-meta-agent

## 运行守卫

为每一席建立独立 run 目录，把该席规格写入 `input/seat.json`，把 run 目录绝对路径导出为 `FDE_RUN_DIR`；包外的图谱与域参数包保持只读。

一次运行只处理一席。批量是外层对席位清单的循环，本 skill 不接受席位数组，也不在段内跨席读写。

所有平台网络调用由你在段外先行执行，响应原样落 `handoff/` 下对应文件；段脚本只读落盘件、只做校验与出回执。段内禁止发起网络请求：隔离实跑会断网并摘掉夹具，段内留有外部依赖即当场失败。

段内不取墙钟。时间戳一律从输入件读取，保证同一份输入重跑得到同样的字节。

按下列主链执行，不得换序或跳段：

```text
freeze_spec
→ accept_environment
→ resolve_routing
→ compile_prompt
→ accept_images
→ apply_config
→ verify_readback
→ finalize_delivery
```

序内两条硬依赖：建体必须早于九键写入，因为访问策略决定后续资源能否被挂载读取；终版提示词必须最后写，因为它引用的平台 id 必须已存在。这两条来自 `references/outputs.md §二 · 写入序列（九步）`，违反即回读第 2 项必失败。

每段落盘后立即审这一段，退出码 1 时阻断下游并保留失败原件，退出码 2 时修契约或调用方式，不重试覆盖。同一条确定性断言连续两次失败即停手，交出原因与证据，不进入第三次。计数按「段名 + 断言 id + 失败明细」三元组算，同一 run 目录内累计，不跨 run。一条断言覆盖多个键时按键分别计：同一键连续两次不符即停手，换了键的失败重新起算——两次都是同一个键说明改的方式不对，换了键说明是新问题。

## 一 · 输入准备

规格五块齐备才进入编制：身份块、职能块、权限块、面孔块、环境块。缺任一块即报 `SPEC_INCOMPLETE` 并停在 freeze_spec 之前。五块字段表见 `references/seat-spec.md §一 · 全貌`。

九键每键必须带 `carrier` 写路由。任一键找不到写路由即拒编，不得把该键标记为「后续手工处理」——不可落地的配置项在规格层就该被挡住，判据见 `references/seat-spec.md §四 · permissions 块（九键）`。

环境块是唯一允许运行时变化的块。两类环境故障分界明确，不可混判：探针本身没拿到响应（非 200）时报 `ENVIRONMENT_UNREADABLE` 并停手，此时不知道世界是什么样，没有依据可推导，更不得回落为写死的目录值；探针拿到了 200 响应、而技能目录里没有该挂载技能时，这是「已知它不在」，按判断段 3.3 登记 `DIRECTORY_FALLBACK` 并改走内嵌机制。前者是无知，后者是知情，处置因此不同。

目录机制不收探针的自报值：段内按技能目录里有无 `references/prompt-segments.md §五` 声明的挂载技能推导。探针可以自报机制，但只能与推导一致，不一致即报 `ENVIRONMENT_UNREADABLE` 停手。

编制前先跑两个平台探针并落盘：员工目录与技能目录。两者的响应合并写入 `handoff/environment_probe.json`，`live_directory` 逐项带逻辑键与平台 id。

面孔件按规格的 `face.rule` 准备：`reuse` 时把既有图像的本地副本放进 `images/`，`generate` 时按 `references/image-handoff.md §二 · 请求单结构` 出请求单交 Codex，取回的成对 PNG 同样落 `images/`。出图执行体是 Codex，本 skill 不出图。

视觉复核结论写入 `handoff/image_qa.json`，复核者字段必须是出图执行体以外的主体。

九键写入的逐键响应写入 `handoff/config_writes.json`，十六项回读的逐项结论写入 `handoff/readback_probe.json`。

## 二 · 执行段（八段）

执行段：freeze_spec
动作：读 `input/seat.json`，冻结五块规格，逐块计哈希，展开九键、参数包六维、五个路由去向与十六项回读清单。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage freeze_spec --run-dir "$FDE_RUN_DIR"`。
依据：`references/seat-spec.md §一 · 全貌` 与 `references/outputs.md §三 · 回读项（FDE 十六项）`。
产出：`s1_spec_receipt.json` 写入 run 根。
值域：`source_id` 非空；`block_count` 为 5；`face_rule` 取 reuse 或 generate，取 reuse 时 `face_local_copy` 非空；`key_count` 为 9；`dim_count` 为 6；`routing_count` 为 5；`readback_item_count` 为 16；各 `sha256` 为 16 位小写十六进制。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + 九键写路由 predicate replay(T1)。

执行段：accept_environment
动作：读 `handoff/environment_probe.json`，校验两个探针的 HTTP 状态与目录非空，接收现役员工目录、模型目录与技能目录，并按技能目录里有无挂载技能推导目录机制。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_environment --run-dir "$FDE_RUN_DIR"`。
依据：`references/seat-spec.md §六 · environment 块` 与 `s1_spec_receipt.json`。
产出：`s2_environment_receipt.json` 写入 run 根。
值域：`team_id` 与 `release` 非空；`probe_count` 为 2 且每项 `http_status` 为 200；`directory_count` 为正整数；`logical_id` 在目录内唯一；`directory_mechanism` 由 `skill_catalog_ids` 是否含 `directory_skill` 推导，取 mounted_skill 或 prompt_embedded，探针自报值若存在须与之逐字相等。
断言：source receipt(T1) + schema conformance(T1) + count/hash(T1) + 探针状态 predicate replay(T1)。

执行段：resolve_routing
动作：把规格里五个路由去向按逻辑键连接现役目录，解析出平台员工 id，解析不到的登记为未解析。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage resolve_routing --run-dir "$FDE_RUN_DIR"`。
依据：`references/outputs.md §1.1 identities 对账表` 与 `s2_environment_receipt.json`。
产出：`s3_routing_receipt.json` 写入 run 根。
值域：`resolved_count` 与 `unresolved_count` 之和为 5；每项 `role` 取自 parent、quick_lookup、escalation、out_of_domain、approval 且全表唯一；已解析项的 `employee_id` 非空。
断言：key coverage(T1) + cardinality(T1) + unmatched set(T1) + joined value replay(T1)。

执行段：compile_prompt
动作：按六段模板编译提示词全文，按环境段定的目录机制决定第五段是否内嵌现役员工目录，派生简介，逐段计哈希并落提示词与简介的权威副本。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage compile_prompt --run-dir "$FDE_RUN_DIR"`。
依据：`references/prompt-segments.md §一 · 六段结构` 与 `references/prompt-segments.md §四 · 公共段 common 正文`。
产出：`s4_prompt_receipt.json` 写入 run 根；`desired/effective-prompt.json` 与 `desired/bio.json` 写入 run 目录。
值域：`segment_count` 为 6；`skeleton_count` 为 4 且四个骨架标签逐字出现；非职责声明与回报目标声明两句逐字出现；简介非空、不超过 120 字且与职责首句逐字一致；`artifact_count` 为 2；`directory_mechanism` 与 accept_environment 逐字相等；`directory_embedded` 由正文有无 `【现役员工目录】` 标记回读得出，须与 accept_environment 的 `directory_fallback` 相等。`prompt_bytes` 为正文的 UTF-8 字节数，是供人读的软闸读数、不设机器阈值——`references/prompt-segments.md §六` 的 3 KB 复核线没有段闸执行，超线不停手。
断言：row/column/sheet reconciliation(T1) + summary reconciliation(T1) + schema conformance(T1) + count/hash 与文件重读(T1) + 骨架与文本 predicate replay(T1) + output field coverage(T1)。

执行段：accept_images
动作：读 `handoff/image_qa.json` 与 `images/` 下成对 PNG，校验 QA 闸结论、逐张 approved、计数相符与像素哈希两侧相等；把回执自报的面孔规则与 freeze_spec 冻结的规格值比对，复用路径另核规格指名的本地副本在盘上且字节哈希等于头像件。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage accept_images --run-dir "$FDE_RUN_DIR"`。
依据：`references/image-handoff.md §五 · QA 闸` 与 `references/image-handoff.md §6.1 FDE 面`。
产出：`s5_image_receipt.json` 写入 run 根。
值域：`qa_status` 为 PASS；`face_rule` 与 freeze_spec 的 `face_rule` 逐字相等；`target_verified` 在复用路径由本地副本比对结果决定，不是常量；`asset_count` 为 2 且逐张 `approved` 为 true；`reviewer` 非空且不等于出图执行体；头像与亮相图的服务端像素哈希与本地相等；两件 `sha256` 为 16 位小写十六进制。
断言：artifact hash 双件(T1) + schema conformance(T1) + count/hash(T1) + approved 与像素相等 predicate replay(T1) + receiver receipt(T1) + 面孔规则与规格 compare_paths(T1)。

执行段：apply_config
动作：读 `handoff/config_writes.json`，先核规格声明要挂的团队技能确实在探针查到的技能目录里，再把九键逐键归入已写、已复用或失败三桶，并核对写后即读的深比较结论。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage apply_config --run-dir "$FDE_RUN_DIR"`。
依据：`references/outputs.md §二 · 写入序列（九步）` 与 `s1_spec_receipt.json`。
产出：`s6_config_receipt.json` 写入 run 根。
值域：`key_count` 为 9；三桶并集等于九键全集且两两不相交；`employee_id` 非空；`team_skills_declared` 每一项都出现在 accept_environment 落的 `skill_catalog_ids` 里；`config_completeness` 为 0 到 1 之间保留六位小数的数。
断言：union completeness(T1) + pairwise disjoint(T1) + assignment rule replay(T1) + schema conformance(T1) + count/hash(T1)。

执行段：verify_readback
动作：读 `handoff/readback_probe.json`，逐项核十六项回读，按通过与失败分桶并核对两桶可独立枚举；两张图的回读项另与 accept_images 核过的本地像素哈希对账。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage verify_readback --run-dir "$FDE_RUN_DIR"`。
依据：`references/outputs.md §三 · 回读项（FDE 十六项）` 与 `s1_spec_receipt.json`。
产出：`s7_readback_receipt.json` 写入 run 根。
值域：`item_count` 为 16；第 13、14 项必须带两侧像素哈希，其本地侧与 accept_images 核过的逐字相等，自称 PASS 时两侧也必须相等；`pass_count` 与 `fail_count` 与 `fallback_count` 三者之和为 16；三桶 id 并集等于 freeze_spec 冻结的十六项 id 全集且两两不相交；每项 `status` 取 PASS、FAIL 或 FALLBACK，FALLBACK 仅第 16 项可取且须已登记目录回退；`config_pass` 仅由 `fail_count` 为 0 决定，登记过的回退不拉低它。
断言：detail recomputation(T1) + total reconciliation(T1) + each bucket independently enumerable(T1) + schema conformance(T1) + count/hash(T1) + 像素哈希与 accept_images compare_paths(T1)。

执行段：finalize_delivery
动作：汇总七段回执出交付闸结论，落回读表与整批 manifest，并把提示词与头像的哈希钉进交付回执。
副作用：run_dir_only
可达接口：运行 `python3 scripts/execute_stage.py --stage finalize_delivery --run-dir "$FDE_RUN_DIR"`。
依据：`references/outputs.md §五 · manifest` 与 `s7_readback_receipt.json`。
产出：`s8_delivery_receipt.json` 写入 run 根；`delivery/readback.json` 与 `delivery/manifest.json` 写入 run 目录。
值域：`gate_count` 为 6 且闸 id 为 spec_complete、carrier_complete、environment_readable、image_qa、config_written、readback_green；`employee_id` 与 `logical_id` 与上游回执逐字相等；`prompt_sha256` 等于 compile_prompt 落的提示词件哈希；`avatar_sha256` 等于 accept_images 核过的头像件哈希；`artifact_count` 为 2。
断言：row/column/sheet reconciliation(T1) + summary reconciliation(T1) + count/hash 与文件重读(T1) + 闸位 predicate replay(T1) + artifact hash 双件(T1) + output field coverage(T1)。

## 三 · 判断段

判断段不进主链的机器审核面，结论由人或由独立复核者给出，落盘后再由执行段接收。

### 3.1 面孔规则裁定

检索：读规格 `face` 块、09.14 交付清单与该逻辑席的历史图像资产；确认是否存在同名同身份的既有头像。
整合：把既有资产的本地副本与服务端 URL 并列，逐件算字节哈希；同名复用的判据是身份与服装连续，不是文件名相同。
生成：`rule=reuse` 时写复用记录并给出本地副本路径；`rule=generate` 时按 `references/image-handoff.md §二 · 请求单结构` 出请求单，系列风格块整块引用不逐席改写。
审核：复用路径必须给 `local_copy` 并做字节比对，不比对即 `FACE_REUSE_UNVERIFIED`；生成路径必须带三参考图且提示词含不借其脸的原句，缺任一即退回重建请求单。
路由：判为复用则给出规格里的 `local_copy` 再进 accept_images——该段会核它在盘上且字节等于头像件，缺件或不等即 `FACE_REUSE_UNVERIFIED`；判为生成则先交 Codex 出图，回图后进视觉 QA 闸；两者都判不成立时标该席 `SPEC_REQUIRES_HUMAN` 并停止本席编制。

### 3.2 视觉 QA 闸

检索：取本批请求单的目标计数与实际取回的资产计数，按逐张而非逐对读取图像。
整合：按身份与服装连续、配色、光线、品牌纹样、构图、有无可见文字六面逐张比对。
生成：写 `handoff/image_qa.json`，逐张给 `approved`，整体给 `status`。
审核：复核者不得是出图执行体自己；计数不符即 `COUNT_MISMATCH`；同一对里有一张不过即整对重出。
路由：全部 approved 且计数相符则置 `status=PASS` 进上传；任一不过则带原因重出，同一席最多三轮；三轮不过升级人工，不得降低闸限放行。

### 3.3 目录机制回退

检索：读 accept_environment 的技能目录探针结果，确认团队技能可达。本段的前置是探针已取到 200 响应——探针非 200 时由 `ENVIRONMENT_UNREADABLE` 在 accept_environment 硬停，本段不接那条路。
整合：把提示词内嵌目录与挂载团队技能两种机制的代价并列——内嵌每席尾部多约 5 KB，且任一员工重建要求全员重写提示词。
生成：可达时取挂载机制，提示词只留本席边约束；技能目录里没有该技能时取内嵌机制并登记 `DIRECTORY_FALLBACK`。机制由段内按目录内容推导，本段给的是处置与汇报，不是机制取值本身。
审核：回退必须留登记记录，不得静默内嵌；回读第 16 项的失败仅在已登记回退时算可接受态。登记与提示词实况必须一致——compile_prompt 从自己编出的正文回读有无内嵌目录，与本段定的机制不符即报 `DIRECTORY_UNRESOLVED`。
路由：可达则正常进 compile_prompt，提示词只留本席五去向；回退则进 compile_prompt 且目录回到提示词尾部（落地点是第五段末尾的 `【现役员工目录】` 标记），并在交付汇报里列为待人裁决项。两条分支编出的字节必须不同，相同即说明回退未落地。

### 3.4 回读失败处置

检索：分两种入口。主链中途硬停时（accept_images、apply_config、verify_readback 各自可停），读 runner 打在 stderr 的失败码与该段 `handoff/` 原件——此时 `s7_readback_receipt.json` 尚未产出，等它就是等一个不会来的文件；verify_readback 跑通而失败桶非空时，读该回执的失败桶。两入口取到的都是「失败码 + 原始响应」这一对，下面三相位不分入口。
整合：把失败项分为配置漂移、图像不符与目录未解析三类；另判每项是否使这一席当前正对预期范围以外可见——访问策略、工作区授权、汇报线三项的漂移可能扩大可见面，属暴露类。
生成：写失败清单，逐项给失败码与保留的原件路径；暴露类逐项另写现在谁能看到这一席、按规格本应是谁。
审核：任一项失败即整席 `configPass=false`；失败原件保留，不重试覆盖。暴露类失败的汇报未给止损选项即退回重写，不以「现状已写明」充抵——写明现状不等于给了人一条现在就能止损的路。
路由：配置漂移退回 apply_config 重写该键并重新回读——重跑前把失败的 `handoff/config_writes.json` 另存为 `handoff/config_writes.<段名>-fail<n>.json`，再在原路径写新响应；段脚本只认原路径，留痕件不参与审核，两条规矩由此并存；属暴露类的漂移在重写之外另给一条立即止损项（收窄该键或下线该席），两条并列交人选，不默认等重写；图像不符重传一次——上传是段外动作，按运行守卫在段外执行，回来后把新探针写进 `handoff/readback_probe.json` 原路径（旧件先另存为 `handoff/readback_probe.<段名>-fail<n>.json`），只重跑 verify_readback 与其下游，不回退到 accept_images（那一段核的是上传前的件，没有变）；仍不等即报 `IMAGE_READBACK_MISMATCH` 并保留两份图——两份指本地上传件与服务端取回件，后者落 `images/server-<件名>.png`，不覆盖本地件；目录未解析在该目标建体后补写并留一条独立证据。

## 四 · 失败码与处置

| 失败码 | 触发 | 处置 |
|---|---|---|
| `CONTRACT_MISSING` / `CONTRACT_DRIFT` | 权威源文件不在包内，或其中的标记与结构已移动 | 停手，不按记忆里的旧值继续 |
| `SPEC_INCOMPLETE` | 规格五块缺任一 | 停在编制前，回流规格生成端补块 |
| `NO_CARRIER_FOR_KEY` | 九键中某键无 `carrier` 写路由 | 拒编，回流规格端补路由，不标「后续手工处理」 |
| `ENVIRONMENT_UNREADABLE` | 探针非 200，或探针自报机制与技能目录证据推导出的机制不一致 | 停手，不回落写死值，不二选一 |
| `DIRECTORY_UNRESOLVED` | 本段所需的上游回执缺失或不可读 | 补跑缺的那一段，不跳段续跑 |
| `DIRECTORY_FALLBACK_UNAPPLIED` | 环境段定了内嵌机制，而 compile_prompt 从正文回读不到 `【现役员工目录】` 内嵌块（或反之） | 回 compile_prompt 查机制取值与编译分支，不手工往正文贴目录 |
| `SKILL_DRIFT` | 九键里声明挂载的技能不在探针查到的技能目录里 | 停在写入前，回规格端改挂载清单，不写一个平台上不存在的技能 |
| `SKELETON_MISSING` | 四个骨架标签未逐字出现 | 退回 compile_prompt 重编，不手工补字 |
| `PROMPT_DRIFT` | 提示词与权威副本不逐字节相等 | 以权威副本重写，不改副本迁就平台 |
| `BIO_DRIFT` | 简介与职责首句不一致 | 退回规格端改职责句，不单改简介 |
| `FACE_REUSE_UNVERIFIED` | 规格缺 `local_copy`；或回执面孔规则与规格不等；或复用件不在盘上、字节与头像件不等 | 按规格把复用件放进 `images/` 后重跑该段；取不到复用件即按 §3.1 停止本席编制，不写自称通过的 QA 回执 |
| `IMAGE_NOT_REVIEWED` | QA 闸未过、复核者与出图执行体同一、缺图像件或非 PNG | 硬拒上传，回视觉 QA 闸 |
| `COUNT_MISMATCH` | 资产计数与 QA 记录不符 | 停手，不部分上传 |
| `IMAGE_READBACK_MISMATCH` | 像素哈希两侧不等。本行是合称，回执里不会出现本行字面：上传前由审核器断言 `images.pixel_match` 判；上传后的回读按件分两个码落盘，头像 `AVATAR_MISMATCH`、亮相图 `BIO_IMAGE_MISMATCH`，定义见 `references/outputs.md §三` 第 13、14 行 | 重传一次，仍不等即保留两份图交人 |
| `CONFIG_WRITE_INCOMPLETE` | 写记录缺九键中某键，或含九键以外的键 | 停手核对写记录，不补记也不忽略多出的键 |
| `EMPLOYEE_MISSING` | 员工 id 形态非法（非 `de_` 起头） | 停手核对建体回执，不自造 id |
| `READBACK_INCOMPLETE` | 十六项回读缺项，或某项状态值非法 | 重取回读探针，不按预期值填 |
| `DELIVERY_INCOMPLETE` | 汇总交付时上游某段回执缺失或不可读 | 回缺的那一段重跑，不跳过该段出交付回执 |

技能目录两类故障分走两码：探针非 200 由 `ENVIRONMENT_UNREADABLE` 报出并硬停；探针 200 而目录里没有该技能不是失败态，按判断段 3.3 登记回退后继续，只有登记与正文实况脱节才由 `DIRECTORY_FALLBACK_UNAPPLIED` 报出。回读第 16 项在已登记回退时判 FALLBACK，其失败码 `DIRECTORY_UNRESOLVED` 见 `references/outputs.md §三` 第 16 行。
路由目标解析不到也不报错——按 §六 记入未解析并在该目标建体后补写。

## 五 · 人类汇报契约

每席编制结束向人汇报一次，顺序固定，不得换序：结果、影响、需要决定的问题、推荐项与理由、各选项后果、最短可复制回复、核验依据。无待决项时省略中间四项，直接给结果、影响与核验依据。

本次汇报依据的是真跑还是演练，写在首段第一句。演练指平台响应由人按形状自拟而非真实返回——此时故障是构造出来的，读者要决的是「这个缺陷排不排期修」而不是「这一席现在恢不恢复」，两者不是同一个决定。把这句压进末尾核验依据，读者会按真故障批一个演练结果。

首段写这一席建成了没有、平台上现在能看到什么。执行未完成时首段必须写停在哪一段、已经在平台上留下了什么副作用、从哪里接着跑。

面向人的正文不出现状态码、字段名、哈希、回执名与段名。这些只进末尾核验依据；无法省略的术语在首次出现处用一句自然语言解释。

把技术件换成日常词时，换出来的词要带住那件东西管什么。提示词说成「开场白」就是换轻了：它是这一席判断自己能做什么、不能做什么的依据，读者按寒暄去读，看不出改它等于改这一席的行为边界。术语解释与日常替换管的是同一件事——读者要能从正文里读出这件东西的分量，不能只读出它的名字。

待决项逐项写：问题是什么、推荐哪个、批准会发生什么、拒绝会发生什么、最短可复制的回复是什么。存在暴露类失败时另写暂缓会发生什么——拖着不决本身在延长暴露，不写这一条，读者看不出等待也有代价。

推荐项是「等」的时候，同一段里写清等什么条件成立、由谁判定成立、大致多久、等待期间有没有真实业务在等这一席。只写「等恢复正常」读者批不下去：他批准的是一个没有终止条件的承诺，既排不了期也追不了责。

回退登记与回读失败是最常见的两类待决项。

失败使这一席正对预期范围以外可见时，首段就写清现在谁能看到它，并把立即止损与彻底修好两条并列给出。只给「修好」一个方向，读者会按和其他待决项一样的节奏读，看不出修好之前暴露一直在继续。

同时写清这次失败的影响面是本席独有还是所有席共有。共有而不写，读者按单席处置，系统面的敞口就留在那里没人认领。

末尾核验依据列出 run 目录路径、八段回执文件名、十六项回读的通过与失败计数、提示词与头像的哈希前缀。机器层的枚举与人类层的汇报指向同一批事实，机器层不得替代人类层。

## 六 · 交付与批量

单席交付物是一个数字员工加完整回读证据。平台侧可见面是详情页的提示词格、简介、头像、亮相图与九项配置。

`blockers` 非空即整批标未完成，已通过的席位不回滚。部分成功是正常态：一席一体的失败域就是本席。

批量由外层驱动对席位清单循环调用本 skill，每席一个 run 目录。同一 run 目录重跑即续跑，不新建目录；run 目录名含发布号，作幂等键成分。

跨席依赖只经 `identities` 对账表传递。后编制席位从对账表解析回报目标，解析不到即写未解析并在该目标建体后补写。

## 七 · 夹具与未验证面

`fixtures/golden-domain-seat` 是一份域席的完整正例，由真跑八段产生，不是手写回执。其余目录各是该正例的整份副本改一处，每个带 `INJECTION.json` 指明它必须被哪条断言拒。

夹具里 `images/` 下的 PNG 是程序生成的极小图像，尺寸与现网的 1024×1024 头像和 1536×896 亮相图不同。审核面只校验 PNG 魔数、文件哈希与回执自洽，不校验像素内容，因此小图不削弱断言强度；但夹具不构成对真实出图质量的证据。

像素哈希这条的残留面在运行期同样在：两侧相等是回执**内部**的比对，两个值都来自 QA 回执，没有一侧由审核器从盘上的 PNG 重算。一对编造的相同值照样过闸（已实测）。它防的是上传前后被平台换图，防不住 QA 回执整体失真——后者靠复核者不得是出图执行体这一条挡，那是人的一道闸，不是机器的。

夹具只覆盖挂载机制这一条分支。目录回退分支（技能目录里没有挂载技能 → 第五段内嵌目录）有机器断言钉住「登记与正文必须一致」，但包内没有一份跑过该分支的正例，回退路径编出的提示词长什么样未经夹具验证。首次撞上回退时按实跑结果核，不得因为断言齐备就当它已被验证过。

下列三条是实现期假设，首次现网运行时必须核，核前不得当既成事实写进汇报：挂载的团队技能在运行时确实可达；建体接口的幂等键字段名未经现网确认，保守走先查后改；平台是否接受空的团队技能数组未经确认。

提示词体积是一条**没有机器执行体的软闸**。`references/prompt-segments.md §六` 写着「超 3 KB 触发人工复核」，但断言谓词词汇表只有等值与集合运算，没有数值比较 op，这条阈值写不成断言；段脚本也不为它停手。compile_prompt 落 `prompt_bytes`（正文 UTF-8 字节数）供人读，且该值由段脚本自报、无任何族从盘上的正文重算核它——把它改成 999 全部断言照样绿。谁来读、超线怎么办，是人的事。

包内 golden 的域席正文 3695 字节（3.61 KB）已越过这条线，而该席按 §六 的目标带只应到 2.8 KB。这不是夹具造错，是真跑产物：当前六段模板编出的体积系统性高于表定值。首次现网编制时按实际字节判是下沉模板还是上调该表，不得因为「闸全绿」就当体积已受控。

六维差异不是本包的闸。`references/职能席.md §四` 描述的 `check_domain_differentiation.py` 是**上游批量脚本**，读全批 `seats/*.json` 两两比对；本 skill 一次编一席，手上没有第二席，结构上跑不了它，包内也没有断言读它。递进来的规格与别席六维撞车时 `accept_spec` 照样放行。去重发生在规格生成期，不在编制期——批量增席时必须在上游先跑过那个脚本，不能因为本包八段全绿就认为席位已差异化。

十六项回读中的第 16 项在目录回退路径下记 FALLBACK，前提是回退已登记；它不进失败桶，因此不把 `config_pass` 拉假。把它填成 FAIL 会拒掉本该放行的交付。除此之外没有允许失败的回读项。

面孔复用的取证面已由 accept_images 机械核验：规格声明的规则与回执自报的规则不等即拒，复用件不在盘上或字节与头像件不等即拒。段脚本核不到的是服务端此刻返回的字节是否仍等于本地副本——那要现网下载，段内禁网，由上传后的像素回读在现网首跑时承接。

## 八 · 权威源指针

| 共享件 | 权威源 | 运行时解析 |
|---|---|---|
| 六段模板与思考骨架 | `references/prompt-segments.md` | ✓ |
| 出图请求单与 QA 闸 | `references/image-handoff.md` | ✗ |
| 席位规格五块与六维参数包 | `references/seat-spec.md` | ✗ |
| 产物目录、写入序列与十六项回读 | `references/outputs.md` | ✓ |
| 职能席的六段展开与六维机检 | `references/职能席.md` | ✗ |
| 系列风格块正文 | `references/series-style-09.20.json` | ✗ |

本 skill 不复制上述正文。上表「运行时解析」列标 ✓ 的件由段脚本在运行时解析取值，其中的标记或行数一旦移动即报 `CONTRACT_DRIFT` 并停手，不按记忆里的旧值继续。

标 ✗ 的件只由人或 agent 在段外读，没有任何机器闸盯着它们——改动这些件不会触发 `CONTRACT_DRIFT`，漂移要靠读的人自己发现。把它们当成有机器保护的权威源是错的：真要让某一条判据受机器约束，得先让某个段脚本去解析它。
