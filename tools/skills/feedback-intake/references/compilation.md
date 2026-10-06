---
title: 反馈接收与整理编译记录
type: skill-reference
status: candidate
updated: "2026-10-07"
---

# 反馈接收与整理编译记录

## 加载链（上下游）

**上游**：../SKILL.md §反馈接收与整理 — 宿主需要把自然语言反馈整理为公开预览时读取。

**管辖文件（下游）：**
- intake-contract.md — 提取字段、公开边界和示例。
- ../SKILL.md §交接与答复 — 预览经真实用户确认后的交接出口。

**同级联动：**
- ../../github-feedback-maintainer/SKILL.md §提交与查询 — 已批准预览进入 Issue 维护流程时同步读取。
- https://github.com/quekou-fde-development/fde-development — 公开 Issue 反馈的固定目标仓库。

## 第 1 步：目标与环境

交付物是一个已脱敏的公开反馈预览，或一条合并后的最少澄清问题。成功条件是预览含来源公开称呼、项目公开代称、对象和版本、类别、现象、期望和可选证据，且宿主将实际用户确认绑定到当前预览摘要。缺对象、现象或期望时停止提交并追问；不能安全概括为公开内容时停止在澄清。

本包只有所有生成物留在显式私有 run-dir 时才是 artifact。写共享队列、持久去重台账或外部系统会使它进入 stateful 范围。

## 第 2 步：判断段与执行段

判断段包括资料充分性、公共脱敏安全性和确认是否绑定当前预览。执行段包括提取结构化字段、写私有 draft、生成预览和向维护包交接。任何判断结果均必须路由到补充信息、生成预览、等待确认或停止公开提交四个出口之一。

## 第 3 步：现有执行证据与机械覆盖

本包的 canonical contract 已将 prepare_feedback 建模为一个 handoff operation，并登记 artifact_hash、schema_conformance、receiver_receipt 三条 T1 断言。scripts/audit.py 独立消费 assertions.json；fixtures/golden_prepare_feedback 和三个定向 mutant 已证明三条断言各自能拒绝对应变异。scripts/run_verification.py 在普通验证环境调用 sibling github-feedback-maintainer 的真实 render 与 wrap_preview，不复制其业务实现。

此包的 handoff 只证明交接物及接收回执；它不将宿主语言抽取、语义脱敏、真实用户批准或 GitHub 外部提交表述为该包已完成的机械证明。已知模式扫描只能覆盖声明的模式；语义脱敏仍须独立人工或黑箱审阅。

## 第 4 步：判断四相位

资料充分性：检索本轮事实和字段合同；整合为最小公开字段；生成 draft 或一次合并问题；审核对象、现象、期望是否齐全并给出明确路由。

公开安全性：检索计划公开的字段和证据；整合隐私类别与项目代称；生成删除类别可见的公开预览；审核已知模式和语义疑点，疑点一律回到安全概括或停止。

确认绑定：检索当前 preview_sha256 和可信宿主的实际用户消息；整合身份、时间和版本；生成 approval 记录；审核记录是否来自当前预览及可信身份，不满足则等待。

## 第 5 步：证据与竞争边界

字段和公开边界以 intake-contract.md 与仓库接口 feedback 字段为准。GitHub Issue 是交接后的状态权威；PR 用于后续内容变更审查，git push 不属于本包的反馈动作。自然语言抽取、最少追问和语义脱敏均需独立运行证据，不能从脚本的格式检查反推。

## 第 6 步：当前编译状态

2026-10-07 的完整 meta validator 结果为 M1–M12 通过。本文件仍不替代 assertions.json、golden/mutant 或宿主外部行为验收；交付侧证据索引另行保存。
