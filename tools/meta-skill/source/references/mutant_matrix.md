# mutant 矩阵

> **本文由 `exec-ledger-isolation/tools/gen_mutant_matrix.py` 生成，勿手改。**
> 改语料后重跑生成器；矩阵臂以 `--check` 验证盘上文档与登记表同步。

每个 operation 的最低谓词族要成为防线，得有至少一个 mutant **被它登记的那条
断言**拒绝过。判据是「被指名的那条拒」，不是「跑出了 FAIL」——错的断言抓错的
错，等于没抓。旁落项（同一注入连带打到的别的断言）在登记表里显式列出，只作
记录，不计入证伪。

## 一 · 按 operation 归族

封闭词汇表八类，定向 mutant 共 49 个。

| operation | mutant 数 | 覆盖的断言 |
|---|---|---|
| `acquire` | 12 | `r0.count_hash`, `r0.schema_conformance`, `r0.source_receipt`, `s1.count_hash`, `s1.schema`, `s1.source_rows`, `x.left_count`, `x.left_receipt`, `x.left_schema`, `x.right_count`, `x.right_receipt`, `x.right_schema` |
| `aggregate` | 2 | `s8.bucket_rebuild`, `s8.detail_recomputation` |
| `filter` | 4 | `s2.predicate_replay`, `s2.subset` |
| `handoff` | 3 | `h0.artifact_hash`, `h0.receiver_receipt`, `h0.schema_conformance` |
| `join` | 5 | `j1.cardinality`, `j1.joined_value_replay`, `j1.key_coverage`, `j1.unmatched_set` |
| `map` | 8 | `s3.attr_source_readback`, `s3.key_preservation`, `s5.source_readback`, `s6.key_preservation`, `s7.key_preservation`, `s7.source_readback`, `y.from_right` |
| `partition` | 3 | `s4.disjoint`, `s4.union`, `s7.enum_rule_replay` |
| `render` | 12 | `final.claimed_total_match_source`, `final.counts_match_source`, `final.output_field_coverage`, `final.render_source_replay`, `final.summary_reconciliation` |

## 二 · 定向 mutant 逐条

### `acquire`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M1-page-total-drift` | OAQ | `s1.count_hash` | — | acquire · 声明行数与实到行数漂移（静默截断的自报侧） |
| `M2-schema-field-missing` | OAQ | `s1.schema` | — | acquire · 导出字段缺失（勾选字段不全 / 结构漂移） |
| `M26-source-row-drift` | OAQ | `s1.source_rows` | — | acquire · 账本行内容与源表漂移，同行数与内容 hash 保持自洽 |
| `R1-fee-type-drift` | jh | `r0.schema_conformance` | `r0.count_hash`, `j1.joined_value_replay` | 右表费率由数值变字符串——字段名在、类型漂。 |
| `R2-fee-receipt-missing` | jh | `r0.source_receipt` | — | 取数回执缺取数时刻——「这批数是什么时候的」无从回答。 |
| `R3-fee-content-drift` | jh | `r0.count_hash` | `j1.joined_value_replay` | 行数不变、内容改了：改一条费率的数值，row_count 一动不动。 |
| `X1-second-op-broken` | multiop | `x.right_count` | — | 第二个 operation 的产物坏：右账声明行数漂移。 |
| `X2-first-op-broken` | multiop | `x.left_count` | — | 第一个 operation 的产物坏：左账声明行数漂移。 |
| `X4-left-receipt-missing` | multiop | `x.left_receipt` | — | 左账回执缺 source_id——只打 x.left_receipt，不碰 rows。 |
| `X5-left-schema-type-drift` | multiop | `x.left_schema` | — | 左账 amount 由 int 漂成 str，重打哈希——只打 x.left_schema。 |
| `X6-right-receipt-missing` | multiop | `x.right_receipt` | — | 右账回执缺 fetched_at——只打 x.right_receipt。 |
| `X7-right-schema-type-drift` | multiop | `x.right_schema` | — | 右账 amount 由 int 漂成 str，重打哈希——只打 x.right_schema。 |

