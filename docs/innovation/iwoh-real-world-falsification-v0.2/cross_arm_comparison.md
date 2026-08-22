# 真实 corpus：Baseline-A、Baseline-B 与 IWOH v0.1 逐字段比较

本比较不把“有输出”当作优势。三个比较臂只有在面对**同一、合格输入**时才能证明互操作差异。IWOH v0.1 对本 corpus 的所有 artifacts 返回 `NON_PROFILE_INPUT`，所以本表同时记录已有 standards-only output 与 profile-input failure。

## 主要 cases

| Case | Field | Baseline-A（无扩展 mapping） | Baseline-B（existing-standard mapping） | IWOH v0.1 | 可归因的差异 |
| --- | --- | --- | --- | --- | --- |
| IA `example.com` 2010 vs 2024 | target grouping | literal URI equality only | exact URI key | `NON_PROFILE_INPUT` | B1 creates an explicit exact-key rule; the real artifacts do not test IWOH’s result. |
| same | representation relation | visibly different replay bodies; no safe historical class | `different-records-not-assessed` | `NON_PROFILE_INPUT` | B5’s safe output vocabulary changes display, not raw evidence. |
| same | temporal relation | archive-reported datetime order only | `chronological-archive-records`; no source-change inference | `NON_PROFILE_INPUT` | B4 blocks unsupported causal inference. |
| Arquivo same-digest 2010 rows | target grouping | literal URI equality only | exact URI key | `NON_PROFILE_INPUT` | B1. |
| same | repeated relation | same reported digest across multiple rows; classification undefined | `same-evidence` at index-digest level | `NON_PROFILE_INPUT` | B2/B5 choose a conservative label. |
| IA / Arquivo same target + same datetime | target grouping | literal URI equality | exact URI key | `NON_PROFILE_INPUT` | B1. |
| same | temporal / parallel | equal reported datetime; capture-event relation undefined | `different-records-not-assessed` | `NON_PROFILE_INPUT` | B4/B5 enforce non-inference. |
| Common Crawl Saturn WARC | comparability | response-selection inputs recorded; no pairwise predicate | `not-assessed`; records Vary/auth/vantage inputs | `NON_PROFILE_INPUT` | B3 chooses missing-context behavior. |
| Stanford legacy WACZ | redirect/canonical | 301/canonical evidence can be displayed; no cross-archive identity conclusion | typed link retained; no key merge | `NON_PROFILE_INPUT` | B1/B5 prevent silent merge. |
| UKWA human verification | scope / absence | unavailable automated query | no `no-result-in-declared-scope`; no absence claim | `NON_PROFILE_INPUT` | B6 prevents an invalid absence inference. |
| import and checkpoint conflict types | agency/equivocation | not provable from collected evidence | not assessed | `NON_PROFILE_INPUT` | No real input can test B7/B8 or profile R7/R8. |

## Field-level outcome summary

| Required comparison dimension | Baseline-A | Baseline-B | IWOH v0.1 on current corpus | Evidence-supported finding |
| --- | --- | --- | --- | --- |
| target grouping | literal strings / undefined variants | deterministic exact-key policy | no profile result | A profile policy is needed for deterministic grouping, but the corpus does not show deployed IWOH interoperability. |
| representation relation | raw HTTP/WARC/Memento facts only | limited safe labels | no profile result | Existing standards plus a mapping can avoid false relation claims. |
| comparability | input fields exist; predicate undefined | explicit complete-context precondition | no profile result | R3-style comparison semantics have realistic inputs but no actual two-statement test. |
| temporal / parallel | reported time only | receipt precedence and non-inference | no profile result | Existing timestamp fields alone do not entail causality; no real qualified receipt pair tests the stronger rule. |
| repeated relation | same digest can be reported | digest-level same-evidence label | no profile result | Existing metadata can record repetition candidates; semantics remain policy-selected. |
| history scope / absence | archive-local return only | declared-scope non-absence policy | no profile result | No real signed scope commitment; not field-testable. |
| imported agency | generic PROV/VC capability; no actual transfer | preservation mapping | no profile result | Not field-testable. |
| equivocation | CT/SCITT base semantics; no real archive checkpoint pair | direct log-conflict mapping | no profile result | R8 cannot provide independent contribution on this corpus. |

## Result discipline

Baseline-B demonstrates **substitutability at the construction level**: a standards-only system can use WARC/WACZ/Memento/HTTP plus PROV/VC/SCITT/CT extension mechanisms to produce safe, deterministic outputs. It pays for that result by writing B1–B7 mapping rules. The profile application demonstrates **no deployed input evidence**: none of the actual public archive artifacts conformed to the required signed-statement and History View inputs.

Therefore this comparison establishes neither that a profile implementation is unnecessary nor that it has real-world indispensability. It establishes that a standard-stack mapping can implement the same class of safeguards, while the present real corpus cannot test the profile’s claimed cross-implementation effect.

## Source documents

[1] [Real corpus registry](real_corpus_registry.md).  
[2] [Baseline-A](baseline_a.md).  
[3] [Baseline-B](baseline_b.md).  
[4] [IWOH v0.1 application on real corpus](profile_application_real_corpus.md).
