# IWOH Real-World Falsification v0.2

**审计日期：** 2026-08-21 GMT+8  
**结论分类：** **D — NO EVIDENCE / INSUFFICIENT REAL CORPUS**  
**审计问题：** Independent Web Observation History Profile（IWOH）是否是不可替代的技术贡献，而非现有 Web archive、provenance、transparency 与签名标准的组合 profile？

> **结论。** 这轮严格的真实世界实验没有得到 IWOH 不可替代性的证据。它确认了一件较窄的事实：跨 archive 的安全历史解释需要明确 mapping rules。它同时确认，这些 rules 能够以 HTTP、WARC/WACZ、Memento、PROV、VC、SCITT、CT 和既有扩展/profile 机制实现；没有发现必须引入新的密码学原语、归档格式、日志结构、存储协议或传输协议的缺口。由于实际公开 archive corpus 中 **0 条** artifact 是 IWOH-conformant Capture Statement，且 **0 个** signed History View 可供验证，不能测试 IWOH 是否在真实第三方部署中产生现有标准 profile 无法产生的互操作效果。因此按照预先锁定的四选一规则，唯一诚实分类为 **D**，不是 A、B 或 C。

## 1. 审计目标、判定门槛与禁止推理

本审计不评价 OIN MVP 的工程质量、公共价值、商业价值、抗审查属性或社会价值。它只检验一个技术命题：在真实多 archive evidence 上，IWOH 是否迫使独立实现作出一致且安全的历史解释，而既有标准组合无法以正常 extension/profile 机制达到同样结果。

四选一门槛在实验开始前锁定。A 要求既有标准无需新的互操作语义即可完全覆盖；B 要求存在少量必要、可测试而且不能被既有 profile 正常替代的 interoperability semantics；C 要求存在既有标准无法表达的核心协议语义；D 要求真实 corpus、真实 profile input 或真实用户效果不足以支持前三者。实际结果满足 D：现有 standards-only Baseline-B 已能构造全部安全行为，而真实 corpus 又不含可运行 IWOH verifier 的输入。

本报告不把以下情况误作肯定证据：API query 未返回、被 CAPTCHA 阻断、缺少 WARC 下载、archive 未发布 scope statement、缺少透明日志 receipt、单一 archive 的 TimeMap、相同 timestamp，或不同 payload digest。它们分别只能表示访问受限、evidence unavailable、archive-local knowledge、时间字段相同或 byte-level difference；均不能推出 global absence、同一 capture event、source causality、observer independence 或 equivocation。

## 2. 真实语料、来源与可访问性

研究只使用实际访问的公共、合法入口。Internet Archive 的 Availability API、CDX Server 和 replay 说明其公开 memento access path；Arquivo.pt 提供 CDX metadata/replay；Common Crawl 允许 public index 与 WARC Range retrieval；Stanford 的 Webrecorder archive 提供可下载真实 legacy WACZ。UK Government Web Archive 的 collection/search UI 公开可用，但自动 timeline query 在 human verification 页面止步，未尝试绕过。[1] [2] [3] [4] [5]

