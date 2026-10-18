---
title: 九份架构写作参照
version: "10.19"
---

# 九份架构写作参照

[返回项目管理手册](https://github.com/quekou-fde-development/fde-development/blob/main/handbook/02-project-management/project-management-handbook.md#stage-45) · [全部模板](https://github.com/quekou-fde-development/fde-development/blob/main/handbook/02-project-management/templates/README.md)

这九份文档用于理解架构送审的内容与写作粒度。王磊八份案例按九件序号映射，新增独立数据结构 `03-data-model.md`；案例中的产品、技术栈和旧编号按实际项目重新设计。

Meta Spec 10.19 已在[工具入口](https://github.com/quekou-fde-development/fde-development/tree/main/tools/meta-spec/)发布，沿用经确认的 v14。测试结果和保留问题见包内 `verification.json`；每个项目生成的架构仍须总架构师审核。

[调研输入空表](https://github.com/quekou-fde-development/fde-development/tree/main/handbook/02-project-management/templates/02-research/通用调研输入文档_10.06.md)填写已知事实和原件位置。架构 Skill 自带同一组 `references/design/` 供运行读取；本目录是人工阅读入口，两者九份文件一致。本目录承载开发方案B的九份写作参照。前置客户分析A用于形成解决方案；Meta Spec据同版A与产品方案生成B，分析保存在本次`working/`。A、解决方案、范围报价、九份`design/*.md`、独立计划与技术可行性判断组成一套方案，一次送审。配套计划使用[开发计划模板](https://github.com/quekou-fde-development/fde-development/blob/main/handbook/02-project-management/templates/04-development/开发计划模板_10.08.md)。

## 九份文档

- [01-concept.md](01-concept.md)
- [02-use-cases.md](02-use-cases.md)
- [03-data-model.md](03-data-model.md)
- [04-security-privacy.md](04-security-privacy.md)
- [05-site-architecture.md](05-site-architecture.md)
- [06-page-layout.md](06-page-layout.md)
- [07-api.md](07-api.md)
- [08-tech-stack-and-directory.md](08-tech-stack-and-directory.md)
- [09-implementation-roadmap.md](09-implementation-roadmap.md)
