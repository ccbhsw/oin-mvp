# OIN Independent Web Observation History Profile v0.1 候选创新验证报告

**作者：** OIN Project  
**日期：** 2026-08-21  
**审计对象：** `Independent Web Observation History Profile v0.1`（IWOH）  
**唯一判定问题：** IWOH 是否构成 OIN 不可替代的技术贡献？

## 结论

> **PROFILE-LEVEL CONTRIBUTION**

IWOH v0.1 **不是**新的底层协议原语，也不是 OIN 的不可替代核心技术。它没有创造新的存储、内容寻址、哈希、签名、WARC/WACZ package、Memento、透明日志、Merkle proof、共识、复制或 Web provenance 基础能力。WACZ 已定义可复制、可校验的 Web archive package；Memento 已定义时间化网页版本与 TimeMap；VC/PROV 已提供可验证 statement 和 agent/activity/entity 表达；SCITT/CT 已提供 signed statement registration、receipt、checkpoint、consistency 与 non-equivocation mechanism。[1] [2] [3] [4] [5] [6]

IWOH 的可保留技术贡献是一个**最小、可实现、可 conformance-test 的跨标准解释 profile**。它规定当多个 archive/observer 对 Web capture 提供证据时，verifier 必须如何：保持 request-target identity；显式处理 redirect/canonical relation；用 HTTP representation-selection context 判断可比性；区分 repeated、temporal、parallel 和 representation variation；限制 local clock 的证据能力；表达 history scope/absence；保留 imported agency；以及只在可验证的 checkpoint 矛盾时报告 equivocation。现有基础标准分别提供承载这些信息的机制，但在已核验的规范中，没有一个强制定义该完整的 Web-observation 结果 contract。[1] [2] [3] [4] [5] [6]

因此，对“是否是真正**不可替代**的技术贡献”的严格回答是：**否，IWOH 不是不可替代的基础技术；它是可被其它标准化或实现团队重建的 profile-level contribution。** 对三选一分类题的严格回答是：**PROFILE-LEVEL CONTRIBUTION**，而不是 `STRONG CANDIDATE`，也不是目前证据下的 `FALSIFIED`。

## 1. 验证方法与证据范围

本审计没有修改 OIN MVP，没有部署公网，没有增加节点，也没有使用 OIN code、schema 或 tests。验证工作区建立了一个离线 corpus，使用合成 `example.test` / `example.net` URL、WACZ 1.1.1 artifacts、W3C `eddsa-jcs-2022` signed Capture Statements、causal receipts 与 signed History Views。WACZ 的 `datapackage.json` resources 和 `datapackage-digest.json` 负责 archive package fixity；W3C EdDSA Data Integrity 负责 statement proof。[1] [3]

两个 verifier 只共享 Profile、静态 corpus、公开规范和 expected results，未共享 source module 或运行时。实现 A 使用 Python `cryptography` 与 `zipfile`；实现 B 使用 Node.js 原生 `crypto`、独立 JCS serializer 和系统 `unzip`。每个实现均独立验证 Ed25519 proof、issuer binding、WACZ resource fixity、WARC payload digest、causal receipt、History View、target relation、comparability、relationship、scope/import/equivocation result。

| 核验项 | 结果 | 证据 |
| --- | --- | --- |
| Fixture corpus 确定性 | 通过 | 27 WACZ、27 statements、4 receipts、4 History Views、17 scenarios 在重复生成后 file digest 相同。 |
| WACZ ZIP container 检查 | 通过 | 所有 27 个 `.wacz` files 通过 ZIP 完整性检查；故意被篡改的 case 保留为 manifest/fixity 负例。 |
| Implementation A 对预期断言 | 通过 | 17/17 scenarios；0 deviations。 |
| Implementation B 对预期断言 | 通过 | 17/17 scenarios；0 deviations。 |
| A 与 B 逐字段交叉比较 | 通过 | 9 类 assertions、17 scenarios；0 deviations。 |
| 实现隔离扫描 | 通过 | 两套 source 未引用 OIN MVP、对方实现或 fixture generator。 |
| 重复运行确定性 | 通过 | A 与 B 各自重复运行产生 byte-identical JSON output。 |

机器可读证据位于 [`fixtures/`](fixtures/)、[`results/implementation_a.json`](results/implementation_a.json)、[`results/implementation_b.json`](results/implementation_b.json) 和 [`results/cross_comparison.json`](results/cross_comparison.json)。完整 contract 位于 [`fixtures_contract.md`](fixtures_contract.md)，coverage matrix 位于 [`fixtures_coverage_matrix.md`](fixtures_coverage_matrix.md)。

> 这是一项受控的互操作与语义歧义测试，不是第三方独立复现。A 和 B 的代码路径独立，但两者由同一审计过程产生；因此结果证明 **implementability** 与 **testability**，不单独证明新颖性或外部可部署性。

