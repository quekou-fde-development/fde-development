# eval workspace 数据结构（meta-skill 第 8-9 步 references）

被 `SKILL.md §第 8 步` `§第 9 步` 引用。定义 eval workspace 里所有 JSON 文件的**形状**——字段名、嵌套、取值。
本文件只管「数据长什么样」；「怎么评、阈值多少、pass^k 怎么算」是方法，在 `references/verification.md`，不在这里复写。
骨架取自 Anthropic skill-creator 2.0 schemas（来源见 verification.md §来源）；本系统两臂适配项标 `本系统加`。

JSON key 一律英文（机器读 + 与 Anthropic 工具对齐）；本文件说明用中文。

---

## 0 · eval_type — 贯穿所有 schema 的分叉（本系统加）

Anthropic 假设 skill 产出一个 artifact，用 assertion 给 artifact 打分。本系统的 skill 分两类，**每条 eval 必带 `eval_type`**，下游 grading / benchmark / viewer 全按它分流：

| eval_type | 适用 skill | 判什么 | 主指标 |
|---|---|---|---|
| `end_state` | 有真实终态产物（招投标决策、write-progress 类） | artifact 对不对 → assertion pass/fail | `pass_rate` |
| `route_convergence` | 不可逆 / DRY RUN / 无终态（dream、daily-review、week-sync 类） | 路由是否正确；另报同路由一致性 | `route_match_rate`；一致性另报 `convergence_rate` |

- 一个 workspace 内允许混装两类 eval（一份 skill 可能既有终态产物又有路由判断），逐条 eval 看自己的 `eval_type`。
- 凡下面字段标 `[A]` = 仅 end_state；`[B]` = 仅 route_convergence；无标 = 两类通用。

---

## 1 · 目录布局

将 eval workspace 放在 skill 包外。显式传 --root；缺省使用 META_SKILL_EVAL_ROOT 或当前目录下 eval-workspaces：

```
eval-workspaces/<目标skill名>/
├── evals\
│   └── evals.json                 任务集（带 eval_type）
├── history.json                   版本胜负账（Improve 模式，workspace 根）
├── trigger_eval\
│   ├── trigger_set.json           触发用例（should_trigger 数组，人手填）
│   ├── _split.json                最近一次 prepare 的兼容镜像；非版本权威源
│   ├── _judge_card.md             prepare 产出：给 agent 派判定 sub-agent 的现成卡
│   ├── judging/<version>/_prepared.json  该版本冻结快照；目录禁止覆盖
│   ├── judging/<version>/run*.json  各独立判定者写回的完整报告
│   └── result.json                score 产出（best_description + 各版本 train/test）
├── iteration-1\
│   ├── iteration_plan.json        冻结用例摘要、运行次数与完整目录集合
│   ├── eval-0-with_skill-run1\
│   │   ├── outputs\               执行产物（含 metrics.json）
│   │   ├── transcript.md          执行转写
│   │   ├── timing.json
│   │   └── grading.json
│   ├── eval-0-without_skill-run1\ 基线（同结构）
│   ├── ...                        run 目录名 = eval-{id}-{config}-run{N}，N 从 1 起
│   └── benchmark\
│       ├── benchmark.json
│       └── benchmark.md
├── iteration-2\                   Improve 模式重跑落这里
│   └── ...（含 comparison-N.json / analysis.json）
└── review\
    └── review.html                generate_review --static 产物
```

`<run-dir>` = 形如 `iteration-N/eval-K-with_skill/` 的单次执行目录。下面凡说"run 根""outputs"皆相对它。

---

## 2 · evals.json（`evals/evals.json`）

任务集。两类 eval 共表，逐条按 `eval_type` 带不同字段。

