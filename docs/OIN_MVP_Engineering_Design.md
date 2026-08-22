# OIN MVP 工程设计与协议规范

**版本：** 0.1.0-draft
**作者：** OIN Project
**范围：** 3–5 个独立部署的 Observer、20–100 个公开 HTTP(S) URL、HTML/文件/公告类页面。系统不采集登录后内容、个性化推荐流或需账户访问的数据。

> **OIN 的可验证陈述是：**“由指定公钥标识的 Observer，在其声明的捕获时刻，签署了这条 Observation；该 Observation 所指向的原始归档字节与其哈希相符，并可由签名、时间证据和透明日志证明链检验。”
>
> 该陈述**不等于**“页面内容为真”“来源陈述为真”或“多数 Observer 所见版本为真”。OIN 永不投票消除少数 Observation。

## 1. MVP 架构

OIN 把 **Public Information Object**、**Observation** 与**归档载荷**分开。Object 是一个可长期指代的公共资源；Observation 是某个 Observer 在一段特定捕获过程中作出的、签名的历史陈述；归档载荷是 WARC 或 WACZ 形式的不可变字节。一个 Object 可以连接零到多个 Observation，任何不同载荷哈希的 Observation 都保留。

```mermaid
flowchart LR
  U[公开 HTTP(S) URL] --> C[Capture Layer\nHTTP GET; WARC/WACZ]
  C --> M[Observation Builder\nObject ID; archive SHA-256]
  K[Observer Ed25519 key] --> S[Canonical manifest + signature]
  M --> S
  S --> T[Timestamp Adapter\nlocal declaration / RFC 3161]
  S --> L[Transparency Log\nappend-only Merkle tree]
  S --> O[(Object Storage\nWARC/WACZ)]
  S --> D[(Observer Metadata DB\nPostgreSQL/SQLite dev)]
  L --> D
  D --> R[Signed HTTP Federation\npull/push + hash validation]
  O --> R
  D --> X[Conflict Classifier\nretain all variants]
  D --> A[Discovery REST API\nobject history; proofs]
  O --> V[Offline verifier]
  S --> V
  T --> V
  L --> V
```

| 层 | 输入 | 输出 | 执行者 | 验证者 | 持久化位置 |
| --- | --- | --- | --- | --- | --- |
| Capture | 允许的公开 URL | HTTP 状态、headers、响应字节、WARC/WACZ | Observer 节点 | WARC/WACZ 工具与离线 verifier | 对象存储 |
| Object identity | observed URL、资源类型 | canonical URL、`object_id` | Observer | 任意实现同一规范者 | manifest / 数据库 |
| Observation | 捕获结果、Observer 密钥 | 签名 manifest、`observation_id` | Observer | 任意 Ed25519 verifier | 元数据数据库、导出包 |
| Timestamp | 完整 manifest 哈希 | 本地声明或 RFC 3161 token | Observer / TSA | 离线 verifier | `evidence.json`、timestamps 表 |
| Transparency log | manifest | leaf、检查点、包含证明 | 日志服务 | 任意 Merkle verifier | 日志文件、log_entries 表 |
| Replication | export envelope | 独立验证后新增副本 | 接收 Observer | 接收节点 | 本地 DB + 存储 |
| Conflict preservation | 同一 object 的多条 Observation | divergence / temporal variation 关联 | 每个节点 | API 客户端、人工审阅者 | conflicts 表 |
| Discovery | Object / Observation ID | 全部 Observation、历史、证明 | API 节点 | API 客户端 | 只读索引 |
| Offline verification | bundle 目录 | `VALID` 或 `INVALID` 的逐项结果 | 第三方 | 第三方自身 | 用户本地 |

WARC 直接承载 HTTP 请求/响应、捕获时间和可选块摘要；WACZ 以 ZIP 打包 WARC、索引与文件级完整性元数据，适合可迁移分发与范围请求访问。[1] [2] OIN 不重新定义网页归档格式，而是在归档载荷**外层**定义跨节点可验证语义。

## 2. Object 与 Observation 身份

Object Identity 与 Observation Identity 必须严格分离。`object_id` 代表“此规范化资源及资源类型”；`observation_id` 代表“此 Observer 对一份精确 manifest 的签名陈述”。同一 URL 内容随时间变化会产生同一 Object 下的多个 Observation；两个不同 URL 若通过配置或人工策展确认是同一资源，可记录 alias/semantic identifier，但不能在 MVP 中静默合并。

