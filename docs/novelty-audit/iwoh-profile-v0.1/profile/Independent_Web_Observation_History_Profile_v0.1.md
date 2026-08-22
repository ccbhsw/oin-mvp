# Independent Web Observation History Profile v0.1

**状态：** 实验性 profile 草案；不是 OIN 已证实创新，也不是新的存储、密码学、归档、透明日志或 P2P 协议。  
**目的：** 让互不共享实现的 Web archive 能够以现有 WARC/WACZ、VC/PROV、C2PA、Memento、SCITT/CT 和 HTTP 语义，对网页捕获记录作出一致、可验证、非裁决的解释。  
**非目标：** 断言网页内容真实；证明现实运营独立性；证明全网历史完整；替代 WARC、WACZ、C2PA、PROV、VC、SCITT、CT、IPFS 或 Memento。

> 本文中的 `MUST`、`MUST NOT`、`SHOULD` 和 `MAY` 按 RFC 2119 / RFC 8174 解释。

## 1. 设计原则

HTTP 中的 URI 标识 resource，而一次 HTTP response 携带的是在特定请求、协商和服务器状态下选出的 representation；同一 resource 可有多个 representations。[1] Memento 已定义 URI-R、URI-M、TimeMap 与 TimeGate 以表达同一 Original Resource 的时间化 prior state。[2] 本 profile 不替代这些概念，而只规定捕获 archive 如何在缺少全局权威的情况下报告它们。

任何 Profile result 都是对**已提交的证据和声明**的机器可验证结论，而不是对世界事实的裁决。一个通过验证的 statement 仅表达“其签名者声称在声明的 capture activity 中获得了相应 evidence bytes”。

## 2. 术语

**Request Target** 是 HTTP request line 中的目标 URI，经 RFC 3986 基本规范化后、移除 fragment 的 URI。fragment 不随 HTTP request 发送，因此不得参与 HTTP capture identity。

**Capture Representation** 是一次完整 HTTP request/response exchange 中记录的 status、selected response headers 和 response body。它不是 URL 所指资源本身。

**Capture Statement** 是符合本 profile 的、由 capture agent 签名的 VC-style statement；它描述一份 Capture Representation 和可验证 evidence artifact。

**History View** 是某个 archive 或 aggregator 在一个明确 scope 内已知的 Capture Statement 集合。它不是“全网完整历史”的同义词。

**Evidence Artifact** 是包含原始 request/response evidence 的 WARC/WACZ package；其完整性由 WACZ/WARC fixity 和 statement 内所绑定的 digest 验证。[3] [4]

## 3. Conformance

一个 **Statement Producer** 必须生成第 5 节的最小 statement。一个 **History Provider** 必须生成第 9 节的 History View。一个 **Verifier** 必须按第 6–11 节生成可重复的 grouping、validity、comparability、relationship、scope 与 equivocation result。

每个 Profile document 或 API response 必须包含 `profile_version: "IWOH-0.1"`。不含该值的 WARC、WACZ、C2PA manifest、VC、PROV graph、SCITT statement 或 TimeMap 仍可被保存与展示，但不得被声称为本 profile 的完整互操作结果。

为避免为测试创造私有签名格式，IWOH-0.1 的 Capture Statement proof **MUST** 使用 W3C `DataIntegrityProof` 的 `eddsa-jcs-2022` cryptosuite：输入 JSON 必须符合 I-JSON，按 RFC 8785 JCS canonicalize，依 W3C 定义的 proof configuration/document hash procedure 生成 Ed25519 detached signature，且 `proofValue` 必须使用 Multibase base58-btc 表示。该要求直接采用 W3C Recommendation；profile 不定义新的 signature algorithm、key format 或 canonicalization。[9] [10]

## 4. Web Target Identity

### 4.1 Request Target Key

每条 Capture Statement 必须包含：

```json
{
  "request_target": {
    "uri": "https://example.org/news?id=7",
    "uri_normalization": "rfc3986-basic; fragment-removed",
    "identity_kind": "request-target"
  }
}
```

