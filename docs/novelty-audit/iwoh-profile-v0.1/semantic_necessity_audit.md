# IWOH v0.1 语义必要性审计

**状态：** Phase 7 证据记录，不是创新结论。  
**问题：** IWOH v0.1 的字段和规则是否消除了两套独立 verifier 无法仅靠基础 artifact 得出的歧义；如果是，它们是否已经被一个现有规范以同样的跨 archive Web-observation contract 强制规定。

## 1. 交叉实现结果

Python implementation A 以 `cryptography` 和 `zipfile` 处理 Ed25519/JCS/WACZ；Node.js implementation B 以原生 `crypto`、显式 JCS serializer 和系统 `unzip` 处理相同输入。两者不导入 OIN source、彼此 source 或 fixture generator。它们在 **17 个离线 scenario**、**27 个 WACZ artifacts**、**27 个 signed Capture Statements**、**4 个 causal receipts**、**4 个 signed History Views** 上，均输出九类完整 assertions。

交叉比较器同时将 A 和 B 与 `expected_results.json` 比较，并将 A 与 B 逐 field 比较。结果为 `pass: true`、`failure_count: 0`。两套实现经重复运行均产生字节相同的自身 JSON output；fixture corpus 也经重复生成得到相同 file digest。该结果证明 Profile 的 rules 可被不同工具链以可重复方式实现；它不证明这些 rules 具有专利新颖性、标准新颖性或不可由现有 extensible standards 承载。

## 2. 字段/规则消融矩阵

| IWOH rule | 被移除或留为未规定时的 corpus 歧义 | 直接覆盖 scenario | 已有基础能力 | IWOH 所增加的内容 |
| --- | --- | --- | --- | --- |
| R1：Request Target Identity 与显式 Target Relation | fragment 与 query 被同样“URL canonicalization”处理；redirect/canonical 被静默合并或完全断开。 | fragment、query、redirect、canonical | RFC 9110 定义 request target/representation；Memento 定义 URI-R/URI-M。 [1] [2] | fragment removal、query preservation 与 relation result 的一致判定。 |
| R2：双重 evidence binding 与 agent binding | artifact package 被替换而 payload digest 仍被信任，或签名 key 不能绑定到 issuer。 | tampered WACZ、agent disclosure | WACZ manifest/fixity、WACZ Auth、VC Data Integrity。 [3] [4] [5] | statement 必须同时绑定 WACZ bytes、WARC payload bytes 和 issuer assertion method。 |
| R3：representation selection comparability | 同 URL 的语言、认证、geographic/CDN response 被错误标记为 temporal change 或 conflict。 | Vary/language、vantage、auth | RFC 9110 的 `Vary` 与 representation selection。 [1] | Vary/auth/vantage/capture policy 的合取 compare predicate 和 reason code。 |
| R4：evidence-bounded temporal semantics | 不同 hash 加本地 clocks 被冒充为有序变化；无 causality 的 independent captures 被错误排序。 | ordered temporal、parallel、clock skew | RFC 3161/CT/SCITT 可提供已签名/透明时间或 registration evidence；SCITT 定义 signed statement/receipt model。 [6] [7] | 只有 externally verifiable interval 或 causal receipt 才可得到 temporal/parallel result；local clock 只能产生 `UNKNOWN`。 |
| R5：互斥 relationship classification | 相同 bytes、可证明有序不同 bytes、并行不同 bytes、selection variation 和不可比较情况被混成 “conflict”。 | repeated、temporal、parallel、Vary/auth/vantage | Git/event log/provenance 能表示 event history；没有本 corpus 发现的 IWOH classification contract。 | 七个互斥 result 与前置条件。 |
| R6：non-adjudication、scope 与 absence semantics | local archive 未返回 statement 被误读为全网不存在，或不同 payload 被强制选出 winner。 | complete missing、partial history | Memento TimeMap 表示 server 提供的 Mementos；SCITT 把 storage/discovery 留给 application。 [2] [6] | `COMPLETE_FOR_DECLARED_SCOPE` 与 `HISTORY_ABSENCE_UNPROVEN` 的可测试边界，外加禁止真伪/赢家输出。 |
| R7：cross-archive exchange | imported evidence 被重写为接收 archive 的 capture，或 package 失去 external agent provenance。 | valid import | WACZ package 可复制；VC/PROV 能表达 issuer/agent。 [3] [5] [8] | `IMPORTED_VALID` 保留外部 issuer、evidence digest 和 capture claim 的 import rule。 |
| R8：equivocation detection boundary | 没有 checkpoint 时把未检测到 equivocation 写成无 equivocation；不同 roots 不能有统一判定。 | contradictory checkpoints | CT/SCITT 的 checkpoint/receipt/non-equivocation mechanisms。 [6] [7] | history response 的 exact condition：同 log ID 和同 tree size 的两条 valid roots 不同才是 `EQUIVOCATION_DETECTED`。 |

