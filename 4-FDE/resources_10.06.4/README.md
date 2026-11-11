---
title: FDE 开发配套资源包
version: "11.11.0"
status: 发布版
---

# FDE 开发配套资源包

## 使用顺序

先读同版开发技术手册，再按任务解压 `packages/`。`inputs/调研报告（对内）.md` 用于项目内部调研与事实整理；`inputs/开发计划.md` 用于编排开发任务、资源、时间与验收；未知项保留来源与补料线索。

## 小包目录

| 文件 | 用途与状态 |
|---|---|
| `packages/01-development-design_10.06.zip` | 九份写作参照；王磊八份与第 3 份数据结构 |
| `packages/02-meta-skill_3.10.1.zip` | Meta Skill 文件快照，目标宿主验证按项目完成 |
| `packages/03-meta-orchestrator_10.06.zip` | 设计方法参考，完整编译实现不在本包 |
| `packages/04-meta-agent_10.06.zip` | 参数化制作候选包，目标宿主尚待验收 |
| `packages/05-workbench-app-development_10.06.zip` | Workbench Skill 与完整 references |
| `packages/06-quekou-frontend_1.0.0.zip` | 前端共享原件，核对目标 React 与浏览器兼容性 |
| `00-fde-flow/FDE_流程图_内部执行版.html` | 九节点内部执行流程图 |
| `07-specialist-tools/README.md` | OctoPlanner、老马 drawings、SKU Radar 的输入、产物与网址 |

## 其他入口

Meta Spec 11.05.1 已在[工具目录](https://github.com/quekou-fde-development/fde-development/tree/main/tools/meta-spec/)发布，下载包从该入口取得；本总包保留以上六个小包。已知问题与验收范围见 Skill 包内 `verification.json`。

开发送审统一提交开发计划、架构设计（含架构图）、解决方案；范围与报价作为附件。审核通过后，FDE 按项目需要用 Meta Spec 撰写所需 spec，不送审。

客户背景、调研、客户分析A、方案、沟通和签字原件保存在知识库「FDE全链」对应项目；Arcubase／Work OS 保存项目结构、进展、状态及文件链接；GitHub 保存 A 的同版引用与来源链接、所需 spec、开发计划、实现与技术记录。手册和工具反馈使用仓库的 [GitHub Issue 入口](https://github.com/quekou-fde-development/fde-development/issues/new?template=feedback.yml)。

## 核验与使用

本版复用已整理的六个工具包快照，保留各包的依赖与验证状态；候选和方法参考按所标范围使用。`manifest.json` 与 `SHA256SUMS.txt` 记录文件和包内哈希。三份流程输入由 `4-FDE/build/package.py` 从仓库正本同步，任何包的存在或文件校验通过都不代表目标项目生产验收完成。