## 2. Falsification Matrix

| 候选命题 | 直接 prior art / 标准 | 判定 | 原因 |
| --- | --- | --- | --- |
| 便携、可复制、可校验的 Web capture evidence container 是新协议 | WARC/WACZ、WACZ Auth | **FALSIFIED** | WACZ 已定义 WARC + manifest + fixity 的可分发 Web archive package；WACZ Auth 已处理 creator/time authentication。[1] [7] |
| signed observation / archive creator identity 是新协议 | VC Data Integrity、PROV、WACZ Auth、C2PA | **FALSIFIED** | 现有标准已经表达 signed claims、issuer/agent/provenance 与 signed archive package。[4] [5] [7] [8] |
| time-indexed Web history 是新协议 | Memento | **FALSIFIED** | RFC 7089 已定义 URI-R、URI-M、TimeMap、datetime negotiation 和多服务器历史可见性。[2] |
| multi-issuer statement registration、receipt、non-equivocation 是新协议 | SCITT、CT | **FALSIFIED** | SCITT/CT 已分别提供 signed statement、receipt、checkpoint、auditing 和 non-equivocation mechanism。[6] [9] |
| decentralized archive / version tracking 是新协议 | IPARO、ARCHANGEL、Archive Assisted Fixity | **FALSIFIED** | 已有研究覆盖 decentralized version tracking、DLT-backed archive integrity 和多 archive fixity dissemination。[10] [11] [12] |
| HTTP selection context 下的 capture comparability 具有统一强制语义 | RFC 9110 提供 `Vary` / representation semantics，但无此跨 archive predicate | **PROFILE-LEVEL CONTRIBUTION** | IWOH 明确要求 auth、vantage、request policy、Vary dimensions 和 context completeness 共同参与可比性。 |
| changed bytes 的 temporal / parallel / unknown 分类具有统一强制语义 | Memento/SCITT/CT 提供时间化与 receipts，但不提供 Web observation classification | **PROFILE-LEVEL CONTRIBUTION** | IWOH 禁止将 hash + local clock 当时序事实，并将 causal/interval evidence 映射到互斥关系。 |
| history absence、scope、imported agency 与 cross-archive equivocation 的共同规则已完全标准化 | Memento、SCITT、VC/PROV 各有部分能力 | **PROFILE-LEVEL CONTRIBUTION** | IWOH 规定 `COMPLETE_FOR_DECLARED_SCOPE`、`HISTORY_ABSENCE_UNPROVEN`、`IMPORTED_VALID` 与 checkpoint conflict boundary。 |
| IWOH 是新的不可替代基础 protocol | 全部上述标准和研究 | **FALSIFIED** | R1–R8 均可表达为既有标准上的 application/profile mapping；没有新的 cryptographic or transport primitive。 |
| IWOH 是强核心协议创新 | 目前实现和证据 | **FALSIFIED** | 两实现证明 profile 可测试，不证明现有 standards 无法通过 extension/profile 达到相同语义。 |

## 3. 最小可保留规则

IWOH 只能以以下八条规则作为最小 profile contribution。删除任一规则都会使 corpus 至少一个 case 无法取得唯一且安全的九类 assertion result；但每条都应被表述为**互操作约束**，而非新底层技术。

| 规则 | 必须写入 Profile 的最小语义 | 所解决的误判 |
| --- | --- | --- |
| R1 | fragment removal、query preservation、explicit target relation，不得静默 canonical merge。 | 将 fragment/query/redirect/canonical 误作同一 object。 |
| R2 | statement 同时绑定 issuer key、WACZ bytes、WARC record 与 payload digest。 | 只验证 archive hash 或只验证 payload hash；签名 key 与 agent 脱钩。 |
| R3 | Vary/auth/vantage/capture policy/context completeness 的合取 comparability predicate。 | 把 language、authenticated 或 geo representation 当 conflict/change。 |
| R4 | 只有 verifiable interval/receipt/causal predecessor 才可导出 temporal 或 parallel；local declaration 只能导出 `UNKNOWN`。 | 用本地时钟和不同 hash 伪造时间顺序。 |
| R5 | `SAME_STATEMENT`、`REPEATED_OBSERVATION`、`TEMPORAL_VARIATION`、`PARALLEL_OBSERVATION`、`REPRESENTATION_VARIATION`、`INCOMPARABLE`、`UNKNOWN` 的互斥定义。 | 把所有不同 bytes 简化成 conflict。 |
| R6 | `History View` 必须声明 scope、coverage、completeness；absence 仅在 complete declared scope 中可报告。 | 将某 archive 未返回结果误称全网不存在。 |
| R7 | imported valid statement 保留原 issuer、evidence 与 capture agency，不得重写为接收 archive capture。 | 复制时丢失或伪造原始 observation agency。 |
| R8 | 只有同一 named log、同一 tree size、不同 valid root/checkpoint 才是 detected equivocation；否则是 not detectable。 | 将“未检测到”伪装成“没有 equivocation”。 |

