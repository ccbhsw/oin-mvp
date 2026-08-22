# IWOH v0.2 External-Substitutability / Real-World Falsification Audit — 方法锁定

**状态：** 进行中。  
**目标：** 回答：在删除 IWOH 后，现有公开 Web archive、HTTP、WARC/WACZ、Memento、PROV、VC、SCITT、CT 与相关标准的直接组合，是否足以让独立 archives 对**真实、公开、合法可访问**的 Web captures 给出一致、可验证且非误导的历史解释。

## 1. 非目标与硬约束

本审计不修改 OIN MVP，不扩展节点，不部署公网，不购买基础设施，也不制作融资或市场材料。它不将工程复杂度、公共价值、易用性、统一字段名、API、SDK、UI 或 reference implementation 视为技术创新。

Synthetic fixtures 只作为 v0.1 可实现性证据；它们不得作为本次“真实世界价值”或“不可替代性”的主要证据。每一条现实案例必须提供 archive name、source URL、capture/memento URL、capture datetime、已见 metadata、WARC/WACZ availability、公开可访问性、抓取日期和原始证据链接。无法自动或公开访问的情况必须明确标为 `UNAVAILABLE`。

## 2. 三个比较臂

| 比较臂 | 可用内容 | 禁止内容 | 目的 |
| --- | --- | --- | --- |
| Baseline-A | HTTP、WARC/WACZ、WACZ Auth、Memento、PROV、VC、C2PA、SCITT、CT、RFC 3161 及其原生语义 | IWOH vocabulary、IWOH-specific fields、私有补充规则 | 识别每个问题是现有标准已定义还是 `UNDEFINED_BY_EXISTING_STANDARDS`。 |
| Baseline-B | 同一组标准，外加其公开允许的 extension/profile mechanism | 对 IWOH 的引用、复制或改名；未在既有标准中允许的私有基础原语 | 测试有经验团队是否可用现有标准正常组合取得相同结果。 |
| IWOH v0.2 | IWOH R1–R8 规则和同一真实 corpus | 任何未由公开证据支持的事实或全局历史断言 | 测试 IWOH 是否改变、限制或澄清结论。 |

## 3. 结果字段

每一案例在三个比较臂中均尝试回答：target grouping、representation relation、comparability、temporal relation、parallel relation、repeated relation、history scope、absence semantics、imported agency、equivocation semantics。无对应定义时必须输出 `UNDEFINED_BY_EXISTING_STANDARDS`，不得临时发明字段或阈值。

## 4. 真实案例覆盖目标

审计将尝试覆盖同 URL 的重复和变化 capture、language/Vary、geography/CDN、User-Agent/Accept/Vary、redirect/canonical、query、fragment、authentication、multi-archive capture、near-time byte difference、history absence、archive-to-archive evidence import 与透明日志 checkpoint conflict。未在真实公开 corpus 找到的类型将保留为 `UNAVAILABLE`，不是缺失数据的替代性结论。

## 5. R1–R8 的严格判定

| 规则 | `FALSIFIED` 条件 | 保留为 `SEMANTIC GAP` 的最低条件 |
| --- | --- | --- |
| R1 Target Identity | 现有规范已足够规范化 URL/query/fragment/redirect/canonical 的跨 archive identity result。 | 真实 corpus 中两个合理 standards-only paths 对同一 target grouping 得出不同结果。 |
| R2 Evidence Binding | WARC/WACZ/WACZ Auth、VC、C2PA、SCITT 已无损表达 issuer、archive bytes、WARC record、payload digest 与 signature 的完整绑定。 | 真实 evidence exchange 无法验证其中一个必要 binding。 |
| R3 Comparability | 现有规范直接给出 Vary、auth、vantage、policy、completeness 的统一 cross-archive compare predicate。 | 两个 standards-only paths 对真实 captures 的 comparability 得到不同且均可辩护的结论。 |
| R4 Temporal / Parallel | 现有规范直接把 capture time、timestamp/receipt、causality 映射为 before/after/overlap/unknown。 | 真实 captures 存在仅凭 timestamps 无法安全排序而 IWOH 的 evidentiary boundary 改变结论。 |
| R5 Relationship Vocabulary | 所有分类只是已有概念的同义改名，且不改变任何真实误判。 | 可展示的真实 archive workflow 会把 representation variation、temporal variation 或 parallel observation 误归为另一种关系。 |
| R6 History Scope / Absence | Memento/archive API/SCITT 已定义 scope、coverage、complete/partial 和 absence uncertainty 的同一交互语义。 | 真实查询中 local absence 被误读为 wider absence，且标准本身未限制该推断。 |
| R7 Imported Agency | PROV/VC/C2PA/SCITT 已完整且规范地保留 original issuer、observation、importer 与 evidence。 | 真实 archive-to-archive transfer 使 original agency 无法明确复核。 |
| R8 Equivocation | CT/SCITT 已完全定义同 log/same tree size/different valid roots 的 result。 | 不适用；若只映射至 Web archive，至多是 `PROFILE MAPPING ONLY`。 |

## 6. 四选一最终分类

**FALSIFIED**：现有标准或公开项目已经以原生或正常 extension/profile 的方式解决 IWOH 的核心问题，或 Baseline-B 对真实 corpus 可以得到 IWOH 的同等规范化结果。

**PROFILE-LEVEL CONTRIBUTION**：IWOH 对真实案例产生实际互操作约束或错误预防，但可完全由既有标准承载，未创造不可表达的核心语义。

**STRONG CANDIDATE**：至少一个核心语义无法由既有标准表达，且其缺失导致真实 corpus 中的明确、可验证、跨实现互操作结果无法产生。

**NO EVIDENCE**：真实、公开、合法的 corpus 不足以区分上述结果。不能以 synthetic fixtures、不可访问 archive 或推测替代实际证据。

## 7. 停止规则

发现 Baseline-B 在同一真实 cases 以现有 standards/profile mechanism 输出 IWOH 等价结论时，必须立即强化 `FALSIFIED` 方向，不得以“实现更方便”保留贡献。发现 corpus 对关键 R3/R4/R6 缺少公开可验证 evidence 时，必须对这些规则报告 `NO EVIDENCE` 或 `UNAVAILABLE`，不得把空白当 semantic gap。
