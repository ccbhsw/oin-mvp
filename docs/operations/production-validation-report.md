# OIN MVP Production Validation Report

**版本：** 第二阶段初步验证
**审计提交：** `e71b667` 为阶段二开始时 HEAD；本阶段新增安全修正、迁移、测试与报告尚待提交。
**最终结论：** **PARTIAL PASS**。

> **为什么不是 PASS。** 当前已经严格验证了 OIN 的最小签名、归档、冲突保留、复制、节点恢复和离线验证闭环，并修复了同内容重复历史记录缺陷。但未完成 3 个长期独立宿主、7 天连续运行、PostgreSQL/S3 真实恢复、认证授权、速率限制和完整密钥生命周期。因此不满足附件中的所有 Production Validation PASS 条件。

## VERIFIED

- A、B、C 在不同 API 进程、数据目录、SQLite 数据库、FileStorage 根目录、Observer Ed25519 keypair 和 transparency log key 下运行；Observer ID 已确认不同。
- 真实公开 HTTPS capture 成功，产生 WACZ、raw content hash、archive hash、Observation ID、Observer ID 与 Ed25519 signature。
- A→B、A→C、B→C、B→A、C→A 的复制路径均在短时故障/恢复流程中实际运行。
- Conflict Preservation 成功：同 Object 的不同 raw content 在同一窗口内产生 `observation_divergence`，A/B Observation 均保留；没有自动事实裁决、覆盖或多数投票。
- Temporal Variation 单元测试成功：窗口外不同内容被分类为 `temporal_variation`，且历史继续保留。
- A 离线后 B/C 继续健康；A 恢复后通过 peer 补齐；删除 A SQLite database 后可由 C 重建 Observation metadata。
- archive 字节篡改、embedded HTTP raw body 篡改、manifest 字段篡改、错误 public key、错误 signature、Merkle entry 篡改和 checkpoint signature 篡改均会导致验证失败。
- SSRF 安全边界已补强并测试：禁止非 HTTP(S)、localhost、私网、link-local、IPv6 loopback 及 DNS 解析到私网的目标；redirect 会重新校验；最大 5 redirect 与 10 MiB response 限制已实施。
- 入站 ingest 与节点侧 verify 现同时检查 archive hash、raw content hash 和 raw content bytes；畸形 manifest 与非法 base64 被实际 API 以 HTTP 422 拒绝且不增加 Observation 数。
- 完整 export package 在所有 A/B/C 服务停止后仍由 `oin verify` 返回 `VALID`，包括 archive hash、raw content hash、Observer signature 和 transparency inclusion proof。
- FileStorage 的 write/read/duplicate/checksum/missing/corruption 行为已由可重复测试覆盖。
- 同一 Observer 在不同时间观察相同 raw content 的多条 Observation 现在可被保留；错误唯一约束已移除，并提供 PostgreSQL migration `002_allow_repeat_content_observations.sql`。
- 自动化测试当前为 30 项通过，静态检查通过。

## PARTIALLY VERIFIED

- 三节点独立性：已证明进程、数据目录、SQLite、FileStorage、key 与 log 的隔离；未证明 operator、provider、physical machine、region 或 network 独立性。
- Transparency log：已验证 append、checkpoint、inclusion proof 与篡改拒绝；未验证 consistency proof、witness、gossip 或 fork detection。
- Replication：已验证正常、重复、冲突、畸形 manifest、非法 base64 与恢复；尚未系统验证大 payload、网络分区、超时重试、恶意 valid-signature-but-policy-invalid peer 和所有损坏 WACZ 变体。
- Storage：FileStorage 已验证；S3 adapter 仅代码存在，尚未连接真实兼容服务。
- 数据库恢复：SQLite database 删除后从 peer 恢复已验证；PostgreSQL backup/drop/restore 未执行。
- 性能：已测本地 SQLite 100–100,000 Observation metadata；未测 capture、WACZ、S3、PostgreSQL 或真实网络 replication。

## NOT VERIFIED

- 3 个不同长期宿主或云 provider 的 Observer。
- 7 天连续运行和可选 30 天运行。
- 20–50 URL 固定集合的成功率、timeout、redirect、失败率与长期 storage 指标。
- Docker Compose 实际容器启动；当前环境没有 Docker/Docker Compose。
- RFC 3161 外部 TSA token 的真实获取、可信 CA 链离线验证。
- PostgreSQL backup/restore 与 S3 object recovery。
- 密钥 rotation、revocation 和 compromised-key policy 的完整实现与测试。

## FAILED

阶段二初始 performance run 发现 schema 中的 `UNIQUE(observer_id, raw_content_hash)`。它禁止一个 Observer 在不同时间记录相同 bytes，违反 Observation 历史一等公民原则。该问题已用回归测试复现，随后从 SQLAlchemy schema 与新的 PostgreSQL migration 中移除，修复后重复 Observation history 测试、30 项测试和 100,000 条 benchmark 均通过。该失败不应被隐藏。

## OPEN ISSUE

- **P1：** API 尚无 authentication、authorization、peer allowlist、request body limit 或 rate limiting；仅限绑定回环或受控私网部署。
- **P1：** DNS rebinding 需要生产 egress firewall / proxy 或固定 transport 进一步防护；当前预解析校验不是完整网络隔离保证。
- **P2：** 入站 archive/WACZ 的解压大小与压缩比上限未实施；存在 zip bomb 资源耗尽风险。
- **P2：** 透明日志无 witness、consistency proof、gossip 或跨节点 fork 侦测。
- **P2：** key rotation / revocation / compromise policy 未实现，不能声称已满足完整密钥安全测试。
- **P2：** 无 S3 和 PostgreSQL 真实验证；无长期 Observability 与告警。
- **P3：** history API 在 100,000 条同 Object Observation 时全量加载，约 9.26 秒；应增加 cursor pagination，同时保留完整导出能力。

## RECOMMENDED NEXT STEP

第一优先级是在三个长期隔离宿主部署现有不变的 OIN 代码并运行 7 天。部署前关闭 API P1：为管理操作与 replication 配置认证/授权、请求大小限制、速率限制、TLS/mTLS 和网络 egress 防护。随后执行 PostgreSQL/S3 backup/restore、RFC 3161、20 URL 连续 capture、网络分区和 key lifecycle 测试。只有这些工作完成后，才能重新评估 Production Validation 是否可从 PARTIAL PASS 升为 PASS。