### `aggregate`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M11-bucket-swap` | OAQ | `s8.bucket_rebuild` | — | partition · 两桶成员互换：计数、和、互斥、可枚举全部恒真 |
| `M16-count-list-decoupled` | OAQ | `s8.detail_recomputation` | — | aggregate · 计数与清单脱钩，但七类和仍 = N（守恒恒真） |

### `filter`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M18-filter-duplicate-row` | OAQ | `s2.subset` | — | filter · 出集把一条保留单复制一份（多重集重数增生） |
| `M19-filter-row-content-rewrite` | OAQ | `s2.subset` | — | filter · 保留行的非谓词字段被改写（sku 改了，country 没动） |
| `M3-phantom-order` | OAQ | `s2.subset` | — | filter · 出集凭空多出入集没有的单 |
| `M4-country-leak` | OAQ | `s2.predicate_replay` | — | filter · 谓词坏死：非中国发货混进保留侧 |

### `handoff`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `H1-payload-hash-drift` | jh | `h0.artifact_hash` | — | 交接物被改（多一行），账本里记的哈希还是旧的。 |
| `H2-intake-schema-gap` | jh | `h0.schema_conformance` | `j1.unmatched_set` | 接回的行缺 sku——字段级残缺，行数对得上。 |
| `H3-receipt-missing` | jh | `h0.receiver_receipt` | — | 接收回执没记接收人：出了问题找不到人，交接等于没交接。 |

### `join`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `J1-join-drop-silent` | jh | `j1.key_coverage` | — | 左键凭空消失：既不在 joined，也不进 unmatched 名单。 |
| `J2-join-fanout` | jh | `j1.cardinality` | — | 右表重键 → 左键一对多放大。总额随之虚增，是 join 最常见的错法。 |
| `J3-unmatched-unlogged` | jh | `j1.unmatched_set` | `j1.key_coverage` | 未匹配只记数不记名单——数对得上，具体是谁查不出来。 |
| `J4-fee-swap` | jh | `j1.joined_value_replay` | — | 两个已连接键的右表载荷互换：键形状一字未动，取值全错。 |
| `J5-false-unmatched` | jh | `j1.unmatched_set` | — | 右表确有匹配的键，被从 joined 挪进 unmatched_ids。 |

### `map`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M12-classify-gap` | OAQ | `s3.key_preservation` | — | map · 入段漏判：s2 有的单在 s3 从未被分类（键集缺口） |
| `M14-funnel-overstep` | OAQ | `s6.key_preservation` | — | map · 漏斗越位：上游已止步的单仍进本段（键集凭空多出） |
| `M15-funnel-drop` | OAQ | `s7.key_preservation` | — | map · 漏斗丢单：上游 continue 的单未进本段 |
| `M20-map-duplicate-row` | OAQ | `s3.key_preservation` | — | map · 分组结果把一条复制一份（键集不变，行数变了） |
| `M5-attr-observation-miscopy` | OAQ | `s3.attr_source_readback` | — | map · 属性观测抄错（源=自制，账本记委外），下游裁决随之自洽 |
| `M7-prod-observation-miscopy` | OAQ | `s5.source_readback` | — | map · 生产观测抄错（源=有未完成，账本记全完成） |
| `M9-logistics-observation-miscopy` | OAQ | `s7.source_readback` | — | map · 物流观测抄错（源=待建物流单，账本记已发货） |
| `X3-downstream-drop` | multiop | `y.from_right` | — | 下游漏掉右账的一行——验的是跨段引用真的落在第二份产物上。 |

### `partition`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M13-tier-union-gap` | OAQ | `s4.union` | — | partition · 入集有的活单没进任何时效桶（并集不完整） |
| `M6-tier-double-listed` | OAQ | `s4.disjoint` | — | partition · 同一单落两个时效组（互斥破缺） |
| `M8-logistics-complement-form` | OAQ | `s7.enum_rule_replay` | — | partition · 把第 6 步的补集式搬到第 7 步：八态之外误判为异常 |

### `render`

| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |
|---|---|---|---|---|
| `M10-render-count-drift` | OAQ | `final.counts_match_source` | — | render · 成品件计数与数据源漂移（出表环节改数） |
| `M17-render-summary-drift` | OAQ | `final.summary_reconciliation` | — | render · 成品件计数与数据源一致，但件内清单与计数打架 |
| `M21-render-unread-field` | OAQ | `final.output_field_coverage` | — | render · 成品件新增一个自报字段，没有任何断言读过它 |
| `M22-render-parent-prefix-only` | OAQ | `final.output_field_coverage` | — | render · lists_public 下新增一个桶，兄弟桶全被逐一比对也覆盖不到它 |
| `M23-claimed-total-drift` | OAQ | `final.render_source_replay` | — | render · 成品件自报总量与上游脱钩 |
| `M24-public-list-属性异常` | OAQ | `final.render_source_replay` | — | render · 公开清单「属性异常」的成员与汇总件对不上 |
| `M24-public-list-无工单` | OAQ | `final.render_source_replay` | — | render · 公开清单「无工单」的成员与汇总件对不上 |
| `M24-public-list-物流异常` | OAQ | `final.render_source_replay` | — | render · 公开清单「物流异常」的成员与汇总件对不上 |
| `M24-public-list-状态待判` | OAQ | `final.render_source_replay` | — | render · 公开清单「状态待判」的成员与汇总件对不上 |
| `M24-public-list-生产异常` | OAQ | `final.render_source_replay` | — | render · 公开清单「生产异常」的成员与汇总件对不上 |
| `M24-public-list-质检异常` | OAQ | `final.render_source_replay` | — | render · 公开清单「质检异常」的成员与汇总件对不上 |
| `M25-claimed-total-chain-drift` | OAQ | `final.claimed_total_match_source` | — | render · 总量沿链一致地漂：成品件与汇总件同改，直连比对看不见 |

## 三 · E 族（主套件预注册预期）

推导链层面的注入，预期在 `fixtures/derivation.md` 里**跑前写定**——
跑完再填预期是拿结果当判据，实现怎么错预期就怎么歪。

| run | 预期被这条拒 |
|---|---|
| `E1-whitelist-always-false` | `s6.whitelist_rule_replay` |
| `E10-observation-miscopy` | `s6.source_readback` |
| `E2-today-start-shift` | `s4.assignment_rule_replay` |
| `E3-silent-row-drop` | `s2.excluded_count` |
| `E4-attr-route-contradiction` | `s3.attr_rule_replay` |
| `E5-pipeline-drop` | `s5.key_preservation` |
| `E6-whitelist-shrunk` | `s6.whitelist_rule_replay` |
| `E7-double-count` | `s8.total_reconciliation` |
| `E8-outsource-route-reversal` | `s5.route_rule_replay` |
| `E9-forced-balance` | `s8.each_bucket_enumerable` |

## 四 · e2e 包内语料

`packages/e2e-orders-probe/fixtures/` 下的 golden + 定向 mutant，
受编译器 M10 闸检验（golden 须零 FAIL，每个 mutant 须被指名的断言拒）。
golden 由 `scripts/run_stages.py` 实跑产出，不手写。

| mutant | 须被这条拒 | 注入内容 |
|---|---|---|
| `E1-receipt-key-missing` | `s1.receipt` | acquire · 取数回执缺一个声明键（source_id 没落账） |
| `E2-schema-type-drift` | `s1.schema` | acquire · 字段类型漂移：A003 的 country 落成整数 |
| `E3-count-drift` | `s1.count_hash` | acquire · 声明行数与实到漂移（静默截断的自报侧） |
| `E4-country-rewrite` | `s1.source_readback` | acquire · 观测抄错：源表记 A004 中国发货，账本记美国发货 |
| `E5-subset-alien-row` | `s2.subset` | filter · 出集凭空多出入集没有的单 |
| `E6-country-leak` | `s2.predicate_replay` | filter · 谓词坏死：该删的美国发货单被留下 |
| `E7-deleted-count-drift` | `s2.excluded_count` | filter · 静默丢单：删了 2 单，删除计数报 0 |

