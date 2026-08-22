# IWOH v0.2 — 来源核验笔记

## 已核验的公开入口

Internet Archive 的官方 Wayback API 页面说明，其 Availability API 可以返回一个指定 URL 的当前可访问 archived snapshot 的 URL、timestamp 与 HTTP status；其 Memento API 用于查询 snapshots/mementos，CDX Server API 用于复杂 capture 查询、筛选和分析。[1]

WACZ 1.1.1 将 Web archive collection 打包为 ZIP，要求根目录 `datapackage.json`，其中含资源 path、bytes 与 fixity；archive directory 含 WARC file，WACZ 可由静态 HTTP 以 Range request 方式发布。WACZ 的 portable package/fixity 不能自动提供 cross-archive history interpretation。[2]

这些资料支持将 Internet Archive 的公开 Availability/Memento/CDX endpoints 和公开 WACZ artifacts 作为 v0.2 的真实 archive evidence sources。每一个具体 capture 仍须在实际访问后登记，不可由文档本身替代。

## References

[1] https://archive.org/help/wayback_api.php
[2] https://specs.webrecorder.net/wacz/1.1.1/

## 实际访问记录 — 2026-08-21 GMT+8

| Archive | 查询 URL | 返回的 capture / memento | Capture datetime | 可访问性 | 观察 |
| --- | --- | --- | --- | --- | --- |
| Internet Archive Wayback Machine | `https://archive.org/wayback/available?url=example.com&timestamp=20100101` | `http://web.archive.org/web/20100102003410/http://example.com/` | `20100102003410` | `AVAILABLE` | 官方 Availability API 实际返回 `available: true`、status 200。 |
| Internet Archive Wayback Machine | `https://web.archive.org/web/20100102003410id_/http://example.com/` | 同一 memento 的 raw replay | `20100102003410` | `AVAILABLE` | 实际 replay 成功，正文为 example.com 的 reserved-domain notice。 |

上述记录只证明该 memento endpoint 在抓取时公开可访问和 replay；它不提供 WARC download、independent observer、representation negotiation 或 history completeness 证据。

## 实际访问记录 — Stanford University Press / Webrecorder WACZ

Webrecorder 的公开 GitHub repository `webrecorder/sup-digital-web-archives` 自述为 Stanford University Press 的 self-hostable Web archive collection，并列出 16 个 Stanford Stack 的 `.wacz` download URLs。该页面公开列出 `Enchanting the Desert` 的 WACZ：`https://stacks.stanford.edu/file/druid:pj930vw7523/etd.wacz`，并且提供对应 replay URL `https://archive.supdigital.org/enchanting-the-desert.html`。该 repository 是现实发布 archive 的目录，而不是 IWOH fixture。[3]

在 2026-08-21 GMT+8 实际访问上述 Stanford Stack URL 时，浏览器触发 WACZ file download；这证明 download endpoint 当时公开可达。需要在 download 落盘后离线检查 `datapackage.json`、pages、WARC 与签名/metadata，才可断言具体 WACZ 内的 capture 内容或 provenance。

[3] https://github.com/webrecorder/sup-digital-web-archives

## 实际访问记录 — 同一 URL 的跨时间 Internet Archive captures

| Case | Original URL | Query evidence | Capture URL | Capture datetime | 可访问性 | 可见 representation 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| IA-EXAMPLE-2010 | `http://example.com/` | Availability API, request timestamp `20100101` | `https://web.archive.org/web/20100102003410id_/http://example.com/` | `2010-01-02T00:34:10Z` | `AVAILABLE` | replay 显示 reserved-domain notice。 |
| IA-EXAMPLE-2024 | `http://example.com/` | Availability API, request timestamp `20240101` | `https://web.archive.org/web/20240101235841id_/http://example.com/` | `2024-01-01T23:58:41Z` | `AVAILABLE` | replay 显示 `Example Domain` 页面，正文及链接与 2010 replay visibly different。 |

该 case 是真实、公开、同 URL 的跨时间 representation difference。Wayback/Memento timestamps 显示 archive capture datetimes，但本记录尚未取得 WARC response bytes、external timestamp receipt 或 causal proof；因此 Baseline-A 不得把“页面不同 + 两个 Wayback datetime”升级为 source-server truth 或 cryptographically proven temporal causality。IWOH 若对该 case 产生 temporal result，必须明确其结论仅限于 archive-recorded observation order 和所见 evidence 范围。

