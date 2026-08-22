# IWOH v0.1 独立互操作输入集合同

**状态：** Phase 4 test contract。该文件定义两套独立 verifier 在同一静态 corpus 上必须产生的输出，不是实现设计文档，也不得被实现用作逐 case 的硬编码规则来源。

## 1. 目的与独立性

输入集用于证伪以下最小主张：若不采用 IWOH v0.1 中明确的跨标准 mapping，两个采用不同语言/工具链的实现不能仅从 WARC/WACZ、HTTP、VC EdDSA、Memento 和透明日志基本对象中得到相同的 history interpretation。它不测试 OIN MVP，不读取、不复制、不导入 `/home/ubuntu/oin-mvp/` 的代码、schema 或测试。

实现 A 是 Python verifier；实现 B 是 Node.js verifier。它们只能共享：IWOH Profile、静态 fixture input、官方规范链接和 expected result。它们**不得**共享 source file、library module、decision table、generated output 或 runtime process。每个实现的 rule mapping 和 artifact parser 必须单独编写。

## 2. 输入 layout

```text
fixtures/
├── keys/public_keys.json
├── trust_registry.json
├── artifacts/*.wacz
├── statements/*.json
├── receipts/*.json
├── history/*.json
├── scenarios.json
└── expected_results.json
```

所有 statement、receipt 与 History View 是使用 W3C `DataIntegrityProof` / `eddsa-jcs-2022` 签名的 JSON。fixture 仅使用 ASCII property names、I-JSON-compatible values、无浮点数；这样 Python 与 Node.js 可按 RFC 8785 JCS 得到相同 canonical bytes。WACZ artifact 符合 WACZ 1.1.1 的 ZIP/data-package layout，并包含 WARC response evidence、CDXJ index、pages list、`datapackage.json` 与 `datapackage-digest.json`。[1] [2] [3]

## 3. 九类可执行断言

每个 scenario 的 expected result 都包含以下九个字段；不适用时值为 `NOT_APPLICABLE`，从而避免各实现通过遗漏输出逃避比较。

| 编号 | 字段 | 允许的核心结论 |
| --- | --- | --- |
| A1 | `target_identity` | `SAME_REQUEST_TARGET`、`DIFFERENT_REQUEST_TARGETS`、`NOT_APPLICABLE` |
| A2 | `target_relation` | `EXACT_REQUEST_TARGET`、`RELATED_TARGET`、`DISTINCT_REQUEST_TARGETS`、`TARGET_RELATION_UNVERIFIED`、`NOT_APPLICABLE` |
| A3 | `statement_validity` | 每 statement 为 `VALID` 或 Profile 第 6 节 error code |
| A4 | `comparability` | `COMPARABLE`、`INCOMPARABLE`、`NOT_APPLICABLE` |
| A5 | `relationship` | Profile 第 8 节的七个互斥 classification 或 `NOT_APPLICABLE` |
| A6 | `history_membership` | `PRESENT`、`MISSING_HISTORY`、`HISTORY_ABSENCE_UNPROVEN`、`NOT_APPLICABLE` |
| A7 | `completeness_scope` | `COMPLETE_FOR_DECLARED_SCOPE`、`PARTIAL`、`UNKNOWN`、`NOT_APPLICABLE` |
| A8 | `statement_import_validity` | `IMPORTED_VALID`、`REJECTED_INVALID`、`NOT_APPLICABLE` |
| A9 | `equivocation_status` | `EQUIVOCATION_DETECTED`、`EQUIVOCATION_NOT_DETECTABLE`、`NOT_APPLICABLE` |

## 4. Scenario coverage

Corpus 至少测试 fragment、query、redirect、canonical alias、`Vary` language、vantage、authentication、repeat bytes、可信有序变更、无因果的平行 observation、missing/partial history、tampered WACZ、issuer/key binding error、local clock skew、contradictory checkpoints 与 imported statement。每个 scenario 仅使用合成的 `example.test` / `example.net` URI 和离线 artifacts；它不捕获或访问公网数据。

## 5. 验证程序的边界

Verifier 必须按 Profile 验证 VC proof、issuer binding、WACZ manifest/fixity、WARC payload digest 与可选 causal receipt。它不得把本地 JSON 文件 mtime、artifact 路径排序、fixture file name、truth labels 或 expected result 当作时序、target 或 trust evidence。

通过 corpus 仅证明两套独立实现对指定 profile rules 一致；它不证明规则新颖、完整、生产安全或现实独立性。若两套实现只有通过共享 decision table 才一致，或者去掉某个 profile 字段仍可凭现有标准原生语义完全再现所有结果，则候选贡献必须降级或证伪。

## References

[1] [WACZ Specification 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/)  
[2] [W3C Data Integrity EdDSA Cryptosuites v1.0](https://www.w3.org/TR/vc-di-eddsa/)  
[3] [RFC 8785 — JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785)
