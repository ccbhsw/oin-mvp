# OIN Original Mission Capability Gap Audit — 实验方法 v0.1

**状态：** 进行中。  
**研究对象：** 使用公开标准与公开实现构建跨 operator、跨 archive、可验证、可复制、非单中心控制的 Web observation history network 的能力。  
**不研究：** OIN 或 IWOH 的底层协议新颖性、融资、市场、部署公网或生产化。

## 1. 锁定边界

本实验不得读取、导入、复制或调用 OIN MVP 源码、数据库 schema、Object/Observation/Observer 命名、IWOH 私有协议、IWOH fixture 或其实现代码。实验目录与 OIN 工作区物理隔离。实验中若必须定义字段，只能使用已有公开标准的既有字段或明确标为 **standards-extension mapping**；该 mapping 本身不是新协议主张。

本实验不部署公网、不购买服务器、不扩展 OIN 生产节点。网络实验在当前会话的本地隔离环境中完成；它测试真实进程、真实密钥、真实公开 URL 的 HTTP capture、WARC/WACZ artifact、签名、Git/object replication 和 offline/recovery 行为。它不冒充三个现实独立组织。

## 2. Operator 模型

因当前没有可招募的外部 archive operators，本实验使用三个完全隔离的 **experimental operator environments**，而不是把它们称为真实独立机构。每个 environment 必须具有独立目录、独立 Ed25519 key、独立 process/runtime、独立 WARC/WACZ storage、独立 signed catalog 和独立 Git/object store。A 用 Python；B 用 Node.js；C 使用第三套公开工具链或 shell/Git/standards-compliant utility。任何共享文件只能通过受记录的 replication/import step 进入另一 operator。

> “隔离 experimental operator”证明技术上的多主体/多实现能力，不证明组织、资金、法律、托管或网络出口的现实独立性。

## 3. 公开标准栈候选

| 能力 | 允许的公开标准或实现 | 禁止替代 |
| --- | --- | --- |
| HTTP capture / evidence | HTTP、WARC 1.1、WACZ | OIN capture format / OIN schema。 |
| integrity | SHA-256、WARC/WACZ digest、Ed25519 | OIN-specific signing envelope。 |
| signer/provenance | W3C VC 2.0、PROV-DM、W3C Data Integrity EdDSA JCS | OIN identity/observer schema。 |
| temporal navigation | Memento links/TimeMap where provided; signed capture time as bounded local claim | OIN history time model。 |
| replication / offline sync | Git signed/object transport, local content-addressed store, static files | OIN replication protocol。 |
| transparent registration / equivocation test | CT/SCITT semantics only where actual receipts exist; otherwise signed conflicting catalogs are retained as application evidence | OIN transparent-log implementation。 |
| discovery | public standards metadata plus signed static catalogs / Git remotes, with mapping documented | OIN discovery API or directory。 |

## 4. Baseline 与 network 实验

**Baseline** 是每个 archive/operator independently holding its own WARC/WACZ evidence, metadata and signature with no shared discovery or import operation.  
**Network** 是三个 experimental operators 使用公开 standard artifacts、signed catalogs 和 documented static/Git discovery/import steps；任何 operator can independently verify foreign artifacts and retain foreign issuer agency.

对每项能力，实验只报告四种结果：`PASS`、`FAIL`、`PARTIAL`、`UNAVAILABLE_IN_THIS_ENVIRONMENT`。`UNAVAILABLE` 不可被解释为标准不足或网络不可行。

## 5. 必测能力与证据要求

| 能力 | PASS 的最低证据 |
| --- | --- |
| cross-archive/operator discovery | 仅提供 URL，第三方可从非中心目录/peer catalog 找到至少两个 operator 的 signed entries、location 和 verifier result。 |
| original agency preservation | A 导入 B artifact 后，B’s signer/issuer remains cryptographically bound and A records only an import activity. |
| evidence verification | foreign verifier recomputes artifact/payload digest and validates signature from public verification material. |
| replication/import | A verifies B’s artifact, imports a byte-identical copy and retains B’s signed original statement; no field is rewritten as A capture. |
| offline / recovery | B storage/catalog becomes unreachable; A/C queries still work from their local peers; B resumes and imports missing items. |
| conflict preservation | distinct payloads/statements are retained and exposed; no network component selects a winner. |
| malicious invalid statement | a digest/signature or issuer-binding failure is detected and retained as invalid evidence, not converted to valid history. |
| equivocation signal | two valid but conflicting signed catalog statements from one experimental operator are discoverable and both preserved; this is **not** CT/SCITT cryptographic log equivocation unless actual same-log proofs are present. |
| operator/index disappearance | delete/withdraw one peer’s local store and one catalog; remaining operator histories and foreign imported evidence remain discoverable/verifiable from remaining peers. |
| new operator join | C starts with only public standard docs + peer locations, creates own signed artifact/catalog, discovers at least one peer and imports/verifies it. |
| implementation interoperability | A/Python, B/Node, C/third tool each consume at least one foreign evidence bundle successfully. |