## 3. 必要性判定

R1–R8 都是 corpus 判定所必需的：移除任一规则会至少令一个 scenario 失去唯一、安全的 expected result，或者导致 verifier 被允许把 evidence 误归类为 change、conflict、absence、equivocation 或 agency。此处的“必需”是**IWOH v0.1 所承诺的九类可重复输出**的必要条件，不是 Web archiving、provenance 或 transparency 的一般必要条件。

R1–R8 都可承载在已有 WARC/WACZ、VC/PROV、HTTP/Memento、SCITT/CT 机制之上。没有一个 rule 创建新的 hash、signature、archive container、content address、Memento、Merkle inclusion proof、consensus 或 replication primitive。WACZ 提供 portable package/fixity，Memento 提供 time-based Web resource access，SCITT 提供 signed statements 与 transparency-service evidence，但三者均未规定此处的跨 archive comparison、scope 和 history interpretation contract。[2] [3] [6]

因此，cross-implementation test 支持的最强陈述是：**R1–R8 是一个可独立实施、可测试的 application/profile-level semantic mapping。** 测试不支持“OIN 创造了新的底层协议原语”这一陈述。

## 4. 仍需被证伪的条件

下列任一证据会使 IWOH 的 profile-level contribution 结论降为 `FALSIFIED`：第一，发现已发布并已实施的规范或开源协议，它使用等价的 mandatory fields 和 conformance rules 对跨 archive Web captures 输出同一 R1–R8 result；第二，独立的第三方实现证明无需 R1–R8 中任一新增 mapping，直接组合这些 standards 的原生 mandatory semantics 即可在相同 corpus 上产生所有九类结果；第三，profile 的 output 可以完全以某个现有明确 profile 的无损、规范化 projection 表达，而不新增或约束任何 field/algorithm。

反之，只有来自与本任务无关的第三方实现、公开 conformance suite 以及外部 review 的复现，才有资格加强 profile-level result；两份由同一研究过程写成的 implementation 不能单独构成强新颖性证据。

## References

[1] [RFC 9110 — HTTP Semantics](https://datatracker.ietf.org/doc/html/rfc9110)  
[2] [RFC 7089 — Memento](https://datatracker.ietf.org/doc/html/rfc7089)  
[3] [WACZ Specification 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/)  
[4] [WACZ Signing and Verification](https://specs.webrecorder.net/wacz-auth/0.1.0/)  
[5] [W3C Data Integrity EdDSA Cryptosuites v1.0](https://www.w3.org/TR/vc-di-eddsa/)  
[6] [RFC 9943 — SCITT Architecture](https://datatracker.ietf.org/doc/html/rfc9943)  
[7] [RFC 9162 — Certificate Transparency Version 2.0](https://datatracker.ietf.org/doc/html/rfc9162)  
[8] [W3C PROV-DM](https://www.w3.org/TR/prov-dm/)
