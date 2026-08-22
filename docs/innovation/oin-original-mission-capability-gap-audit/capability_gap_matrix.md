# Original Mission Capability Matrix — Standards-Only Network

## 判定纪律

`PASS` 只表示在三个隔离 experimental operator environments、真实公开 URL、真实 HTTP/WARC/WACZ artifact、真实 Ed25519 keys 和实际 endpoint failure 下已经运行成功。它不表示三个现实独立组织、三个独立 egress/geographies、Internet-wide history completeness，或 Web-server non-repudiation。`PARTIAL` 表示基础能力已运行，但用户要求的更强语义需要已有机制的额外部署或未在当前环境中得到证据。`UNAVAILABLE` 不能被误写为技术缺口。

| Question | Experiment result | Evidence | Strict interpretation |
| --- | --- | --- | --- |
| A. 跨 archive discovery | **PASS** | Multi-peer verifier queried A/B/C static signed catalogs for one exact URL and discovered all available evidence. | Discovery works for a declared peer set, not the whole Internet. Memento Aggregator is deployed prior art for broader cross-archive Memento discovery.[1] |
| B. 跨 operator discovery | **PASS** | A/B/C independently served signed catalogs; a client found records by issuer and target from each peer. | Technical environment separation, not proof of real-world institutional independence. |
| C. 原始 agency preservation | **PASS** | A imported B and B imported C; imported original statement/signature/key stayed foreign, while importer only signed its own catalog import record. | Proves signer/key agency preservation, not social/operator independence or origin-server truth. |
| D. 离线运行 | **PASS** | B endpoint stopped; A/C catalogs and imported B copies remained queryable/verifiable. | Only within the retained peer set and existing replicas. |
| E. 无中心同步 | **PASS, manual/static** | Direct peer fetch/import and replicated signed descriptors operated without a central database, coordinator or OIN endpoint. | Not automatic global gossip, DHT routing or incentive system. Existing Git/object transfer and WACZ/IPFS primitives can provide the transfer substrate.[2] [3] |
| F. 发现 equivocation | **PARTIAL** | A same-key, same declared claim-key, different-payload pair was detected and preserved. | This is catalog/evidence conflict detection, **not** CT/SCITT cryptographic log equivocation because no receipts/tree heads/consistency proofs existed.[4] [5] |
| G. 保留 conflicting observations | **PASS** | UUID multi-record output retained valid different payloads, invalid-binding record and same-signer conflicting valid claims without selecting a winner. | No assertion that any record is true/false. |
| H. 验证 evidence | **PASS** | Verifier checked detached Ed25519 signatures, package SHA-256, WACZ ZIP/resource manifest digests and WARC-level payload digest binding. | Existing WACZ signing/fixity techniques cover these primitives.[6] |
| I. 验证历史来源 | **PASS, bounded** | Validated issuer key control, statement time assertion, capture request context, WARC/WACZ binding and importer chain. | WACZ Auth explains why this does not prove that a Web server non-repudiably served the content.[6] |
| J. 声明 history scope | **PASS** | Every catalog declares `local-and-explicit-imports`; peer descriptor says completeness only for listed endpoints at query time. | No global completeness claim. Memento TimeMaps are likewise archive-known holdings rather than a global universe.[7] |
| K. operator 消失后工作 | **PASS** | C service and full storage/catalog directory were removed; B’s retained C import and A’s store remained valid; C restoration restored source. | No resilience if all copies vanish. |
| L. 新 operator 无中心批准加入 | **PASS, experimental** | C generated a new key/captures/catalog, downloaded B’s public catalog/bundle, verified it with public material and published an import without a central approval service. | C was an isolated experimental environment scripted by the experiment, not an unaffiliated human organization. |
| M. 不同实现互操作 | **PASS** | Python A, Node B and shell/openssl/curl/zip C each produced/consumed foreign signed WACZ bundles. | The shared artifact mapping is an ordinary profile/extension agreement; it is not a new fundamental protocol. |
| N. 已有 deployed system 是否完整提供全部能力 | **NO CONFIRMED SINGLE COMPLETE DEPLOYMENT FOUND** | Memento Aggregator covers federated discovery but uses central cache/rules; ipwb covers WARC/IPFS replication/index/replay; WACZ/WACZ Auth cover portable signed packages; Webrecorder decentralized use cases cover many requirements.[1] [2] [3] [6] | This is not evidence of absence. It is a documented finding that this audit did not identify one publicly documented deployed system covering the full A–M combination. |

## Real URL case outcomes

