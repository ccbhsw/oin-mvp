# Existing-Standards Baseline-B

**规则：** 本比较臂可以使用既有标准明确允许的 extension/profile mechanism，但只采用本文显式定义的独立 mapping rules。目标是测试一个有经验团队能否仅以公开标准构建一个安全、可互操作的真实 Web archive history explorer，并明确记录其不得不写出的附加 mapping rules。

## 可用的标准承载层

| 需要承载的事实 | 已有标准承载路径 | 能直接保证的内容 | 不能直接保证的内容 |
| --- | --- | --- | --- |
| capture bytes / HTTP exchange | WARC response/request、WARC payload/block digest、WACZ package resources | Target URI、capture date、HTTP messages、internal request-response link、fixity input。 | Cross-archive identity or relation. |
| archive temporal navigation | Memento Original Resource, Memento, TimeMap, Memento-Datetime | Archive-local access to frozen prior state and navigation. | Global history completeness or multi-archive relation judgement. |
| signed archive assertion | VC 2.0 secured credential, custom domain vocabulary / schema | Cryptographically secured claims about a subject, issuer and evidence. | Truth of claim or standard Web-capture claim semantics. |
| original / importing agency | PROV Entity, Activity, Agent, association, attribution, delegation; VC issuer | A provenance graph with attributed roles. | Which role becomes “original observation” without profile rule. |
| transparent registration | SCITT signed statements and receipts; CT-style transparency artifact | Statement inclusion and log-specific consistency/inclusion proof. | Meaning of a Web capture statement, discovery or statement-storage semantics. |

WARC 1.1 permits extension fields/record types and directs processors to ignore unknown names. WACZ permits additional top-level files/directories if listed in its `datapackage.json` resources. PROV-DM and VC 2.0 are domain-agnostic/extensible models. These are legitimate routes for a profile; they do not themselves provide a cross-archive interpretation algorithm.[1] [2] [3] [4]

## Adversarial standards-extension mapping

The following **Archive Evidence Exchange Mapping (AEEM)** is intentionally presented as a separate, standards-only construction. It uses only existing containers and extension points. A record consists of: a VC-secured assertion whose subject is a WARC/WACZ/Memento evidence reference; a PROV bundle identifying archive agents and activities; optional SCITT/CT-compatible receipt references; and a WACZ/WARC artifact reference. No new cryptographic primitive, archive file format, log type, or transport is needed.

| Mapping rule | Minimal, conservative rule | Existing carrier | Is the rule already imposed by a base standard? |
| --- | --- | --- | --- |
| B1 URI and relation key | Treat exact original URI strings as the same key. Keep different URI strings distinct unless a verifiable, typed relation from the evidence specifically justifies a relation; redirect/canonical hints are stored, not silently collapsed. | Memento `original` link, WARC-Target-URI, HTTP Link/redirect evidence, VC claim. | **No.** This is a profile selection policy. |
| B2 artifact binding | A claim must reference an immutable package digest or WARC record id plus payload/block digest where present; a signature covers the claim/evidence references. | WARC digests/record IDs, WACZ resource hash, VC security mechanism, SCITT receipt. | **Partly.** Fixity and signatures are standard; minimum cross-layer binding set is a profile rule. |
| B3 comparison precondition | Before comparing response payloads, require identical media-type/selection-relevant context or explicitly record that any `Vary` dimensions, request headers, auth state, locale/geography/vantage or capture policy are unknown. Missing input yields `not-assessed`, never equivalence. | HTTP `Vary`, WARC request/response, VC evidence claim. | **No.** RFC 9110 identifies selection inputs; it does not define this cross-capture predicate. |
| B4 temporal evidence precedence | Use a verified third-party receipt/transparent-log order when supplied. Otherwise state only archive-reported WARC/Memento datetime order; do not infer source mutation, causation or simultaneity from digest plus two timestamps. | RFC 3161 when available, SCITT/CT receipt, WARC-Date, Memento-Datetime. | **No.** Individual time fields are standard; the precedence and inference limit are profile rules. |
| B5 safe relationship result | Output only literal/evidence facts and four conservative verdicts: `same-evidence`, `chronological-archive-records`, `different-records-not-assessed`, or `not-assessed`. | VC/PROV statements and any JSON/RDF syntax. | **No.** The vocabulary and decision algorithm are profile rules. |
| B6 scope and absence | A query result carries the responder/archive/collection/query parameters and any advertised TimeMap interval. It may say `no-result-in-declared-scope`; it cannot say global absence unless a signed, authoritative coverage statement supplies that scope. | Memento TimeMap `from`/`until`, WACZ collection context, VC/SCITT assertion. | **No.** Memento interval is optional and does not define this non-inference rule. |
| B7 imported provenance | An importer creates a new PROV activity using the original evidence entity; it retains original issuer/agent identifiers and any verifiable signature/receipt. The importer must not rewrite the original agent as issuer. | PROV derivation/association/attribution/delegation, VC issuer/evidence. | **No.** Models can encode it; preservation obligation is a profile rule. |
| B8 log conflict | A checkpoint conflict is asserted only when two valid signed tree heads/receipts for the same log identity and same tree size or otherwise incompatible consistency proof fail verification. | CT/SCITT receipt and consistency proof. | **Yes for a given CT/SCITT log.** Mapping this to archive evidence is a profile rule. |

