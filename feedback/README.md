---
title: 开发规范反馈
version: "10.15.4"
status: active
---

# 反馈

[填写反馈表单](https://github.com/quekou-fde-development/fde-development/issues/new?template=feedback.yml) · [查看全部反馈](https://github.com/quekou-fde-development/fde-development/issues?q=is%3Aissue) · [填写示例](example.md)

登录 GitHub 后填写表单即可提交。先搜索已有反馈；同一问题可在原 Issue 补充版本和证据。

手册与工具问题在GitHub Issue提交，便于统一处理和回查。项目正式送审仍由PM邮件发送，见[两次送审格式](../handbook/02-project-management/templates/03-solution/送审邮件.md)。

表单填写：反馈类型、涉及的文件或工具版本、发生了什么与复现步骤、预期结果、可公开证据（选填）。GitHub 自动保存编号、提交人和时间。此仓库公开，提交前移除客户名称、业务数据、密码和令牌；私有项目问题应提交到该项目的 private 仓库。

## 缺少工具或希望改进工具

提交具体节点、当前做法、输入、期望输出及判断要求，并给出可公开的样例或证据。尚未掌握的判断保留待补，不能用工具生成代替业务决定。

夏洛克统一审核共用手册和工具的修改范围；团队可提交候选或PR，经过审核及对应核验后合入和发布。需要新工具时沿Meta Skill制作流程接续；已有工具问题优先在原Issue跟进，不直接将个人修改作为共用正式版本。

## 处理与回读

维护者确认归属后，在 Issue 的 Assignees 指定接手人，并维护一个状态：

| 状态 | GitHub 表示 | 后续动作 |
|---|---|---|
| 待处理 | Open，标签“待处理” | 核实问题、判断影响、分派接手人 |
| 处理中 | Open，标签“处理中” | 在原 Issue 关联修改 PR、补证据或说明等待条件 |
| 已关闭 | Closed | 最后一条处理记录说明决定、修改链接或未采纳原因、适用的验证结果 |

修复并验证后按 Completed 关闭；重复、移交或不采纳时说明原因及关联地址，按 Not planned 关闭。需要重做时重开原 Issue。进入新状态时移除旧状态标签。

反馈事实和处理状态只维护在对应 Issue。本目录保存填写方法与示例。提交后以 GitHub Issue 的实际状态与处理记录为准。
