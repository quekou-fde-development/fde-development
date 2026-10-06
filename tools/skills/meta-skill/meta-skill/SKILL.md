---
name: meta-skill
description: 将长链复杂判断、多阶段执行或有副作用恢复要求的工作流蒸馏为可重复触发的 SKILL.md；新增、重写或加固这类 skill 时调用。简单单步 skill 交给系统 skill-creator。输入可为访谈语料、案例集、现役 skill 或判据库，输出命令式 Skill 包。
metadata:
  version: v3.10.1
  updated: 2026-09-21
  workflow_mode: artifact
---

# meta-skill

按第 1→9 步编译或修复持久 Skill 包。每一步保留实际产物与检验回执；遇缺料或不可执行项，输出具体段、缺件和补料入口。

## 输入与授权

- 读取已提供的素材、正反案例、现役 skill 或判据库；保留素材端给出的成功/失败标注。
- 修复已有 skill 时，先读取上次问题记录与原始证据，建立“记录的问题 → 代码位置 → 修复 → 回归结果”清单。
- 按当前用户指定的方法与范围执行；复用本轮已有授权，修改前保留可回滚基线。
- 将无法补齐的判断段交回素材端；逐项报告实际覆盖面和未完成面。
- 对具体阈值、定义与长期判据只引用唯一权威源；将运行期必要守卫就地写全。
- 编译第 1–6 步；亲跑第 8 步机械闸与白箱审；将黑箱测交给独立、互不可见的注册 sub-agent。记录实际派发输入与返回证据。
- 将 `run_meta_stages.py` 的内置输入仅作为确定性辅助脚本夹具；语义能力、触发行为和业务验收使用实际独立运行证据。

## 第 1 步 · 锁定目标函数与选择环境

判定产物是否为带 name/description、未来会再次触发的持久 Skill 包；属于一次性任务时返回入口诊断。

填写最终产物、成功条件、失败条件、选择环境、可接受复现率、证据类型，以及最终接收者能否仅凭汇报完成裁决。缺项时指出缺项并停止进入下一步。

按 `references/compilation_rules.md §第 1 步` 锁定目标；保留该表为编译记录。

同时按 `references/stateful_workflows.md §1 · 双轴分类` 将 workflow_mode 定为 artifact 或 stateful。出现共享状态写入、跨进程锁、外部副作用、排程补跑或崩溃后续跑任一项即选 stateful；禁止把这类动作仅标成 handoff 后跳过恢复契约。

在生成 assertions 前先盘点真实执行入口：命令选择器、工作目录参数、handler 绑定方式与最终调用点。把生产 runner 标为 `canonical_stage_runner` 或 `production_router_needing_adapter`。看到 `argparse.add_parser(...).set_defaults(function=handler)`、`args.function(args)`、if/elif 路由或其它非 `--stage` 字典 dispatch 时，必须生成独立的 canonical verification adapter；不得给出“只补 assertions.json 即可接入 M8”的建议。

## 第 2 步 · 切执行段与判断段

把工作流逐项标为执行段或判断段，排出有序序列。将切分标为 inferred，并交独立黑箱核查。

按 `references/compilation_rules.md §第 2 步` 区分两类段；按下一步分别展开。

## 第 3 步 · 展开两类段

按 `references/compilation_rules.md §第 3 步` 执行：

- 将判断段展开为检索、整合、生成、审核四相位；提取判断标准、触发钩子及逐分支路由。
- 将执行动作拆至每个动作恰好一个 operation；按 `references/contract_ir.md §2 · operation 封闭词汇表` [OBL:OPERATION.VOCAB] 标注，逐段填动作、可达接口、依据、产出、值域、断言六槽。
- 按 `references/contract_ir.md §3 · 最低强断言族` [OBL:ASSERTION.MINIMUM] 查最低断言族；按 `references/contract_ir.md §4 · 总禁则` [OBL:ASSERTION.NO_BACKSOLVE] 排除守恒式反解的自证覆盖。
- 词汇表外的动作按 `references/contract_ir.md §5 · custom operation` [OBL:CUSTOM.EVIDENCE] 补独立 golden、定向 mutant 与来源锚；缺任一项即返回该段。
- 对无法填满的执行段列出具体缺槽，交回素材端补齐。

为本包的三个确定性辅助段保留下列实际入口卡；只用其结果检验辅助脚本管道。