| Evidence record | Archive | 真实证据 | 审计可用结论 | 不能得出的结论 |
| --- | --- | --- | --- | --- |
| IA `example.com` 2010 / 2024 | Internet Archive | 实际 replay 与 Availability response；同 original URL，在不同 archive-reported datetime 展示不同可见内容。 | 同字面 URI、两条 archive-reported 时间、replay body 可见差异。 | 原站内容在两个时点发生因果变化、完整历史、payload fixity。 |
| IA CDX URL variants | Internet Archive | 实际 exact CDX response 含 `http`、`https`、`www`、port 与 query form。 | URL forms/digests/timestamps 是公开 metadata。 | 自动 alias/canonical/query equivalence policy。 |
| Arquivo repeated records | Arquivo.pt | 实际 CDX response 对同 URI 给出同 digest 的多行记录和 ARC location。 | local index has repeated reported-digest rows。 | repeated capture cause、global history、original agent。 |
| IA + Arquivo same datetime | 两个独立 archive endpoint | 两端报告同 URI 与 `20100323155533`。 | same literal target string and same reported 14-digit datetime。 | one shared capture event、agency transfer、same payload。 |
| Common Crawl Saturn WARC | Common Crawl | Public CDX + read-only Range extraction of real WARC record。 | WARC-Date、digest、request/response headers，以及 `Vary`、language、Cookie、Authorization、User-Agent 和 GeoIP input。 | 两条 representation 是否 comparable；language/region/auth pair。 |
| Stanford legacy WACZ | Stanford SUP / Webrecorder | 实际下载 `etd.wacz`；archive has legacy `webarchive.yaml`、CDXJ、WARC 和 root 301。 | package layout diversity、package digest、local redirect evidence。 | current WACZ 1.1.1 conformance、cross-archive target merge、import chain。 |
| UKWA query | UK Government Web Archive | 公开 search UI reached, query blocked by human verification。 | automated collection unavailable。 | archive or Web historical absence。 |

A–O 实际场景覆盖为 **4 个 AVAILABLE、3 个 PARTIAL、8 个 UNAVAILABLE**。同 URL 的跨时 replay、同 archive repeated-digest row、两 archive same-URL/same-time、WARC representation context 与 legacy package layout均为真实输入。语言对、地域/CDN 对、authenticated/unauthenticated 对、fragment 对、verified cross-archive different-byte pair、signed history scope、statement import 和 checkpoint conflict 未得到真实可验证案例。完整登记册、原始 URLs、响应 metadata 与本地证据路径见 [`real_corpus_registry.md`](real_corpus_registry.md) 和 [`real_corpus_registry.json`](real_corpus_registry.json)。

## 3. Existing-Standards Baseline-A：不添加 mapping 的原生结果

Baseline-A 禁止候选 Profile vocabulary/rules，只使用 HTTP、Memento、WARC/WACZ、PROV、VC、SCITT、CT 和实际 evidence。HTTP 规定 target resource、representation、content negotiation 和 `Vary`，但不规定独立 archives 如何合并 URL forms 或比较不同 capture representations。[6] Memento 规定 Original Resource、Memento、TimeGate 和 TimeMap；它明确允许 versions 位于多个 servers，而每个 server 通常只知道自己持有的 versions，TimeMap coverage interval 也是 optional。[7] WARC 提供 capture date、target URI、request/response、record association 和 digest，但推荐 no particular algorithm for choosing a record by date；PROV/VC 又提供可扩展的 provenance/issuer carrier，而非 Web-capture comparison procedure。[8] [9] [10]

| 必答问题 | Baseline-A 输出 |
| --- | --- |
| target 是什么 | HTTP request target / Memento Original Resource URI；对真实 records 只能做 literal URI equality。 |
| two captures 是否属于同 target | 相同 URI string：literal equality。`http`/`https`/`www`/query/redirect/canonical/mirror：`UNDEFINED_BY_EXISTING_STANDARDS`，除非另选 policy。 |
| representations 是否 comparable | WARC/HTTP 给出选择 context 输入；没有现成 cross-archive predicate。 |
| different hash 是否 temporal change | 否。它只证明 different reported digest 与 archive-reported time；因果关系未定义。 |
| 是否 parallel observation | 否。既有 base standards 不从 two archive records/timestamps 推导该关系。 |
| 是否 repeated observation | 同 archive same-digest rows 是 index evidence；跨 archive observation relation 未定义。 |
| archive absence 是否可推出 absence | 否。local non-return、partial TimeMap 或 blocked access 不等于 global absence。 |
| imported agency 是谁 | PROV/VC 可表达，但本 corpus 没有实际 transferred statement/provenance chain。 |
| 什么算 equivocation | CT/SCITT 可对同一透明服务的 valid proof 判断；本 corpus 没有 archive checkpoint pair。 |

