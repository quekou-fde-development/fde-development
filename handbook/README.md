---
title: FDE 流程与开发手册
version: "10.09"
---

# FDE 流程与开发手册

先看项目总流程，再进入其中技术开发环节的细则。这里的两份 HTML 分别承担以下职责：

| 阅读顺序 | 文件 | 解决什么问题 |
|---|---|---|
| 1 · FDE 总流程 | [FDE 流程图（内部执行版）](FDE_流程图_内部执行版.html) · [下载 HTML](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/FDE_流程图_内部执行版.html) | 袁黎明提供的总图：项目整体阶段、角色分工、决策节点与交接关系 |
| 2 · 技术开发细则 | [开发技术手册 Markdown](development-handbook.md) · [下载 HTML 阅读版](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/index.html) | 展开总流程中的调研输入、架构设计、审核、计划、开发、测试与发布 |

`index.html` 是开发技术手册阅读版。总流程图保留原件；技术手册的项目产物与批准记录按具体项目执行。

项目送审按技术手册 §5.1—5.2 执行：Arcubase 母项目关联固定编号仓库，包含业务流程与 spec 的开发文档，以及独立开发计划，作为两项交付物，先 push，再由项目经理发邮件异步送审；取得对应版本的通过记录后进入开发。

母项目与子项目（场景）由 Arcubase 管理，关键决定、实际阶段、卡点、支持事项和验收结果在 Arcubase 维护；GitHub 保存按场景编号关联的开发成果与版本记录。

## 填写与配套资料

- [调研输入空表](inputs/通用调研输入文档_10.06.md)：填写调研事实、原件位置、业务约束和待澄清项。
- [开发计划模板](inputs/开发计划模板_10.08.md)：项目经理组织填写任务、依赖、负责人、排期、资源与验证安排，保存为对应场景开发目录的 `plan/开发计划.md`。
- [九份 spec 写作参照](architecture-reference/)：理解九份开发规格的内容与写作粒度；实际项目按证据重新设计。
- [配套资源总 ZIP](FDE开发配套资源包_10.06.zip)：保存设计参照、工具包及专项工具指引；解压后读包内 README。
- [开发工具](../tools/)：每个工具的说明、源码、ZIP、版本和验证范围。
- [提交反馈](../feedback/)：提交问题、查询处理进度并查看填写示例。

## 下载与维护

下载两个 HTML 和资源总 ZIP 后，将三者放在同一目录，在浏览器打开总流程图或 `index.html`；技术手册中的总流程、源码和资源包链接按仓库目录解析。需要全部相对链接时，下载整个仓库并保留目录结构。

技术手册的 Markdown 是正文编辑源，HTML 由 `build/render.mjs` 生成，摘要见 [build-manifest.json](build-manifest.json)。修改正文后在本目录运行 `node build/render.mjs`。项目架构仍须取得总架构师的版本审核记录。
