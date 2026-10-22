# dream-house（梦想家）— AI 买房决策助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个 Agent Skill：帮你在**中国境内任意城市**选到心仪住房。

它不只搜房子——它会实时检索公开信息筛选候选小区，核查**开发商、物业、纠纷、预售房交付能力**等避坑风险，并给出 **0-100 量化评分**与置信度，最后生成一份可分享的 HTML 评分卡报告。

## 核心能力

- **双模式交互**：一句话给齐「城市+预算」直接出 Top 推荐（快速模式）；信息不足时最多 5 个问题建立需求画像（深度模式）
- **0-100 评分卡**：地段/价格/品质/配套/前景/口碑/风险 7 维度，带打分理由与置信度
- **避坑排雷**：开发商违约、烂尾停工、物业纠纷、产权查封、不利因素逐一排查；一票否决项直接淘汰
- **实时性铁律**：房价超 30 天、政策超 90 天必须重新核实；所有数据标注来源与日期；禁止凭 AI 记忆输出房价
- **多渠道口碑**：Web 搜索 + 微信公众号 + 小红书真实业主评价；搜索被风控时切换**用户身份浏览器通道**（chrome-devtools MCP 操作用户已登录的浏览器，过登录墙/验证码）
- **城市专项指南**：郑州已内置专项档案——郑好房官方交易平台、存量房"一房一码"核验、保交房/白名单排查、以旧换新与人才购房补贴通道（`references/cities/zhengzhou.md`）

## 安装

```bash
npx skills add toringzhang/dream-house
```

或直接把本目录放入你 AI 工具的 skills 目录。兼容所有支持 Agent Skills 的工具（Claude Code、OpenCode、Cursor 等）。

## 依赖

| 依赖 | 用途 | 是否必需 |
|------|------|---------|
| `requests` `beautifulsoup4` | 公众号/小红书基础搜索 | 推荐 |
| `playwright` | 抓取公众号正文、小红书直搜 | 可选（缺失时自动降级） |
| chrome-devtools MCP | 用户身份浏览器搜索（反风控兜底） | 可选（搜索被风控时需要；AI 工具侧配置，连接日常 Chrome） |

```bash
pip3 install requests beautifulsoup4
# 可选增强：
pip3 install playwright && python3 -m playwright install chromium
# chrome-devtools MCP 为 AI 工具侧配置（非 pip/npm 依赖），配置方法见 references/browser_search.md
```

可选配置：在 `.dream-house/.env` 中设置 `XHS_COOKIE=...` 可启用小红书直搜（不配置则自动走搜索引擎间接搜索）。

## 目录结构

```
dream-house/
├── SKILL.md                  ← Skill 主文件
├── references/               ← 渐进式披露的参考文档
│   ├── scoring.md            ← 0-100 评分体系细则
│   ├── risk_checklist.md     ← 避坑排查清单与查询渠道
│   ├── data_sources.md       ← 信息源清单与时效规则
│   ├── browser_search.md     ← 用户身份浏览器搜索（chrome-devtools MCP 反风控通道）
│   ├── concepts.md           ← 选房方法论（只含方法论，不含过时数据）
│   ├── templates.md          ← 输出模板与 report.json 结构
│   └── cities/               ← 城市专项指南（官方渠道/特色政策/排雷要点）
│       └── zhengzhou.md      ← 郑州：郑好房/一房一码/保交房/以旧换新/人才补贴
├── scripts/
│   ├── search_wechat.py      ← 微信公众号口碑搜索
│   ├── search_xiaohongshu.py ← 小红书口碑搜索（自动降级）
│   └── render_report.py      ← 渲染 HTML 评分卡报告
└── assets/
    └── report_template.html  ← HTML 报告模板
```

运行时数据（用户画像、调研资料、报告）存放在当前工作目录的 `.dream-house/`，跨对话延续。

## 使用示例

直接对你的 AI 助手说：

> "我想在杭州买套 400 万左右的二手房，在阿里附近上班，帮我推荐几个小区"

> "XX 楼盘是期房，帮我查查开发商有没有延期交付的风险"

> "对比一下 A 小区和 B 小区，给个评分"

## 贡献

欢迎贡献！最想要的是**更多城市的专项指南**（`references/cities/`，目前仅内置郑州）——如果你熟悉某座城市的官方查房源渠道与购房风险点，欢迎 PR。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 免责声明

本 Skill 输出仅为信息整理与决策参考，不构成投资建议。房产信息以官方渠道与实地核验为准。买房有风险，决策需谨慎。

## 许可证

[MIT](LICENSE) © toringzhang
