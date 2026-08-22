# IWOH v0.1 Fixture Coverage Matrix

**状态：** 可执行输入集的人工审计索引。机器可读的规范性输入在 `fixtures/scenarios.json` 和 `fixtures/expected_results.json`；本文件不应被任一 verifier 导入。

所有 artifacts、statements、receipts 和 History Views 均为离线合成数据。每条可验证 statement 使用 `eddsa-jcs-2022`，archive artifact 使用 WACZ 1.1.1 package layout；`tampered_wacz` 是唯一故意破坏 manifest/resource fixity 的负例。[1] [2]

| Scenario | 覆盖的 Profile 规则 | 关键预期结论 |
| --- | --- | --- |
| `fragment_identity` | fragment excluded from HTTP target; same bytes | `SAME_REQUEST_TARGET`、`REPEATED_OBSERVATION` |
| `query_variation` | query is retained; no silent URL cleanup | `DISTINCT_REQUEST_TARGETS`、`INCOMPARABLE` |
| `redirect_relation` | redirect as evidenced target relation | `RELATED_TARGET`，但不自动 merge / compare |
| `canonical_alias` | HTML canonical as evidenced relation | `RELATED_TARGET`，但不自动 merge / compare |
| `vary_language` | HTTP `Vary: Accept-Language` | `REPRESENTATION_VARIATION` |
| `vantage_variation` | disclosed network vantage difference | `REPRESENTATION_VARIATION` |
| `authentication_variation` | anonymous versus authenticated context | `REPRESENTATION_VARIATION` |
| `repeated_observation` | independent captures of identical bytes | `REPEATED_OBSERVATION` |
| `ordered_temporal_variation` | causally ordered receipts and changed bytes | `TEMPORAL_VARIATION` |
| `parallel_observation` | overlapping trusted intervals without predecessor | `PARALLEL_OBSERVATION` |
| `clock_skew_local_declarations` | local clock values are not ordering evidence | `UNKNOWN` |
| `tampered_wacz` | WACZ resource digest validation | `INVALID_ARCHIVE_DIGEST` |
| `inconsistent_agent_disclosure` | issuer/verification-method binding | `INVALID_AGENT_BINDING` |
| `missing_history_complete_scope` | signed complete declared scope | `MISSING_HISTORY` |
| `partial_history_absence` | partial scope cannot prove absence | `HISTORY_ABSENCE_UNPROVEN` |
| `contradictory_checkpoints` | same log/tree-size, different signed roots | `EQUIVOCATION_DETECTED` |
| `valid_statement_import` | imported capture retains external agency | `IMPORTED_VALID` |

## Assertion completeness

Each expected result contains all nine assertions: target identity, target relation, per-statement validity, comparability, relationship classification, history membership, completeness/scope, import validity and equivocation status. Irrelevant fields are deliberately set to `NOT_APPLICABLE`; the cross-checker will reject missing fields. The corpus currently has **27 WACZ artifacts**, **27 Capture Statements**, **4 causal receipts**, **4 signed History Views**, **17 scenarios**, and **67 fixture files**.

The corpus validates ZIP container integrity for all WACZ files, but this container test does not validate profile semantics; that responsibility belongs to the forthcoming independent Python and Node.js verifiers. Passing the forthcoming corpus says only that both implementations agree with v0.1 rules; it does not establish novelty or production readiness.

## References

[1] [WACZ Specification 1.1.1](https://specs.webrecorder.net/wacz/1.1.1/)  
[2] [W3C Data Integrity EdDSA Cryptosuites v1.0](https://www.w3.org/TR/vc-di-eddsa/)
