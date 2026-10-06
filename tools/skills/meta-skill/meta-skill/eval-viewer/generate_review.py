# -*- coding: utf-8 -*-
"""
generate_review.py — meta-skill 第 8/9 步：人审 viewer（只做静态 HTML）。

大白话契约（给不懂代码的人看）：
  把一轮 eval 的产物 + 评分 + benchmark 收成一份自包含 HTML，丢浏览器就能看，给人（夏洛克）审。
  只做 --static：单机不守 server 进程（Anthropic 原版可起 HTTP server，本系统砍掉，单机用静态更稳）。
  它只读 workspace 文件、只写一份 HTML，不调模型、不动 skill。无外部依赖。

  两种模式：
    1) iteration 审阅（默认）：
       python generate_review.py "<workspace>/iteration-N" --skill-name <name> --static <out.html> \\
           [--benchmark <iteration-N/benchmark/benchmark.json>] [--previous-workspace <iteration-(N-1)>]
       → 两 tab：Outputs（逐 run 的路由/断言 + 转写摘要 + 卡壳）、Benchmark（with vs without 对照）。
         给了 --previous-workspace 则 Benchmark tab 多一列上一轮对比。

    2) 触发 eval 审阅：
       python generate_review.py --trigger "<workspace>/trigger_eval" --skill-name <name> --static <out.html>
       → 套 assets/eval_review.html 模板，填 trigger_set + description，供人核 should_trigger 标注。

  审阅产物落 <workspace>/review/。人看完把反馈口头给主 agent（单人系统无需 feedback.json 回写）。
"""
import argparse
import html
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RUN_RE = re.compile(r"^eval-(?P<eid>\d+)-(?P<config>with_skill|without_skill)-run(?P<run>\d+)$")


def esc(x):
    return html.escape(str(x)) if x is not None else ""


