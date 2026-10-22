# 社媒口碑搜索（小红书 / 微信公众号 / 兜底渠道）

房价可以查平台，但**"住得爽不爽"只有业主知道**。这一层负责拿到真实口碑，是 dream-house 排雷与"开发商与物业口碑""纠纷与交付风险"两个评分维度的主要输入。

## 一、小红书（业主真话浓度最高）

### L0：`xiaohongshu-skills`（首选，真实登录态）

来源：[autoclaw-cc/xiaohongshu-skills](https://github.com/autoclaw-cc/xiaohongshu-skills)。它通过 **Chrome 扩展 + 本地 CLI** 操作你自己的浏览器和真实账号，天然绕过匿名访问必弹的登录墙。

安装（前置：Python ≥ 3.11、`uv`、Google Chrome）：

```bash
# 1. 放到 WorkBuddy 的 skills 目录
cd ~/.workbuddy/skills/                                   # Windows: C:\Users\<用户名>\.workbuddy\skills
git clone https://github.com/autoclaw-cc/xiaohongshu-skills.git
cd xiaohongshu-skills && uv sync

# 2. 加载浏览器扩展：chrome://extensions/ → 开发者模式 → 加载已解压的扩展程序 → 选 extension/ 目录
#    确认 "XHS Bridge" 已启用
```

dream-house 只用到它的**只读**能力：

```bash
python <xhs_dir>/scripts/cli.py check-login
python <xhs_dir>/scripts/cli.py search-feeds --keyword "XX小区 踩坑"
python <xhs_dir>/scripts/cli.py search-feeds --keyword "XX楼盘 交付" --sort-by "最多点赞" --note-type "图文"
python <xhs_dir>/scripts/cli.py get-feed-detail --feed-id <FEED_ID> --xsec-token <XSEC_TOKEN>
```

- 输出 JSON，退出码：`0` 成功 · `1` 未登录 · `2` 错误
- 退出码 1 → 跑 `python <xhs_dir>/scripts/cli.py login` 拿二维码给用户扫，登录后重跑；**不要在对话里回显 token**
- 首次运行若 Chrome 未打开，CLI 会自行拉起

**只读取用清单（红线）**：`check-login` / `login` / `search-feeds` / `get-feed-detail` / `list-feeds` / `user-profile`。
**禁止**调用 `publish` / `publish-video` / `like-feed` / `favorite-feed` / `post-comment` / `reply-comment`——dream-house 只做调研，绝不代用户在小红书上留下任何痕迹。

**频率控制**：单次任务一个小区不超过 3 个关键词、总量 ≤10 条笔记详情；连续操作间隔几秒。触发风控立即停止并换渠道。

### L1 / L2：内置脚本（零配置降级）

`xiaohongshu-skills` 未安装或未登录时，用内置脚本，它会自动两级降级：

```bash
# Windows
python <skill_dir>/scripts/search_xiaohongshu.py --keyword "XX小区 踩坑"
python <skill_dir>/scripts/search_xiaohongshu.py --keyword "XX小区 交付" --json
# macOS / Linux 把 python 换成 python3
```

- **L1（默认）**：搜索引擎 `site:xiaohongshu.com` 间接搜，拿标题+摘要，零配置零依赖
- **L2**：`.dream-house/.env` 配 `XHS_COOKIE=...` 后 Playwright 直搜，可拿正文摘要；Cookie 失效会自动降级 L1
- 常用参数：`--limit`（默认 8）、`--mode auto|search-engine|direct`、`--output`、`--json`
- 结果写入 `.dream-house/data/search-results/xhs_results.txt`

### L3：都被拦 → 浏览器通道

L0 未配置且 L1/L2 被风控（登录墙/验证码/空结果）时，走 [browser_search.md](browser_search.md) 的 WorkBuddy 浏览器通道。

## 二、微信公众号

公众号测评通常比平台更敢说，交付实拍、业主维权纪实常有独家信息。

```bash
python3 <skill_dir>/scripts/search_wechat.py --keyword "杭州 未来科技城 小区测评"
python3 <skill_dir>/scripts/search_wechat.py --keywords "XX小区 业主" "XX楼盘 交付" --limit 8
python3 <skill_dir>/scripts/search_wechat.py --url "https://mp.weixin.qq.com/s/xxx"   # 抓单篇正文
```

- 走搜狗微信，**有反爬限频**：`--limit` ≤10，关键词之间已内置 2 秒间隔，不要连续高频调用
- 基础搜索零第三方依赖（缺 `requests`/`beautifulsoup4` 时自动用标准库降级）
- `--fetch-content` / `--url` 需 Playwright：`python -m pip install playwright && python -m playwright install chromium`
- 触发验证码 → 浏览器通道（见 browser_search.md 的搜狗微信条目）

## 三、其他口碑渠道（WebSearch 直达）

| 渠道 | 搜索姿势 | 适合查什么 |
|------|---------|-----------|
| 知乎 | `site:zhihu.com {小区名} 体验/入住感受` | 长文居住体验、板块对比 |
| 黑猫投诉 | `site:tousu.sina.com.cn {开发商/物业名}` | 物业与开发商投诉量与类型 |
| 微博 | `site:weibo.com {楼盘名} 维权` | 维权事件的时间线验证 |
| 人民网领导留言板 | `{城市} {小区名} 投诉` | **官方回复记录**，可信度高，排雷利器 |
| 业主论坛 / 城市贴吧 | `{小区名} 业主论坛` | 交付细节、装修改造经验 |

## 四、口碑使用规范

1. **单一来源不结论**：物业口碑类需 ≥2 个独立来源印证才写入评分理由；只有一条时置信度降为"低"。
2. **区分事实与情绪**："物业态度差"是主观感受，"2025 年 12 月因漏水被 30 户联名投诉"是可核事实，优先用后者。
3. **看时间**：3 年前的吐槽大概率已整改，必须核对发帖时间，超 1 年的口碑只作参考。
4. **记录格式统一**写入 `.dream-house/research.md`：

```
- [事实描述] [来源: {平台/标题}, {URL}, {日期 YYYY-MM-DD}, {渠道: 小红书/公众号/知乎}]
```

5. **搜不到就直说**：不要因为"没搜到负面"就写"口碑良好"——写"未检索到近一年的负面舆情"，并在置信度上体现。
