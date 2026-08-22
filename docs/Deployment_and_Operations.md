# OIN MVP 部署与运维规范

## 开发网络与生产网络的边界

Docker Compose 用于本地建立三个**数据隔离**的 Observer。每个默认节点拥有单独的持久卷、SQLite 元数据数据库、归档目录、Observer 私钥和透明日志私钥。该设计故意避免让 A/B/C 共用一个开发数据库或归档目录，因而可验证复制、冲突保留和节点退出恢复的基本性质。

```bash
docker compose up --build -d
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
curl http://localhost:8003/healthz
```

| 环境 | 数据库 | 归档存储 | 透明日志 | 适用性 |
| --- | --- | --- | --- | --- |
| 本地开发 | 每节点 SQLite | 每节点 Docker volume / FileStorage | 每节点文件日志 | 零配置 3 节点测试 |
| 受控生产 MVP | 每节点独立 PostgreSQL | 每节点独立 S3-compatible bucket/prefix | 每节点持久卷 + checkpoint 发布 | 20–100 URL、3–5 Observer |
| 后续扩展 | PostgreSQL 高可用实例但不跨独立性边界共享 | 多区域 bucket + 冷备/可选 IPFS | Rekor adapter + 多 witness | 更大规模、可审计运维 |

`postgres` 和 `minio` 已在 Compose 的 `adapters` profile 中提供，以验证可选适配器镜像与连接参数；它们**不能**在生产中成为全部 Observer 的单一共享真相源。要启用示例服务，请执行 `docker compose --profile adapters up -d`。容器镜像安装了 PostgreSQL 和 S3 compatible 依赖；每个生产 Observer 以自己的 `OIN_DATABASE_URL`、`OIN_S3_BUCKET`、凭证和对象存储边界启动。

```bash
# 单个生产 Observer 的示例变量。三个节点必须使用不同的 DB/bucket/credential 边界。
export OIN_NODE_NAME=observer-a
export OIN_DATA_DIR=/var/lib/oin
export OIN_DATABASE_URL='postgresql+psycopg://oin:REDACTED@db-a/oin'
export OIN_STORAGE_BACKEND=s3
export OIN_S3_BUCKET=oin-observer-a
export OIN_S3_ENDPOINT_URL=https://s3.example.net
export AWS_ACCESS_KEY_ID=REDACTED
export AWS_SECRET_ACCESS_KEY=REDACTED
uvicorn oin.api.app:app --host 0.0.0.0 --port 8000
```

> `OIN_PRIVATE_KEY_PATH` 的私钥必须由节点本地密钥管理机制提供。部署不得将私钥写入镜像层、Git 仓库、共享对象存储或同步备份。开发版未加密 PEM 仅为可运行 MVP 的便利性，生产应采用 HSM、KMS 或严格权限的挂载密钥。

## 复制、日志和恢复操作

每个节点应定期保存从同伴 `/v1/replication/ids` 获取的 ID 清单，并按差集使用 `/v1/replication/pull` 拉取。接收端在写入元数据或对象存储前检查 Observation ID、Ed25519 签名、WARC/WACZ `archive_hash`；之后以自己的透明日志写入新的 leaf。因此节点 B 不会仅因为 A 的 API 返回成功而信任 A。

| 事件 | 必做操作 | 可验证结果 |
| --- | --- | --- |
| 新 Observation | 至少推/拉至两个独立节点 | 每个副本都有自身 StorageRef 与可查询 proof |
| 节点离线 | 从另两个节点检查 Object history 与 raw archive | 不需要原节点即可 `GET /verify/{id}` 或离线 `oin verify` |
| 存储审计 | 周期运行 `StorageBackend.verify()` 并重算 WARC payload hash | archive/content 双哈希失败即隔离副本 |
| 日志检查点 | 定期导出、交叉交换和检查 consistency proof | 不一致 tree head 作为 fork 事件保留与告警 |
| 密钥轮换 | 发布旧/新 key 交叉签名 rotation statement；保留旧 key | 历史 Observation 仍按原 key 验证 |
| 私钥泄露 | 停止捕获、标记 compromised、发布影响区间、启动新 key | 数学验签仍可通过，但策略层显示风险 |

透明日志 checkpoint、Merkle audit path 和时间证据均应在每次导出时携带；它们是 manifest 之外的 detached evidence。RFC 3161 token 必须保存其可信 TSA CA 链，离线验证使用 `openssl ts -verify` 对 canonical manifest 的消息摘要进行验证。若没有 token，`local-declaration` 只表达 Observer 的已签署时间声明。

## Compose 与 Kubernetes 的部署顺序

MVP 先使用 Compose 验证协议而非过早引入编排复杂性。完成 3–5 个真实独立节点、外部对象存储、跨自治网络复制和 checkpoint gossip 的运行验收后，再迁移 Kubernetes。迁移时应遵循一节点一 namespace/service account/DB credential/bucket prefix 的隔离原则，并将每个 Observer 私钥作为独立 secret 引用。

| Compose 开发配置 | Kubernetes 后续映射 | 不可丢失的约束 |
| --- | --- | --- |
| `observer-a/b/c` services | 每 Observer 一个 Deployment/StatefulSet | 不共享密钥、卷、数据库或 bucket credential |
| Docker volume | PVC + 对象存储副本 | 可恢复 WARC/WACZ 与透明日志状态 |
| `/healthz` | liveness/readiness probes | 不把健康检查当成证明系统正确性 |
| bridge network | mTLS/NetworkPolicy | 联邦 API 必须有速率限制、认证策略和审计日志 |

## 已执行的验收测试

本运行环境不包含 Docker daemon，因此未启动 Compose 容器；Compose 文件已提供并通过静态审阅。为验证实际可运行性，使用三个隔离数据目录、三个独立本地 API 进程完成了同等的联邦闭环。

| 验收项目 | 实际动作 | 结果 |
| --- | --- | --- |
| 节点启动 | A/B/C 在 8101/8102/8103 端口运行，各有独立数据目录 | 三个 `/healthz` 均返回 `ok` |
| 真实捕获 | A 对 `https://example.com` 执行 HTTP capture，生成 WACZ 与签名 Observation | 生成 `raw_content_hash` 和 `archive_hash` |
| 多节点复制 | B、C 从 A 执行 HTTP pull | 两个节点均返回 `created` |
| 冲突保留 | B 用自身 Ed25519 key 对同一 Object 导入不同原始 body | `observation_divergence`，`is_conflict_candidate=true`，C 保存两条 Observation |
| 节点退出恢复 | 终止 A 后，在 B、C 验证 A 的已复制 Observation | B/C 均返回 `VALID` |
| 离线验证 | 从 B 导出 `observation.json + raw.wacz + evidence.json` 后运行 `oin verify` | `VALID`，raw content hash 与 Merkle proof 均通过 |
| 单元测试 | `pytest -q` | 4 项通过 |
| 静态检查 | `ruff check .` | 通过 |

## 监控与告警最小集

生产节点至少应公开或发送下列指标：捕获成功/失败率、队列延迟、每个 Object 的最后 Observation 时刻、复制积压数量、各 peer 的 `verified`/`failed` 副本数、对象存储 hash audit 失败数、最近 checkpoint tree size、checkpoint fork 事件、密钥状态和磁盘/对象存储容量。所有指标仅描述系统状态；不得把“多节点一致”标作内容真相指标。