执行段：init_eval_workspace
动作：调用评测脚手架并保存本段输出文件快照及回执
副作用：run_dir_only
可达接口：`python3 scripts/run_meta_stages.py --stage init_eval_workspace --run-dir runs/self-check`
依据：`SKILL.md §第 7 步`
产出：`init_eval_workspace_receipt.json` 与 `stage_outputs/init_eval_workspace/` 下的真实文件
值域：`source_id` 非空；`output_count` 为非负整数；`outputs_sha256` 为 16 位小写十六进制
断言：source receipt(T1) + schema conformance(T1) + count/hash与文件重读(T1)

执行段：run_trigger_eval
动作：用确定性夹具执行 prepare/score 并保存本段文件快照及回执
副作用：run_dir_only
可达接口：`python3 scripts/run_meta_stages.py --stage run_trigger_eval --run-dir runs/self-check`
依据：`SKILL.md §第 7 步`
产出：`run_trigger_eval_receipt.json` 与 `stage_outputs/run_trigger_eval/` 下的真实文件
值域：`source_id` 非空；`output_count` 为非负整数；`outputs_sha256` 为 16 位小写十六进制
断言：source receipt(T1) + schema conformance(T1) + count/hash与文件重读(T1)

执行段：aggregate_benchmark
动作：用确定性夹具聚合两类指标并保存本段文件快照及回执
副作用：run_dir_only
可达接口：`python3 scripts/run_meta_stages.py --stage aggregate_benchmark --run-dir runs/self-check`
依据：`SKILL.md §第 9 步`
产出：`aggregate_benchmark_receipt.json` 与 `stage_outputs/aggregate_benchmark/` 下的真实文件
值域：`source_id` 非空；`output_count` 为非负整数；`outputs_sha256` 为 16 位小写十六进制
断言：source receipt(T1) + schema conformance(T1) + count/hash与文件重读(T1)

## 第 4 步 · 定位或提取判据

按 `references/compilation_rules.md §第 4 步` 分流：判据已有权威源时用 index-mode，指至文件具体节；判据尚无归属时用 extract-mode，从正反案例差异提取规则、阈值、边界、置信度和更新条件。

对每条判据先检查反例；标明相关性与因果证据的区别。

## 第 5 步 · 补足缺料推理

按 `references/compilation_rules.md §第 5 步` 生成 2–4 个竞争假说，逐个写可区分的预测与反证。

将原始素材和问题交给 2–3 个独立注册 sub-agent；只在证据支持时立 inferred 判据，保留置信度与更新条件。分歧时返回第 4 步；案例不足时输出补料诊断。

## 第 6 步 · 编码与落脚本

按 `references/compilation_rules.md §第 6 步` 编写命令式 SKILL.md，正文控制在 500 行内，将解释和长明细放至一级直达 references。

