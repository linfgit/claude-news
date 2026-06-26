#!/usr/bin/env python3
"""抓取 Claude / Anthropic 相关新闻,聚合生成静态网页 index.html。
数据源全部免费、无需 API key:Hacker News、Google News、Reddit。
纯标准库,无第三方依赖,python3 fetch.py 直接跑。"""

import os
import ssl
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

UA = "Mozilla/5.0 (claude-news bot; +https://github.com)"
TIMEOUT = 20

# 默认走正常证书校验(GitHub Actions 与生产用)。
# 仅当本地缺系统证书时,临时 export CLAUDE_NEWS_INSECURE_SSL=1 绕过。
_SSL_CTX = (ssl._create_unverified_context()
            if os.environ.get("CLAUDE_NEWS_INSECURE_SSL") == "1" else None)
KEYWORDS = ("claude", "anthropic")   # 标题里命中任一才算相关
MAX_ITEMS = 60                        # 网页最多展示条数
CST = timezone(timedelta(hours=8))    # 北京时间,用于显示


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as r:
        return r.read()


def fetch_hn():
    """Hacker News 官方搜索 API,按时间倒序取最新 story。"""
    items = []
    for kw in ("Claude", "Anthropic"):
        url = ("https://hn.algolia.com/api/v1/search_by_date"
               "?query=%s&tags=story&hitsPerPage=40" % kw)
        try:
            data = json.loads(_get(url))
        except Exception as e:
            print("  [HN] %s 失败: %s" % (kw, e))
            continue
        for h in data.get("hits", []):
            title = h.get("title")
            if not title:
                continue
            link = h.get("url") or ("https://news.ycombinator.com/item?id=%s"
                                    % h.get("objectID"))
            ts = h.get("created_at_i")
            when = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
            items.append({"title": title, "url": link, "source": "Hacker News",
                          "time": when, "meta": "%s 分" % (h.get("points") or 0)})
    return items


def fetch_google_news():
    """Google News RSS 搜索,覆盖各媒体报道。"""
    url = ("https://news.google.com/rss/search?"
           "q=%22Claude%22+Anthropic+AI&hl=en-US&gl=US&ceid=US:en")
    items = []
    try:
        root = ET.fromstring(_get(url))
    except Exception as e:
        print("  [GoogleNews] 失败: %s" % e)
        return items
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        when = None
        pub = it.findtext("pubDate")
        if pub:
            try:
                when = parsedate_to_datetime(pub)
            except Exception:
                pass
        src = (it.findtext("source") or "").strip()
        if src and title.endswith(" - " + src):   # 去掉标题尾部冗余的「 - 媒体名」
            title = title[: -(len(src) + 3)].strip()
        items.append({"title": title, "url": link, "source": "Google News",
                      "time": when, "meta": src})
    return items


def fetch_reddit():
    """Reddit r/ClaudeAI 本周热门(可能偶发 403,失败不影响其他源)。"""
    url = "https://www.reddit.com/r/ClaudeAI/top.json?t=week&limit=30"
    items = []
    try:
        data = json.loads(_get(url))
    except Exception as e:
        print("  [Reddit] 失败: %s" % e)
        return items
    for c in data.get("data", {}).get("children", []):
        d = c.get("data", {})
        title = d.get("title")
        if not title:
            continue
        link = d.get("url_overridden_by_dest") or ("https://reddit.com"
                                                   + d.get("permalink", ""))
        ts = d.get("created_utc")
        when = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
        items.append({"title": title, "url": link, "source": "Reddit",
                      "time": when, "meta": "%s 赞" % (d.get("score") or 0)})
    return items


def relevant(item):
    t = item["title"].lower()
    return any(k in t for k in KEYWORDS)


def dedup(items):
    seen, out = set(), []
    for it in items:
        key = it["title"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def collect():
    all_items = []
    for name, fn in (("Hacker News", fetch_hn),
                     ("Google News", fetch_google_news),
                     ("Reddit", fetch_reddit)):
        print("抓取 %s ..." % name)
        got = fn()
        print("  得到 %d 条" % len(got))
        all_items += got
    all_items = [i for i in all_items if relevant(i)]
    all_items = dedup(all_items)
    # 有时间的排前面(新→旧),无时间的垫底
    all_items.sort(key=lambda i: i["time"] or datetime(1970, 1, 1, tzinfo=timezone.utc),
                   reverse=True)
    return all_items[:MAX_ITEMS]


def human_time(dt):
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    diff = now - dt
    secs = diff.total_seconds()
    if secs < 3600:
        return "%d 分钟前" % max(1, int(secs // 60))
    if secs < 86400:
        return "%d 小时前" % int(secs // 3600)
    if secs < 86400 * 7:
        return "%d 天前" % int(secs // 86400)
    return dt.astimezone(CST).strftime("%Y-%m-%d")


SOURCE_COLOR = {"Hacker News": "#ff6600", "Google News": "#4285f4",
                "Reddit": "#ff4500"}


def render(items):
    updated = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    cards = []
    for it in items:
        color = SOURCE_COLOR.get(it["source"], "#888")
        meta = " · ".join(x for x in (it.get("meta"), human_time(it["time"])) if x)
        title = (it["title"].replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;"))
        cards.append(
            '<a class="card" href="%s" target="_blank" rel="noopener">'
            '<span class="src" style="--c:%s">%s</span>'
            '<span class="title">%s</span>'
            '<span class="meta">%s</span></a>'
            % (it["url"], color, it["source"], title, meta))
    return HTML.replace("{{UPDATED}}", updated)\
               .replace("{{COUNT}}", str(len(items)))\
               .replace("{{CARDS}}", "\n".join(cards))


HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude News · 每日自动聚合</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:0 16px}
.wrap{max-width:760px;margin:0 auto;padding:48px 0 80px}
header{margin-bottom:32px;border-bottom:1px solid #21262d;padding-bottom:24px}
h1{font-size:30px;font-weight:700;letter-spacing:-.5px}
.sub{color:#8b949e;margin-top:8px;font-size:14px}
.list{display:flex;flex-direction:column;gap:2px}
.card{display:flex;flex-direction:column;gap:6px;padding:16px 14px;border-radius:10px;text-decoration:none;color:inherit;transition:background .15s}
.card:hover{background:#161b22}
.src{font-size:11px;font-weight:600;color:var(--c);text-transform:uppercase;letter-spacing:.5px}
.title{font-size:16px;color:#e6edf3;font-weight:500}
.card:hover .title{color:#58a6ff}
.meta{font-size:12px;color:#6e7681}
footer{margin-top:48px;padding-top:24px;border-top:1px solid #21262d;color:#6e7681;font-size:13px;text-align:center}
footer a{color:#58a6ff;text-decoration:none}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>Claude News</h1>
<div class="sub">自动聚合 Claude / Anthropic 相关新闻 · 共 {{COUNT}} 条 · 最后更新 {{UPDATED}}（北京时间）</div>
</header>
<div class="list">
{{CARDS}}
</div>
<footer>
由 GitHub Actions 每天自动抓取生成 · 数据来自 Hacker News / Google News / Reddit<br>
开源项目 · 欢迎 star 与 PR
</footer>
</div>
</body>
</html>
"""


def main():
    items = collect()
    print("\n相关、去重后共 %d 条" % len(items))
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render(items))
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump([{**i, "time": i["time"].isoformat() if i["time"] else None}
                   for i in items], f, ensure_ascii=False, indent=2)
    print("已生成 index.html 和 data.json")


if __name__ == "__main__":
    main()