`canonical_url` 采用保守规范化：协议及主机小写、移除 fragment、移除默认端口、将空路径标准化为 `/`、移除末尾 `/`（根路径除外）、按键值排序 query，并仅剔除明确的跟踪参数 `utm_*`、`fbclid`、`gclid`。它**不**将 `http` 与 `https` 合并，不根据重定向自动重写 Object Identity，也不删除未知 query 参数。原始请求 URL 位于 `original_url`，最终响应 URL 位于 `observed_url`，完整跳转链在 `capture.redirect_chain`。

```text
object_id = "oin:object:sha256:" + SHA-256(JCS({
  canonical_url, resource_type, protocol: "oin/0.1"
}))

observation_id = "oin:observation:sha256:" + SHA-256(JCS(unsigned_manifest_without_observation_id))
observer_id = "oin:observer:sha256:" + SHA-256(raw_ed25519_public_key)
```

MVP 实现使用排序键、无空白的确定性 JSON 序列化；发布 1.0 协议前应以 RFC 8785 JSON Canonicalization Scheme 的正式测试向量锁定互操作性。`observation_id` 从未签名 manifest 派生，而签名覆盖含 `observation_id` 的完整 manifest（但排除 `signature` 字段），从而避免 ID 和签名递归。

## 3. Observation Protocol

签名流程为：构建无签名 manifest → 计算 `observation_id` → 写入该 ID → 对全部 manifest（排除 `signature`）做 canonical JSON → Ed25519 签名 → 追加签名字段。Ed25519 是 RFC 8032 定义的 EdDSA 实例，其公钥和签名尺寸小，适用于 MVP 无证书 Observer 身份。[3]

```json
{
  "protocol_version": "oin/0.1",
  "observation_id": "oin:observation:sha256:5fd0995f0d6af264121a87ea46b1659ddf9251dcbcc1c0b46b60164d1928df4f",
  "object": {
    "object_id": "oin:object:sha256:20f67a4bcbbd80619ca3f275c71298dbb9d7a3a66a7a0f93e36de638b403ceca",
    "canonical_url": "https://agency.example/policy/123",
    "original_url": "https://agency.example/policy/123?utm_source=observer-a",
    "observed_url": "https://agency.example/policy/123",
    "resource_type": "html",
    "semantic_identifiers": {"issuer": "agency.example", "notice_id": "123"}
  },
  "observer": {
    "observer_id": "oin:observer:sha256:77e1d64d2c4b10c9cd8bf83e0683e2860f0f2f642ea5dd0a0289e0b1f4b3d917",
    "public_key": "xYtGdU…base64-encoded-32-byte-Ed25519-key…=",
    "key_algorithm": "Ed25519",
    "created_at": "2026-08-21T10:00:00Z"
  },
  "capture": {
    "captured_at": "2026-08-21T10:00:01Z",
    "capture_method": "http-get",
    "capture_software": "oin.capture.http_capture",
    "capture_software_version": "0.1.0",
    "http_status": 200,
    "http_headers": {"content-type": "text/html; charset=utf-8", "etag": "abc"},
    "redirect_chain": ["https://agency.example/policy/123"]
  },
  "content": {
    "archive_format": "wacz",
    "archive_media_type": "application/wacz",
    "raw_content_hash": "sha256:aaa…",
    "raw_content_bytes": 18421,
    "raw_content_reference": "warc:response-payload:0",
    "archive_hash": "sha256:ccc…",
    "archive_bytes": 19042,
    "archive_reference": "urn:oin:artifact:sha256:ccc…"
  },
  "provenance": {
    "capture_agent": "OIN Observer",
    "assertion_scope": "Observer statement authenticity and artifact integrity only; no truth determination."
  },
  "signature": {
    "algorithm": "Ed25519",
    "signed_fields": "all-fields-except-signature",
    "value": "…base64-encoded-signature…"
  }
}
```

以下示例显示同一 `object_id` 的两个并存版本。它们不是“投票候选”，也不是互相覆盖的修订记录；每一个都保持可验证。

| 字段 | Observation A | Observation B |
| --- | --- | --- |
| `object_id` | `oin:object:sha256:20f6…` | `oin:object:sha256:20f6…` |
| Observer | A | B |
| `captured_at` | 10:00:01Z | 10:00:04Z |
| `raw_content_hash` | `sha256:AAA…` | `sha256:BBB…` |
| 分类 | `observation_divergence` 候选 | `observation_divergence` 候选 |
| 保存状态 | 永久保留 | 永久保留 |

