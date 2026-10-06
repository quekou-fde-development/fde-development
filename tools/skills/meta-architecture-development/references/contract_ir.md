# contract IR · 执行段机械契约中间表示

本文件是执行段机械覆盖的**唯一判据源**。第 3 步按此填槽，第 6 步按此生成 canonical contract，第 8 步机械闸按此验，运行期 `scripts/audit.py` 按此判 PASS/FAIL。

**消费者三方，各取所需，不得各写一份**：编译期（第 3/6 步填槽与生成）、机械闸（`validate.py` 验覆盖）、运行期（`audit.py` 执行断言）。三方读同一张表；任何一方内联复制本表内容 = 造第二权威源，第 8 步指针审按复制体判 fail。

---

## 1 · 为什么按 operation 而非按字段类型

断言强度不由编译者手填「强 / 中 / 弱」再自证——手填即自证，自证不构成检验。也不由产物字段类型推断（「有数值字段就要求守恒」）：数值字段之间未必存在守恒关系（停留天数、超时率、耗时之间无守恒），按字段类型硬映射会制造假断言，把机械闸变成噪声源。

判据落在**这一段对数据做了什么**——即 operation。operation 决定输入与输出之间存在哪些恒等关系，恒等关系决定最低强断言族。这条链上每一环都机械可判：operation 是否在封闭词汇表内（枚举比对）、最低谓词族是否全覆盖（集合包含）、定向 mutant 是否被拒（跑一次，看退出码）。

---

## 2 · operation 封闭词汇表（8 类）

每个执行段的每个动作标恰好一个 operation。标不出 = 该段未拆到位，回第 2 步重切；标 `custom` 见 §5。

| operation | 语义 | 判别问句 |
|---|---|---|
| `acquire` | 从外部源取数进本流程 | 数据此前不在流程内？ |
| `filter` | 按谓词删子集，保留项不变形 | 出集 ⊆ 入集，且未改任何字段？ |
| `map` | 逐元素变形，元素个数不变 | 一进一出，键不变？ |
| `join` | 按键合并两个及以上集合 | 有两个来源、按键对齐？ |
| `partition` | 按规则把入集分到互斥的桶 | 每个元素恰好落一个桶？ |
| `aggregate` | 由明细算出汇总量 | 出的是计数 / 合计 / 分布？ |
| `render` | 把结构化数据写成交付格式 | 出的是给人或给下游系统的成品件？ |
| `handoff` | 交接给流程外的执行者（人 / GUI / 他系统）并接回产物 | 这一步本流程内的脚本做不了？ |

**切分粒度**：operation 标在 contract boundary 上，不要求一段一文件。一个 runner 可用 stage 参数覆盖多段；但一个 stage 内混多个 operation 时，每个 operation 各自登记断言，不合并。

---

## 3 · 最低强断言族（强制下限，不是上限）

登记该 operation 即必须全覆盖对应族；缺一条 = 第 8 步机械闸 fail。可以多写，不可以少写。

| operation | 最低强断言族 | 各条挡住什么 |
|---|---|---|
| `acquire` | `source receipt`（源标识 + 取数时刻 + 定位参数）<br>`schema conformance`（字段集与类型符声明）<br>`count/hash`（行数与内容指纹落账） | 源取错 / 结构漂 / 静默截断 |
| `filter` | `output subset input`（`output ⊆ input`，出集是入集子集）<br>`predicate replay`（逐元素重跑谓词，与保留决定比对）<br>`excluded count/set`（被删项计数与清单落账） | 凭空多出 / 谓词坏死 / 静默丢单 |
| `map` | `key/row preservation`（键集与行数不变）<br>`field-function replay`（逐元素重算变形函数，与产物比对） | 元素丢失或增生 / 变形函数错 |
| `join` | `key coverage`（连接键在两侧的覆盖率落账）<br>`cardinality`（一对一 / 一对多基数符声明）<br>`unmatched set`（两侧未匹配项清单落账，且与已连接键不相交、且与按键重算的应未匹配集逐项相等）<br>**`joined value replay`**（逐键回右表查值，与产物落的取值比对） | 连接键错配 / 笛卡儿爆炸 / 未匹配项被静默吞掉 / **已匹配项被谎报未匹配** / **键连对了但取值取错** |
| `partition` | `union completeness`（各桶并集 = 入集）<br>`pairwise disjoint`（桶间两两不交）<br>**`assignment rule replay`**（逐元素按声明的分桶函数重算，与账本裁决值比对） | 漏桶 / 重计 / **分桶规则应用错** |
| `aggregate` | `detail recomputation`（由明细重算汇总）<br>`total reconciliation`（汇总与上游总量对账）<br>**`each-bucket independently enumerable`**（每个桶有独立可追踪成员清单） | 汇总算错 / 与上游脱节 / **某桶由减法得出** |
| `render` | `row/column/sheet reconciliation`（成品件行列表数与数据源对账）<br>`summary reconciliation`（成品件内统计与明细对账）<br>**`output field coverage`**（成品件每个输出字段都被某条断言碰过，留白须逐条写豁免理由） | 出表丢行丢列 / 表内统计与明细打架 / **成品件自报字段无人审，改之无声** |
| `handoff` | `artifact hash`（交接物指纹）<br>`schema conformance`（交接物结构符声明）<br>`receiver receipt`（接收方或下一段的接收回执） | 交接物被换 / 结构不符 / 交接未闭合 |

