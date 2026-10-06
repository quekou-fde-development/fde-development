# 检验方法（meta-skill 第 8 步条件下沉配方）

## 四层验收

1. **Host layer**：宿主 frontmatter、目录与加载规则通过当前 host validator。
2. **Contract layer**：SKILL、assertions、stateful contract 与 fixture 声明闭合。
3. **Entry-binding layer**：每个机器段可从 canonical verification surface 单独调起并到达真实 handler；生产 router 不兼容时有薄 adapter。`assertions.json` 不能替代入口绑定。
4. **Behavior/recovery layer**：golden、定向 mutant、隔离真跑、故障注入、独立 readback 与黑箱均按适用面通过。

四层分别出 verdict。较高层的成功不覆盖较低层失败；未运行写 NOT_RUN。遇到 `argparse.set_defaults(function=...) → args.function(args)` 等生产 callback router 时，先判为 `production_router_needing_adapter`，生成 canonical adapter 后再跑 M8，禁止把 stage mismatch 解释成断言缺失。

## 安装后宿主实跑

四层验收通过只允许发布“候选可安装”。安装后另给 deployment verdict，并保存目标宿主、实际解释器、工作目录、环境、原样命令、stdout/stderr、退出码与产物回读。

- artifact skill：从已安装路径调用一次真实入口，核对真实输入、产物与人类汇报。
- scheduler / stateful skill：从排程或同一生产入口完成一笔获授权 canary / 真实事务；必须回读终态回执、commit、unlock 与 probe/游标的一致性。任一环未终态即 FAIL，等待中记 RUNNING，未执行记 NOT_RUN。
- 外部不可逆效果仍遵守 DRY RUN 安全边界；无法安全实跑时明确写“代码已安装，生产闭环未验证”，不得把 fixture、mock、静态检查或局部命令成功替代 deployment PASS。
- 宿主敏感检查必须固化唯一可移植命令并在目标解释器上真跑。只写“校验 UTF-8”“检查文件”等抽象动作不算可执行契约；候选不得临场改用未经验证的同名系统工具。

并行执行另验活性：首次进度和连续无进展均有明确上限；每个分片及时持久化；超时后只取消失联执行者并接管尚未完成分片；禁止再等一个完整窗口或重跑已完成工作。缺任一项，deployment verdict 不得为 PASS。

被 `SKILL.md §第 8 步` 引用。第 8 步前两道（机械闸 / 内部逻辑审）必跑、本体已内联 SKILL.md，不在此重复。按 skill 特征加载指针审与重档黑箱配方；修复本编译器时再执行随包工程回归。
正文只写「查什么 / 怎么查 / grader / 判据」，不解释为什么。黑箱骨架取自 Anthropic eval 指引（来源见文末），场景特化项标注。

## grader 三类（先判归属再选工具，能确定性就别上模型）

| grader | 工具 | 判什么 |
|---|---|---|
| Code | `validate.py` / `anchor_check.py` | 死的、确定的：字段、死链、指针存在性、阈值数值扫描 |
| LLM | 异于被测的模型当裁判，每维度独立，给 "Unknown" 出口防幻觉 | 语义：自洽、一致、命令式、路由对错 |
| Human | SME 抽检 | 校准 LLM 裁判、终裁；审慎用 |

LLM 裁判 rubric 要明确（"路由未走 reference 指定分支即 incorrect"）；让裁判先推理再打标签，然后丢弃推理只取标签。

## 指针审（第 8 步第三道下沉 · skill 有 references / scripts 才跑）

skill 引用了外部权威源时才有指针可审；纯 extract-mode 内联 skill 本道空过。逐项 pass/fail：

