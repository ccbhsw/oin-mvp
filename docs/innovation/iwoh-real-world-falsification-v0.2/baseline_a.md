# Existing-Standards Baseline-A

**规则：** 本基线只使用 HTTP、Memento、WARC/WACZ、PROV、VC、SCITT、CT 和真实 corpus 中已经实际获得的 evidence。标准未规定或 evidence 未提供的判断必须写为 **`UNDEFINED_BY_EXISTING_STANDARDS`** 或 **`NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`**，而不是另行补充规则。

## 原生输出词表

| 输出 | 含义 | 是否是新规则 |
| --- | --- | --- |
| `LITERAL_URI_EQUAL` / `LITERAL_URI_DIFFERENT` | 两个已有 evidence field 的 URI string 相同/不同。 | 否；纯字符串事实。 |
| `ARCHIVE_REPORTED_DATETIME_BEFORE` / `ARCHIVE_REPORTED_DATETIME_EQUAL` | 两个 archive-provided datetime field 的字面时间比较。 | 否；不主张 source event causality。 |
| `SAME_REPORTED_DIGEST` | 同一 archive index 使用相同 digest string 报告两个 records。 | 否；不替代 payload-byte re-hash 或 agency proof。 |
| `DIFFERENT_REPLAY_BODIES_OBSERVED` | 实际访问的 replay 页面可见内容不同。 | 否；不推断 origin-server truth。 |
| `RESPONSE_HEADER_INPUT_RECORDED` | 一条 WARC response 实际保留了 relevant HTTP/WARC header input。 | 否；不定义 compare decision。 |
| `UNDEFINED_BY_EXISTING_STANDARDS` | 在准许的 standards-only 组合中没有统一定义的结果。 | 否；明确拒绝造规则。 |
| `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE` | 一般标准可以承载某类信息，但 corpus 没有实际 evidence。 | 否；明确拒绝由缺失推出否定。 |

## 对真实 cases 的基线结果

