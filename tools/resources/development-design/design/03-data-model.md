---
title: 03 - 数据模型（Data Model）
type: added-writing-reference
source: 为九件体系新增；非王磊原八份原稿
status: reference-only
updated: 2026-10-06
---

# 03 - 数据模型（Data Model）

## 加载链（上下游）

**上游**：`../nine-document-authoring.md §使用原则` — 起草独立数据建模文件时读取本参照。

**管辖文件（下游）：**
- `../../SKILL.md §起草九份文件` — 将本文件的结构用于项目的 `03-data-model.md`。

**同级联动：**
- `01-concept.md` — 统一业务对象与术语。
- `02-use-cases.md` — 从真实用例决定需要保存、读取和改变的事实。
- `04-security-privacy.md`、`07-api.md` — 对齐 Arcubase access rule 与调用契约。

> **新增写作参照。** 本文件由当前九件体系新增，用于补足王磊原八份中的数据建模层。它规定共享、持久、可查询的业务事实采用 Arcubase 原生表、FieldVO 字段和 `linkto` 关系；不提供任何项目的默认业务表或固定平台 ID。

## 1. 总共有哪几张表

先声明本项目采用既有 App 或新 App。既有 App 用 `whoami`、App 列表和 `app get` 的实读证据指向精确 App ID、现有表、schema 与 stable field key；新 App 写出待批准的表、字段、`linkto` 关系和访问模型，随后在实施阶段创建。新建表必须带非空 `fields` 数组。表 ID、`schema_version`、`field_id_seq`、二维 `layout` 和真实 field ID 由既有 schema 或建表回读取得；field 与 ingress 的 stable TypeScript-compatible `key` 到位后才生成 typed client。新建或修改架构只写计划结构，不预填未读到的 App、table、field、actor 或 row ID。

再列出承载业务事实的 Arcubase 表。每一行说明一个 `DataRecord` 代表什么；页面、报表、临时计算和业务角色自身不因出现于界面就成为业务表。角色成员关系使用 Arcubase organization actor 与表规则表达；对象归属、负责人和审批人仍按业务需要保存在业务表中。

`DataRecord.id` 是平台记录地址及 Link 目标记录的依据。面向人、合同或外部系统的业务编号需作为显式业务字段设计，不能把 `DataRecord.id` 当作业务编号。

| Arcubase 表名 | 一条 `DataRecord` 代表什么 | 对应业务对象 / 用例 | 表 ID 状态 | 业务编号字段 | 权威来源 | 主要状态 | 是否需要历史记录 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 《表名》 | 《一行的业务含义》 | `UC-xx` | 《既有实读 / 新建回读》 | 《field key 或不适用》 | 《系统或业务记录》 | 《状态或不适用》 | 《是 / 否及原因》 |

表是否存在、哪一方拥有权威记录、是否保留历史会改变业务结果或权限时，先向人确认。业务语义已经明确时，Skill 可以提出表名和计划 schema，作为待审核的设计推导。

## 2. 每张表分别有哪些字段

每张表用一个小节写 Arcubase FieldVO。`label` 是展示名，`key` 是稳定的 TypeScript-compatible 代码键；两者分别列出。真实 `field.id` 在既有 schema 读取或建表回读后写入，不能猜测。每个字段显式说明 `required`、`unique`、`default_value_mode` 和 `value`；类型专属 `options` 按当前官方 schema 证据给出。

### 《Arcubase 表名》

**一条记录代表：**《说明》  
**表 ID / schema 版本 / field ID 序列：**《既有实读，或新建后回读》  
**权威记录与写入者：**《说明》

| label（展示名） | key（稳定代码键） | FieldVO 类型 | 业务含义 | 必填 | 唯一 | 默认值模式 / 值 | 类型专属 options 与证据 | 记录职责 | 可读 / 可写角色 | 已确认约束 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 《字段展示名》 | `field_key` | `text` / 《按证据选择》 | 《说明》 | 是 / 否 | 是 / 否 | 《明确值或无》 | 《当前 schema / 实施前读取》 | 《业务编号 / 业务事实 / 派生值 / 系统元数据》 | 《Arcubase 原生角色》 | 《值域、格式、不可变等》 |

字段设计遵守以下边界：

