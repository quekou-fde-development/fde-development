---
title: FDE 流程与开发手册
version: "10.09.2"
status: 发布版
---

# FDE 流程与开发手册

先看项目总流程，再进入其中技术开发环节的细则。这里的两份 HTML 分别承担以下职责：

| 阅读顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 · FDE 总流程 | [FDE 流程图（内部执行版）](FDE_流程图_内部执行版.html) · [下载 HTML](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/FDE_流程图_内部执行版.html) | 袁黎明提供的总图：项目整体阶段、角色分工、决策节点与交接关系 |
| 2 · 技术开发细则 | [开发技术手册 Markdown](development-handbook.md) · [下载 HTML 阅读版](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/index.html) | 展开总流程中的调研输入、架构设计、审核、计划、开发、测试与发布 |

`index.html` 是开发技术手册阅读版。总流程图保留原件；技术手册的项目产物与批准记录按具体项目执行。

项目先按技术手册 §0 在 Arcubase 登记母项目与场景，再新建“母项目编码＋客户名称＋期号”的 private 仓库，并在母项目仓库下建立各场景文件夹。送审按 §5.1—5.2 执行。将开发架构（A+B）和独立开发计划作为两项交付物，先 push，再由项目经理发邮件异步送审；取得对应版本的通过记录后进入开发。

送审时每个场景只需 `workflow/`、`design/` 和 `plan/`，README 提供关联与阅读导航。计划提前写明测试与发布安排；审核通过后先建立 `releases/` 并开发，形成可测试版本后再建立 `tests/`，记录测试、缺陷和复测。技术复核与发布批准完成后上线，部署和交接资料归入相应开发版本，正式环境测试结果写入 `tests/`。实现目录按实际工具和框架组织，不统一要求建立 `src/`。

母项目与子项目（场景）由 Arcubase 管理，关键决定、实际阶段、卡点、支持事项和验收结果在 Arcubase 维护；GitHub 项目仓库作为内部开发协作台，只保存各场景的开发架构、计划、实现和技术记录。项目内容、客户背景、调研原件及沟通解释在 Arcubase 维护，README 只保留标识、关联链接与开发目录索引。

执行顺序：**Arcubase 登记 → 新建母项目仓库与场景文件夹 → Meta Workflow 产出文件组 A → Meta Spec 基于 A 产出文件组 B → 编制独立开发计划 → 将开发架构（A+B）和开发计划两部分送审。**

## 填写与配套资料

- [调研输入空表](inputs/通用调研输入文档_10.06.md)：填写调研事实、原件位置、业务约束和待澄清项。
- [开发计划模板](inputs/开发计划模板_10.08.md)：项目经理组织填写任务、依赖、负责人、开发时间、开发方式与工具、预计 token 消耗、资源与验证安排，保存为对应场景开发目录的 `plan/开发计划.md`。
- [九份 spec 写作参照](architecture-reference/)：理解九份开发规格的内容与写作粒度；实际项目按证据重新设计。
- [配套资源总 ZIP](FDE开发配套资源包_10.06.zip)：保存调研与开发计划模板、设计参照、工具包及专项工具指引；解压后读包内 README。
- [开发工具](../tools/)：每个工具的说明、源码、ZIP、版本和验证范围。
- [提交反馈](../feedback/)：提交问题、查询处理进度并查看填写示例。

## 下载与维护

下载两个 HTML 和资源总 ZIP 后，将三者放在同一目录，在浏览器打开总流程图或 `index.html`；技术手册中的总流程、源码和资源包链接按仓库目录解析。需要全部相对链接时，下载整个仓库并保留目录结构。

技术手册的 Markdown 是正文编辑源，HTML 由 `build/render.mjs` 生成，摘要见 [build-manifest.json](build-manifest.json)。修改正文后在本目录运行 `node build/render.mjs`。项目架构仍须取得总架构师的版本审核记录。
