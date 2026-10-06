# 触发判定卡 · meta-skill-self · original

派 1 个独立、互不可见的注册 sub-agent。只给 description 与待判用户消息，
不给 should_trigger 标签。独立性由派发记录证明，JSON 完整性不能证明独立性。

[skill description]
把一条「长链复杂判断工作流」蒸馏成可自动执行的 SKILL.md。创建任何新 skill 时调用；重写或加固已有 skill 时调用。输入可以是已完成的访谈语料 / 案例集 / 现役 skill 文本，或一个已成型的判据库（如某 agent 规则文件）。输出一份纯命令式 SKILL.md。

[待判用例]
0: Create a reusable skill
1: Run an existing skill
2: Repair an existing skill
3: Summarize a skills training class

各 agent 每条只判 TRIGGER 或 SKIP，写一份报告到 `fixture://run/workspace/meta-skill-self/trigger_eval/judging/original/runN.json`。
报告形状（N 为该 agent 编号，1 至 1；verdicts 必须覆盖全部 id 各一次）：
{"run": N, "eval_fingerprint": "6cf22704a020c64c4a8f1a6840914ed352b8ecd4a0d67fdd11dfb0efb20d1f60", "verdicts": [{"id": 0, "decision": "TRIGGER"}]}

全部报告到齐后运行：
`python3 fixture://package/scripts/run_trigger_eval.py score --skill meta-skill-self --root fixture://run/workspace --version original`