| 项 | 查什么 | 怎么查 | grader |
|---|---|---|---|
| 复制体 | 判据有权威源的家，却把本体内联进 skill | `anchor_check.py "<SKILL.md>" --inline` 列阈值数值候选 → 逐条查权威源有无家 → 有家而内联 = fail（改指针） | Code 筛 + Human 判 |
| 指针有效 | 引用的每个 §X 真实可达且确含所称判据 | `anchor_check.py "<SKILL.md>"` 解析每个 (文件,§) 对，到目标文件验标题存在 → DEAD/NOFILE = fail；AMBIG = 节名太泛、写到能唯一命中 | Code |
| 被引自洽 | skill 引到的权威源片段彼此不矛盾 | 只读被引片段；矛盾 = fail 且标"权威源待修"，不在审 skill 时改权威源 | LLM + Human |

边界（防 scope 爆炸）：只查被 skill 引用到的片段。发现权威源缺判据 / 不自洽 → 报告 + 标"权威源待修"，完整权威源自洽审计另起一轮。

## 人类裁决可用性

从该 skill 的三类终态各取一例：完成且无需行动、完成且需要裁决、未完成。若某类按设计不可达，记录 N/A 与路由证据。

把每例的最终用户可见文本单独交给未读过实现的独立判定者，隐藏日志、源码、内部术语表和主模型结论。判定者逐项回答：

- 已经发生了什么，目标是否完成；
- 当前影响和下一步是什么；
- 如需裁决，唯一问题、互斥选项与推荐项是什么；
- 批准、拒绝或暂缓分别会发生什么；
- 用户最短需要回复什么。

五项均可从文本直接作答才 PASS。标题或摘要依赖裸状态码、字段名、锁、哈希、receipt、stage、内部 verdict，或技术附件早于人类结论，均判 FAIL。术语即使技术上准确，只要判定者必须先翻译术语才能知道该做什么，也判 FAIL。

## 黑箱测·重档（第 8 步第四道下沉 · skill 高 stakes 才跑）

skill 判错担责 / 要求接近 100% 复现率（接第 1 步 `可接受复现率`）才触发本档；否则停在第 8 步内联的轻档 smoke。重档 = 收敛测（同任务 × 3 路 + pass^k + held-out 切分），主 agent 派 sub-agent 真跑、自己只裁断（不下场试跑）。

### 任务集构造

- 目标量：**10 起步 / 30 健康 / 50 上限**。实际量由判断段覆盖长出来（每判断段 ≥1 + 边界 case 骑墙信号/临界值/分支两侧），不硬凑、不为凑数编假任务。
- 每条标 `eval_type`：有终态产物 = end_state / 不可逆无终态 = route_convergence；每条配 reference solution（已知正确路由/产物），验任务可解 + 校 grader。
- 准入：两 SME 独立判 pass/fail 得同结论才算好任务。
- 平衡集：同放"该触发"与"不该触发"两侧，防单边优化。
- 某任务 0% 全挂，先疑任务坏，非 agent 无能。

### 测试集来源（高 stakes 但无测试集时的降级链）

skill 高 stakes、本该跑重档，但手上没有现成测试集时，按序走：

1. **有案例库 / 测试集 / 校准集** → 切 held-out：旧段做蒸馏 train、新段做测试 test（与第 7 步触发 eval 同一 60/40 切分机制，从 query 层搬到 case-corpus 层）。
2. **无测试集** → 问使用者：要你提供测试集，还是我去网上检索真实任务？
   - 使用者提供 → 用使用者给的。
   - 使用者无法提供 / 令检索 → 去网上检索真实任务，拿来当测试集跑。
3. 检索也补不够 10 个 → 标红"基于 N 例、统计置信低"，按现有量跑，不编假任务凑数。

（取测试数据问使用者 / 检索，是检验层取数，不违反第 1 步"蒸馏层不向用户追问判据"——层不同。）

### 跑法