## 6. 真实 URL 情形纪律

每个 operator must capture the same public URL set. `unchanged`, `changed`, redirect, canonical, language/request-header, query and failure cases require actual public HTTP interaction and saved request/response evidence. A same-egress sandbox cannot establish true geographic/operator network independence or genuine CDN geography variation. Such a case will be labeled `UNAVAILABLE_IN_THIS_ENVIRONMENT` unless a public, independently evidenced multi-vantage record can be verified without fabrication.

## 7. 最终判定

如果 Network 在不使用任何 OIN-specific network protocol 的条件下通过跨 operator discovery、agency preservation、offline replication/recovery、conflict preservation、new operator join、evidence verification 与 three-implementation interoperability，则必须声明：

> **OIN 的网络架构本身不是技术创新。**

若某项失败，必须先区分 implementation defect、sandbox limitation、missing public infrastructure、existing-standard profile choice 与无法由已有标准/profile/extension 表达的 mechanism。只有最后一种情况，才允许写出“最小新增网络机制”；同时必须给出其 precise semantics、prior-art check 与独立实现结果。

## 8. 已部署替代系统的初步原始证据

Webrecorder 的《Use Cases for Decentralized Web Archives》明示 portable/distributed Web archive collections 的目标，并列出 researcher local copy、institutional repository、journalism source archive、aggregated recurring crawls、cross-archive reconstruction、offline-first materials、creator trust evaluation 和 physical-media repatriation 等场景。该文档同时把 authenticity、logs、aggregation、share、technical metadata、fidelity 等列为 requirements。[1] 它证明原始愿景的多个组件已有公开标准社区在研究/实现；它不单独证明一个 deployed system 已完整实现 operator discovery、agency-preserving import、offline reconciliation 和 equivocation detection 的全组合。

WACZ-on-IPFS specification 定义 WARC/WACZ content-aware chunking, UnixFS content addressing, WARC-record/payload-level deduplication and WACZ reconstruction without duplicating data。[2] 它支持 independent artifact storage/replication and content verification, but does not define capture-agent statement semantics, peer discovery policy, history scope or conflict/equivocation treatment.

The LANL Memento Aggregator source describes a deployed-style Java service that federates archives, discovers mementos for an Original-URL, exposes TimeGate/TimeMap, and caches results in MySQL with configured archive rules.[3] This is strong prior art for cross-archive discovery. It also is an explicit counterexample to non-centralization: the aggregator is a service with central cache/rules and deliberately strips HTTP/HTTPS distinction. It is not evidence of a fully decentralized, agency-preserving observation network.

[1] https://specs.webrecorder.net/use-cases/latest/
[2] https://github.com/webrecorder/specs/blob/main/wacz-ipfs/latest/index.md
[3] https://github.com/lanl/TimeStitch-Memento-Aggregator

InterPlanetary Wayback (ipwb) 是直接 prior art：它将 WARC response headers/payload disseminate into IPFS, obtains content-addressed deduplication/opt-in replication, writes CDXJ references, and replays a CDXJ index from a local path, HTTP location or IPFS hash.[4] IPFS ecosystem describes it as a full indexing/replay system that decouples individual captures from the original machine.[5] It covers independent WARC/IPFS storage, opt-in replication, index-based discovery and replay. It does not in its published README define signed capture-agent claims, cross-operator agency-preserving import, scoped history commitments, conflict/equivocation semantics or membership admission policy.

WACZ Auth 0.1 is direct prior art for portable archive creator identity, package manifest/hash verification, public-key or domain-certificate signing and RFC 3161 timestamp verification. It explicitly states WACZ can be distributed through any online network in a decentralized manner, while also stating that authenticity from the Web server perspective is not possible with current HTTP/S and that creator identity may need external key management.[6] This eliminates any claim that OIN must invent Web archive signing, package integrity, creator identity or timestamping.

[4] https://github.com/oduwsdl/ipwb
[5] https://ecosystem.ipfs.tech/project/interplanetary-wayback
[6] https://github.com/webrecorder/wacz-auth-spec/blob/main/spec.md
