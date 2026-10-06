# Skill 包布局（供 meta-skill 蒸馏）

本件描述两个 skill 包**应当含什么**。包本身未写，蒸馏属 C 级，等夏洛克拍板。

## 一 · 与 meta-skill 九步的对应

| meta-skill 步 | `fde-meta-agent` | `builder-agent` |
|---|---|---|
| ① 锁目标功能 + 选择环境 | 一席位规格 → 一团队私有员工；环境 = 团队管理 API | 一产品定义 → 一已发布版本；环境 = builder CLI |
| ② 切执行段 / 判断段 | 执行段：P0 P2 P6 P7 P8 P9；判断段：P1（规格是否可编）、P3（六段填法）、P5（面孔复用 / 生成） | 执行段：B0 B3 B4 B5 B6 B7；判断段：B1（lint 命中怎么处置）、B2（哪些内容下沉技能包） |
| ③ 判断段四相 → 三件套 | P1：判断标准 = 九键全有写路由 + 六维差异；触发钩子 = 规格加载完成；路由 = 拒编 / 进编 | B1：判断标准 = 零命中；钩子 = 定义就位；路由 = fail-closed / 进 B2 |
| ③ 执行段六槽 | 每步：动作 / 可达接口 / 依据 / 产出 / 值域 / 断言，取自 `spec §3.2` 表 | 取自 `spec §4.2` 表 |
| ④ 判据定位 | `contracts/outputs.md §三` 十六项 | `contracts/outputs.md §四` 七项 |
| ⑤ 补缺料推理 | 环境块运行时读取；探针失败的回退路径 | 五键 schema 服务端所有 → 先写后读验证 |
| ⑥ 编码 + 脚本 | 见 §二 | 见 §三 |
| ⑦ description 触发评估 | 见 §四 | 见 §四 |
| ⑧ 检验与回流 | 影子编制三席 → 差异判定 | dry-run 停在上架前 |
| ⑨ 聚合基准 | 十九席影子编制通过率 | 一次完整发布 + 一次复用 worker 的再发布 |

## 二 · `fde-meta-agent` 包

```
fde-meta-agent/
├── SKILL.md                      ≤500 行。入口：一席位规格路径 → 十步 → 回读表
├── assertions.json               十六项回读 + P1 拒编条件 + 图像闸条件（canonical）
├── references/
│   ├── 职能席.md                 ← streams/09-meta-agent/references/职能席.md
│   ├── 功能席.md                 ← 占位（未采用）
│   ├── seat-spec.md              ← contracts/seat-spec.md
│   ├── prompt-segments.md        ← contracts/prompt-segments.md（权威源）
│   ├── image-handoff.md          ← contracts/image-handoff.md
│   └── outputs.md                ← contracts/outputs.md
└── scripts/
    ├── probe_environment.py      P0：两接口探针 + 挂载技能可达性
    ├── check_seat_spec.py        P1：五块齐备 + 九键写路由
    ├── check_domain_differentiation.py  P1：六维差异机检
    ├── resolve_identities.py     P2：逻辑键 → 平台 id
    ├── compile_prompt.py         P3：六段编译，产出 effective-prompt.json
    ├── derive_bio.py             P4
    ├── build_image_request.py    P5：请求单；复用路径做字节比对
    ├── write_sequence.mjs        P6–P8：建体 → 九键 → 图像；每步 intent/response 落 evidence
    ├── readback.mjs              P9：十六项
    └── upload_assets.mjs         图像上传 + 像素哈希回读（承接 09.14 `upload-assets.mjs`）
```

`references/` 下四份契约在编译时从 `streams/09-meta-agent/contracts/` 复制，`SKILL.md` 头部记录每份的 `sha256`；`scripts/check_contract_hash.py` 断言相等，漂移即 skill 自检失败。

## 三 · `builder-agent` 包

```
builder-agent/
├── SKILL.md                      入口：一产品定义 → 七步 → 五键回读 + 上架状态
├── assertions.json               七项回读 + lint 条件
├── references/
│   ├── builder-product.md        ← streams/09-meta-agent/references/builder-product.md
│   ├── prompt-segments.md        引用 FDE 包的权威源，记 sha256，不复制正文
│   └── image-handoff.md          同上
└── scripts/
    ├── lint_tenant_free.py       B1
    ├── compile_prompt_builder.py B2：取 ①②④⑥，去实体
    ├── publish_sequence.sh       B3–B6：CLI 命令序列，每步 stdout 落 evidence
    ├── readback_builder.py       七项
    └── upgrade_plan.py           B7
```

## 四 · description 触发评估（⑦）

每个 skill ≥20 条正例 + near-miss。方向示例：

| skill | 正例方向 | near-miss（应不触发） |
|---|---|---|
| `fde-meta-agent` | 「按这份席位规格建一个数字员工」「重编 d_people」「给这席换头像并回读」「补 PATCH 回报目标」 | 「建一个工作区」「改团队的 KB 树」「看看某员工现在的配置」（只读，不编制）「批量重编十九席」（外层驱动的事，skill 应答「我一次一席，请循环调用」） |
| `builder-agent` | 「把这个技能包上架成市场产品」「发新版本并 public」「复用 bworker 再发一版」 | 「升级租户里的某个已雇实例」（租户侧）「写这个产品的 SKILL.md」（meta-skill 的事）「配一个团队私有员工」 |

near-miss 里两条最要紧：批量请求与技能包编写。前者划清 skill 与驱动的边界，后者划清 skill 与 meta-skill 的边界。

## 五 · assertions.json 骨架

```json
{"skill": "fde-meta-agent", "version": "09.20.1",
 "contract_hashes": {"prompt-segments.md": "...", "seat-spec.md": "...", "image-handoff.md": "...", "outputs.md": "..."},
 "reject_conditions": ["SPEC_INCOMPLETE", "DOMAIN_SEATS_UNDIFFERENTIATED", "NO_CARRIER_FOR_KEY", "ENVIRONMENT_UNREADABLE", "FACE_REUSE_UNVERIFIED", "IMAGE_NOT_REVIEWED", "COUNT_MISMATCH"],
 "readback": ["EMPLOYEE_MISSING", "PROMPT_DRIFT", "BIO_DRIFT", "TOOLKIT_DRIFT", "MODEL_DRIFT", "THINKING_DRIFT", "POLICY_DRIFT", "KB_READ_DRIFT", "KB_WRITE_DRIFT", "WORKSPACE_DRIFT", "REPORTING_DRIFT", "SKILL_DRIFT", "AVATAR_MISMATCH", "BIO_IMAGE_MISMATCH", "SKELETON_MISSING", "DIRECTORY_UNRESOLVED"],
 "accepted_fallbacks": ["DIRECTORY_FALLBACK"],
 "stage_entry": {"P0": "scripts/probe_environment.py", "...": "..."}}
```

失败码与 `contracts/outputs.md` 同名，二者不允许各自命名。