### 3.1 两条加粗项的来源

`partition` 的 `assignment rule replay` 与 `aggregate` 的 `each-bucket independently enumerable` 是 2026-08-06 错误注入实测的直接产物，不是推演补全：

- 无 `assignment rule replay` 时，注入 E2（时效分组日界错，单 0003 由 t2 误划入当日组；复现 08-05 TODAY_START 差 18h40m 真 bug）——并集仍完整、各桶仍互斥，前两条断言全绿放行。检出它靠的是逐元素重算分桶函数与账本裁决值比对。同族放行的还有 E1 / E4 / E6 / E8。
- 无 `each-bucket independently enumerable` 时，注入 E9（正常桶 = 总数 − 其余六类反推，无逐单清单）——守恒式恒真且不可追踪，前两条断言全绿放行。

`filter` 的 `predicate replay` 与 `map` 的 `field-function replay` 是同一防线在各自 operation 上的形态。三者共享同一机制：**产物的守恒性质与产物的规则应用正确性正交，守恒断言不蕴含规则断言。**

---

## 4 · 总禁则 · 守恒式反解

**任何值由守恒式反解得出时，该守恒式不得充当检验。**

判别：某个字段的值是由「总量减去其余各项」「差额倒推」「相减配平」得出的，则包含该字段的守恒断言恒真，对该字段零约束。此时该守恒断言登记无效，必须另有独立来源的断言覆盖该字段。

机械判定：`assertions.json` 中每条断言登记 `derived_fields`（本断言涉及的、由反解得出的字段）。字段出现在 `derived_fields` 里，则该断言不计入最低谓词族覆盖。每个字段必须至少被一条 `derived_fields` 不含它的断言覆盖。

此禁则跨全部 operation 生效，不限于 `aggregate`。诊断源：2026-08-05 双包实测——两套取数各坏在不同处，两边的守恒校验只验分桶数之和 = 输入数，对输入是否正确零约束。

---

## 5 · custom operation

词汇表外一律登记 `custom`，**默认 FAIL**。启用须三条件全在位，缺一即拒：

1. **独立 golden**：一份已知正确的输入输出对，该断言必须 PASS。
2. **定向 mutant**：一份按本 operation 特征构造的错误样本，该断言必须 FAIL。只 PASS 不 FAIL 的断言不构成检验。
3. **来源锚**：断言依据出自哪条判据 / 哪份权威源，写明文件 §节。

三条件在位后，`custom` 才计入覆盖。新 operation 反复出现 → 提请扩词汇表，不长期挂 `custom`。

---

## 6 · canonical contract schema

默认文件为包根 `assertions.json`。若包内已有同名原生回归件或布局受限，编译期与运行期可同时显式传 `--contract <包内相对路径>` 选择另一份 canonical contract；显式路径解析后必须仍在包根内，`scripts/audit.py` 必须注册并消费同一参数。不得自动扫描包根、`fixtures/` 等多位置：同名多方言会令选料依赖搜索顺序。

原生回归方言（例如顶层 `{assertions: [...]}`）可与本契约共存，只继续服务它自己的审核器；缺 `contract_ir_version: "1.0"` 或 `stages[].operations[].assertions[]` 时不计作 canonical contract。默认件或显式件缺失、不可读、JSON / 方言不合时，M8 FAIL，M9/M10 记 `NOT_RUN (FAIL-CLOSED)`，不得形成覆盖或证伪结论；canonical contract 成功加载后的 operation、family、tier、mutant 缺口才分别记 M9/M10 FAIL。

```json
{
  "package": "<skill 名>",
  "contract_ir_version": "1.0",
  "stages": [
    {
      "stage": "<段标识>",
      "operations": [
        {
          "op": "partition",
          "artifact": "<本 operation 产物的相对路径>",
          "source_reachability": "machine | human_handoff",
          "assertions": [
            {
              "id": "<稳定唯一标识>",
              "family": "assignment_rule_replay",
              "tier": 1,
              "predicate": "<解释器可执行的谓词声明>",
              "derived_fields": [],
              "source_anchor": "<判据出处：文件 §节>",
              "mutants": ["<必须被本断言拒绝的 mutant id>"]
            }
          ]
        }
      ]
    }
  ]
}
```