- 搭 workspace + 备任务集：`python scripts/init_eval_workspace.py "<名>"` 起骨架 → 填 `evals/evals.json`（形状见 `references/schemas.md`）→ `python scripts/init_eval_workspace.py "<名>" --iteration 1 --runs 3` 摊 run 目录。
- 派 3 路独立 sub-agent：各 clean context、互不可见、不给主 agent 结论；产物落各 run `outputs/`、转写落 `transcript.md`。
- skill 含不可逆动作（改文件 / 建 cron / 删数据）→ `eval_type=route_convergence` 且令其 DRY RUN（声明动作不真做）。
- 主轮（必跑）：可读 skill 引用的权威源 → 测指针有效。
- 判据必要性轮（按需）：不读权威源 → 三档：读了才判对 = 指针有效判据该留 / 不读也判对 = 可能已被模型默认吸收、可议删 / 读了仍判不动 = 指针错或权威源缺判据。
- 派 grader sub-agent 评分（prompt 见 `agents/grader.md`）：逐 run 写 `grading.json`（end_state 评断言 / route_convergence 评路由 + 卡壳清单 (a)(b)）。
- 聚合：`python scripts/aggregate_benchmark.py "<ws>/iteration-1" --skill-name <名>` → benchmark.json/.md（end_state 主指标 pass_rate；路由正确性用 route_match_rate，同路由一致性另报 convergence_rate）。
- 生成人审 HTML：`python eval-viewer/generate_review.py "<ws>/iteration-1" --skill-name <名> --static <out.html>` → 交人审。

### 主 agent 裁断（不下场试跑，只据报告 + 人审反馈）

- 收敛判定：同判断段 3 路走同分支 = 收敛；用 pass^k（要一致性，非 pass@k）。
- 拿 reference solution 给路由/产物做 code grade，防 3 路集体滑到同一错。
- 分叉追因：卡壳 (a) → 权威源补判据（标"权威源待修"，非本流程改）；(b) → skill 回第 1-3 步重拆。
- 必读 transcript：分清是 skill 错，还是 grader 拒了合法解。

### pass^k vs pass@k

- pass@k = k 次至少 1 次对（随 k 升）；用于"一次成功就够"（如 coding）。
- pass_k = 同一任务 k 次全对的任务数 / 该类任务总数；使用实际运行结果。独立同分布假设下的 p**k 仅作模型估计，单列字段，不代替实测 pass_k。
- 本场景用 pass^k：skill 作协议，要稳定可复现，不是偶尔跑对。
- 环境隔离：每次试验 clean context，防共享 state 致相关性失败。

### 阈值

- 改进型 eval（skill 未上线）：起步可低通过率，留爬坡空间。
- 回归型 eval（skill 已上线）：须接近 100%，任何下滑即破坏信号。
- 不按字面信分数：必读 transcript 确认评分公平。
- 饱和：可解任务全过、无提升空间 = 饱和；capability eval 优化到高通过后可"毕业"成持续回归套件。

### DRY-RUN 与 stateful 恢复场景特化

不可逆 skill（动记忆池 / 建 cron / 删数据）对真实系统保持 DRY RUN；路由主指标使用 3 路收敛性与 reference code grade。workflow_mode=stateful 还须在一次性 fixture root + 模拟 effect adapter 上真跑状态机与故障注入；DRY RUN 只隔离真实外部效果，不能替代崩溃恢复、幂等、readback 与证据保留测试。评终态 / 路由，不按脆弱的工具调用字面序列评分。多组件任务用 partial credit。

## 脚本（索引 · 详细参数见各步就地引用）

- `scripts/validate.py "<skill 文件夹>"` — 机械闸 M1–M12；显式目标路径，使用本包随附的脚本。
- `scripts/anchor_check.py "<SKILL.md>" [--inline]` — 指针审：默认解析指针有效性；`--inline` 加复制体阈值数值候选扫描。
- `scripts/init_eval_workspace.py "<名>" [--iteration N] [--runs K]` — 搭 eval workspace 骨架 / 摊 run 目录。只建目录写空模板，不调模型。
- `scripts/run_trigger_eval.py prepare / score` — 第 7 步触发 eval（prepare 切分+判定卡 / score 多数票计分，均不调模型、无 subprocess/CLI 依赖）。
- `scripts/aggregate_benchmark.py "<ws>/iteration-N" --skill-name <名>` — 聚合 grading → benchmark.json/.md，指标按 eval_type 分流。
- `eval-viewer/generate_review.py "<ws>/iteration-N" --skill-name <名> --static <out>` — 人审 HTML（静态态，单机不守 server）；`--trigger` 切触发 eval 复核模式。
- agent prompt：`agents/grader.md`（评分）/ `agents/comparator.md`（盲评，第 9 步）/ `agents/analyzer.md`（追因，第 9 步）。
- eval workspace 数据形状全在 `references/schemas.md`。