## Applied result on the real corpus

| Case | AEEM output without external profile vocabulary | Why the result is safe | New semantic work still required |
| --- | --- | --- | --- |
| Internet Archive `example.com` 2010 / 2024 | `chronological-archive-records`; `different-records-not-assessed` for source change. | Exact original URI and chronological reported datetimes are documented; visible replay content differs. | B1, B3, B4 and B5. |
| Arquivo repeated same-digest 2010 rows | `same-evidence` only at the reported digest level; separate archive records remain visible. | Equality of index digest is preserved without falsely assigning cause. | B2, B4 and B5. |
| Arquivo / Internet Archive same URL + datetime | `different-records-not-assessed`. | Equal archive-reported time does not prove one event or shared bytes. | B1, B2, B4 and B5. |
| Common Crawl Saturn WARC | `not-assessed` for any pairwise representation comparison; record all `Vary`, language, cookie/auth/user-agent and GeoIP inputs. | No second record with matching complete context exists. | B2 and B3. |
| Stanford legacy package 301 / canonical input | Store the 301 and canonical evidence as typed facts; do not merge target keys. | Package layout and linkage form do not decide cross-archive equivalence. | B1 and B5. |
| UK Government Web Archive human-verification case | `no-result-in-declared-scope` is **not** emitted because no declared archive scope was obtained; retain `unavailable-for-automated-collection`. | CAPTCHA is an access condition, not an absence statement. | B6. |
| import / checkpoint-conflict categories | `not-assessed`. | The corpus provides neither an actual provenance transfer nor real log checkpoint pair. | B7 and B8 cannot be field-tested on this corpus. |

## Substitutability finding of Baseline-B

A competent team can build a safe history explorer with the existing standard stack. All persistence, transport, digital-signature, append-only-log, time-navigation, provenance and Web-capture mechanisms already exist. The stack can avoid misleading results by refusing to classify insufficiently contextualized evidence and by emitting limited factual results.

However, equivalence to a rich cross-archive history interpreter is not obtained merely by serializing WARC, Memento, PROV, VC and SCITT objects. The team must choose B1–B7 as normative mapping rules. Those choices are not cryptographic, storage or log inventions; they are interoperable semantic constraints. B8 is a direct mapping of existing CT/SCITT log logic and is not an independent semantic contribution.

Thus Baseline-B demonstrates two facts at once. First, a new implementation can deliver the same implementation and data-model capabilities without new primitives. Second, the interoperability behavior is still conditional on a profile-sized set of rules. The base standards alone do not select those rules, and the real corpus contains concrete inputs (URL variants, equal reported timestamps across archives, unpaired `Vary` context, legacy package layout and unavailable query scope) for which an implementation must choose a policy or decline a conclusion.

## References

[1] [IIPC, WARC Format 1.1](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/).  
[2] [Webrecorder, WACZ 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/).  
[3] [W3C, PROV-DM](https://www.w3.org/TR/prov-dm/).  
[4] [W3C, Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/).  
[5] [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html).  
[6] [RFC 7089, Memento](https://www.rfc-editor.org/rfc/rfc7089.html).  
[7] [RFC 9943, SCITT Architecture](https://www.rfc-editor.org/rfc/rfc9943.html).  
[8] [RFC 9162, Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html).  
[9] [Real corpus registry](real_corpus_registry.md).