**字段硬约束**：

- `stages[].stage` 在包内非空且唯一；全部 `assertions[].id` 在包内非空且全局唯一。
  唯一性须在转成 set / dict 之前验证：重复键会被集合吞掉或被映射覆盖，表面闭包与
  逐条结果仍可全绿，而其中一份声明已失去身份。
- `family` 取值须在 §3 表内（或 `custom_*`，走 §5）。
- `tier`：`0` = 终态可审面（不读账本）/ `1` = 段级账本内断言（不读源）/ `2` = 源重读比对（读源）。
- `source_reachability` = `human_handoff` 时，本 operation 的 tier 2 断言登记为 `UNVERIFIED`，不得省略、不得改判 PASS。
- `mutants` 为空 = 该断言未经证伪，机械闸 fail（`tier 0` 除外——终态守恒断言以 golden 对照背书）。
- **上游引用按 (段, 产物) 双键寻址**：谓词里的 `input`／`compare_map.input`／`compare_paths[].input`
  指向某段产物时，
  若该段在契约里挂了两个及以上 operation，必须同时给 `artifact`。只给段名时解释器
  **拒绝求值**（该断言 FAIL），不得代为选定第一份产物——一段两份产物、只说段名，
  指的是哪一份无从确定；替它选一份等于让断言跑在没指定的东西上，与产物按段覆盖是同一个错。
  段恰好挂一个 operation 时可省略 `artifact`。歧义按**契约声明**的 operation 数判，
  不按 run 目录里已落盘的产物数判——第二份没落盘时引用照样歧义。

### 6.1 `row_column_sheet_reconciliation` 的三种口径

同族三种谓词形状，按「要钉住什么」选，**同一条断言只许一种**（并存则解释器拒绝求值——判据取哪个由实现顺序决定，那就不是判据）：

| 谓词键 | 比什么 | 用在 |
|---|---|---|
| `rendered_rows` | 行数 / 标量与上游总量相等 | 成品件自报总量是否出自上游，而非渲染时另算 |
| `compare_map` | 单路径整块相等 | 一整个字典或清单原样落地 |
| `compare_paths` | **多条直连路径逐路径精确相等** | 成品件多个字段各自直连上游的某个路径 |

`compare_paths` 每项须**同时**显式声明两端——`{"output": <成品件路径>, "input": {"stage","path"}}`。三条硬约束：

- **两端都显式**。只给一端让解释器按同名去对侧找，是把对应关系交给命名巧合：`lists_public.<桶>` 与 `lists.<桶>` 本就不同名，上游某个桶改名时同名推断会安静地配错一对，两边照样各自存在、比对照样"成立"。
- **精确相等，不是计数相等**。清单成员换成一个等长的错值时，长度与计数一动不动，按 `len` 比的口径在这一形态上恒真——清单长度相等不约束成员是谁。
- **空表判 FAIL**。`compare_paths: []` 逐项遍历零次、返回真，是一条恒真断言；恒真断言登记在册比不登记更坏，它占着覆盖名额且永远绿。

**直连只证明「没在渲染时另算」，不证明「这个数对」**：两端同改则直连恒等成立。链首那一端须另有断言钉到真实上游（OAQ 里 `final.claimed_total_match_source` 把 `N_claimed` 对到 s2 段实际保留行数，与直连的 `N_claimed → s8_summary.N_claimed` 各挡一侧）。诊断源：`M25-claimed-total-chain-drift`——只做直连时，把总量沿链一起改写全绿。

`output_field_coverage` 由解释器**强制排在同 operation 全部其余断言之后**求值，与它在契约里登记的位置无关：它要的是其余断言**实际读过**哪些路径。覆盖证据只取求值时记录的读取路径，不取谓词字面量——往兄弟断言里塞 `"note": "<字段名>"` 就能让字段名"出现过"，而没有任何代码读它，与 §8 已拒的诱饵字面量同类。

### 6.2 段入口绑定（M8 逐段判据）

契约的链形是「本段落盘 → 立刻跑本段断言 → 过了再进下一段」（§8 链形）。一个 runner 从头跑到尾、中途无处切入，这条链就只剩首尾两点，中间段的断言全部退化成事后追认：错在第二段、第四段才发现，而那时前三段的产物已经互相污染。故每个含非 `handoff` operation 的段，须有一个能**单独调起它**的入口。

两种合法形态，二选一，**无第三条兜底**：

| 形态 | 要求 |
|---|---|
| 专用脚本 | 文件名恰为 `run_<段名>.py`，AST 里真注册 `--run-dir` |
| 共用 runner | AST 里真注册 `--stage` 与 `--run-dir`，且有一个被段选择器**实际索引并调用**的显式字典 dispatch，键含该段名 |