- 给每个执行步填全动作、依据、产出、值域；给每个判断段写全标准、钩子和路由；给每个问句的答案补齐后续动作。
- 按 `references/compilation_rules.md §6A · 人类汇报契约` 为所有面向人的终态补齐自然语言汇报。先写结果和影响；需要裁决时逐项写明问题、推荐选项、批准与拒绝的后果、最短可复制回复；内部状态码、锁、哈希、字段名与 stage 只进末尾技术证据，首次出现必须解释。
- 按 `references/contract_ir.md §6 · canonical contract schema` [OBL:CONTRACT.DATA] 生成 canonical assertions.json；从规则源生成谓词，逐条保存 source_anchor。
- 给每个机器执行段编写可单独调用的入口，按 `references/contract_ir.md §6.2` [OBL:STAGE.ENTRY_BINDING] 绑定参数、dispatch 与落盘产物。
- 生产 CLI 可保留自身 subcommand/callback 路由；若它不满足 M8 的 canonical `--stage`/`--run-dir` 字典 dispatch，另写薄 verification adapter，调用真实 handler 或公开 API，禁止复制业务实现，并用 runner_binding.json 绑定生产文件全量 hash 与可达调用。先记录 runner topology，再生成 assertions；assertions 本身不证明执行入口可达。
- 出现并行 sub-agent / reader / worker 时，必须编译出有界活性契约：首次可核验进度期限、连续无进展期限、主执行者最多等待几轮、逐项持久化位置、取消动作、只接管未完成分片的 fallback，以及 fallback 失败后的精确停止点。没有这些字段时不得保留“并行执行”措辞，也不得靠主执行者全量重跑掩盖失联。
- 按 `references/contract_ir.md §6.3` [OBL:STAGE.DECLARATION] [OBL:STAGE.CLOSURE] 保证正文、contract、runner 与 golden manifest 的 stage 集一致。
- 分离执行脚本与审核脚本；审核器读取落盘产物与声明式契约。输出文件清单回执时按 `references/contract_ir.md §6 · canonical contract schema` [OBL:CONTRACT.DATA] 的 file_bindings 规则校验真实文件路径与内容。
- 按 `references/contract_ir.md §6.1` [OBL:RENDER.COMPARE_PATHS] 显式声明渲染对照的两端路径。
- 按 `references/contract_ir.md §8.0` [OBL:FAMILY.TIER] 在 T2 降级前校验 family/tier；保留 T2 未验证面。
- 按 `references/contract_ir.md §9` [OBL:AUDITOR.EVIDENCE] [OBL:AUDIT.FAMILY.FALSIFIABILITY] 为审核器建立真实 golden 与逐条定向 mutant。
- 在每段落盘后立即审核，通过后进入下一段，最后全量审核；按 `references/contract_ir.md §8.1` [OBL:AUDIT.EXIT_CODES] 区分 rc 0/1/2/3；只将 rc=1 计为有效断言拒绝。
- 按 `references/contract_ir.md §7` [OBL:MANIFEST.SCHEMA] 保存 manifest、逐段结果及 unresolved_coverage。
- 遇同一确定性断言连续两次失败，停止自动重试并提交原因与证据。
- 按 `references/contract_ir.md §6.4` [OBL:PLACEHOLDER.FAIL_CLOSED] 拒绝未填模板残留。
- 顶层只写 system Skill 规范允许的键；将 version、updated 及网络节点的 topology_version、edges_in、edges_out 写入 metadata。
- 将 workflow_mode 写入 metadata。stateful 包另按 `references/stateful_workflows.md §2 · stateful_contract schema` 生成 stateful_contract.json，逐 effect boundary 填稳定 idempotency key、前置状态、effect receipt、readback、未知状态处理、reconcile-before-retry、补偿或人工裁断；逐张有副作用执行卡以 `path.py::symbol` 绑定 production_entrypoints，真实入口必须转入唯一 transaction kernel 并原样传递 target/revision/attempt/fence/adapter。
- 每张执行段卡及每条编号/列表执行步显式写 `副作用：run_dir_only|shared_state|external_system|scheduler|lock`；artifact 只能使用 run_dir_only，任一其它 scope 将整包提升为 stateful。
- 将工作目录由显式参数传入；缺省交互根采用 META_SKILL_EVAL_ROOT 或当前目录下 eval-workspaces。保持所有机器调用显式传 --root/--run-dir。

## 第 7 步 · description 触发 eval

按 `references/compilation_rules.md §第 7 步` 准备至少 20 条正例与 near-miss 触发用例。

- **动作：** 运行 `python3 scripts/init_eval_workspace.py meta-skill --root eval-workspaces` **副作用：** run_dir_only **依据：** `references/schemas.md §11` 与本轮用例素材 **产出：** `eval-workspaces/meta-skill/trigger_eval/trigger_set.json` **值域：** id 唯一、query 非空、should_trigger 为 boolean 的数组

- **动作：** 运行 `python3 scripts/run_trigger_eval.py prepare --skill meta-skill --skill-path . --root eval-workspaces --runs 3` **副作用：** run_dir_only **依据：** 已填写触发集与所选 SKILL.md description **产出：** 该 workspace 下 judging/original 的冻结快照与判定卡 **值域：** `references/schemas.md §11` 的 schema_version=2 快照

按生成卡派独立判定者，保存实际派发记录；要求全部报告带本轮 eval_fingerprint、与文件名一致的 run 号及每条 id 恰好一次的 TRIGGER/SKIP 判定。

- **动作：** 运行 `python3 scripts/run_trigger_eval.py score --skill meta-skill --root eval-workspaces` **副作用：** run_dir_only **依据：** 同一版本冻结快照与全部独立判定报告 **产出：** 该 workspace 下 trigger_eval/result.json **值域：** 输入完整时写入 COMPLETE；缺件、格式错误或输入漂移返回非零且保留既有结果；平票记 TIE

按 `references/compilation_rules.md §第 7 步` 补实际竞争路由行为闸，保存正例、near-miss、NO_MATCH 与故意错域 description 哨兵。按失败类型修 description、边界或测试集，再复验；最多五轮。

