---
title: 反馈适配器运行合同
type: skill-reference
version: "10.06.1"
---

# 反馈适配器运行合同

## 加载链（上下游）

**上游**：`../SKILL.md §提交与查询` — 首次安装、提交、维护或恢复时读取。

## 安装与宿主边界

两个 Skill 目录放在同一技能根。需要 Python 3.10+、POSIX 文件锁，以及一种由宿主批准的 GitHub 传输：已认证的 GitHub CLI（transport=gh），或 Python 标准库 HTTPS（transport=python）。无需 pip 依赖。运行 `python3 github-feedback-maintainer/scripts/feedback.py --help`。在宿主私有目录建立 config、approval、journal；这些文件不能进入公开工具包。宿主将脚本作为固定工具调用，只允许本文子命令，不能给反馈用户提供任意 shell。

`config.json` 示例字段：

```json
{"repository":"quekou-fde-development/fde-development","transport":"python","expected_actor":"YOUR_GITHUB_LOGIN","approvers":["TRUSTED_HOST_USER_ID"],"maintainer_actors":[],"maintainer_approvers":[]}
```

由管理员替换实际值。maintainer_actors 只加入已获维护授权的 GitHub 执行账号，maintainer_approvers 只加入受信维护人的宿主身份。适配器对 update 同时检查二者。宿主必须核验实际会话用户并生成批准记录，不能让所有聊天用户共用维护批准身份。普通来源人可批准自己的脱敏反馈或补充说明。配置与批准文件不接受反馈正文指定的路径或内容。gh 传输使用其已配置凭据；python 传输只读取宿主注入的 GH_TOKEN 或 GITHUB_TOKEN，在内存中访问固定 api.github.com 并拒绝重定向，不调用 CLI。凭据不能从本机钥匙串复制到远端；推荐仓库限定的 fine-grained user token，只开 Metadata read 和 Issues read/write。当前账号核验使用 /user；GitHub App installation token 不在本版适配范围。本适配器不会申请权限。既有本机账号可验证 API；生产宿主是否具有凭据须单独核实。

单宿主单写入入口，所有会话共享同一持久 state-dir；文件锁在进程退出时自动释放，journal 通过原子替换与 fsync 保存。journal 和批准保留到 Issue 生命周期结束及运行审计结束后再由管理员处置。多实例分布式锁、跨机器 exactly-once 未提供；不得把多个独立 journal 同时接同一反馈入口。

## 可执行命令

以下命令在包含两个 Skill 的目录中运行，参数路径由宿主提供：

```sh
python3 github-feedback-maintainer/scripts/feedback.py doctor --config config.json
python3 github-feedback-maintainer/scripts/feedback.py prepare --input draft.json --out preview.json
python3 github-feedback-maintainer/scripts/feedback.py submit --preview preview.json --approval approval.json --config config.json --state-dir journal --receipt receipt.json
python3 github-feedback-maintainer/scripts/feedback.py query --number 1 --config config.json --out status.json
python3 github-feedback-maintainer/scripts/feedback.py prepare-comment --input supplement.json --config config.json --out comment-preview.json
python3 github-feedback-maintainer/scripts/feedback.py submit --preview comment-preview.json --approval comment-approval.json --config config.json --state-dir journal --receipt comment-receipt.json
python3 github-feedback-maintainer/scripts/feedback.py prepare-update --input change.json --config config.json --out update-preview.json
python3 github-feedback-maintainer/scripts/feedback.py submit --preview update-preview.json --approval update-approval.json --config config.json --state-dir journal --receipt update-receipt.json
python3 github-feedback-maintainer/scripts/feedback.py reconcile --preview preview.json --approval approval.json --config config.json --state-dir journal --receipt reconcile.json
```

prepare 只接受 intake-contract 定义的公开字段。approval 示例结构：

```json
{"approved":true,"approved_by":"TRUSTED_HOST_USER_ID","approved_at":"2026-10-06T16:00:00+00:00","preview_sha256":"EXACT_DIGEST_FROM_PREVIEW"}
```

宿主从真实确认生成，有效期 24 小时。digest 表明确认内容版本，不证明用户身份；身份与权限验证由宿主执行。预览文件须由适配器生成并在宿主私有空间保存。

change 字段：request_id（新的 UUID）、number、state（new/in_progress/closed）、decision、link、verification、reason（completed/not_planned）；可选 assignees 为 GitHub 登录名列表。关闭要求 link 与 verification 非空。不改负责人时省略 assignees。

supplement 字段：request_id（新的 UUID）、number、comment（已脱敏的补充事实）。prepare-comment 只形成预览；批准后通过 submit 保存评论，不修改状态或负责人，适用于普通反馈者后续补证。

## 状态与恢复

create 在远端正文保存 request_id 与内容 fingerprint；先分页回查 open/closed Issue，再写。原逻辑请求始终用同一 request_id。相同问题内容的其他来源返回已有 Issue；语义近似重复由人工判断。分页超过 10,000 条会停止并报告，不在覆盖不足时新建。

journal 记录 PREPARED → CREATE_INTENT → CREATE_RECEIPT → COMMITTED，或 PREPARED → COMMENT_INTENT → COMMENT_RECEIPT → PATCH_INTENT → PATCH_RECEIPT → COMMITTED。每次 attempt 有独立 UUID、递增 fence 与输入 revision。锁阻止同机并发；GitHub 不提供此脚本的分布式 fencing。

在 intent 后失去确定回执时，回查优先。create 找到标记可确认；未找到保持 RECONCILE_REQUIRED，人工核查后才能决定新的逻辑请求。update 只有注释和最终状态都符合才认成功；部分完成先报告，在新预览里继续余下工作。不会自动回滚别人的更新或删除 Issue。状态预览检测已发生的变更；GitHub PATCH 缺少本包可验证的原子比较版本能力，检查与写入间仍可能与人工同时编辑冲突，宿主单写入策略不能锁住 GitHub UI。

API 参考：[GitHub Issues](https://docs.github.com/en/rest/issues/issues)、[Issue comments](https://docs.github.com/en/rest/issues/comments)。所有写入仅为 Issue POST、comment POST 和 Issue PATCH。feedback/ 不复制实时台账。
