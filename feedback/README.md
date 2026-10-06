---
title: 开发规范反馈
version: 10.07.1
status: active
---

# 反馈

[填写反馈表单](https://github.com/quekou-fde-development/fde-development/issues/new?template=feedback.yml) · [查看全部反馈](https://github.com/quekou-fde-development/fde-development/issues?q=is%3Aissue) · [填写示例](example.md)

登录 GitHub 后填写表单即可提交。先搜索已有反馈；同一问题可在原 Issue 补充版本和证据。

表单填写五项：反馈类型、涉及的文件或工具版本、发生了什么与复现步骤、预期结果、可公开证据（选填）。GitHub 自动保存编号、提交人和时间。此仓库公开，提交前移除客户名称、业务数据、密码和令牌；私有项目问题应提交到该项目的 private 仓库。

维护者确认归属后，在 Issue 的 Assignees 指定接手人，并维护一个状态：

| 状态 | GitHub 表示 | 后续动作 |
|---|---|---|
| 待处理 | Open，标签“待处理” | 核实问题、判断影响、分派接手人 |
| 处理中 | Open，标签“处理中” | 在原 Issue 关联修改 PR、补证据或说明等待条件 |
| 已关闭 | Closed | 最后一条处理记录说明决定、修改链接或未采纳原因、适用的验证结果 |

修复并验证后按 Completed 关闭；重复、移交或不采纳时说明原因及关联地址，按 Not planned 关闭。需要重做时重开原 Issue。进入新状态时移除旧状态标签。

反馈事实和处理状态只维护在对应 Issue。本目录保存填写方法与示例。当前由人提交和处理；数字员工接入由独立工作线开发。

## 数字员工反馈接口

已提供 [反馈接收 Skill](../tools/skills/feedback-intake/SKILL.md)、[GitHub 提交与维护 Skill](../tools/skills/github-feedback-maintainer/SKILL.md)及[合集 ZIP](../tools/packages/feedback-channel-10.06.1-candidate.zip)。两包为本地已验证候选，宿主接入中；GitHub 安全凭据未配置，黑背老六的真实提交闭环尚未验证。当前可使用上方手工表单提交反馈。

接口工作顺序为：自然语言描述 → 一次集中补齐必要信息 → 展示脱敏公开预览 → 本人确认该版本 → 提交并回读 GitHub Issue → 返回实际链接与状态。公开字段有变化时重新确认；缺少批准或凭据时保留草稿并报告缺件。

补充证据采用新的公开预览与确认；关闭、重开和负责人变更需受信维护人授权。请求重试先回查原请求和已有 Issue，结果不明时停止自动重发。Issue 仍为唯一实时状态来源，手册与代码修改由仓库维护人走受控 PR。

宿主配置、凭据、身份与批准记录、持久 journal 存放在宿主安全区。配置要求和恢复命令见 [运行合同](../tools/skills/github-feedback-maintainer/references/operations.md)；此仓库不分发私有宿主配置。