`uri` 必须保留 query component。Profile 不允许默认删除 `utm_*`、session id、`ref` 或任何其它 query parameter，因为 HTTP 并不定义这些参数是否语义无关。不同 query URI 的 default relation 是 `DISTINCT_REQUEST_TARGETS`。

### 4.2 Target Relation，而不是秘密的 canonical URL 合并

redirect、HTML `rel=canonical`、HTTP `Link: rel=canonical`、mirror、alias 和人工声明都只能建立**显式 Target Relation**，不能在没有 evidence 的情况下改变 request-target identity：

```json
{
  "target_relations": [
    {
      "relation": "redirect-final-uri | html-canonical | http-canonical | declared-mirror | declared-alias",
      "from": "https://example.org/a",
      "to": "https://example.org/b",
      "evidence_locator": "warc://...#record-id",
      "asserted_by": "response | archive | external-signer"
    }
  ]
}
```

Verifier 必须输出以下之一：`EXACT_REQUEST_TARGET`、`RELATED_TARGET`、`DISTINCT_REQUEST_TARGETS`、`TARGET_RELATION_UNVERIFIED`。它不得把 `RELATED_TARGET` 自动提升为同一 logical target。这样既处理 redirect/canonical/mirror/alias，又避免将 `canonical_url = normalized URL` 误作身份协议。

### 4.3 认证、地理与表示选择

authentication state、cookie jar、IP/ASN、proxy、locale、Accept-*、User-Agent、content negotiation 和 server side personalization 不是 target identity 的组成部分；它们是 representation selection context。若 capture 未记录这些因素，target identity 不失效，但后续 comparability 可能是 `INCOMPARABLE`。

## 5. 最小 Capture Statement

本 profile 的规范化交换 envelope 是 **W3C Verifiable Credential 2.0**，并以 `type: ["VerifiableCredential", "WebObservationCapture"]` 表示；PROV 语义用于 agent/activity/entity 关系。C2PA manifest、SCITT transparent statement、RFC 3161 token、WACZ Auth signature 或 IPFS CID 可作为 evidence extension，不替代本节必填字段。[5] [6] [7]

| 字段 | 要求 | 语义 |
| --- | --- | --- |
| `profile_version` | REQUIRED | 必须为 `IWOH-0.1`。 |
| `id` | REQUIRED | 签名 statement 的 URI；不得以 URL hash 冒充全局 Web object identity。 |
| `issuer` | REQUIRED | VC issuer / PROV SoftwareAgent；必须可解析为 verification method。 |
| `proof` | REQUIRED | `type: "DataIntegrityProof"`、`cryptosuite: "eddsa-jcs-2022"`；验证的是 issuer 对 statement 的签名。 |
| `capture_activity` | REQUIRED | PROV Activity；含 `started_at`、`ended_at`、method 与 capture software identifier。 |
| `request_target` | REQUIRED | 第 4.1 节定义。 |
| `request_context` | REQUIRED | method、recorded request headers、authentication class、network-vantage disclosure。不得记录原始 secret/cookie。 |
| `response` | REQUIRED | status、recorded response headers、raw body digest、body byte length。 |
| `evidence` | REQUIRED | WARC/WACZ locator、WARC digest、WACZ digest、payload digest、record locator、artifact retrieval URI 或 content address。 |
| `time_evidence` | REQUIRED | `local-declaration`、`rfc3161`、`transparency-receipt`、`causal-receipt` 或 `none`；含 precision/uncertainty 与适用的 proof/receipt。 |
| `capture_context_completeness` | REQUIRED | `COMPLETE_FOR_REPRESENTATION_SELECTION`、`PARTIAL` 或 `UNKNOWN`。 |
| `target_relations` | OPTIONAL | 第 4.2 节；缺失时不推断 alias/canonical/mirror。 |
| `transparency` | OPTIONAL | SCITT/CT/Rekor receipt、checkpoint、log ID、inclusion/consistency proof。 |
| `c2pa` | OPTIONAL | C2PA manifest locator/digest。 |
| `provenance` | OPTIONAL | 扩展 PROV bundle/graph。 |

