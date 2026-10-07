# Reference · Builder 产品契约

**归属**：`builder-agent/references/builder-product.md`。**写入面**：`@syngy/octopus-builder-cli` 0.1.1 → `https://builder.autostaff.cn`。

## 一 · CLI 实测面（0.1.1）

| 组 | 子命令 |
|---|---|
| `auth` | `login` / `logout` / `whoami` / `profiles` |
| `profile` | `get` / `update --display-name --bio --avatar-url --partner-markets-only` |
| `toolsets` | `list`（29 项） |
| `workers` | `list` / `get` / `create --name --bio --avatar-url --bio-picture-url` / `update` / `upload-avatar` / `upload-bio-picture` |
| `workers versions` | `list` / `create` / `update --secret-level public\|partner_markets_only --config-file` / `publish` |
| `workers config` | `get <workerId> <versionId>` / `set <workerId> <versionId> --file` |
| `workers skills` | `list --prefix --cursor --limit --q` / `upload --path --content-type` / `delete` / `scan` |
| `teams` | `create --name --summary --description --avatar-url` / `members set --file` / `versions publish` |
| `authorization-groups` | `create --resource-scope` / `resources set` / `codes create --type market\|team --max-redemptions --expires-at` / `bindings` |
| `help-json` | 全量命令树 |

`agents` 不是子命令。早期记录里的 `agents create/versions/config/skills` 已失效，以 `help-json` 为准。

## 二 · 五键定义

`workers config get` 返回 `definitionPayload`，恰五键：

| 键 | 类型 | 说明 |
|---|---|---|
| `hasInitPhase` | bool | 是否有初始化阶段 |
| `initSkill` | string | 首条客户消息前展示的品牌 / 引导文案 |
| `promptSpec` | `{type:'static', text}` | 系统提示词 |
| `quickStartPrompts` | string[] | 快捷开场（先例 4 条） |
| `toolkitKeys` | string[] | 从 29 项中选（先例 14 项） |

`configPayload` 在版本列表上为 `{}`。五键 schema 为**服务端所有**，CLI 包内无定义；任何新增键必须先 `config set` 后 `config get` 验证回读，不猜。

`definition.json` 形态：

```json
{"definitionPayload": {
  "hasInitPhase": true,
  "initSkill": "...",
  "promptSpec": {"type": "static", "text": "..."},
  "quickStartPrompts": ["...", "...", "...", "..."],
  "toolkitKeys": ["...", "..."]
}}
```

## 三 · 提示词编译（Builder 侧）

取六段的 ①②④⑥，去 ③⑤。⑥ 的公共段保留注入防御 / 真人裁决 / 工作区与 KB 分工三段与骨架四位，删目录。深度下沉到技能包（`SKILL.md` + `references/`），提示词只留身份、职责、席位特段与协作约束。

**租户无关性 lint**（B1，fail-closed）：

```
/(^|[^a-z])(de_|dw_|kbd_|workspace_|lm_|team_)[a-f0-9]/i
/\/kb\//
/(缺口|杭州缺口|White_Matter|白质)/
/(^|[^A-Za-z0-9])[A-Za-z]{1,2}\d[A-Za-z]\b|(^|[^A-Za-z0-9])[A-Za-z]{1,2}\d(?=[一-鿿])/
```

对 `promptSpec.text`、`initSkill`、`quickStartPrompts[]`、技能包全部文本文件逐一扫。零命中才进 B2。命中列文件与行号。

P4 抓租户席位代号（`M3N` / `C1D` / `T2审批席` 一类字母数字混排的内部代号）。它不能靠 `compile_prompt` 的 `no_seat_code` 兜底：那一条只反查改写表里的四个字符串，换个大小写或换一个表外代号就穿透到已发布的市场提示词（实测 `m3n` 与 `T2审批席` 均全链零拦截）。P4 放行 `GPT-4`、`H100`、`v2`、`B2 段` 一类技术串——判据是代号后紧跟中文或为纯字母数字三段式。

## 四 · 命令序列

```
B0  auth whoami
B3  workers create --name <n> --bio <b>            → bworker_*
    workers upload-avatar      <bworker> --file images/<key>-avatar.png
    workers upload-bio-picture <bworker> --file images/<key>-bio.png
B4  workers versions create <bworker>              → bwv_*
    workers config set <bworker> <bwv> --file definition.json
    workers config get <bworker> <bwv>             （五键回读）
B5  workers skills upload <bworker> <bwv> --path SKILL.md        --content-type text/markdown
    workers skills upload <bworker> <bwv> --path assertions.json --content-type application/json
    workers skills upload ... references/* scripts/*
    workers skills scan   <bworker> <bwv>          （file_count / packageSha256）
B6  workers versions update  <bworker> <bwv> --secret-level public
    workers versions publish <bworker> <bwv>       （listedVersionId 切换）
B7  升级计划：列出 sourceType=builder 且 source 指向本 bworker 的租户实例
```

复用既有 `bworker` 时跳过 `create`，从 `versions create` 起。旧版自动 `superseded`。

## 五 · 先例事实（企业谋士团 v3）

| 项 | 值 |
|---|---|
| worker | `{{BUILDER_PRODUCT_WORKER_ID_1}}` |
| author | `{{BUILDER_AUTHOR_ID_1}}` |
| 版本链 | `{{BUILDER_VERSION_ID_1}}`(v1) → `{{BUILDER_VERSION_ID_2}}`(v2) → `{{BUILDER_VERSION_ID_3}}-d8a8-4b13-887b-01fa000222f4`(v3，listed / public) |
| 技能包 | `SKILL.md` 26,456 B + `assertions.json` 11,175 B + `references/` + `scripts/`，共 10 文件 228,241 B |
| `packageSha256` | `705b45c78244eae5177a4dcb5d866a676cd81180844c11728bc4cba4a1822f9e` |
| 配置完成度 | 100% |
| 图像主机 | `pub.autostaff.cn/builder/public/workers/<bworker>/avatar\|bio-picture/<uuid>.(png\|jpg)` |
| 五键实测 | `hasInitPhase=true`，`initSkill` 471 字符，`promptSpec.text` 1,183 字符，`quickStartPrompts` 4，`toolkitKeys` 14 |

## 六 · 升级语义

- Builder 发布**不**自动升级已雇实例。08-25 v3 上架后，08-19 入职的实例 `{{FDE_EMPLOYEE_INSTANCE_ID_1}}` 仍持旧版快捷入口。
- 租户侧入口：`POST /api/v1/teams/{t}/digiemployees/{e}/builder-upgrade`（单员工）、`/market/plans/{p}/builder-upgrade`、`/market/workers/{w}/builder-upgrade`；员工记录带 `builderUpgradeAvailable` / `builderUpgradeScope`。
- skill 产出 `upgrade-plan.json`，逐实例 `{team_id, employee_id, from_version, to_version, action: "builder-upgrade", executed: false}`。动作归租户。

## 七 · 团队整包（可选形态）

`teams create` 后 `members set --file members.json` 把多个 `bworker` 组成一个可雇团队；`teams versions publish` 上架整包。整包的租户侧升级走 `builderUpgradeDigiTeamDesc` 对应的整队入口。团队整包不改变单 worker 的五键定义，只增加成员关系一层。
