#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house HTML 评分卡报告渲染器

用法：
  python3 render_report.py .dream-house/report.json --output .dream-house/report.html

输入 JSON 结构见 references/templates.md。
输出为单文件 HTML（内联 CSS/SVG，无外部依赖，可离线打开与分享）。
"""

import argparse
import html
import json
import math
import os
import sys

DIMENSIONS = [
    ("location", "地段与通勤"),
    ("price", "价格与性价比"),
    ("quality", "小区品质"),
    ("amenities", "生活配套"),
    ("potential", "板块前景"),
    ("reputation", "开发商与物业口碑"),
    ("risk", "纠纷与交付风险"),
]

RISK_STYLES = {
    "green": ("🟢 无重大风险", "#16a34a"),
    "yellow": ("🟡 有瑕疵需知悉", "#ca8a04"),
    "red": ("🔴 高风险慎入", "#dc2626"),
    "eliminated": ("⛔ 淘汰", "#4b5563"),
}

CONFIDENCE_STYLES = {
    "高": ("✅ 置信度 高", "#16a34a"),
    "中": ("⚠️ 置信度 中", "#ca8a04"),
    "低": ("❓ 置信度 低", "#dc2626"),
}


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "")


def radar_svg(dimensions: dict, size: int = 240) -> str:
    """生成 7 维雷达图 SVG。"""
    cx = cy = size / 2
    radius = size / 2 - 34
    n = len(DIMENSIONS)
    axis_angles = [(-90 + i * 360 / n) * math.pi / 180 for i in range(n)]

    def point(angle, r):
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    parts = []
    # 背景网格（25/50/75/100% 四层）
    for ratio in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{point(angle, radius * ratio)[0]:.1f},{point(angle, radius * ratio)[1]:.1f}"
                       for angle in axis_angles)
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#e5e7eb" stroke-width="1"/>')
    # 轴线与标签
    for (key, label), angle in zip(DIMENSIONS, axis_angles):
        x, y = point(angle, radius)
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        lx, ly = point(angle, radius + 24)
        anchor = "middle"
        if abs(math.cos(angle)) > 0.45:
            anchor = "start" if math.cos(angle) > 0 else "end"
        dim = dimensions.get(key, {})
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="#6b7280" '
                     f'text-anchor="{anchor}" dominant-baseline="middle">{esc(label)} {esc(dim.get("score", "-"))}</text>')
    # 数据多边形
    data_pts = []
    for (key, _), angle in zip(DIMENSIONS, axis_angles):
        dim = dimensions.get(key, {})
        score, mx = dim.get("score", 0) or 0, dim.get("max", 1) or 1
        ratio = max(0.0, min(1.0, score / mx))
        x, y = point(angle, radius * ratio)
        data_pts.append(f"{x:.1f},{y:.1f}")
    parts.append(f'<polygon points="{" ".join(data_pts)}" fill="rgba(37,99,235,0.18)" '
                 f'stroke="#2563eb" stroke-width="2"/>')
    for pt in data_pts:
        x, y = pt.split(",")
        parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#2563eb"/>')

    return (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')


def score_class(total) -> str:
    if total is None:
        return "score-eliminated"
    if total >= 80:
        return "score-good"
    if total >= 65:
        return "score-mid"
    return "score-bad"


def render_card(p: dict) -> str:
    eliminated = p.get("eliminated") or p.get("risk_level") == "eliminated"
    risk_label, risk_color = RISK_STYLES.get(p.get("risk_level", "green"), RISK_STYLES["green"])
    conf_label, conf_color = CONFIDENCE_STYLES.get(p.get("confidence", "中"), CONFIDENCE_STYLES["中"])

    if eliminated:
        score_html = '<div class="score score-eliminated">⛔</div>'
    else:
        total = p.get("total_score")
        score_html = f'<div class="score {score_class(total)}">{esc(total)}<span class="score-max">/100</span></div>'

    dim_rows = []
    for key, label in DIMENSIONS:
        dim = p.get("dimensions", {}).get(key, {})
        score = dim.get("score", "-")
        mx = dim.get("max", "")
        reason = dim.get("reason", "")
        pct = ""
        if isinstance(score, (int, float)) and mx:
            width = max(0, min(100, score / mx * 100))
            pct = (f'<div class="bar"><div class="bar-fill" style="width:{width:.0f}%"></div></div>')
        dim_rows.append(
            f'<tr><td class="dim-name">{esc(label)}</td>'
            f'<td class="dim-score">{esc(score)}/{esc(mx)}</td>'
            f'<td class="dim-bar">{pct}</td>'
            f'<td class="dim-reason">{esc(reason)}</td></tr>')

    pros = "".join(f"<li>{esc(x)}</li>" for x in p.get("pros", []))
    cons = "".join(f"<li>{esc(x)}</li>" for x in p.get("cons", []))
    risk_notes = "".join(f"<li>{esc(x)}</li>" for x in p.get("risk_notes", []))
    sources = "".join(
        f'<li><a href="{esc(s.get("url", "#"))}" target="_blank" rel="noopener">{esc(s.get("title", "来源"))}</a>'
        f' <span class="src-date">{esc(s.get("date", ""))}</span></li>'
        for s in p.get("sources", []))

    if eliminated and p.get("eliminate_reason"):
        eliminate_reason_html = f'<div class="eliminate-reason"><strong>淘汰原因：</strong>{esc(p["eliminate_reason"])}</div>'
    else:
        eliminate_reason_html = ""

    radar = radar_svg(p.get("dimensions", {})) if not eliminated else ""

    return f"""
