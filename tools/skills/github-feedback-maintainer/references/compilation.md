---
title: GitHub 反馈维护编译记录
type: skill-reference
status: candidate
updated: "2026-10-07"
---

# GitHub 反馈维护编译记录

## 第 1 步：目标与环境

目标是返回真实 Issue URL 和经过回读的当前状态，或返回 duplicate、reconcile-required、权限不足或未确认失败回执。固定目标为 quekou-fde-development/fde-development 的 GitHub Issue；feedback 目录只保存导航与示例，不能另写实时状态台账。

本包调用外部可变 GitHub API，并持久化 journal 和锁，所以 workflow_mode 为 stateful。唯一七参数 transaction kernel 是 scripts/kernel.py 的 apply_transaction；真实生产入口是 scripts/entrypoints.py 的 apply_feedback_effect，feedback.py 的 transaction 通过该入口协调生产 adapter。

## 第 2 步：判断段与执行段

判断段包括：批准和调用者授权、create/duplicate/reconcile 分流、Issue 是否已被他人修改、未知外部状态和恢复是否需要人工裁断。

执行段包括：固定仓库与身份检查、创建 Issue、普通补充说明或处理决定说明、Issue PATCH、独立回读和 journal checkpoint。stateful contract 以 create_issue、add_comment、patch_issue 三种真实效果作为 effect boundary；维护决定评论与普通评论共享 add_comment 效果类型。

## 第 3 步：当前执行与契约

当前 production path 以 request_id、preview 摘要、attempt_id 和本地 fence 保存 journal；创建和评论分别用不可见 marker 查重，状态维护先写处理说明再 PATCH 并回读。stateful_contract.json 将三种 effect boundary 统一绑定到唯一 injected-adapter kernel，并将 production entrypoint 与 kernel 的当前全量 SHA-256 绑定。

2026-10-07 的独立 stateful runner 隔离 fault/scenario probe 已通过 M12。该机械结果由 stateful_contract.json 记录，不能替代黑背老六宿主部署、可信批准集成或公开生产 canary。

## 第 4 步：判断四相位

Mutation safety：检索 preview、approval、journal、GitHub identity、Issue、labels 和 comments；整合 request marker、revision、现有状态和授权；生成 create、duplicate、comment、update 或 reconcile outcome；审核固定仓库、唯一 marker、批准权限和回读结果。

Recovery：检索 journal 与独立 GitHub readback；整合 intent/receipt/checkpoint 和远端 marker；生成 verified receipt 或 RECONCILE_REQUIRED；审核未知状态时没有重复写入。

## 第 5 步：竞争方案

Issue API 被选择，因为仓库接口明确将 Issue 定义为反馈与状态权威，并已有 Issue 表单和队列。受控 PR 是后续手册或工具变更的审查载体，可以被 Issue 关闭说明引用。git push 不创建反馈记录，也不属于本包授权范围。直接在 feedback Markdown 更新状态会违反仓库接口的唯一权威约束。

## 第 6 步：当前编译状态

本包已有 canonical stage runner、assertions.json、独立审计器、golden/mutant、FakeGitHub 生产适配器验证和本机 GitHub TEST 回执。2026-10-07 的完整 meta validator 完成 M1–M12。独立行为与触发路由评测以及黑背老六宿主 deployment canary 仍未形成完成口径，结论以实际交付证据为准。
