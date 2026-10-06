---
name: meta-architecture-development
description: 从项目调研文档、访谈和既有设计中澄清业务目标与约束，生成或修订九份待总架构师审核的开发设计 Markdown；输入空白、部分填写或互相冲突时先集中追问。用于开发前的架构设计，不用于直接实施、发布、纯排版或单纯蒸馏其他 Skill。
metadata:
  version: 0.1.0-candidate
  updated: 2026-10-06
  workflow_mode: artifact
---

# Meta Architecture Development

## 加载链（上下游）

**上游**：调用者通过技能目录或显式名称进入本 Skill，在项目需要形成或修订九份开发设计、提交总架构师审核时加载。

**管辖文件（下游）：**
- `references/input-and-evidence.md` — 收到调研输入、原件或人类回答时读取，确定来源、事实、推断与缺件。
- `references/pre-review-analysis.md` — 从材料形成业务流和系统架构理解时读取。
- `references/clarification-and-decision-loop.md` — 出现设计关键缺口、冲突或方案选择时读取。
- `references/nine-document-authoring.md` — 起草或复核九份设计文档时读取。
- `references/design/01-concept.md` 至 `references/design/09-implementation-roadmap.md` — 起草每一份对应设计文件前，实际读取同名编号的写作参照。
- `references/mechanical-contract.md` — 调用随包 `acquire_sources` 或 `render_documents` 确定性辅助段时读取。

**同级联动：**
- 总架构师审核通过后，由项目指定的开发流程与 Meta Agent、Meta Skill、Workbench 工具承接实施。

**编制来源**：`agentfs://workspace/01 Projects Zone/Quekou_FDE/FDE_Methodology/_overview.md` 记录本包的项目来源；外部接收者使用随包内容即可运行。

**便携运行：** 随包的 `assets/`、`references/`、`scripts/` 和契约文件构成运行所需的正文、写作参照与确定性辅助能力。以上 `agentfs://` 指针仅说明本工作库中的来源与联动；外部接收者不需要读取本机旧手册或其他工作库文件，除非调用者把它们作为本项目输入资料明确提供。

## 目标与边界

把指定的通用调研输入及其原始证据，收束成以下九份候选设计文件：

```text
design/
├── 01-concept.md
├── 02-use-cases.md
├── 03-data-model.md
├── 04-security-privacy.md
├── 05-site-architecture.md
├── 06-page-layout.md
├── 07-api.md
├── 08-tech-stack-and-directory.md
└── 09-implementation-roadmap.md
```

业务流、系统边界、判断点和方案分歧先在本次运行的 `working/` 中分析，再被映射进九份文件。不要新建第十份架构治理文件、巨大统一表头或与项目无关的模板。九份文件交付时的唯一状态是“待总架构师审核”。

本 Skill 不替代现场调研，不自行确认业务规则、阈值、权限或客户承诺，不创建 Arcubase 资源、数字员工、Skill、Workbench 应用或外部系统写入，不安装或发布任何包。获批后的实施由指定的 Meta Agent、Meta Skill、`workbench-app-development` 和其他现役工具负责。

既有九份设计可以作为输入资料，用于发现已定内容、矛盾和需要修订的范围；它们不自动高于原始业务证据和有权人决定。修订仍输出到新的候选 `run-dir`，不覆盖既有项目文件。

## 固定平台边界

本包覆盖的全部候选架构以 Syngy Workbench React、Octopus 与 Arcubase 为固定平台边界；这一边界是本项目的已确认决定，应写进九份设计的相应位置。

调研转写中出现的 “Occupace” 或 “AQBase” 在本包内统一规范为 Arcubase；引用原始口述时可保留原词并在首次出现处标明该规范化。