| Case | 直接可得事实 | Target / representation 结论 | 时间、重复、并行结论 | history scope / absence | agency / import | equivocation | 原生依据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BA-01：IA `example.com` 2010 vs 2024 | 两条实际 replay；original URL literal 相同；可见 body 不同。 | `LITERAL_URI_EQUAL`; `DIFFERENT_REPLAY_BODIES_OBSERVED`。HTTP 定义 representation，但未定义 archive replay body 的跨时历史分类。 | `ARCHIVE_REPORTED_DATETIME_BEFORE`; source-side causal change、parallel observation、repeated observation 均 `UNDEFINED_BY_EXISTING_STANDARDS`。 | 两条 local captures 不表示 collection completeness；对中间/其他 dates 的 absence 为 `UNDEFINED_BY_EXISTING_STANDARDS`。 | Wayback API/replay 不提供本 corpus 所需的 signed original observer or import chain，故 `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | RFC 9110 resource/representation；RFC 7089 Memento datetime。 |
| BA-02：Arquivo.pt 2010 multiple `www.example.com` CDX rows | 实际 CDX response 中多条 `http://www.example.com/` rows 使用 digest `EF7...`。 | `LITERAL_URI_EQUAL`; same digest is index evidence, not a target-equivalence algorithm. | `SAME_REPORTED_DIGEST`; datetime order can be compared row-by-row. “Repeated observation” and any causal reason for repetition are `UNDEFINED_BY_EXISTING_STANDARDS`。 | CDX query only states returned holdings; unreturned records / other archives remain `UNDEFINED_BY_EXISTING_STANDARDS`。 | No provenance statement naming capture agent in collected row; `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | WARC digest fields and CDX record metadata; RFC 7089’s server-local holdings model. |
| BA-03：Arquivo.pt 与 IA 同 URL、同 14-digit datetime | 两个不同 archive endpoints 实际报告 `http://www.example.com/` 与 `20100323155533`。 | `LITERAL_URI_EQUAL`; RFC 7089 allows multiple servers hosting versions, but contains no rule that equal datetime identifies one capture event. | `ARCHIVE_REPORTED_DATETIME_EQUAL`; same event, repeated, parallel, temporal change are `UNDEFINED_BY_EXISTING_STANDARDS`。 | Neither endpoint claims a global TimeMap; global history and absence are `UNDEFINED_BY_EXISTING_STANDARDS`。 | Neither collected artifact provides an import/provenance chain between the two archives; `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | RFC 7089’s distributed multi-server model; archive API/CDX facts. |
| BA-04：Common Crawl Saturn raw WARC | One publicly range-retrieved WARC response contains payload/block digest, WARC date, target URI, `content-language`, `vary`, cookie/auth/user-agent and GeoIP context. | One target URI and one response are recorded. There is no second response to compare; `UNDEFINED_BY_EXISTING_STANDARDS` for a comparison result. | WARC-Date says capture began for this record. No second record/receipt means all relation output is `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | No inventory or scope statement in the record; absence is `UNDEFINED_BY_EXISTING_STANDARDS`。 | WARC records crawler facts, not a signed original-observer/import chain in this evidence. | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | WARC 1.1 capture event, request/response, digest and concurrent-record fields; RFC 9110 Vary. |
| BA-05：Stanford SUP legacy WACZ + real 301/CDXJ | Downloaded real package contains legacy `webarchive.yaml`, CDXJ and WARC; root record is status 301; Common Crawl record’s HTML has an HTTP canonical link for its own target. | HTTP can express a redirect response and `rel=canonical` link. Without the specific redirect Location or an equivalence policy, target equivalence is `UNDEFINED_BY_EXISTING_STANDARDS`。 | No two linked captures qualified for a temporal/repetition claim. | Package context scopes its own collection; no global coverage/absence conclusion. | Package manifest context names a collection but gives no signed archive-to-archive import chain. | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | HTTP redirect/link semantics; legacy package/CDXJ facts; WACZ portability specification. |
| BA-06：UK Government Web Archive query | Public collection page and UI are reachable; submitted timeline query stops at human verification. | No capture target result is available. | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | `UNAVAILABLE_FOR_AUTOMATED_COLLECTION`, not archive absence. | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | Actual access observation only. |
| BA-07：real request-context inputs | Common Crawl response contains `Vary: Accept-Encoding,X-Subdomain,Cookie,Authorization,User-Agent` and GeoIP/cookie headers. | RFC 9110 establishes that those request headers can affect selected representation. It does **not** emit a predicate for comparing two captured responses across archives when one/more inputs are missing. Therefore result is `UNDEFINED_BY_EXISTING_STANDARDS`。 | Only one capture, therefore no relation result. | No scope/absence result. | No original/import result. | No log proof. | RFC 9110 selected representation and Vary; raw WARC evidence. |
| BA-08：transparency and import test | No real VC/SCITT/CT archive statement, receipt, import transfer or conflicting checkpoint was present in the corpus. | No target/representation result. | No temporal/parallel/repeated result. | No history/absence result. | VC/PROV/SCITT can encode issuer/provenance/receipts in general, but real import evidence is `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | CT/SCITT define log-specific proofs; real archive checkpoint conflict is `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`。 | VC 2.0; PROV-DM; RFC 9943; RFC 9162. |

## 必答问题的 standards-only 回答

| Question | Baseline-A answer |
| --- | --- |
| 1. target 是什么？ | HTTP target resource is identified by the request target / URI; Memento adds an Original Resource URI. The collected records permit literal URI equality, not a cross-archive target identity algorithm. |
| 2. 两个 capture 是否属于同一 target？ | For byte-identical URI strings: literal equality is established. For `http`, `https`, `www`, userinfo, query, fragment, redirect or canonical variants: `UNDEFINED_BY_EXISTING_STANDARDS` absent a separately selected URI/profile policy. |
| 3. 两个 representation 是否 comparable？ | RFC 9110 supplies representation-selection inputs, including Vary, but no cross-archive `comparable` decision. For the real one-record Vary case: `UNDEFINED_BY_EXISTING_STANDARDS`. |
| 4. 两个不同 hash 是否代表 temporal change？ | No. Different digest values establish distinct reported digest values; timestamps establish archive-reported times. The temporal-cause claim is `UNDEFINED_BY_EXISTING_STANDARDS`. |
| 5. 是否可以证明 parallel observation？ | No standards-only rule derives it from two archive records/timestamps. `UNDEFINED_BY_EXISTING_STANDARDS`. |
| 6. 是否可以证明 repeated observation？ | Within an archive, equal digest plus multiple index rows is evidence of repeated records; it does not create an inter-archive repeated-observation semantic. The latter is `UNDEFINED_BY_EXISTING_STANDARDS`. |
| 7. archive absence 能否推出 absence？ | No. RFC 7089’s distributed design and optional TimeMap interval attributes do not make archive-local non-return a global absence statement. |
| 8. imported observation 的原始 agency 是谁？ | PROV/VC/SCITT can express agents/issuers when supplied, but no collected real import case provides that graph. `NOT_PROVABLE_FROM_COLLECTED_EVIDENCE`. |
| 9. 什么情况下可以称为 equivocation？ | For an actual CT/SCITT transparency service, consistency/inclusion proofs or conflicting valid proofs can be cryptographically tested. No collected archive checkpoint evidence exists. Mapping that rule to archive statements is not defined by the base standards. |

## Baseline-A conclusion

The existing standards already expose a large amount of the required **input evidence**: URI strings, captured HTTP request/response content, timestamps, digests, internal same-capture associations, replay navigation, optional TimeMap intervals, and general provenance or signed-statement structures. They do **not** directly standardize a cross-archive procedure that converts these inputs into target equivalence, representation comparability, temporal-versus-parallel classification, global-history scope, or Web-archive import relation. This conclusion identifies `UNDEFINED_BY_EXISTING_STANDARDS`; it does **not** establish that an additional normative rule is necessary, because a later standards-extension profile may lawfully supply the procedure through existing mechanisms.

## References

[1] [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html).  
[2] [RFC 7089, Memento](https://www.rfc-editor.org/rfc/rfc7089.html).  
[3] [IIPC, WARC Format 1.1](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/).  
[4] [W3C, PROV-DM](https://www.w3.org/TR/prov-dm/).  
[5] [W3C, Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/).  
[6] [RFC 9943, SCITT Architecture](https://www.rfc-editor.org/rfc/rfc9943.html).  
[7] [RFC 9162, Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html).  
[8] [Real corpus registry](real_corpus_registry.md).