```json
{
  "skill_name": "dream",
  "evals": [
    {
      "id": 0,
      "eval_type": "end_state",
      "prompt": "用户任务 prompt（原样喂给执行 sub-agent）",
      "files": [],
      "expected_output": "期望产物的文字描述",
      "expectations": [
        "可客观验证的断言1（描述性命名见 eval_metadata）",
        "断言2"
      ]
    },
    {
      "id": 1,
      "eval_type": "route_convergence",
      "prompt": "触发该 skill 的任务 prompt",
      "files": [],
      "expected_route": "已知正确路由（reference solution：该走哪个分支 / 哪几步）",
      "reference_solution": "为什么这条路由对——判断依据，供 grader code-grade 路由结论",
      "dry_run": true
    }
  ]
}
```

- `files`：可选，任务附带的输入文件路径（招标文件、案例集等）。空数组 = 纯 prompt。
- `[A] expected_output` / `expectations[]`：assertion 在 eval_metadata.json 里展开成带名条目。
- `[B] expected_route` / `reference_solution`：路由层 reference，**不评说辞、不评 tool-call 序列**（见 verification.md §DRY-RUN 特化）。
- `[B] dry_run`：true = 令执行 sub-agent 声明动作不真做（skill 含改文件 / 建 cron / 删数据时必 true）。

## 3 · eval_metadata.json（`<run-dir>` 同级，每条 eval 一份）`[A]`