1. Workbench 应用保留官方 React 脚手架和 `@syngy/workbench-auth`，由受信任的 Workbench 会话提供人类身份。候选架构不设计独立登录页、令牌仓或第二套认证链。
2. Octopus 承担 Host 能力及组织管理入口。项目需要用户、团队、组织目录、数字员工、会话、文件、Skill 或其他 Host 能力时，实施选择 `octopus` feature 与 `@syngy/octopus-client`；只读取已认证查看者的页面无需虚构额外 Host API。
3. 所有共享、持久、可查询的业务事实落在 Arcubase App 的原生表、字段和 Link 中。实施使用 `arcubase` feature 与生成的 typed ingress client；本地对象、静态样例及 `octopus.api` 的通用 Arcubase 代理不构成业务数据层。Taskboard 只在项目确有任务或项目工作流时选择。
4. 架构必须明确 Arcubase App 采用既有 App 还是新 App。既有 App 需要以实读的精确 App ID、schema 和稳定键为依据；新 App 先在九份设计中给出表、字段、Link 与访问模型，再在批准后的实施阶段创建。名称匹配、推测 ID 或静默创建都不能充当选择依据。
5. Octopus 提供 Arcubase 原生组织角色及成员关系的统一管理入口，Arcubase 原生角色和表规则承载有效业务授权。所有业务表引用同一组已核验角色；Host 管理员或团队成员资格、对象归属、负责人和审批人分别保留各自语义，不能直接互相替代。前端消费当前有效授权，数据入口也必须执行授权。涉及代理、后台代办或 `conversation_member` 的项目，还需在实施中取得真实调用者、执行身份和撤权的允许/拒绝证据后才能称为可用。

## 运行前提

1. 调用者提供显式 `run-dir`，并指定本次项目的调研输入、相关材料或需要修订的既有设计。输入可完整、部分填写或尚为空白，按下条识别缺口。
2. 随包 `assets/通用调研输入文档.md` 是可携带的空白输入结构。项目运行时指定它的项目副本；副本中已有的材料与来源构成本项目输入权威。空白项、空白单元标记、不适用项和部分填写都可进入取源、分析与澄清；它们分别按未知、不适用或需要补充处理。只有设计关键问题未清零时，才阻断最终九份文件的渲染。
3. 输入文档列出可访问的访谈转写、观察记录、真实样本、规则原件、现有系统或接口证据，以及每项的权威性和取得状态；并列出 Arcubase App 选择、既有 schema、组织角色/成员关系、现有 Workbench 应用及目标环境的已知证据。
4. 先按 [输入与证据](references/input-and-evidence.md) 获取并实际阅读必要来源。随包机械合同可用时，使用其 `acquire_sources` 形成运行快照；快照证明取源完成，不替代语义判断。
5. 当前候选只在显式 `run-dir` 内写入。因此属于 `artifact`。若有人要求直接改共享项目目录、调用平台写操作、排程或改变其他共享状态，停止并重新按 stateful 工作流设计恢复与授权边界。

输入或原件缺失时，说明缺少的具体文件、字段、样本或接口证据。可以保留 `working/` 候选分析，不能用模型常识补成项目事实。

## 确定性辅助段

执行段：acquire_sources  
动作：读取 `input/source_manifest.json` 中声明的只读资料，逐项落盘原始字节快照、来源快照和取源回执。  
副作用：run_dir_only  
可达接口：`python3 scripts/run_meta_stages.py --stage acquire_sources --run-dir "$RUN_DIR"`  
依据：`references/mechanical-contract.md §input/source_manifest.json` 与 `§acquire_sources receipt`。  
产出：`working/sources/`、`working/source_snapshot.json`、`acquire_sources_receipt.json`。  
值域：来源清单符合 1.0 结构且每项资料可读时，回执逐项记录来源标识、取数时刻、路径与内容哈希、字节数和快照位置；清单或资料不合格时停止本段。  
断言：source receipt（T1）+ schema conformance（T1）+ count/hash 与实际文件重读（T1）。

