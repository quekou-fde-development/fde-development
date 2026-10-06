#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_runs.py — Part 1 错误注入器。

嵌入 mock-task1 / mock-task3 的手工推导 golden（账本形态），
生成 golden 两个对照 run + E1-E9 九个带错 run。
每个 run = 一个目录，含 s1-s8 段级落盘 json + final_stats.json（终态统计件）。

带错 run 的错误按「真实错误传播」构造：错误发生段之后的所有下游段
与终态都与该错误自洽（一个真的跑错的执行体就会这样产出）。

用法: python3 make_runs.py <runs_root>
"""
import copy
import hashlib
import json
import os
import sys

D = "2026-08-05"


def content_hash(rows):
    """与 audit.py 的 _content_hash 同算法：规范化 JSON 后 sha256 取前 16 位。

    两边算法必须同一个，否则 golden 自己就对不上。count_hash 要的是
    「行数 + 内容指纹」两样——只落行数时，同行数改内容即无声通过。
    """
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def stamp_s1(run):
    """按 s1 当前的 rows 重算并写入 rows_sha256。

    注入器改完 s1 的行之后必须重跑一次：指纹是**产物的**指纹，不是 golden 的
    指纹。若只在 golden 上盖一次章、注入后不重算，那么任何动了 s1 行的 mutant
    都会被 count_hash 拒——而它本该由各自指名的那条断言拒，旁落项要显式登记，
    不能靠指纹兜底。反过来，故意冲 count_hash 的 mutant（改内容不改行数）必须
    **不**重算，才留得住那处不一致。
    """
    s1 = run["s1_export.json"]
    s1["rows_sha256"] = content_hash(s1["rows"])
    return run


def order(oid, country, sku, created):
    return {"id": oid, "country": country, "sku": sku, "created": created}


# ---------- golden task1（手工推导，见 fixtures/derivation.md） ----------

G1 = {}
G1["s1_export.json"] = {
    "page_total": 10,
    "rows": [
        order("EF260805000001", "中国发货", "30011", "2026-08-05 09:12"),
        order("EF260805000002", "中国发货", "30022", "2026-08-05 10:40"),
        order("EF260804000003", "中国发货", "30011", "2026-08-04 15:02"),
        order("EF260803000004", "中国发货", "30033", "2026-08-03 11:21"),
        order("EF260801000005", "中国发货", "30044", "2026-08-01 08:55"),
        order("EF260801000006", "中国发货", "30022", "2026-08-01 16:30"),
        order("EF260805000007", "美国发货", "30055", "2026-08-05 09:00"),
        order("EF260804000008", "美国发货", "30055", "2026-08-04 12:00"),
        order("", "", "", ""),
        order("EF260802000009", "中国发货", "30066", "2026-08-02 14:10"),
    ],
}
G1["s2_filtered.json"] = {
    "orders": [r for r in G1["s1_export.json"]["rows"] if r["country"] == "中国发货"],
    "deleted_us": 2,
    "deleted_blank": 1,
}
G1["s3_groups.json"] = {
    "classified": [
        {"id": "EF260805000001", "sku": "30011", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260805000002", "sku": "30022", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260804000003", "sku": "30011", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260803000004", "sku": "30033", "observed_attr": "委外", "group": "委外"},
        {"id": "EF260801000005", "sku": "30044", "observed_attr": "委外", "group": "委外"},
        {"id": "EF260801000006", "sku": "30022", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260802000009", "sku": "30066", "observed_attr": "外购", "group": "属性异常"},
    ]
}
G1["s4_tiers.json"] = {
    "exec_day": D,
    "tiers": [
        {"id": "EF260805000001", "group": "自制", "created": "2026-08-05 09:12", "tier": 1},
        {"id": "EF260805000002", "group": "自制", "created": "2026-08-05 10:40", "tier": 1},
        {"id": "EF260804000003", "group": "自制", "created": "2026-08-04 15:02", "tier": 2},
        {"id": "EF260803000004", "group": "委外", "created": "2026-08-03 11:21", "tier": 2},
        {"id": "EF260801000005", "group": "委外", "created": "2026-08-01 08:55", "tier": 3},
        {"id": "EF260801000006", "group": "自制", "created": "2026-08-01 16:30", "tier": 3},
    ],
}
G1["s5_prod.json"] = {
    "results": [
        {"id": "EF260805000001", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260805000002", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260804000003", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260803000004", "group": "委外", "observed": "全完成", "decision": "continue"},
        {"id": "EF260801000005", "group": "委外", "observed": "有未完成", "decision": "生产异常"},
        {"id": "EF260801000006", "group": "自制", "observed": "全完成", "decision": "continue"},
    ]
}
G1["s6_qc.json"] = {
    "results": [
        {"id": "EF260805000001", "observed_status": "质检完成", "decision": "continue"},
        {"id": "EF260805000002", "observed_status": "质检不通过", "decision": "质检异常"},
        {"id": "EF260804000003", "observed_status": "质检完成", "decision": "continue"},
        {"id": "EF260803000004", "observed_status": "工单完工待质检", "decision": "continue"},
        {"id": "EF260801000006", "observed_status": "质检完成", "decision": "continue"},
    ]
}
G1["s7_logistics.json"] = {
    "results": [
        {"id": "EF260805000001", "observed_status": "待确认", "decision": "正常"},
        {"id": "EF260804000003", "observed_status": "已发货", "decision": "正常"},
        {"id": "EF260803000004", "observed_status": "待建物流单", "decision": "物流异常"},
        {"id": "EF260801000006", "observed_status": "待确认", "decision": "正常"},
    ]
}
G1["s8_summary.json"] = {
    "counts": {"生产异常": 1, "质检异常": 1, "物流异常": 1,
               "属性异常": 1, "无工单": 0, "状态待判": 0, "正常": 3},
    "lists": {
        "生产异常": ["EF260801000005"],
        "质检异常": ["EF260805000002"],
        "物流异常": ["EF260803000004"],
        "属性异常": ["EF260802000009"],
        "无工单": [],
        "状态待判": [],
        "正常": ["EF260805000001", "EF260804000003", "EF260801000006"],
    },
    "N_claimed": 7,
}

# ---------- golden task3 ----------

G3 = {}
G3["s1_export.json"] = {
    "page_total": 5,
    "rows": [
        order("EF260805000021", "中国发货", "50011", "2026-08-05 08:30"),
        order("EF260803000022", "中国发货", "50022", "2026-08-03 09:00"),
        order("EF260728000023", "中国发货", "50011", "2026-07-28 10:00"),
        order("EF260805000024", "中国发货", "50033", "2026-08-05 11:00"),
        order("EF260803000025", "中国发货", "50033", "2026-08-03 16:00"),
    ],
}
G3["s2_filtered.json"] = {"orders": list(G3["s1_export.json"]["rows"]),
                          "deleted_us": 0, "deleted_blank": 0}
G3["s3_groups.json"] = {
    "classified": [
        {"id": "EF260805000021", "sku": "50011", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260803000022", "sku": "50022", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260728000023", "sku": "50011", "observed_attr": "自制", "group": "自制"},
        {"id": "EF260805000024", "sku": "50033", "observed_attr": "委外", "group": "委外"},
        {"id": "EF260803000025", "sku": "50033", "observed_attr": "委外", "group": "委外"},
    ]
}
G3["s4_tiers.json"] = {
    "exec_day": D,
    "tiers": [
        {"id": "EF260805000021", "group": "自制", "created": "2026-08-05 08:30", "tier": 1},
        {"id": "EF260803000022", "group": "自制", "created": "2026-08-03 09:00", "tier": 2},
        {"id": "EF260728000023", "group": "自制", "created": "2026-07-28 10:00", "tier": 3},
        {"id": "EF260805000024", "group": "委外", "created": "2026-08-05 11:00", "tier": 1},
        {"id": "EF260803000025", "group": "委外", "created": "2026-08-03 16:00", "tier": 2},
    ],
}
G3["s5_prod.json"] = {
    "results": [
        {"id": "EF260805000021", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260803000022", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260728000023", "group": "自制", "observed": "全完成", "decision": "continue"},
        {"id": "EF260805000024", "group": "委外", "observed": "查无", "decision": "continue"},
        {"id": "EF260803000025", "group": "委外", "observed": "查无", "decision": "continue"},
    ]
}
G3["s6_qc.json"] = {
    "results": [
        {"id": "EF260805000021", "observed_status": "质检完成", "decision": "continue"},
        {"id": "EF260803000022", "observed_status": "质检完成", "decision": "continue"},
        {"id": "EF260728000023", "observed_status": "质检完成", "decision": "continue"},
        {"id": "EF260805000024", "observed_status": "搜索无结果", "decision": "状态待判"},
        {"id": "EF260803000025", "observed_status": "搜索无结果", "decision": "状态待判"},
    ]
}
G3["s7_logistics.json"] = {
    "results": [
        {"id": "EF260805000021", "observed_status": "已取消", "decision": "正常"},
        {"id": "EF260803000022", "observed_status": "已建物流单", "decision": "物流异常"},
        {"id": "EF260728000023", "observed_status": "已签收", "decision": "正常"},
    ]
}
G3["s8_summary.json"] = {
    "counts": {"生产异常": 0, "质检异常": 0, "物流异常": 1,
               "属性异常": 0, "无工单": 0, "状态待判": 2, "正常": 2},
    "lists": {
        "生产异常": [], "质检异常": [],
        "物流异常": ["EF260803000022"],
        "属性异常": [], "无工单": [],
        "状态待判": ["EF260805000024", "EF260803000025"],
        "正常": ["EF260805000021", "EF260728000023"],
    },
    "N_claimed": 5,
}


def rebuild_s8(run):
    """按下游账本重建 s8（错误注入后保持终态与账本自洽）。"""
    s3 = run["s3_groups.json"]["classified"]
    s5 = run["s5_prod.json"]["results"]
    s6 = run["s6_qc.json"]["results"]
    s7 = run["s7_logistics.json"]["results"]
    lists = {
        "生产异常": [r["id"] for r in s5 if r["decision"] == "生产异常"],
        "质检异常": [r["id"] for r in s6 if r["decision"] == "质检异常"],
        "物流异常": [r["id"] for r in s7 if r["decision"] == "物流异常"],
        "属性异常": [r["id"] for r in s3 if r["group"] == "属性异常"],
        "无工单": [r["id"] for r in s5 if r["decision"] == "无工单"],
        "状态待判": [r["id"] for r in s6 if r["decision"] == "状态待判"]
                  + [r["id"] for r in s7 if r["decision"] == "状态待判"],
        "正常": [r["id"] for r in s7 if r["decision"] == "正常"],
    }
    run["s8_summary.json"] = {
        "counts": {k: len(v) for k, v in lists.items()},
        "lists": lists,
        "N_claimed": len(run["s2_filtered.json"]["orders"]),
    }


def drop_downstream(run, oid, from_seg):
    """把 oid 从 from_seg 及之后的段账本中移除（模拟中途被错误拦截/丢失后自洽传播）。"""
    segs = ["s5_prod.json", "s6_qc.json", "s7_logistics.json"]
    for seg in segs[segs.index(from_seg):]:
        run[seg]["results"] = [r for r in run[seg]["results"] if r["id"] != oid]


def build_runs():
    runs = {"golden-task1": copy.deepcopy(G1), "golden-task3": copy.deepcopy(G3)}

    # E1 复刻 bug A：质检白名单比对恒 False → 进第 6 步的单全部判质检异常
    r = copy.deepcopy(G1)
    for rec in r["s6_qc.json"]["results"]:
        rec["decision"] = "质检异常"
    r["s7_logistics.json"]["results"] = []
    rebuild_s8(r)
    runs["E1-whitelist-always-false"] = r

    # E2 复刻 bug B：TODAY_START 差 18h40m → 0003 (08-04) 被划进当日组
    r = copy.deepcopy(G1)
    for t in r["s4_tiers.json"]["tiers"]:
        if t["id"] == "EF260804000003":
            t["tier"] = 1
    rebuild_s8(r)
    runs["E2-today-start-shift"] = r

    # E3 第 2 步静默丢单：0009 在筛选中丢失（删除计数未变），全下游自洽于 6 单
    r = copy.deepcopy(G1)
    r["s2_filtered.json"]["orders"] = [
        o for o in r["s2_filtered.json"]["orders"] if o["id"] != "EF260802000009"]
    r["s3_groups.json"]["classified"] = [
        c for c in r["s3_groups.json"]["classified"] if c["id"] != "EF260802000009"]
    rebuild_s8(r)
    runs["E3-silent-row-drop"] = r

    # E4 第 3 步记录矛盾：0004 观测值委外（正确）但归组自制
    r = copy.deepcopy(G1)
    for c in r["s3_groups.json"]["classified"]:
        if c["id"] == "EF260803000004":
            c["group"] = "自制"
    for t in r["s4_tiers.json"]["tiers"]:
        if t["id"] == "EF260803000004":
            t["group"] = "自制"
    for rec in r["s5_prod.json"]["results"]:
        if rec["id"] == "EF260803000004":
            rec["group"] = "自制"
    rebuild_s8(r)
    runs["E4-attr-route-contradiction"] = r

    # E5 第 5 步漏查一单：0006 从第 5 步起消失（管道丢失，终态计数和 6 ≠ N 7）
    r = copy.deepcopy(G1)
    drop_downstream(r, "EF260801000006", "s5_prod.json")
    rebuild_s8(r)
    r["s8_summary.json"]["N_claimed"] = 7
    runs["E5-pipeline-drop"] = r

    # E6 第 6 步白名单缩水：工单完工待质检 被判异常 → 0004 止步
    r = copy.deepcopy(G1)
    for rec in r["s6_qc.json"]["results"]:
        if rec["id"] == "EF260803000004":
            rec["decision"] = "质检异常"
    drop_downstream(r, "EF260803000004", "s7_logistics.json")
    rebuild_s8(r)
    runs["E6-whitelist-shrunk"] = r

    # E7 第 8 步重计：0004 同时留在质检异常与物流异常两份清单（计数和 8 ≠ 7）
    r = copy.deepcopy(G1)
    rebuild_s8(r)
    r["s8_summary.json"]["lists"]["质检异常"].append("EF260803000004")
    r["s8_summary.json"]["counts"]["质检异常"] += 1
    runs["E7-double-count"] = r

    # E8 (task3) 路由反转：委外查无工单 → 误判无工单清单（应直通质检）
    r = copy.deepcopy(G3)
    for rec in r["s5_prod.json"]["results"]:
        if rec["observed"] == "查无" and rec["group"] == "委外":
            rec["decision"] = "无工单"
    for oid in ["EF260805000024", "EF260803000025"]:
        drop_downstream(r, oid, "s6_qc.json")
    rebuild_s8(r)
    runs["E8-outsource-route-reversal"] = r

    # E9 正常数由守恒反推而非追踪：无正常清单，计数 = N - 其余六类之和
    r = copy.deepcopy(G1)
    rebuild_s8(r)
    others = sum(v for k, v in r["s8_summary.json"]["counts"].items() if k != "正常")
    r["s8_summary.json"]["lists"]["正常"] = None
    r["s8_summary.json"]["counts"]["正常"] = r["s8_summary.json"]["N_claimed"] - others
    r["s8_summary.json"]["derivation_note"] = "正常计数按 N - 其余六类反推，无逐单追踪"
    runs["E9-forced-balance"] = r

    # E10 观测抄录错误：0002 的子订单状态记成 质检完成（源表=质检不通过），
    # 裁决与观测自洽（continue），下游照常 → 段内断言按设计失明，只有源重读能抓
    r = copy.deepcopy(G1)
    for rec in r["s6_qc.json"]["results"]:
        if rec["id"] == "EF260805000002":
            rec["observed_status"] = "质检完成"
            rec["decision"] = "continue"
    r["s7_logistics.json"]["results"].append(
        {"id": "EF260805000002", "observed_status": "搜索无结果", "decision": "状态待判"})
    rebuild_s8(r)
    runs["E10-observation-miscopy"] = r

    # 全部 run 统一盖 s1 内容指纹。本套 E1-E10 无一注入动 s1 的行（错都发生在
    # s2 及以后），故各 run 的 s1 与 golden 逐字相同，统一重算即可。
    # 将来若加冲 count_hash 的注入（改 s1 行内容而不改行数），那一个必须跳过
    # 本步——指纹要留住那处不一致，否则它自己把自己修好了。
    for r in runs.values():
        stamp_s1(r)

    return runs


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "runs"
    runs = build_runs()
    for name, run in runs.items():
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        for fname, payload in run.items():
            with open(os.path.join(d, fname), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
        # 终态统计件 = s8 的对外投影（现役包唯一可审面）
        s8 = run["s8_summary.json"]
        final = {"counts": s8["counts"], "N_claimed": s8["N_claimed"],
                 "lists_public": {k: v for k, v in s8["lists"].items()
                                  if k != "正常" and v is not None}}
        with open(os.path.join(d, "final_stats.json"), "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=1)
    print(f"generated {len(runs)} runs under {root}")


if __name__ == "__main__":
    main()
