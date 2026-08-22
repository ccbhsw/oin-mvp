# OIN Original Mission Capability Gap Audit

**审计日期：** 2026-08-21 GMT+8  
**审计问题：** 在完全不使用 OIN 代码、schema、Object/Observation/Observer 命名或 IWOH 私有协议的情况下，公开标准与公开基础设施能否构建真正工作的、开放、跨 archive、跨 operator、可验证、可复制、非单一机构控制的公共 Web observation history network？

> **最终结论：可以。** 本审计实际运行了一个由 Python、Node.js 与 shell/openssl 三套不同工具链组成的三环境 standards-only network。它使用真实公开 URL、真实 HTTP capture、WARC、WACZ-style package、SHA-256、Ed25519、signed static catalog、VC/PROV-shaped public extension、direct peer import 和复制的 peer descriptor，完成 discovery、验证、agency-preserving import、离线恢复、operator/index temporary disappearance、新 operator 加入、恶意 evidence binding 拒绝和冲突保留。
>
> 因而必须明确宣布：**OIN 的网络架构本身不是技术创新。**

这不是“已有某个单一产品已经替代 OIN”的断言。它是更严格的技术结论：原始使命所需的网络能力可以由现有公开标准、公开实现和普通 profile/extension mapping 构造并实际运行；本审计没有发现一个必须使用 OIN-specific network protocol 才能表达或实现的网络机制。

## 1. 实验范围与诚实边界

三者是本地隔离的 **experimental operator environments**，并非三家现实独立机构。每个环境有独立目录、Ed25519 key、capture runtime、WARC/WACZ storage、catalog、HTTP port 和 foreign-import store；A 使用 Python，B 使用 Node.js，C 使用 shell/curl/openssl/zip。它们在同一 sandbox host 和同一外部 egress 下运行，所以本报告不声称证明现实组织独立性、独立托管/资金、独立 ASN、独立 CDN geography 或公网持续可用性。

该限制不使实验无效。它精确限制了实验所证明的东西：**不同技术实现可通过公开 artifact 和密钥材料组成一个无中心数据库的、多本地保存、可验证和可恢复的网络。** 它不证明某个协议能从 cryptography 推导出社会独立性或 Internet-wide history completeness。

| 硬约束 | 实验处理 | 未作出的主张 |
| --- | --- | --- |
| 禁止 OIN/IWOH 私有基础 | 三套 operator 源码与 artifact mapping 均未导入 OIN/IWOH 代码或 schema。 | 不能把已有 OIN implementation success 计作证据。 |
| 使用真实公开 URL | 实际 capture `example.com`、`httpbingo.org` 和 Wikipedia；保留 HTTP request/response/WARC evidence。 | 不把预期 URL 行为或模拟 fixture 写成事实。 |
| 不部署公网/不买服务器 | 三个 ephemeral local HTTP endpoints 完成失败/恢复测试。 | 不声称长期公网 deployment。 |
| 三个独立参与者 | 三个隔离技术环境，明确标为 experimental operators。 | 不声称真实组织、地理或治理独立。 |

## 2. 使用的公开技术栈

WARC 是已广泛使用的 Web archive record format；WACZ packages WARC and archive metadata for distribution; WACZ Auth specifies package fixity, creator signature and optional timestamp verification.[1] [2] W3C VC 2.0 和 PROV-DM 可以承载 issuer、entity、activity 和 provenance assertion；Ed25519 is an existing signature primitive; Memento defines Original Resource, Memento and TimeMap navigation; CT/SCITT supply optional transparency-log mechanics.[3] [4] [5] [6] [7]