仅 end_state 用。把 evals.json 的 `expectations` 字符串展开成带名断言，供 grader 引用。

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "用户任务 prompt",
  "assertions": [
    { "name": "has-axis-labels", "text": "图表含坐标轴标签" }
  ]
}
```

route_convergence 不产此文件（它的 reference 在 evals.json 的 expected_route）。

---

## 4 · grading.json（`<run-dir>/grading.json`）

grader agent 产出（见 `agents/grader.md`）。**按 eval_type 分叉**。

### 4A · end_state 形态

```json
{
  "eval_type": "end_state",
  "expectations": [
    { "text": "断言原文", "passed": true, "evidence": "引用转写/产物里的证据" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 },
  "execution_metrics": {
    "tool_calls": { "Read": 5, "Write": 2, "Bash": 8 },
    "total_tool_calls": 15, "total_steps": 6, "errors_encountered": 0,
    "output_chars": 12450, "transcript_chars": 3200
  },
  "timing": { "executor_duration_seconds": 165.0, "grader_duration_seconds": 26.0, "total_duration_seconds": 191.0 },
  "claims": [ { "claim": "...", "type": "factual", "verified": true, "evidence": "..." } ],
  "user_notes_summary": { "uncertainties": [], "needs_review": [], "workarounds": [] },
  "eval_feedback": { "suggestions": [ { "assertion": "...", "reason": "..." } ], "overall": "..." }
}
```

- `expectations[]` 三字段 `text` / `passed` / `evidence` 名字固定不可改（viewer 依赖）。
- `claims[].type` ∈ `factual` / `process` / `quality`。
- `pass_rate` 取值 0.0–1.0。
- `eval_feedback`：grader 对断言本身的批评（断言太弱会通过劣质产物 → 假信心）。

### 4B · route_convergence 形态（本系统加）

```json
{
  "eval_type": "route_convergence",
  "route_result": {
    "expected_route": "evals.json 里的 reference",
    "actual_route": "本次 sub-agent 实走的分支",
    "route_match": true,
    "evidence": "转写里走该分支的证据原文",
    "stuck": []
  },
  "execution_metrics": { "...": "同 4A" },
  "timing": { "...": "同 4A" },
  "eval_feedback": { "suggestions": [], "overall": "..." }
}
```

- `route_match`：本路与 reference 是否一致（单路视角；3 路一致性在 benchmark 层算）。
- `stuck[]`：卡壳清单，每项 `{ "type": "a" | "b", "note": "..." }`——
  `a` = 顺指针读权威源仍判不动（→ 权威源待修）；`b` = skill 该说没说（→ skill 回第 1-3 步重拆）。见 verification.md §黑箱测·重档。
- 无 `expectations` / `summary` / `claims`（无 artifact 可断言）。

## 5 · metrics.json（`<run-dir>/outputs/metrics.json`）

执行 sub-agent 自留，grader 读入并拷进 grading.json 的 `execution_metrics`。

```json
{
  "tool_calls": { "Read": 5, "Write": 2 }, "total_tool_calls": 7,
  "total_steps": 4, "files_created": 2, "errors_encountered": 0,
  "output_chars": 12450, "transcript_chars": 3200
}
```

`output_chars` 当 token 代理量（无终态时仍可量转写规模）。

## 6 · timing.json（`<run-dir>/timing.json`）

```json
{
  "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3,
  "executor_start": "...", "executor_end": "...", "executor_duration_seconds": 165.0,
  "grader_start": "...", "grader_end": "...", "grader_duration_seconds": 26.0
}
```

执行一结束立刻写（`total_tokens` / `duration_ms` 只有此刻能拿到，过后丢失）。

---

## 7 · benchmark.json

读取 iteration_plan.json 冻结的 expected_runs、runs 和 evals_sha256；按该计划收齐 grading。metadata.status 取 COMPLETE 或 INCOMPLETE，缺件/坏件写 errors 并返回 rc=1。输入计划无效时失败并保留原有 benchmark。

在 run_summary.with_skill.by_eval_type 与 without_skill.by_eval_type 内分别存各类指标；delta 也按 eval_type 与 metric 分组。两类并存时 primary_metric=mixed，不计算混合总分。

| eval_type | 指标字段 | 取值 |
|---|---|---|
| end_state | pass_rate | 各 eval 的断言通过率多 run 均值，再跨 eval 平均 |
| route_convergence | route_match_rate | 各 eval 与 reference 匹配的 run 比例，再跨 eval 平均 |
| route_convergence | convergence_rate | 实际路由全部相同的 eval 比例；缺 actual_route 时为 null |
| 两类各自 | pass_k | k 次全部正确的 eval 比例 |

缺任一计划内 run 时，该配置该类型 complete=false，指标为 null。runs[] 保留每条计划项、实际结果或缺件错误。保留 k、expected_runs、valid_runs 与 evals_sha256 供回溯。

## 8 · comparison.json（`iteration-N/.../comparison-N.json`，Improve 模式）`[A]` 主用

comparator agent 盲评产出（见 `agents/comparator.md`）。A/B 双盲对比两版输出，不知谁是谁。

```json
{
  "winner": "A",
  "reasoning": "为何 A 胜 / 为何 tie，引具体处",
  "rubric": {
    "A": { "content": { "correctness": 5, "completeness": 5, "accuracy": 4 },
           "structure": { "organization": 4, "formatting": 5, "usability": 4 },
           "content_score": 4.7, "structure_score": 4.3, "overall_score": 9.0 },
    "B": { "...": "同结构" }
  },
  "output_quality": { "A": { "score": 9, "strengths": [], "weaknesses": [] }, "B": { "...": "" } },
  "expectation_results": {
    "A": { "passed": 4, "total": 5, "pass_rate": 0.8, "details": [ { "text": "...", "passed": true } ] },
    "B": { "...": "" }
  }
}
```

- `winner` ∈ `A` / `B` / `TIE`；rubric 各维 1–5，overall 缩放到 1–10。
- `expectation_results` 仅 end_state 有 expectations 时出，无则整字段删。
- `[B] route_convergence 适配`：无 artifact 质量可比 → comparator 比"两版的路由正确性 + 收敛稳定性 + 卡壳少否"，rubric 维度换成 `route_correctness` / `convergence_stability` / `stuck_count`（见 comparator.md route 分支），output_quality 仍给 1–10。

## 9 · analysis.json（`iteration-N/.../analysis.json`，Improve 模式）

analyzer agent 产出（见 `agents/analyzer.md`）。揭盲后追因：赢家为何赢、输家怎么改。

```json
{
  "comparison_summary": { "winner": "A", "winner_skill": "...", "loser_skill": "...", "comparator_reasoning": "..." },
  "winner_strengths": ["..."],
  "loser_weaknesses": ["..."],
  "instruction_following": { "winner": { "score": 9, "issues": [] }, "loser": { "score": 6, "issues": ["..."] } },
  "improvement_suggestions": [
    { "priority": "high", "category": "instructions", "suggestion": "...", "expected_impact": "..." }
  ],
  "transcript_insights": { "winner_execution_pattern": "...", "loser_execution_pattern": "..." }
}
```

- `priority` ∈ `high`（可能翻转本对比胜负）/ `medium` / `low`。
- `category` ∈ `instructions` / `tools` / `examples` / `error_handling` / `structure` / `references`。

## 10 · history.json（workspace 根，Improve 模式）

版本胜负账。每跑一轮 Improve 追加一条 iteration。

```json
{
  "started_at": "...", "skill_name": "dream", "current_best": "iteration-2",
  "iterations": [
    { "version": "iteration-1", "parent": null, "eval_type": "route_convergence",
      "primary_metric": "convergence_rate", "metric_value": 0.33,
      "grading_result": "baseline", "is_current_best": false },
    { "version": "iteration-2", "parent": "iteration-1",
      "primary_metric": "convergence_rate", "metric_value": 1.0,
      "grading_result": "won", "is_current_best": true }
  ]
}
```

- `grading_result` ∈ `baseline` / `won` / `lost` / `tie`（相对 parent 或 current_best，由 comparator 定）。
- `primary_metric` / `metric_value`：本系统加，让胜负账对两类 eval 都机器可读（Anthropic 原版只有 `expectation_pass_rate`）。
- `current_best` 由 test-score（非 train）择优，防过拟合。

---

## 11 · trigger 触发 eval 数据

### trigger_set.json

用数组保存每条 {id, query, should_trigger}。id 为唯一非负整数；省略时按原始序列生成。query 为非空字符串；should_trigger 必须为 JSON boolean。正式触发评测至少 20 条，覆盖正例与 near-miss；辅助管道夹具最少两条，以保持 train/test 不相交。

### judging/VERSION/_prepared.json

prepare 保存 schema_version=2、version、description、description_src、train_ids、test_ids、runs、seed、split、trigger_set_sha256、comparison_key、eval_fingerprint。根 _split.json 只镜像最近 prepare；score 始终读取所选版本的 _prepared.json。

comparison_key 绑定完整数据集、分区、seed 与 runs；eval_fingerprint 在其上绑定 version 与 description。准备后更改数据集或快照时重新 prepare 与独立判定；保存全部旧证据。

### judging/VERSION/runN.json

每份对象须含整数 run、与判定卡一致的 eval_fingerprint、verdicts 数组。每条 verdict 含整数 id 和 decision=TRIGGER/SKIP。

文件名集合必须恰为 run1.json 至 runN.json；内容 run 号逐份对应且为整数。每条用例恰有一份判定。缺件、多件、重复/未知/遗漏 id、坏 JSON、非法 decision 或 fingerprint 不符时返回非零，保留已有 result.json。独立性由原始派发记录证明。

### result.json

写 skill_name、original_description、best_description、best_version、best_test_score、runs_per_query、comparison_key、split、input_validation、evaluation_pass、method、iterations、updated_at。每条 iteration 保存 version、description、comparison_key、eval_fingerprint、train_score、test_score、train_failures、test_failures、validated_runs、scored_at。平票保留 fired=null、reason=TIE，并按未答对计分。

仅在当前 comparison_key 下选 best；保留其他数据集及旧格式历史但不让它们参与本轮排序。rc=0 与 input_validation=COMPLETE 只表示计分输入齐全且已完成。接受触发层前还要查失败清单及实际行为闸。将反复参与择优的 test_score 视为验证分数；泛化能力另用未参与选择的测试集。

版本目录一经 prepare 即冻结；再次 prepare 使用新的 version。best_* 仅在当前 comparison_key 内选优；current_version/current_evaluation_pass 表示最近一次评分，evaluation_pass 保留为其兼容别名。