## 五 · 闸负例（编译器机械闸 M7-M11）

`gate-fixtures/` 与 `custom-fixtures/` 下的定向坏包，各自从正例整包复制后
**只坏一处**，判据是「被指名的那道闸拒」。旁落的别的闸只作记录：坏包同时
踩响两道闸时，若不指名，闸恒 FAIL 与闸能鉴别在退出码上长得一样。

| fixture | 套件 | 须被这道闸拒 | 注入内容 |
|---|---|---|---|
| `C1-junk-artifacts` | custom | M9 | M9 · golden/mutant 是塞满垃圾的非空目录——目录在位不等于料成立 |
| `C10-strong-family-marked-t2` | custom | M9 | M9 · 机械可判的族被标成 T2——借 UNVERIFIED 把断言从「须成立」降成「没判过」 |
| `C2-anchor-file-missing` | custom | M9 | M9 · source_anchor 指向不存在的文件（裸 bogus.md） |
| `C3-anchor-heading-missing` | custom | M9 | M9 · source_anchor 的文件在、标题不在——锚点悬空 |
| `C4-path-escape` | custom | M9 | M9 · 路径逃逸：golden 指到包外 |
| `C5-same-content-diff-path` | custom | M9 | M9 · 同料不同路径：mutant 是 golden 的逐字节副本 |
| `C6-mutant-not-rejected-by-named` | custom | M9 | M9 · mutant 里的错不在被指名的那条断言上 |
| `C7-same-payload-diff-metadata` | custom | M9 | M9 · 同载荷不同元数据：mutant 载荷与 golden 逐字节相同，只多了 INJECTION.json |
| `C8-t2-family-marked-t1` | custom | M9 | M9 · 回源族被降成 T1——family↔tier 不符，且顺手废掉 UNVERIFIED 语义 |
| `C9-anchor-substring-only` | custom | M9 | M9 · 来源锚只是某个真标题的子串——指向哪一节不确定 |
| `P1-persistent-but-empty` | custom | M8 | P1 · 持久包判定：既无 assertions.json 也无两类脚本，带 --persistent 必须被拒。 |
| `G1-no-audit-script` | gate | M8 | M8 · 审核脚本缺失——源不可达也不豁免审核脚本，缺件即 fail |
| `G10-golden-fails-on-positive` | gate | M10 | M10 · 正例上闸也拒——假阳性对照不成立 |
| `G11-golden-all-unverified` | gate | M10 | M10 · 审核器真读契约、遍历全部断言，却一条也不判——全 UNVERIFIED 不是背书 |
| `G12-runner-no-stage-flag` | gate | M8 | M8 · 共用 runner 不认 --stage——中间段无从单独调起 |
| `G13-stage-entrypoint-stub` | gate | M8 | M8 · 入口是空壳——认得段名，一份产物也不落 |
| `G14-stage-name-docstring-only` | gate | M8 | M8 · 段名只在 docstring 里——散文不构成认领 |
| `G15-runner-unrelated-to-stages` | gate | M8 | M8 · 执行脚本与本包的段全无关系——两个旗标一个也不认 |
| `G16-dispatch-declared-not-used` | gate | M8 | M8 · 旗标齐、段名字典齐，字典却没被用来选路——声明一张表不是绑定 |
| `G17-card-missing-value-domain` | gate | M7 | M7 · 卡片式执行段缺「值域」一槽——单点，只打卡片式那一支 |
| `G18-unmarked-exec-command` | gate | M7 | M7 · 裸 shell 命令编号步未标动作，旧 M7 完全看不见 |
| `G19-assertions-omits-stage` | gate | M8 | M8 · assertions 少声明 s2，四面 stage 集必须精确闭合 |
| `G2-op-outside-vocab` | gate | M9 | M9 · operation 在封闭词汇表外，且未走 custom 三条件 |
| `G20-fenced-example-only` | gate | M7 | M7 · 只有围栏内教学卡，持久包的真实执行段集合为空 |
| `G21-inline-command-in-prose` | gate | M7 | M7 · 普通散文句内嵌反引号命令，命令不在行首也须落四槽 |
| `G22-numbered-prefix-inline-command` | gate | M7 | M7 · 编号散文前缀后嵌反引号命令，前置说明不得绕过四槽闸 |
| `G23-git-inline-command` | gate | M7 | M7 · git 行内命令不在旧白名单，仍须落四槽 |
| `G24-curl-inline-command` | gate | M7 | M7 · curl 行内命令不在旧白名单，仍须落四槽 |
| `G25-relative-script-command` | gate | M7 | M7 · 相对路径脚本命令须落四槽 |
| `G26-poetry-wrapper-command` | gate | M7 | M7 · poetry wrapper 命令须落四槽 |
| `G27-pnpm-command` | gate | M7 | M7 · pnpm 项目命令须落四槽 |
| `G28-env-prefixed-command` | gate | M7 | M7 · 环境变量前缀命令须落四槽 |
| `G29-absolute-path-command` | gate | M7 | M7 · 绝对解释器路径命令须落四槽 |
| `G3-family-coverage-gap` | gate | M9 | M9 · 最低强断言族缺条（filter 缺 predicate_replay，只剩两条守恒式） |
| `G30-bare-numbered-command` | gate | M7 | M7 · 无反引号裸编号 git 命令须落四槽 |
| `G31-indented-command-block` | gate | M7 | M7 · 四空格缩进命令块须落四槽 |
| `G32-empty-slot-shell` | gate | M7 | M7 · 四槽标签在但前三槽为空，不构成结构化执行步 |
| `G33-dead-write-decoy` | gate | M8 | M8 · 死函数写产物诱饵不可替代 stage handler 可达写盘 |
| `G34-auditor-reads-test-answer` | gate | M10 | M10 · 审核器偷读 INJECTION 答案，原矩阵看似全对也须拒绝 |
| `G35-constant-dead-write` | gate | M8 | M8 · if False 常量死分支里的写盘不构成 stage 产出 |
| `G36-post-return-write` | gate | M8 | M8 · return 后不可达写盘不构成 stage 产出 |
| `G37-audit-exit-row-mismatch` | gate | M10 | M10 · rows 明示 FAIL 却返回 rc0，控制信号与证据互相矛盾 |
| `G38-duplicate-assertion-id` | gate | M8 | M8 · assertions.json 断言 id 重复，结果映射会覆盖前一条 |
| `G39-duplicate-skill-stage` | gate | M7 | M7 · SKILL 两张执行段卡重名，set 闭包会吞掉重复声明 |
| `G4-assertion-no-mutant` | gate | M10 | M10 · 强断言 mutants 为空——未经证伪，不构成检验 |
| `G40-duplicate-contract-stage` | gate | M8 | M8 · assertions.json 两个 stage 重名，set 闭包会吞掉重复声明 |
| `G41-duplicate-manifest-stage` | gate | M8 | M8 · golden manifest 两个 stage 重名，set 闭包会吞掉重复声明 |
| `G42-paren-numbered-missing-slots` | gate | M7 | M7 · `1)` 编号动作行缺三槽且没有命令，不能靠编号变体绕过 |
| `G43-bullet-action-missing-slots` | gate | M7 | M7 · bullet 动作行缺三槽且没有命令，列表形态同样须四槽 |
| `G44-audit-unknown-row` | gate | M10 | M10 · 审核输出夹带契约未声明的 ghost 断言 |
| `G45-audit-duplicate-row` | gate | M10 | M10 · 审核输出重复第一条 id，dict 映射会吞掉一条 |
| `G46-module-bound-constant-dead-write` | gate | M8 | M8 · 模块级常量绑定后的假分支仍不可达 |
| `G47-local-bound-constant-dead-write` | gate | M8 | M8 · 函数内常量绑定后的假分支仍不可达 |
| `G48-not-true-dead-write` | gate | M8 | M8 · 一元 not 组成的静态假分支仍不可达 |
| `G49-short-circuit-dead-write` | gate | M8 | M8 · 布尔短路中含必假项的分支仍不可达 |
| `G5-placeholder-residue` | gate | M11 | M11 · 模板占位残留（成品里留未填的 TODO 产物名） |
| `G50-compare-dead-write` | gate | M8 | M8 · 比较式假分支由隔离真跑兜住，不依赖静态枚举 |
| `G51-empty-list-dead-write` | gate | M8 | M8 · 空列表假分支由隔离真跑兜住 |
| `G52-empty-dict-dead-write` | gate | M8 | M8 · 空字典假分支由隔离真跑兜住 |
| `G53-empty-tuple-dead-write` | gate | M8 | M8 · 空元组假分支由隔离真跑兜住 |
| `G54-len-empty-dead-write` | gate | M8 | M8 ·纯函数 len 假值由隔离真跑兜住 |
| `G55-bool-zero-dead-write` | gate | M8 | M8 · 纯函数 bool 假值由隔离真跑兜住 |
| `G56-while-compare-dead-write` | gate | M8 | M8 · while 比较式假分支由隔离真跑兜住 |
| `G57-assert-false-dead-write` | gate | M8 | M8 · assert 终止导致的运行崩溃须 fail-closed |
| `G58-runtime-external-write` | gate | M8 | M8 · 真跑探针须禁止 run-dir 外写入 |
| `G59-runtime-network` | gate | M8 | M8 · 真跑探针须禁止网络能力 |
| `G6-slot-missing-value-domain` | gate | M7 | M7 · 编号执行步缺值域槽 |
| `G60-runtime-signal` | gate | M8 | M8 · 真跑探针须禁止向沙箱外进程发信号 |
| `G61-runtime-fork` | gate | M8 | M8 · 真跑探针须禁止 fork 与后台进程逃逸 |
| `G62-runtime-copy-upstream` | gate | M8 | M8 · 从上游照抄一份文件不能冒充本段产物 |
| `G63-runtime-empty-artifact` | gate | M8 | M8 · 零字节普通文件不构成 stage 产物 |
| `G64-runtime-invalid-json` | gate | M8 | M8 · 扩展名为 JSON 的垃圾文本不能冒充 stage 产物 |
| `G65-runtime-hollow-json` | gate | M8 | M8 · 可解析的空壳 JSON 仍须通过本段声明断言 |
| `G66-runtime-upstream-mutation` | gate | M8 | M8 · 本段 runner 不得篡改预置的其他 stage 输入 |
| `G67-auditor-external-write` | gate | M10 | M10 · 审核器实跑时向验收探针外写副作用，判定本身仍可全绿 |
| `G68-auditor-external-read` | gate | M10 | M10 · 审核器实跑时读取验收探针外的主机文件，rows 仍可全绿 |
| `G69-runner-capture-symlink` | gate | M8 | M8 · runner 预植后续审计 stdout/stderr symlink，父进程不得跟随截断 |
| `G7-backsolve-not-discounted` | gate | M9 | M9 · 守恒式反解：断言登记 derived_fields，不得计入族覆盖 |
| `G8-no-fixtures-dir` | gate | M8 | M8 · fixtures/ 缺失——审核器验收料不在位，无从做假阳性对照 |
| `G9-mutant-not-actually-rejected` | gate | M10 | M10 · 登记面齐全但 mutant 拒不住——把 golden 的料塞进 mutant 目录 |

闸覆盖数（按须被拒的那道闸）：

| 闸 | 定向 fixture 数 |
|---|---|
| M10 | 10 |
| M11 | 1 |
| M7 | 19 |
| M8 | 37 |
| M9 | 13 |

## 六 · golden 正例

假阳性对照。golden 上出现任何 FAIL，则该套件全部「拒绝」都不携带信息——
闸恒 FAIL 与闸能鉴别，在退出码上长得一样。

| golden | 套件 |
|---|---|
| `golden-task1` | OAQ |
| `golden-task3` | OAQ |
| `golden-jh` | jh |
| `golden-multiop` | multiop |
| `fixtures/golden` | e2e 包 |
| `gate-fixtures/G0-good` | gate（五闸须全 PASS） |
| `custom-fixtures/C0-good` | custom（五闸须全 PASS） |