- 从已证实类型中按需要选择，例如 `text`、`textarea`、`number`、`datetime`、`boolean`、`select`、`status`、`member`、`file`、`linkto`、`lookup`、`rollup`、`formula` 或 `serialnumber`。`text` 取代 `string`，`member` 取代 `user`；每种类型需要自己的已证实 `options` 形状。
- 业务编号通常是有 stable `key` 的显式字段，并在确有唯一性要求时写 `unique: true`。`DataRecord.id` 只用于平台记录寻址、读写和 Link 目标。
- `datetime` 字段写入前明确时区；行写入使用有限整数 epoch seconds，首次写入后读回比对目标时刻。日期前缀序列号、未确认的 serial 选项和任意默认行为均需先以当前帮助或实测确认。
- `lookup`、`rollup` 的关系必须指向真实的本地 `linkto` field ID。`tags` 和 `workflow_status` 不手工加入 schema。附件、计算、导入导出、索引或字段级可见性只在用例或规则需要时列出。

## 3. 多维表格之间的 Link 及关系

业务关联使用 Arcubase `linkto`（或已证实适用的 `relation`）字段。每条关系写出源字段到 `relation.entity_id` 目标表的方向、`relation.app_id`、目标显示/查询字段、选择结构和业务含义。目标记录以其 `DataRecord.id` 为 Link 和行查询的依据，不能假定通过业务编号、SQL 外键或自动 join 关联。

| 源表.字段 | FieldVO 类型 | 目标 `app_id / entity_id` 状态 | `mode` | `structure` | 目标显示 / 查询 field ID | 业务流中的写入或变更事件 | 业务含义 | 反向、删除、归档边界 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `《源表》.《link_key》` | `linkto` | 《既有实读 / 新建回读》 | `manual` / `auto` | `single` / `multiple` | 《实读或建表回读》 | `BF-xx`《事件》 | 《说明》 | 《源→目标；逆向、级联或保留须有实读证据》 |

`linkto` 的 `relation` 在实施时需要真实的 `app_id`、`entity_id`、`type: entity`、`show_fields`、`queryFields`、`condition` 和默认 `sorts`。设计可以先决定哪一条业务关系、单选或多选和显示语义；真实 target field ID 与完整 payload 在目标 schema 可读后补齐。当前契约没有自动反向关系、`target_field_key`、SQL join 或级联删除的证明，文档只描述有证据的方向和处理规则。未选择 Link 时，行数据可出现空数组；已填 Link 的具体行值序列化要经创建和读回验证。

关系表、明细表或状态历史表应说明其必要性。衍生目标字段用 `lookup` 或 `rollup` 表达，并以实际 `local_linkto_field_id`、`target_field_id` 和 `target_field_type` 为依据。

## 4. 这些表与 Link 承载怎样的业务流

选择每条关键业务流，按实际步骤说明读取哪些 Arcubase 表、以哪个 `DataRecord.id` 或业务字段寻址、写入哪些 FieldVO、Link 怎样建立或变更、状态怎样变化、由谁触发、结果到哪里回读。流程编号与 `02-use-cases.md`、审核前分析中的 `BF-xx` 对应。

### `BF-xx / UC-xx`《业务流名称》

1. **触发与读取：**《角色或系统经 Workbench/受证实入口读取的表、字段、Link、记录 ID 或业务编号；所依据的状态和当前有效授权。》
2. **判断与动作：**《使用的事实或规则；写入的表、FieldVO、Link 或派生字段；所需 Arcubase 原生角色与对象条件。》
3. **状态与回读：**《状态从何值变为何值、何时写历史、用生成的 typed ingress client 如何回读、谁看到结果。》
4. **异常与人工决定：**《重复、缺件、拒权、失败、Link 为空或未知结果的处置；谁接手。》

必要时用一张简表补充：

| 流程步骤 | 读取（表 / `DataRecord.id` 或业务字段） | 写入 / 状态变化 | `linkto` 使用 | 角色或对象条件 | 回读 / 验收结果 |
| --- | --- | --- | --- | --- | --- |
| 《步骤》 | 《表.字段》 | 《表.key 或状态》 | 《关系或不适用》 | 《Arcubase 角色与业务条件》 | 《可检查结果》 |

完成检查：每个需要持久保存的用例事实有 Arcubase 位置；每个业务编号与平台 `DataRecord.id` 的职责分开；每个状态变化有触发和责任；每条 Link 能解释业务含义及其已证实方向；字段、关系和状态不与权限、页面或 API 矛盾；schema、行值或平台能力尚未实测的部分明确列为实施前验证。