Baseline-A 的价值是严格显示现有标准已经提供的**输入证据**，以及没有原生选择的解释层。它不证明需要 IWOH；它只证明若想要 deterministic cross-archive output，就必须选定 mapping policy。

## 4. Existing-Standards Baseline-B：允许标准扩展的可替代实现

Baseline-B 采用 WARC extension、WACZ additional resources、PROV/VC domain vocabulary、SCITT domain statement 和 CT/SCITT receipt 这些已存在的扩展机制。WARC 明确支持 extension fields/types；WACZ 支持在 package resources 中声明 additional files；PROV-DM 和 VC 2.0 均是 domain-agnostic/extensible；SCITT 将 statement payload 视为 application/domain-defined。[8] [11] [9] [10] [12]

Baseline-B 构造了独立的 **Archive Evidence Exchange Mapping（AEEM）**。它使用 B1 exact URI key + typed relation evidence、B2 artifact/signature binding、B3 complete Vary/auth/vantage/policy precondition、B4 receipt-first time precedence、B5 conservative result vocabulary、B6 declared-scope non-absence、B7 importer preserves original agent/issuer 和 B8 CT/SCITT log-conflict mapping。B1–B7 是 profile-sized mapping choices；B8 的 log-level mechanism 直接复用现有 CT/SCITT。完整规则及每个真实 case 的输出见 [`baseline_b.md`](baseline_b.md)。

| 真实 case | Baseline-B 安全结果 | 必须写出的 mapping | 是否需要新基础原语 |
| --- | --- | --- | --- |
| IA 2010 / 2024 | `chronological-archive-records` 与 `different-records-not-assessed`。 | B1, B3, B4, B5。 | 否。 |
| Arquivo same digest rows | `same-evidence` at reported-digest level；保留 separate records。 | B2, B4, B5。 | 否。 |
| IA / Arquivo same datetime | `different-records-not-assessed`。 | B1, B2, B4, B5。 | 否。 |
| Common Crawl context | `not-assessed`；retain Vary/auth/vantage inputs。 | B2, B3。 | 否。 |
| legacy WACZ redirect/canonical | retain typed link; do not merge target keys。 | B1, B5。 | 否。 |
| blocked UKWA query | preserve unavailable status; emit no absence。 | B6。 | 否。 |

这已经反驳了“必须有新的 OIN/IWOH protocol 才能实现安全解释”的强主张。已有 stack 能实现完全相同类型的保守行为；代价是实现者必须公开写出 mapping rules。该代价属于 interoperability profile work，不是不可替代的协议基础设施。

## 5. IWOH v0.1 在真实 corpus 上的实际运行结果

IWOH v0.1 的自身 conformance rule 是严格的：完整 Capture Statement 必须有 `profile_version: "IWOH-0.1"`、VC-style issuer、`eddsa-jcs-2022` proof、capture activity、request context、response digest、WARC/WACZ evidence binding、time evidence 和 context completeness。其 Section 3 明示：不带 profile version 的 WARC、WACZ、C2PA、VC、PROV、SCITT statement 或 TimeMap 可以保存展示，**不得被声称为完整 IWOH interoperability result**。[13]

真实 corpus 的 8 个输入单元均未通过该 input gate。7 个 artifact records 与 UKWA access case 都缺 capture-agent IWOH DataIntegrityProof、profile version 和 required signed statement fields；Common Crawl raw WARC 虽保存许多 response/request inputs，也不是 Profile Capture Statement；Stanford legacy WACZ 也没有 profile statement。审计没有把它们重新签名为 IWOH statement，因为那会让审计者伪装为 historical original capture agent。

