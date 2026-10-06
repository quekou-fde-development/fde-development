---
title: Meta Orchestrator 架构分析方法包
version: "10.06.3"
created: 2026-10-06
---

# Meta Orchestrator 架构分析方法包

## 加载链（上下游）

**上游**：总资源包 `README.md` §小包目录。

## 阅读与使用范围

先读 `meta-orchestrator-design/spec.md` 的 §1—4、§6 及 §7 Step 0—3，完成业务流、工作形态判别、系统分段与交接关系。当前设计判据版本为 v1.2。具体项目的产物与送审要求，以随附 HTML 手册第一部分为准。

本包用于架构分析，保留当前设计规格原文。该规格描述完整 Orchestrator 的目标流程；Step 4—5 的正式 Skill 蒸馏、最终 topology 与机械检验属于后续实现，所需 topology_schema 和校验脚本不在本包。架构分析完成不能记为完整 Orchestrator 编译通过。

当前分发状态为设计方法参考。与同一总 ZIP 内的 Meta Skill 包一起阅读；规格中的旧编译器版本及历史迁移附记不作为本次安装命令。源码中的历史归档指针只承担追溯作用，审核前分析无需加载。
