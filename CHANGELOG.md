# CHANGELOG

## 2026-08-24

### 时间戳
- 同一 `raw_content_hash` 再次提交时，必须携带可绑定当前已签名 manifest 的 RFC 3161 凭证，否则返回 `TIMESTAMP_EVIDENCE_REQUIRED`，不会把 `signature_valid` 打成 false。
- 某个 content_hash 的第一次提交仍允许 Observer 本地时间声明（`local-declaration`），公共节点首次捕获体验不变。
- `GET /v1/verify/{id}` 增加 `timestamp.kind`（`local-declaration` / `rfc3161`）。重复内容且证据为 RFC 3161 时，同时给出 TSA 盖章时间与 `captured_at` 的差值，仅供查看，不作为拒绝条件。
- 覆盖 `docs/limitations.md` 第 1 条中“可对同一内容无限重签并更换 captured_at”这一段；**不覆盖**“只提交一次时伪造 captured_at 仍无法被发现”。不要把本次改动读成时间戳漏洞已整体关闭。
- 历史 observation 不会被回溯盖章。CLI `oin submit` 增加可选 `--tsa-url`。

## 2026-08-22

### 撤回
- 撤回全链路测试报告中第 5 步（REPLICATE/VERIFY）的 PASS 结论。原因：审计发现当时未实际调用验证接口，该结论仅代表数据同步成功，不代表验证逻辑通过。修正后的验证结果详见交叉验证报告。
- 原始报告文件：docs/experiments/alicloud_test_report.md