MVP 同时承诺两种字节：`raw_content_hash` 是 WARC response record 中原始 HTTP 响应 body 的 SHA-256，用于 Object 历史差异与冲突检测；`archive_hash` 是承载该 body 的完整 WARC/WACZ 文件的 SHA-256，用于存储、复制与容器完整性。`archive_reference` 因此内容寻址 WARC/WACZ，而 `raw_content_reference` 固定指向 `warc:response-payload:0`。两项校验均为强制项。**不**签 DOM hash 或“规范化 HTML hash”，因为不同解析器、注入标记或序列化规则会带来额外的非确定性。后续版本可添加可选 `normalized_html_hash`，且绝不能替代原始字节哈希。选择 SHA-256 是为了与 WARC/WACZ、RFC 3161 生态互操作；SHA-512 与 BLAKE3 可作为未来的附加摘要，不能取代 v0.1 的主完整性标识。

## 4. Conflict Preservation Specification

系统对内容哈希的不同只作**观察差异分类**，不对事实作裁决。两个不同哈希可能是正常先后时间变化、A/B 地理/CDN 差异、语言协商差异、网络劫持、恶意 Observer 或真正的并时不一致。MVP 默认使用 300 秒并时窗口，且只在两条 Observation 来自不同 Observer、同一 Object、原始 HTTP 内容哈希不同、捕获时间差不大于窗口时产生 `observation_divergence` 候选。窗口外的不同哈希标记为 `temporal_variation`；同哈希标记为 `identical_content`；一个副本缺失但原件未变时标记为 `replication_difference`。

客户端在 `/v1/objects/{id}/observations` 获取**全部**记录，`/history` 获取时序，`/conflicts` 获取关联与分类。没有“接受版本”列、没有多数投票算法，也没有自动删除工作流。UI 应以时间、Observer、摘要、HTTP 状态、独立性风险证据和差异提示帮助人类解释，且必须把“候选冲突”措辞与“事实冲突”区分。

## 5. Identity、密钥轮换与独立性

MVP 采用每个 Observer 一个 Ed25519 keypair 与从公钥哈希派生的稳定 `observer_id`。X.509 为此规模引入 CA、证书更新和撤销运维；DID 对跨生态互操作有用但不解决本 MVP 的签名或独立性问题；自定义随机 ID 无法从公钥自校验。因此三者中 Ed25519 是最低复杂度的推荐方案。

| 事件 | 处理 | 验证含义 |
| --- | --- | --- |
| 正常轮换 | 发布由旧、新华钥交叉签署的 rotation statement；新 key 获得新 `observer_id`，旧记录不重签 | 验证者按捕获时密钥验证历史签名 |
| 主动撤销 | 在可审计 `key-status` 记录中标记 `revoked` 并纳入日志 | 撤销不改写既有 Observation；只影响后续信任策略 |
| 密钥疑似泄露 | 标记 `compromised`、停用采集、生成新 key、发布事件时间和影响区间 | 既有签名仍可数学验证，但信任策略须提示风险 |
| 假 Observer | 接纳名单和独立性资料与签名身份分离 | 签名证明“此 key 签了”，不证明运营者所声称身份 |

`Independence Profile` 记录 `operator`、`organization`、`hosting_provider`、`asn`、`region`、`jurisdiction`、`data_center`、`software_stack`、`network_path`、`funding_relationship`、`administrative_relationship`、`attested_at` 和证据来源。它同时支持可验证事实（例如签名 key、可复查 ASN/DNS 快照）、可检测相关性（同 IP/ASN、证书、镜像延迟）、运营者声明（组织、资金、管理关系）和启发式风险评分。**密码学无法证明现实世界中的组织独立性。** `Independence Risk Score` 仅是披露的风险评估，必须伴随评分方法和证据版本，不能作为去中心化的数学证明。

## 6. Time Evidence、Transparency Log 与存储

