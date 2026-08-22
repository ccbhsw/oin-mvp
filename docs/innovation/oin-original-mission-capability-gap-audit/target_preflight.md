# 真实公开 URL 预检结果

预检在 2026-08-21 以实际 HTTP GET 执行。完整每项 digest/status 在 [`target_preflight.ndjson`](target_preflight.ndjson)；该记录是准备证据，不替代后续 operator 的独立 capture artifact。

| Case | URL family | 实际 HTTP status | 可用于网络实验的事实 | 结论边界 |
| --- | --- | ---: | --- | --- |
| T01 | `example.com/` | 200 | 公开 body 可访问。 | 未经重复 capture 不能称 unchanged。 |
| T02 | `httpbingo.org/uuid` | 200 | 公开 UUID endpoint 可访问。 | 未经至少两 capture 不能称 changed。 |
| T03 | `httpbingo.org/redirect-to` | 302 | `Location: https://example.com/` 已被实际接收。 | redirect 不等同 target identity merge。 |
| T04 | `en.wikipedia.org/wiki/Saturn` | 200 | 公开 HTML body 已可访问，供后续 canonical link extraction。 | canonical relation only if actual HTML evidence is retained. |
| T05 | `httpbingo.org/headers` | 200 | echo target 可接收不同 request headers。 | 显示请求差异，不自动证明 origin language representation varies. |
| T06 | `anything?ref=alpha` | 200 | query target 可访问。 | No automatic coalescing with beta. |
| T07 | `anything?ref=beta` | 200 | query target 可访问。 | No automatic coalescing with alpha. |
| T08 | `status/503` | 503 | actual server-error response can be captured. | A captured 503 is not absence of a URL/history. |
| T09 | `ip` | 200 | public egress-response target accessible. | All operators share sandbox egress; no genuine independent geo/CDN experiment. |

**Phase-4 disposition.** T01–T08 are available for actual independent capture. T09 is retained solely as an environment-boundary record. Fragment variation is not sent in HTTP requests by RFC URI semantics and will be reported as unavailable as an HTTP capture differentiation test. No target relies on fabricated content or a controlled local page.
