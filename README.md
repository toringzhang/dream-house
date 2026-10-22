# dream-house（梦想家）— AI 买房决策助手 · WorkBuddy 版

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个面向 **WorkBuddy** 的 Agent Skill：帮你在**中国境内任意城市**选到心仪住房。

它不只搜房子——它会实时检索权威房源数据、核查**开发商、物业、纠纷、预售房交付能力**等避坑风险，给出 **0-100 量化评分**与置信度，最后生成一份可分享的 HTML 评分卡报告。

## 核心能力

- **权威数据源优先**：房源/小区/成交价/行情/政策/学区默认走**贝壳官方 `beike` CLI**（[LianjiaTech/beike-ai-platform](https://github.com/LianjiaTech/beike-ai-platform)），拿不到再降级网络搜索
- **真实业主口碑**：小红书走 [xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills)（用你自己的浏览器登录态，**只读**），未安装时自动降级为内置脚本的搜索引擎间接搜；微信公众号走搜狗微信
- **双模式交互**：一句话给齐「城市+预算」直接出 Top 推荐（快速模式）；信息不足时最多 5 个问题建立需求画像（深度模式）
- **0-100 评分卡**：地段/价格/品质/配套/前景/口碑/风险 7 维度，带打分理由与置信度
- **避坑排雷**：开发商违约、烂尾停工、物业纠纷、产权查封、不利因素逐一排查；一票否决项直接淘汰
- **实时性铁律**：房价超 30 天、政策超 90 天必须重新核实；所有数据标注来源与日期；禁止凭模型记忆输出房价
- **WorkBuddy 原生输出**：报告生成后自动用 `present_files` 打开预览，对话内用 `show_widget` 渲染对比图/评分卡
- **城市专项指南**：郑州已内置专项档案（`references/cities/zhengzhou.md`）

## 安装（WorkBuddy）

把本目录放到 WorkBuddy 的用户级 skills 目录即可生效：

```
~/.workbuddy/skills/dream-house/          # macOS / Linux
C:\Users\<用户名>\.workbuddy\skills\dream-house\   # Windows
```

```bash
# 示例（macOS / Linux）
git clone https://github.com/toringzhang/dream-house.git ~/.workbuddy/skills/dream-house

# 或：npx skills add toringzhang/dream-house
```

同时也兼容其他支持 `SKILL.md` 的 Agent（Claude Code、OpenCode、Cursor 等），只是浏览器通道与报告预览需按其工具链替换。

## 可选依赖

| 依赖 | 用途 | 是否必需 |
|------|------|---------|
| `beike` CLI + API Key | 贝壳官方权威数据（房源/小区/成交/政策/学区） | **推荐**；缺失时自动降级网络搜索 |
| `xiaohongshu-skills` + Chrome 扩展 | 小红书真实登录态只读搜索 | **推荐**；缺失时降级为间接搜索 |
| `requests` `beautifulsoup4` | 提升搜索脚本解析质量 | 可选（缺失时用标准库降级，**不会报错**） |
| `playwright` | 抓取公众号正文、小红书 Cookie 直搜 | 可选（缺失时自动跳过） |
| WorkBuddy 浏览器控制（`workbuddy-browser-use` / agent-browser） | 反风控兜底通道 | 可选（被验证码/登录墙拦截时需要） |

```bash
# 贝壳官方 CLI
curl -fsSL https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/cli/releases/install.sh | bash
beike doctor          # 首次会引导你登录取 API Key

# Python 依赖（可选）
python -m pip install requests beautifulsoup4          # Windows
python3 -m pip install requests beautifulsoup4         # macOS / Linux
```

贝壳 API Key 获取页：`https://building.ke.com/?action=get-key&source=workbuddy`（登录后把页面上的身份凭证发给助手，它会静默保存到 `~/.beike/BEIKE_MCP_API_KEY`）。

## 与 `beike-assistant` 的分工

WorkBuddy 内置了贝壳官方 `beike-assistant` Skill。两者是**分层**关系，不是重复：

| 你要做什么 | 用谁 |
|-----------|------|
| 找房源、看房、约看、联系经纪人、租房、卖房、装修报价 | `beike-assistant` |
| 需求梳理、多源排雷、0-100 评分、候选对比、"该不该买"、出决策报告 | **dream-house** |

dream-house 需要权威数据时直接调 `beike` CLI，自身不重复实现房源检索。

## 目录结构

```
dream-house/
├── SKILL.md                  ← Skill 主文件（含 WorkBuddy 工具映射）
├── references/
│   ├── beike_channel.md      ← 贝壳 CLI：安装/鉴权/命令映射/降级
│   ├── social_search.md      ← 小红书（xiaohongshu-skills）+ 公众号 + 兜底渠道
│   ├── browser_search.md     ← WorkBuddy 浏览器通道（反风控兜底）
│   ├── scoring.md            ← 0-100 评分体系细则
│   ├── risk_checklist.md     ← 避坑排查清单与查询渠道
│   ├── data_sources.md       ← 信息源清单与时效规则
│   ├── concepts.md           ← 选房方法论（只含方法论，不含过时数据）
│   ├── templates.md          ← 输出模板与 report.json 结构
│   └── cities/               ← 城市专项指南
│       └── zhengzhou.md      ← 郑州：郑好房/一房一码/保交房/以旧换新/人才补贴
├── scripts/
│   ├── dh_common.py          ← 公共抓取/解析库（零第三方依赖可跑）
│   ├── search_wechat.py      ← 微信公众号口碑搜索
│   ├── search_xiaohongshu.py ← 小红书口碑搜索（三级降级）
│   └── render_report.py      ← 渲染 HTML 评分卡报告
└── assets/
    └── report_template.html  ← HTML 报告模板
```

运行时数据（用户画像、调研资料、报告）存放在当前工作目录的 `.dream-house/`，跨对话延续，已被 `.gitignore` 排除。

## 使用示例

直接在 WorkBuddy 里说：

> "我想在杭州买套 400 万左右的二手房，在阿里附近上班，帮我推荐几个小区"

> "XX 楼盘是期房，帮我查查开发商有没有延期交付的风险"

> "对比一下 A 小区和 B 小区，给个评分"

助手会实时检索 → 排雷 → 评分 → 生成 HTML 报告并直接打开给你看。

## 贡献

欢迎贡献！最想要的是**更多城市的专项指南**（`references/cities/`，目前仅内置郑州）。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 免责声明

本 Skill 输出仅为信息整理与决策参考，不构成投资建议。房产信息以官方渠道与实地核验为准。买房有风险，决策需谨慎。

## 许可证

[MIT](LICENSE) © toringzhang
