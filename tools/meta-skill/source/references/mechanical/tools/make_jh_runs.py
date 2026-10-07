#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_jh_runs.py — join / handoff 两个 operation 的验收料。

存在理由：主套件（oaq 九段）里没有 join 与 handoff 形态，这两类的最低谓词族
（key_coverage/cardinality/unmatched_set/joined_value_replay、artifact_hash/
schema_conformance/receiver_receipt）因而从未被证伪过——词汇表里写着，验收
矩阵里是空的。声明了但没被拒过的族不构成防线，与没写等价。

造一个正例 + 八个定向 mutant，每个 mutant 只冲一族：
  J1 join-drop-silent      单子既不在 joined 也不在 unmatched → key_coverage
  J2 join-fanout           右表重键致左键在 joined 出现两次   → cardinality
  J3 unmatched-unlogged    未匹配集合只记数不记名单          → unmatched_set
  J4 fee-swap              两个已连接键的右表载荷互换        → joined_value_replay
                           （键形状一字未动，前三条全绿）
  J5 false-unmatched       右表确有匹配的键被挪进未匹配名单  → unmatched_set
                           （不相交成立、左集成员成立、joined 里剩下的行也都对）
  R1 fee-type-drift        右表费率由数值变字符串            → schema_conformance
  R2 fee-receipt-missing   右表取数回执缺取数时刻            → source_receipt
  R3 fee-content-drift     行数不变、改一条费率的值          → count_hash
                           （只比 len 时全绿——指纹落账为它而在）
  H1 payload-hash-drift    交接物内容变了、账本记的哈希没变  → artifact_hash
  H2 intake-schema-gap     接回的行缺必填字段                → schema_conformance
  H3 receipt-missing       接收回执关键字段空                → receiver_receipt

