#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dream-house 脚本公共工具：HTTP 抓取 + 列表解析。

设计目标：**零第三方依赖也能跑**。
- 有 requests 时优先用它（对 gzip/编码/重定向处理更好）
- 没装 requests / beautifulsoup4 时自动降级到标准库 urllib + HTMLParser

WorkBuddy 环境里常见"没有 requests"的情况，所以这里不把第三方库当硬依赖。
"""

import base64
import datetime
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DEFAULT_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def fetch_html(url, headers=None, timeout=15):
    """抓取网页文本。失败返回空串并打印提示（不抛异常，避免中断整个调研流程）。"""
    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)

    try:
        import requests  # noqa: WPS433 可选依赖
        resp = requests.get(url, headers=hdrs, timeout=timeout)
        if resp.status_code != 200:
            print(f"[抓取失败] HTTP {resp.status_code} {url}", file=sys.stderr)
            return ""
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except ImportError:
        pass
    except Exception as e:  # requests 抛错时仍尝试标准库兜底
        print(f"[提示] requests 抓取失败（{e}），改用标准库重试", file=sys.stderr)

    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, errors="replace")
    except Exception as e:
        print(f"[抓取失败] {url}: {e}", file=sys.stderr)
        return ""


class _ListParser(HTMLParser):
    """通用结果列表解析：定位结果项 → 取首个链接(标题+URL)、首个段落(摘要)、指定 class 的账号与时间。"""

    def __init__(self, container_marker=None, li_marker=None,
                 account_marker="account", date_marker="s2"):
        super().__init__(convert_charrefs=True)
        self.container_marker = container_marker
        self.li_marker = li_marker
        self.account_marker = account_marker
        self.date_marker = date_marker

        self.items = []
        self._container_stack = []   # 记录进入的容器标签名，用于精确配平
        self._li_depth = 0
        self._in_item = False
        self._cur = None
        self._a = None        # (href, buf)
        self._h = None        # 标题标签(h1-h3)文本缓冲，优先作为标题
        self._p = None        # buf
        self._acc = None      # buf
        self._date = None     # buf
        self._script_depth = 0

    # ---- 工具 ----
    @staticmethod
    def _cls(attrs):
        for k, v in attrs:
            if k == "class":
                return v or ""
        return ""

    @staticmethod
    def _has(cls, marker):
        """marker 支持字符串或字符串元组（多候选 class 匹配）。"""
        if not marker:
            return False
        markers = (marker,) if isinstance(marker, str) else tuple(marker)
        return any(m in cls for m in markers)

    def _attr(self, attrs, name):
        for k, v in attrs:
            if k == name:
                return v or ""
        return ""

    # ---- 解析回调 ----
    def handle_starttag(self, tag, attrs):
        cls = self._cls(attrs)

        if tag == "script":
            self._script_depth += 1
            return

        if self.container_marker and self.container_marker in cls and tag in ("ul", "ol", "div"):
            self._container_stack.append(tag)

        if tag == "li":
            self._li_depth += 1
            if not self._in_item:
                hit = False
                if self.li_marker and self.li_marker in cls:
                    hit = True
                elif (not self.li_marker) and self.container_marker and self._container_stack:
                    hit = True
                if hit:
                    self._in_item = True
                    self._cur = {"title": "", "url": "", "summary": "",
                                 "account": "", "date": ""}
            return

        if not self._in_item:
            return

        if tag == "a":
            href = self._attr(attrs, "href")
            if self._has(cls, self.account_marker):
                if self._acc is None:
                    self._acc = []
                return
            if self._h is not None and self._cur is not None and not self._cur["url"]:
                self._cur["url"] = href      # 标题行里的链接优先作为结果链接
            if self._a is None:
                self._a = (href, [])
            return

        if tag in ("h1", "h2", "h3") and self._h is None:
            self._h = []
            return

        if tag == "p" and self._p is None:
            self._p = []
            return

        if tag == "span" and self._has(cls, self.account_marker) and self._acc is None:
            self._acc = []
            return

        if tag == "span" and self._has(cls, self.date_marker) and self._date is None:
            self._date = []

    def handle_data(self, data):
        if self._script_depth > 0:
            # 搜狗用 <script>document.write(timeConvert('1568863160'))</script> 渲染时间，
            # 把脚本内容喂给时间缓冲，稍后正则还原成日期；其余脚本内容一律丢弃
            if self._date is not None:
                self._date.append(data)
            return
        if not self._in_item:
            return
        # 多缓冲并行收集：外层标签的文本也要保留
        if self._a is not None:
            self._a[1].append(data)
        if self._h is not None:
            self._h.append(data)
        if self._acc is not None:
            self._acc.append(data)
        if self._p is not None:
            self._p.append(data)
        if self._date is not None:
            self._date.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self._script_depth = max(0, self._script_depth - 1)
            return

        if tag == "a":
            if self._acc is not None:
                if self._cur is not None:
                    self._cur["account"] = "".join(self._acc).strip()
                self._acc = None
            elif self._a is not None:
                href, buf = self._a
                self._a = None
                if self._cur is not None:
                    title = "".join(buf).strip()
                    if title and not self._cur["title"]:
                        self._cur["title"] = title
                        self._cur["url"] = self._cur["url"] or href
            return

        if tag in ("h1", "h2", "h3") and self._h is not None:
            heading = "".join(self._h).strip()
            self._h = None
            if self._cur is not None and heading:
                self._cur["title"] = heading      # 标题行覆盖拼接出的杂文本
            return

        if tag == "p" and self._p is not None:
            summary = "".join(self._p).strip()
            if self._cur is not None and not self._cur["summary"]:
                self._cur["summary"] = summary
            self._p = None
            return

        if tag == "span":
            if self._acc is not None:
                if self._cur is not None and not self._cur["account"]:
                    self._cur["account"] = "".join(self._acc).strip()
                self._acc = None
                return
            if self._date is not None:
                if self._cur is not None:
                    self._cur["date"] = "".join(self._date).strip()
                self._date = None
                return

        if (self.container_marker and self._container_stack
                and self._container_stack[-1] == tag):
            self._container_stack.pop()

        if tag == "li":
            if self._in_item and self._li_depth <= 1:
                if self._cur and self._cur["title"]:
                    self.items.append(self._cur)
                self._in_item = False
                self._cur = None
                self._a = self._p = self._acc = self._date = self._h = None
            self._li_depth = max(0, self._li_depth - 1)


def parse_list(html_text, container_marker=None, li_marker=None,
               account_marker="account", date_marker="s2", base_url=""):
    """解析结果列表，返回 [{title, url, summary, account, date}]。"""
    if not html_text:
        return []
    p = _ListParser(container_marker, li_marker, account_marker, date_marker)
    try:
        p.feed(html_text)
    except Exception as e:
        print(f"[解析失败] {e}", file=sys.stderr)
        return []
    for it in p.items:
        it["url"] = decode_bing_redirect(it["url"])
        if base_url and it["url"].startswith("/"):
            it["url"] = urllib.parse.urljoin(base_url, it["url"])
        it["title"] = " ".join(it["title"].split())
        it["summary"] = " ".join(it["summary"].split())
        it["account"] = " ".join(it["account"].split())
        it["date"] = _normalize_date(it["date"])
    return p.items


def decode_bing_redirect(url: str) -> str:
    """把 Bing 的跳转链接（/ck/a?...&u=a1aHR0...）还原成真实地址。"""
    if "bing.com/ck/a" not in url or "u=" not in url:
        return url
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        raw = qs.get("u", [""])[0]
        if not raw.startswith("a1"):
            return url
        b64 = raw[2:]
        b64 += "=" * (-len(b64) % 4)
        return base64.b64decode(b64).decode("utf-8", errors="replace")
    except Exception:
        return url


def _normalize_date(raw: str) -> str:
    """把搜狗的 timeConvert('1568863160') 之类还原成 YYYY-MM-DD；原样返回无法识别的内容。"""
    if not raw:
        return ""
    m = re.search(r"(1[5-9]\d{8})", raw)
    if m:
        try:
            return datetime.datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError):
            return raw
    return " ".join(raw.split())
