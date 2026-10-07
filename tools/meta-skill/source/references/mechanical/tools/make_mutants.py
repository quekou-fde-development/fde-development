#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_mutants.py — 按 operation 归族补齐定向 mutant（M1–M11）。

存在理由（contract_ir §9）：**只 PASS 不 FAIL 的断言不构成检验**。
E1–E10 是按「真实事故形态」构造的，按 operation 归族后覆盖不全——acquire /
render 两族无 mutant，partition 的成员互换面、filter 的凭空多出面也无。
本器按 operation 特征逐条构造，每个 mutant 声明它必须被哪条断言拒绝。

每个 mutant 都从 golden 复制后定点改一处，改动写进 INJECTION.json 存证。

用法: python3 make_mutants.py <runs_root>
"""
import copy
import hashlib
import json
import os
import shutil
import sys

# mutant id → (基线 run, 说明, 必须被哪条断言拒绝, 改动函数)
def m1(r):
    """acquire · 声明行数与实到行数漂移（静默截断的自报侧）"""
    r["s1_export.json"]["page_total"] += 1


def m2(r):
    """acquire · 导出字段缺失（勾选字段不全 / 结构漂移）"""
    del r["s1_export.json"]["rows"][2]["sku"]


def m3(r):
    """filter · 出集凭空多出入集没有的单"""
    r["s2_filtered.json"]["orders"].append(
        {"id": "EF260899999999", "country": "中国发货", "sku": "30011",
         "created": "2026-08-05 09:00"})
    r["s2_filtered.json"]["deleted_us"] -= 1


def m4(r):
    """filter · 谓词坏死：非中国发货混进保留侧"""
    r["s2_filtered.json"]["orders"][0]["country"] = "美国发货"


def m5(r):
    """map · 属性观测抄错（源=自制，账本记委外），下游裁决随之自洽"""
    for c in r["s3_groups.json"]["classified"]:
        if c["id"] == "EF260805000001":
            c["observed_attr"] = "委外"
            c["group"] = "委外"
    for t in r["s4_tiers.json"]["tiers"]:
        if t["id"] == "EF260805000001":
            t["group"] = "委外"
    for p in r["s5_prod.json"]["results"]:
        if p["id"] == "EF260805000001":
            p["group"] = "委外"


def m6(r):
    """partition · 同一单落两个时效组（互斥破缺）"""
    dup = copy.deepcopy(r["s4_tiers.json"]["tiers"][0])
    dup["tier"] = 3
    r["s4_tiers.json"]["tiers"].append(dup)


def m7(r):
    """map · 生产观测抄错（源=有未完成，账本记全完成）"""
    for p in r["s5_prod.json"]["results"]:
        if p["id"] == "EF260801000005":
            p["observed"] = "全完成"
            p["decision"] = "continue"
    r["s6_qc.json"]["results"].append(
        {"id": "EF260801000005", "observed_status": "质检完成", "decision": "continue"})
    r["s7_logistics.json"]["results"].append(
        {"id": "EF260801000005", "observed_status": "待确认", "decision": "正常"})
    r["s8_summary.json"]["counts"]["生产异常"] = 0
    r["s8_summary.json"]["lists"]["生产异常"] = []
    r["s8_summary.json"]["counts"]["正常"] = 4
    r["s8_summary.json"]["lists"]["正常"].append("EF260801000005")
    r["final_stats.json"]["counts"] = copy.deepcopy(r["s8_summary.json"]["counts"])
    r["final_stats.json"]["lists_public"]["生产异常"] = []


def m8(r):
    """partition · 把第 6 步的补集式搬到第 7 步：八态之外误判为异常

    SKILL.md 第 7 步明写「不用补集式」「未知态无家」。这条挡的是
    规则形态串味——两步规则长得像，抄错一步不改数量、不破守恒。
    """
    r["s7_logistics.json"]["results"].append(
        {"id": "EF260801000006x", "observed_status": "运输中", "decision": "物流异常"})
    r["s6_qc.json"]["results"].append(
        {"id": "EF260801000006x", "observed_status": "质检完成", "decision": "continue"})
    r["s5_prod.json"]["results"].append(
        {"id": "EF260801000006x", "group": "自制", "observed": "全完成", "decision": "continue"})
    r["s4_tiers.json"]["tiers"].append(
        {"id": "EF260801000006x", "group": "自制", "created": "2026-08-01 16:30", "tier": 3})
    r["s3_groups.json"]["classified"].append(
        {"id": "EF260801000006x", "sku": "30022", "observed_attr": "自制", "group": "自制"})
    r["s2_filtered.json"]["orders"].append(
        {"id": "EF260801000006x", "country": "中国发货", "sku": "30022",
         "created": "2026-08-01 16:30"})
    r["s1_export.json"]["rows"].append(
        {"id": "EF260801000006x", "country": "中国发货", "sku": "30022",
         "created": "2026-08-01 16:30"})
    r["s1_export.json"]["page_total"] += 1
    r["s8_summary.json"]["counts"]["物流异常"] += 1
    r["s8_summary.json"]["lists"]["物流异常"].append("EF260801000006x")
    r["s8_summary.json"]["N_claimed"] += 1
    r["final_stats.json"]["counts"] = copy.deepcopy(r["s8_summary.json"]["counts"])
    r["final_stats.json"]["N_claimed"] += 1
    r["final_stats.json"]["lists_public"]["物流异常"].append("EF260801000006x")


def m9(r):
    """map · 物流观测抄错（源=待建物流单，账本记已发货）"""
    for x in r["s7_logistics.json"]["results"]:
        if x["id"] == "EF260803000004":
            x["observed_status"] = "已发货"
            x["decision"] = "正常"
    r["s8_summary.json"]["counts"]["物流异常"] = 0
    r["s8_summary.json"]["lists"]["物流异常"] = []
    r["s8_summary.json"]["counts"]["正常"] = 4
    r["s8_summary.json"]["lists"]["正常"].append("EF260803000004")
    r["final_stats.json"]["counts"] = copy.deepcopy(r["s8_summary.json"]["counts"])
    r["final_stats.json"]["lists_public"]["物流异常"] = []


def m10(r):
    """render · 成品件计数与数据源漂移（出表环节改数）"""
    r["final_stats.json"]["counts"]["质检异常"] = 2
    r["final_stats.json"]["lists_public"]["质检异常"].append("EF260803000004")


def m11(r):
    """partition · 两桶成员互换：计数、和、互斥、可枚举全部恒真

    这条是 §3 三条强断言之外的第四个面：守恒性质对「谁在哪个桶」零约束。
    只有按上游裁决重建成员才抓得到。
    """
    s8 = r["s8_summary.json"]
    s8["lists"]["质检异常"] = ["EF260803000004"]
    s8["lists"]["物流异常"] = ["EF260805000002"]
    fs = r["final_stats.json"]
    fs["lists_public"]["质检异常"] = ["EF260803000004"]
    fs["lists_public"]["物流异常"] = ["EF260805000002"]


def m12(r):
    """map · 入段漏判：s2 有的单在 s3 从未被分类（键集缺口）"""
    r["s3_groups.json"]["classified"] = [
        c for c in r["s3_groups.json"]["classified"] if c["id"] != "EF260802000009"]


def m13(r):
    """partition · 入集有的活单没进任何时效桶（并集不完整）"""
    r["s4_tiers.json"]["tiers"] = [
        t for t in r["s4_tiers.json"]["tiers"] if t["id"] != "EF260801000005"]


def m14(r):
    """map · 漏斗越位：上游已止步的单仍进本段（键集凭空多出）

    SKILL.md 第 9 行 · 被拦截即止步，不再进后续环节核查。0005 在第 5 步
    已判生产异常，不应出现在第 6 步。
    """
    r["s6_qc.json"]["results"].append(
        {"id": "EF260801000005", "observed_status": "质检不通过", "decision": "质检异常"})


def m15(r):
    """map · 漏斗丢单：上游 continue 的单未进本段"""
    r["s7_logistics.json"]["results"] = [
        x for x in r["s7_logistics.json"]["results"] if x["id"] != "EF260801000006"]


def m16(r):
    """aggregate · 计数与清单脱钩，但七类和仍 = N（守恒恒真）

    质检异常记 0（清单实有 1）、正常记 4（清单实有 3），和仍 = 7。
    total_reconciliation 对此零约束，只有逐桶明细重算抓得到。
    成品件按实际渲染路径同步计数（否则漂移被 T0 计数一致性挡在前面，
    检验的就不是这条了）。
    """
    s8 = r["s8_summary.json"]
    s8["counts"]["质检异常"] = 0
    s8["counts"]["正常"] = 4
    r["final_stats.json"]["counts"] = copy.deepcopy(s8["counts"])


def m17(r):
    """render · 成品件计数与数据源一致，但件内清单与计数打架

    counts 仍等于 s8（counts_match_source 恒真），只有件内明细—汇总
    对账抓得到。
    """
    r["final_stats.json"]["lists_public"]["质检异常"] = []


def m18(r):
    """filter · 出集把一条保留单复制一份（多重集重数增生）

    集合语义下这一形态完全隐形：出集的 id 集合仍是入集的子集，谓词重跑
    对每一行照样成立，两条最低族全绿。破的是重数——「筛选」不改变任何
    一行的份数。set 化把重数抹掉，恰好看不见这一种。

    删除计数同步减一以配平：不减则 excluded_count 也报错，旁落进来就分不清
    是重数被抓到还是配平被抓到。要验的是多重集那一条。

    旁落声明（真实依赖，不是判据松动）：多出来的这一行会沿管线一路走下去，
    故 s3.key_preservation、s8.total_reconciliation、
    final.claimed_total_match_source 三条也报。filter 段多出一行本就该在
    下游全部露头——旁落为零反倒说明下游没在看。credit 只记 s2.subset。
    """
    dup = copy.deepcopy(r["s2_filtered.json"]["orders"][0])
    r["s2_filtered.json"]["orders"].append(dup)
    r["s2_filtered.json"]["deleted_us"] -= 1


def m19(r):
    """filter · 保留行的非谓词字段被改写（sku 改了，country 没动）

    filter 的语义是筛选：保留行原样通过。改 sku 不碰谓词字段，故谓词重跑
    照样成立；id 集合没动，子集的集合面也成立；删除计数一行未动。三条最低族
    全过——除非子集族按**整行载荷**比对。改内容的已经不是 filter 了，是
    filter 混进了一次未申报的 map。
    """
    r["s2_filtered.json"]["orders"][1]["sku"] = "99999"


def m20(r):
    """map · 分组结果把一条复制一份（键集不变，行数变了）

    key_row_preservation 的族名写的是 key **与** row。只比键集时这一形态
    全绿：复制一行，键集一模一样。IR §3 该族挡的是「元素丢失或增生」，
    增生正是重数变化，用 set 恰好看不见。

    与 M12-classify-gap 咬同一条断言的两端：M12 是丢，本例是增。
    """
    dup = copy.deepcopy(r["s3_groups.json"]["classified"][0])
    r["s3_groups.json"]["classified"].append(dup)


def m21(r):
    """render · 成品件新增一个自报字段，没有任何断言读过它

    `pending_manual` 是成品件对外声称的一项数字，而契约里没有任何一条断言
    碰它：counts 对账读 counts，总量对账读 N_claimed，逐路径直连读
    lists_public 的各桶。它可以是任何数，全部断言照样 PASS——「其余全 PASS」
    在一个没被读过的字段上不成立任何结论。

    诱饵下在**同一 operation 的兄弟断言**里（final.counts_match_source 的
    `note: "pending_manual"`）：字面量扫描会认为该字段"被覆盖"，而没有任何
    求值器读过它。覆盖证据只能取解释器求值时实际记录的读取路径——与 M8 已经
    拒过的诱饵字符串同类。

    诱饵必须同 operation：覆盖集逐 operation 收（`covered` 在 op 循环内新建），
    下在别的段里的字面量根本进不到这条断言的判定视野，那样这条 mutant 只验了
    「新字段没人读」，没验「字面量不算读」。
    """
    r["final_stats.json"]["pending_manual"] = 2


def m22(r):
    """render · lists_public 下新增一个桶，兄弟桶全被逐一比对也覆盖不到它

    `待复核` 是 lists_public 下凭空多出的一个清单。它的六个兄弟桶各有一条
    整块比对断言，`lists_public` 这个路径名在六条谓词里都出现过——但没有
    任何一条读到这个新键。

    这一条咬的是覆盖判定的传递方向：整块比对（deep）向下传递覆盖，普通读取
    与兄弟节点的覆盖**不传递**。若按前缀认账，「lists_public 出现过」就会
    把它下面任何一个新桶都算成已覆盖，而清单里多出来的这一整桶从未被审过。
    counts 里没有对应项，故计数对账与明细—汇总对账都不报——只有覆盖那条能抓。
    """
    r["final_stats.json"]["lists_public"]["待复核"] = ["EF260899999999"]


def m23(r):
    """render · 成品件自报总量与上游脱钩

    N_claimed 是成品件对外声称的受理总量。把它改掉而 counts 与各清单一动
    不动：计数对账读 counts、逐桶对账读 lists_public，两侧都不碰这个数。
    总量只能出自汇总、不另算——这正是 render_source_replay 里
    `N_claimed → s8_summary.N_claimed` 那一条要钉住的。
    """
    r["final_stats.json"]["N_claimed"] = 99


def m25(r):
    """render · 总量沿链一致地漂：成品件与汇总件同改，直连比对看不见

    `final.render_source_replay` 只保证成品件的 N_claimed 等于汇总件的
    N_claimed。两处同改则这条恒等成立——直连是「成品件没在渲染时另算」的
    证据，不是「这个数对」的证据。链首那一端得另有人钉：
    `final.claimed_total_match_source` 把它对到 s2 段真实保留行数上，
    s8 段的断言一条都不读 N_claimed，故本形态只有它能抓。

    「至少直连」四个字里的「至少」就是这条 mutant 的位置：只做直连时，
    把总量整条链一起改写仍然全绿。
    """
    r["final_stats.json"]["N_claimed"] = 99
    r["s8_summary.json"]["N_claimed"] = 99


def m26(r):
    """acquire · 账本行内容与源表漂移，同行数与内容 hash 保持自洽"""
    target = "EF260805000001"
    for row in r["s1_export.json"]["rows"]:
        if row["id"] == target:
            row["created"] = "2099-01-01 00:00"
    # filter 产物同步承接改后的行，避免 s2.subset 旁落；本例只证 source_row_match。
    for row in r["s2_filtered.json"]["orders"]:
        if row["id"] == target:
            row["created"] = "2099-01-01 00:00"
    raw = json.dumps(r["s1_export.json"]["rows"], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":"))
    r["s1_export.json"]["rows_sha256"] = hashlib.sha256(
        raw.encode("utf-8")).hexdigest()[:16]


# 逐桶对账的定向 mutant 按桶生成：六条直连链形状相同、只差桶名，注入形态也
# 只差桶名。手抄六份除了抄错风险没有别的收益，故用工厂。六条链现由
# `final.render_source_replay` 一条断言统一承载，故六个 mutant 同指它。
#
# 注入是**换而不是加**：把该桶清单里的单号换成一个上游没有的、等长的号。加一条
# 会让清单长度变了，明细—汇总对账（读 len）随之报错，旁落进来就分不清是成员
# 比对抓到的还是长度抓到的。换等长号则长度不变、计数不变，只有逐路径精确相等
# 看得见——「清单长度相等」不约束成员是谁。
def _bucket_swap(bucket):
    def fn(r):
        lst = r["final_stats.json"]["lists_public"][bucket]
        if lst:
            lst[0] = "EF260899999999"
        else:
            # 空桶换不了，改成占位一条并把计数同步——计数不同步则长度那条也报
            r["final_stats.json"]["lists_public"][bucket] = ["EF260899999999"]
            r["final_stats.json"]["counts"][bucket] = 1
        return r
    fn.__doc__ = (f"render · 公开清单「{bucket}」的成员与汇总件对不上\n\n"
                  f"    换等长号不加号：清单长度与计数一动不动，明细—汇总对账（只读 len）\n"
                  f"    照样成立。清单长度相等不约束成员是谁——只有逐路径精确相等看得见。")
    return fn


PUBLIC_BUCKETS = ["生产异常", "质检异常", "物流异常", "属性异常", "无工单", "状态待判"]

MUTANTS = [
    ("M1-page-total-drift", "golden-task1", "acquire", "s1.count_hash", m1),
    ("M26-source-row-drift", "golden-task1", "acquire", "s1.source_rows", m26),
    ("M2-schema-field-missing", "golden-task1", "acquire", "s1.schema", m2),
    ("M3-phantom-order", "golden-task1", "filter", "s2.subset", m3),
    ("M4-country-leak", "golden-task1", "filter", "s2.predicate_replay", m4),
    ("M5-attr-observation-miscopy", "golden-task1", "map", "s3.attr_source_readback", m5),
    ("M6-tier-double-listed", "golden-task1", "partition", "s4.disjoint", m6),
    ("M7-prod-observation-miscopy", "golden-task1", "map", "s5.source_readback", m7),
    ("M8-logistics-complement-form", "golden-task1", "partition",
     "s7.enum_rule_replay", m8),
    ("M9-logistics-observation-miscopy", "golden-task1", "map",
     "s7.source_readback", m9),
    ("M10-render-count-drift", "golden-task1", "render", "final.counts_match_source", m10),
    ("M11-bucket-swap", "golden-task1", "aggregate", "s8.bucket_rebuild", m11),
    ("M12-classify-gap", "golden-task1", "map", "s3.key_preservation", m12),
    ("M13-tier-union-gap", "golden-task1", "partition", "s4.union", m13),
    ("M14-funnel-overstep", "golden-task1", "map", "s6.key_preservation", m14),
    ("M15-funnel-drop", "golden-task1", "map", "s7.key_preservation", m15),
    ("M16-count-list-decoupled", "golden-task1", "aggregate", "s8.detail_recomputation", m16),
    ("M17-render-summary-drift", "golden-task1", "render", "final.summary_reconciliation", m17),
    ("M18-filter-duplicate-row", "golden-task1", "filter", "s2.subset", m18),
    ("M19-filter-row-content-rewrite", "golden-task1", "filter", "s2.subset", m19),
    ("M20-map-duplicate-row", "golden-task1", "map", "s3.key_preservation", m20),
    ("M21-render-unread-field", "golden-task1", "render", "final.output_field_coverage", m21),
    ("M22-render-parent-prefix-only", "golden-task1", "render",
     "final.output_field_coverage", m22),
    ("M23-claimed-total-drift", "golden-task1", "render",
     "final.render_source_replay", m23),
    ("M25-claimed-total-chain-drift", "golden-task1", "render",
     "final.claimed_total_match_source", m25),
] + [(f"M24-public-list-{b}", "golden-task1", "render",
      "final.render_source_replay", _bucket_swap(b)) for b in PUBLIC_BUCKETS]

FILES = ["s1_export.json", "s2_filtered.json", "s3_groups.json", "s4_tiers.json",
         "s5_prod.json", "s6_qc.json", "s7_logistics.json", "s8_summary.json",
         "final_stats.json"]


def main():
    root = sys.argv[1]
    for mid, base, op, must_reject, fn in MUTANTS:
        src = os.path.join(root, base)
        dst = os.path.join(root, mid)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        run = {f: json.load(open(os.path.join(src, f), encoding="utf-8")) for f in FILES}
        fn(run)
        for f, obj in run.items():
            with open(os.path.join(dst, f), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=1)
        meta = {"mutant_id": mid, "baseline": base, "operation": op,
                "must_be_rejected_by": must_reject,
                "doc": (fn.__doc__ or "").strip()}
        with open(os.path.join(dst, "INJECTION.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
        print(f"built {mid}  op={op}  must_reject={must_reject}")


if __name__ == "__main__":
    main()
