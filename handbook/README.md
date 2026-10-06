---
title: 开发手册
version: 10.06.4
---

# 开发手册

[阅读 Markdown 正文](development-handbook.md) · [下载 HTML 阅读版](https://github.com/quekou-fde-development/fde-development/raw/refs/heads/main/handbook/index.html) · [下载配套资源 ZIP](FDE开发配套资源包_10.06.zip)

HTML 下载后可在浏览器打开；配套 ZIP 与 HTML 放在同一目录即可保留离线下载入口。也可下载整个仓库，保留目录结构。

[调研输入空表](inputs/通用调研输入文档_10.06.md) · [开发工具](../tools/) · [提交反馈](../feedback/)

Markdown 是正文编辑源，HTML 由同目录 `build/render.mjs` 生成；版本与源文件摘要见 [build-manifest.json](build-manifest.json)。修改正文后，在本目录运行 `node build/render.mjs` 更新阅读版。当前手册为 10.06.4 待审阅版，具体项目仍须取得总架构师的版本审核记录。