这两种是 canonical verification surface，不要求生产 CLI 改成同一种用户界面。若生产入口使用 `argparse.add_parser(...).set_defaults(function=handler)` 后由 `args.function(args)` 调用，或使用 if/elif 路由，它属于 `production_router_needing_adapter`：必须另建薄 adapter 暴露上述 canonical surface，并从 adapter 可达真实 handler/API。只新增 `assertions.json` 不会让这类入口获得 M8 绑定；adapter 及其递归可达的包内 imported helper 复制、覆写生产实现同样不合格，动态 import/reflection 在薄 adapter 闭包内 fail-closed。

包内检出 production callback router 时，根目录必须有 `runner_binding.json`。每个 canonical stage 登记唯一 adapter、真实 `production_path`、该文件完整 SHA-256 与调用机制；绑定 callback router 时还须列 `production_commands[]`，`symbols[]` 必须精确等于这些 command 在真实 topology 中登记的 handler 集，任意 helper 不能替代。`runpy` 绑定须从本 stage handler 可达 `runpy.run_path(<生产文件>)` 及全部 command；`module_call` 绑定的 import/call 须位于本 stage handler 可达路径。stage 与 production command 同名时采用一对一 `module_call` 薄委派：adapter 自身不得写业务产物，真实 handler 必须直接接收调用方 run-dir。只在常量、注释、死分支中出现路径或 symbol 不算绑定。该清单区分参数归一后的真实委派、象征性 healthcheck 与复制实现。

两种形态都再验产物。**检出主闸是隔离真跑**：在中性包副本中，以 golden 目录预置
运行输入、删除 `run_manifest.json` 与本段声明的 `artifact`，随后移除包内整个
`fixtures/` 验收料目录，再单独调起该 stage。runner 不得读取 golden/mutant 标准答案，
也不得改写或删除预置的其他 stage 输入；退出码须为 0，且全部目标产物须以非 symlink、
非空普通文件重新落到 `run-dir`，`.json` 产物还须可解析。

文件存在与 JSON 可解析仍不足以背书。runner 退出后，验证器才把 canonical contract、
通用断言解释器与 IR 从可信原件复制进探针，在同一 OS sandbox 内只对本段做一次可信重放；
本段 T0/T1 断言须逐条、身份闭合地返回 PASS。若包有唯一 `fixtures/source*.md`，该源件同样
在 runner 退出后才进入可信区，本段 T2 也须 PASS；无独立源件时 T2 只能如实保留
UNVERIFIED，不得借它放行 T0/T1。包内 `scripts/audit.py` 不参与这次 stage 产物背书，
避免候选 runner 与候选 auditor 共因。

macOS 用 `sandbox-exec`；Linux 用
bubblewrap 建空 mount/PID/network namespace，只读挂载解释器与动态链接运行时，并在 runner
进程内装 seccomp，拒绝 fork/exec、网络与 signal syscall。两端都禁止探针根外写入和读取
用户目录/卷/主机临时区；环境变量最小化，30 秒超时，并限制 CPU、单文件大小、打开文件数与
进程数。多脚本 runner 的 helper 须在同一进程内 import/runpy 调用。可靠隔离后端、Linux
架构 syscall 表或安全系统 Python 任一缺失时 fail-closed，不得降级为 `ro-bind / /` 或裸跑。

静态可达性退为归因层：从该 stage 实际 dispatch 到的 handler 沿本地调用链判断写盘，
用于解释死函数、常量假分支或 `return` / `raise` 后的不可达语句。隔离真跑成功时，
静态未知或误判不得阻断；隔离真跑未落盘时，静态能定位则给出具体机制，不能定位则
报告运行成功但缺产物、运行失败或隔离器不可用。
常量假分支按静态语义判定，不限于字面量 AST：至少沿模块级与函数内简单绑定跟四跳，
并识别 `not <常量>` 与 `and/or` 必然短路；`enabled=False; if enabled:`、
`if not True:`、`if run_dir and False:` 均属不可达。静态求值只覆盖无副作用的小子集，
本层不得执行被审包代码来换取归因结论；表达式枚举边界由上面的隔离真跑兜底。参数与
局部绑定会遮蔽同名模块常量；解构赋值、
import、函数/类定义及复合控制流内重绑定等无法安全求值的写名，必须使旧静态值退回未知，
不得把陈旧常量传播成不可达结论。
`--stage` 的 `choices` 里把段名写全是零成本的，`add_argument("--stage",
choices=[...]); print("ok")` 这个空壳照样过「认得 `--stage`」那一关，而它什么也没
产出——段名可达而不落产物，绑定是空的。

