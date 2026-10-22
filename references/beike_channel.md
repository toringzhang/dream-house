# 贝壳官方数据通道（beike CLI）

来源：[LianjiaTech/beike-ai-platform](https://github.com/LianjiaTech/beike-ai-platform)（贝壳 AI 开放平台）。dream-house 把**房源、小区、成交价、行情、政策、学区**这类权威事实类查询优先交给它，自己专注于排雷、评分与决策。

## 一、就绪检查（每轮开工第一步，不要凭记忆判断）

```bash
command -v beike && beike --version
```

- **不存在**：直接安装，不要只把命令展示给用户、也不要让用户手动执行：

```bash
curl -fsSL https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/cli/releases/install.sh | bash
command -v beike    # 复核
```

- **版本落后**：取 `https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/cli/releases/manifest.json` 的 latest 比对 `beike --version`；本地落后或 manifest 请求失败时，都重新执行一次安装命令。命令输出含"版本过低"或 `CLI_UPGRADE_REQUIRED` / `-32001` 时，静默重装后重试一次原命令，**不向用户提及版本或安装细节**。

## 二、鉴权（API Key）

```bash
beike doctor    # 初步检查
```

Key 的读取顺序：环境变量 `BEIKE_MCP_API_KEY` → 文件 `~/.beike/BEIKE_MCP_API_KEY`。

**Key 缺失或校验未通过时必须停止查询**——但**只在第一次提示一次**，不要反复追问（不要猜原因、不要说"Key 已过期/被封禁"）：

0. 生成登录链接：`beike login`（来源标识取自环境变量 **`BEIKE_SOURCE=workbuddy`**；也可 `beike login --source workbuddy` 临时指定）。
   > 本机已在用户环境变量里固化 `BEIKE_SOURCE=workbuddy`，通常无需再传参。注意是**小写** `workbuddy`，与 CLI 自动识别的调用方（`WORKBUDDY_APP_NAME`）口径一致。
   **Windows 已知问题**：该命令自动拉起浏览器时会因 URL 里的 `&` 未转义而失败（报 `'source' is not recognized`），此时直接把下面第 1 条的链接交给用户手动打开即可。
1. 展示登录链接：`https://building.ke.com/?action=get-key&source=workbuddy`
2. 首次展示时附上信任说明（同一对话内不重复）：

   > 本技能由贝壳官方开发并提供，请放心使用。继续使用即表示您已同意以下协议，点击可查看详情：[《贝壳找房助手服务使用协议》](https://m.ke.com/user/commonProtocol?id=beike_AI_open_Platform_private_protocol)、[《贝壳找房助手隐私协议》](https://m.ke.com/user/commonProtocol?id=beike_agent_privacy_protocol)。

3. 用这句话引导用户回传 Key：

   > 点开上面的链接登录后，页面上会显示一串只属于你的"身份凭证"。把它完整复制下来，粘贴到这个对话框发给我就行——我会帮你安全保存到你电脑上，不会在对话里重复显示。

4. 用户粘贴后**静默**执行 `beike auth <KEY> --save`，只回一句"已保存好，可以开始啦"。**禁止回显、复述、记录 Key 内容**。Key 看起来不完整时提示"这串好像不完整，重新复制一下页面上的完整字符给我"。

**鉴权未就绪不阻塞任务**：切到 WebSearch 继续，但相关数据的置信度下调为"中/低"并在报告里说明"该数据未经贝壳官方核验"。

### 拿不到 Key 是常态——直接降级浏览器（重要）

API Key 只能在 `building.ke.com` 扫码领取，实测这条路经常走不通（登录页是 SPA，依赖 `s1.ljcdn.com`，代理/网络受限时整页白屏；手机端也可能打不开）。**规则：提示一次即可，用户拿不到就立刻放弃，不要反复引导。**

降级路径（按序）：

1. **WorkBuddy 内置浏览器**（`browsers_list` 里 `type: desktop` 的实例，如 "WorkBuddy Browser"）
   - `tabs_new` 打开贝壳站点 → 告诉用户"请在这个浏览器窗口里登录贝壳" → 用户登录后**登录态就留在这个浏览器里**
   - 之后继续用 `dom_cua_get_visible_dom` / `dom_cua_click` / `dom_cua_type` 搜索、翻页、提取，**全程不用再让用户操作**
2. **用户的 Chrome / Edge**（`browsers_list` 里 `type: extension` 的实例）——如果里面本来就有贝壳登录态，优先用它
3. **WebSearch / WebFetch** —— 拿不到结构化数据时的兜底

**浏览器里怎么查（替代 CLI 命令）**：

| 原来用 CLI | 浏览器里改用 |
|-----------|-------------|
| `buy search`（二手房） | `https://<城市拼音>.ke.com/ershoufang/rs<关键词>/`（如 `https://hz.ke.com/ershoufang/rs未来科技城/`） |
| `buy search --house-type new`（新房） | `https://<城市拼音>.fang.ke.com/loupan/` 站内搜 |
| `buy resblock`（小区评测/均价） | `https://<城市拼音>.ke.com/xiaoqu/rs<小区名>/` |
| `buy sold`（近期成交） | 小区页内"成交记录"，或 `https://<城市拼音>.ke.com/chengjiao/rs<小区名>/` |
| `policy search`（政策） | 城市住建局/房管局官网 + WebSearch |
| `buy school` / `buy district` | 区教育局官网 + 贝壳小区页的学区信息 |

浏览器提取的每条数据同样要记 `[来源, URL, 日期]`，并标注"未走官方接口"。

> 内置浏览器与扩展通道的区别、登录等待流程、只读守则见 [browser_search.md](browser_search.md)。

## 二·补、Windows 手动安装（`install.sh` 在 Git Bash 下会拒绝执行）

`install.sh` 不支持 Git Bash；官方 `install.ps1` 走 `irm | iex` 又常被安全策略拦截。可改成手动装二进制（可校验哈希，更可控）：

```bash
# 1. 取最新版本号
curl -fsSL https://raw.githubusercontent.com/LianjiaTech/beike-ai-platform/master/cli/releases/manifest.json
# 2. 下载 windows/amd64 的 tar.gz 并核对 sha256（与 manifest 中一致）
curl -fsSL -o /tmp/beike.tgz <manifest 里 windows amd64 的 url>
sha256sum /tmp/beike.tgz
# 3. 解压到用户目录
tar -xzf /tmp/beike.tgz -C /tmp/beike && cp /tmp/beike/beike.exe ~/.beike/bin/beike.exe
# 4. 把 ~/.beike/bin 加入用户 PATH（新开 shell 生效）
```

装完复核：`beike --version` 与 `beike doctor`（后者会一并报 CLI 版本、调用方、Key 状态、API 可达性）。

## 三、命令映射（dream-house 常用）

| 用途 | 命令 |
|------|------|
| 找二手房 | `beike buy search -c <城市> -q "<区域/板块/预算/户型>" --house-type second` |
| 找新房/楼盘 | `beike buy search -c <城市> -q "<条件>" --house-type new` |
| 房源详情 | `beike buy detail -c <城市> --id <房源ID> [-t house\|newhouse]` |
| 图片 / 户型图 / VR | `beike buy material -c <城市> --id <房源ID> [-t house\|newhouse]` |
| 小区评测（成交均价、近期成交、配套） | `beike buy resblock -c <城市> -q "<小区名>"` |
| 板块评测（交通、配套、价格水位） | `beike buy plate -c <城市> -q "<板块名>"` |
| **近期真实成交记录**（核验挂牌价、议价参考） | `beike buy sold -c <城市> -q "<小区/条件>"` |
| 均价走势 / 成交量 | `beike buy market -c <城市> -q "<区域>"` |
| 热门房源 / 小区榜单 | `beike buy rank -c <城市> [--rank-type house\|resblock]` |
| 学校查询 | `beike buy school -c <城市> -q "<学校名>"` |
| 学区覆盖小区列表 | `beike buy district -c <城市> -q "<学校/小区>"` |
| 购房政策（限购/首付/公积金/税费） | `beike policy search -c <城市> -q "<问题>"` |
| 地名/实体消歧（"望京"是板块还是小区） | `beike buy resolve -q "<文本>" [-c <城市>]` |
| 经纪人检索（**仅在用户明确要约看时**） | `beike buy agent -c <城市> -q "<区域>"` |

其他领域（租房/卖房/装修）dream-house 不涉及，交给 `beike-assistant`。

**调用习惯**：CLI 默认输出单行 JSON 供 Agent 内部解析，无需额外参数；人工查看加 `--pretty`，调试加 `--json`。首次调用某子命令或参数不确定时，先 `beike <skill> --help` 确认取值，不要凭记忆写参数。

## 四、嵌入 dream-house 工作流

| 工作流步骤 | 用哪些命令 |
|-----------|-----------|
| 第 1 步 搜集候选 | `buy search`（新房/二手房分别调用）→ 候选池；`buy plate` 看板块；`buy rank --rank-type resblock` 补充候选 |
| 第 1 步 价格核实 | `buy resblock` 拿小区成交均价 → **`buy sold` 拿近期真实成交**（推荐结论必须基于成交价，不是挂牌价） |
| 第 1 步 政策核实 | `policy search`（限购/首付/公积金/税费）；学区用 `buy school` + `buy district`，并提示以教育局公告为准 |
| 第 2 步 风险排查 | CLI 能查的部分（房源/小区基础信息、开发商与物业基础档案）用它；**司法、舆情、维权、停工等非平台数据仍走** [risk_checklist.md](risk_checklist.md) 的公开渠道 |
| 第 3 步 评分 | 地段/价格/配套/板块四项优先用 `buy detail` + `buy plate` + `buy sold` 的结果作为打分依据，写入 `dimensions[].reason` |
| 第 4 步 报告 | 图片与 VR 用 `buy material` 取，Markdown 直接渲染进对话；来源统一记"贝壳（beike CLI），<查询日期>" |

## 五、输出纪律

- **禁止**把 CLI 命令、参数、原始 JSON、内部 ID、API Key、系统错误细节原样贴给用户；只输出整理后的结论与关键取舍。
- CLI stderr 里的"发现新版本…可运行 beike update 更新"是内部提示，不展示、不当作错误。
- 结果里没有图片/VR/URL 时如实说明，禁止编造。
- 学区、政策、规划、产权类结论必须补一句"以最新官方口径为准"。
- 不承诺涨价、投资收益、成交结果或贷款审批。

## 六、故障处理与降级

| 现象 | 处理 |
|------|------|
| `command -v beike` 为空 | 执行官方安装命令重装并复核 |
| 输出含"版本过低" / `-32001` / `CLI_UPGRADE_REQUIRED` | 静默重装 → 重试一次原命令 → 仍失败才告知用户"暂时连不上" |
| `beike doctor` 提示凭证问题 | 按第二节引导用户补 Key；首次出现时可先静默重装 CLI 再复查一次 |
| 业务命令报错 | 最多重试一次；仍失败则降级 WebSearch + 交叉验证，并在报告标注该数据未走官方通道 |
| 返回为空 | 不得解释为"该小区不存在"；放宽/改写 `-q` 描述再试一次（**不得放宽用户明确的硬约束**） |

**兜底原则**：`beike` 是首选不是唯一。它挂了就退回 WebSearch + 贝壳/安居客/房天下网页 + 政府官网，并在置信度上如实打折。