`evidence.wacz_digest` 和 `response.payload_digest` 必须分别验证 package bytes 与从 WARC record 重建的 response body bytes。archive hash 与 payload hash 不得互相替代。WACZ 已规定 package manifest 与 resource fixity；WACZ Auth 可提供 archive creator signature 与 time evidence。[3] [4]

当 `time_evidence.kind` 为 `causal-receipt` 时，`receipt` 必须是一个独立签名的 `WebObservationSequenceReceipt` VC。它必须使用同一 `eddsa-jcs-2022` cryptosuite，包含 `id`、`issuer`、`statement_id`、`log_id`、整数 `ordinal`、`interval.not_before`、`interval.not_after` 与 `predecessor_statement_ids`。receipt issuer 的 verification method 必须可由 verifier 的明确 trust registry 或受信 transparency service policy 解析。该 structure 采用 VC/EdDSA 作为载体；本 profile 只规定它何时足以支持 history ordering，不创造时间戳算法。

## 6. Evidence Validity

Verifier 必须以如下顺序得出 `statement_validity`：

1. 验证 VC proof；失败则 `INVALID_SIGNATURE`。
2. 验证 `proof.verificationMethod` 属于 `issuer` 的 assertion method 或由 verifier 的明确 trust registry 映射；失败则 `INVALID_AGENT_BINDING`。
3. 检索 WACZ/WARC artifact；不可得则 `EVIDENCE_UNAVAILABLE`。
4. 验证 WACZ/WARC digest；失败则 `INVALID_ARCHIVE_DIGEST`。
5. 从指定 WARC record 提取 HTTP payload，验证 `payload_digest`；失败则 `INVALID_PAYLOAD_DIGEST`。
6. 验证可选 C2PA/SCITT/RFC 3161 proof，或 `causal-receipt` 的独立 VC proof；失败则 `INVALID_EXTERNAL_EVIDENCE`。
7. 全部必填校验通过才为 `VALID`。

`VALID` 不表示 HTTP source、内容含义、页面事实、archive 运营者或 issuer 的现实身份为真。

## 7. Comparability

`Comparable(A,B)` 仅在下列所有条件为真时成立：

1. `request_target.uri` 完全相同，或存在一个已验证且双方一致采用的 Target Relation policy；
2. HTTP method 相同；
3. 两条 statement 都是 `VALID`；
4. `capture_context_completeness` 都是 `COMPLETE_FOR_REPRESENTATION_SELECTION`；
5. 将两个 response 的 `Vary` header field names 取并集后，所有相应 request header values 均被记录且逐项相同；
6. authentication class 相同；
7. network-vantage disclosure 相同，或者双方均明确声明 `vantage_effect: NONE_EXPECTED`；
8. request policy（redirect handling、cookie policy、content decoding、capture scope）相同。

任何一个必填信息缺失时，Verifier 必须返回 `INCOMPARABLE`，并附一个或多个 reason code：`TARGET_MISMATCH`、`UNVERIFIED_TARGET_RELATION`、`METHOD_MISMATCH`、`INVALID_EVIDENCE`、`INCOMPLETE_CONTEXT`、`VARY_VALUE_MISMATCH`、`AUTH_CONTEXT_MISMATCH`、`VANTAGE_MISMATCH`、`CAPTURE_POLICY_MISMATCH`。

HTTP `Vary` 指示 response selection 的可变维度；因此同 URL 的英文与中文、不同 User-Agent、不同 geographic/CDN response 或身份认证 response 的不同 bytes 不得直接被归类为 temporal change 或 conflict。[1]

## 8. Observation Relationship 与时间语义

对于两条 valid statement，Verifier 必须使用以下互斥关系：