| Network capability | Standards-only realization actually used |
| --- | --- |
| Capture evidence | Real HTTP request/response → WARC 1.1 records → WACZ-style ZIP package with `datapackage.json`, CDXJ and resource SHA-256. |
| Integrity / signer | Detached Ed25519 signature over raw statement and catalog; SHA-256 for package, WARC and payload bindings. |
| Provenance | Public VC/PROV-shaped JSON: issuer, activity, target, request context, response digest, WARC/WACZ evidence and import relation. |
| Discovery | Each operator serves a signed static catalog; a copied signed peer descriptor directs a client to several catalogs. |
| Replication | Direct HTTP download and local foreign store; Git-compatible object/files are permitted substrate but not required for correctness. |
| Conflict | All records stay in catalog; a verifier labels invalid binding or same-signer/same-declared-claim-key different-payload conflict. |
| Scope | Catalog says `local-and-explicit-imports`; peer descriptor says completeness only for its listed endpoints at query time. |

No item above required a novel archive format, novel cryptographic primitive, novel Merkle tree, novel consensus system, novel storage network, OIN-specific object model or OIN-specific wire protocol.

## 3. Actual network experiment

### 3.1 Real public Web evidence

The network captured a stable public page, a UUID endpoint producing actually different bytes, an actual HTTP 302 redirect, a public HTML page for canonical-relation evidence, an echo target under distinct `Accept-Language`/User-Agent headers, two distinct query URLs, an actual HTTP 503 response and a public egress endpoint. The preflight registry and each resulting local WARC/WACZ package are included in the evidence directory.

| Case | Observed result | Network behavior |
| --- | --- | --- |
| Same public URL, repeated bytes | A/B captured `example.com` with one equal payload digest. | Retained as separate signed captures; no automatic agency/capture-event merge. |
| Same public URL, different bytes | A/B captured `httpbingo.org/uuid` with different actual payload digests. | Both discoverable and valid; neither is adjudicated as the true state. |
| Redirect | Actual 302 with `Location: https://example.com/`. | Redirect response retained; original request target is not automatically merged with destination. |
| Header variation | Same echo URL under different `Accept-Language` and User-Agent. | Request context/different bytes retained; it does not falsely claim origin language variance. |
| Query variation | `?ref=alpha` and `?ref=beta` both captured. | Distinct request targets remain distinct. |
| HTTP failure | Actual 503 response captured and signed. | It remains evidence of an observed response, not a declaration of no history. |
| CDN/geo | Shared sandbox egress. | **UNAVAILABLE_IN_THIS_ENVIRONMENT**; no fabricated geographic result. |

### 3.2 Discovery, verification and agency

A third-party verifier began with only a peer descriptor, queried A/B/C directly, verified each catalog signature, then verified foreign statements, signer-key binding, package digest, WACZ ZIP/resource manifest digests and WARC payload binding. Before imports, `example.com` returned two valid independent source records. After A imported B’s original bundle, discovery returned A’s source, B’s source and A’s replica of B’s source; the replica still validated under B’s public key. C independently performed the same verification/import using shell, curl and OpenSSL. B subsequently recovered and imported C’s evidence using Node.js.

> Importer catalogs prove only an import activity. The original signed foreign statement remains the authoritative source for foreign capture agency.

### 3.3 Offline, disappearance, recovery and noncentral bootstrap

B’s endpoint was stopped. A and C remained reachable, and their retained B copies remained verifiable. After B restart, it imported missing C evidence. C’s service and entire local directory—including catalog, key material exposed for verification, local bundles and index—were temporarily moved out of the served path. A/B still supplied two valid results for C’s canonical-target evidence because B had retained C’s imported original bundle. Restoring C returned the third source record.

Each operator also stored and signed its own copy of the same peer descriptor. With A offline, discovery started from C’s copied descriptor and continued against B/C without any central database, central history server or OIN endpoint. This is **declared-peer-set resilience**, not global peer discovery.

### 3.4 Malicious and contradictory publisher

B generated a signed statement pointing to a real package but deliberately declared the wrong package digest. The signature was valid, the ZIP/resource structure was valid, and the verifier rejected the record because statement-to-evidence binding was invalid. The catalog retained the rejected record for audit.

