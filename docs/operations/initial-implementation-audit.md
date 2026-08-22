# OIN MVP 第二阶段：初始实现审计

**审计时间：** 2026-08-21 GMT+8
**审计范围：** `main` 分支、提交 `e71b667ed6217ae49de0a60cb088421b9c33727b`、本地工作区。
**审计方式：** 源码、配置、schema、migration、文档与自动化测试的只读检查；本文件不将“代码存在”描述为“生产能力已证明”。

> **结论摘要。** 当前仓库已经实现了一个可运行的、签名化、冲突保留、可复制并支持离线验证的 OIN MVP 闭环。它尚未完成生产化验证：缺少真实分离宿主的 7 天连续运行、容器实际运行、数据库备份恢复、S3 实测、安全边界测试、性能测试和完整密钥生命周期实现。因此当前状态只能作为第二阶段的起点，不能宣称 Production Validation PASS。

## A. 当前实现清单

| 组件 | 当前实现 | 审计判定 |
| --- | --- | --- |
| Protocol / Identity | URL 规范化、确定性 JSON、SHA-256 派生 Object/Observation ID、Ed25519 身份与签名。 | 已实现；仅基础密钥生命周期。 |
| Observation | 已签名 manifest 记录 Object、Observer、HTTP 捕获元数据、raw/archive 双哈希、签名与版本。 | 已实现。 |
| Capture / Archive | `httpx` HTTP GET 捕获，WARC 1.1 生成、最小 WACZ 封装和 response body 提取。 | 已实现；未具备 SSRF 防护、大小限制或浏览器渲染捕获。 |
| Storage | FileStorage 与可选 S3-compatible adapter，引用按 archive SHA-256 内容寻址。 | FileStorage 已本地验证；S3 尚未真实验证。 |
| Repository | SQLite/PostgreSQL SQLAlchemy 模型保存 Object、Observation、Signature、Timestamp、StorageRef、Conflict、Replica 和 Independence Profile。 | 已实现；缺少备份恢复实测。 |
| Conflict | 同 Object、不同 raw content hash、300 秒窗口内产生 `observation_divergence`；窗口外产生 `temporal_variation`。 | 已实现并有基础测试。 |
| Replication | HTTP export/push/pull，以 ingest 的签名与 archive hash 校验作为接收门槛。 | 已实现并曾在本地三进程验证；尚未覆盖恶意、损坏和网络中断矩阵。 |
| Transparency log | 本地追加式 Merkle log、Ed25519 checkpoint、包含证明和离线 proof 验证。 | 已实现并有基础测试；无 consistency proof、witness、gossip 或 fork 侦测。 |
| Offline verification | 验证 archive hash、从 WARC/WACZ 重新提取 raw body、raw hash、Object/Observer ID、签名、可选时间证据和 Merkle proof。 | 已实现并曾用导出包验证。 |
| API / CLI | FastAPI 捕获、查询、复制、节点信息、proof、节点侧 verify；Typer CLI 的 keys/capture/verify/serve。 | 已实现；尚未完成 API 安全测试矩阵。 |
| Deployment | Dockerfile、三 Observer Compose、PostgreSQL/MinIO adapters profile。 | 配置已实现；当前环境未安装 Docker，尚未容器实测。 |

## B. 当前自动化测试清单

当前 `pytest --collect-only -q` 收集到 4 项测试，`ruff check .` 当前通过。

1. `test_signed_manifest_and_offline_bundle`：构造 Observation 并验证导出包。
2. `test_observation_tamper_is_detected`：篡改 archive 后离线验证拒绝。
3. `test_log_inclusion_proof`：验证 Merkle inclusion proof。
4. `test_conflicting_observations_are_both_retained`：验证两位 Observer 的冲突 Observation 同时保留。

现有测试目录中没有 `tests/integration/`、`tests/failure/`、`tests/security/` 或 `tests/offline_verification/`。这些目录及可重复运行的阶段二测试尚待建立。

## C. 已经实际验证的功能

