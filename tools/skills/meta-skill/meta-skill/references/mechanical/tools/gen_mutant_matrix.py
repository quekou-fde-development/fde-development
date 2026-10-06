#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_mutant_matrix.py — 由各语料登记表**生成** references/mutant_matrix.md。

不手写这份文档：手写的矩阵是「我以为语料长什么样」，加一个 mutant 而忘了改文档
时，文档照样自洽、照样看起来齐全，而它描述的语料已经不是盘上那套了。文档是
登记表的投影，登记表变则文档变，两者不同步这件事必须能被机械发现。

故本器有两个姿势：
  写：  gen_mutant_matrix.py <out.md>
  验：  gen_mutant_matrix.py <out.md> --check   盘上文档与登记表逐字不符即 rc=1

--check 供矩阵臂调用。少了它，「生成器存在」只证明某一刻同步过，
不证明此刻仍同步——而后者才是文档能被引用的前提。

mutant 的说明文字取自注入函数 docstring 首行，不另写一份：同一件事写两处，
两处迟早分叉，且分叉时无从判定哪份作数。
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def first_line(fn):
    return (fn.__doc__ or "").strip().splitlines()[0].strip() if fn.__doc__ else ""


def collect():
    """三套语料的定向 mutant + 主套件的 E 族预期 + e2e 包内语料 + 闸负例两套。

    闸负例（G/C/P 系）此前不在投影内：它们是编译器机械闸的语料，与断言层
    mutant 不同族，于是被漏在文档外。代价是加 G15/G16/G17 时 `--check` 一声
    不响——「文档与登记表同步」这句话对没被投影的那半从不成立。凡有登记表，
    就得进投影，否则 --check 的绿只覆盖它碰巧看得见的部分。
    """
    mm = importlib.import_module("make_mutants")
    jh = importlib.import_module("make_jh_runs")
    mo = importlib.import_module("make_multiop_fixture")
    am = importlib.import_module("accept_matrix")
    me = importlib.import_module("make_e2e_package")
    gf = importlib.import_module("make_gate_fixtures")
    cf = importlib.import_module("make_custom_fixtures")
    gf._registry_spec()
    cf._registry_spec()

    rows = []
    for mid, _base, op, must, fn in mm.MUTANTS:
        rows.append(dict(suite="OAQ", mid=mid, op=op, must=must,
                         also=[], doc=first_line(fn)))
    for mid, op, must, fn, also in jh.MUTANTS:
        rows.append(dict(suite="jh", mid=mid, op=op, must=must,
                         also=list(also), doc=first_line(fn)))
    for mid, must, fn in mo.MUTANTS:
        rows.append(dict(suite="multiop", mid=mid, op=mo._OP_OF[mid], must=must,
                         also=[], doc=first_line(fn)))
    e_rows = [dict(mid=k, must=v) for k, v in sorted(am.E_EXPECT.items())]
    pkg_rows = [dict(mid=mid, must=must, doc=first_line(fn))
                for mid, must, fn in me.FIXTURE_MUTANTS]
    gate_rows = [dict(mid=mid, suite="gate", must=gate, doc=first_line(fn))
                 for mid, gate, fn in gf.MUTANTS]
    gate_rows += [dict(mid=mid, suite="custom", must=gate, doc=first_line(fn))
                  for mid, gate, fn in cf.MUTANTS]
    # P1 不走 MUTANTS 表（它不是从 C0 复制后定点坏一处，而是另建的空包），
    # 故单列——登记表的形状不同不构成免于投影的理由。
    gate_rows.append(dict(mid="P1-persistent-but-empty", suite="custom", must="M8",
                          doc=first_line(cf.build_persistence_negative)))
    return rows, e_rows, pkg_rows, gate_rows, am.GOLDENS


