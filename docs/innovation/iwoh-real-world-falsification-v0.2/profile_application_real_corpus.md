# IWOH v0.1 在真实公开 corpus 上的应用结果

**输入版本：** 已锁定的 `Independent Web Observation History Profile v0.1`。  
**重要限制：** 本文不创作、回填或自签任何 archive capture statement。这样做会把审计者变成虚假的 original capture agent，并破坏本实验的 agency 与 evidence-boundary 要求。

## 输入门槛

IWOH v0.1 规定完整 Capture Statement 必须包含 `profile_version: "IWOH-0.1"`、VC-style issuer、`eddsa-jcs-2022` DataIntegrityProof、capture activity、request context、response digest、evidence locator and digest、time evidence 与 context-completeness declaration。对不含 `profile_version` 的 WARC、WACZ、C2PA manifest、VC、PROV graph、SCITT statement 或 TimeMap，规范允许保存和展示，但禁止将其声称为完整 profile interoperability result。[1]

真实 corpus 的 archive artifacts 是有价值的原始证据，不是 IWOH statements。将 Internet Archive、Arquivo.pt、Common Crawl 或 Stanford WACZ 的 metadata 转写为新 signed statements，只能证明审计者在 2026 年做出的描述，不能证明历史 capture agent 在其 capture activity 中做出的声明。因此所有 case 先经过以下 input gate。

| Evidence record | `profile_version` | capture-agent DataIntegrityProof | required request context + completeness declaration | required evidence bindings | Input-gate result |
| --- | --- | --- | --- | --- | --- |
| IA-EXAMPLE-2010 | absent | absent | absent | replay/API metadata only | `NON_PROFILE_INPUT` |
| IA-EXAMPLE-2024 | absent | absent | absent | replay/API metadata only | `NON_PROFILE_INPUT` |
| IA-CDX-EXAMPLE-URL-VARIANTS | absent | absent | absent | CDX fields only | `NON_PROFILE_INPUT` |
| ARQUIVO-EXAMPLE-20100323 | absent | absent | absent | CDX digest/ARC location only | `NON_PROFILE_INPUT` |
| IA-EXAMPLE-20100323 | absent | absent | absent | Availability metadata only | `NON_PROFILE_INPUT` |
| CC-SATURN-20260714 | absent | absent | raw WARC has selected response inputs but no required statement disclosure/completeness | WARC record/payload digest available; no statement-level artifact binding | `NON_PROFILE_INPUT` |
| SUP-ETD-20170706 | absent | absent | legacy manifest/capture context only | legacy WACZ/CDXJ/WARC package, no profile statement | `NON_PROFILE_INPUT` |
| UKWA query attempt | absent | absent | absent | no capture artifact obtained | `NON_PROFILE_INPUT` |

## Profile result

For all collected real records, `statement_validity`, `Comparable(A,B)`, relationship classification, History View membership/completeness, import validity and equivocation status are **not produced**. The reason is not `INVALID_SIGNATURE`: a raw archive record did not purport to be an IWOH Capture Statement. The correct output is `NON_PROFILE_INPUT`, followed by no profile result.

| Requested profile output | Result on real corpus | Why no result is permitted |
| --- | --- | --- |
| Target identity / relation | no IWOH result | A raw URI can be displayed, but no profile Statement exists to feed Section 4/5 verification. |
| Statement validity | no IWOH result | There is no statement to which the Section 6 verification sequence can be applied. |
| Comparability | no IWOH result | Section 7 requires two `VALID` Statements and complete recorded context. |
| Relationship | no IWOH result | Section 8 requires valid statements; temporal and parallel claims further require admissible time evidence. |
| History membership / completeness | no IWOH result | No signed History View with declared scope/commitment exists in the corpus. |
| Import validity | no IWOH result | No transferred Capture Statement/evidence bundle exists. |
| Equivocation status | no IWOH result | No IWOH History View or named log receipt/checkpoint pair exists. |

## What the real corpus does and does not test

The real corpus tests whether the pre-profile world exposes the inputs that a profile would need. It does: URI variants, Memento/replay times, WARC digests, a raw `Vary` header, geo/auth/cookie/user-agent context, package layout diversity, and two archive endpoints reporting an equal datetime. It does not test actual third-party production, exchange, verification or adoption of profile statements.

Consequently, the corpus can be used to assess the **need for a mapping policy** and the substitutability of that policy by a standards-only extension profile. It cannot demonstrate that IWOH itself improves interoperability in deployed practice. Any conclusion claiming deployed real-world profile value would be unsupported.

## Non-adjudication

No page content is classified as true, false, correct, incorrect, a winner, or consensus. No archive is judged dishonest, incomplete, independent, or non-independent. No local query non-return is treated as historical absence.

## Reference

[1] [Independent Web Observation History Profile v0.1, Sections 3, 5–11](../../novelty-audit/iwoh-profile-v0.1/profile/Independent_Web_Observation_History_Profile_v0.1.md).
