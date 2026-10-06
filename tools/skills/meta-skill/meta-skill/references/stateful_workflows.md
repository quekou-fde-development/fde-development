# 有副作用工作流契约

本文件约束持久 Skill 中跨进程状态、外部副作用、排程补跑与崩溃恢复。operation 描述“数据如何变换”；本契约描述“动作执行到一半后如何安全继续”。两轴同时成立。

## 1 · 双轴分类

每个编译目标在 frontmatter `metadata.workflow_mode` 写一个值：

- `artifact`：全部效果限于显式 run-dir 内可重建产物；重复运行不会改变共享或外部状态。
- `stateful`：写共享状态、调用外部可变系统、持有跨进程锁、创建排程、补跑历史事务，或一次中断会影响下次执行。

任一动作命中 stateful 条件，整包按 stateful 验收。`handoff` 只表示执行者在流程外，不能替代效果声明和恢复契约。

每张执行段卡另写一行 `副作用：<scope>`；scope 只允许 `run_dir_only`、`shared_state`、`external_system`、`scheduler`、`lock`。artifact 包的所有卡必须为 `run_dir_only`；任一其它值将整包提升为 stateful。结构化声明用于完整枚举，动作文本的副作用信号用于抓声明与语义冲突；词表命中不是自然语言完备证明，独立黑箱仍须核查错标。

## 2 · stateful_contract schema

stateful 包根必须有 `stateful_contract.json`。顶层字段：

```json
{
  "stateful_contract_version": "1.0",
  "logical_target_key": "稳定标识逻辑目标的字段",
  "evidence_revision_key": "同一逻辑目标下输入证据版本的字段",
  "attempt_key": "每次执行尝试唯一的字段",
  "fence_key": "每次成功取得/接管租约后单调变化的字段",
  "states": ["..."],
  "terminal_states": ["..."],
  "effect_boundaries": [],
  "production_entrypoints": [],
  "recovery": {},
  "durability": {},
  "tests": {}
}
```

`logical_target_key`、`evidence_revision_key`、`attempt_key`、`fence_key` 必须四者分离。它们依次回答“哪一个业务目标”“用哪版证据推导”“哪一次实际执行”“当前谁仍有写权”。逻辑日期、输入 hash、线程/排程 id 与租约 generation 不得互相冒充。

每个 `effect_boundaries[]` 条目必须含：

| 字段 | 判据 |
|---|---|
| `id` | 包内唯一 |
| `action` | 明确外部或共享状态动作 |
| `authority` | 谁授权、谁拥有该状态 |
| `precondition` | 执行前可重读的状态与版本条件 |
| `idempotency_key` | 稳定去重键；同一业务效果重试时不变 |
| `checkpoint_before` | effect 前先持久化的 intent/checkpoint |
| `receipt_after` | effect 成功后持久化的回执及外部 operation id |
| `readback` | 通过独立读接口确认外部最终状态 |
| `unknown_state` | 固定为 `halt_and_reconcile` |
| `retry_rule` | 固定为 `reconcile_before_retry` |
| `compensation` | 可逆补偿，或明确 `manual_verdict` |
| `implementation_symbols` | 唯一的 `path.py::symbol` 数组；所有 boundary 合集与 production bindings 精确相等 |

`recovery` 必须含 `lock_owner_identity`、`fencing_rule`、`stale_lock_rule`、`resume_selector`、`no_progress_rule`、`commit_rule`、`unlock_rule`。`resume_selector` 必须能选中最早未终态事务；已有 attempt receipt 不能永久阻止 reconcile 或新 attempt。

`no_progress_rule` 对所有并行执行者必须逐项给出：首次持久化进度期限、连续无新产物期限、协调者最多等待轮数、分片级 checkpoint、取消接口、remaining-only fallback 与 fallback 失败终态。恢复只能接管未完成分片；已回执分片不得重放。只有“定期检查”“超时重试”或没有数字上限的描述视为缺失。

`durability` 必须含 `journal`、`commit_receipt`、`evidence_retention`。COMMITTED 回执的存活期不得长于验证它所需证据；证据缺失时进入 reconcile 或人工裁断，不得仅凭终态标记宣告成功。

`production_entrypoints[]` 逐一登记每张非 `run_dir_only` 执行卡的真实 `可达接口`。每项含入口 `path`、全量 `sha256`、`symbol` 与唯一 `kernel` 引用；SKILL.md 里的 `path.py::symbol` 集合须与该数组精确相等。每个入口文件必须 import-safe，公共函数精确等于已登记 symbol，不得含未登记 callback、`main` / `__main__` 或模块级执行路径。每个入口的前五个参数固定为 `logical_target, evidence_revision, attempt_id, fence_token, adapter`，并把同一组名字传入 kernel；入口、本文件 helper 及递归可达的包内 imported helper 都不得另开 subprocess、网络、数据库或文件 mutation 路径。动态 import、反射取函数与间接 callee 在该闭包内 fail-closed。验证器同时用跨模块 AST 闭包与隔离动态 trace 证明真实入口进入 kernel。

