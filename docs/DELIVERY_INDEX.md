# OIN MVP 交付索引

本仓库直接进入 OIN 的工程设计与可运行 MVP 实施，不包含项目市场审计、创新性审计或 GO/NO-GO 判断。

| 附件要求的交付物 | 仓库位置 | 交付形态 |
| --- | --- | --- |
| 1. OIN MVP Architecture | `docs/OIN_MVP_Engineering_Design.md` §1 | 架构图、闭环、职责边界 |
| 2. OIN Protocol Specification | `docs/OIN_MVP_Engineering_Design.md` §2–3；`oin/protocol/core.py` | ID、canonical JSON、签名序列 |
| 3. OIN Observation Schema | `schemas/observation.schema.json`；工程设计 §3 | JSON Schema、双重完整性字段、示例 |
| 4. OIN Conflict Preservation Specification | 工程设计 §4；`oin/api/repository.py` | divergence/temporal variation 保留逻辑 |
| 5. OIN Observer Specification | 工程设计 §5；`oin/identity/keys.py` | Ed25519 身份、轮换/泄露处理 |
| 6. OIN Independence Profile | 工程设计 §5；`independence_profiles` schema | 证据、检测、声明与风险评分边界 |
| 7. OIN Storage Specification | 工程设计 §6；`oin/storage/backends.py` | File/S3 adapter、迁移与完整性策略 |
| 8. OIN Replication Specification | 工程设计 §7；`oin/api/app.py` | Signed HTTP pull/push、差集与入站验证 |
| 9. OIN Transparency Log Specification | 工程设计 §6；`oin/transparency/merkle.py` | append-only Merkle、checkpoint、包含证明 |
| 10. OIN Offline Verification Specification | 工程设计 §7；`oin/verifier/offline.py` | 无官网依赖的 CLI 验证 |
| 11. OIN API Specification | 工程设计 §7；运行时 `/docs` | REST endpoints 与 request/response 边界 |
| 12. OIN Database Schema | `migrations/001_initial.sql`；工程设计 §8 | PostgreSQL 表、外键、索引、约束 |
| 13. OIN Repository Structure | `README.md`；下方目录树 | 可开发 Python 仓库 |
| 14. OIN Docker Deployment | `Dockerfile`、`docker-compose.yml`、`docs/Deployment_and_Operations.md` | 三节点开发部署与生产隔离规范 |
| 15. OIN Security Threat Model | 工程设计 §9 | 攻击、检测、防御与残余风险 |
| 16. OIN MVP Development Roadmap | 工程设计 §10 | 9 个阶段、依赖、输入输出、验收 |
| 17. OIN Recommended Technology Stack | 工程设计 §8 | 明确选型与标准复用矩阵 |
| 18. InformationObject Schema v1 | `oin/schema/v1.py`；`tests/test_schema_v1.py` | Pydantic v2、签名验证、JSON Schema 输出与边界测试 |
| 19. Discovery Bootstrap 原型 | `oin/discovery/`；`docs/architecture/discovery-bootstrap-api.md` | 签名 Descriptor、静态 Bundle、只读 API、输入边界与节点签名的 Bundle 来源审计 |
| 20. Custody 激励现实检验 | `docs/economics/custody-incentives-reality-check.md` | 非代币化参与动机、失败假设与可证伪实验 |
| 21. Operator 试点准备材料 | `docs/experiments/operator-pilot-protocol.md`、`operator-pilot-recruitment.md` 与 `templates/` | 待批准的招募说明、资格问卷、独立性、聚合成本、退出与恢复测量模板；不代表已有参与者。 |
| 22. Python 依赖锁定 | `requirements-build.in`、`requirements*.lock`、`docs/security/dependency-locking.md` | Python 3.11 固定版本、SHA-256 哈希与受控更新流程 |

## 代码库结构

```text
oin-mvp/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
├── schemas/
│   └── observation.schema.json
├── migrations/
│   └── 001_initial.sql
├── oin/
│   ├── api/              # FastAPI node 与元数据仓储
│   ├── capture/          # HTTP → WARC/WACZ
│   ├── identity/         # Ed25519 keypair / signing
│   ├── observation/      # signed manifest 与 export bundle
│   ├── protocol/         # canonicalization / IDs / hashes
│   ├── schema/           # Pydantic InformationObject Schema v1
│   ├── discovery/        # signed Descriptor / Bootstrap registry / API helpers
│   ├── storage/          # File / S3 adapters
│   ├── timestamp/        # local declaration / RFC 3161 adapter
│   ├── transparency/     # CT-style Merkle log
│   ├── verifier/         # offline verification
│   └── cli.py
├── tests/
│   └── test_protocol.py
├── examples/
│   ├── e2e_conflict.py
│   └── export_bundle_from_node.py
└── docs/
    ├── OIN_MVP_Engineering_Design.md
    ├── Deployment_and_Operations.md
    └── DELIVERY_INDEX.md
```

## 验收摘要

主测试套件已通过 `ruff check` 与 `pytest -q tests`（66 项）；在全新 Python 3.11 环境中按构建锁、开发锁和无依赖本地安装顺序复验通过。Discovery API 的成功、验签失败、过期过滤、超大 Bundle 边界、来源哈希链审计和篡改拒绝已在单元测试中覆盖。网络演示仍依赖对 `https://example.com` 的真实捕获；本环境于 2026-08-21 遇到 TLS 握手超时，故不能将该外部依赖测试计为通过。具体操作及限制见 [Deployment_and_Operations.md](Deployment_and_Operations.md)。

> **实现边界。** 当前捕获引擎为稳定、可验证的 HTTP GET/WARC/WACZ 最小实现。对于高度 JavaScript 化页面，后续应实现 Browsertrix 或 Playwright capture adapter，并继续沿用同一 Observation、签名、时间证据和复制协议；不应改变冲突保存的语义。
