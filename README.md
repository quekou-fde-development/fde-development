---
title: 缺口 FDE 手册与工具
version: "10.15"
status: 发布索引
---

# 缺口 FDE 手册与工具

FDE 总流程、架构手册、开发技术手册、配套工具与反馈入口集中于本仓库。

| 内容 | 当前状态 | 阅读入口 |
|---|---|---|
| FDE 总流程 | 原流程图 | [流程图](handbook/FDE_流程图_内部执行版.html) |
| 架构手册 | 10.14.1 · 试行 | [Markdown](handbook/architecture-handbook.md) |
| 开发技术手册 | 10.09.2 · 发布版 | [Markdown](handbook/development-handbook.md) · [下载 HTML](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/index.html) |
| 项目管理手册 | 入口待补 | |
| 开发工具 | 各工具按自身版本维护 | [工具与下载](tools/) |
| 问题反馈 | 提交、查询与处理记录 | [反馈入口](feedback/) |

阅读顺序：**总流程 → 架构手册 → 开发技术手册**。两本手册的阶段分工、试行审核衔接及模板入口见[手册索引](handbook/)。

仓库保留三个主要目录：

- `handbook/`：手册、流程图、已发布模板与写作参照。
- `tools/`：每个工具的说明、源码、版本 ZIP 及使用条件。
- `feedback/`：反馈填写、处理与查询说明。

缺少的材料保留空位，补齐后再建立下载链接。具体项目的文件在知识库「FDE全链」对应项目查阅；开发版本与技术记录沿开发技术手册在对应的私有项目仓库维护。共用模板和工具的版本、验证范围见[工具清单](tools/catalog.json)。

修改共用规范时提交 Pull Request，说明变化、依据及验证结果。架构与正式方法变更由总架构师审核。