以下项目是此前本地真实运行而非仅从源码推断的证据：三个独立数据目录和独立 API 进程的 A/B/C 节点启动；A 对 `https://example.com` 的真实 HTTP 捕获与 WACZ Observation 生成；A 到 B、A 到 C 的复制；由 B 对同一 Object 注入不同原始内容后产生并保留 `observation_divergence`；停止 A 后 B/C 对已复制 Observation 继续返回 `VALID`；从 B 导出验证包并通过不依赖 OIN API 的 `oin verify`。

这些证据说明 MVP 的最小闭环存在，但不等同于不同云服务商、不同组织或长期生产环境的独立性证明。

## D. 仅存在代码或仅部分验证的功能

Docker Compose 三节点容器、PostgreSQL、MinIO/S3、RFC 3161 外部 TSA、长期定时捕获、7 天连续运行、30 天运行、完整失败恢复、数据库备份恢复、数据库删除后恢复、S3 损坏与恢复、恶意复制输入、SSRF、防重放、速率限制、密钥轮换、密钥撤销、compromised key 标记、consistency proof、witness/gossip、100 到 100,000 Observation 的性能曲线都尚未在本阶段开始时真实验证。

透明日志当前证明单节点本地日志对 Observation 的包含性；它不证明全网日志一致，也不替代 archive、Observation 签名或独立存储。

## E. 明显技术风险

| 优先级 | 风险 | 审计依据与影响 |
| --- | --- | --- |
| P1 | SSRF 与重定向到私网 | `capture_url()` 直接请求用户提供 URL，并允许跟随 redirect；当前没有公网地址、DNS 再解析、localhost、RFC1918、link-local 或 metadata endpoint 防护。未解决前不得把 capture API 公开暴露。 |
| P1 | 入站 archive 与 raw content hash 绑定不足 | `ingest()` 校验签名和 archive hash，但没有从 WARC/WACZ 重提取 body 后校验 `raw_content_hash`；节点侧 `/v1/verify` 也未执行这项检查。离线 verifier 已实现该检查。应在不改变协议的前提下将同一校验前移到 ingest 和 API verify。 |
| P1 | 无 API authentication/authorization/rate limit | API 可被任何网络可达客户端捕获、导入、复制、导出归档或消耗带宽。生产验证必须将其限定在隔离测试网络并记录为 Open Security Issue，直至增加最小访问控制。 |
| P2 | 无 response/archive 大小上限 | 当前 HTTP/WARC/WACZ 使用内存字节串，未限制响应、解压或 base64 payload 尺寸，存在资源耗尽与 zip bomb 风险。 |
| P2 | 透明日志单点与并发边界 | 文件 JSONL 日志没有跨进程锁、consistency proof、witness 或 gossip。该日志不能作为跨节点不可分叉证明。 |
| P2 | S3 与数据库恢复未验证 | S3 adapter 未实测；migration 存在但没有 PostgreSQL backup/restore 演练。 |
| P2 | 密钥生命周期不完整 | 基础 key 生成与验签存在，但 rotation、revocation、compromise statement 和历史信任链尚未实现。 |
| P3 | Capture 范围有限 | 当前是 HTTP GET；JavaScript 渲染、认证内容、robots/politeness、MIME policy 和复杂 WARC 互操作性未实现。 |

## F. 当前不应修改的稳定部分

第二阶段不应推翻以下已经通过基础验证并与 OIN 核心性质直接相关的部分：Object 与 Observation 的分离；Observation 的不可变、签名化 manifest；raw content hash 与 archive hash 的双重承诺；Ed25519 签名身份；冲突 Observation 并列保存；不进行多数投票或事实裁决；WARC/WACZ 作为可移动原始归档；复制时先验证后持久化；以及不依赖 OIN 网站的离线验证器。

后续只应做最小、证据驱动的修正，优先修复会破坏 OIN 核心性质或会使公开部署不安全的问题。任何修正都必须附带可重复运行的失败测试和报告证据。