## 实际访问记录 — Wayback CDX metadata

在 2026-08-21 GMT+8 实际访问受限 CDX query：

`https://web.archive.org/cdx/search/cdx?url=http%3A%2F%2Fexample.com%2F&matchType=exact&output=json&fl=timestamp,original,statuscode,digest,mimetype&filter=statuscode:200&collapse=digest&limit=20`

该 endpoint 公开返回 `timestamp`、`original`、`statuscode`、`digest`、`mimetype`。输出中包含多个不同 original URL forms（例如 `http://example.com:80/`、`http://www.example.com/`、`http://example.com/`、`https://example.com/` 以及 userinfo-bearing forms）、多个 timestamps 和多个 digest。例如，`http://example.com/` 在 `20131026014032` 的 digest 为 `B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A`，而 `http://www.example.com/` 在 `20100603215612` 的 digest 为 `COSFPXIHL6FDWTZZOQFPYN5HBTZ4Z57M`。

这提供真实 archive 的 timestamp、digest 与 URL-variation metadata，但 CDX response 本身没有将 URL variants 定义为同一 target、没有 Vary/auth/vantage/context completeness、也没有 original observer agency、scope completeness 或 cross-archive relation judgement。Baseline-A 必须把这些未指定结果保留为 `UNDEFINED_BY_EXISTING_STANDARDS`，而不能从 CDX metadata 推导 IWOH classification。

## 真实 WACZ evidence — Stanford `Enchanting the Desert`

已下载的 `etd.wacz` 文件 SHA-256 为 `0aa2ffc2c894c8e4ab99021fbe99b583c982adf03f80ee553d992bd61f155210`，大小 114,997,692 bytes。其 ZIP listing 显示 `webarchive.yaml`、`indexes/index.cdxj`、`archive/enchanting-the-desert-20200622050104.warc`，没有 current WACZ 1.1.1 预期的 `datapackage.json` 或 `datapackage-digest.json`。因此它是一个真实可 replay/archive package，但在本审计中必须标记为 `LEGACY_WACZ_LAYOUT`，不得以 current WACZ 1.1.1 manifest/fixity 规则直接验证。

`webarchive.yaml` 显示 collection title `Enchanting the Desert`，说明为 Nicholas Bauch 2016 Stanford University Press interactive scholarly work 的 archive，并列出页面 `http://enchantingthedesert.com/console/`、date `2017-07-06T22:36:33`。CDXJ index 的真实 records 包含 URL、capture timestamp、mime、status、digest、WARC `length`/`offset`/`filename`；例如 root `http://enchantingthedesert.com/` 有 2017-07-06 22:36:05 的 `301` record，digest `TNDXUEFJ3JM75I7UXYLVDYLV2FD7NBKW`。

这提供确凿的真实 archive package、WARC+CDXJ evidence 和 archive context，同时也提供一个实际 interoperability limitation：历史 WACZ-compatible packages 存在不同 manifest conventions。仅由该 package 不可推出 cross-archive target mapping、representation comparability、original observer identity、complete history scope 或 transparency non-equivocation。

## 实际访问记录 — UK Government Web Archive

The National Archives 的 UK Government Web Archive 官方页面称其 capture、preserve 并 make accessible 自 1996 年以来的 UK central government Web information，内容包括 websites、videos、tweets 与 images。实际访问的 “Find websites” 页面提供公开 search facility、A–Z browse、从 live UK government website access archived versions 的入口，并明确要求用户了解 archive limitations 和 reuse legal information。[4]

该 archive 因此可作为与 Internet Archive 不同的公开 archive corpus source。当前实际访问记录只证明 collection page 和 search/replay entrypoint 可达；尚未从其 search endpoint 获得特定 memento URL、HTTP capture metadata、WARC/WACZ download、independent observer identity 或 transparency receipt。相关字段必须暂登记为 `UNAVAILABLE`，而不能以 archive homepage 代替。

[4] https://www.nationalarchives.gov.uk/webarchive/

## UK Government Web Archive 具体 capture 查询结果

