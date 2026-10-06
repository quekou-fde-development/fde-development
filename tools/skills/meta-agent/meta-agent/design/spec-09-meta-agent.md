---
title: 企业大脑 v1 · Meta Agent 规格（09.20）
version: 09.20.1
status: spec_frozen_pending_distillation
updated: 2026-09-20
graph: "../README.md#internal-evidence-not-included"
predecessors:
  - "../README.md#internal-evidence-not-included"
  - "../README.md#internal-evidence-not-included"
  - "../README.md#internal-evidence-not-included"
---

# 企业大脑 v1 · Meta Agent 规格（09.20）

本件定义**数字员工的批量生产机器**。前件 `06-arch-09.16/spec-09.16.md` 定义席位结构与落值；本件定义产出这些席位的编制器。两者冲突改前件，本件不改变任何席位的行为约定。

范围：单个数字员工的编制。系统层（工作区、知识库、ArcuBase、本体、排程、外部入口）不在本件范围。

## 一 · 两类 meta agent

生产机器的目标有两个，写面不同、可验收面不同，因此是两个 skill。

| | **FDE meta agent** | **Builder agent** |
|---|---|---|
| 产物 | 团队私有数字员工，`sourceType=team_private` | 市场数字员工产品，`bworker_*` + `bwv_*` |
| 写入面 | `https://fde.autostaff.cn` 团队管理 API | `octopus-builder-cli` → `https://builder.autostaff.cn` |
| 定义字段 | 提示词、简介、工具键、模型与思考、访问策略、KB 读写、工作区授权、汇报线、技能挂载（九键） | `hasInitPhase`、`initSkill`、`promptSpec`、`quickStartPrompts`、`toolkitKeys`（五键） |
| 租户实体 | 必须绑定：员工 id、工作区 UUID、KB 路径、ArcuBase 表 | 禁止出现任何租户实体 |
| 头像通道 | `POST /private-digiworkers/{avatar\|bio-picture}:upload-url` → PUT PNG → PATCH `*PreviewToken` | `workers upload-avatar` / `workers upload-bio-picture` |
| 版本 | 无版本，PATCH 覆盖即生效 | `versions create` → `config set` → `skills upload` → `scan` → `update --secret-level` → `publish` |
| 升级 | 不存在 | 已雇实例不随发布更新，租户端逐实例「Builder 来源升级」按钮 |
| 先例 | 09.16 十九席 | 企业谋士团 v3 |
| skill 名 | `fde-meta-agent` | `builder-agent` |

两类共享的部分只有三样：六段提示词模板、思考骨架四位、出图交接契约。三者各自唯一权威源在本目录 `contracts/`。

## 二 · 共同形态：输入一席、输出一体

两个 skill 都不管系统、不管批量。批量是外层驱动（Codex 或 Claude Code）对席位清单的循环，skill 自身每次只处理一个对象。

```
席位清单 (批)  →  [ skill × N ]  →  员工/产品 (单)
                       ↑
                  出图交 Codex（夏洛克裁定）
```

FDE 侧一次编制的产物是「一个数字员工 + 完整回读证据」；Builder 侧是「一个产品 worker + 一个已发布版本 + 完整回读证据」。

## 三 · FDE meta agent skill

### 3.1 输入

一份席位规格（seat spec），源自图谱节点，形如 `contracts/seat-spec.md §二`。五块：

| 块 | 内容 | 来源 |
|---|---|---|
| 身份块 | `display_name` / 逻辑席位键 / 代号 / `tier` / `kind` / `human_facing` / `parent` / `name_origin` | 图谱节点 |
| 职能块 | `responsibility` 一句；`domain` 的 slug / label / role_id / isolation / kb / workspace；**参数包六维** | 图谱节点 + 域参数包 `params.json` |
| 权限块 | 九键取值。KB 读写路径、工作区授权、访问策略可从域推导；工具键、模型策略、技能按席类默认；回报目标与 ArcuBase 权限必须显式给 | 图谱节点 + 默认表 |
| 面孔块 | 复用：现有头像与简介图 URL + 本地副本；生成：人物参考（演员 / 剧 / 年份 / 参考图） | 图谱节点 `face` + 09.14 交付清单 |
| 环境块 | 发布号、team id、现役员工目录、路由合同、模型目录、技能目录 | 运行时读取，禁止写死 |