| 关系 | 先决条件 | 含义 |
| --- | --- | --- |
| `SAME_STATEMENT` | 相同 `id` 且相同 signed statement digest | 同一已签名陈述。 |
| `REPEATED_OBSERVATION` | Comparable；不同 capture activity；相同 payload digest | 不同 capture 活动记录到相同 representation bytes。 |
| `TEMPORAL_VARIATION` | Comparable；payload digest 不同；可信时间 intervals 不重叠且先后次序由 `rfc3161`、透明 receipt 或可验证 causal receipt 证明 | 在 profile 可证明的顺序内观察到不同 representation。 |
| `PARALLEL_OBSERVATION` | Comparable；payload digest 不同；两个 statement 的可信时间 intervals 重叠，且 profile evidence 中不存在任一指向另一方的 causal predecessor | 在 profile evidence 范围内未建立顺序的不同 captures；不声称物理同时发生。 |
| `REPRESENTATION_VARIATION` | 同一个或已验证 related target；payload digest 不同；Context 原因是 Vary/auth/vantage/policy difference | 不同选择 context 下的 representation；不是 content conflict。 |
| `INCOMPARABLE` | 第 7 节任一条件失败，且不满足 representation variation 的已知 context 理由 | 无法安全比较。 |
| `UNKNOWN` | statement/evidence/time/relation information不足 | 不作分类。 |

本 profile **禁止**使用“不同 hash + 固定秒数阈值”判定 temporal、parallel 或 conflict。只有有效 RFC 3161 token、有效 transparency receipt，或有效 `causal-receipt` 所携带的 time interval、precision、uncertainty 和 causal predecessor 可参与时序推断。`local-declaration` 时间仅支持 `LOCAL_TIME_REPORTED`，不支持 `TEMPORAL_VARIATION` 或 `PARALLEL_OBSERVATION`。

## 9. Non-Adjudication 与 History View

History Provider 必须保留所有 `VALID` Capture Statement；它不得因 payload 不同而删除另一条 statement。`relation` 仅描述 evidence 之间的关系，不输出 `true`、`false`、`correct`、`incorrect`、`winner` 或 consensus result。

每个 History View 必须由 History Provider 以第 3 节的 `eddsa-jcs-2022` proof 签名，并包含 `id`、`issuer`、`proof`、`profile_version` 及：

```json
{
  "history_scope": "ARCHIVE_LOCAL | DECLARED_PEER_SET | TRANSPARENCY_LOG | UNKNOWN",
  "coverage": {
    "target_relation_policy": "exact-request-target-only | profile-policy-id",
    "time_interval": {"from": "...", "until": "..."},
    "ingestion_policy": "..."
  },
  "completeness": "COMPLETE_FOR_DECLARED_SCOPE | PARTIAL | UNKNOWN",
  "scope_evidence": "SCITT/CT checkpoint URI or null"
}
```

`COMPLETE_FOR_DECLARED_SCOPE` 只能在 History Provider 提供已验证的 statement-set commitment（如 SCITT/CT checkpoint）并明确声明 target relation policy、时间范围、ingestion policy 与 peer set 时使用。它绝不意味着全局 Web history 完整。Memento TimeMap 表示某个 server 可提供的 Mementos；profile 必须把该 server scope 显示出来，而不是暗示其穷尽全网。[2]

## 10. Cross-Archive Discovery 与 Statement Exchange

History Provider 必须支持以下至少一种 discovery method，并在 profile response 中声明 `discovery_method`：

- `memento-timemap`：使用 RFC 7089 `rel="timemap"` 与 `rel="memento"`；
- `http-link`：对 target 或 history endpoint 使用 HTTP Link 关系；
- `declared-peer-set`：一个已签名的 peer descriptor，列出完成查询所覆盖的 archives；
- `out-of-band-registry`：外部 registry URI 与 registry trust policy。

profile 不定义全球 archive discovery，也不把任一 registry 当作默认权威。未声明 peer set 时，`history_scope` 必须为 `ARCHIVE_LOCAL` 或 `UNKNOWN`。

Statement exchange 的基本单元是：