执行段：render_documents  
动作：读取已准备的 `working/render_request.json`，在设计关键问题清零时逐字写出精确九份候选 Markdown，并写入输入与落盘回执。  
副作用：run_dir_only  
可达接口：`python3 scripts/run_meta_stages.py --stage render_documents --run-dir "$RUN_DIR"`  
依据：`references/mechanical-contract.md §working/render_request.json` 与 `§render_documents receipt`。  
产出：`design/` 下九份指定文件、`render_input_receipt.json`、`render_documents_receipt.json`；问题未清零时只产出 `working/render_blocked.json`。  
值域：`unresolved_questions` 为空且文件名恰为九个指定名称时，九份正文按原字符串落盘，回执固定为待总架构师审核；数组非空时不创建或改写 `design/`。  
断言：source receipt（T1）+ schema conformance（T1）+ count/hash（T1）+ artifact hash（T1）+ row/column/sheet reconciliation（T1）+ summary reconciliation（T1）+ output field coverage（T1）。

## 先理解业务，再形成设计

按 [审核前业务流与系统架构分析](references/pre-review-analysis.md) 处理材料：

1. 锁定交付对象、业务目标、成功/失败条件、使用者和决定权；每项都带来源锚点。
2. 还原从触发到结果的时间顺序，分开事实、推断、异常、等待、人工裁决与并行。
3. 区分执行段与判断段。执行段写动作、依据、入口、产出和失败处置；判断段写证据、整合、候选、标准、分支去向。
4. 沿流程划出人、既有系统、新建 Workbench 应用、潜在数字员工、潜在 Skill 与数据权威位置的职责边界；记录调用、数据流、身份与恢复约束。
5. 为每个 `BF-xx` 标出 Workbench 入口、所需的 Octopus 能力、Arcubase 表/字段/Link 和角色规则、是否确有 Taskboard 需求，以及外部交接。没有实读证据的 App ID、字段类型、Link payload、调用者映射或平台能力保留为核验项。
6. 使用 Meta Orchestrator Step 0—3 的画时序、判别、切段和交接分析方法，使用 Meta Skill 的目标、段落、判据与补料方法。此处不生成 `topology.json`、网络 ABI、最终 Skill 包或运行测试声明。

分析产物只服务于本次候选设计。持续维护来源编号、流程段编号、对象和用例编号，使九份文件可以互相引用。

## 澄清循环

发现下列任一情况时，立刻读取 [澄清与决定循环](references/clarification-and-decision-loop.md) 并向人集中提问：范围或成功条件、角色或决定权、流程及异常终点、数据权威和状态变化、权限、既有能力或接口、Arcubase App 的既有/新建选择、业务角色和对象授权、对外动作与失败接手、验收、技术或部署约束。

一次只合并同一决定主题的问题。每个问题簇说明已知证据、需要作出的决定、可选项或需补材料、影响的流程段与九份文件，以及最短可回答方式。收到回答后记录决定来源和决定人，更新所有受影响的分析与候选正文；回答没有解决的部分继续保留为问题。

`working/render_request.json` 中存在任何设计关键 `unresolved_questions` 时，不得请求渲染最终九份文件。外部能力尚未实测、上线前验证或总架构师审核条件可作为限制写入相关文档；它们不能掩盖尚未回答的设计问题。

## 方案推导与提问边界

基于已确认的业务目标、流程、对象、权限和约束，主动提出可审阅的 Arcubase 表/字段/Link、API 形状、Workbench 页面结构、Octopus/Arcubase 系统分工、技术路线和实施顺序，并说明它们如何满足已知依据。这样的内容是待总架构师审核的设计推导，不能伪装为客户既有事实。

同一业务含义下的命名、章节组织、字段分组、页面呈现和 API 表达可由 Skill 自行写清，不要求人逐个决定。只有选择会改变业务范围或结果、决定权、数据权威或状态、权限、对外副作用、既有系统接入、合规、验收、成本/周期承诺或运行责任时，才把备选方案和影响集中交人确认。技术能力未知时先确认约束或实际能力，不能把一个未核实的候选当作既成事实。

