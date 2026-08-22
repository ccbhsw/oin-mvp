# IWOH v0.2 — 真实公开 Web Archive Corpus 登记册

**抓取日期：** 2026-08-21 GMT+8。  
**机器可读源：** [`real_corpus_registry.json`](real_corpus_registry.json)。  
**证据纪律：** 本登记册仅纳入实际公开访问的服务、API、replay、WACZ/WARC 或由其直接返回的 metadata。`UNAVAILABLE` 与 `PARTIAL` 不是 archive absence、标准不足或 IWOH 必要性的证据。

## Archive 来源与公开访问边界

| Archive | 实际核验的公开入口 | 可见内容 | 本审计中没有声称拥有的内容 |
| --- | --- | --- | --- |
| Internet Archive Wayback Machine | Availability API、CDX Server、replay | Memento URL、capture datetime、status、CDX digest、URL forms、replay body。 | WARC download、archive-wide completeness、signed archive statement、原始观察者 agency。 |
| Arquivo.pt | CDX Server API、replay | URL、timestamp、status、digest、ARC filename/length/offset、replay body。 | Cross-archive target relation、original agency、shared-ingest proof、signed receipt。 |
| Common Crawl | public collection index、CDX、HTTPS WARC Range | CDX metadata、raw WARC/HTTP header、request context inputs、payload/block digests。 | Memento history、archive-to-archive relation、signed provenance、scope coverage assertion。 |
| Stanford University Press / Webrecorder | public GitHub catalogue、Stanford Stack WACZ download、replay URL | A real downloaded archive package、legacy manifest, CDXJ and WARC evidence. | Current WACZ 1.1.1 conformance、cross-archive evidence exchange、signed WACZ Auth statement。 |
| UK Government Web Archive | collection website、search UI | collection scope and public search/replay entrypoint. | Automated capture timeline; the public URL query reached human verification and was not bypassed. |

Internet Archive documents its Availability, Memento and CDX paths publicly.[1] Arquivo.pt publishes an automatic CDX-server API with JSON and WARC-location fields.[2] Common Crawl publicly exposes WARC source data and index access.[3] Webrecorder’s WACZ specification describes portable WARC packaging, but does not itself define cross-archive historical relation semantics.[4]

## 已核验的真实 evidence records

