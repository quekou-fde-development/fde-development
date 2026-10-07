---
title: meta-skill 分发说明
version: "10.06.3"
created: 2026-10-06
---

# meta-skill 分发说明

完整保留本次读取的 Meta Skill 3.10.1 包。先读 [source/SKILL.md](source/SKILL.md)，再按任务加载 references；scripts、agents、fixtures 和 runner_binding 一同保留。运行依赖 Python 3、目标 AI 宿主的执行/评测能力，以及其 system skill-creator quick validator。依赖版本以目标环境核对为准。

## 下载与安装

[下载 3.10.1 ZIP](meta-skill-3.10.1.zip)。安装以此 ZIP 为准，解压后的 `meta-skill/` 为安装根，须连同 references 等文件整体保留。`source/` 是对应的可读源码；外层 README 与 ZIP 不属于 Skill 文件集。