四处不算绑定：

- docstring / 常量里出现段名不算——出现不是可达。
- 只注册两个旗标不算——旗标是登记面。
- 声明了 `STAGES = {...}` 且 `choices` 从它取，但 `args.stage` 从没拿去索引它（只打印，两段无条件顺跑）不算：`--stage a` 与 `--stage b` 行为完全一样时，段与入口之间那条数据流并不存在。判的是控制流真的交给了那张表，不是表存在。
- 「本包只有一段，所以随便哪个脚本都算」不算。这条曾作兜底，它把判据从「这个入口能单独调起这一段」换成了「这个包只有一段」——段数是包的属性，不是入口的证据，单段包因此永远免检。单段包把脚本改名成 `run_<段名>.py` 即合规，成本一次改名，换来的是本判据无例外。

`handoff` 段不入本闸：该段产出由人做，本流程内没有执行脚本可绑。

### 6.3 执行段声明与四面闭包

持久 Skill 包的真实执行段只认 `SKILL.md` Markdown 围栏外的 `执行段：<段名>`
六槽卡。围栏内的卡片只作教学示例，不得充当本包执行段。围栏外正文任意位置的
反引号代码跨度只要呈 shell-like 可执行形态，即须落在编号四槽步或六槽卡内；识别
不能只靠有限命令白名单，须覆盖常用 CLI、wrapper / 环境变量前缀、相对或绝对脚本
路径与项目自带命令。命令前的散文说明与编号前缀均不豁免；围栏外裸编号命令、列表
命令与四空格缩进代码块亦按同一规则拒绝。backtick 与 tilde Markdown 围栏内的教学
代码均不进入本闸。单 token 属性名、配置路径等非命令代码跨度不得误伤。

同一包的 stage 集必须在四面精确相等：围栏外执行段卡、`assertions.json`
`stages[].stage`、执行 runner 的可达 dispatch、每份 `fixtures/golden*` 下
`run_manifest.json` 的 `stages[].stage`。任一面缺段或多段均 FAIL；空集合不得
冒充闭包成立。该闭包把“写在条文里的段”“闸会审的段”“脚本能跑的段”“正例
实际覆盖的段”锁成同一集合。

四面各自先验身份唯一：执行段卡名、`assertions.json` stage 名、每份 golden
manifest 的 stage 名均不得重复。先转 set 再比集合会把重复声明吞掉，故“集合相等”
不能替代唯一性检查。编号执行步同时接受 `1.` 与 `1)`；带 `**动作：**` 的 Markdown
bullet 同属列表式执行步，均须填满四槽，不能因列表前缀变化退出 M7。

### 6.4 占位残留 fail-closed

持久包的现役声明面不得残留模板占位标记。`SKILL.md` 与 `assertions.json` 围栏外
出现尖括号模板、TODO、TBD、FIXME、XXX、待填或待补标记时，M11 直接 FAIL；
围栏内教学示例不计入现役声明面。

---

### 6.5 · 文件回执与段选择

文件清单型 count_hash 断言必须声明 predicate.file_bindings，含 path_field 与 hash_field。按 run-dir 解析每个路径，拒绝绝对路径、父目录段、重复文件、目录及解析后越界的符号链接；重读真实文件，校验其 SHA-256 前 16 位。回执内部 count/hash 自洽仍须通过该文件核验。

调用审核器时在 --all 与一组唯一的 --stage 间二选一。未知段、空 stages、空 operations 或空 assertions 按契约/用法错误返回 rc=2，不形成 PASS 或完成 manifest。

## 7 · run manifest schema

每次运行产出一份，落 run 目录根。**T2 未跑不得表述为全链 PASS。**

```json
{
  "run_id": "<run 标识>",
  "package_hash": "<包内容指纹>",
  "contract_hash": "<assertions.json 指纹>",
  "run_dir_resolved": "<解析后的绝对路径>",
  "run_dir_source": "explicit_arg | env | default",
  "started_at": "<时刻>",
  "stages": [
    {
      "stage": "<段标识>",
      "operations": [
        {"op": "<operation>", "artifact": "<产物相对路径>",
         "source_reachability": "machine | human_handoff"}
      ],
      "audit_tiers_run": [0, 1],
      "assertions": {"passed": 0, "failed": 0, "unverified": 0},
      "verdict": "PASS | FAIL | PASS_WITH_UNVERIFIED",
      "unresolved_coverage": ["<未覆盖面的显式清单>"]
    }
  ],
  "final_verdict": "PASS | FAIL | PASS_WITH_UNVERIFIED",
  "retention": "always | on_failure | never"
}
```