| IWOH requested output | 真实 corpus 的允许输出 | 原因 |
| --- | --- | --- |
| target relation | `NON_PROFILE_INPUT`，无 profile result。 | 无 IWOH Capture Statement。 |
| statement validity | `NON_PROFILE_INPUT`，无 profile result。 | 没有可应用 Section 6 的 statement。 |
| comparability | `NON_PROFILE_INPUT`，无 profile result。 | Section 7 requires two `VALID` statements and full context declarations。 |
| relationship classification | `NON_PROFILE_INPUT`，无 profile result。 | Section 8 additionally needs eligible time evidence。 |
| history membership/scope | `NON_PROFILE_INPUT`，无 profile result。 | 没有 signed History View/declared scope/commitment。 |
| import validity | `NON_PROFILE_INPUT`，无 profile result。 | 没有 transferred profile statement/evidence bundle。 |
| equivocation | `NON_PROFILE_INPUT`，无 profile result。 | 没有 named log checkpoints or signed History Views。 |

因此，IWOH 在真实 corpus 上的“效果”不是 failure by invalid signature，也不是 successful comparison；它是 **not runnable because no real Profile input exists**。这决定了本报告不能以 synthetic fixture 的 prior success 代替 deployed real-world evidence，也不能声称 IWOH 已被现实采用或已证明用户收益。详见 [`profile_application_real_corpus.md`](profile_application_real_corpus.md)。

## 6. 同一真实案例的三臂逐字段对照

| Dimension | Baseline-A | Baseline-B | IWOH v0.1 actual run | 可证实结论 |
| --- | --- | --- | --- | --- |
| target grouping | literal URI or undefined variant relation。 | deterministic exact-key + typed relation evidence。 | no output。 | deterministic grouping needs a mapping; no evidence current IWOH implementation is uniquely necessary. |
| representation relation | raw HTTP/WARC/Memento facts。 | limited safe labels/no-assessment。 | no output。 | standards-only profile can avoid false change/conflict claim. |
| comparability | inputs exist, predicate absent。 | explicit context completeness precondition。 | no output。 | R2-type predicate has realistic inputs but no real IWOH pair. |
| time / parallel | archive-reported time only。 | receipt-precedence/non-inference policy。 | no output。 | existing time/receipt systems suffice; no qualified real pair tests stronger semantics. |
| history scope/absence | local holdings only。 | declared-scope rule。 | no output。 | scope needs honest labeling, not a new primitive. |
| import/agency | generic model, no case evidence。 | preservation mapping if transfer occurs。 | no output。 | untested in deployed real corpus. |
| equivocation | existing CT/SCITT mechanism, no case evidence。 | direct same-log mapping。 | no output。 | untested across Web archives; log primitive is prior art. |

这不是 “IWOH 被 Baseline-B 完全功能性击败” 的已验证实证结论，因为 IWOH 无法接收当前 corpus；同样也不是 “IWOH 证明必须存在” 的结论。唯一成立的比较结论是：existing-standard mapping 已能构造安全替代行为，而 profile 真实互操作效果尚无输入证据。

## 7. 两条独立 standards-only 实现与分歧调查

路径 A 使用 Python，literal HTTP/Memento/WARC reading；路径 B 使用 Node.js，provenance/statement-first reading。两者不引用 OIN、IWOH implementation、彼此代码或共同 schema，只读取同一个 machine-readable real corpus registry。重复运行输出逐字节稳定，边界检查确认没有任何项目实现导入。源代码、source SHA-256、JSON outputs 和 comparator 见 [`independent_path_a/`](independent_path_a/)、[`independent_path_b/`](independent_path_b/) 与 [`independent_results/`](independent_results/)。