1. `WebObservationCapture` VC statement；
2. 引用的 WACZ/WARC artifact；
3. 所有 required evidence digest；
4. 可选 C2PA manifest、PROV graph、SCITT receipt 与 Memento links。

接收 archive 必须按第 6 节验证后，才将 statement 标为 `IMPORTED_VALID`。它可以拒绝 policy 不允许的 statement，但不得把 `IMPORTED_VALID` 的可验证历史改写为自身 capture。WACZ 已可作为静态、可复制、独立 package 分发；SCITT 可作为 content-agnostic signed statement registration 层，但 SCITT 本身把 storage/discovery/notification 留在 application profile 范围。[3] [7]

## 11. History Conflict、Correction、Deletion 与 Equivocation

一条后续 statement 是 `LEGITIMATE_NEW_STATEMENT`，当其拥有新的 `id`、有效签名、有效 evidence，且在同一 transparency log 内以可验证 inclusion/consistency proof 追加。

`CORRECTION` 必须是新的 signed statement，包含 `supersedes: [prior-statement-id]` 和 correction reason；它不得删除或重写 prior evidence。

`DELETION_DECLARATION` 必须是新的 signed tombstone statement；它只表示 archive 的可用性/保留政策变化，不表示 prior capture 未发生。

`MISSING_HISTORY` 只能表示“在声明 scope 内没有列出某 statement”；若 scope 不为 `COMPLETE_FOR_DECLARED_SCOPE`，Verifier 必须改为 `HISTORY_ABSENCE_UNPROVEN`。

`EQUIVOCATION_DETECTED` 仅在同一个 named SCITT/CT-style log 对同一 tree size 产生两个有效但不同的 signed root/checkpoint，或同一 declared complete History View 在相同 scope/checkpoint 对同一 query 产生不可协调的 signed responses 时成立。没有 receipt/consistency proof/witness evidence 时，结果必须是 `EQUIVOCATION_NOT_DETECTABLE`，而不是 `NO_EQUIVOCATION`。CT 和 SCITT 已为单个 transparency service 的 inclusion、consistency、receipt、auditor 与 non-equivocation 提供机制；profile 只规定 archive history response 如何使用这些已有机制。[7] [8]

## 12. 最小 Conformance Test 要求

一个实现必须能够在公开 fixture corpus 上输出相同的：

1. target identity / target relation result；
2. statement validity；
3. comparability；
4. relationship classification；
5. history membership；
6. completeness / scope；
7. statement import validity；
8. equivocation status。

至少必须覆盖：redirect、canonical alias、fragment、query variation、Vary/language、geographic/vantage variation、User-Agent/auth variation、same bytes repeated、ordered changed bytes、unordered different bytes、missing history、tampered WACZ、inconsistent agent disclosure、clock skew、partial history、contradictory checkpoints。

## 13. 已知限制

本 profile 的关键规则 R1–R8 是现有标准间的严格 mapping，而不是独立基础原语。它可能有用，也可独立实现和 conformance-test；但在外部团队实现并确认这些 semantics 不能通过现有 C2PA/VC/PROV/Memento/SCITT extension/profile 直接表达前，不得称为 OIN Protocol Candidate。

## References

[1] [RFC 9110 — HTTP Semantics](https://datatracker.ietf.org/doc/html/rfc9110)  
[2] [RFC 7089 — Memento](https://datatracker.ietf.org/doc/html/rfc7089)  
[3] [WACZ Specification 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/)  
[4] [WACZ Signing and Verification](https://specs.webrecorder.net/wacz-auth/0.1.0/)  
[5] [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/)  
[6] [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)  
[7] [RFC 9943 — SCITT Architecture](https://datatracker.ietf.org/doc/html/rfc9943)  
[8] [RFC 9162 — Certificate Transparency Version 2.0](https://datatracker.ietf.org/doc/html/rfc9162)  
[9] [W3C Data Integrity EdDSA Cryptosuites v1.0](https://www.w3.org/TR/vc-di-eddsa/)  
[10] [RFC 8785 — JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785)
