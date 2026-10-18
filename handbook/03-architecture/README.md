---
title: 架构设计手册（架构师）
version: "10.19"
status: 发布索引
---
# 架构设计手册（架构师）

[阅读手册10.19](architecture-handbook.md) · [全部模板](../02-project-management/templates/README.md)

## 阅读与执行

1. 先依据现场事实及baseline形成客户业务流和整体架构graph（A），再定义客户问题及经营意义；以target和baseline的gap明确产品价值，设计产品、AI采用依据、信息流与完整客户体验流。
2. 解决方案明确后，用Meta Spec依据同版A、方案和技术约束形成技术架构B的九份spec，编制独立开发计划与技术可行性评估，核对范围报价。
3. PM把A、解决方案、范围报价和技术材料作为**一套方案一次送审**，总架构师同时判断商业可行性、技术可行性及整体一致性。
4. 整体审核通过并落实开工条件后，FDE沿[开发手册](../04-development/development-handbook.md)执行开发、测试与发布。

各类客户采用上述统一顺序，记录整套明确版本的结论、范围与条件。PM代表客户核对业务和基线、协调资源并组织正式送审。

## 输入与配套

| 内容 | 文件 | 文档Skill |
|---|---|---|
| 调研输入 | [通用调研输入](../02-project-management/templates/02-research/通用调研输入文档_10.06.md) | |
| 基线与试点记录 | [既有记录表](../02-project-management/templates/02-research/基线与试点对比记录表.md) | |
| 问题和产品定义 | [解决方案模板](../02-project-management/templates/03-solution/解决方案.md) | |
| 范围分期与报价 | [模板](../02-project-management/templates/03-solution/范围分期与报价.md) | |
| 整套送审 | [邮件格式](../02-project-management/templates/03-solution/送审邮件.md) | |
| 九份开发规格 | [写作参照](../02-project-management/templates/04-development/architecture-reference/README.md) | [Meta Spec](../../tools/meta-spec/README.md) |

Meta Workflow沿开发手册§2—3使用现有方法，独立Skill尚未发布。资料与文件位置按[PM手册](../02-project-management/project-management-handbook.md#locations)执行。

[返回四块索引](../README.md)