| 指标 | 结果 | 解读 |
| --- | ---: | --- |
| 真实 cases | 7 | 每个 case 均来自实际 archive evidence/access result。 |
| raw serialized outputs 相同 | 0 / 7 | Existing standards do not naturally select one common output vocabulary/model. |
| factual conservative outcome compatible | 7 / 7 | 两路径都拒绝无证据的 causality、global absence、import agency 与 checkpoint conflict。 |
| 实质矛盾历史断言 | 0 / 7 | 没有路径对同一真实 evidence 给出相反、会误导用户的 conclusion。 |
| 可运行 IWOH enforcement test | 0 / 7 | 全部为 `NON_PROFILE_INPUT`。 |

分歧不是 implementation error。HTTP 的 resource/representation 语言、Memento 的 Original Resource/Memento 语言和 PROV 的 entity/activity/agent 语言都允许对同一 evidence 作不同建模；WARC digest 也不规定 observation relation。两路径在 raw output 上不同，显示需要 mapping；但两路径均作保守结论，未显示任何真实 user harm，且 Baseline-B 可把这些 outputs 统一。因而该实验既没有证实 A，也没有证实 B/C；它为 D 提供了额外理由：profile enforcement value 尚未在真实 input 上被测量。

## 8. R1–R8 逐条证伪

