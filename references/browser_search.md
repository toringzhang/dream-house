# WorkBuddy 浏览器通道（反风控兜底）

当 `beike` CLI、WebSearch、社媒脚本被风控（验证码、登录墙、空结果）时，改用 **WorkBuddy 的浏览器能力**：操作用户自己的浏览器，风控系统看到的是真实浏览器与登录态，而不是爬虫。

> 本文替代旧版的 chrome-devtools MCP 方案。WorkBuddy 不提供 chrome-devtools MCP，请按下面的通道走。

## 一、两条通道，按优先级选

### 通道 A：浏览器工具（`mcp__browser__*`，主力）

`mcp__browser__browsers_list` 通常返回**两类实例**，选哪个取决于"登录态在哪"：

| 实例 | 特征 | 什么时候用 |
|------|------|-----------|
| **WorkBuddy 内置浏览器** | `type: desktop`（名称常为 "WorkBuddy Browser"） | **需要用户现场登录时**。它不带任何登录态，但用户可以在里面登录；**登录一次后状态保留**，之后 WorkBuddy 全程用 DOM 工具自己操作，不再打扰用户 |
| **用户 Chrome / Edge** | `type: extension`（带 `extension_id`、profile） | **用户浏览器里本来就有登录态时优先用**（小红书、贝壳、知乎等） |

典型流程（以贝壳为例，Key 拿不到时的标准降级）：

```text
1. browsers_list → 选 desktop 实例（内置浏览器）的 browser_id
2. tabs_new(browser_id, url="https://<城市拼音>.ke.com/xiaoqu/rs<小区名>/")
3. dom_cua_get_visible_dom 判断：是不是被挡在登录页
   是 → 告诉用户"请在刚打开的浏览器窗口里登录贝壳"，等用户说"好了" → 重新读 DOM 验证
   否 → 直接提取
4. 登录态已在浏览器里，后续所有搜索/翻页/详情都自己用 dom_cua_click / dom_cua_type 完成
5. 每条数据记 [来源, URL, 日期]，标注「（浏览器提取）」
```

> 注意：`dom_cua_*` 的 `node_id` 只对当前快照有效，页面一变必须**重新读 DOM**，不要用旧 node_id 重试。

### 通道 B：Skill / 网页抓取（辅助）

| 优先级 | 通道 | 说明 |
|-------|------|------|
| 1 | **`workbuddy-browser-use` Skill** | 加载后按其规范操作，内部同样是 `mcp__browser__*` |
| 2 | `WebFetch` | 只需静态文本、无需登录/交互时最快 |
| 3 | 请用户手动查 | 都不行时给出精确查询路径 |

## 二、工具速查

### workbuddy-browser-use Skill

加载后按其指令操作用户自己的浏览器（打开 URL、读页面、点击、截图、填表）。适合需要真人式交互与登录等待的场景。

### agent-browser MCP

| 工具 | 用途 | 要点 |
|------|------|------|
| `browsers_list` / `browser_info` | 健康检查 | 确认浏览器可用 |
| `tabs_list` / `tabs_get` / `user_open_tabs` | 盘点标签页 | **只读盘点**，不动用户既有页面 |
| `tabs_new` | 新建标签页 | 记下返回的 page/tab 标识 |
| `tab_goto` / `tab_reload` / `tab_back` / `tab_forward` | 导航 | 日常搜索尽量后台进行 |
| `dom_cua_get_visible_dom` | **结构化提取主力** | 拿可见 DOM，比截图省 token |
| `dom_cua_click` / `dom_cua_type` / `dom_cua_scroll` / `dom_cua_keypress` | 交互 | 基于可见 DOM 定位元素 |
| `cua_click` / `cua_type` / `cua_scroll` / `cua_move` / `cua_drag` | 坐标级操作 | 拿不到 DOM 时的兜底 |
| `tab_screenshot` | 截图 | 扫码登录时把二维码给用户扫 |
| `tab_title` / `tab_url` | 确认当前页 | 判断有没有被跳到登录页 |
| `tabs_close` / `tabs_finalize` | 关闭 | **只关自己开的** |

## 三、标准流程

```text
1. 浏览器可用性检查（browsers_list / browser_info）
2. tabs_new 打开搜索页 → tab_goto 到目标 URL
3. tab_url / dom_cua_get_visible_dom 判断：是不是被挡在登录墙
   否 → 提取结构化结果
   是 → 登录等待流程（见下）
4. 每条结果记录 [来源, URL, 日期] 到 .dream-house/research.md，来源标注「（浏览器身份搜索）」
5. 收尾：列出本次打开的页面，征得用户同意后关闭
```

登录墙判定：看 `tab_url` 是否跳到 `/login`、`passport`、`security` 之类，或可见 DOM 里出现"登录后查看""扫码登录"等字样。

## 四、登录等待流程（核心交互）

发现登录墙后**不要尝试任何绕过**，直接让用户登录：

