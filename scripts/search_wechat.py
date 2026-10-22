#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house 微信公众号搜索工具

用法：
  python3 search_wechat.py --keyword "杭州 未来科技城 小区测评"
  python3 search_wechat.py --keywords "XX小区 业主" "XX楼盘 交付" --limit 8
  python3 search_wechat.py --keyword "..." --fetch-content      # 需 playwright
  python3 search_wechat.py --url "https://mp.weixin.qq.com/s/xxx"  # 需 playwright

说明：
  - 基础搜索通过搜狗微信（requests + beautifulsoup4），有反爬限频，请控制频率
  - --fetch-content / --url 用 Playwright 抓取正文（微信文章由 JS 动态渲染）
  - 结果保存到 .dream-house/data/search-results/wechat_results.txt
"""

import argparse
import os
import sys
import time
import urllib.parse
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

OUTPUT_PATH = os.path.join(".dream-house", "data", "search-results", "wechat_results.txt")


def sogou_search(keyword: str, limit: int = 5) -> list:
    """搜狗微信搜索，返回 [{title, url, account, summary, date}]"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("缺少依赖，请先执行: pip3 install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    results = []
    page = 1
    while len(results) < limit and page <= 2:
        params = {"type": "2", "query": keyword, "page": str(page)}
        url = "https://weixin.sogou.com/weixin?" + urllib.parse.urlencode(params)
        headers = {
            "User-Agent": UA,
            "Referer": "https://weixin.sogou.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            print(f"[搜索失败] {keyword}: {e}", file=sys.stderr)
            break
        if resp.status_code != 200:
            print(f"[搜索失败] {keyword}: HTTP {resp.status_code}（可能触发反爬，请稍后再试）", file=sys.stderr)
            break
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("ul.news-list > li")
        if not items:
            break
        for item in items:
            if len(results) >= limit:
                break
            a = item.select_one("h3 a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            summary_el = item.select_one("p.txt-info")
            summary = summary_el.get_text(strip=True) if summary_el else ""
            account_el = item.select_one("a.account")
            account = account_el.get_text(strip=True) if account_el else ""
            time_el = item.select_one("span.s2")
            date_str = ""
            if time_el:
                t = time_el.get_text(strip=True)
                date_str = t
                # 搜狗时间戳兼容
                script = time_el.find("script")
                if script and "document.write" in (script.string or ""):
                    date_str = ""
            results.append({
                "title": title,
                "url": href,
                "account": account,
                "summary": summary,
                "date": date_str,
                "keyword": keyword,
            })
        page += 1
        time.sleep(2)  # 反爬限速
    return results


def fetch_article(url: str) -> str:
    """用 Playwright 抓取微信文章正文。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[提示] 未安装 playwright，无法抓取正文。安装: pip3 install playwright && python3 -m playwright install chromium", file=sys.stderr)
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=UA)
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
    os.makedirs(os.path.dirname(output), exist_ok=True)
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

    header = f"# 微信搜索结果（{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n\n"
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


if __name__ == "__main__":
    main()