对公开 search form 输入 `www.gov.uk` 并提交后，服务将请求导向 `https://webarchive.nationalarchives.gov.uk/ukgwa/timeline1/www.gov.uk`，返回 “Let's confirm you are human” security check。按照本审计规则，不绕过 CAPTCHA/人机验证，不伪造 archive timeline 或 capture details。因此 `UKWA-www.gov.uk-specific-captures` 当前状态为 `UNAVAILABLE_FOR_AUTOMATED_COLLECTION`。该结果本身是可复核的 archive-access limitation，不是 absence、没有 capture 或 standards insufficiency 的证据。

## 公开 API / WARC data sources — Arquivo.pt 与 Common Crawl

Arquivo.pt 官方培训资料明确列出对其 APIs 的远程自动访问，包括 Full-text & URL search、Image Search、CDX-server API 与 Memento API。这使 Arquivo.pt 成为可用于第二条 Memento/CDX archive path 的候选；具体 cases 仍须实际 endpoint access 后登记。[5]

Common Crawl 官方数据说明其 crawl data 可通过 public HTTPS 访问且不需要 AWS account；其 WARC raw crawl data 保存 HTTP request、HTTP response 和 crawl metadata，response record 包含 raw HTTP headers 与 payload evidence。官方示例展示 real WARC headers 可包含 `WARC-Date`、target URI、IP、protocol、payload/block digests、HTTP `Vary`、`Content-Language`、cookie 与 cache headers。该 source 适合测试 raw WARC 可表达哪些 capture context 字段；它不是 Memento history service，也不自动提供 archive-to-archive comparison、observer identity、signed provenance、scope completeness 或 equivocation semantics。[6]

[5] https://sobre.arquivo.pt/en/collaborate/training-courses-by-arquivo-pt/automatic-access-and-processing-of-preserved-web-data-module-c/
[6] https://commoncrawl.org/get-started

## 实际访问记录 — Arquivo.pt CDX 对照

Arquivo.pt 的公开 CDX-server API 文档指定 `https://arquivo.pt/wayback/cdx`，支持 `url`、from/to、matchType、limit、JSON output、filter 和 `url,timestamp,status,digest,length,offset,filename` fields。[7]

在 2026-08-21 GMT+8 实际调用 `https://arquivo.pt/wayback/cdx?url=http%3A%2F%2Fexample.com%2F&output=json&fields=url,timestamp,status,digest,length,offset,filename&limit=20`。该 endpoint 返回真实 records：例如 `http://www.example.com/` 于 `20100323155533` 的 status 200、digest `EF7YLJGKQUMLJFP3F7A7LBALC65T5W2O`、length 538、offset 678670、filename `IAH-20100323155325-00000-p12.arquivo.pt.arc.gz`。多个 2010 captures 的 digest 相同。

该 digest 也出现在 Internet Archive CDX query 的 `http://www.example.com:80/` record（2003-02-07）中。这是实际跨 archive metadata-level byte equality evidence；然而两个 CDX rows 的 URL forms、crawler activity、source WARC accessibility 和 the digest algorithm semantics 未由这些 rows 统一为 same target or repeated observation。Baseline-A 能报告 archive-provided digest equality，但根据公开 CDX/Memento semantics 不能单独断言“同一 Web observation”。

[7] https://github.com/arquivo/pwa-technologies/wiki/URL-search:-CDX-server-API

## 实际跨 archive 同 timestamp 对照 — Arquivo.pt 与 Internet Archive

Arquivo.pt replay URL `https://arquivo.pt/noFrame/replay/20100323155533id_/http://www.example.com/` 于 2026-08-21 GMT+8 实际 replay 成功，页面内容为 Example Web Page reserved-domain notice。随后实际调用 Internet Archive Availability API：`https://archive.org/wayback/available?url=www.example.com&timestamp=20100323`，该 API 返回同一 capture timestamp `20100323155533`、status 200 和 `http://web.archive.org/web/20100323155533/http://www.example.com/`。

