#!/usr/bin/env bash
# full_matrix.sh — v3.8 候选件的全套验收矩阵；臂数由数组动态汇总。
#
# 各臂判据不同向：多数臂「rc=0 才算过」，2b 那臂反过来——歧义上游引用**必须**
# 被拒，rc=0 反倒是不合格。故汇总列打印的是**判定**（0=合格），另列 raw rc；
# 把两者混在一列时，反向臂显示 rc=0 PASS 与正向臂的 rc=0 PASS 长得一样，
# 而它们说的是相反的事。
#
# 臂数由 ${#NAMES[@]} 现算，不写死在收尾那句里：加一臂而收尾仍印「8/8」时，
# 那行字说的是上一版的事，而它恰好是唯一被人读的一行。
#
# 用法: bash tools/full_matrix.sh    （须在 exec-ledger-isolation/ 下跑）
# 退出码 0 = 全臂合格；n = n 臂不合格。
set -o pipefail
cd "$(dirname "$0")/.."
V=../v3.8-draft/scripts/validate.py
A=../v3.8-draft/scripts/audit.py
R=layer3_results; L1=layer1_results
declare -a NAMES VERDICTS RAW DIRN

run(){ NAMES+=("$1"); DIRN+=("须 0"); shift; "$@" >/tmp/m_out.txt 2>&1; r=$?
  RAW+=($r); VERDICTS+=($([ $r -eq 0 ] && echo 0 || echo 1))
  tail -2 /tmp/m_out.txt | sed 's/^/    /'; }

run_fail(){ NAMES+=("$1"); DIRN+=("须非 0"); shift; "$@" >/tmp/m_out.txt 2>&1; r=$?
  RAW+=($r); VERDICTS+=($([ $r -ne 0 ] && echo 0 || echo 1))
  tail -1 /tmp/m_out.txt | sed 's/^/    /'; }

echo "### 1 · 闸负例矩阵 (gate_matrix · gate-fixtures + custom-fixtures)"
run gate_matrix python3 tools/gate_matrix.py gate-fixtures custom-fixtures $V $L1/gate_matrix.json

echo "### 2 · 解释器验收矩阵 (accept_matrix · OAQ + jh + multiop 三套件)"
run accept_matrix python3 tools/accept_matrix.py runs fixtures/assertions_oaq.json \
  fixtures/mock-task1.md fixtures/mock-task3.md $R/accept_matrix.json \
  runs-jh fixtures/assertions_jh.json runs-multiop fixtures/assertions_multiop.json

echo "### 2b · 歧义上游引用须被拒（反向臂）"
run_fail ambiguous_ref python3 $A runs-multiop/golden-multiop \
  --contract fixtures/assertions_multiop_ambiguous.json --all

echo "### 3 · 运行期三臂链 (e2e_chain)"
run e2e_chain python3 tools/e2e_chain.py packages/e2e-orders-probe runs-e2e $R/e2e_chain.json

echo "### 4 · IR 三面漂移 (ir_drift)"
run ir_drift python3 tools/ir_drift.py

echo "### 5 · manifest 消费方 (manifest_consumer --self-test)"
run manifest_consumer python3 tools/manifest_consumer.py --self-test

echo "### 6 · e2e 包机械闸 (validate)"
run validate_e2e python3 $V packages/e2e-orders-probe

echo "### 7 · mutant 矩阵文档与登记表同步 (gen_mutant_matrix --check)"
run mutant_matrix python3 tools/gen_mutant_matrix.py ../v3.8-draft/references/mutant_matrix.md --check

echo "### 8 · compare_paths 契约写法负例 (render_contract_negatives)"
run render_negatives python3 tools/render_contract_negatives.py

echo "### 8b · 契约身份键运行期负例 (contract_identity_negatives)"
run contract_identity python3 tools/contract_identity_negatives.py

echo "### 8c · predicate fixture 生成器闭包"
run predicate_fixture python3 tools/make_predicate_fixtures.py predicate-fixtures --check

echo "### 8d · audit.py 28 个谓词族逐族行为证据"
run predicate_family python3 tools/predicate_family_behavior.py ../v3.8-draft

echo "### 8e · M 闸指定理由须绑定目标 detail 块"
run reason_binding python3 tools/gate_reason_binding_negatives.py

echo "### 8f · 契约显式路径、canonical schema 与 NOT_RUN 诊断分层"
run contract_path python3 tools/contract_path_behavior.py

echo "### 9 · 五面：SKILL.md ↔ IR ↔ registry ↔ 源码闸 ↔ 行为证据 (skill_drift)"
run skill_drift bash tools/skill_drift_tail.sh

echo "### 10 · 五面检查器自身的负例 (skill_drift_negatives)"
run skill_drift_neg python3 tools/skill_drift_negatives.py

echo "### 11 · v3.8 候选包 persistent 自验证（M8/M9/M10 禁 SKIP）"
run persistent_self python3 $V ../v3.8-draft --persistent

echo "### 12 · fixture registry → manifest → 实物闭包负例"
run fixture_material python3 tools/fixture_materialization_negatives.py

echo
echo "======== 汇总 ========"
bad=0
for i in "${!NAMES[@]}"; do
  if [ "${VERDICTS[$i]}" -eq 0 ]; then s=PASS; else s=FAIL; bad=$((bad+1)); fi
  printf "  %-18s rc=%-3d %-7s %s\n" "${NAMES[$i]}" "${RAW[$i]}" "${DIRN[$i]}" "$s"
done
echo "总判定: $([ $bad -eq 0 ] && echo "PASS 全绿（${#NAMES[@]}/${#NAMES[@]}）" || echo "FAIL（$bad 臂）")"
exit $bad
