---
title: meta-skill 分发说明
version: "10.06.3"
created: 2026-10-06
---

# meta-skill 分发说明

## 加载链（上下游）

**上游**：总资源包 `README.md` §小包目录。

完整保留本次读取的 Meta Skill 3.10.1 包。先读 meta-skill/SKILL.md，再按任务加载 references；scripts、agents、fixtures 和 runner_binding 一同保留。运行依赖 Python 3、目标 AI 宿主的执行/评测能力，以及其 system skill-creator quick validator。依赖版本以目标环境核对为准。
