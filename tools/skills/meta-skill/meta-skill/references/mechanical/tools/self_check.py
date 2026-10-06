#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self_check.py — order-aging-query 段级账本机械审核器（B 包运行期闸）。

三层审面，各自独立可跑：
  T0 --tier 0  现役可审面：只读 final_stats.json（七类和=N + 清单长度=计数）
  T1 --tier 1  段级账本断言：读 s1-s8 账本，验分割守恒 / 流转集合 / 规则函数 / 重建一致
  T2 --tier 2  源表重读：读 mock 表源文件，逐条比对账本 observed 值 vs 源表机械重读值

用法:
  python3 self_check.py <run_dir> --tier 0
  python3 self_check.py <run_dir> --tier 1
  python3 self_check.py <run_dir> --tier 2 --source <mock-task.md>
输出: JSON 报告到 stdout；有 FAIL → exit 1，全 PASS → exit 0。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

QC_WHITELIST = {"质检完成", "工单完工待质检"}
LOGI_NORMAL = {"已发货", "已签收", "已取消", "已归档", "待确认"}
LOGI_ABNORMAL = {"待建物流单", "已建物流单", "物流单生成失败"}
BUCKETS = ["生产异常", "质检异常", "物流异常", "属性异常", "无工单", "状态待判", "正常"]