<section class="card {'card-eliminated' if eliminated else ''}">
  <div class="card-head">
    <div>
      <h2>{esc(p.get('name', ''))}</h2>
      <div class="subtitle">{esc(p.get('subtitle', ''))}</div>
    </div>
    {score_html}
  </div>
  <div class="badges">
    <span class="badge" style="color:{risk_color};border-color:{risk_color}">{risk_label}</span>
    <span class="badge" style="color:{conf_color};border-color:{conf_color}">{conf_label}</span>
    <span class="badge badge-plain">{esc(p.get('price', ''))}</span>
    <span class="badge badge-plain">{esc(p.get('commute', ''))}</span>
  </div>
  <p class="one-liner">{esc(p.get('one_liner', ''))}</p>
  {eliminate_reason_html}
  <div class="card-body">
    <div class="radar">{radar}</div>
    <table class="dim-table">
      <thead><tr><th>维度</th><th>得分</th><th></th><th>打分理由</th></tr></thead>
      <tbody>{''.join(dim_rows)}</tbody>
    </table>
  </div>
  <div class="cols">
    <div><h3>优点</h3><ul class="pros">{pros}</ul></div>
    <div><h3>缺点</h3><ul class="cons">{cons}</ul></div>
    <div><h3>风险排查</h3><ul>{risk_notes}</ul></div>
  </div>
  <details><summary>数据来源（{len(p.get('sources', []))} 条）</summary><ul class="sources">{sources}</ul></details>
</section>"""


def render(data: dict, template: str) -> str:
    meta = data.get("meta", {})
    props = data.get("properties", [])
    # 未淘汰的按总分降序，淘汰的排最后
    props_sorted = sorted(props, key=lambda x: (x.get("eliminated") or x.get("risk_level") == "eliminated",
                                                -(x.get("total_score") or 0)))
    cards = "\n".join(render_card(p) for p in props_sorted)

    out = template
    out = out.replace("{{city}}", esc(meta.get("city", "")))
    out = out.replace("{{generated_at}}", esc(meta.get("generated_at", "")))
    out = out.replace("{{buyer_summary}}", esc(meta.get("buyer_summary", "")))
    out = out.replace("{{data_coverage}}", esc(meta.get("data_coverage", "")))
    out = out.replace("{{total_count}}", str(len(props)))
    out = out.replace("{{cards}}", cards)
    return out


def main():
    parser = argparse.ArgumentParser(description="dream-house HTML 评分卡报告渲染器")
    parser.add_argument("input", help="评分数据 JSON 文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出 HTML 文件路径")
    parser.add_argument("--template", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                           "..", "assets", "report_template.html"),
                        help="HTML 模板路径（默认 assets/report_template.html）")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    with open(args.template, encoding="utf-8") as f:
        template = f.read()

    out = render(data, template)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"报告已生成: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