## 随包工程回归

从包根执行以下命令；run-dir 选择包外尚不存在的目录，保存 stdout、stderr、退出码及生成的 result.json。

```bash
python3 scripts/regression.py --run-dir ../meta-regression-01
python3 scripts/full_matrix.py --run-dir ../meta-matrix-01
python3 scripts/validate.py . --persistent
```

另运行当前宿主 system skill-creator 的 quick validator。其运行依赖缺失或未执行时记录 NOT_RUN；不得用本包自检替代宿主格式验收。

- 用工程回归验证未知 stage、真实文件回执、判定完整性、版本冻结、YAML、路径、HTML 与分类聚合。
- 由 `references/mechanical/` 的随包生成器生成正负例，再运行 18 臂矩阵。只将全部指定退出码一致计为 PASS；`--prepare-only` 只生成输入。
- 更改审核器或 sandbox 后，使用系统 Python 和实际执行端 Python 分别实跑；报告解释器路径和平台。将各解释器的证据放在不同目录。
- 运行 `scripts/build_self_fixtures.py --output ../meta-fixtures-01` 可重建自检材料。只将 receipts、stage_outputs、run_manifest 和定向 mutant 装入包，保留 mutable workspace 在本轮证据目录。fixture:// 路径表示可移植确定性夹具；内容规范化后重新按实际文件计算 hash。
- 将回归代码、生成器、registry、golden 与 mutant 随安装包交付；在另一目录解包复验并保存安装后日志。
- 单列 deterministic_fixture、独立触发判定、实际竞争路由、业务黑箱与弱模型臂。机械 PASS 只覆盖已运行的工程不变量；未跑的能力层标为 NOT_RUN。

## M8–M10 运行隔离

- 在 macOS 使用 sandbox-exec：禁止网络、包外写入、用户目录及临时目录读取；只额外放行探针根、所选 Python 的 base_prefix 与精确可执行文件。系统默认可读区域仍受平台 profile 约束。
- 将 bundled Python 放行范围限制到该解释器运行树；拒绝根目录、/Users 或用户 home 级白名单。
- stage runner 禁止 fork；audit 包装可在同一 OS 沙箱内启动子进程。限制执行时间与输出资源，核查探针输入哈希与写入范围。
- 在 Linux 使用 bubblewrap 与 seccomp；无可用可靠隔离后端时 fail-closed。只报告实际运行平台的结果。
- 用自己创建的无敏感内容 sentinel 检验包外读取、写入、子进程和退出后的残留行为；不得将实际私有文件用作探针。

## 来源

Anthropic 官方 eval 方法学（2026 口径）：
- 《Demystifying evals for AI agents》— anthropic.com/engineering/demystifying-evals-for-ai-agents（构集 / grading / pass@k vs pass^k / 评终态 / 阈值）
- 《Define success criteria and build evaluations》— platform.claude.com/docs（SMART 标准 / edge case / LLM rubric）
- 《Building evals》Cookbook — platform.claude.com/cookbook（grader 代码模板 + 裁判 prompt 结构）
- 《Improving skill-creator: Test, measure, refine》— claude.com/blog（benchmark 三指标 / Comparator 盲评 A/B / "base 模型也过 = skill 可退役"信号）

场景特化（本系统加，非 Anthropic）：路由收敛性主指标（因 DRY RUN 无终态）/ 读不读权威源筛判据必要性 / 卡壳 (a)(b) 分类 / 3 路对齐记忆系统三路独立蒸馏 / 轻档 smoke 地板 + 重档收敛条件触发 / 测试集来源降级链（问使用者→检索）/ 10-30-50 量纲。
