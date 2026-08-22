# Candidate Profile Prior-Art 深度审计笔记

## 本轮原始资料结论

WACZ 1.1.1 已经将 WARC、CDXJ、页面列表、技术/描述 metadata 和 package fixity 组合为可复制、可通过静态 HTTP 托管的 archive package。其 `pages.jsonl` 至少要求 `url` 与 RFC 3339 `ts`，`datapackage.json` 要求 resource path/size/fixity，并允许 custom properties。WACZ 还允许将 archive 从一个存储系统复制到另一个系统，且可由不依赖 specialized server 的客户端按 HTTP Range replay。这完全覆盖 portable archive/evidence container，但没有规定多个 archives 对同一 logical Web target 的 grouping、可比性、共同 statement envelope、history scope 或跨 archive equivocation 语义。[1]

Memento RFC 7089 已经定义 Original Resource（URI-R）、Memento（URI-M）、TimeGate（URI-G）、TimeMap（URI-T）、datetime negotiation、多服务器驻留的 resource versions 和 TimeMap 中某服务器已知 Mementos 的历史。它特别承认每个 server 可能只知道自己持有的 versions。RFC 7089 处理 3xx、4xx/5xx、Vary 与 TimeMap pagination；因此“跨 archive 时间化网页历史”不是 OIN 新概念。不过它不绑定 WARC evidence、third-party capture agent、signature、compare predicate、共同 statement schema 或 global completeness。[2]

IPARO（iPRES 2023）是很接近的学术 prior art：它提出基于 IPFS/IPNS 的 decentralized version tracking，面向 archived web pages，不依赖中心化 archive/replay server，并保留 aggregator 的作用以让大小 archives 参与。其公开摘要没有显示 WACZ/PROV/VC/SCITT 风格的 capture evidence、独立 observer semantics、可比性或非裁决跨 archive history profile。因此它反驳去中心化版本历史的新颖性，但没有显示它已经完成候选 Profile 的全部组合。[3]

SCITT RFC 9943 已成为 Proposed Standard。它定义 artifact 相关的 signed statement、issuer（可为 independent auditor/reviewer/endorser）、subject correlation、Transparency Service receipt、auditor、statement sequence 和 non-equivocation；同一 artifact 可以有多 issuer statement。它同时明确把 statements 的管理/存储以及 entities 如何 discovery/notification 排除在 scope 外。故其覆盖 signature、registration、receipt、per-Transparency-Service history/non-equivocation，而没有提供 web-capture domain semantics 或 cross-archive discovery contract。[4]

本轮结论：未发现一个已部署/公开规范能完整同时定义 multi-independent web capture、WARC/WACZ evidence、target grouping、representation comparability、non-adjudicative classification、cross-archive statement import、history scope 和 cross-archive equivocation。该“未发现”不是新颖性证明；其最可能表示一个尚未标准化的集成 profile。

## References

[1] https://specs.webrecorder.net/wacz/1.1.1/
[2] https://datatracker.ietf.org/doc/html/rfc7089
[3] https://www.ideals.illinois.edu/items/128294
[4] https://datatracker.ietf.org/doc/html/rfc9943

## WARC provenance 的最新状态

IIPC WARC specifications 的公开 issue #120（2026-07，仍为 open）提出把 C2PA Manifest Store 追加进 WARC 的 `c2paprovenance` record，以便对 WARC record collection 做 cryptographically signed provenance/fixity。讨论明确该 record type 是 provisional，仍有 compression、index/replay、record identifier、metadata leakage 与 WARC standardization 的开放问题。该工作和 `c2pa-warc` crate 是强相关 prior art：它试图把 C2PA、WARC append-only convention 与 record-level fixity 连接起来。但它不是已完成的 WARC/C2PA 标准，也没有定义多 archive target grouping、observation comparability、cross archive statement import 或 history scope。[5]

ReplayWeb.page 已可显示 signed WACZ archive receipt，实时验证加载到的 WARC/index/page list hash，并显示 archive creator public key 或 trusted third-party observer certificate。它是已部署的 verifiable web archive provenance/replay 先例。其公开说明仍定位于单个 archive 的 receipt、validated archive package 和 creator provenance，而非多个 independent captures 的共同 history model。[6]

这加强而非削弱此前结论：archive evidence/provenance 有大量实现和标准化工作；候选 Profile 若存在，必须严格局限于 archive-to-archive interoperability semantics，不能将 WARC/WACZ/C2PA binding 或 signed archive receipt 作为自己的创新。

[5] https://github.com/iipc/warc-specifications/issues/120
[6] https://webrecorder.net/blog/2022-11-10-showing-provenance-on-replaywebpage-embeds/

## 可信档案与跨 archive fixity 的学术先例

ARCHANGEL（2018）提出使用 distributed ledger technology 为公共档案中的数字文档提供 provenance、immutability 与 integrity；这说明“多个公共档案 + 不可篡改/可验证记录”不是新问题。其公开摘要聚焦 archived digital documents 的长期 integrity，并未给出 HTTP representation capture context、多独立 observer statement、Memento-style cross archive history grouping 或 non-adjudication comparison 语义。[7]

Archive Assisted Archival Fixity Verification Framework（2019）更直接相关：它为 public/private web archives 提出 Atomic 和 Block manifests，在 archive 外发布每个或多个 archived page 的 fixity，并将 manifest disseminate 到多个 on-demand web archives；在 archival fixity server 缺失时仍可验证。论文明确针对 archive 自己提供的 fixity 可能不够独立这一问题。它已解决多 archive 的 verified fixity dissemination，但不定义 common target identity、HTTP context comparability、observation statement exchange、temporal/parallel classification 或 history completeness。[8]

因此，候选 Profile 不能以“多方 archive fixity”或“分布式账本下的档案 provenance”主张新颖性。尚未找到将这些能力和 Memento/WACZ/SCITT/PROV 端到端融合成 common web-observation semantics 的已部署开放实现；这仍是 gap hypothesis，而非创新证明。

[7] https://arxiv.org/abs/1804.08342
[8] https://arxiv.org/abs/1905.12565

## Fixture artifact 格式依据

IWOH fixture 的 archive evidence 将使用实际 WACZ 1.1.1 layout：ZIP 内含 `archive/data.warc`、`datapackage.json`、`datapackage-digest.json`、CDXJ index 与 pages JSONL；datapackage manifest 列举 resources 的 SHA-256 fixity。WACZ 的定义是可移植的 web archive package，而不是新的 observation history semantics。[9]

WACZ Auth 的目标是由 capture client/third-party observer 对 WACZ creator identity 与 archive creation time 提供 authentication；它明确说明既有 HTTP/TLS 不能证明 web server 曾在某时提供该内容。这再次界定 profile 的证据边界：有效 Capture Statement 证明 signing agent 的 capture claim，不证明 source truth。[10]

[9] https://specs.webrecorder.net/wacz/1.1.1/
[10] https://specs.webrecorder.net/wacz-auth/0.1.0/