### 3.2 处理

十步，每步留 intent 与 response。

| 步 | 动作 | 断言 |
|---|---|---|
| P0 | 连通性探针：`GET /private-digiworkers` 与 `/skills?limit=200` | 两接口 200；目录 JSON 非空 |
| P1 | 规格校验：五块齐备；域席六维与同类席有差异（机检）；九键每个值有写路由 | `check_domain_differentiation.py` 通过；无「无法写入的配置项」 |
| P2 | 解析目录：逻辑键 → `employee_id` / `worker_id`；无则登记待建 | 每个回报目标可解析或标 UNRESOLVED |
| P3 | 编译提示词六段（`contracts/prompt-segments.md`） | 骨架四标签与非职责声明逐字出现；域席 ③⑥ 两段齐备；④ 段按 `kind` 与 `id` 选中恰一条 |
| P4 | 派生简介：职责首句（自动委派读此字段） | 非空、≤120 字、与职责首句逐字一致 |
| P5 | 出图请求单：复用则哈希比对，生成则按契约出单交 Codex | 生成路径必须带系列风格块与三参考图 |
| P6 | 建体：`POST /private-digiworkers`，body 带两个 preview token 与幂等键 | 返回 id；重复运行命中既有身份走 PATCH |
| P7 | 配九键：access-policy → kb-access → workspace-access → reporting-line → team-skills → runtime-config → 终版提示词 | 每键写后即读，深比较相等 |
| P8 | 上传图像并 PATCH token | 服务端图像下载后像素哈希与本地相等 |
| P9 | 十六项回读（`contracts/outputs.md §三`） | 全绿；任一项失败即 `configPass=false` 并保留失败原件 |

顺序固定：**建体必须早于九键**，九键里的 access-policy 决定后续资源能否被挂载读取；**终版提示词最后 PATCH**，因为它引用的 id 必须已存在。

### 3.3 输出

`runs/<release>-meta-agent/<run-id>/` 下七类产物，见 `contracts/outputs.md §一`。平台侧可见面 = 详情页的提示词格、简介、头像、亮相图、九项配置。

## 四 · Builder agent skill

### 4.1 输入

| 块 | 内容 |
|---|---|
| 产品身份 | `name` / `bio` / 头像与亮相图的请求单或现成 URL |
| 形态 | 单体产品，或团队整包（`teams create` + `members set`） |
| 初始化 | `hasInitPhase` / `initSkill` 欢迎词全文 / `quickStartPrompts` |
| 工具键 | 从 `toolsets list` 的二十九键中选，逐个标注理由 |
| 技能包 | `SKILL.md` + `references/` + `scripts/` + `assertions.json`。**包本身由 meta-skill 编译**，本 skill 只负责上传与扫描 |
| 发布策略 | `secretLevel`（public / partner_markets_only）、是否覆盖上架、是否 `publish` |

### 4.2 处理

| 步 | 动作 | 断言 |
|---|---|---|
| B0 | 探针：`auth whoami` 返回非空身份且 profile 正确 | 已登录，team 与作者 id 可读 |
| B1 | **租户无关性 lint**：提示词与欢迎词正则拒 `de_` / `dw_` / `kbd_` / `workspace_` / `lm_` / `team_` / `/kb/` / 租户名 | 零命中，命中即 fail-closed |
| B2 | 编译提示词：六段去掉域段与实体，思考骨架四位保留，深度下沉技能包 | 骨架四标签逐字出现；无实体 |
| B3 | `workers create`（或复用 `workerId`）→ `upload-avatar` / `upload-bio-picture` | worker 回读头像 URL 非空 |
| B4 | `versions create` → `config set --file definition.json` | 五键回读一致 |
| B5 | `skills upload` 逐文件带 `--path` → `skills scan` | `file_count` 与上传数相等；记录 `packageSha256` |
| B6 | `versions update --secret-level` → `versions publish` | `listedVersionId` 指向本版；旧版 `superseded` |
| B7 | 发升级计划：列出已雇实例 | `upgrade-plan.json` 逐实例一行，动作归租户 |