`capture.captured_at` 是 Observer 自己签署的本地时间声明。NTP 可改善时钟准确度，但不提供独立存在证明。MVP 将 `local-declaration` 作为默认最小证据，并用可选 RFC 3161 适配器将**完整、已签名 manifest 的哈希**提交 TSA；RFC 3161 的设计正是由 TSA 对摘要签名，以证明该数据在指定时间前已存在。[4] 时间戳 token 不嵌入被时间戳的 manifest，避免哈希递归；它作为 detached evidence 以 `message_imprint = SHA-256(canonical_manifest)` 绑定。Roughtime 可作为后续多源时间扩展；区块链时间戳不在 MVP 范围。

透明日志以 Observation ID 和 manifest hash 的有序组合做叶子，使用 Certificate Transparency 风格域分隔二叉 Merkle Tree。日志在追加后签发包含 `tree_size`、`root_hash`、`issued_at`、日志公钥和 Ed25519 签名的 checkpoint。第三方凭叶子、audit path 与 checkpoint 验证 inclusion；凭两个 tree head 的 consistency proof 验证追加关系。RFC 9162 明确该结构能有效证明条目包含和后续树对先前树的追加超集，但单个恶意日志仍可能展示不一致视图，因此 OIN 还需要跨 Observer 监视、checkpoint gossip 和独立 witness。[5]

MVP 的 `MerkleLog` 是可运行原型；生产替换点可采用 Rekor adapter。Rekor 提供 REST API、透明日志、CLI 和独立部署能力，适合承载 OIN manifest adapter，但 OIN 仍需定义自己的 leaf payload 与离线证据包。[6] 透明日志**不是**唯一存储：可恢复的原始 WACZ 与 manifest 必须在至少两个独立 Observer 的对象存储中保留。

存储通过 `StorageBackend` 抽象：`put()`、`get()`、`exists()`、`delete()`、`list()` 与 `verify()`。MVP 实现 `FileStorage`（本地开发）和 `S3Storage`（MinIO/AWS 等兼容对象存储）。路径只是可更换定位符；签名 manifest 使用内容地址 `urn:oin:artifact:sha256:...`，因此对象可跨后端迁移。IPFS/Filecoin/Arweave 是可选副本后端，不是本 MVP 正确性前提。

## 7. Federation、API 与离线验证

联邦采用可审计、简单的 HTTPS pull/push，而非 MVP 阶段的 libp2p/IPFS。节点先通过 `/v1/replication/ids` 获取增量 ID，再以 `/v1/replication/export/{id}` 获得 `manifest + archive bytes + source proof`。接收方在写库之前必须验证 manifest ID、Ed25519 签名和 archive SHA-256；随后以自身透明日志追加该 Observation，并记录副本状态。源节点证明可供审计，但接收方不会仅凭它信任内容。离线节点恢复时重复 ID 差集同步；退出节点不影响已复制到其他节点的历史。

| 方法 | 请求主体 / 返回主体 | 行为 |
| --- | --- | --- |
| `POST /v1/captures` | `{url, archive_format, resource_type}` | 发起本地捕获、签名并入日志 |
| `POST /v1/observations` | `{manifest, archive_b64, source_node?}` | 先验签/验哈希，再导入；绝不覆盖 |
| `GET /v1/observations/{id}` | manifest | 返回原始签名 Observation |
| `GET /v1/observations/{id}/raw` | WARC/WACZ bytes | 下载载荷 |
| `GET /v1/observations/{id}/proof` | proof JSON | 返回 inclusion proof/checkpoint |
| `GET /v1/objects/{id}` | object summary | 资源摘要 |
| `GET /v1/objects/{id}/observations` | Observation 数组 | 返回全部版本 |
| `GET /v1/objects/{id}/history` | chronological JSON | 返回时序 |
| `GET /v1/objects/{id}/conflicts` | 关联数组 | 返回差异分类，不裁定真伪 |
| `POST /v1/replication/pull` | `{peer_url, observation_ids?}` | 拉取并独立核验 |
| `POST /v1/replication/push` | replication envelope | 推送并独立核验 |
| `GET /v1/verify/{id}` | verification JSON | 节点侧便捷验证；不替代离线验证 |

离线 verifier 输入目录含 `observation.json`、`raw.warc` 或 `raw.wacz`、`observer-public.json`，以及可选 `evidence.json`。它无需访问 OIN 网站，依次核对 WARC/WACZ 容器的 `archive_hash`、从容器中确定性提取的 HTTP response body `raw_content_hash` 与长度、Object ID/canonical URL、Observer ID 与公钥哈希、Observation ID、Ed25519 签名、RFC 3161 evidence（如提供可信 TSA CA）和 Merkle inclusion proof（如提供）。输出仅为 `VALID`/`INVALID` 加逐项结果；缺少第三方时间戳时，默认结果仍可为 `VALID`，但会明确标示 `NOT_PRESENT`，使用 `--require-timestamp` 则失败。

