# OIN MVP 第二阶段：Acceptance Report

**最终验收结论：PARTIAL PASS**

本报告严格以实际证据为准。`VERIFIED` 表示本阶段已真实运行并通过；`PARTIALLY VERIFIED` 表示代码与部分测试存在但不构成完整证明；`NOT VERIFIED` 表示尚未在要求环境中执行；`OPEN ISSUE` 表示当前不能忽略的工程风险。

| 验收条件 | 状态 | 证据或限制 |
| --- | --- | --- |
| 3 个独立 Observer 成功运行 | PARTIALLY VERIFIED | 3 个进程、独立 directory/SQLite/key/storage/log；同一宿主，非跨组织/跨云。 |
| 各节点独立身份与密钥 | VERIFIED | 3 个不同 Observer ID 与独立 Ed25519 PEM。 |
| 真实 URL capture | VERIFIED | `example.com`、IANA example page 捕获成功。 |
| Observation 独立生成 | VERIFIED | A 与 B 独立生成带签名 manifest。 |
| 原始 bytes 保存 | VERIFIED | WARC/WACZ 通过 FileStorage 保存与导出。 |
| raw_content_hash 验证 | VERIFIED | 节点与 offline verifier 均验证；篡改失败。 |
| archive_hash 验证 | VERIFIED | 节点与 offline verifier 均验证；篡改失败。 |
| Observer signature 验证 | VERIFIED | 正常、错误 key、错误 signature、字段篡改均测试。 |
| Transparency Log 验证 | PARTIALLY VERIFIED | checkpoint/inclusion proof/篡改拒绝已验证；无 witness/consistency/gossip。 |
| Observation 复制 | VERIFIED | A↔B/C 多路径复制与恢复已运行。 |
| Conflict Preservation | VERIFIED | `observation_divergence` 保留两条 Observation。 |
| 无自动事实裁决/覆盖少数 Observation | VERIFIED | 冲突与重复复制测试未发现覆盖；代码不含投票路径。 |
| Temporal Variation / Divergence 区分 | VERIFIED | 300 秒内外单元测试均通过。 |
| A 下线后 B/C 工作 | VERIFIED | 健康与 B→C 新 Observation 复制已运行。 |
| A 恢复后同步 | VERIFIED | A 从 B 恢复 2 条缺失 Observation。 |
| archive 篡改失败 | VERIFIED | 离线验证返回 INVALID。 |
| Observation 篡改失败 | VERIFIED | URL、Observer ID、时间、哈希、版本、signature 测试通过。 |
| 错误签名 / 非法 Observation 拒绝 | VERIFIED | API 对畸形 manifest/base64 返回 422；signature 测试通过。 |
| 完全离线验证 | VERIFIED | A/B/C 停止后 `oin verify` 返回 VALID。 |
| 数据库恢复 | PARTIALLY VERIFIED | SQLite 删除后从 peer 恢复；PostgreSQL backup/restore 未执行。 |
| Storage 恢复 | PARTIALLY VERIFIED | FileStorage 校验/缺失/损坏可发现；完整对象丢失后的 peer artifact 恢复与 S3 未完成。 |
| SSRF 等高风险处理或记录 | PARTIALLY VERIFIED | 公网 URL 过滤与大小/redirect 限制已实现；认证、rate limit、DNS rebinding、zip bomb 仍开放。 |
| 7 天连续运行 | NOT VERIFIED | 当前环境不持久，尚无三个长期独立宿主。 |

> 即使此前多数协议闭环测试通过，缺少 7 天连续运行与独立长期宿主这一项也意味着不能宣布 Production Validation PASS。

详细证据位于 `initial-implementation-audit.md`、`independence-profile.md`、`failure-recovery-report.md`、`security-review.md`、`continuous-run-report.md`、`performance-report.md` 与 `production-validation-report.md`。
