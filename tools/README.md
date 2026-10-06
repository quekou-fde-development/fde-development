---
title: 开发工具
version: 10.07.3
---

# 开发工具

选择需要的工具，阅读入口说明后下载 ZIP。包版本、来源包名、SHA-256、依赖和适用条件见 [完整清单](catalog.json)。

| 工具 | 阅读入口 | ZIP | 内容与适用范围 |
|---|---|---|---|
| Meta Skill | [阅读](skills/meta-skill/README.md) | [下载](packages/meta-skill-3.10.1.zip) | 技能蒸馏工作流、references、scripts、agents 与 fixtures；固定源快照。 |
| Meta Orchestrator | [阅读](skills/meta-orchestrator/README.md) | [下载](packages/meta-orchestrator-10.06.zip) | 业务流与协作分段设计规格；完整编译实现不在此包。 |
| Meta Agent | [阅读](skills/meta-agent/README.md) | [下载](packages/meta-agent-10.06.zip) | 参数化候选、两条路线与配套合同/代码；按目标宿主完成验证。 |
| Workbench App Development | [阅读](skills/workbench-app-development/README.md) | [下载](packages/workbench-app-development-10.06.zip) | Workbench 开发 Skill 与完整 references；准备平台依赖与授权后使用。 |
| Quekou Workbench Frontend | [阅读](resources/quekou-frontend/quekou-workbench-1.0.0/START_HERE.md) | [下载](packages/quekou-frontend-1.0.0.zip) | 原始 1.0.0 前端共享包，保留原许可证与第三方声明。 |
| Specialist Tool Guides | [阅读](resources/specialist-tool-guides/README.md) | [下载](packages/specialist-tool-guides-10.06.zip) | 排产、图纸与商品分析指引及官方入口；在线服务按其账号与接口使用。 |
| 九份架构写作参照 | [阅读](resources/development-design/README.md) | [下载](packages/development-design-10.06.zip) | 精确九份写作参照，含新增数据结构；供架构设计阅读。 |
| 自然语言反馈接收 | [阅读](skills/feedback-intake/SKILL.md) | [下载](packages/feedback-intake-10.06.1-candidate.zip) | 已挂载并通过宿主离线检查；整理反馈、集中澄清并形成脱敏公开预览。 |
| GitHub 反馈提交与维护 | [阅读](skills/github-feedback-maintainer/SKILL.md) | [下载](packages/github-feedback-maintainer-10.06.1-candidate.zip) | 已挂载并通过宿主离线检查；提交、查询、补证与状态维护，正式 GitHub 配置待完成。 |
| Meta Architecture Development | [阅读](skills/meta-architecture-development/SKILL.md) | [下载](packages/meta-architecture-development-10.06.zip) | 已验证候选，从调研输入形成九份待总架构师审核的设计文档；真实项目与安装后运行待验证。 |

## 调研与流程资料

- [通用调研输入空表](resources/通用调研输入文档_10.06.md)：填写后的客户材料保存在对应项目的受控仓库。
- [FDE 上层流程图](resources/fde-flow/)：查看开发小环所处的流程。
- [开发手册](../handbook/)：每一步的输入、产出、工具和审核关系。

来源包没有附许可证的条目在清单中照实记录；仓库未替原作者增授许可。实际项目记录采用的工具版本与验证条件。

## 反馈接口安装包

[下载两项反馈 Skill 合集](packages/feedback-channel-10.06.1-candidate.zip)。解压后保持两目录同级，按 [运行合同](skills/github-feedback-maintainer/references/operations.md)准备宿主配置和安全凭据。

两项 Skill 已挂载黑背老六，70 文件核对与真实宿主离线检查通过；冻结包的本机真实 API 测试已完成。正式宿主仍缺限定仓库凭据、预期 GitHub 账号和可信用户批准映射，真实提交闭环尚未验证。当前可直接使用 [GitHub 反馈表单](../feedback/)。
