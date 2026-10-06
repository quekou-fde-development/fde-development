---
title: 九份开发设计文件写作
status: candidate-reference
updated: 2026-10-06
---

# 九份开发设计文件写作

## 使用原则

`design/` 下九份是直接写作参照：八份案例文件的**文件名**已映射到当前体系，正文保持王磊原文件字节不变；新增独立数据建模。案例正文的标题和文内旧编号不需要改写，只借用“概念—用例—数据—安全—站点—页面—API—技术—路线”的递进、简洁正文、必要表格、场景和禁止项表达；不继承其中的业务对象、Ticket、Go、Redis、Kubernetes、认证、路由、API 形式或部署方案。

只写这九份设计文件；业务流和系统架构分析在运行材料中完成，再由各文件引用相关 `BF-xx`、对象、用例和决定编号。

## 固定平台落点

九份文件共同采用 Workbench、Octopus 与 Arcubase。将该已确认平台边界写成项目设计，不将它混同为调研得出的业务事实：

- Workbench React 与 `@syngy/workbench-auth` 提供应用壳、会话和页面入口；项目没有独立登录、令牌存储或替代认证链。
- Host 用户、团队、组织目录、数字员工、会话、文件或 Skill 等能力按用例选择 `octopus` feature 和 `@syngy/octopus-client`。Taskboard 只在用例含任务或项目工作流时采用。
- 所有共享、持久、可查询的业务记录使用 Arcubase App 的原生表、字段和 `linkto` 关系，通过 `arcubase` feature 与生成的 typed ingress client 读写。页面样例、静态对象及 `octopus.api` 的通用 Arcubase 代理没有业务数据权威。
- 每份涉及存储的文档都说明 Arcubase App 采用既有还是新建：既有 App 写实读 App ID、schema 与稳定 key 的来源；新 App 写待批准的 schema 和访问模型。未实读的 ID 留空并列为实施前取证，不能由名称推断。
- 角色成员关系由 Octopus 的官方 Arcubase organization role 管理入口维护，Arcubase 原生 actor 和表 access rule 形成有效授权。业务对象的归属、负责人和审批人留在业务表；Host 团队资格不自动授予业务权限。

| 最终文件 | 必读写作参照 | 本项目应表达 |
| --- | --- | --- |
| `01-concept.md` | `design/01-concept.md` | 术语、业务对象、角色边界、关系、关键约束、样本或来源指针。 |
| `02-use-cases.md` | `design/02-use-cases.md` | 范围与假设、按真实角色组织的用例、触发/主流程/异常/权限/验收结果、关键场景。 |
| `03-data-model.md` | `design/03-data-model.md` | Arcubase 实体一行代表什么、稳定 key、原生字段、`linkto` 关系、状态与转换、权威来源、读写者和样例映射。 |
| `04-security-privacy.md` | `design/04-security-privacy.md` | 安全目标与边界、Arcubase 原生角色×对象×动作×数据范围、Octopus 身份映射与角色维护、敏感数据、审计、幂等/失败与一致性检查。 |
| `05-site-architecture.md` | `design/05-site-architecture.md` | Workbench 角色入口、站点或工作台结构、路由/页面清单、需要的 Octopus 能力、跨系统交接与不可达功能。 |
| `06-page-layout.md` | `design/06-page-layout.md` | 页面主任务、数据来源、主要动作、加载/空/错/无权/人工等待状态、视觉与组件约定。 |
| `07-api.md` | `design/07-api.md` | 按调用方或能力分组的调用契约：Octopus/Arcubase typed client 边界、提供方/调用方、输入输出、身份权限、错误、幂等、超时、回读和批量语义。 |
| `08-tech-stack-and-directory.md` | `design/08-tech-stack-and-directory.md` | 官方 Workbench React 工具链、采用/复用/新增 feature 的依据、目录、认证与环境、依赖和锁文件、生成 client、部署目标与运行责任。 |
| `09-implementation-roadmap.md` | `design/09-implementation-roadmap.md` | Arcubase App 选择与 schema/role 建立、依赖顺序、完整用例、难度/周期依据、联调、身份与撤权验收、上线条件与恢复准备。 |

## 各文件的最低内容

### 01 概念

让同一对象在其他八份文件中有同一含义。必要时给短术语表、角色边界、关系树或约束清单。每个名词说明范围、唯一标识或权威位置；可自行统一同义命名，概念范围或权威位置尚不明确时回到澄清。

### 02 用例

按用户、系统或人工角色列出真实目标。每个用例关联 `UC-xx` 和 `BF-xx`，写触发、前提、输入、主流程、成功可检查结果、异常或拒绝、权限与验收。选择少量真实关键场景串联，不以页面清单代替业务用例。

### 03 数据建模

从用例和真实记录出发，先明确一行代表什么。共享持久事实写为 Arcubase 原生表和字段，关联写为 `linkto`；用简洁的实体说明和关系/状态图或表表达稳定 key、必要字段、值域或计算规则、关系基数、历史/重复、状态转换、来源、权威位置、写入者和读取者。字段名和内部结构可由已确认的业务语义推导；会改变业务含义、数据权威或权限的字段与状态先澄清。App、表 ID、field ID 和具体 schema payload 只取自目标环境读回、当前 CLI 帮助或批准后的建表回读，不能伪造。