用法: python3 make_jh_runs.py <runs_root> <contract_out>
"""
import copy
import hashlib
import json
import os
import shutil
import sys

# ---------------------------------------------------------------- 正例数据

# 外部（财务）交接回来的费率单：交接物本体 + 账本里的接收回执。
PAYLOAD_ROWS = [
    ("EF260805000001", "30011"),
    ("EF260805000002", "30022"),
    ("EF260804000003", "30011"),
    ("EF260803000004", "30033"),
    ("EF260801000005", "30044"),
    ("EF260801000006", "30022"),
]

# 内部费率表：30044 故意缺——未匹配是常态，必须被登记而不是被吞掉。
FEE_TABLE = {"30011": 12.0, "30022": 8.5, "30033": 20.0}


def payload_csv():
    lines = ["id,sku"] + [f"{i},{s}" for i, s in PAYLOAD_ROWS]
    return "\n".join(lines) + "\n"


def sha16(data):
    """与 audit.py 的 sha256_file 同算法：sha256 取前 16 位十六进制。"""
    return hashlib.sha256(data).hexdigest()[:16]


def content_hash(rows):
    """与 audit.py 的 _content_hash 同算法：规范化 JSON 后 sha256 取前 16 位。

    count_hash 要的是「行数 + 内容指纹」两样；两边算法必须同一个，
    否则 golden 自己就对不上。
    """
    canon = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def golden():
    body = payload_csv()
    rows = [{"id": i, "sku": s} for i, s in PAYLOAD_ROWS]
    intake = {
        "source_id": "finance-fee-2026W32",
        "received_at": "2026-08-07T09:30:00",
        "receiver": "夏洛克",
        "payload_file": "h0_payload.csv",
        "payload_sha256": sha16(body.encode("utf-8")),
        "rows": rows,
    }
    joined, unmatched = [], []
    for r in rows:
        if r["sku"] in FEE_TABLE:
            joined.append({"id": r["id"], "sku": r["sku"], "fee": FEE_TABLE[r["sku"]]})
        else:
            unmatched.append(r["id"])
    # 右表落成独立产物：joined_value_replay 与 unmatched_set 的重算都要回查它。
    # 右表若只以 fee_table 字典嵌在产物里，「回右表查」就成了拿产物验产物。
    right_rows = [{"sku": k, "fee": v} for k, v in sorted(FEE_TABLE.items())]
    right = {"source_id": "internal-fee-table-v3",
             "fetched_at": "2026-08-07T09:28:00",
             "row_count": len(right_rows),
             "rows_sha256": content_hash(right_rows),
             "rows": right_rows}
    j1 = {"joined": joined, "unmatched_ids": unmatched,
          "unmatched_count": len(unmatched)}
    return {"h0_payload.csv": body, "h0_intake.json": intake,
            "r0_fee_table.json": right, "j1_joined.json": j1}


# ---------------------------------------------------------------- 定向注入

def j1_drop(run):
    """左键凭空消失：既不在 joined，也不进 unmatched 名单。"""
    j = run["j1_joined.json"]
    j["joined"] = [x for x in j["joined"] if x["id"] != "EF260804000003"]


def j2_fanout(run):
    """右表重键 → 左键一对多放大。总额随之虚增，是 join 最常见的错法。

    复制行的 fee 与原行保持一致：只冲基数这一条，不顺带把取值也弄错。
    一个 mutant 冲一族，混着坏则「被哪条拒的」说不清。
    """
    j = run["j1_joined.json"]
    dup = dict(j["joined"][0])
    j["joined"].insert(1, dup)


def j3_unlogged(run):
    """未匹配只记数不记名单——数对得上，具体是谁查不出来。"""
    j = run["j1_joined.json"]
    j.pop("unmatched_ids")


def j4_fee_swap(run):
    """两个已连接键的右表载荷互换：键形状一字未动，取值全错。

    key_coverage 仍覆盖全部左键、cardinality 仍一对一、unmatched_set 仍与
    重算的应未匹配集全等——三条键形状断言全绿。「连对了行」与「取对了值」
    正交，故必须有一条逐键回右表查值的断言。
    """
    j = run["j1_joined.json"]
    a, b = None, None
    for x in j["joined"]:
        if x["sku"] == "30011" and a is None:
            a = x
        elif x["sku"] == "30022" and b is None:
            b = x
    a["fee"], b["fee"] = b["fee"], a["fee"]


def j5_false_unmatched(run):
    """右表确有匹配的键，被从 joined 挪进 unmatched_ids。

    key_coverage 仍覆盖它（未匹配也算覆盖）、cardinality 只看 joined、
    未匹配清单与 joined 不相交且都出自左集、joined_value_replay 只管还留在
    joined 里的行——每一条都成立。识破它只能靠按左右两侧连接键**重算**
    应未匹配集，与账本记的逐项比。
    """
    j = run["j1_joined.json"]
    victim = j["joined"].pop(0)
    j["unmatched_ids"].append(victim["id"])
    j["unmatched_count"] = len(j["unmatched_ids"])


def h1_hash_drift(run):
    """交接物被改（多一行），账本里记的哈希还是旧的。"""
    run["h0_payload.csv"] += "EF260899999999,30099\n"


def h2_schema_gap(run):
    """接回的行缺 sku——字段级残缺，行数对得上。"""
    run["h0_intake.json"]["rows"][2] = {"id": "EF260804000003"}


def h3_receipt_missing(run):
    """接收回执没记接收人：出了问题找不到人，交接等于没交接。"""
    run["h0_intake.json"]["receiver"] = ""


def r1_fee_type_drift(run):
    """右表费率由数值变字符串——字段名在、类型漂。

    只验「键在不在」时全绿，一路带到汇总才炸，且炸在别处。
    """
    run["r0_fee_table.json"]["rows"][0]["fee"] = "12.0"


def r2_receipt_missing(run):
    """取数回执缺取数时刻——「这批数是什么时候的」无从回答。"""
    run["r0_fee_table.json"]["fetched_at"] = ""


def r3_content_drift(run):
    """行数不变、内容改了：改一条费率的数值，row_count 一动不动。

    count_hash 若只比 len，这条全绿——「取回来的还是那批数据」这一问
    从未被回答过。指纹落账正是为它而在。
    """
    run["r0_fee_table.json"]["rows"][0]["fee"] = 99.0


MUTANTS = [
    ("J1-join-drop-silent", "join", "j1.key_coverage", j1_drop, []),
    ("J2-join-fanout", "join", "j1.cardinality", j2_fanout, []),
    # unmatched_ids 整个字段被删时 key_coverage 也读不到该路径而 FAIL——
    # 两条断言本就共用这一字段。登记仍只指 unmatched_set，旁落项显式列出，
    # 不借旁落充数（判据是「被它登记的那条拒」）。
    ("J3-unmatched-unlogged", "join", "j1.unmatched_set", j3_unlogged,
     ["j1.key_coverage"]),
    ("J4-fee-swap", "join", "j1.joined_value_replay", j4_fee_swap, []),
    ("J5-false-unmatched", "join", "j1.unmatched_set", j5_false_unmatched, []),
    ("R1-fee-type-drift", "acquire", "r0.schema_conformance", r1_fee_type_drift,
     ["r0.count_hash", "j1.joined_value_replay"]),
    ("R2-fee-receipt-missing", "acquire", "r0.source_receipt", r2_receipt_missing, []),
    ("R3-fee-content-drift", "acquire", "r0.count_hash", r3_content_drift,
     ["j1.joined_value_replay"]),
    ("H1-payload-hash-drift", "handoff", "h0.artifact_hash", h1_hash_drift, []),
    ("H2-intake-schema-gap", "handoff", "h0.schema_conformance", h2_schema_gap,
     ["j1.unmatched_set"]),
    ("H3-receipt-missing", "handoff", "h0.receiver_receipt", h3_receipt_missing, []),
]


# ---------------------------------------------------------------- 契约

def contract():
    def a(aid, fam, tier, pred, mutants):
        return {"id": aid, "family": fam, "tier": tier, "predicate": pred,
                "derived_fields": [], "source_anchor": "fixtures/jh_rules.md §交接与合并规则",
                "mutants": mutants}

    LEFT = {"stage": "h0_intake", "artifact": "h0_intake.json",
            "collection": "rows", "id_field": "id"}
    RIGHT = {"stage": "r0_fee_table", "artifact": "r0_fee_table.json",
             "collection": "rows", "key_field": "sku"}

    return {
        "package": "jh-suite",
        "contract_ir_version": "1.0",
        "stages": [
            {"stage": "h0_intake", "operations": [{
                "op": "handoff", "artifact": "h0_intake.json",
                "source_reachability": "human_handoff",
                "assertions": [
                    a("h0.artifact_hash", "artifact_hash", 1,
                      {"artifact_path": "h0_payload.csv", "declared_hash": "payload_sha256"},
                      ["H1-payload-hash-drift"]),
                    a("h0.schema_conformance", "schema_conformance", 1,
                      {"collection": "rows", "required_fields": ["id", "sku"],
                       "field_types": {"id": "str", "sku": "str"}},
                      ["H2-intake-schema-gap"]),
                    a("h0.receiver_receipt", "receiver_receipt", 1,
                      {"required_keys": ["source_id", "received_at", "receiver"]},
                      ["H3-receipt-missing"]),
                ]}]},
            # 右表自成一段：joined_value_replay 与 unmatched_set 的重算都回查它。
            # 它登记为 acquire，故必须齐 acquire 的三条最低族，每条各带定向
            # mutant——测试料本身不能是一份违反 IR 的契约，否则拿它证出来的
            # 「闸有效」立不住。
            {"stage": "r0_fee_table", "operations": [{
                "op": "acquire", "artifact": "r0_fee_table.json",
                "source_reachability": "machine",
                "assertions": [
                    a("r0.source_receipt", "source_receipt", 1,
                      {"required_keys": ["source_id", "fetched_at"]},
                      ["R2-fee-receipt-missing"]),
                    a("r0.schema_conformance", "schema_conformance", 1,
                      {"collection": "rows", "required_fields": ["sku", "fee"],
                       "field_types": {"sku": "str", "fee": "number"}},
                      ["R1-fee-type-drift"]),
                    a("r0.count_hash", "count_hash", 1,
                      {"collection": "rows", "declared_count": "row_count",
                       "declared_hash": "rows_sha256"},
                      ["R3-fee-content-drift"]),
                ]}]},
            {"stage": "j1_joined", "operations": [{
                "op": "join", "artifact": "j1_joined.json",
                "source_reachability": "machine",
                "assertions": [
                    a("j1.key_coverage", "key_coverage", 1,
                      {"input": LEFT,
                       "output": {"collection": "joined", "id_field": "id"},
                       "unmatched_ids": "unmatched_ids"},
                      ["J1-join-drop-silent"]),
                    a("j1.cardinality", "cardinality", 1,
                      {"collection": "joined", "key_field": "id", "expect": "one_to_one"},
                      ["J2-join-fanout"]),
                    a("j1.unmatched_set", "unmatched_set", 1,
                      {"field": "unmatched_ids",
                       "output": {"collection": "joined", "id_field": "id"},
                       "input": LEFT, "right": RIGHT, "join_key": "sku"},
                      ["J3-unmatched-unlogged", "J5-false-unmatched"]),
                    a("j1.joined_value_replay", "joined_value_replay", 1,
                      {"collection": "joined", "key_field": "id", "join_key": "sku",
                       "right": RIGHT, "value_fields": {"fee": "fee"}},
                      ["J4-fee-swap"]),
                ]}]},
        ],
    }


def write_run(root, name, run):
    d = os.path.join(root, name)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for fn, obj in run.items():
        path = os.path.join(d, fn)
        if fn.endswith(".csv"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(obj)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
    return d


def main():
    root, contract_out = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    write_run(root, "golden-jh", golden())
    print("built golden-jh")

    for mid, op, must, fn, also in MUTANTS:
        run = copy.deepcopy(golden())
        fn(run)
        d = write_run(root, mid, run)
        meta = {"mutant_id": mid, "baseline": "golden-jh", "operation": op,
                "must_be_rejected_by": must, "also_fails": also,
                "doc": fn.__doc__.strip().splitlines()[0]}
        with open(os.path.join(d, "INJECTION.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        print(f"built {mid}  op={op}  must_reject={must}")

    with open(contract_out, "w", encoding="utf-8") as f:
        json.dump(contract(), f, ensure_ascii=False, indent=1)
    print(f"contract → {contract_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