**`source_reachability` 逐 operation 报，不设段级字段**：可达性是 operation 的属性。一段挂两个 operation 时两者可以不同，压成一个段级标量就只能二选一——报第一个则「另一个源不可机械重读」从 manifest 上消失，而 manifest 正是交接时用来判「哪些面没验」的那份东西；改报清单则同一字段时而是枚举值时而是数组，消费方按 schema 解析必错。段级的判定量（`audit_tiers_run` / `assertions` / `verdict`）仍按段汇总，因为它们本就是断言在段上的统计。

**`run_dir` 解析三级优先级**（显式 > 环境 > 默认），三级均合法，但解析结果必须落进 manifest 的 `run_dir_resolved` 与 `run_dir_source`：

1. 显式参数 `--run-dir <path>`——机器调用方（排程 / 上游流水线 / 测试 harness）强制走此级。
2. 环境变量。
3. 默认 `./runs/<run-id>/`。

包内禁写死绝对路径。诊断源：order-expiration-query 的 `out/` 为固定路径无条件覆盖，测试期两臂产物互相覆盖（`testbed/new_arm.sh` 注释存证）。

**`final_verdict` 生成规则**：任一段 `FAIL` → `FAIL`；无 FAIL 但存在 `unverified > 0` → `PASS_WITH_UNVERIFIED`；全部 tier 跑齐且零失败 → `PASS`。三值不得压成二值报出。

---

## 8 · tier 分层与闸的硬度

| tier | 读什么 | 何时跑 | 失败后果 |
|---|---|---|---|
| 0 | 终态产物 | 末端 | 阻断交付 |
| 1 | 本段账本（不读源） | **本段落盘后立即** | 阻断下游段（fail-fast） |
| 2 | 源 + 账本观测值比对 | 首次取源时 | 阻断下游段；源不可达则标 `UNVERIFIED` |

### 8.0 family↔tier 相符（预检，双向硬拒）

T2 专用族恰有两个——`source_readback`、`source_row_match`。判据是**该族是否真的读源**，不是作者觉得哪条更重要：

| 写法 | 判定 | 为什么 |
|---|---|---|
| 非 T2 族标 `tier: 2` | FAIL | 源不可达时走 `UNVERIFIED` 短路。UNVERIFIED 不进 `failed` 计数、不阻断交付、退出码不变红——这条断言从「须成立」变成「从未判过」，而摘掉防线的动作看起来像是更保守 |
| T2 族标 `tier: 0/1` | FAIL | 无源时它不再短路，照常求值判 `FAIL`——把「没法验」谎报成「验过了、不成立」 |

两面同判据同拒：`audit.py` 在求值前预检（排在 T2 短路**之前**，否则短路先吃掉这条），`validate.py` M9 在编译期预检。只留执行面不够——包交出去时没人跑过它，闸却说过了。

链形：

```text
init run manifest
→ run stage
→ audit --stage <stage>   非 0 立即停
→ next stage
→ audit --all
→ finalize manifest
```

### 8.1 退出码三分

判定有三个值（§7 `final_verdict`），加上「闸没跑成」这一种，共四码，各占一个，不压缩：

| 码 | 判定 | 含义 | 出现在 |
|---|---|---|---|
| `0` | `PASS` | 全部 tier 跑齐、零失败 | `--stage` / `--all` |
| `1` | `FAIL` | 任一断言 FAIL | `--stage` / `--all` |
| `2` | —— | 用法或契约本身错，断言**一条都没跑过** | 任何调用 |
| `3` | `PASS_WITH_UNVERIFIED` | 无 FAIL，但有 `UNVERIFIED` | **仅 `--all`** |

- **`3` 不并进 `0`**：「验过且全对」与「有面没验」是两种交接状态。并进同一个码，调用方（排程 / 上游流水线 / 交付闸）的信号里「哪些面没验」这一位就消失了——而这正是 §7 要求 manifest 报 `unresolved_coverage` 的那件事。要判它就只能去解析 stdout，闸的判定退化成文本比对。
- **`3` 只在 `--all` 出现**：两种调用职责不同。`--stage` 是 fail-fast 段闸，输出只回答「下游能不能走」；源不可机械重读不是产物错，按 §8 表 tier 2 行的规定不阻断 T0/T1，故段闸下该判定返回 `0`。UNVERIFIED 不因此丢失：逐条在 stdout / `--json` 的 rows 里，并落进 manifest。
- **`2` 不并进 `1`**：契约写错时断言根本没跑过，与「跑了且拒了」不是一回事。并进 `1` 则「闸拒了」与「闸没跑」在退出码上不可分——而这两种情况的处置完全相反（前者修产物，后者修契约）。
- **调用方判 `rc == 1`，不判 `rc != 0`**：把 `2` 当检出，等于把「闸没跑成」记成一次成功拦截；把 `3` 当失败，等于让源不可达阻断整条链。
- **逐条 rows 与退出码必须同判定**：rows 含任一 `FAIL` 时 rc 必为 `1`；零 FAIL
  但含 `UNVERIFIED` 时 `--all` rc 必为 `3`；其余为 `0`。调用方须同时核两面，
  任一矛盾即审核器自身 FAIL，不得挑对自己有利的一面采信。