def render():
    rows, e_rows, pkg_rows, gate_rows, goldens = collect()
    by_op = {}
    for r in rows:
        by_op.setdefault(r["op"], []).append(r)

    L = []
    w = L.append
    w("# mutant 矩阵")
    w("")
    w("> **本文由 `exec-ledger-isolation/tools/gen_mutant_matrix.py` 生成，勿手改。**")
    w("> 改语料后重跑生成器；矩阵臂以 `--check` 验证盘上文档与登记表同步。")
    w("")
    w("每个 operation 的最低谓词族要成为防线，得有至少一个 mutant **被它登记的那条")
    w("断言**拒绝过。判据是「被指名的那条拒」，不是「跑出了 FAIL」——错的断言抓错的")
    w("错，等于没抓。旁落项（同一注入连带打到的别的断言）在登记表里显式列出，只作")
    w("记录，不计入证伪。")
    w("")
    w("## 一 · 按 operation 归族")
    w("")
    w(f"封闭词汇表八类，定向 mutant 共 {len(rows)} 个。")
    w("")
    w("| operation | mutant 数 | 覆盖的断言 |")
    w("|---|---|---|")
    for op in sorted(by_op):
        rs = by_op[op]
        aids = sorted({r["must"] for r in rs})
        w(f"| `{op}` | {len(rs)} | {', '.join('`%s`' % a for a in aids)} |")
    w("")
    w("## 二 · 定向 mutant 逐条")
    w("")
    for op in sorted(by_op):
        w(f"### `{op}`")
        w("")
        w("| mutant | 套件 | 须被这条拒 | 旁落（不计入证伪） | 注入内容 |")
        w("|---|---|---|---|---|")
        for r in sorted(by_op[op], key=lambda x: x["mid"]):
            also = ", ".join(f"`{a}`" for a in r["also"]) or "—"
            w(f"| `{r['mid']}` | {r['suite']} | `{r['must']}` | {also} | {r['doc']} |")
        w("")
    w("## 三 · E 族（主套件预注册预期）")
    w("")
    w("推导链层面的注入，预期在 `fixtures/derivation.md` 里**跑前写定**——")
    w("跑完再填预期是拿结果当判据，实现怎么错预期就怎么歪。")
    w("")
    w("| run | 预期被这条拒 |")
    w("|---|---|")
    for r in e_rows:
        w(f"| `{r['mid']}` | `{r['must']}` |")
    w("")
    w("## 四 · e2e 包内语料")
    w("")
    w("`packages/e2e-orders-probe/fixtures/` 下的 golden + 定向 mutant，")
    w("受编译器 M10 闸检验（golden 须零 FAIL，每个 mutant 须被指名的断言拒）。")
    w("golden 由 `scripts/run_stages.py` 实跑产出，不手写。")
    w("")
    w("| mutant | 须被这条拒 | 注入内容 |")
    w("|---|---|---|")
    for r in pkg_rows:
        w(f"| `{r['mid']}` | `{r['must']}` | {r['doc']} |")
    w("")
    w("## 五 · 闸负例（编译器机械闸 M7-M11）")
    w("")
    w("`gate-fixtures/` 与 `custom-fixtures/` 下的定向坏包，各自从正例整包复制后")
    w("**只坏一处**，判据是「被指名的那道闸拒」。旁落的别的闸只作记录：坏包同时")
    w("踩响两道闸时，若不指名，闸恒 FAIL 与闸能鉴别在退出码上长得一样。")
    w("")
    w("| fixture | 套件 | 须被这道闸拒 | 注入内容 |")
    w("|---|---|---|---|")
    for r in sorted(gate_rows, key=lambda x: (x["suite"], x["mid"])):
        w(f"| `{r['mid']}` | {r['suite']} | {r['must']} | {r['doc']} |")
    w("")
    w("闸覆盖数（按须被拒的那道闸）：")
    w("")
    by_gate = {}
    for r in gate_rows:
        by_gate.setdefault(r["must"], []).append(r["mid"])
    w("| 闸 | 定向 fixture 数 |")
    w("|---|---|")
    for g in sorted(by_gate):
        w(f"| {g} | {len(by_gate[g])} |")
    w("")
    w("## 六 · golden 正例")
    w("")
    w("假阳性对照。golden 上出现任何 FAIL，则该套件全部「拒绝」都不携带信息——")
    w("闸恒 FAIL 与闸能鉴别，在退出码上长得一样。")
    w("")
    w("| golden | 套件 |")
    w("|---|---|")
    for g in goldens:
        w(f"| `{g}` | OAQ |")
    w("| `golden-jh` | jh |")
    w("| `golden-multiop` | multiop |")
    w("| `fixtures/golden` | e2e 包 |")
    w("| `gate-fixtures/G0-good` | gate（五闸须全 PASS） |")
    w("| `custom-fixtures/C0-good` | custom（五闸须全 PASS） |")
    w("")
    return "\n".join(L) + "\n"


def main():
    if len(sys.argv) < 2:
        print("用法: gen_mutant_matrix.py <out.md> [--check]", file=sys.stderr)
        return 2
    out, check = sys.argv[1], "--check" in sys.argv[2:]
    # 位置参数不许长得像开关：`gen_mutant_matrix.py --check`（漏了路径）会把
    # `--check` 当输出路径，于是生成一个名叫 --check 的文件、打印 written、
    # 退出 0。调用方看见的是一次成功的同步检查，而它检查的是它自己刚写出来的
    # 那个文件是否存在。少一个参数就把闸变成恒真——用法错须走 rc2。
    if out.startswith("-"):
        print(f"用法错：输出路径不能以 - 开头（收到 {out!r}）。"
              "只给 --check 而漏了路径时，它会被当成输出文件写掉。", file=sys.stderr)
        return 2
    text = render()
    if check:
        if not os.path.isfile(out):
            print(f"FAIL: {out} 不存在——contract_ir.md 引用它，指针悬空")
            return 1
        cur = open(out, encoding="utf-8").read()
        if cur != text:
            print(f"FAIL: {out} 与登记表不同步——语料改过而文档没重生成")
            return 1
        print(f"PASS: {out} 与登记表逐字一致")
        return 0
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"written → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
