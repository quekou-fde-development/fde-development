---
title: FDE开发手册（FDE）
version: "10.15.1"
status: 发布索引
---

# FDE开发手册（FDE）

## 手册正文

| 版本 | Markdown | HTML |
|---|---|---|
| 10.09.2 · 发布版 | [阅读手册](development-handbook.md) | [下载阅读版](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/04-development/index.html) |

架构设计阶段与开发阶段的试行衔接见[架构设计手册入口](../03-architecture/README.md#架构与开发的试行衔接)。

## 模板、参照与资源

现有模板与人工阅读参照统一收在[项目管理手册模板目录](../02-project-management/templates/README.md)，下表直达对应文件。

| 内容 | 入口 |
|---|---|
| 开发计划模板 | [Markdown](../02-project-management/templates/04-development/开发计划模板_10.08.md) |
| 九份 spec 写作参照 | [参照目录](../02-project-management/templates/03-solution/architecture-reference/) |
| 开发配套资源总包 | [下载 ZIP](FDE开发配套资源包_10.06.zip) |
| 通用调研输入空表 | [项目管理手册中的空表](../02-project-management/templates/02-research/通用调研输入文档_10.06.md) |

## 开发工具

| 工具 | 说明、源码与下载 |
|---|---|
| Meta Spec | [进入](../../tools/meta-spec/) |
| Meta Skill | [进入](../../tools/meta-skill/) |
| Meta Agent | [进入](../../tools/meta-agent/) |
| Meta Orchestrator | [进入](../../tools/meta-orchestrator/) |
| Workbench App Development | [进入](../../tools/workbench-app-development/) |
| Quekou Frontend | [进入](../../tools/quekou-frontend/) |

工具保留各自版本和适用条件，详见[工具清单](../../tools/catalog.json)。专项工具指引见手册正文及配套资源总包的 `07-specialist-tools/README.md`。

## 离线阅读与构建

下载整个仓库并保留目录结构，可使用手册、总流程图和模板之间的相对链接。`index.html` 与资源总包位于本目录；总流程图位于 `../01-workflow/`。

HTML 由 [build/render.mjs](build/render.mjs) 生成，同源校验见[构建记录](build-manifest.json)。

[返回四块索引](../README.md) · [反馈入口](../../feedback/)