**弱断言只能 WARN，不能单独满足段闸。**族名：`existence`（存在性）、`nonzero rows`（行数 > 0）、`file present`（文件在位）。「文件存在」只证明产物出生，不证明产物正确。

弱不等于可以不判：三族都必须真跑，空集 / 文件不在时判 FAIL。「弱」说的是这条断言的结论弱，不是它可以不出结果——声明了却判不出，与没声明的区别只在登记表上。

**同一断言连续两次 FAIL → 停手交人，不再自动重试。** 重试对确定性断言无意义，连续失败是判据错或源变了，属需要人判的信号。

---

## 9 · 审核器自身的验收

审核器是一个判断节点，未验的审核器不构成检验。每个包的 `audit.py` + `assertions.json` 组合须过：

- **正例 golden**：已知正确的 run，全断言 PASS。
- **定向 mutant**：每个登记的强断言至少有一个必须被它拒绝的 mutant。
- **谓词族逐族证伪**：`audit.py` 的 `FAMILIES` dispatch 值域就是谓词闸集合；每个
  family 入口须有稳定 Gate-ID、obligation、实现漂移探针及至少一条绑定到该 family
  断言行的定向负例。dispatch 有而 witness 无、验收语料零引用、理由只在别的断言行
  或输入回显中出现，均 FAIL。弱族也必须以“正例 WARN / 坏例 FAIL”证明真执行。
- **假阳性对照**：golden 上零 FAIL。
- **元数据独立性**：同一 golden / mutant 载荷改成中性目录名并剥掉
  `INJECTION.json` 后，逐条状态必须不变。审核器读取 fixture 名称或
  `must_be_rejected_by` 来生成判定，等于偷看测试答案，FAIL。
- **逐条身份闭合**：输出的断言 id 须非空、唯一，且恰来自本契约；重复 id 会被
  结果映射覆盖，幽灵 id 会伪增覆盖面，两种都 FAIL。status 只取
  `PASS | FAIL | WARN | UNVERIFIED`。
- **隔离执行边界**：验收 `audit.py` 时只把当前 case、canonical contract、包内规则与
  可信通用解释器复制进一次性探针；候选审核器及其子进程断网，探针外读写、外部信号与
  后台遗留进程均由 OS 隔离器拒绝。薄封装可在同一边界内调用可信解释器；隔离后端不可用、
  越界副作用或脚本未完成均 fail-closed，不得用一份格式正确的 rows 掩盖验收期间的外部动作。

诊断源两例：2026-08-06 隔离测试 harness 自身出过一次假阳性（T2 解析器把空白行数据当格式丢弃——与被审对象同构的错）；order-expiration-query 的 `check.sh` 实现期踩 CRLF 与 bash 3.2 两处自身 bug（23 行错数成 1481）。

**审核器与生产脚本不得从同一段散文自由生成**（共因错误）：生产端读 contract IR 生成执行逻辑，审核端读同一份 `assertions.json` 由稳定解释器执行——解释器本体跨包复用、随 §10 回归语料一起演进，不逐包重写。

**接口不混用**：交互查询 / 诊断工具与生产交付闸分开两个入口。一个脚本同时承担「用户查订单」与「出 PASS/FAIL」两种接口时，闸会退化成靠人目视比对。诊断源：order-expiration-query 的 `run.sh` 不调用 `check.sh`，SKILL.md 要求 agent 目视比对两份输出。

---

## 10 · 解释器回归语料

`exec-ledger-isolation/` 的 2 个 golden run + E1–E10 注入 run 是解释器本体的回归语料，按 operation 归族见 `references/mutant_matrix.md`。改解释器后须全跑，结果与预注册预期表逐格对照；不一致先疑解释器，不改预期表迁就实现。

### 10.1 obligation registry

`references/obligation_registry.json` 是“条文要求由哪道闸执行”的机读登记面。每道
机械闸须有稳定 gate id、源码函数、判据源节与 obligation id；每条 obligation
须至少被一道闸执行，并在 `SKILL.md` 用 `[OBL:<id>]` 承接。源码实际闸集合、
registry 闸集合、闸 docstring 声明、SKILL obligation 引用四面须精确闭合。

registry 的 `implementation_sha256` 只作**疏忽漂移探针**：去 docstring 后的 gate 与
可达 helper AST 变化却未同步登记时 FAIL。它不承担主动防篡改——改实现者可以调用
同一 `body_hash()` 重算并重签 registry；同源实现生成的指纹不能反过来证明实现正确。

