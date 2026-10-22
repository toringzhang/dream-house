#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house 小红书口碑搜索工具（WorkBuddy 版，三级降级）

降级层级：
  L0  xiaohongshu-skills（外部 skill，用你自己的浏览器登录态，只读搜索，最可靠）
      python <xhs_dir>/scripts/cli.py search-feeds --keyword "XX小区 踩坑"
      → 详见 references/social_search.md；本脚本不负责 L0
  L1  搜索引擎 site:xiaohongshu.com 间接搜（默认，零配置零依赖）
  L2  .dream-house/.env 配置 XHS_COOKIE 后 Playwright 直搜（Cookie 失效自动回落 L1）
  L3  都被风控 → references/browser_search.md 的 WorkBuddy 浏览器通道

用法（Windows 用 python，macOS/Linux 用 python3）：
  python search_xiaohongshu.py --keyword "XX小区 踩坑"
  python search_xiaohongshu.py --keyword "XX楼盘 交付" --mode direct
  python search_xiaohongshu.py --keyword "XX小区 物业" --json

结果保存到 .dream-house/data/search-results/xhs_results.txt
"""

import argparse
import datetime
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dh_common import DEFAULT_HEADERS, fetch_html, parse_list  # noqa: E402

OUTPUT_PATH = os.path.join(".dream-house", "data", "search-results", "xhs_results.txt")
ENV_PATH = os.path.join(".dream-house", ".env")
XHS_BASE = "https://www.xiaohongshu.com"


def load_cookie() -> str:
    """从 .env 文件或环境变量读取 XHS_COOKIE。"""
    cookie = os.environ.get("XHS_COOKIE", "")
    if cookie:
        return cookie
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("XHS_COOKIE="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _bing_query(query: str, limit: int) -> list:
    url = "https://cn.bing.com/search?" + urllib.parse.urlencode(
        {"q": query, "ensearch": "0", "count": str(min(limit * 3, 30))})
    html_text = fetch_html(url)
    if not html_text:
        return []
    out = []
    for it in parse_list(html_text, li_marker="b_algo"):
        it["source"] = "bing"
        out.append(it)
    return out


def search_engine_query(keyword: str, limit: int) -> list:
    """L1：搜索引擎间接搜。Bing 常忽略 site: 语法，故双查询互补 + 站内过滤。"""
    # 查询 1：限定站内；查询 2：带上"小红书"字样，靠自然结果命中
    raw = _bing_query(f"site:xiaohongshu.com {keyword}", limit) \
        + _bing_query(f"{keyword} 小红书", limit)

    seen, results = set(), []
    for it in raw:
        url = it.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        results.append(it)

    def is_xhs(it):
        return "xiaohongshu.com" in it.get("url", "") or "小红书" in it.get("title", "")

    in_site = [it for it in results if is_xhs(it)]
    if in_site:
        return in_site[:limit]

    # 站内没命中：返回泛结果但明确告知，避免静默给出无关内容
    if results:
        print("[L1 提示] 未命中小红书站内结果，以下为相关网页；"
              "建议改用 L0（xiaohongshu-skills）或 L3（WorkBuddy 浏览器通道）", file=sys.stderr)
    return results[:limit]


def direct_search(keyword: str, limit: int, cookie: str) -> list:
    """L2：Playwright + Cookie 直搜小红书。前端结构变化频繁，失败时返回空。"""
    try:
        from playwright.sync_api import sync_playwright  # noqa: WPS433 可选依赖
    except ImportError:
        print("[提示] 未安装 playwright，降级到搜索引擎间接搜索", file=sys.stderr)
        return []

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"],
                                          locale="zh-CN")
            cookie_pairs = []
            for pair in cookie.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookie_pairs.append({
                        "name": k.strip(), "value": v.strip(),
                        "domain": ".xiaohongshu.com", "path": "/",
                    })
            if cookie_pairs:
                context.add_cookies(cookie_pairs)
            page = context.new_page()
            search_url = (f"{XHS_BASE}/search_result?keyword="
                          + urllib.parse.quote(keyword))
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if "login" in page.url or page.query_selector(".login-container"):
                print("[提示] Cookie 已失效，请更新 .dream-house/.env 中的 XHS_COOKIE；"
                      "本次降级为间接搜索", file=sys.stderr)
                browser.close()
                return []

            cards = page.query_selector_all("section.note-item")
            for card in cards[:limit]:
                try:
                    a = card.query_selector("a.title") or card.query_selector("a.cover")
                    title_el = card.query_selector(".title") or card.query_selector("a.title span")
                    author_el = card.query_selector(".author .name") or card.query_selector(".author")
                    title = title_el.inner_text().strip() if title_el else ""
                    author = author_el.inner_text().strip() if author_el else ""
                    href = a.get_attribute("href") if a else ""
                    if href and href.startswith("/"):
                        href = XHS_BASE + href
                    if title:
                        results.append({
                            "title": title, "url": href,
                            "summary": f"作者: {author}", "source": "xiaohongshu",
                        })
                except Exception:
                    continue
            browser.close()
    except Exception as e:
        print(f"[L2 直搜失败] {e}，降级为间接搜索", file=sys.stderr)
        return []
    return results


def main():
    parser = argparse.ArgumentParser(description="dream-house 小红书口碑搜索")
    parser.add_argument("--keyword", required=True, help="搜索关键词，如 'XX小区 踩坑'")
    parser.add_argument("--limit", type=int, default=8, help="返回条数（默认 8）")
    parser.add_argument("--mode", choices=["auto", "search-engine", "direct"], default="auto",
                        help="auto=有 Cookie 则直搜否则间接搜（默认）；search-engine=强制间接搜；direct=强制直搜")
    parser.add_argument("--output", default=OUTPUT_PATH, help=f"输出文件路径（默认 {OUTPUT_PATH}）")
    parser.add_argument("--json", action="store_true", help="额外向 stdout 输出 JSON 结果")
    args = parser.parse_args()

    cookie = load_cookie()
    results = []
    mode_used = ""

    use_direct = (args.mode == "direct") or (args.mode == "auto" and cookie)
    if use_direct:
        if not cookie:
            print("[提示] 未配置 XHS_COOKIE，无法直搜，降级为间接搜索", file=sys.stderr)
        else:
            print(f"[L2 直搜小红书] {args.keyword} ...")
            results = direct_search(args.keyword, args.limit, cookie)
            if results:
                mode_used = "小红书直搜"

    if not results:
        print(f"[L1 搜索引擎间接搜] site:xiaohongshu.com {args.keyword} ...")
        results = search_engine_query(args.keyword, args.limit)
        mode_used = "搜索引擎间接搜"

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    lines = [f"# 小红书搜索结果（{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}）",
             f"关键词: {args.keyword} | 模式: {mode_used}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"- 链接: {r['url']}")
        if r.get("summary"):
            lines.append(f"- 摘要: {r['summary']}")
        lines.append("")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"已保存 {len(results)} 条结果到 {args.output}（模式: {mode_used}）")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}")
        print(f"   {r['url']}")

    if args.json:
        print("\n===JSON===")
        print(json.dumps(results, ensure_ascii=False, indent=2))

    if not results:
        print("\n[提示] 结果为零：可能已被风控。建议改用 L0（xiaohongshu-skills）"
              "或 L3（WorkBuddy 浏览器通道）。", file=sys.stderr)
    elif mode_used == "搜索引擎间接搜" and not cookie:
        print("\n[提示] 配置 .dream-house/.env 中的 XHS_COOKIE 可解锁小红书直搜；"
              "更推荐安装 xiaohongshu-skills 走真实登录态", file=sys.stderr)


if __name__ == "__main__":
    main()
