---
title: GitHub 反馈执行段机械契约
type: skill-reference
version: "10.06.1"
---

# GitHub 反馈执行段机械契约

## process_feedback receipt

验证入口读取显式运行目录中的 input/request.json；只使用隔离传输，调用实际生产 transaction 函数生成、提交并重复回查同一反馈。网络与凭据均不进入此验证入口。生产 CLI 继续以宿主的真实连接运行，同一 transaction 内的写入调用 entrypoints.py 的受控入口。

回执必须有非空 source_id、fetched_at 和 locator。outputs 列表中的每个对象必须有字符串 id、kind、sha256。id 是运行目录内的相对普通文件，sha256 是重读该文件字节得到的 SHA-256 前 16 位。output_count 等于 outputs 实际行数，outputs_sha256 等于该列表按 UTF-8、键排序、紧凑分隔符编码后的 SHA-256 前 16 位。

stage_outputs/process_feedback/observed.json 是同段声明的第二产物。它也必须有非空 source_id、fetched_at、locator；receipts 包含两次实际回执，每条包含字符串 result、url、state 和整数 number。receipt_count 等于 receipts 长度，receipts_sha256 为同一规范 JSON 编码的 SHA-256 前 16 位。该文件同时保存实际创建回执、重复请求回执、外部效果调用次数、远端记录数和输入摘要。业务正确性由实际行为测试与 stateful 恢复测试负责；此段机械断言只证明产物来源和文件完整性，不能用这些断言宣称宿主已部署。

## 运行边界

真实生产外部效果只有三个边界：create、comment、patch。它们通过 apply_feedback_effect 进入 apply_transaction，动作由生产 RemoteEffectAdapter 执行。每一边界先持久化意图，独立回查后才决定是否执行；未知状态进入人工核查，已有效果不重放。journal 在完整操作范围持有本机独占锁，单个边界的 unlock 结束其检查阶段，操作退出时由 journal 上下文释放进程锁。