## 起草九份文件

读取 [九份文件写作](references/nine-document-authoring.md)，并在每份正文起草前实际读取 `references/design/` 中同编号的参照文件，以来源支持的项目语言、范围与章节粒度写作。八份案例参照的文件名已映射到当前九件序号，正文保持王磊原文件字节不变，因此其标题和文内旧编号仅作案例风格参考。案例中的 Ticket、特定语言、缓存、部署、路由、身份系统和业务规则不能复制到新项目。

逐份读取参照；读取结果截断时，分段补读到文件末尾再起草，在已有 `working/` 分析中记录读取范围。只得到标题、摘要或被截断的合并输出时，先补读对应原文。

- `01-concept.md` 先统一名词、角色、关系、约束和样本指针。
- `02-use-cases.md` 以真实角色和可验收任务组织主流程、异常和场景。
- `03-data-model.md` 独立表达 Arcubase 实体、原生字段、Link、状态和权威来源，保持简洁。
- `04` 至 `09` 从已经确认的用例、数据、权限、Workbench/Octopus 入口和 Arcubase 依赖向下展开。
- 每个业务事实和约束都回到项目来源或人类决定；每个技术、接口、页面、字段或里程碑都回到这些依据，或写明其设计推导。影响业务结果的未定选择集中提问，不能从案例继承默认答案。

渲染前逐项对照参照检查正文。`03-data-model.md` 保留“表、每表字段、Link、业务流”四项；字段分别写展示 `label`、稳定 `key`、原生类型代码、必填、唯一、默认值模式/值及按需 options。用 `text`、`textarea`、`datetime` 等已知代码表达类型；表名或应用内模块名不能冒充平台自带的表级 stable key。Link 写清源字段、目标表及 ID 取得方式、单选/多选和关系所支持的流程；业务时间按已知契约写 epoch seconds 与首次回读要求。实际资源 ID 和目标环境行为可留待实施核验，随包已知的 schema 结构必须写进设计。遗漏这些内容时补齐正文后再渲染。

先检查九份内容的对象、角色、状态、权限、入口、契约和依赖是否一致，并按最终用例编号同步 `working/` 分析中的交叉映射。设计关键问题清零后，按随包机械合同准备 `working/render_request.json` 并调用 `render_documents`。该辅助段只写精确九份文件并回执；九份正文的业务含义仍由本 Skill 的分析与人类澄清负责。

渲染器发现 Markdown 表头与分隔行列数不齐时，按报出的文件和行号修正格式，再提交渲染；保持表头、单元格内容和业务含义不变。已有渲染回执时使用新的候选运行目录，保留原稿和原检查记录。

## 结束与报告

面向使用者的文字先说明已经完成什么、尚未完成什么和下一步。需要澄清时，先说明九份最终候选尚未生成；建议由有权人一次回答所列问题簇。说明答复齐备后会更新分析并生成候选、纠正来源时会重查受影响部分、暂缓时会保留材料并停在澄清。问题不能根据现有证据推荐某一业务方案时，直说需由有权人决定，保留每簇最短回复格式。

渲染成功后，报告：本次输入和实际读取范围、已经明确的设计边界、九份文件位置、仍未验证的能力或实施前提，以及“待总架构师审核”的状态。不要把候选设计称为已通过、可上线或已部署。

建议总架构师先核对业务范围、数据和权限，再决定批准、退回修改或暂缓；技术检查不替其作出审核推荐。说明批准后进入既有实施流程、退回时修订受影响文件、暂缓时保留候选，并提供三种最短回复。明确本次没有执行开发或平台资源创建。

总架构师审核通过后，实施人员以批准版本和审核条件进入既有开发流程；审核退回、业务变化或实施发现设计问题时，回到受影响的来源、澄清或九份文件重跑本 Skill。