B then emitted two individually valid signed bundles for the same URL and a shared declared claim key, with different actual payload/WARC/package digests. The verifier retained both and emitted their issuer, target, claim key, statement IDs and distinct payload hashes. It chose no winner.

This is catalog/evidence conflict detection. It is **not CT/SCITT equivocation proof**, because no transparency service receipt, signed tree head, consistency proof or gossip witness was present. Existing CT/SCITT mechanisms can be added if strong log-level non-equivocation is required.[6] [7]

## 4. A–N required results

| Question | Result | Exact boundary |
| --- | --- | --- |
| A. Cross-archive discovery | **PASS** | Works across the declared signed peer set. |
| B. Cross-operator discovery | **PASS** | Finds A/B/C technical environments; not proof of real organizational independence. |
| C. Preserve original agency | **PASS** | Original signer/issuer remains foreign after import; importer signs only its own import catalog. |
| D. Offline operation | **PASS** | Surviving local peers and replicas continue; no guarantee after loss of every copy. |
| E. No-central synchronization | **PASS, manual/static** | Direct peer fetch/import and replicated peer descriptors; no central DB. No automatic global gossip was tested. |
| F. Detect equivocation | **PARTIAL** | Same-signer conflicting catalog claims detected; no CT/SCITT receipt-level proof. |
| G. Preserve conflicts | **PASS** | Valid difference, invalid binding and conflicting valid claims all retained. |
| H. Verify evidence | **PASS** | Statement, signer, WACZ resources, package and WARC payload binding verified. |
| I. Verify history source | **PASS, bounded** | Key-controlled issuer/capture provenance verified; not origin-server non-repudiation. |
| J. Declare scope | **PASS** | Local/import and peer-set completeness claims are explicit and bounded. |
| K. Continue after operator/index disappearance | **PASS** | C endpoint/storage removal leaves B’s retained C copy usable. |
| L. New operator joins without central approval | **PASS, experimental** | C creates own key/catalog/capture and imports B via public endpoint. |
| M. Multi-implementation interoperability | **PASS** | Python A, Node B and shell/OpenSSL C produce/consume foreign bundles. |
| N. Existing deployed complete system | **NO CONFIRMED SINGLE COMPLETE DEPLOYMENT FOUND** | This audit found deployed component systems, not a single documented deployed A–M turnkey network. This is not evidence of absence. |

The detailed matrix and raw output links are in [`capability_gap_matrix.md`](capability_gap_matrix.md).

## 5. Existing deployed prior art: what it settles and what it does not

Memento Aggregator is direct prior art for federation: it discovers Mementos across archives and exposes TimeGate/TimeMap APIs, but its published architecture uses configured archive rules, central cache and MySQL.[8] InterPlanetary Wayback is direct prior art for WARC/IPFS content-addressed dissemination, opt-in replication, CDXJ indexing and replay.[9] WACZ/IPFS specifies content-aware WARC/WACZ chunking, content addressing and deduplication.[10] Webrecorder’s decentralized archive use cases explicitly cover local copies, repository storage, journalism, aggregation, authenticity, logs and lost-site reconstruction.[11]

These systems do not constitute evidence that one currently deployed product provides every requested A–M characteristic in one ready-made service. They do prove that the principal building blocks are mature prior art. The actual experiment closes the remaining gap: it assembled those classes of public mechanisms into a working standards-only network without OIN-specific protocol machinery.

## 6. Capability-gap result

The user’s original vision is technically achievable with existing technology. The network passed the core capabilities under real interaction and adverse node conditions. Its additional glue is a documented interoperability profile: exact target matching, statement fields, signature input, package binding checks, import semantics, peer-descriptor scope and conservative output labels. Existing standard extension mechanisms are designed for such domain/profile mappings; a mapping is not a new irreducible network protocol.[2] [3] [4]