## 4. 为什么不是 FALSIFIED

`FALSIFIED` 的门槛是：现有标准的原生、强制语义已经不依赖新 mapping 地覆盖所有 R1–R8 result。当前 prior-art 审计没有发现该端到端 contract。WACZ 标准化 archive package 而非 cross-archive comparison；Memento 标准化 time-based access 和 server-known mementos 而非 WARC evidence/proof/comparability；SCITT 标准化 transparent signed statement registration 而明确将 statement storage、discovery 与 notification 放在 application scope；VC/PROV 表达 claims/provenance 而不规定 Web HTTP selection comparison。[1] [2] [4] [5] [6]

因而，现有技术的直接组合**能重建 IWOH 的能力**，但需要明确写出 R1–R8 才能在相同输入上得出一致安全结论。这正是 profile-level contribution 的含义：组合并不自动产生互操作语义。

## 5. 为什么不是 STRONG CANDIDATE

`STRONG CANDIDATE` 要求发现一个现有标准无法表达的核心协议语义。IWOH 没有满足该条件。其 envelope 可使用 VC Data Integrity，evidence 可以使用 WARC/WACZ/C2PA，temporal registration/commitment 可以使用 SCITT/CT/RFC 3161，historical discovery 可以使用 Memento/HTTP Link，agent/activity/entity 可以使用 PROV。R1–R8 是这些能力的 profile composition、约束和 result vocabulary，而非无法表达的新 primitive。[1] [2] [4] [5] [6]

因此，任何将 OIN 描述为“新的 Web history layer protocol”“新的 decentralized truth protocol”“新的 immutable observation network”或“不可替代基础设施”的陈述都不被当前证据支持，必须删除。有效的技术表述只能是：

> **OIN 的候选贡献是 IWOH：一个基于现有 archive、provenance、HTTP 和 transparency standards 的、可互操作测试的多观察者 Web capture history profile。**

## 6. 最终可证伪条件

以下任一项出现后，结论必须立即改为 `FALSIFIED`：

1. 找到已发布且已实施的标准或开源协议，使用等价 mandatory fields 和 conformance rules，完整地产生 R1–R8 的结果 contract。
2. 一个与本任务无关的独立团队证明无需 IWOH-specific mapping，直接采用现有 standards 的原生 mandatory semantics 即可在此 corpus 上输出同样九类结果。
3. IWOH 的所有 fields、rules 和 outputs 可无损投影到一个已存在且已经规范化的 profile，而不新增或收紧任何 conformance requirement。
4. 第三方实现显示 R1–R8 中任何一条不影响 corpus 或现实 Web capture 误分类，证明其只是冗余命名而非必要互操作规则。

要从 `PROFILE-LEVEL CONTRIBUTION` 升级到任何更强的结论，必须有不受本审计控制的第三方实现、公开 conformance suite、真实 archive corpus、外部 review 和明确的 standards-gap analysis；即使做到这些，也不能把 profile composition 改写成底层原语创新。

## 7. 建议：如何处置 OIN

应当保留 IWOH 草案和 fixture corpus，停止所有“新底层网络/存储/透明日志/共识”的创新叙事。后续工作若继续，仅应围绕 profile 标准化质量：扩大真实 archive corpus、邀请第三方实现、将 R1–R8 与 WACZ/Memento/VC/SCITT registry/extension 明确映射，并准备在发现等价 prior art 时立即将项目结论降为 `FALSIFIED`。

不应再投入到节点扩张、公开部署、服务器采购、融资材料、市场叙事或把公共价值包装为技术新颖性。它们不能改变本报告的技术分类。

## References

[1] [WACZ Specification 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/)  
[2] [RFC 7089 — Memento](https://datatracker.ietf.org/doc/html/rfc7089)  
[3] [RFC 8785 — JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785)  
[4] [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/)  
[5] [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)  
[6] [RFC 9943 — SCITT Architecture](https://datatracker.ietf.org/doc/html/rfc9943)  
[7] [WACZ Signing and Verification](https://specs.webrecorder.net/wacz-auth/0.1.0/)  
[8] [C2PA Technical Specification](https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html)  
[9] [RFC 9162 — Certificate Transparency Version 2.0](https://datatracker.ietf.org/doc/html/rfc9162)  
[10] [IPARO — InterPlanetary Archival Record Object for Decentralized Web Archiving and Replay](https://www.ideals.illinois.edu/items/128294)  
[11] [ARCHANGEL: Trusted Archives of Digital Public Documents](https://arxiv.org/abs/1804.08342)  
[12] [Archive Assisted Archival Fixity Verification Framework](https://arxiv.org/abs/1905.12565)
