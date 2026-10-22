# 输出模板

## 一、对话中的推荐卡片模板

每个候选输出格式：

```markdown
### {序号}. {小区/楼盘名} —— {总分}/100 {置信度图标} {风险灯}

> 一句话推荐理由（直接对接用户核心诉求，例如："三个候选里唯一同时满足你地铁 40 分钟通勤和两卫硬条件的"）

- **价格**：{挂牌/成交价，注明口径} [来源, 日期]
- **位置**：{区域/板块}，距 {地铁站} {距离}；通勤至 {用户工作地点} 约 {时长}
- **基础信息**：{建成年份} / {容积率} / {户型面积段} / {物业公司与物业费}
- **优点**：{2-4 条，每条带来源或依据}
- **缺点**：{1-3 条，坦诚、具体，不淡化}
- **风险排查**：{开发商/物业/纠纷结论各一句}
- **信息时效**：价格数据 {日期}，政策数据 {日期}
```

风险灯：🟢 无重大风险 ｜ 🟡 有瑕疵需知悉 ｜ 🔴 高风险慎入 ｜ ⛔ 淘汰（一票否决）
置信度：✅ 高（多源交叉验证）｜ ⚠️ 中 ｜ ❓ 低（有无法核实的信息，需说明）

## 二、评分卡表格模板（对话中）

```markdown
| 维度 | 满分 | {小区A} | {小区B} | {小区C} |
|------|------|--------|--------|--------|
| 地段与通勤 | 15 | 12 | … | … |
| 价格与性价比 | 15 | 11 | | |
| 小区品质 | 20 | 16 | | |
| 生活配套 | 15 | 12 | | |
| 板块前景 | 5 | 4 | | |
| 开发商与物业口碑 | 15 | 12 | | |
| 纠纷与交付风险 | 15 | 13 | | |
| **总分** | **100** | **80** | | |
| 置信度 | — | ✅ 高 | | |
```

## 三、推荐报告头部模板（.dream-house/research.md 与报告通用）

```markdown
# {城市}购房推荐报告
- 信息核查时间：{YYYY-MM-DD HH:mm}
- 数据覆盖：价格数据截至 {日期}；政策数据截至 {日期}；口碑数据截至 {日期}
- 用户核心诉求：{一句话}
- 硬性条件：{列表}
```

## 四、report.json 结构（render_report.py 输入）

```json
{
  "meta": {
    "city": "杭州",
    "generated_at": "2026-10-22 14:30",
    "buyer_summary": "预算 400 万，二手房，阿里西溪园区通勤，两卫",
    "data_coverage": "价格截至 2026-10-20；政策截至 2026-10-01"
  },
  "properties": [
    {
      "name": "XX 小区",
      "subtitle": "余杭区 · 未来科技城 | 2018 年 | 二手房",
      "total_score": 82,
      "confidence": "高",
      "risk_level": "green",
      "one_liner": "一句话推荐理由",
      "price": "挂牌 4.2 万/㎡，近 90 天成交 3.9-4.3 万/㎡",
      "commute": "距 5 号线 XX 站 900m，驾车至阿里约 25 分钟",
      "dimensions": {
        "location":  { "score": 12, "max": 15, "reason": "…" },
        "price":     { "score": 11, "max": 15, "reason": "…" },
        "quality":   { "score": 16, "max": 20, "reason": "…" },
        "amenities": { "score": 12, "max": 15, "reason": "…" },
        "potential": { "score": 4,  "max": 5,  "reason": "…" },
        "reputation":{ "score": 12, "max": 15, "reason": "…" },
        "risk":      { "score": 13, "max": 15, "reason": "…" }
      },
      "pros": ["优点1", "优点2"],
      "cons": ["缺点1"],
      "risk_notes": ["开发商近 3 年无违约记录 [来源, 日期]"],
      "eliminated": false,
      "eliminate_reason": "",
      "sources": [
        { "title": "贝壳小区页", "url": "https://…", "date": "2026-10-20" }
      ]
    }
  ]
}
```

字段约束：
- `confidence`：高 / 中 / 低
- `risk_level`：green / yellow / red / eliminated
- `eliminated` 为 true 时 `total_score` 填 null，`eliminate_reason` 必填
- `dimensions` 的 key 固定为 7 个：location / price / quality / amenities / potential / reputation / risk

## 五、渲染命令与交付（WorkBuddy）

```bash
# Windows
python <skill_dir>/scripts/render_report.py .dream-house/report.json --output .dream-house/report.html
# macOS / Linux
python3 <skill_dir>/scripts/render_report.py .dream-house/report.json --output .dream-house/report.html
```

1. 渲染成功后调用 **`present_files`**，传入 HTML 的**绝对路径**打开预览（这一步必须做，否则用户看不到报告）。
2. 对话内再补一张 **`show_widget`** 可视化（先 `widget_guidelines` 加载规范）：候选横评的维度对比条形图或单个候选的雷达图。浅色主题、浅底深字，颜色语义与风险灯一致（🟢 绿 / 🟡 黄 / 🔴 红）。
3. 收尾一句："报告已生成，这个 HTML 可以直接保存或分享。"

## 六、对话内可视化建议（show_widget）

| 场景 | 画什么 |
|------|--------|
| Top 3-5 候选横评 | 分组条形图：7 个维度的得分对比，或总分 + 风险灯 |
| 单个候选深度解读 | 7 维雷达图（与 HTML 报告里的雷达图口径一致） |
| 预算/通勤取舍 | 双轴散点：横轴通勤时长、纵轴总价，气泡大小=评分 |
| 决策路径 | 流程图：硬条件筛选 → 排雷 → 评分 → 推荐 |

图表里不堆砌数字，只保留影响判断的维度；每个图配一句话结论。