验收使用的独立实现证据落在候选树外 `exec-ledger-isolation/gate_behavior_registry.json` 与
`tools/gate_behavior.py`：每个源码实际 gate id 必须恰有一个行为 witness 集；未改正例
须 PASS，所有归属该 witness 集的注册定向负例须由指定目标闸判 FAIL 且命中指定理由。
validate 负例还须剥离 `GATE_INJECTION.json`、换成中性目录名复跑，五闸状态不得漂移。
每个定向负例都须在候选树外独立登记稳定的机器病因码；候选诊断以
`[CAUSE:<code>]` 输出。目标闸块必须恰有该负例登记的单元素病因集合（同码重复允许）；
缺码、错码、通用码或同时塞入多个码均 FAIL。此约束覆盖 M7-M11 全部 79 个定向负例，
不以共享自由文本理由为分组边界；同一闸的全部诊断也不得塌成一条超集消息。自由文本只供
人读，不能单独证明理由与失败机制仍一一绑定。M7 命令归槽负例另绑定 `(行号, 原始命令)`
唯一元组，防止保留病因码却丢失可定位诊断。

若同一 `(目标闸, 病因码)` 由多个定向负例共享，候选树外 registry 还须登记该组当前
合法的不同目标诊断块数。完整行为入口与 gate matrix 都按目标闸块内容计算组内多样性，
并要求与基线精确相等。基线集合须与全部多成员病因组精确闭合，新增 fixture 后不得
静默落在未受管组。

块数只锁分区基数，不能证明块内仍有诊断内容。对基线块数大于 1 的多成员组，每个
fixture 还须登记闸别结构化诊断绑定；验收树用与候选实现分离的 extractor 抽出定位行、
原命令、缺槽、段名/脚本、不可达机制、隔离真跑结果与失败类别、载荷指纹、缺失族、
family↔tier 与来源标题等事实，实际集合
必须精确等于登记集合。绑定项集合须与这些组的全部成员精确闭合。这样同时拒绝块数变化
与“保留块数/病因码/reason、只掏空块内解释”的内容退化；自然语言措辞可变，受约束的
结构事实不可丢失或换位。当前 9 个多成员组均有可抽取的机制事实与逐 fixture 绑定。
其中 M8 不可达写盘组按 6 种机制计数：死函数、字面量假分支、绑定常量假分支
（模块/局部各一件）、一元取反、逻辑短路、return 后语句；机制块数基线为 6、
逐 fixture 绑定为 7。同一机制允许多件，机制缺口不得靠增加同形 fixture 冲数；
不得把可区分机制登记成基线 1 来豁免归因。
M8 隔离真跑失败组按 6 种机制计数：rc0 但缺产物、assertion error、沙箱拒外写、
沙箱拒网络、沙箱拒外部信号、沙箱拒 fork；12 个 fixture 逐件绑定，机制块数基线为 6。
同组内若诊断承担数据定位职责（如 M7 指明违规行与原始命令），外部 registry 还须登记
预期定位值；目标块解析出的定位元组集必须精确等于该负例的登记项。只保留通用 reason、
替换定位值或把多个负例的定位值塞进一条超集消息，均 FAIL。
witness 集的 gate id 与源码实际 gate 集须精确相等；audit 谓词 gate 从 `FAMILIES`
值域机械发现，不维护函数名白名单。`skill_drift.py` 的正常入口必须实跑该行为面；
`--static-only` 只供漂移器自身的单点负例隔离，不得用于候选验收或发布判定。静态面
无问题时必须输出 `PARTIAL（未跑行为面）` 并返回 rc3，不得与完整 `PASS` / rc0 同形。

这里的独立边界是 candidate tree 与候选树外验收树：它阻断“只改候选实现并用同源
hash 重签”的自洽伪证，不声称提供密码学防篡改。若同一写入者同时改候选、行为 registry、
runner 与 fixture，机械证据也可被重造；该更高层风险须由独立复审者固定验收树并核 diff。

因此 pass / 恒返回空壳、实现体漂移、函数仍登记但调用解除仍由静态面优先拒；若在
活体首行提前 return、保留后续旧函数体并同步重签实现 hash，静态面即使自洽，也须由
该 gate 名下的独立行为 witness 拒绝。新增条文要求却没有 registry obligation 或执行
闸，及删除闸的全部判据源声明，均按漂移 FAIL。

查看尾部输出须运行 `tools/skill_drift_tail.sh`，或由调用方先 `set -o pipefail` 再接
管道。裸 `python3 skill_drift.py | tail` 的退出码按 shell 规则取自 `tail`，不能当作
验收结果；全矩阵使用带 `pipefail` 的受支持入口。
