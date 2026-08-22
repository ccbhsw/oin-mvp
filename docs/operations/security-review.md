# OIN MVP 第二阶段：Security Review

**审查范围：** Capture API、Observation 入站验证、签名、归档、透明日志、复制、FileStorage 与当前本地隔离节点。
**结论：** 已修复并验证两项 P1 完整性/SSRF 风险；认证、授权、速率限制、跨网络 TLS/mTLS、S3 和密钥生命周期仍为开放问题。当前节点只能用于绑定回环地址的受控验证网络，不能直接暴露为公共 capture/replication 服务。

## 已验证安全行为

| 场景 | 结果 | 证据 |
| --- | --- | --- |
| localhost、RFC1918、link-local、IPv6 loopback、非 HTTP(S) URL | VERIFIED | `tests/security/test_capture_security.py` 8 项通过；实际 `POST /v1/captures` 请求 `127.0.0.1` 返回 HTTP 422。 |
| DNS 解析至私网地址 | VERIFIED | 测试 monkeypatch 解析为 `192.168.1.9`，`validate_capture_url()` 拒绝。 |
| archive container 篡改 | VERIFIED | 离线 verifier 返回 `INVALID` 且 `archive_hash=false`。 |
| WARC response body 篡改 | VERIFIED | 离线 verifier 返回 `INVALID` 且 `raw_content_hash=false`。 |
| manifest URL、Observer ID、timestamp、raw/archive hash、protocol version 篡改 | VERIFIED | 7 个签名/manifest 篡改案例均被 `verify_manifest()` 拒绝。 |
| 错误 Observer public key / 修改 signature | VERIFIED | Ed25519 测试均拒绝。 |
| Merkle entry / checkpoint signature 篡改 | VERIFIED | `verify_proof()` 返回 false。 |
| 畸形 manifest 或非法 base64 入站 | VERIFIED | 实际 B 节点均返回 HTTP 422；Observation 数在请求前后均为 3。 |
| 重复复制同一 Observation | VERIFIED | 接收节点返回 `already_present`，无覆盖。 |
| archive/raw 双重绑定 | VERIFIED | 新增 `verify_archive_binding()`；节点 ingest 与 `/v1/verify` 都校验 archive hash、WARC/WACZ raw body hash 与字节数。 |

## 已实施最小修正

### SSRF 与资源消耗边界

`capture_url()` 现仅允许 HTTP(S)，拒绝 userinfo、无 host、DNS 解析出的非全局地址，并在每次 redirect 前重新解析/验证目标。捕获限制为最多 5 次 redirect 和 10 MiB 响应体。Capture API 将安全拒绝映射为 HTTP 422，而非 500。

### Archive 与 Observation 内容绑定

此前节点入站路径只核验 manifest 签名和 archive hash。现已复用离线 verifier 的核心语义：从 WARC/WACZ 提取 response body，校验 `raw_content_hash` 与 `raw_content_bytes`。任何一项失败都在写入 storage、database 或本地 transparency log 之前被拒绝。节点侧 `/v1/verify/{id}` 也显示三个绑定检查值。

## OPEN SECURITY ISSUE

| 优先级 | 问题 | 当前状态与要求 |
| --- | --- | --- |
| P1 | API authentication / authorization | 当前 API 无身份认证、授权或 peer allowlist。部署时必须仅绑定受控网络；对外公开前需增加最小节点认证与操作权限。 |
| P1 | Rate limiting / request body limits | FastAPI 路径没有请求频率限制，`archive_b64` 可造成大量内存压力。公开部署前必须限制请求体、并发、单 peer 速率与存储配额。 |
| P1 | DNS rebinding 的连接级保证 | 当前在连接前解析/校验 DNS；http client 随后重新解析的极端 DNS rebinding 仍需在生产使用 egress firewall、代理或固定 transport 完整消除。 |
| P2 | WACZ zip bomb / archive size | Capture response 已有 10 MiB 限制，但入站 WACZ 解压和 base64 envelope 没有同级 archive/解压比限制。 |
| P2 | TLS / mTLS | 当前测试节点使用 loopback HTTP。跨节点生产复制必须启用 TLS，并推荐 mTLS 或签名 peer registry。 |
| P2 | Key rotation / revocation / compromise | 仅实现 Ed25519 基础身份与验签。不存在 rotation statement、revocation registry 或 compromise time-window policy；不得把此项写作已验证。 |
| P2 | 透明日志 witness / consistency / fork detection | inclusion proof 和 checkpoint 已验证；无 witness、gossip、consistency proof 或跨节点 fork 侦测。 |
| P2 | S3 / PostgreSQL hardening | adapter 与 migration 存在，但没有真实 S3、PostgreSQL backup/restore 或 IAM 最小权限演练。 |

## 部署约束

在上述 P1 项关闭前，Observer API 必须绑定 `127.0.0.1` 或受控私网，capture 输入仅能来自受信管理者。不能将“已加入 SSRF 地址过滤”描述为“公共 API 已完成安全审计”。