| Requested case | Actual result | Network treatment |
| --- | --- | --- |
| Content unchanged | A and B captured `example.com` with equal payload SHA-256. | Two distinct signed records retained; equal bytes do not merge issuer or capture events. |
| Content changed | A and B captured `httpbingo.org/uuid` with distinct actual payload digests. | Both retained; conflict/change not adjudicated from bytes alone. |
| Redirect | A/B observed actual HTTP 302 `Location: https://example.com/`. | Request target and redirect response remain separate evidence; no automatic target merge. |
| Canonical variation | C captured actual public Wikipedia page; target relation could be extracted only from evidence if present. | No automatic identity merge. |
| Language/request variation | A/B made differing real `Accept-Language` and User-Agent requests to a public echo endpoint. | Request context and differing payloads retained. Does not prove server localized variant behavior. |
| CDN/geo variation | All operators shared sandbox egress. | **UNAVAILABLE_IN_THIS_ENVIRONMENT**; no fabricated geographic claim. |
| Query variation | Distinct `ref=alpha`/`ref=beta` public URLs were captured. | Queries retained as distinct targets. |
| Capture failure | B captured actual HTTP 503 response. | It remains a signed capture; does not imply history absence. |

## What existing technology already provides

The experiment itself reconstructed a functioning network from HTTP, WARC/WACZ-style packages, SHA-256, Ed25519, static signed catalogs, generic VC/PROV-shaped JSON, direct HTTP/Git-compatible copying and a peer descriptor. WACZ is a portable data package for Web archives; WACZ Auth documents package creator/time signing and verification; IPWB provides WARC/IPFS dissemination, CDXJ indexing and replay; WACZ-IPFS documents WARC/WACZ content-addressed chunks and deduplication; and Memento aggregation provides an existing federation model for Original-URL discovery.[1] [2] [3] [6] [8]

None of the network capabilities that passed required a new archive format, hash primitive, signature primitive, Merkle structure, consensus scheme, distributed storage scheme or OIN-specific wire protocol. The only additional material is a documented mapping agreement: which existing fields identify a capture, how a peer descriptor is copied, what import preserves, when a verifier rejects a binding, and which bounded labels it returns. That is interoperability/profile engineering.

## Remaining gaps and whether they are irreducible

| Remaining issue | Existing mechanism / profile route | Irreducible network mechanism? |
| --- | --- | --- |
| Internet-scale peer discovery | DHT, DNS/HTTPS service discovery, static peer lists, ActivityPub/WebSub-style distribution, Memento archive lists, or a registry with replicated mirrors. | **No evidence that a new primitive is required.** Choice of bootstrapping/governance is an engineering/profile issue. |
| Automatic convergence/gossip | Git remotes, IPFS providers, pubsub, periodic sync, CRDT/gossip libraries. | **No evidence.** This experiment used direct import; automation does not require a novel history protocol. |
| Strong archive-log equivocation | CT/SCITT receipts, consistency proofs, auditors and gossip. | **No for log mechanics.** A deployment would need to select services/policy; cross-archive membership policy remains a profile choice. |
| Real operator independence | Legal/entity/hosting/network/funding disclosures and external auditing. | **Not cryptographically provable by a protocol alone.** |
| Web-server delivery non-repudiation | Server-signed HTTP/Signed Exchanges or trusted capture hardware/attestations. | **No, but origin proof is an Internet/Web-server deployment constraint, not an archive-network primitive.** |
| Global history completeness | Declared peer set/scope, registries, transparency logs, collection policies. | **No global proof is obtainable from a finite network absent a defined universe.** |
| Real geo/CDN comparability | Multiple independently hosted egresses and recorded request context. | **No new primitive; requires real deployment conditions.** |

## Capability-gap finding

The standards-only network proves that the original mission’s technical core—independent local capture, signed/evidence-bound artifacts, multi-peer discovery, foreign import without agency rewrite, surviving-replica operation, conflict retention, invalid-binding rejection and multi-toolchain participation—can be assembled into a working experimental network without any OIN-specific network protocol.

The remaining gaps are deployment/governance/scope questions or ordinary profile decisions. This audit found **no minimal network mechanism that existing standards, public implementations or extensions cannot express**. Accordingly, the conclusion must be:

> **OIN 的网络架构本身不是技术创新。**

This conclusion does not say that existing deployments already offer a single turnkey system for every A–M requirement. It says that the functional architecture can be built from public technology, as this experiment did, and that the absence of one turnkey deployment does not establish a new irreducible protocol mechanism.

## References

[1] [LANL TimeStitch Memento Aggregator](https://github.com/lanl/TimeStitch-Memento-Aggregator).  
[2] [InterPlanetary Wayback](https://github.com/oduwsdl/ipwb).  
[3] [WACZ IPFS Custom File Chunking](https://github.com/webrecorder/specs/blob/main/wacz-ipfs/latest/index.md).  
[4] [RFC 9162 — Certificate Transparency Version 2.0](https://www.rfc-editor.org/rfc/rfc9162.html).  
[5] [RFC 9943 — SCITT Architecture](https://www.rfc-editor.org/rfc/rfc9943.html).  
[6] [WACZ Signing/Verification Specification 0.1.0](https://github.com/webrecorder/wacz-auth-spec/blob/main/spec.md).  
[7] [RFC 7089 — Memento](https://www.rfc-editor.org/rfc/rfc7089.html).  
[8] [Use Cases for Decentralized Web Archives](https://specs.webrecorder.net/use-cases/latest/).