1. 把该标签页置前台（browser-use 的聚焦能力 / MCP 的 `tabs_selected`）
2. 告诉用户："需要登录 {站点} 才能继续搜索，已在你的浏览器打开登录页，登录完成后告诉我"
3. 用户说「好了」→ 重新检查 `tab_url` 与可见 DOM 确认已登录 → 继续
4. 扫码场景：`tab_screenshot` 把二维码截给用户扫
5. 登录态由用户浏览器自身持久化，下次直接用

## 五、站点搜索手册

> 2026-10 实测标注。前端改版会导致选择器失效，失效时重新取可见 DOM 再定位。

| 站点 | 搜索 URL 模板（`<kw>` 需 URL 编码） | 实测状态 |
|------|-----------------------------------|---------|
| 小红书 | `https://www.xiaohongshu.com/search_result?keyword=<kw>` | 匿名必弹登录墙；登录后正常（**优先走 xiaohongshu-skills，别重复造轮子**） |
| Bing | `https://www.bing.com/search?q=<kw>` | 匿名可用 |
| 必应国际版 | `https://www.bing.com/search?q=<kw>&setlang=en` | 偶尔更全 |
| 知乎 | `https://www.zhihu.com/search?type=content&q=<kw>` | 匿名列表可读，登录后更全 |
| 贝壳（二手房列表） | `https://<城市拼音>.ke.com/ershoufang/rs<kw>/` | 替代 `beike buy search --house-type second` |
| 贝壳（小区页：均价/成交/配套） | `https://<城市拼音>.ke.com/xiaoqu/rs<kw>/` | 替代 `beike buy resblock`，**查小区首选入口** |
| 贝壳（成交记录） | `https://<城市拼音>.ke.com/chengjiao/rs<kw>/` | 替代 `beike buy sold`，结论必须基于成交价 |
| 贝壳（新房/楼盘） | `https://<城市拼音>.fang.ke.com/loupan/` 站内搜 | 替代 `beike buy search --house-type new` |
| 贝壳（登录页，取 API Key 用） | `https://building.ke.com/?action=get-key&source=workbuddy` | 纯 SPA，依赖 `s1.ljcdn.com`，网络受限时**白屏属正常**，拿不到就走上面的网页版 |
| 安居客 | `https://<城市拼音>.anjuke.com/community/?kw=<kw>` | 验证码频繁，建议登录 |
| 搜狗微信 | `https://weixin.sogou.com/weixin?type=2&query=<kw>` | 高频触发验证码 |
| 微博 | `https://s.weibo.com/weibo?q=<kw>` | 登录后更全 |
| 黑猫投诉 | `https://tousu.sina.com.cn/index/search/?keywords=<kw>` | 基本可读 |
| 人民网领导留言板 | `https://liuyan.people.com.cn/` 站内搜索 | 官方回复记录，排雷价值高 |

提取要点：
- 列表页：优先 `dom_cua_get_visible_dom`，从中取标题、链接、摘要、时间
- 详情页：`tab_goto` 打开后取正文文本，按段截取即可，不用整页塞进上下文
- 元素定位失败 → `tab_screenshot` 看一眼真实页面再调整

## 六、操作守则（这是用户的日常浏览器，必须遵守）

1. **不动用户已有标签页**：只操作自己新建的页面；`tabs_list` / `user_open_tabs` 只用于盘点
2. 批量搜索默认后台进行；只有需要用户操作（登录、过验证码）时才置前台
3. **只读**：搜索、浏览、提取。绝不代用户发帖、评论、点赞、关注、私信、下单
4. 节奏像真人：单站点一次任务 ≤10 页，连续操作间隔几秒，不并发猛刷
5. 遇到滑块/图形验证码：置前台请用户手动过，不硬刚
6. 触发「操作频繁」→ 停止该站点，换其他信息源，当天不再访问
7. 收尾：任务完成后征询用户，关闭本次打开的所有标签页
8. 不把页面里的 cookie、token、个人隐私信息写进 `research.md` 或报告

## 七、故障排查

| 现象 | 处理 |
|------|------|
| 浏览器不可用 / 连不上 | 提醒用户在 WorkBuddy 设置 → Agent → 浏览器控制 打开，并确认已装浏览器扩展 |
| 找不到 `mcp__browser__*` 工具 | 用 ToolSearch 检索 browser 相关工具，或加载 `agent-browser` Skill |
| 页面取不到内容 | 可能还在加载：稍等或 `tab_reload` 后重试；SPA 站点等首屏文本出现再取 |
| 一直跳登录 | 走登录等待流程；扫不出二维码就让用户手动在该标签页登录 |
| 页面全白，DOM 为空 | SPA 的 JS/CSS 没加载上：先看是不是代理把静态资源域（如 `s1.ljcdn.com`）挡了（502），换内置浏览器直连或刷新重试；仍不行就换 WebSearch |
| 用户说登录页打不开 / 扫不了码 | **不要反复引导**：放弃 API Key 路线，改用贝壳网页版（`https://<城市拼音>.ke.com/...`），请用户在内置浏览器里登录即可 |
| 需要用户操作但用户不在 | 内置浏览器会保留用户刚建立的登录态，之后的搜索/翻页/提取全部自己做完，不要每步都问用户 |