| Alleged missing mechanism | Result | Why |
| --- | --- | --- |
| Cross-operator capture exchange | **Not missing** | WARC/WACZ + signed statement + HTTP/Git/IPFS transfer and public keys work. |
| Foreign agency preservation | **Not missing** | Detached original signed statement stays immutable; importer signs a separate provenance/import record. |
| Conflict retention | **Not missing** | Ordinary append-only catalogs retain all signed records; verifier reports condition without adjudication. |
| Offline recovery / replica operation | **Not missing** | Multiple local stores and copied descriptor/import data work without central database. |
| Cross-peer discovery | **Not missing as a primitive** | Static lists, Memento archive lists/aggregators, DHT/DNS/registry/gossip options are deployment choices. |
| Log equivocation proof | **Not missing** | CT/SCITT already provide log mechanics; archive aggregation policy is a profile/governance decision. |
| Proof of real independent observers | **Impossible from protocol alone** | It requires external evidence about organization, hosting, network and governance. |
| Global history completeness | **Not a finite-network guarantee** | It requires a declared universe/scope; no protocol can infer global completeness from local non-return. |

## 7. Final answer

**现有技术能直接拼成一个真正工作的开放 Web observation network。** 本次真实三环境实验已经运行了这种组合，并在 discovery、验证、复制、离线、恢复、operator/index disappearance、新加入、恶意 binding、冲突保留和跨实现互操作上得到可复核结果。

**差距不在新的网络协议。** 现实部署仍需要治理、operator enrollment/discovery policy、availability/replication policy、privacy/abuse controls、real multi-vantage hosts、transparency-service selection、key lifecycle和范围声明。这些是 deployment、governance 和 profile engineering 问题。它们不能被包装成 OIN-specific irreducible protocol innovation。

**本审计没有发现任何现有标准/profile/extension 无法表达的最小新增网络机制。** 因而没有可诚实定义为“OIN 不可替代核心网络机制”的对象。

## 8. Evidence map and references

| Evidence | Content |
| --- | --- |
| [`methodology.md`](methodology.md) | Locked experimental boundaries and pass/fail criteria. |
| [`architecture.md`](architecture.md) | Three-environment architecture and standards-only mapping. |
| [`targets.json`](targets.json) / [`target_preflight.md`](target_preflight.md) | Real public URL corpus and verified availability. |
| [`results/discovery_and_agency.md`](results/discovery_and_agency.md) | Cross-peer verification and agency-preserving import. |
| [`results/offline_recovery_baseline.md`](results/offline_recovery_baseline.md) | Offline, recovery, endpoint/storage removal evidence. |
| [`results/adversarial_and_conflict.md`](results/adversarial_and_conflict.md) | Invalid binding and conflicting claim evidence. |
| [`capability_gap_matrix.md`](capability_gap_matrix.md) | A–N matrix, prior art and detailed boundaries. |
| [`operators/`](operators/) / [`results/`](results/) | Raw signed packages, catalogs, statements, signatures and verifier outputs. |

[1] [IIPC, WARC Format 1.1](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/).  
[2] [Web Archive Collection Zipped (WACZ)](https://specs.webrecorder.net/wacz/1.1.1/).  
[3] [WACZ Signing/Verification Specification](https://github.com/webrecorder/wacz-auth-spec/blob/main/spec.md).  
[4] [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/).  
[5] [W3C PROV-DM](https://www.w3.org/TR/prov-dm/).  
[6] [RFC 9162 — Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html).  
[7] [RFC 9943 — SCITT Architecture](https://www.rfc-editor.org/rfc/rfc9943.html).  
[8] [LANL TimeStitch Memento Aggregator](https://github.com/lanl/TimeStitch-Memento-Aggregator).  
[9] [InterPlanetary Wayback](https://github.com/oduwsdl/ipwb).  
[10] [WACZ IPFS Custom File Chunking](https://github.com/webrecorder/specs/blob/main/wacz-ipfs/latest/index.md).  
[11] [Use Cases for Decentralized Web Archives](https://specs.webrecorder.net/use-cases/latest/).  
[12] [RFC 7089 — Memento](https://www.rfc-editor.org/rfc/rfc7089.html).