这是一个强的现实 metadata counterexample：两个独立 archive 对同一 URL form 报告相同的 14-digit datetime，且 Arquivo CDX digest 可公开取得。现有 HTTP/Memento/CDX metadata 没有定义“同一 timestamp”是否表示同一 crawl event、同一 response bytes、shared upstream WARC ingest、独立 simultaneous captures 或 coincidence。Baseline-A 因此只能安全报告 `SAME_REPORTED_CAPTURE_DATETIME`，而 target-agency/repeated/parallel semantics 在既有 standards-only reading 中仍为 `UNDEFINED_BY_EXISTING_STANDARDS`。这不是 IWOH 新颖性证明：它是一个真实案例，要求 Baseline-B 测试现有 PROV/VC/SCITT extensions 是否可在不引用 IWOH 的条件下解决该不确定性。

## 实际访问记录 — Common Crawl public index registry

在 2026-08-21 GMT+8 实际访问 `https://index.commoncrawl.org/collinfo.json`。响应列出当前公开 collections；首项为 `CC-MAIN-2026-30`（July 2026 Index），其 `timegate` 为 `https://index.commoncrawl.org/CC-MAIN-2026-30/`，`cdx-api` 为 `https://index.commoncrawl.org/CC-MAIN-2026-30-index`，crawl 时间范围为 2026-07-10 至 2026-07-23。该 registry 是后续选择真实 WARC index case 的公开、可复现入口。

## 已验证的真实 Common Crawl WARC representation context

使用 `CC-MAIN-2026-30` public CDX query，实际取得 `https://en.wikipedia.org/wiki/Saturn` 的 response record：timestamp `20260714154228`、record id `019f614b-3ce1-7dd1-976e-6b2f24bd6f26`、payload digest `sha1:HO4IXO5J5LQSUBV7QTCX6VDBOKDBONSE`。再按其 public filename、offset 180,423,195 与 length 172,162 对 `data.commoncrawl.org` 执行只读 HTTP Range access，获得压缩 WARC record，保存其 range SHA-256 与解压 headers。

该真实 WARC response 的 headers 明确包含 `WARC-Date: 2026-07-14T15:42:28Z`、target URI、IP address、HTTP/2、TLS 1.3、payload/block digest；HTTP response 包含 `content-language: en`、`vary: Accept-Encoding,X-Subdomain,Cookie,Authorization,User-Agent`、cookie 值与 `GeoIP=US:VA:Ashburn...`。

它证明 standards-only WARC 可以传递许多 representation context inputs。它也证明这些 fields 并不自动形成 cross-archive comparison algorithm：真实 record 不声明哪个 Vary dimension must-match、如何处理 unknown request headers、是否 transferable across crawler vantages、何时因 cookie/authorization/vary 而 `INCOMPARABLE`。这是 R3 的现实输入，不是 IWOH 新颖性结论。

## Baseline-A 规范原生语义边界

RFC 9110 将 target resource 定义为 HTTP request 的 target，并把 representation 定义为反映 resource state 的 metadata 加 data；同一 target resource 可以依据 content negotiation 的 request dimensions 返回多个 selected representations。[8] 它定义 HTTP message-level semantics，但不规定独立 archives 如何将不同 URL forms、replay URLs 或 canonical hints 合并成一个 historical target，也不规定跨 archive comparison predicate。

RFC 7089 定义 Original Resource、Memento、TimeGate 与 TimeMap；TimeMap 是列出某 Original Resource memento URIs 的资源，Memento-Datetime 表示被 encapsulated prior state 的 datetime。RFC 7089 自身明确指出 versions 可以位于多个 servers，且每个 server likely only aware of versions it holds；`from`/`until` TimeMap coverage attributes 为 optional。[9] 它支持 archive-local temporal navigation，未将 one archive’s TimeMap absence 规定为 global absence，也没有多-archive same/different/parallel/repeated relation vocabulary。

WARC 1.1 规定 capture records、WARC-Target-URI、WARC-Date、record id、request/response linkage、optional payload/block digest 和 `WARC-Concurrent-To`（同一 capture event 内 records 的 association）。WARC-Date 是 record creation data capture began 的 UTC instant；WARC recommends no particular algorithm for access software to choose a record by date when exact match unavailable。[10] 因此 WARC 可表达 archive record evidence 和 same-event internal linkage，不能在原生层面对不同 archive records 归类为 temporal change、parallel observation 或 comparable representation。

