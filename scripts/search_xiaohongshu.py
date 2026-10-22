#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house 小红书口碑搜索工具（两级自动降级）

用法：
  python3 search_xiaohongshu.py --keyword "XX小区 踩坑"
  python3 search_xiaohongshu.py --keyword "XX楼盘 交付" --mode direct   # 强制直搜（需 Cookie）

工作级别：
  L1（默认，零配置）：通过搜索引擎 site:xiaohongshu.com 间接搜索，拿标题+摘要
  L2（增强）：.dream-house/.env 或环境变量配置 XHS_COOKIE 后，用 Playwright 直搜小红书

未配置 Cookie 或未安装 playwright 时自动降级 L1，不报错不阻塞。
结果保存到 .dream-house/data/search-results/xhs_results.txt
"""

import argparse
import os
import sys
import time
import urllib.parse
from datetime import datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

OUTPUT_PATH = os.path.join(".dream-house", "data", "search-results", "xhs_results.txt")
ENV_PATH = os.path.join(".dream-house", ".env")


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


def search_engine_query(keyword: str, limit: int) -> list:
    """L1：必应搜索 site:xiaohongshu.com，返回 [{title, url, summary}]"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("缺少依赖，请先执行: pip3 install requests beautifulsoup4", file=sys.stderr)
        sys.exit(1)

    q = f"site:xiaohongshu.com {keyword}"
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": q, "count": str(min(limit * 2, 30))})
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        print(f"[L1 搜索失败] {e}", file=sys.stderr)
        return []
    if resp.status_code != 200:
        print(f"[L1 搜索失败] HTTP {resp.status_code}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        if len(results) >= limit:
            break
        a = li.select_one("h2 a")
        if not a:
            continue
        href = a.get("href", "")
        title = a.get_text(strip=True)
        p = li.select_one(".b_caption p")
        summary = p.get_text(strip=True) if p else ""
        results.append({"title": title, "url": href, "summary": summary, "source": "bing"})
    return results


def direct_search(keyword: str, limit: int, cookie: str) -> list:
    """L2：Playwright + Cookie 直搜小红书。小红书前端结构变化频繁，失败时返回空。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[提示] 未安装 playwright，降级到搜索引擎间接搜索", file=sys.stderr)
        return []

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=UA, locale="zh-CN")
            # 注入 cookie
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
            search_url = ("https://www.xiaohongshu.com/search_result?keyword="
                          + urllib.parse.quote(keyword))
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if "login" in page.url or page.query_selector(".login-container"):
                print("[提示] Cookie 已失效，请更新 .dream-house/.env 中的 XHS_COOKIE；本次降级为间接搜索", file=sys.stderr)
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
                        href = "https://www.xiaohongshu.com" + href
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

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    lines = [f"# 小红书搜索结果（{datetime.now().strftime('%Y-%m-%d %H:%M')}）",
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

    if mode_used == "搜索引擎间接搜" and not cookie:
        print("\n[提示] 配置 .dream-house/.env 中的 XHS_COOKIE 可解锁小红书直搜（正文+评论）", file=sys.stderr)


if __name__ == "__main__":
    main()