def load(run_dir, name):
    p = os.path.join(run_dir, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Report:
    def __init__(self):
        self.items = []

    def check(self, aid, ok, detail=""):
        self.items.append({"assert": aid, "status": "PASS" if ok else "FAIL",
                           "detail": detail if not ok else ""})

    @property
    def failed(self):
        return [i for i in self.items if i["status"] == "FAIL"]


# ---------------- T0 现役可审面 ----------------

def tier0(run_dir, rep):
    fs = load(run_dir, "final_stats.json")
    if fs is None:
        rep.check("T0.exists", False, "final_stats.json 缺失")
        return
    total = sum(fs["counts"].values())
    rep.check("T0.sum==N", total == fs["N_claimed"],
              f"七类和={total} vs N={fs['N_claimed']}")
    for k, lst in fs.get("lists_public", {}).items():
        rep.check(f"T0.len({k})==count", len(lst) == fs["counts"].get(k, -1),
                  f"清单长={len(lst)} vs 计数={fs['counts'].get(k)}")


# ---------------- T1 段级账本断言 ----------------

def expected_tier_of(created, exec_day):
    d = date.fromisoformat(created.split()[0])
    e = date.fromisoformat(exec_day)
    diff = (e - d).days
    if diff < 0:
        return None  # 创建时间在执行日之后 = 数据异常
    if diff == 0:
        return 1
    if diff in (1, 2):
        return 2
    return 3


def tier1(run_dir, rep):
    s1 = load(run_dir, "s1_export.json")
    s2 = load(run_dir, "s2_filtered.json")
    s3 = load(run_dir, "s3_groups.json")
    s4 = load(run_dir, "s4_tiers.json")
    s5 = load(run_dir, "s5_prod.json")
    s6 = load(run_dir, "s6_qc.json")
    s7 = load(run_dir, "s7_logistics.json")
    s8 = load(run_dir, "s8_summary.json")
    for name, obj in [("s1", s1), ("s2", s2), ("s3", s3), ("s4", s4),
                      ("s5", s5), ("s6", s6), ("s7", s7), ("s8", s8)]:
        if obj is None:
            rep.check(f"T1.{name}.exists", False, f"{name} 账本缺失")
    if rep.failed:
        return

    # s1→s2 分割守恒：保留 + 删美国 + 删空白 = 页面总数；保留侧唯一发货国
    kept = len(s2["orders"])
    part = kept + s2["deleted_us"] + s2["deleted_blank"]
    rep.check("T1.s2.partition", part == s1["page_total"],
              f"保留{kept}+美国{s2['deleted_us']}+空白{s2['deleted_blank']}={part} vs 页面总数{s1['page_total']}")
    bad_country = [o["id"] for o in s2["orders"] if o["country"] != "中国发货"]
    rep.check("T1.s2.uniq-country", not bad_country, f"非中国发货混入: {bad_country}")

    s2_ids = {o["id"] for o in s2["orders"]}

    # s2→s3 流转集合 + 属性→组 纯函数
    s3_ids = {c["id"] for c in s3["classified"]}
    rep.check("T1.s3.ids==s2", s3_ids == s2_ids,
              f"缺{sorted(s2_ids - s3_ids)} 多{sorted(s3_ids - s2_ids)}")
    for c in s3["classified"]:
        want = {"自制": "自制", "委外": "委外"}.get(c["observed_attr"], "属性异常")
        rep.check(f"T1.s3.rule[{c['id']}]", c["group"] == want,
                  f"观测属性={c['observed_attr']} → 应归{want}，实归{c['group']}")

    # s3→s4 流转 + 自然日分组函数
    live_ids = {c["id"] for c in s3["classified"] if c["group"] in ("自制", "委外")}
    s4_ids = {t["id"] for t in s4["tiers"]}
    rep.check("T1.s4.ids==live", s4_ids == live_ids,
              f"缺{sorted(live_ids - s4_ids)} 多{sorted(s4_ids - live_ids)}")
    for t in s4["tiers"]:
        want = expected_tier_of(t["created"], s4["exec_day"])
        rep.check(f"T1.s4.rule[{t['id']}]", t["tier"] == want,
                  f"created={t['created']} exec_day={s4['exec_day']} → 应组{want}，实组{t['tier']}")

    # s4→s5 流转 + 生产规则函数
    s5_ids = {r["id"] for r in s5["results"]}
    rep.check("T1.s5.ids==s4", s5_ids == s4_ids,
              f"缺{sorted(s4_ids - s5_ids)} 多{sorted(s5_ids - s4_ids)}")
    for r in s5["results"]:
        if r["observed"] == "全完成":
            want = "continue"
        elif r["observed"] == "有未完成":
            want = "生产异常"
        elif r["observed"] == "查无":
            want = "continue" if r["group"] == "委外" else "无工单"
        else:
            want = None
        rep.check(f"T1.s5.rule[{r['id']}]", r["decision"] == want,
                  f"观测={r['observed']} 组={r['group']} → 应{want}，实{r['decision']}")

    # s5→s6 流转 + 质检白名单函数
    cont5 = {r["id"] for r in s5["results"] if r["decision"] == "continue"}
    s6_ids = {r["id"] for r in s6["results"]}
    rep.check("T1.s6.ids==cont5", s6_ids == cont5,
              f"缺{sorted(cont5 - s6_ids)} 多{sorted(s6_ids - cont5)}")
    for r in s6["results"]:
        st = r["observed_status"]
        if st in QC_WHITELIST:
            want = "continue"
        elif st == "搜索无结果":
            want = "状态待判"
        else:
            want = "质检异常"
        rep.check(f"T1.s6.rule[{r['id']}]", r["decision"] == want,
                  f"观测状态={st} → 应{want}，实{r['decision']}")

    # s6→s7 流转 + 物流封闭枚举函数
    cont6 = {r["id"] for r in s6["results"] if r["decision"] == "continue"}
    s7_ids = {r["id"] for r in s7["results"]}
    rep.check("T1.s7.ids==cont6", s7_ids == cont6,
              f"缺{sorted(cont6 - s7_ids)} 多{sorted(s7_ids - cont6)}")
    for r in s7["results"]:
        st = r["observed_status"]
        if st in LOGI_NORMAL:
            want = "正常"
        elif st in LOGI_ABNORMAL:
            want = "物流异常"
        else:
            want = "状态待判"
        rep.check(f"T1.s7.rule[{r['id']}]", r["decision"] == want,
                  f"观测状态={st} → 应{want}，实{r['decision']}")

    # s8 重建一致：七桶全部由账本重建，与 s8 自报逐桶比对
    rebuilt = {
        "生产异常": {r["id"] for r in s5["results"] if r["decision"] == "生产异常"},
        "无工单": {r["id"] for r in s5["results"] if r["decision"] == "无工单"},
        "质检异常": {r["id"] for r in s6["results"] if r["decision"] == "质检异常"},
        "物流异常": {r["id"] for r in s7["results"] if r["decision"] == "物流异常"},
        "属性异常": {c["id"] for c in s3["classified"] if c["group"] == "属性异常"},
        "状态待判": {r["id"] for r in s6["results"] if r["decision"] == "状态待判"}
                  | {r["id"] for r in s7["results"] if r["decision"] == "状态待判"},
        "正常": {r["id"] for r in s7["results"] if r["decision"] == "正常"},
    }
    for b in BUCKETS:
        claimed = s8["lists"].get(b)
        if claimed is None:
            rep.check(f"T1.s8.trace[{b}]", False, f"{b} 桶无逐单清单（不可追踪，疑守恒反推）")
            continue
        rep.check(f"T1.s8.rebuild[{b}]", set(claimed) == rebuilt[b],
                  f"自报{sorted(claimed)} vs 账本重建{sorted(rebuilt[b])}")
        rep.check(f"T1.s8.count[{b}]", s8["counts"][b] == len(claimed),
                  f"计数{s8['counts'][b]} vs 清单长{len(claimed)}")

    # 互斥 + 域完整：每单恰好落一桶；N 对账 s2
    all_claimed = [oid for b in BUCKETS for oid in (s8["lists"].get(b) or [])]
    dupes = sorted({x for x in all_claimed if all_claimed.count(x) > 1})
    rep.check("T1.s8.exclusive", not dupes, f"重复落桶: {dupes}")
    union = set(all_claimed)
    rep.check("T1.s8.domain", union == s2_ids,
              f"漏单{sorted(s2_ids - union)} 幽灵单{sorted(union - s2_ids)}")
    rep.check("T1.s8.N==len(s2)", s8["N_claimed"] == len(s2["orders"]),
              f"N_claimed={s8['N_claimed']} vs s2 实际{len(s2['orders'])}")


# ---------------- T2 源表机械重读 ----------------

def parse_tables(src_path):
    with open(src_path, encoding="utf-8") as f:
        text = f.read()
    tables = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r"^##\s+表\s+([A-E])", line)
        if m:
            cur = m.group(1)
            tables[cur] = []
            continue
        if cur and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and any(cells) and all(re.fullmatch(r"-+", x) for x in cells if x):
                continue
            tables[cur].append(cells)
    out = {}
    for key, rows in tables.items():
        out[key] = rows[1:] if rows else []  # 掉表头
    return out