| ID | Archive | Original URL | Capture datetime | Evidence URL | Access | Evidence boundary |
| --- | --- | --- | --- | --- | --- | --- |
| IA-EXAMPLE-2010 | Internet Archive | `http://example.com/` | 2010-01-02T00:34:10Z | [Availability query](https://archive.org/wayback/available?url=example.com&timestamp=20100101), [replay](https://web.archive.org/web/20100102003410id_/http://example.com/) | AVAILABLE | Replay body was observed; raw WARC/fixity was not obtained. |
| IA-EXAMPLE-2024 | Internet Archive | `http://example.com/` | 2024-01-01T23:58:41Z | [Availability query](https://archive.org/wayback/available?url=example.com&timestamp=20240101), [replay](https://web.archive.org/web/20240101235841id_/http://example.com/) | AVAILABLE | Same URL’s visible replay differs from 2010; this is not source-server truth or causal proof. |
| IA-CDX-EXAMPLE-URL-VARIANTS | Internet Archive | `http://example.com/` | multiple | [CDX query](https://web.archive.org/cdx/search/cdx?url=http%3A%2F%2Fexample.com%2F&matchType=exact&output=json&fl=timestamp,original,statuscode,digest,mimetype&filter=statuscode:200&collapse=digest&limit=20) | AVAILABLE | CDX returns URL forms, timestamps and digests; no target-equivalence rule. |
| ARQUIVO-EXAMPLE-20100323 | Arquivo.pt | `http://www.example.com/` | 2010-03-23T15:55:33Z | [CDX query](https://arquivo.pt/wayback/cdx?url=http%3A%2F%2Fexample.com%2F&output=json&fields=url,timestamp,status,digest,length,offset,filename&limit=20), [replay](https://arquivo.pt/noFrame/replay/20100323155533id_/http://www.example.com/) | AVAILABLE | ARC location and digest are public; imported agency and signed statement are not. |
| IA-EXAMPLE-20100323 | Internet Archive | `http://www.example.com/` | 2010-03-23T15:55:33Z | [Availability query](https://archive.org/wayback/available?url=www.example.com&timestamp=20100323) | AVAILABLE | Reports the same 14-digit datetime as Arquivo.pt; that fact alone does not identify one crawl event. |
| CC-SATURN-20260714 | Common Crawl | `https://en.wikipedia.org/wiki/Saturn` | 2026-07-14T15:42:28Z | [CDX query](https://index.commoncrawl.org/CC-MAIN-2026-30-index?url=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FSaturn&output=json&filter=status%3A200&limit=5) | AVAILABLE | Public WARC range yielded actual `Content-Language`, `Vary`, cookie, GeoIP, digest and transport headers. |
| SUP-ETD-20170706 | Stanford SUP / Webrecorder | `http://enchantingthedesert.com/console/` | 2017-07-06T22:36:33Z | [WACZ download](https://stacks.stanford.edu/file/druid:pj930vw7523/etd.wacz), [replay](https://archive.supdigital.org/enchanting-the-desert.html) | AVAILABLE | Package is a legacy WACZ layout (`webarchive.yaml`, CDXJ, WARC), not a proven current WACZ 1.1.1 package. |

## A–O 覆盖状态

| 真实案例类型 | 状态 | 证据或严格限制 |
| --- | --- | --- |
| A. 同 URL、同 representation、不同时间 | AVAILABLE | Arquivo’s actual 2010 CDX result contains repeated same-digest records. |
| B. 同 URL、内容历史变化 | AVAILABLE | Internet Archive `example.com` 2010 and 2024 replays visibly differ. |
| C. 同 URL、语言 representation | UNAVAILABLE | One actual Common Crawl WARC has `content-language: en`; no contrasting same-URL pair was collected. |
| D. 同 URL、geography/CDN representation | UNAVAILABLE | One record has GeoIP/Vary context; no contrasting geographic pair was collected. |
| E. 同 URL、User-Agent/Accept/Vary | PARTIAL | One WARC lists `Vary: ... Cookie,Authorization,User-Agent`; no two request contexts were collected. |
| F. redirect/canonical relation | PARTIAL | Stanford CDXJ records a 301; Common Crawl Saturn HTML contains a canonical link; no cross-archive rule is embedded. |
| G. query parameter difference | PARTIAL | Internet Archive CDX lists URL-form/query variations; no semantically matched pair was collected. |
| H. fragment difference | UNAVAILABLE | No real archived fragment pair was collected. |
| I. authenticated/unauthenticated context | UNAVAILABLE | `Vary: Authorization` is real input evidence, but no authenticated archive content was collected. |
| J. 两个 archive 对同 URL capture | AVAILABLE | Arquivo.pt and Internet Archive report `http://www.example.com/` at `20100323155533`. |
| K. 两个 archive 近时间不同 bytes | UNAVAILABLE | No verified different-byte cross-archive pair was collected. |
| L. 同 archive 重复 capture | AVAILABLE | Arquivo CDX query returns multiple same-digest 2010 records. |
| M. archive 缺少某时间段 | UNAVAILABLE | No signed coverage statement; local non-return is never interpreted as absence. |
| N. Archive A 转发 Archive B evidence | UNAVAILABLE | No public case established both original agency and import provenance. |
| O. transparency checkpoint conflict | UNAVAILABLE | No real archive statement system conflict was found or fabricated. |

The primary corpus has four `AVAILABLE`, three `PARTIAL`, and eight `UNAVAILABLE` A–O categories. It is sufficient for factual tests of URL variation, replayed temporal difference, raw WARC context, legacy package layout and multi-archive same-timestamp ambiguity. It is **not** sufficient to prove strong claims about real language/geography variants, authenticated captures, archive absence, evidence import or checkpoint equivocation.

## References

[1] [Internet Archive, “Wayback Machine APIs”](https://archive.org/help/wayback_api.php).  
[2] [Arquivo.pt, “URL search: CDX server API”](https://github.com/arquivo/pwa-technologies/wiki/URL-search:-CDX-server-API).  
[3] [Common Crawl, “Get Started”](https://commoncrawl.org/get-started).  
[4] [Webrecorder, “WACZ 1.1.1”](https://specs.webrecorder.net/wacz/1.1.1/).  
[5] [Webrecorder, Stanford University Press digital archives catalogue](https://github.com/webrecorder/sup-digital-web-archives).  
[6] [The National Archives, “UK Government Web Archive”](https://www.nationalarchives.gov.uk/webarchive/).
