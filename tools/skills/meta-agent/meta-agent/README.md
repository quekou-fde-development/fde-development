---
title: Meta Agent 参数化分享副本
kind: share_snapshot
status: candidate_not_deployed
source_snapshot: enterprise-brain-v1/streams/09-meta-agent
load_chain:
  - README.md
  - design/spec-09-meta-agent.md
  - design/architecture.md
  - design/skill-layout.md
  - skills/fde-meta-agent/SKILL.md
  - skills/builder-agent/SKILL.md
sanitization_manifest: sanitization-manifest.json
---

# Meta Agent 参数化分享副本

本目录是从 Meta Agent 开发源导出的**参数化候选副本**。其中的项目平台实体标识已替换为一致的占位符；内部逻辑路径导航已改为本说明。原始运行记录、评测工作区、夹具、编译记录、scratchpad 与状态原文均未随包提供。

## 加载链

1. 先读本说明和 `sanitization-manifest.json`，确认副本范围及参数化类别。
2. 读 `design/spec-09-meta-agent.md`、`design/architecture.md`、`design/skill-layout.md`，确定席位、平台边界与两类 Meta Agent 的分工。
3. 按目标选择 `skills/fde-meta-agent/` 或 `skills/builder-agent/`。每个候选包只处理一个席位或一个产品；批量循环由外层驱动。
4. 在接入目标平台前，用本组织已批准的席位/产品定义、权限、KB、工作区与数据资源替换参数化占位符，并建立本组织的运行证据目录。

## 当前状态与使用边界

- 本副本是候选实现参考，**未完成目标平台验收，也不代表生产已部署版本**。
- 两个候选包当前把真实平台网络调用置于段外 handoff；包内脚本负责读取落盘件、编译局部产物与核验回执。它们不能单独证明目标平台已经建体、写配置、上传资源或发布版本。
- 含外部建体、配置、上传和发布的生产实现需要 `stateful` 恢复契约：稳定幂等键、intent、effect receipt、独立 readback、reconcile-before-retry、故障恢复与人工裁决出口。本副本未附该生产恢复实现。
- `restricted_domain` 访问策略尚须进入正式生产断言并完成真实平台回读；golden package hash 的稳定计算范围也须重新定义。真实平台 shadow/canary、权限验证、图像回读和最终人类裁决仍是上线前阻断项。
- 本副本未附 fixtures 与 `generate_fixtures.py`。因此可阅读和审查运行核心，不能声称已在本副本中重现完整夹具审计、mutant sweep 或原项目的通过结论。

## 外部依赖

- Python 3 标准库可运行所附脚本核心。
- FDE 路径还需要目标团队的管理面身份与写权限、FDE 平台 API、已批准的 seat spec、员工目录、KB 路径、工作区、数据资源、技能目录及图像交接能力。
- Builder 路径还需要目标环境的 `octopus-builder-cli`、Builder 管理面身份与发布权限、产品定义、可上传的技能包、扫描和发布能力。
- 出图由独立图像执行体完成；本副本只保留请求、QA 与回读约束。

## 内部证据未随包

原始设计引用的内部图谱、前代编译器、运行回执、平台快照、评测和工作流记录没有随本副本导出。它们不能在外部环境中解析，也不能替代目标环境的真实验收。
