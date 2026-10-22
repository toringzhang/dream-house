#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house 微信公众号搜索工具（WorkBuddy 版）

用法（Windows 用 python，macOS/Linux 用 python3）：
  python search_wechat.py --keyword "杭州 未来科技城 小区测评"
  python search_wechat.py --keywords "XX小区 业主" "XX楼盘 交付" --limit 8
  python search_wechat.py --keyword "..." --json              # 结构化输出，便于 Agent 消费
  python search_wechat.py --keyword "..." --fetch-content      # 抓正文（需 playwright）
  python search_wechat.py --url "https://mp.weixin.qq.com/s/xxx"  # 抓单篇正文（需 playwright）

说明：
  - 基础搜索零第三方依赖：有 requests/bs4 时用它们，没有则自动用标准库降级
  - 走搜狗微信，有反爬限频，--limit ≤10，关键词之间已内置间隔
  - --fetch-content / --url 需要 Playwright
  - 结果保存到 .dream-house/data/search-results/wechat_results.txt

降级建议：搜狗触发验证码时，改用 references/browser_search.md 的 WorkBuddy 浏览器通道。
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dh_common import DEFAULT_HEADERS, fetch_html, parse_list  # noqa: E402

OUTPUT_PATH = os.path.join(".dream-house", "data", "search-results", "wechat_results.txt")
SOGOU_BASE = "https://weixin.sogou.com/"


def sogou_search(keyword: str, limit: int = 5) -> list:
    """搜狗微信搜索，返回 [{title, url, account, summary, date, keyword}]"""
    results = []
    page = 1
    while len(results) < limit and page <= 2:
        params = {"type": "2", "query": keyword, "page": str(page)}
        url = SOGOU_BASE + "weixin?" + urllib.parse.urlencode(params)
        headers = dict(DEFAULT_HEADERS)
        headers["Referer"] = SOGOU_BASE
        html_text = fetch_html(url, headers=headers)
        if not html_text:
            print("[提示] 未拿到结果，可能触发搜狗反爬；建议改用浏览器通道", file=sys.stderr)
            break
        items = parse_list(html_text, container_marker="news-list",
                           account_marker=("all-time-y2", "account"),
                           date_marker="s2",
                           base_url=SOGOU_BASE)
        if not items:
            break
        for it in items:
            if len(results) >= limit:
                break
            it["keyword"] = keyword
            results.append(it)
        page += 1
        time.sleep(2)  # 反爬限速
    return results


def fetch_article(url: str) -> str:
    """用 Playwright 抓取微信文章正文。"""
    try:
        from playwright.sync_api import sync_playwright  # noqa: WPS433 可选依赖
    except ImportError:
        print("[提示] 未安装 playwright，无法抓取正文。"
              "安装：python -m pip install playwright && python -m playwright install chromium",
              file=sys.stderr)
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            el = page.query_selector("#js_content") or page.query_selector(".rich_media_content")
            text = el.inner_text().strip() if el else ""
            browser.close()
            return text
    except Exception as e:
        print(f"[抓取失败] {url}: {e}", file=sys.stderr)
        return ""


def save_and_print(all_results: list, output: str):
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    lines = []
    for i, r in enumerate(all_results, 1):
        lines.append(f"### {i}. {r['title']}")
        meta = []
        if r.get("account"):
            meta.append(f"公众号: {r['account']}")
        if r.get("date"):
            meta.append(f"时间: {r['date']}")
        meta.append(f"关键词: {r.get('keyword', '')}")
        lines.append("- " + " | ".join(meta))
        lines.append(f"- 链接: {r['url']}")
        if r.get("summary"):
            lines.append(f"- 摘要: {r['summary']}")
        if r.get("content"):
            lines.append(f"\n{r['content']}\n")
        lines.append("")

    header = (f"# 微信搜索结果（{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}）\n\n")
    with open(output, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))

    print(f"已保存 {len(all_results)} 条结果到 {output}")
    for i, r in enumerate(all_results, 1):
        date_info = f" | {r['date']}" if r.get("date") else ""
        print(f"{i}. {r['title']} [{r.get('account', '')}{date_info}]")
        print(f"   {r['url']}")


def main():
    parser = argparse.ArgumentParser(description="dream-house 微信公众号搜索")
    parser.add_argument("--keyword", help="单个搜索关键词")
    parser.add_argument("--keywords", nargs="+", help="多个搜索关键词")
    parser.add_argument("--limit", type=int, default=5, help="每个关键词返回条数（建议 ≤10）")
    parser.add_argument("--fetch-content", action="store_true", help="抓取每篇文章正文（需 playwright）")
    parser.add_argument("--url", help="直接抓取单篇文章正文（需 playwright）")
    parser.add_argument("--output", default=OUTPUT_PATH, help=f"输出文件路径（默认 {OUTPUT_PATH}）")
    parser.add_argument("--json", action="store_true", help="额外向 stdout 输出 JSON 结果")
    args = parser.parse_args()

    if args.url:
        content = fetch_article(args.url)
        if content:
            save_and_print([{
                "title": args.url, "url": args.url, "account": "",
                "summary": "", "date": "", "keyword": "", "content": content,
            }], args.output)
        return

    keywords = []
    if args.keyword:
        keywords.append(args.keyword)
    if args.keywords:
        keywords.extend(args.keywords)
    if not keywords:
        parser.print_help()
        sys.exit(1)

    if args.limit > 10:
        print("[警告] limit > 10 容易触发搜狗反爬验证码，已自动调整为 10", file=sys.stderr)
        args.limit = 10

    all_results = []
    for kw in keywords:
        print(f"[搜索] {kw} ...")
        results = sogou_search(kw, args.limit)
        print(f"  找到 {len(results)} 条")
        all_results.extend(results)
        time.sleep(2)

    if args.fetch_content:
        for r in all_results:
            print(f"  抓取正文: {r['title'][:30]} ...")
            r["content"] = fetch_article(r["url"])
            time.sleep(1)

    save_and_print(all_results, args.output)

    if args.json:
        print("\n===JSON===")
        print(json.dumps(all_results, ensure_ascii=False, indent=2))

    if not all_results:
        print("\n[提示] 结果为零：可能是搜狗反爬。改用浏览器通道，或换用小红书/知乎渠道。",
              file=sys.stderr)


if __name__ == "__main__":
    main()