| Rule | 最终规则级判断 | 证据理由 |
| --- | --- | --- |
| R1 Target grouping | `PARTIALLY_FALSIFIED_AS_PROFILE` | HTTP/Memento/PROV provide carriers; a profile must choose grouping basis, but no new primitive exists. |
| R2 Representation comparability | `PARTIALLY_FALSIFIED_AS_PROFILE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | RFC 9110/WARC provide Vary and context inputs; Baseline-B defines an equivalent safe predicate; no real conformant pair exists. |
| R3 Time evidence | `FALSIFIED_AS_UNIQUE_PRIMITIVE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | RFC 3161/RFC 4998/CT/SCITT plus causal ordering are prior art; no real qualified receipt pair was collected. |
| R4 Parallel observation | `FALSIFIED_AS_UNIQUE_PRIMITIVE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | CRDT/happens-before semantics directly cover concurrency; no real suitable pair was collected. |
| R5 History scope | `PARTIALLY_FALSIFIED_AS_PROFILE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | Memento/SCITT scopes and collection metadata can express limits; no real signed scope statement is present. |
| R6 Statement exchange | `FALSIFIED_AS_UNIQUE_PRIMITIVE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | WACZ + VC/PROV + SCITT domain-profile mechanisms already support a signed envelope; no deployed import case exists. |
| R7 Independence disclosure | `FALSIFIED_AS_UNIQUE_PRIMITIVE` + `NO_EVIDENCE_OF_DEPLOYED_VALUE` | Cryptography cannot prove sociological/operational independence; provenance disclosure is existing profile work. |
| R8 Equivocation | `FALSIFIED_AS_UNIQUE_PRIMITIVE` for log conflict + `NO_EVIDENCE_OF_DEPLOYED_VALUE` for archive aggregation | CT/SCITT already define same-log consistency/non-equivocation; no real archive checkpoint pair exists. |

R1、R2 与 R5 可以成为**有用的 profile clauses**，因为互操作实现确实需要明确 policy。它们不满足 “不可替代技术贡献” 的门槛。R3、R4、R6、R7 与 R8 的基础能力已有直接 prior art；它们在 Web archive domain 中的组合不把它们变成新的底层协议。详见 [`r1_r8_falsification_matrix.md`](r1_r8_falsification_matrix.md)。

## 9. 真实用户需求调查

真实用户和运营方确实有 Web evidence 的 provenance、integrity、context、scope 和 independent verification 需求。Webrecorder 的 ReplayWeb.page 已展示 original URL、archived date、capture tool、signed WACZ validation、package hash 与 observer/key metadata，并在加载时验证 archive data。[14] Starling Lab/Rolling Stone 的公开 war-crimes investigation 用 Webrecorder、C2PA、hash/signature、content addressing 和多种存储系统保存了 183 个 Web archives，且向读者开放 inspectable evidence。[15] BnF 对研究人员的访谈显示，他们需要可独立复核的 Web citations、shared/defined corpus 与已记录的 source selection；受访者明确指出 printouts/screenshots 对 dynamic Web source 缺少足够 scientific validity/authenticity。[16] IIPC 也将 selection goals、harvest metadata、unaltered preservation 与未来 researcher/public access 列为 web archiving practice 的核心。[17]

这些证据只证明**问题真实存在**，不证明 IWOH 必须存在。反而它们表明，现有 WACZ、signature、C2PA、Webrecorder、archive metadata 和 content-addressed preservation 已能在真实项目中承担大量需求。没有一份公开来源要求或描述了 IWOH 的 target relation、comparability、parallel classification、signed History View 或 cross-archive import vocabulary 为不可替代的缺口。

## 10. 最终分类与可替代性判断

**最终分类：D — NO EVIDENCE / INSUFFICIENT REAL CORPUS。**

该分类不是含糊的中间结论，而是由预设门槛直接决定。不能选 A，因为 Baseline-A 没有自然选定统一的 cross-archive mapping。不能选 B，因为 Baseline-B 表明 B1–B7 可以在既有标准允许的 profile mechanism 内重建，且没有真实 profile input 证明 IWOH 不能被这样替代。不能选 C，因为没有发现新的、无法以现有 carrier/extension/receipt/log mechanism 表达的核心协议语义。

IWOH 当前**可被替代**为一个 standards-only Archive Evidence Exchange mapping：WARC/WACZ 负责 capture evidence/fixity，HTTP 负责 selection inputs，Memento 负责 archive-local temporal navigation，PROV/VC 负责 agent/issuer/assertion，SCITT/CT 负责 optional transparent registration and log proofs。B1–B7 作为一个公开 profile 写入即可。这种替代并不否认 profile engineering 的实用性；它否认将该实用性称为不可替代的新协议技术贡献的证据基础。

剩余可主张的价值仅限于：**一个可公开讨论、可复现、可进行 conformance test 的 Web-archive interoperability profile 草案**。它不能宣称为已验证的 OIN core protocol innovation、现实独立 observer history layer、证明实际 operator independence 的机制、全局 Web history layer，或超越既有标准组合的不可替代解决方案。

## 11. 若继续，唯一值得做的下一最小实验

下一步不是扩展 OIN MVP、增加节点、部署公网或生产化。唯一有信息增益的实验是：邀请至少 **两个实际独立的 archive/capture operators**，各自对同一事先约定的公开 URL set 产生自己签名的 Capture Statements 和 signed scoped History Views。每个 operator 必须保留 WARC/WACZ evidence、complete request context、capture policy、time evidence、scope/peer set disclosure 和 issuer provenance；至少包含一个 matched `Vary`/locale/user-agent case、一个 unmatched context case、一个 cross-archive different-byte case、一个 imported statement case，以及一个 same-log checkpoint pair。

实验将预先注册两份不含 IWOH vocabulary 的 standards-only profiles，分别由独立团队实现，并与 IWOH verifier 对同一真实 signed statements 交叉运行。若 IWOH 输出与两个 standards-only profiles 相同，或其差异可通过普通 VC/PROV/SCITT/WARC extension profile 消除，则应将结论升级为 **A — FALSIFIED**。只有当所有 existing-standard profiles 在公开、独立复现中持续无法表达并稳定验证某一必要 result，而 IWOH 在同一 evidence 上能做到，才有资格重新讨论 **B**。在该实验发生前，禁止选择 B 或 C。

## 12. 现实性、复杂度与用户价值的诚实边界

IWOH 所述的 evidence-preserving history practice 在技术上可实现：此前 synthetic conformance experiment 已显示不同语言工具链可以实现一组共享规则。它的现实部署可行性和用户价值尚未由本次真实 corpus 证实。当前 public Web archive ecosystem 已经让 archive operators、调查记者、研究人员和 preservation institutions 使用 WARC/WACZ、replay、metadata、signatures、C2PA、transparent registration 与 content addressing 来完成相当多的工作。

因此，技术复杂度不等于新颖性；公共价值不等于协议创新；“多 observer、跨时间、保留不同 bytes”也不等于不可替代的语义缺口。IWOH 的确提出了值得测试的 interoperability discipline，但本轮证据要求我们停止把它描述为已证实的技术创新。

## 13. 证据文件与参考文献

**本次实验产生的本地证据：**

| Artifact | 内容 |
| --- | --- |
| [`methodology.md`](methodology.md) | 预先锁定的证伪标准与判定门槛。 |
| [`real_corpus_registry.md`](real_corpus_registry.md) / [`.json`](real_corpus_registry.json) | 真实 archive evidence、来源、access boundary 与 A–O coverage。 |
| [`baseline_a.md`](baseline_a.md) | 无 mapping 的 existing-standard results。 |
| [`baseline_b.md`](baseline_b.md) | 可替代的 existing-standard mapping。 |
| [`profile_application_real_corpus.md`](profile_application_real_corpus.md) | IWOH input gate and `NON_PROFILE_INPUT` results。 |
| [`cross_arm_comparison.md`](cross_arm_comparison.md) | 三臂逐字段 comparison。 |
| [`independent_paths_audit.md`](independent_paths_audit.md) | 两路径、zero raw agreement 和 semantic compatibility investigation。 |
| [`r1_r8_falsification_matrix.md`](r1_r8_falsification_matrix.md) | R1–R8 与 user-demand evidence。 |

[1] [Internet Archive, “Wayback Machine APIs”](https://archive.org/help/wayback_api.php).  
[2] [Arquivo.pt, “URL search: CDX server API”](https://github.com/arquivo/pwa-technologies/wiki/URL-search:-CDX-server-API).  
[3] [Common Crawl, “Get Started”](https://commoncrawl.org/get-started).  
[4] [Webrecorder, “WACZ 1.1.1”](https://specs.webrecorder.net/wacz/1.1.1/).  
[5] [The National Archives, “UK Government Web Archive”](https://www.nationalarchives.gov.uk/webarchive/).  
[6] [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html).  
[7] [RFC 7089, Memento](https://www.rfc-editor.org/rfc/rfc7089.html).  
[8] [IIPC, WARC Format 1.1](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/).  
[9] [W3C, PROV-DM](https://www.w3.org/TR/prov-dm/).  
[10] [W3C, Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/).  
[11] [Webrecorder, “WACZ 1.1.1”](https://specs.webrecorder.net/wacz/1.1.1/).  
[12] [RFC 9943, SCITT Architecture](https://www.rfc-editor.org/rfc/rfc9943.html).  
[13] [Independent Web Observation History Profile v0.1](../../novelty-audit/iwoh-profile-v0.1/profile/Independent_Web_Observation_History_Profile_v0.1.md).  
[14] [Webrecorder, “Showing Provenance on ReplayWeb.page Embeds”](https://webrecorder.net/blog/2022-11-10-showing-provenance-on-replaywebpage-embeds/).  
[15] [Starling Lab, “Creating the First Cryptographic Archive for a War Crimes Investigation”](https://starlinglab.org/case-studies/the-first-cryptographic-archive-war-crimes-investigation/).  
[16] [Stirling, Chevallier, Illien, “Web Archives for Researchers”](https://www.dlib.org/dlib/march12/stirling/03stirling.html).  
[17] [International Internet Preservation Consortium, “About archiving”](https://netpreserve.org/web-archiving/about-archiving/).  
[18] [RFC 9162, Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html).  
[19] [RFC 4998, Evidence Record Syntax](https://www.rfc-editor.org/rfc/rfc4998.html).  
[20] [Shapiro et al., “Conflict-free Replicated Data Types”](https://arxiv.org/abs/1805.06358).
