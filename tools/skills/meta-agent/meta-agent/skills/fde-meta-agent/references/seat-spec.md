# 契约 · 席位规格（seat spec）

**权威源**：本件。**消费方**：`fde-meta-agent`。**状态**：职能席已定；功能席结构预留、未采用。

席位规格是编制器的唯一输入，一份 JSON 描述一席。不读图谱直接编制，读图谱只发生在**生成规格**这一步，那一步在本包之外——执行体是上游 `enterprise-brain-v1/runs/20260916-rebuild/prepare-domain-params.py` 或其后继，不随包发。

## 一 · 全貌

```json
{
  "schema_version": "seat-spec-09.20.1",
  "release": "09.20",
  "logical_id": "m3_i",
  "identity": { },
  "function": { },
  "permissions": { },
  "face": { },
  "environment": { }
}
```

五块的字段面分别见本文件 §二（identity）、§三（function）、§四（permissions）、§五（face）、§六（environment）。缺任何一块即 `SPEC_INCOMPLETE`，不进入编制。

## 二 · identity 块

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `logical_id` | string | 是 | 逻辑席键，全批唯一。跨批稳定，作幂等键主体 |
| `code` | string | 是 | 平台显示代号（M3I / C1D / D-006） |
| `display_name` | string | 是 | 中文名（陈文锦 / 半截李 / 霍仙姑） |
| `function_label` | string | 是 | 职能标签（对内检索 / 反例推演 / 人力） |
| `tier` | enum | 是 | 平台层档。见 §二.1 |
| `kind` | enum | 是 | `entrance` / `domain_seat` / `restricted_domain` / `judgement` / `execution` / `system` |
| `human_facing` | bool | 是 | 是否直接面向真人。决定 `common` 段中真人裁决条目的措辞强度 |
| `parent` | string \| null | 是 | 上级 `logical_id`。根为 null |
| `name_origin` | object | 否 | 取名来源（人名 / 影视角色的出处），进面孔块的理由说明 |

`tier` 取值：`orchestrator` / `domain` / `support` / `external`。与 `kind` 正交：`m1_entry` 是 `external` + `entrance`。

## 三 · function 块

`responsibility` 一句，必须能单独作 `bio` 的首句——这是硬约束，因为平台用 `bio` 做自动委派判定（`allowAutoDelegate`）。

`domain` 子块（域席必填，非域席为 null）：

| 字段 | 说明 |
|---|---|
| `slug` / `label` | 域键与中文域称 |
| `role_id` | 域角色 id（本体侧） |
| `isolation` | 隔离语义：`derived_from_workspace` / `explicit` / `none` |
| `kb` | 域 KB 前缀与挂载树 |
| `workspace` | 域工作区 UUID、`ident`、显示名、`permission` |

**参数包六维**（域席之间差异的全部载体，机检对象）：

| 维 | 字段 | 说明 |
|---|---|---|
| 1 | `templates` | 该域标准产出物模板（表 / 卡 / 单的结构） |
| 2 | `landing_tables` | 落表定义。`domain_owned[]` 每项 `{table_key, app_id, table_id, name, required_fields}` |
| 3 | `relation_gates` | 关系闸。非 `d_fde` / `d_ops` 席只取 `kind=generic` |
| 4 | `signing_roles` | 签署角色（谁能签什么） |
| 5 | `kb_prefix` | KB 前缀 |
| 6 | `workspace` | 工作区授权面 |

差异判据（P1 机检）：同 `tier` 同 `kind` 的任意两席，六维至少三维取值不同；同域两席允许同 `kb_prefix` 但必须异 `landing_tables`。

**快反三闸**（`fast_response`，域席必有）：

```json
{"gates": ["条目存在", "条目与问题匹配", "条目带引用"],
 "all_required": true,
 "missing_evidence": "UNVERIFIED",
 "human_approval_does_not_follow_from_gate_pass": true}
```

最后一条是本设计的硬约束：三闸全过**不推出**可以动真人世界。凡涉及真人的动作另走审批路由。

## 四 · permissions 块（九键）

| # | 键 | 平台载体 | 必填 |
|---|---|---|---|
| 1 | 提示词 | `promptSpec.text` | 是（编译器产出，规格不填） |
| 2 | 简介 | `bio` | 是（编译器产出首句） |
| 3 | 工具键 | `toolkitKeys[]` | 是 |
| 4 | 模型与思考 | `llmModelId` + `thinkingConfig` | 是 |
| 5 | 访问策略 | `accessPolicy` | 是 |
| 6 | KB 读写路径 | `kbPaths[]` + `kbWritePaths[]`（`manual_kb_allowlist`） | 是（可为空数组） |
| 7 | 工作区授权 | `workspace_access` | 是 |
| 8 | 汇报线 | `reporting_line` | 是 |
| 9 | 技能挂载 | `team-skills` | 是（可为空数组） |

规格里每键带 `value`、`carrier`（写路由，如 `PUT /digiemployees/{id}/runtime-config`）、`source`（推导来源或 `explicit`）。九键中**任一键找不到写路由即拒编**——这是防止设计出现不可落地的配置项。

附带的两个**非员工级**项，规格里显式标注机制：

| 项 | 机制 | 处置 |
|---|---|---|
| 回报目标 | `prompt_constraint` | 写进提示词边约束，并原句声明「reply-targets 为会话级平台能力，本名单在本席提示词中约束路由；不把它声称为员工级硬 ACL」 |
| 记忆配置 | `not_supported` | 不写。产品定义中删除，不编造字段 |

## 五 · face 块

```json
{"rule": "reuse" | "generate",
 "reuse": {"avatar_url": "...", "bio_picture_url": "...", "local_copy": "...", "source_employee": "..."},
 "generate": {"name": "...", "actor": "...", "show": "...", "year": "...",
              "reference_image": "...", "face_hair_costume": "..." },
 "reason": "同名复用 / 新造"}
```

`rule=reuse` 时必须给 `local_copy`，编制器做字节比对，不比对即 `FACE_REUSE_UNVERIFIED`。`rule=generate` 时 `reference_image` 指向人物参考图，与实际出图请求单同源。

## 六 · environment 块

| 字段 | 说明 |
|---|---|
| `release` | 发布号，作幂等键成分 |
| `team_id` | 目标团队 |
| `live_directory` | 现役员工目录（运行时读取，禁止写死） |
| `routing_contract` | parent / quick_lookup / escalation / out_of_domain / approval 五个去向的逻辑键 |
| `model_catalog` | 可用模型与思考档 |
| `skill_catalog` | 可挂载团队技能 |

环境块是规格里唯一**允许运行时变化**的块。P0 探针失败时，编制器不得回落为写死值，而是报 `ENVIRONMENT_UNREADABLE`。

## 七 · 规格生成（上游）

规格由 `prepare-domain-params.py` 及其后继产出，输入三源：

```
graph-09.16.json（节点）  ─┐
ArcuBase 落表映射         ─┤─▶ prepare-domain-params.py ─▶ seats/<logical_id>.json
identities 对账表         ─┘
```

生成器只做合并与字段对齐，不做判断。任何需要判断的取值（回报目标、ArcuBase 权限、面孔复用与否）必须在输入源里已存在，生成器遇到缺失即报错并把该席标 `SPEC_REQUIRES_HUMAN`。