def script_json(value):
    """JSON embedded in an HTML script must not contain an HTML closing tag."""
    return (json.dumps(value, ensure_ascii=False).replace("&", "\\u0026")
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def read_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(path, limit=4000):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        t = f.read()
    return t[:limit] + ("\n…（截断）" if len(t) > limit else "")


def render_run(it_dir, name):
    """渲一个 run 的卡片。"""
    g = read_json(os.path.join(it_dir, name, "grading.json"))
    tr = read_text(os.path.join(it_dir, name, "transcript.md"), 2000)
    parts = [f'<div class="run"><h4>{esc(name)}</h4>']
    if g is None:
        parts.append('<p class="missing">（无 grading.json）</p></div>')
        return "".join(parts)
    et = g.get("eval_type", "?")
    parts.append(f'<p class="et">eval_type: <b>{esc(et)}</b></p>')
    if et == "route_convergence":
        rr = g.get("route_result", {})
        match = rr.get("route_match")
        cls = "pass" if match else "fail"
        parts.append(f'<p>route_match: <span class="{cls}">{esc(match)}</span></p>')
        parts.append(f'<p>expected: {esc(rr.get("expected_route"))}</p>')
        parts.append(f'<p>actual: {esc(rr.get("actual_route"))}</p>')
        parts.append(f'<p class="ev">evidence: {esc(rr.get("evidence"))}</p>')
        stuck = rr.get("stuck", [])
        if stuck:
            parts.append('<p class="stuck">卡壳: ' +
                         "; ".join(f'[{esc(s.get("type"))}] {esc(s.get("note"))}' for s in stuck) + '</p>')
    elif et == "end_state":
        summ = g.get("summary", {})
        parts.append(f'<p>pass_rate: <b>{esc(summ.get("pass_rate"))}</b> '
                     f'({esc(summ.get("passed"))}/{esc(summ.get("total"))})</p>')
        for e in g.get("expectations", []):
            cls = "pass" if e.get("passed") else "fail"
            parts.append(f'<div class="exp"><span class="{cls}">{esc(e.get("passed"))}</span> '
                         f'{esc(e.get("text"))}<br><i>{esc(e.get("evidence"))}</i></div>')
    fb = g.get("eval_feedback", {})
    if fb.get("overall"):
        parts.append(f'<p class="fb">grader 批断言: {esc(fb.get("overall"))}</p>')
    if tr:
        parts.append(f'<details><summary>转写摘要</summary><pre>{esc(tr)}</pre></details>')
    parts.append("</div>")
    return "".join(parts)


def render_iteration(it_dir, skill, bench, prev_bench, out_path):
    runs = sorted(n for n in os.listdir(it_dir) if RUN_RE.match(n))
    out_cards = "\n".join(render_run(it_dir, n) for n in runs) or "<p>（无 run 目录）</p>"

    # benchmark tab
    btab = "<p>（无 benchmark.json）</p>"
    if bench:
        rs = bench.get("run_summary", {})
        primary = rs.get("with_skill", {}).get("primary_metric") or "pass_rate"
        w = rs.get("with_skill", {}).get(primary)
        wo = rs.get("without_skill", {}).get(primary)
        d = rs.get("delta", {}).get(primary)
        prev_cell = ""
        if prev_bench:
            prs = prev_bench.get("run_summary", {})
            pw = prs.get("with_skill", {}).get(primary)
            prev_cell = f"<td>{esc(pw)}</td>"
        prev_head = "<th>上轮 with</th>" if prev_bench else ""
        btab = f"""
        <p>主指标: <b>{esc(primary)}</b> · evals={esc(bench.get('metadata',{}).get('evals_run'))}
           · runs/配置={esc(bench.get('metadata',{}).get('runs_per_configuration'))}</p>
        <table><tr><th>with_skill</th><th>without_skill</th><th>delta</th>{prev_head}</tr>
        <tr><td class="big">{esc(w)}</td><td class="big">{esc(wo)}</td>
            <td class="big {'pass' if (isinstance(d,(int,float)) and d>0) else ''}">{esc(d)}</td>{prev_cell}</tr></table>
        """
        if "by_eval_type" in rs.get("with_skill", {}):
            rows = []
            for et, metrics in rs["with_skill"]["by_eval_type"].items():
                for metric in ("pass_rate", "route_match_rate", "convergence_rate", "pass_k"):
                    if metric not in metrics:
                        continue
                    w = metrics[metric]
                    wo = rs.get("without_skill", {}).get("by_eval_type", {}).get(et, {}).get(metric)
                    d = rs.get("delta", {}).get(et, {}).get(metric)
                    prior = ""
                    if prev_bench:
                        previous = prev_bench.get("run_summary", {}).get("with_skill", {}).get("by_eval_type", {}).get(et, {}).get(metric)
                        prior = f"<td>{esc(previous)}</td>"
                    rows.append(f"<tr><td>{esc(et)}</td><td>{esc(metric)}</td><td>{esc(w)}</td><td>{esc(wo)}</td><td>{esc(d)}</td>{prior}</tr>")
            btab = (f"<p>Status: <b>{esc(bench.get('metadata', {}).get('status'))}</b></p>"
                    "<table><tr><th>eval_type</th><th>metric</th><th>with_skill</th><th>without_skill</th><th>delta</th>"
                    + ("<th>上轮 with</th>" if prev_bench else "") + "</tr>"
                    + "".join(rows) + "</table>")

    doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>eval review · {esc(skill)} · {esc(os.path.basename(it_dir))}</title>
<style>
 body{{font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a}}
 header{{background:#222;color:#fff;padding:12px 20px}} header h1{{font-size:16px;margin:0}}
 .tabs{{display:flex;gap:4px;background:#222;padding:0 20px}}
 .tabs button{{background:#333;color:#bbb;border:0;padding:8px 16px;cursor:pointer;font-size:13px}}
 .tabs button.active{{background:#f6f7f9;color:#111;font-weight:600}}
 .panel{{display:none;padding:20px;max-width:1000px}} .panel.active{{display:block}}
 .run{{background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:12px 16px;margin-bottom:12px}}
 .run h4{{margin:0 0 8px}} .run p{{margin:4px 0;font-size:13px}}
 .pass{{color:#0a7d23;font-weight:600}} .fail{{color:#c0271a;font-weight:600}}
 .missing{{color:#999}} .stuck{{color:#b5651d}} .ev,.fb{{color:#555;font-size:12px}}
 .exp{{font-size:12px;border-left:3px solid #ddd;padding-left:8px;margin:6px 0}}
 pre{{background:#f0f0f0;padding:8px;font-size:11px;overflow:auto;white-space:pre-wrap}}
 table{{border-collapse:collapse;margin-top:8px}} th,td{{border:1px solid #ccc;padding:8px 14px;text-align:center}}
 td.big{{font-size:20px;font-weight:700}} details{{margin-top:6px}} summary{{cursor:pointer;font-size:12px;color:#06c}}
</style></head><body>
<header><h1>eval review · {esc(skill)} · {esc(os.path.basename(it_dir))}</h1></header>
<div class="tabs">
 <button class="active" onclick="show('out')">Outputs ({len(runs)} runs)</button>
 <button onclick="show('bench')">Benchmark</button>
</div>
<div id="out" class="panel active">{out_cards}</div>
<div id="bench" class="panel">{btab}</div>
<script>
 function show(id){{
   for(const p of document.querySelectorAll('.panel')) p.classList.remove('active');
   for(const b of document.querySelectorAll('.tabs button')) b.classList.remove('active');
   document.getElementById(id).classList.add('active');
   event.target.classList.add('active');
 }}
</script></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"写: {out_path}  ({len(runs)} runs)")


def render_trigger(trig_dir, skill, out_path):
    tset = read_json(os.path.join(trig_dir, "trigger_set.json")) or []
    result = read_json(os.path.join(trig_dir, "result.json")) or {}
    tmpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "eval_review.html")
    desc = result.get("best_description") or result.get("original_description") or "（未知）"
    if os.path.isfile(tmpl_path):
        with open(tmpl_path, encoding="utf-8") as f:
            tmpl = f.read()
        doc = (tmpl.replace("__SKILL_NAME_PLACEHOLDER__", esc(skill))
                   .replace("__SKILL_DESCRIPTION_PLACEHOLDER__", esc(desc))
                   .replace("__EVAL_DATA_PLACEHOLDER__", script_json(tset)))
    else:
        rows = "\n".join(
            f'<tr><td>{esc(q.get("query"))}</td><td>{esc(q.get("should_trigger"))}</td></tr>' for q in tset)
        doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>trigger review · {esc(skill)}</title></head><body>
<h2>触发 eval 复核 · {esc(skill)}</h2><p>description: {esc(desc)}</p>
<table border=1 cellpadding=6><tr><th>query</th><th>should_trigger</th></tr>{rows}</table></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"写: {out_path}  ({len(tset)} queries)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="iteration 目录（默认模式）")
    ap.add_argument("--trigger", help="trigger_eval 目录（触发审阅模式）")
    ap.add_argument("--skill-name", required=True)
    ap.add_argument("--static", required=True, help="输出 HTML 路径")
    ap.add_argument("--benchmark", default=None)
    ap.add_argument("--previous-workspace", default=None)
    args = ap.parse_args()

    bar = "=" * 56
    print(bar); print(f"generate_review.py · {args.skill_name}"); print(bar)
    os.makedirs(os.path.dirname(os.path.abspath(args.static)), exist_ok=True)

    if args.trigger:
        render_trigger(args.trigger, args.skill_name, args.static)
    else:
        if not args.target or not os.path.isdir(args.target):
            print(f"FAIL: iteration 目录无效: {args.target}")
            sys.exit(1)
        bpath = args.benchmark or os.path.join(args.target, "benchmark", "benchmark.json")
        bench = read_json(bpath)
        prev_bench = None
        if args.previous_workspace:
            prev_bench = read_json(os.path.join(args.previous_workspace, "benchmark", "benchmark.json"))
        render_iteration(args.target, args.skill_name, bench, prev_bench, args.static)
    print(bar)


if __name__ == "__main__":
    main()