### 04 安全与隐私

从角色、对象、动作和数据范围展开权限。Octopus 的官方接口维护 Arcubase organization actor 成员关系；Arcubase 表规则引用这些 actor，实施时以当前真实 role/actor 映射为准。写清哪些业务角色可 `view`、`add`、`edit`、`delete`，哪些字段需受限，谁能维护角色以及对象归属如何参与后端判定。Arcubase 字段规则实施时以 `:<field_id>` 为键，不能以展示 key 代替；同一 rule 的多项 scope 是 OR，多个 ingress 的合并语义仍需实测。前端只消费当前有效授权，数据入口执行同样的限制。涉及外部调用时写身份、最小暴露、幂等、重复/未知结果、拒权和失败处置。人类调用者映射与撤权列出允许/拒绝验收条件；项目涉及数字员工代办或 `conversation_member` 时，再列出发起和执行身份的验收条件。

### 05 站点架构

沿用例安排 Workbench 入口、菜单、路由、工作台、员工会话、审批或外部系统交接。每个页面或入口关联角色、用例、Arcubase 对象和权限；需要 Octopus client 的 Host 能力明确列出，只有认证查看者的页面不虚构调用。页面清单之外的能力不得被描述为可达；整体模块职责、数据流引用分析所得结论。Host 管理屏与业务数据屏分别标明其角色管理或 Arcubase 数据职责。

### 06 页面布局

逐页写主任务、信息层级、字段及其数据来源、主要操作、状态与权限。可按已确认任务推导清晰的页面和交互结构；品牌、无障碍、设备或视觉参考已有约束时遵从，缺失时把不影响业务结果的呈现作为设计选择。原型和演示数据不能充当真实后端或验收依据。

### 07 API

只为已经确认的页面、员工、Skill、既有系统或人工交接定义调用入口。每项明确提供方和调用方、输入输出、授权、错误语义、分页/批量、幂等、超时、结果回读和版本或迁移影响。Arcubase 业务读写走生成的 typed ingress client；Octopus Host 调用从当前 `@syngy/octopus-client` 类型确定。既有接口引用实际契约；新接口可从确认的用例、数据和权限推导责任模块与契约形状。接口名称和字段表达由 Skill 统一；接入方式、外部能力、权限或副作用未确认时进入澄清。

### 08 技术栈与目录

技术选择服从用例、数据、安全、接口和部署约束。使用官方 Workbench React 脚手架，保留 `@syngy/workbench-auth`；按已确认用例选择 `octopus`、`arcubase` 和按需 `taskboard` feature。既有应用先写明实读的 `package.json`、锁文件、`src/lib/syngy.ts` 与保留范围；新应用再写明所需 feature、Arcubase App 选择、schema、访问模型及生成 typed client 的位置。可基于这些约束提出目录和工具分工，并说明理由；会改变成本、周期、合规、外部接入、运行责任或客户承诺的选择集中提问。列出采用、复用和新增的理由，以及实读版本、代码和文档目录、环境、依赖/锁文件、生成物、部署目标和运行责任。没有项目依据时保留候选方案及待确认点，不沿用案例技术栈。

### 09 实施与验证路线

以用例为主线拆任务，说明输入、产物、前置依赖、负责人、完成条件、风险与验证。先安排既有/新 Arcubase App 的明确选择，再安排 schema 与 access rule、typed client、Workbench 页面和必要的 Octopus 能力；应用权限变更时先读取完整角色成员关系，保留无关角色，再以单 App `bulk-apply` 的 `dry_run` 和实际回读验证表规则。优先安排一条含真实人类会话、Arcubase 数据、业务动作、保存和回读的完整链路；共享数据、权限和契约明确后再安排并行。联调包含已知允许与拒绝主体、角色调整、撤权和直接数据入口；项目涉及数字员工代办或 `conversation_member` 时，再验证代办的发起/执行身份。写上线条件和恢复准备，但不声称这些测试已经完成。

## 交叉检查

提交渲染前检查：术语和对象在九份中一致；每项用例有数据、权限、入口、契约和验收去向；状态转换不冲突；技术选择支持而不覆盖业务边界；路线图未绕过依赖；所有设计关键问题已经清零。检查失败时回到材料、分析或澄清，不用额外模板掩盖缺口。

逐份对照已经完整读取的同编号参照。03 必须能直接找到四项：表清单、每表原生字段、Link、业务流；字段至少明确 label、key、原生类型代码、required、unique、default_value_mode/value 和类型所需 options。只有真实 ID、当前 SDK 方法或目标环境行为需要实施取证；已经由随包契约明确的原生类型、字段语义、Link 结构和 epoch-seconds 写入要求应在本次设计写清。机械渲染审核只核落盘一致性，不能替代本项内容核对。
