---
title: 开发工具
version: "10.09"
---

# 开发工具

按任务选择工具。同一工具的说明、源码和版本 ZIP 放在同一目录；版本、SHA-256、依赖和验证范围见 [工具清单](catalog.json)。

| 工具 | 阅读入口 | ZIP | 用途与状态 |
|---|---|---|---|
| Meta Spec | [阅读](meta-spec/) | [下载](meta-spec/meta-spec-10.09.zip) | 调研输入生成九份架构文档；验证候选，待总架构师审核与目标环境验证 |
| Meta Skill | [阅读](meta-skill/) | [下载](meta-skill/meta-skill-3.10.1.zip) | 技能蒸馏工作流与完整配套源码，3.10.1 固定快照 |
| Meta Agent | [阅读](meta-agent/) | [下载](meta-agent/meta-agent-10.06.zip) | 数字员工与市场产品两条制作路线；参数化候选，目标宿主待验收 |
| Meta Orchestrator | [阅读](meta-orchestrator/) | [下载](meta-orchestrator/meta-orchestrator-10.06.zip) | 业务流、系统分段与协作关系设计参考；完整编译实现未随包提供 |
| Workbench App Development | [阅读](workbench-app-development/) | [下载](workbench-app-development/workbench-app-development-10.06.zip) | 工作台开发 Skill；按包内要求准备平台依赖和授权 |
| 缺口前端共享包 | [阅读](quekou-frontend/) | [下载](quekou-frontend/quekou-frontend-1.0.0.zip) | 原始 1.0.0 前端包，保留许可证、组件和第三方声明 |

## 使用与安装

安装以各条目列出的 ZIP 为准，解压后按包内说明选择安装根。`source/` 保存可读源码，外层下载文件不纳入 Skill 安装。Meta Agent 的两个安装根位于其解压包的 `meta-agent/skills/`；前端原包的版本目录与许可证保持原样。

来源包未附许可证的情况在清单中记录；使用范围按原包条款与项目授权执行。实际项目记录采用的工具版本和验证条件。

[开发手册](../handbook/) · [调研输入空表](../handbook/inputs/通用调研输入文档_10.06.md) · [九份架构写作参照](../handbook/architecture-reference/) · [上层 FDE 流程图](../handbook/FDE_流程图_内部执行版.html) · [提交反馈](../feedback/)
