# 契约 · 产物与回读

**权威源**：本件。**消费方**：两个 skill。

## 一 · 产物目录

```
runs/<release>-meta-agent/<run-id>/
├── seats/<logical_id>.json            输入快照（冻结，编制期间不变）
├── identities/<logical_id>.json        平台 id 对账表（跨席依赖的唯一来源）
├── desired/<logical_id>-profile.json   意图态九键
├── desired/<logical_id>-effective-prompt.json  提示词逐字节权威副本
├── desired/<logical_id>-bio.json       简介
├── evidence/<logical_id>-<step>.json   每步 intent 与 response
├── images/<key>-avatar.png / -bio.png
├── images/qa.json                      QA 闸结论
├── after/<logical_id>-images.json      上传回读（URL + 双方哈希）
├── readback.json                       回读表
└── manifest.json                       整批汇总
```

`run-id` 含发布号，作幂等键成分。同一 `run-id` 重跑即续跑，不新建目录。

### 1.1 identities 对账表

```json
{"logical_id": "m3_i", "code": "M3I", "display_name": "陈文锦",
 "employee_id": "de_...", "worker_id": "dw_...", "role_id": "...",
 "parent": "m1_entry", "resolved_at": "<timestamp>", "source": "created" | "existing"}
```

后编制席位的 ⑤ 段从本表解析回报目标。解析不到即写 `UNRESOLVED` 并在该目标建体后补 PATCH——补 PATCH 留下一条独立 evidence。

## 二 · 写入序列（九步）

| 序 | 键 | 载体 |
|---|---|---|
| 1 | 建体 | `POST /private-digiworkers`（body 含名称、简介、工具键、初版提示词、图像 preview token、幂等键） |
| 2 | 访问策略 | `PATCH /digiemployees/{id}/access-policy` |
| 3 | KB 读写 | `PUT .../kb-access`（`manual_kb_allowlist`） |
| 4 | 工作区授权 | `PUT .../workspace-access` |
| 5 | 汇报线 | `PUT .../reporting-line` |
| 6 | 团队技能 | `PUT .../team-skills` |
| 7 | 模型与思考 | `PUT .../runtime-config` |
| 8 | 图像上传 + token | `:upload-url` → PUT → PATCH |
| 9 | **终版提示词** | `PATCH /private-digiworkers/{id}` |

序 1 必须最先（后者依赖 id）。序 2 必须早于 3–7（访问策略决定资源可否被挂载读取）。序 9 最后（提示词引用的 id 必须已存在）。序 3–7 之间无依赖，可并，但证据逐键留。

每键写后**即读**，深比较相等。写读之间不插入其他席位的写。

## 三 · 回读项（FDE 十六项）

| # | 项 | 判据 | 失败码 |
|---|---|---|---|
| 1 | 员工存在 | `GET` 返回 200 且 id 等于对账表 | `EMPLOYEE_MISSING` |
| 2 | 提示词逐字节 | 与 `effective-prompt.json` 全等 | `PROMPT_DRIFT` |
| 3 | 简介 | 非空且与职责首句逐字一致 | `BIO_DRIFT` |
| 4 | 工具键 | 集合相等，顺序不计 | `TOOLKIT_DRIFT` |
| 5 | 模型 | `llmModelId` 相等 | `MODEL_DRIFT` |
| 6 | 思考档 | `thinkingConfig` 相等 | `THINKING_DRIFT` |
| 7 | 访问策略 | `mode` 与主体集合相等 | `POLICY_DRIFT` |
| 8 | KB 读路径 | 集合相等 | `KB_READ_DRIFT` |
| 9 | KB 写路径 | 集合相等 | `KB_WRITE_DRIFT` |
| 10 | 工作区授权 | 集合相等且 `permission` 语义一致 | `WORKSPACE_DRIFT` |
| 11 | 汇报线 | 上级 id 相等 | `REPORTING_DRIFT` |
| 12 | 团队技能 | 挂载清单相等 | `SKILL_DRIFT` |
| 13 | 头像 | 服务端像素哈希等于本地 | `AVATAR_MISMATCH` |
| 14 | 亮相图 | 服务端像素哈希等于本地 | `BIO_IMAGE_MISMATCH` |
| 15 | 骨架四位 | 四个标签逐字出现在提示词 | `SKELETON_MISSING` |
| 16 | 环境探针 | 挂载技能可达，或已登记回退 | `DIRECTORY_UNRESOLVED` |

任一失败即 `configPass=false`，保留失败原件，不重试覆盖。第 16 项的失败是可接受态**仅当**已按回退路径登记 `DIRECTORY_FALLBACK`。

## 四 · Builder 侧回读（七项）

| # | 项 | 判据 |
|---|---|---|
| 1 | 租户无关性 lint | 零命中（`de_` / `dw_` / `kbd_` / `workspace_` / `lm_` / `team_` / `/kb/` / 租户名） |
| 2 | 五键定义 | `workers config get` 回读与写入定义一致 |
| 3 | 技能包扫描 | `skills scan` 的 `file_count` 等于上传数；记录 `packageSha256` |
| 4 | 头像与亮相图 | worker 对象两个 URL 非空，主机为 `pub.autostaff.cn` |
| 5 | 版本状态 | `listedVersionId` 指向本版；旧版 `superseded` |
| 6 | 秘密级别 | `secretLevel` 等于发布策略 |
| 7 | 升级计划 | `upgrade-plan.json` 逐实例一行；动作归租户，未执行 |

第 7 项是**计划**而非动作。Builder 发布不自动升级已雇实例，skill 不在租户侧执行升级。

## 五 · manifest

```json
{"schema_version": "meta-agent-manifest-09.20.1",
 "run_id": "...", "release": "09.20", "surface": "fde" | "builder",
 "started_at": "...", "finished_at": "...",
 "seat_count": 0, "created": 0, "reused": 0,
 "readback": {"pass": 0, "fail": 0, "rows": "readback.json"},
 "images": {"requested": 0, "approved": 0, "qa": "images/qa.json"},
 "directory_fallback": false,
 "config_completeness": 1.0,
 "blockers": []
}
```

`blockers` 非空即整批标未完成，但**已通过的席位不回滚**。部分成功是正常态：一席一体的失败域就是本席。