```bash
oin verify ./export
# {
#   "status": "VALID",
#   "checks": {"raw_content_hash": true, "observer_signature": true, ...},
#   "timestamp": {"status": "NOT_PRESENT", ...}
# }
```

## 8. 技术复用与最终推荐栈

| 领域 | 最终选择 | 选择原因 |
| --- | --- | --- |
| Language | Python 3.11 | 加密、HTTP、FastAPI 与归档工具生态成熟，原型可读性高 |
| Capture | `httpx` HTTP GET；后续 Browsertrix adapter | MVP 高保真保存原始 HTTP；复杂 JS 延迟到 adapter |
| Archive | WARC 1.1 + WACZ 1.1.1 | 开放、可迁移、载荷/索引/元数据可封装 [1] [2] |
| Hash | SHA-256 | 与 WACZ、RFC 3161 和 Merkle 生态兼容 |
| Signature / identity | Ed25519 / RFC 8032 | 轻量、可离线验证 [3] |
| Timestamp | 本地声明 + 可选 RFC 3161 TSA | 严格区分声明时间与独立证据 [4] |
| Transparency Log | CT/RFC 9162 算法原型；Rekor adapter | inclusion/consistency proof、可替换运行时 [5] [6] |
| Metadata DB | PostgreSQL；SQLite 仅本地测试 | 关系约束、JSONB、索引与生产运维平衡 |
| Object storage | S3-compatible（MinIO 开发）；本地文件开发 | 迁移方便、无需将归档塞入 DB |
| Replication | Signed HTTPS pull/push | 易实现、断点补齐、每节点独立验证 |
| API | FastAPI + OpenAPI | 强类型、低实现负担 |
| Verifier / CLI | Python + Typer + OpenSSL RFC 3161 验证 | 可脱离服务执行 |
| Frontend | API-first；MVP 不单列前端 | 先确保闭环；后续只消费公开 API |
| Deployment | Docker Compose 开发；Kubernetes 后续 | 先验证 3 节点联邦，再增加编排复杂性 |
| Monitoring | 健康检查、结构化日志、checkpoint gossip 指标 | 检测节点消失与日志分叉 |
| Testing | pytest、协议向量、容器集成测试 | 覆盖加密、冲突、复制与恢复 |

| 规范或项目 | MVP 处置 | 边界 |
| --- | --- | --- |
| WARC | **DIRECTLY REUSE** | HTTP 捕获与原始控制信息容器 |
| WACZ | **DIRECTLY REUSE** | 可携带、可校验归档分发包 |
| Memento / RFC 7089 | **ADAPTER** | `/history` 可映射 TimeMap；不承担身份/证明 [7] |
| C2PA | **OPTIONAL** | 媒体来源载荷的未来扩展，不是网页观察正确性前提 |
| W3C PROV | **OPTIONAL** | `provenance` 的可交换映射，而非签名协议 [8] |
| RFC 3161 | **ADAPTER** | Detached 第三方时间证据 |
| CT / Merkle | **DIRECTLY REUSE** | 树、包含证明、一致性证明模型 |
| Sigstore / Rekor | **ADAPTER** | 生产透明日志替换点 |
| IPFS / Filecoin / Arweave | **OPTIONAL** | 额外副本，不参与 MVP 信任根 |
| libp2p | **NOT NEEDED FOR MVP** | HTTPS federation 更直接可靠 |
| Blockchain | **NOT NEEDED FOR MVP** | 不额外解决真实性；签名、多副本和日志已覆盖所需完整性 |

## 9. 安全威胁模型