`tests` 必须含相对路径 `runner`、`fault_points[]`、`scenarios[]`、`implementation_bindings[]` 与 `trusted_entrypoint`。状态事务只暴露一个公共 transaction kernel；support/helper 使用私有名。每个 effect boundary 的 `implementation_symbols` 都只指向该 kernel，生产 CLI handler 经它 dispatch。实现绑定声明 kernel 的 `path`、完整 `sha256` 与唯一 `symbol`；路径不得位于 `tests/`、`fixtures/` 或指向 runner 自身。`trusted_entrypoint` 必须就是该 kernel，其前七个参数固定为 `logical_target, evidence_revision, attempt_id, fence_token, adapter, fault_point, run_dir`，其中后两项可给默认值；函数体直接调用注入 adapter 的 `intent/effect/receipt/readback/commit/unlock` 六方法。kernel 与其递归可达 private/imported helper 采用封闭调用面：effect 只能经注入 adapter；直接文件、进程、网络、数据库调用、动态/高阶 callable 与未登记对象方法均 fail-closed。runner 只在一次性 fixture root 和模拟 effect adapter 上运行，禁止触碰真实外部系统。

runner 的固定接口为：

```text
python <runner> --contract <stateful_contract.json> --run-dir <一次性目录> --json
```

成功时须同时向 stdout 和 `<run-dir>/stateful_test_report.json` 写同一份 JSON。报告必须绑定 contract 全量 SHA-256，逐项覆盖 contract 声明的全部 fault point / scenario / effect boundary。每项 `evidence` 是 run-dir 内 JSON 的相对 `path` + 全量 `sha256`，验证器独立重读：成功事务须严格遵循 `INTENT→READBACK(initial)→[EFFECT]→RECEIPT→READBACK(final)→COMMIT→UNLOCK`；fault evidence 的 `effect_count` 必须是 0 或 1，boundary evidence 必须含一次且仅一次 EFFECT。未知外部状态、陈旧锁、积压重试、证据缺失及跨目标隔离另验各自终态字段。`implementation_bindings` 必须与 contract 完全相同。

production binding 只能暴露上述唯一 kernel；同文件其它函数须为私有 helper。可信 harness 独立记录实际进入过的 kernel，并使用验证器拥有的 effect adapter 对 kernel 及每条 `production_entrypoint` 分别执行四个崩溃点的崩溃→恢复、UNKNOWN、证据缺失与重复尝试：adapter 掌握逐次 INTENT/EFFECT/RECEIPT/READBACK/COMMIT/UNLOCK 轨迹、外部 effect applied 集与实际 `effect_calls` 计数。每条真实入口都须在故障注入下动态进入同一 kernel，逐 attempt 满足严格时序，跨恢复的 `effect_calls` 必须精确等于 1；集合去重后的 applied 数量不能替代调用次数。候选 runner 只承担结构化报告与可重读证据格式检查；它写出的 PASS/evidence 不能生成恢复 verdict。声明、静态 import/call、入口级故障注入、boundary 映射、可重读故障证据与可信 adapter 全部成立才通过。

## 3 · 恢复验收

故障注入至少覆盖：

- `after_intent_before_effect`
- `after_effect_before_receipt`
- `after_receipt_before_commit`
- `during_unlock`

场景至少覆盖：

- `duplicate_attempt`
- `unknown_external_state`
- `stale_lock`
- `backlog_retry`
- `evidence_missing`
- `cross_target_isolation`

每个场景验四项：共享/外部效果至多一次；attempt owner 与 logical target 不串用；未知外部状态停在 reconcile；终态回执能由保留证据独立重验。积压选择器还须证明一个失败日期不会因“已有尝试记录”永久失去调度资格，并提供有限的 no-progress 状态与人工出口。

结构闸只证明声明齐全。测试 runner、真实实现、故障注入和独立黑箱共同构成行为证据；其中任一未跑即标 NOT_RUN。validator 会在 OS sandbox 内真跑 runner、冻结包输入、核对可信调用轨迹与双份报告；无隔离后端时 fail-closed。

stateful 生产 runner 常用 subcommand/callback 路由。先按 `contract_ir.md §6.2` 建 canonical verification adapter，再让 fault runner 通过该 adapter 或真实公开 API 驱动实现；禁止在测试 runner 内重写一份平行状态机。若 adapter 无法到达真实 effect journal、lock/fence 或 readback 实现，行为层保持 NOT_RUN。
