# 两条独立 standards-only 路径审计

## 实验纪律

路径 A 是 Python literal HTTP/Memento/WARC reader；路径 B 是 Node.js provenance-first reader。二者不导入 OIN MVP、IWOH implementation、彼此源代码或同一 schema，仅读取 `real_corpus_registry.json`。它们各自输出 7 个真实 cases 的 target、representation、time、relation、scope、agency 与 equivocation result。源文件哈希和结果均保存在 [`independent_results/`](independent_results/)。

## 结果

| 指标 | 数值 | 含义 |
| --- | ---: | --- |
| 真实 cases | 7 | 基于已访问的 Internet Archive、Arquivo.pt、Common Crawl、Stanford WACZ 和 UKWA access result。 |
| 原始 JSON result 完全相同 | 0 / 7 | 现有 standards-only paths 没有自然产生相同 serialized history interpretation。 |
| 事实级保守结论兼容 | 7 / 7 | 两条路径都拒绝无证据的 source causality、global absence、transfer agency 和 log-equivocation claim。 |
| 已证实的互操作失败 | 0 / 7 | 不存在两条路径对同一真实 evidence 作出相互矛盾、会误导用户的历史断言。 |
| 已测试的 IWOH 强制一致性 | 0 / 7 | 真实 artifacts 都不是 profile-compliant Capture Statements，不能运行 profile comparator。 |

## 分歧调查

| Case family | A 的表达 | B 的表达 | 是否实现错误 | 标准是否允许两种表达 | IWOH 是否已在真实输入上强制一致 | 实际互操作影响 |
| --- | --- | --- | --- | --- | --- | --- |
| 同 URI、不同 replay | literal URI + different body + ordered archive time | one Original Resource candidate + two Memento responses | 否。 | 是。HTTP uses resource/representation；Memento uses Original Resource/Memento。 | 未测试。没有 profile statements。 | 命名和建模粒度不同，但两者都不声称 source causality。 |
| 同 digest、多 CDX rows | same reported digest, no causal label | potential duplicate evidence artifact, no activity provenance | 否。 | 是。WARC defines digest; PROV allows entity/activity modeling without defining derivation conditions。 | 未测试。 | 不会导致相反历史主张；仍需 mapping 选择稳定标签。 |
| 两 archive、同 URI/同 timestamp | no common-event inference | no PROV communication/derivation asserted | 否。 | 是。Memento permits multiple servers; PROV only models relation when asserted。 | 未测试。 | 两者均安全地拒绝把同 timestamp 当共享 observation。 |
| WARC Vary/context | one response, no pair to classify | one contextualized response entity, no second entity | 否。 | 是。HTTP supplies selection inputs but no cross-archive predicate。 | 未测试。 | 两者均拒绝比较；不存在被证明的 user-visible conflict。 |
| redirect/canonical | literal targets stay distinct | typed evidence, no PROV equivalence assertion | 否。 | 是。HTTP links and PROV relation are different layers。 | 未测试。 | 术语不一致，未产生错误 target merge。 |
| query blocked / missing cases | unavailable access, no absence | access challenge, no assertion | 否。 | 是。 | 未测试。 | 一致地避免 absence claim。 |
| import/checkpoint absent | no evidence | no transfer/receipt | 否。 | 是。 | 未测试。 | 未形成可比较的 real case。 |

## 结论

这不是 “两实现无 IWOH 已自然得到相同结果” 的证据。相反，**0/7 的 raw output agreement** 显示标准术语及数据模型本身不选择同一 serialized interpretation。可是，这也不是 IWOH 已证明不可替代的证据。两条路径的差别没有造成相互矛盾的历史结论；它们在每一条真实 evidence 上都收敛到保守、不误导的事实级结论。

更关键的是，使用既有标准可构造 Baseline-B 的 B1–B7 mapping 以统一这些 outputs。该 mapping 使用 WARC/WACZ、HTTP、Memento、PROV、VC 与 SCITT/CT 的既有 extension points，未需要新的 cryptography、archive format、transparency primitive 或 transport。它说明 raw divergence 本身只证明 **interoperability mapping is required**，不证明一个具体新 profile 不可替代。

IWOH 的最强可检验主张应是：给定两个真实 capture agents 实际发布的 signed Capture Statements 与 signed scoped History Views，独立 verifiers 会在 target relation、comparability、relationship、scope、import and equivocation fields 上收敛，而 standards-only alternatives 不能以既有 profile mechanism 达到同样的 result。当前 corpus 不含该种输入。因此本阶段对“profile 强制一致且有现实价值”的结果为 **NO EVIDENCE**。

## Evidence files

[1] [Path A source](independent_path_a/standards_literalist.py).  
[2] [Path B source](independent_path_b/provenance_first.mjs).  
[3] [Path A result](independent_results/path_a.json).  
[4] [Path B result](independent_results/path_b.json).  
[5] [Comparison result](independent_results/comparison.json).  
[6] [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html).  
[7] [RFC 7089](https://www.rfc-editor.org/rfc/rfc7089.html).  
[8] [W3C PROV-DM](https://www.w3.org/TR/prov-dm/).