| 威胁 | 攻击方式 | 检测 | 防御 | 剩余风险 |
| --- | --- | --- | --- | --- |
| 恶意 Observer | 签署伪造/选择性捕获内容 | 与独立 Observation 比较、独立性 profile | 保留冲突、公开身份与证据 | 签名不能证明所见内容为真 |
| 私钥失窃 | 攻击者伪造后续 Observation | 异常行为、泄露通告 | 轮换、撤销/compromised 状态、硬件密钥生产部署 | 失窃前检测不到的签名不可区分 |
| 假 Observer / Sybil | 批量 key 冒充独立来源 | profile 相关性、注册审查 | 标注运营/网络/资金关系，不以数量投票 | 现实身份无法密码学证明 |
| 时间操纵 | 篡改系统时钟 | TSA imprint、NTP drift 监控 | RFC 3161、多源时间；本地时间明确降级 | TSA 自身是信任方 |
| 内容替换 | 替换 WACZ/WARC | SHA-256 和签名校验 | 内容寻址、离线 verifier | 原始捕获本身可能已异常 |
| 日志回滚/分叉 | 对不同客户端给不同树状态 | checkpoint gossip、consistency proof、witness | 多日志/监视器、不可变 checkpoint 发布 | 单日志离线且无 gossip 时难发现 |
| 节点串通 / 多数串通 | 共同签同一错误内容 | independence evidence、第三方 Observer | 不把多数当真相 | 无法阻止社会层串通 |
| 存储消失 | 节点或 bucket 删除 | 副本状态、周期性 hash audit | 至少两个独立副本、导出包 | 所有副本丢失则不可恢复 |
| 恶意复制 | 发送错误 manifest/载荷 | 入站验签、验 hash、验证 ID | 验证后才写入、速率限制 | DoS 仍须基础设施缓解 |
| DNS/CDN/地域差异 | 不同网络获取不同变体 | 保存 headers、链路、region/ASN profile | 多地域 Observer、保留而非覆盖 | 难以判断原因 |
| 重放攻击 | 重推相同 Observation | ID 唯一约束 | 幂等导入、日志只追加唯一 Observation | 重放流量可耗资源 |
| 审查 / DoS | 阻断 capture/API/replication | 健康检查、缺失副本告警 | 多节点、多路径、退避、离线导出 | 大范围网络阻断无法消除 |

## 10. 开发路线与验收

| Phase | 目标与模块 | 输入 → 输出 | 依赖 | 完成标准 |
| --- | --- | --- | --- | --- |
| 1 | `protocol/`, `schemas/` | 需求 → 固化 ID/JSON schema | 无 | JSON schema 与固定测试向量通过 |
| 2 | `identity/`, `observation/` | capture metadata + key → signed manifest | Phase 1 | 篡改任一字段导致验签失败 |
| 3 | `capture/`, `storage/` | URL → WARC/WACZ + content hash | Phase 2 | HTTP headers/status/bytes 可离线复验 |
| 4 | `api/`, `migrations/` | manifest + artifact → 可查询持久化 | Phase 2–3 | DB 不存 raw archive；索引查询可用 |
| 5 | `transparency/`, `timestamp/` | manifest → proof / detached evidence | Phase 2 | inclusion proof 通过；本地/第三方时间明确区分 |
| 6 | `replication/` API | peer export → 本地独立副本 | Phase 4–5 | 错误签名或哈希绝不落盘 |
| 7 | `conflict/`, discovery | 多 Observation → 全量 history/conflicts | Phase 4 | A/B 不同内容均保留且可发现 |
| 8 | `verifier/`, `cli` | 导出包 → VALID/INVALID | Phase 2、5 | 断网状态可完成必要校验 |
| 9 | `deployments/`, integration tests | 3 节点 → 捕获、复制、失效恢复 | 全部 | A 消失后 B/C 保有历史且可验证 |

MVP 成功不以网页数量衡量，而以真实 Observation、离线验证、冲突同时保存、节点退出后恢复、无单一数据库依赖、新 Observer 加入、完整历史导出和开放格式迁移八项能力衡量。

## References

[1]: https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/ "IIPC: WARC Format 1.1"
[2]: https://specs.webrecorder.net/wacz/1.1.1/ "WACZ 1.1.1 Specification"
[3]: https://datatracker.ietf.org/doc/html/rfc8032 "RFC 8032: Edwards-Curve Digital Signature Algorithm"
[4]: https://www.rfc-editor.org/rfc/rfc3161.html "RFC 3161: Time-Stamp Protocol"
[5]: https://www.rfc-editor.org/rfc/rfc9162.html "RFC 9162: Certificate Transparency Version 2.0"
[6]: https://docs.sigstore.dev/logging/overview/ "Sigstore Rekor Overview"
[7]: https://www.rfc-editor.org/rfc/rfc7089.html "RFC 7089: Memento"
[8]: https://www.w3.org/TR/prov-overview/ "W3C PROV Overview"
