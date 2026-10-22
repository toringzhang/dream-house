# 用户身份浏览器搜索（chrome-devtools MCP，反风控通道）

当 WebSearch / 脚本搜索被风控（验证码、登录墙、空结果）时，切换到本通道：**通过 chrome-devtools MCP 操作用户的浏览器**搜索。风控系统看到的是用户本人的真实浏览器与登录态，而不是爬虫。

## 依赖

用户的 AI 工具需配置 **chrome-devtools MCP** 并连接到其日常 Chrome（Chrome 144+ 在 `chrome://inspect/#remote-debugging` 开启远程调试后自动连接；或 `--browser-url` 手动连接）。配置完成后浏览器里**已登录的站点直接可用**，未登录的走「登录等待」流程。

启用检测：调用 `list_pages` 能列出用户当前标签页即就绪；报连接失败则提醒用户检查 MCP 配置。

## 常用工具速查

| 工具 | 用途 | 要点 |
|------|------|------|
| `list_pages` | 列出标签页 | 拿 pageId；也用于健康检查 |
| `new_page` | 打开搜索页 | 日常搜索传 `background: true` 减少打扰 |
| `take_snapshot` | 拿 a11y 树（uid） | 页面结构不明时用它找搜索框/按钮 uid |
| `evaluate_script` | **结构化提取主力** | `function` 写 `"() => ..."`，只读操作传 `waitForStableDom: false` |
| `click` / `fill` / `press_key` | 交互 | uid 来自 snapshot |
| `wait_for` | 等文本出现 | 登录等待用，长 timeout |
| `select_page` | 切页/置前台 | `bringToFront: true` 用于请用户登录 |
| `take_screenshot` | 截图 | 扫码登录时把二维码截给用户 |
| `close_page` | 关闭标签页 | **只关自己开的**；最后一个页面关不掉属正常 |

## 标准搜索流程

```text
1. new_page(url=搜索URL, background: true)          → 记下返回的 pageId
2. evaluate_script 检测登录墙（见下）
3. 已登录 → evaluate_script 提取结构化结果
   未登录 → 登录等待流程（见下）
4. 每条结果记录 [来源, URL, 日期] 到 research.md，来源标注「（浏览器身份搜索）」
5. 任务收尾：列出本次打开的 pageId，征得同意后 close_page 逐一关闭
```

登录墙检测片段（通用）：

```js
() => ({
  loginWall: !!document.querySelector('.login-container')
    || !!Array.from(document.querySelectorAll('button,div')).find(e => e.innerText?.trim() === '登录'),
  title: document.title
})
```

## 登录等待流程（核心交互）

发现登录墙后**不要尝试任何绕过**，直接让用户登录：

1. `select_page(pageId, bringToFront: true)` 把登录页置前台
2. 告诉用户："需要登录 {站点} 才能搜索，已在浏览器打开登录页，登录完成后告诉我"
3. 用户说「好了」→ 重新执行登录墙检测验证通过 → 继续搜索
4. 加速项（可选）：`wait_for(pageId, text: ["登录后才会出现的标志文本"], timeout: 300000)` 自动感知登录完成，超时再转人工确认
5. 扫码场景：`take_screenshot` 把二维码截给用户扫

登录态由用户浏览器自身持久化，与 skill 无关，下次直接用。

## 站点搜索手册

> 2026-10 实测标注。选择器随前端改版可能失效，失效时 `take_snapshot` 重新定位后再写 `evaluate_script`。

| 站点 | 搜索 URL 模板（`<kw>` 为 URL 编码关键词） | 实测状态 |
|------|------------------------------------------|----------|
| 小红书 | `https://www.xiaohongshu.com/search_result?keyword=<kw>` | 匿名必弹登录墙；登录后正常 |
| Bing | `https://www.bing.com/search?q=<kw>` | 匿名可用 |
| 知乎 | `https://www.zhihu.com/search?type=content&q=<kw>` | 匿名列表可读，登录后更全 |
| 贝壳（小区） | `https://<城市拼音>.ke.com/xiaoqu/rs<kw>/` | 部分页面登录墙 |
| 安居客 | `https://<城市拼音>.anjuke.com/community/?kw=<kw>` | 验证码频繁，建议登录 |
| 搜狗微信 | `https://weixin.sogou.com/weixin?type=2&query=<kw>` | 高频触发验证码 |
| 微博 | `https://s.weibo.com/weibo?q=<kw>` | 登录后更全 |
| 黑猫投诉 | `https://tousu.sina.com.cn/index/search/?keywords=<kw>` | 基本可读 |

已实测的提取片段：

```js
// 小红书搜索结果（需登录）
() => Array.from(document.querySelectorAll('section.note-item')).slice(0,10).map(n => ({
  title: n.querySelector('.title')?.innerText?.trim(),
  author: n.querySelector('.author .name')?.innerText?.trim(),
  url: n.querySelector('a')?.href
}))

// Bing 搜索结果
() => Array.from(document.querySelectorAll('li.b_algo')).slice(0,10).map(li => ({
  title: li.querySelector('h2')?.innerText,
  url: li.querySelector('h2 a')?.href,
  summary: li.querySelector('.b_caption p')?.innerText
}))
```

进入详情页：`click` 结果链接或 `new_page` 打开 URL，正文用 `evaluate_script` 提取 `document.body.innerText` 后按段截取。

## 操作守则（这是用户的日常浏览器，必须遵守）

1. **不动用户已有标签页**：只操作自己 `new_page` 打开的 pageId；`list_pages` 只用于发现和盘点，不得对用户既有页面执行 click/fill/close
2. 批量搜索默认 `background: true`；只有需要用户操作（登录、过验证码）时才 `bringToFront`
3. **只读**：搜索、浏览、提取。绝不代用户发帖、评论、点赞、关注、私信
4. 节奏像真人：单站点一次任务 ≤10 页，连续操作间隔几秒，不并发猛刷
5. 遇到滑块/图形验证码：置前台请用户手动过，不硬刚
6. 触发「操作频繁」→ 停止该站点，换其他信息源，当天不再访问
7. 收尾清理：任务完成后征询用户，关闭本次打开的所有标签页

## 故障排查

| 现象 | 处理 |
|------|------|
| `list_pages` 报连接失败 | 提醒用户检查 chrome-devtools MCP 配置与 Chrome 远程调试开关 |
| snapshot 找不到元素 | 页面可能还在加载：`wait_for` 等标志文本后再 snapshot |
| `evaluate_script` 返回空 | 站点改版：`take_snapshot` 看新结构，重写选择器 |
|  uid 失效报错 | 页面已变化，重新 `take_snapshot` 拿新 uid |
| 登录态失效 | 重新走登录等待流程；小红书 cookie 通常数周有效 |