PROV-DM 是 domain-agnostic provenance model，表达 entities、activities、agents、generation、usage、derivation、attribution、association 与 delegation，且允许 domain-specific extensions。PROV explicitly does not specify the conditions under which derivations exist; derivation must have been determined by unspecified means。[11] 因此 PROV 可以承载 original observer/importer agency graph，却不在原生层提供 Web capture target identity、HTTP Vary comparability、history scope 或 transparency-equivocation decision procedure。

[8] https://www.rfc-editor.org/rfc/rfc9110.html
[9] https://www.rfc-editor.org/rfc/rfc7089.html
[10] https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/
[11] https://www.w3.org/TR/prov-dm/

## Baseline-A：签名声明、透明日志与 issuer 的标准边界

RFC 9943 SCITT 定义 single-issuer signed-statement transparency、COSE receipts、append-only statement sequence 和 issuer/subject metadata。它明确将 statement discovery/notification 和 statements 的 storage/management 置于 scope 外；其 semantic statements are opaque to the transparency service。[12] 因此，SCITT 能为已定义的 Web capture statement 提供 issuer binding、registration/inclusion receipt 与 log-specific consistency，但不定义 Web capture target identity、representation comparability、absence scope 或 archive import policy。

RFC 9162 CT 定义 public log、signed timestamps、Merkle inclusion and consistency proof；它也指出 a misbehaving log can show different inconsistent views to different clients and mechanisms preventing blind trust are outside RFC 9162 scope。[13] 对“同 log、同 tree size、different valid signed roots”可进行 cryptographic conflict assessment；把该 rule 映射到 a Web archive statement is at most a profile mapping, not a new transparency primitive.

VC Data Model 2.0 为 issuer claims、subject、credential、verification material、holder/verifier roles 提供 extensible data model；verification does not imply truth of claims and claim validation is done by verifier-specific business rules。[14] 因此 VC can encode a Web archive observation assertion and issuer, but does not standardize which archive capture facts must be included nor the rules for comparing independent observations.

[12] https://www.rfc-editor.org/rfc/rfc9943.html
[13] https://www.rfc-editor.org/rfc/rfc9162.html
[14] https://www.w3.org/TR/vc-data-model-2.0/

## 真实用户与运营方需求证据（不等同于 Profile 需求）

Webrecorder 的 ReplayWeb.page provenance feature 表明独立 archive/replay operator 已实际展示 original URL、archived-on date、capture tool、signed WACZ validation status、key/observer certificate 和 package hash；其 viewer validates WARC records, indexes and page lists on load and surfaces tampering.[15] 这是对 archive provenance 和 package integrity 的现实需求与实现证据，但不包含跨 archive target-relation、comparability、history-scope 或 non-adjudication semantics。

Starling Lab / Rolling Stone 的公开 war-crimes investigation case study 记录了近 2,000 documents、40 key images 和 183 web archives，并将 capture/store/verify、Webrecorder、C2PA、hash/signature、content addressing 和 decentralized storage combined for evidence preservation and reader inspection.[16] 它证明调查新闻/公益证据工作有 provenance、date/time、integrity、chain-of-trust 和 independent verification needs；它也构成反证：现实团队能将现有技术组合投入实际案例，而不是必须使用某一新的 Web history profile。

BnF researcher interviews reported difficulty independently re-examining a cited Web source, justifying a website’s selection within a defined shared corpus, and documenting why one site rather than another was used. Researchers described uncertainty in corpus contours and stressed that screenshots/printouts lack scientific validity/authenticity for dynamic content.[17] 这支持 scope、collection context、source documentation and repeatability 的实际需求，不证明跨 archive relation vocabulary has demand.

IIPC describes selection goals, crawl-time harvest metadata, preservation without modification, and access for researchers/historians/public as standard web-archiving practice.[18] 这支持 archive-local collection scope/harvest context 的现实相关性。IIPC statement does not request global history claims or a specific cross-archive interoperability profile.

[15] https://webrecorder.net/blog/2022-11-10-showing-provenance-on-replaywebpage-embeds/
[16] https://starlinglab.org/case-studies/the-first-cryptographic-archive-war-crimes-investigation/
[17] https://www.dlib.org/dlib/march12/stirling/03stirling.html
[18] https://netpreserve.org/web-archiving/about-archiving/