只比较同一 comparison_key 的候选；将 test_score 用于本轮候选比较时，另留未参与选择的测试集再报告泛化能力。description 发生变化时重做本步。

## 第 8 步 · 检验与回流

- 先运行当前宿主 system skill-creator 的 quick validator；frontmatter 出现宿主白名单外顶层键或宿主 validator 未通过时停止发布。宿主 validator 依赖缺失须显式报告并补到隔离测试环境，不能把“未运行”记成 PASS。
- **动作：** 运行 `python3 scripts/validate.py . --persistent` **副作用：** run_dir_only **依据：** `references/compilation_rules.md §第 8 步` 的 M1–M12、`references/contract_ir.md` 与 `references/stateful_workflows.md` **产出：** 逐闸报告和退出码 **值域：** 所有适用机械闸通过才继续；NOT_RUN、FAIL 与 SKIP 分别披露
- workflow_mode=stateful 时，按 `references/stateful_workflows.md §3 · 恢复验收` 在一次性 fixture root 跑 test runner；至少覆盖 effect 前、effect 后 receipt 前、receipt 后 commit 前、unlock 中断四个故障点及重复尝试、未知外部状态、陈旧锁、积压重试、证据缺失场景。任何重复副作用、跨 target 串锁、未知状态自动重放或证据不足仍推进均判 FAIL。
- 按 `references/verification.md §四层验收` 分别记录 host、contract、entry-binding、behavior/recovery 四层结果。任一层未运行即保持 NOT_RUN；较高层 PASS 不能覆盖较低层失败。
- 安装到目标宿主后，按 `references/verification.md §安装后宿主实跑` 另给 deployment verdict。排程或 stateful skill 至少要从真实入口完成一笔允许的 canary / 真实事务，并回读终态、提交凭证、解锁状态与进度探针；只有隔离测试或 DRY RUN 时只能报告“代码已安装，生产闭环未验证”，不得报告整套完成。

逐项审核局部判准、执行可行性、全局一致性和命令式表达；按 `references/verification.md §指针审` 检查权威源指针。

按 `references/verification.md §人类裁决可用性` 增加一条独立黑箱任务：只给判定者最终汇报，不给运行日志和源码。判定者必须能复述发生了什么、需要决定什么、推荐方案、两种选择的后果和最短回复；任一项只能靠猜测或先懂内部术语即判 FAIL。

按 `references/compilation_rules.md §第 8 步` 派独立黑箱：Round 1 用三条不同任务覆盖边界；Round 2 复用最敏感任务补足三路比较。出现路由分歧时返回第 1–3 步；一致时记“未测出分歧”。

达到重档条件时按 `references/verification.md §黑箱测·重档` 使用 reference 与独立弱模型臂；将不可逆动作置为 DRY RUN。

实跑一条完整段链，逐段审核并全量审核，核 manifest、退出码和所有未验证面。

修复本编译器时，再按 `references/verification.md §随包工程回归` 执行随包回归与 18 臂机械矩阵；以当前包字节和当前运行证据裁定工程结果。

## 第 9 步 · Improve 与交付

按 `references/compilation_rules.md §第 9 步` 将失败点回流到对应段，以现役基线与候选运行同一冻结任务集，派独立 comparator 盲评、analyzer 追因，保存 comparison、analysis 与 history。

- **动作：** 运行 `python3 scripts/aggregate_benchmark.py eval-workspaces/meta-skill/iteration-1 --skill-name meta-skill` **副作用：** run_dir_only **依据：** 冻结 iteration_plan.json 与逐 run 的 grading.json **产出：** 该 iteration 下 benchmark/benchmark.json 与 benchmark.md **值域：** 按 eval_type 分组的指标；缺件时 INCOMPLETE 且返回非零

- **动作：** 运行 `python3 eval-viewer/generate_review.py eval-workspaces/meta-skill/iteration-1 --skill-name meta-skill --static eval-workspaces/meta-skill/review/review.html` **副作用：** run_dir_only **依据：** 本轮完整 benchmark 与逐 run 证据 **产出：** 独立可打开的静态 review.html **值域：** 安全转义所有输入，逐类展示指标

达到用户认可、反馈为空或连续两轮无改善时停止迭代。交付先用自然语言给结果、影响与待用户动作，再附修复清单、验证范围、仍待验证项及回滚点；不得让内部状态码或工程结构承担结论。已有修改授权时，在备份与检查通过后更新对应现役文件及其共享源。
