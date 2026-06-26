# Claude News

> 每天自动聚合 Claude / Anthropic 相关新闻,一个页面看完。
> Auto-aggregated daily news about Claude & Anthropic — one page, always fresh.

**在线地址**:`https://<你的GitHub用户名>.github.io/claude-news/`（上线后把这里替换成你的真实地址）

---

## 这是什么

一个零成本、全自动的 Claude 新闻聚合页:

- 每天定时从 **Hacker News、Google News、Reddit** 抓取 Claude / Anthropic 相关内容
- 自动去重、按时间排序,生成一个干净的静态网页
- 全程跑在 **GitHub Actions** 上,**不需要服务器、不花一分钱**
- 没有任何第三方依赖,一个 `python3 fetch.py` 就能在本地跑

## 为什么做它

这是我学着把"自己做出来的东西"开源出去的第一个项目。
与其追求完美,不如先做出一个**能跑、能用、每天自动更新**的真东西。

如果它对你有用,欢迎点个 star;如果你想加新的新闻源或改进样式,欢迎提 PR——
这个项目就是为了一起迭代而存在的。

## 本地运行

```bash
python3 fetch.py
```

跑完会在当前目录生成 `index.html`（网页）和 `data.json`（原始数据)。
用浏览器打开 `index.html` 就能看到效果。

> 如果本地报 SSL 证书错误(macOS 自带 Python 常见),临时这样跑一次:
> `CLAUDE_NEWS_INSECURE_SSL=1 python3 fetch.py`

## 它怎么自动更新

`.github/workflows/update.yml` 里配了一个定时任务:
每天 UTC 00:00(北京时间 08:00)自动跑 `fetch.py`,把更新后的页面提交回仓库,
GitHub Pages 随即刷新。你什么都不用做。

也可以去仓库的 **Actions** 页面手动点一下 "Run workflow" 立刻更新。

## 怎么贡献

- **加新闻源**:在 `fetch.py` 里仿照 `fetch_hn()` 写一个新的 `fetch_xxx()`,
  返回 `{title, url, source, time, meta}` 列表,加进 `collect()` 即可
- **改样式**:网页样式全在 `fetch.py` 末尾的 `HTML` 模板里
- **报问题**:开个 issue

## License

[MIT](LICENSE) — 随便用。