### 4.3 输出

`bworker_*` / `bwv_*` / 五键定义回读 / 扫描哈希 / 上架状态 / 交付清单 / 升级计划。

## 五 · 出图（夏洛克裁定：统一交 Codex）

两个 skill 都不出图。skill 负责三件：**写请求单、过 QA 门、做上传与哈希回读**。出图执行体是 Codex。

请求单契约见 `contracts/image-handoff.md`。要点：

- 一次请求产出一对：头像（方）与亮相图（横）。
- 生成必须带**三参考图**：图一定身份与服装，图二图三定系列风格与构图，且提示词显式声明「不借其脸」。
- 系列风格块（介质 / 背景 / 品牌纹样 / 配色 / 光线 / 两种构图）整块复用，见契约 §三。
- 视觉 QA 是**独立闸**：逐张人工或独立复核者勾 `approved`，未勾即 `IMAGE_NOT_REVIEWED`，fail-closed，不许上传。
- 上传后服务端图像下载回来做**像素哈希**，与本地相等才算过。

## 六 · 共享件的单一权威源

| 共享件 | 权威源 | 消费方 |
|---|---|---|
| 六段模板与骨架 | `contracts/prompt-segments.md` | 两个 skill |
| 出图请求单 | `contracts/image-handoff.md` | 两个 skill |
| 六维参数包结构 | `contracts/seat-spec.md §三` | FDE skill |
| 回读项 | `contracts/outputs.md §3` | FDE skill；Builder 侧取同名子集 |

Builder skill 不复制正文，编译期记录权威源路径与 `sha256`，构建脚本断言哈希相等，漂移即失败。

## 七 · 本次裁定的四个开放点

| # | 议题 | 裁定 | 理由 |
|---|---|---|---|
| 1 | 目录 JSON 是否继续挂在提示词里 | **移出**。改为挂载团队技能 `live-directory`，提示词只留本席边约束（parent、升级路由、回报目标、ArcuBase 权限）。带 P0 读探针，探针失败则回退 `mechanism: prompt_embedded` 并登记限制 | 09.16 每席尾部约 5 KB，任一员工重建要求全员重 PATCH，与「只管单个」相冲 |
| 2 | 职能席是否补推导位与跨轮位 | **不补**。公共段加一条**非职责声明**：本席不设反例推演与跨轮策略，须判断交 M3N，须深度推理交 C1D | 职能席的定位是快反与域内取证，判断与多轮策略在上游席位；写进模板比留白更可检 |
| 3 | 六段编译器是否各自持一份 | **不各自持**。FDE skill 持权威源，Builder 侧按哈希引用 | 模板是行为约定，两份必然漂移 |
| 4 | 出图执行体 | **统一 Codex**，skill 只做请求单、QA 门、上传回读 | 夏洛克本轮裁定 |

## 八 · 验收

| 面 | 判据 |
|---|---|
| FDE skill | 十六项回读全绿；提示词逐字节相等；图像像素哈希相等；三席试编（一域席、一受限域席、一入口席）后现网详情页人工核对 |
| Builder skill | 五键回读一致；扫描 `file_count` 相等；`listedVersionId` 正确；lint 零命中；一次 dry-run 停在上架前 |
| 回归 | 用 09.16 十九席做影子编制，比对与 `runs/20260916-rebuild/after/` 的差异，差异逐条判定为「设计变更」或「缺陷」 |

## 九 · 落地顺序

1. 本件冻结（现态）。
2. `fde-meta-agent` 与 `builder-agent` 两个 skill 各走 meta-skill 九步蒸馏。
3. 影子编制三席，判差异。
4. 全量重编十九席为 09.20 身体。

第 2 步属 C 级，等夏洛克拍板。
