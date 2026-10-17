---
title: 架构设计手册（架构师）
version: "10.17"
status: 发布索引
---
# 架构设计手册（架构师）

[阅读手册10.17](architecture-handbook.md) · [全部模板](../02-project-management/templates/README.md)

## 阅读与执行

1. 先依据现场事实及baseline形成客户业务流和整体架构graph（A），再定义客户问题及经营意义；以target和baseline的gap明确产品价值，设计产品、AI采用依据、信息流与完整客户体验流。
2. PM提交客户分析A、方案与范围报价，总架构师进行**方案审核（闸1）**，判断商业可行性。
3. A/B客户方案通过后，团队依据A与方案形成开发方案B的九份spec、独立开发计划和技术可行性评估，总架构师进行**开发审核（闸2）**。C客户允许提前准备开发材料并与方案一起送审。
4. 开发审核通过并落实开工条件后，FDE沿[开发手册](../04-development/development-handbook.md)执行开发、测试与发布。

A/B客户依次送审，C客户可并行准备、合并送审；各部分引用同版客户分析与方案，保留商业与技术两项审核结论。PM代表客户核对业务和基线、协调资源并组织正式送审。

## 输入与配套

| 内容 | 文件 | 文档Skill |
|---|---|---|
| 调研输入 | [通用调研输入](../02-project-management/templates/02-research/通用调研输入文档_10.06.md) | |
| 基线与试点记录 | [既有记录表](../02-project-management/templates/02-research/基线与试点对比记录表.md) | |
| 问题和产品定义 | [解决方案模板](../02-project-management/templates/03-solution/解决方案.md) | |
| 范围分期与报价 | [模板](../02-project-management/templates/03-solution/范围分期与报价.md) | |
| 两次送审 | [邮件格式](../02-project-management/templates/03-solution/送审邮件.md) | |
| 九份开发规格 | [写作参照](../02-project-management/templates/04-development/architecture-reference/README.md) | [Meta Spec](../../tools/meta-spec/README.md) |

Meta Workflow沿开发手册§2—3使用现有方法，独立Skill尚未发布。资料与文件位置按[PM手册](../02-project-management/project-management-handbook.md#locations)执行。

[返回四块索引](../README.md)