def normalize_b(cell):
    if "查询无结果" in cell:
        return "查无"
    if ":未完成" in cell or "：未完成" in cell:
        return "有未完成"
    return "全完成"


def tier2(run_dir, src_path, rep):
    t = parse_tables(src_path)
    s1 = load(run_dir, "s1_export.json")
    s3 = load(run_dir, "s3_groups.json")
    s5 = load(run_dir, "s5_prod.json")
    s6 = load(run_dir, "s6_qc.json")
    s7 = load(run_dir, "s7_logistics.json")

    # s1 vs 表A：行多重集一致 + 页面总数
    src_rows = sorted(tuple(r[:4]) for r in t.get("A", []))
    led_rows = sorted((o["id"], o["country"], o["sku"], o["created"])
                      for o in s1["rows"])
    rep.check("T2.s1.rows==表A", src_rows == led_rows,
              f"账本 {len(led_rows)} 行与源表 {len(src_rows)} 行内容不符")
    rep.check("T2.s1.page_total", s1["page_total"] == len(src_rows),
              f"page_total={s1['page_total']} vs 源表行数{len(src_rows)}")

    # s3 vs 表E
    attr = {r[0]: r[1] for r in t.get("E", []) if r[0]}
    for c in s3["classified"]:
        src = attr.get(c["sku"], "（表E无此SKU）")
        rep.check(f"T2.s3.obs[{c['id']}]", c["observed_attr"] == src,
                  f"账本观测={c['observed_attr']} vs 源表E={src}")

    # s5 vs 表B
    prod = {r[0]: normalize_b(r[1]) for r in t.get("B", []) if r[0]}
    for r in s5["results"]:
        src = prod.get(r["id"], "查无")
        rep.check(f"T2.s5.obs[{r['id']}]", r["observed"] == src,
                  f"账本观测={r['observed']} vs 源表B={src}")

    # s6 vs 表C（缺行 = 搜索无结果）
    qc = {r[0]: r[1] for r in t.get("C", []) if r[0]}
    for r in s6["results"]:
        src = qc.get(r["id"], "搜索无结果")
        if src.startswith("（"):
            src = "搜索无结果"
        rep.check(f"T2.s6.obs[{r['id']}]", r["observed_status"] == src,
                  f"账本观测={r['observed_status']} vs 源表C={src}")

    # s7 vs 表D（缺行 = 搜索无结果）
    logi = {r[0]: r[1] for r in t.get("D", []) if r[0]}
    for r in s7["results"]:
        src = logi.get(r["id"], "搜索无结果")
        rep.check(f"T2.s7.obs[{r['id']}]", r["observed_status"] == src,
                  f"账本观测={r['observed_status']} vs 源表D={src}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--tier", type=int, required=True, choices=[0, 1, 2])
    ap.add_argument("--source", help="T2 源表文件（mock-task .md）")
    args = ap.parse_args()

    rep = Report()
    if args.tier == 0:
        tier0(args.run_dir, rep)
    elif args.tier == 1:
        tier1(args.run_dir, rep)
    else:
        if not args.source:
            print("T2 需要 --source", file=sys.stderr)
            sys.exit(2)
        tier2(args.run_dir, args.source, rep)

    out = {"run": os.path.basename(os.path.normpath(args.run_dir)),
           "tier": args.tier,
           "n_asserts": len(rep.items),
           "n_fail": len(rep.failed),
           "verdict": "FAIL" if rep.failed else "PASS",
           "failures": rep.failed}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
