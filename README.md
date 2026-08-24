# OIN MVP

OIN MVP 是一个**签名、可复制、冲突保留**的公共信息 Observation 网络原型。它记录“哪个 Observer 在何时观察到什么”，而不对网页内容本身作真假判定。

> 此仓库的第一闭环是：公共 URL → HTTP 捕获 → WARC/WACZ → SHA-256 → Ed25519 签名 → Merkle 透明日志 → 多节点复制 → 冲突保留 → API 发现 → 离线验证。

## 当前状态与已知限制
1. **时间戳新鲜度（部分收窄）**：同一内容再次提交必须带 RFC 3161 凭证；首次提交仍可用本地时间声明。只提交一次时，伪造 `captured_at` 仍无法被发现。详见 [docs/limitations.md](docs/limitations.md)。
2. **验证器异构性独立性待完全闭合**：Node.js 验证器由同一执行上下文参考 Python 源码实现，待后续由独立执行者复现确认。
3. **历史测试结论修正**：原全链路测试报告中第 5 步 (REPLICATE / VERIFY) 的 PASS 结论已撤回。日志显示当时未调用验证接口，PASS 仅代表数据同步。

### 测试节点访问

公共测试节点是 HTTP API，用命令行客户端访问，不是网站。macOS 终端、Windows PowerShell、Linux 均可。

浏览器请打开：

- 状态：https://oin.timfi.top/healthz
- 接口文档：https://oin.timfi.top/docs

根路径 https://oin.timfi.top/ 没有页面，会返回 `Not Found`。

安装客户端：

```bash
pip install "git+https://github.com/ccbhsw/oin-mvp.git"
```

然后：

```bash
oin init --endpoint https://oin.timfi.top
oin submit https://example.com
oin verify <object_id>
oin conflicts <object_id>
```

该节点为公共测试环境，不保证稳定性，测试数据可能被重置。请勿用于生产用途。请勿提交违法或未授权抓取的目标。节点只接受 URL 捕获；公开环境关闭 replication pull/push、Observer 注册，以及直接导入 observation。

本地离线核验请使用节点导出的验证包，或阅读 [SAFE_DEMO.md](SAFE_DEMO.md)。连接远程节点使用 `oin init` / `oin submit` / `oin verify <object_id>`。

## 先从安全 Demo 开始

陌生开发者应先阅读 [SECURITY.md](SECURITY.md)、[SECURITY_AUDIT.md](SECURITY_AUDIT.md) 和 [SAFE_DEMO.md](SAFE_DEMO.md)。默认安全 demo **不访问网络**、不要求 API key 或现有私钥，并且只写入项目内的 `demo/data/`。不要将 `docs/innovation/` 中的历史研究脚本作为首次运行路径。

本仓库的网络行为不是隐式的：`pip install` 或 Docker build 会从配置的包/镜像来源下载依赖；`oin submit`、API capture 与 `operator.py capture` 只访问调用者明确提供的公开 HTTP(S) URL；replication pull、RFC 3161 TSA 和 S3 都必须由调用者或部署者显式配置。完整表格见 [SAFE_DEMO.md](SAFE_DEMO.md)。

## 出站网络访问清单

| 触发操作 | 目标 | 发送的数据 | 是否默认执行 |
| --- | --- | --- | --- |
| `pip install` 或 `docker build` | 配置的 Python 包索引或容器镜像仓库 | 依赖/镜像下载请求 | 仅在显式安装或构建时。 |
| `oin submit`、`operator.py capture`、API capture | 调用者明确指定的公开 HTTP(S) URL 与经验证的 redirect | HTTP GET；不会上传本地文件。 | 否。 |
| API replication pull | 调用者明确指定的 peer；默认只允许公开目标 | GET 请求 observation ID 与 export 包。 | 否。 |
| API `tsa_url` | 调用者明确指定且验证为公开的 RFC 3161 TSA | 签名 manifest 的 hash timestamp query。 | 否。 |
| 可选 S3 backend | 部署者显式配置的 bucket / endpoint | 归档字节与对象存储操作。 | 否。 |

`oin verify`、Node verifier、默认 `SAFE_DEMO` identity 初始化以及默认安全容器运行均不发起网络连接。

验证器独立性说明：OIN 目前有 Python 和 Node.js 两套验证器实现，功能层面均已通过测试，但两套实现由同一执行上下文参考 Python 源码完成，尚未经第三方独立设计验证。我们正在寻找未接触过本项目代码的开发者，仅依据协议文档独立复现验证逻辑，以正式闭合此缺口。
请参阅 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解如何参与。


## 网络化快速开始（显式选择）

```bash
cd oin-mvp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-build.lock
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip install "click>=8.0" "requests>=2.31"

# 启动一个仅监听本机的 API 节点
OIN_DATA_DIR=./node-a OIN_NODE_NAME=observer-a python -m uvicorn oin.api.app:app --host 127.0.0.1 --port 8001

# 另开一个终端，连接该节点
oin init --endpoint http://127.0.0.1:8001
oin submit https://example.com
oin verify <object_id>
```

## 三节点开发网络（仅本机开发）

```bash
docker compose up --build -d
curl http://localhost:8001/healthz
curl -X POST http://localhost:8001/v1/captures \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","archive_format":"wacz"}'
```

从第一个节点将全部 Observation 拉至第二、三个节点：

```bash
curl -X POST http://localhost:8002/v1/replication/pull \
  -H 'content-type: application/json' \
  -d '{"peer_url":"http://observer-a:8000"}'

curl -X POST http://localhost:8003/v1/replication/pull \
  -H 'content-type: application/json' \
  -d '{"peer_url":"http://observer-a:8000"}'
```

端口仅绑定 `127.0.0.1`。为使三个 Compose 容器能互相复制，Compose 显式设置 `OIN_ALLOW_PRIVATE_PEERS=1` 和 `OIN_ALLOWED_PRIVATE_PEER_HOSTS=observer-a,observer-b,observer-c`；两者同时存在时才允许这三个内部主机，其他私有地址仍被拒绝。该设置只适合已隔离的本地开发网络。`docker compose down -v` 会删除开发网络的测试历史；不要在实际保留环境中使用该命令。

## 文档与边界

安全策略、审计范围、已修复问题和残余风险见 [SECURITY.md](SECURITY.md) 与 [SECURITY_AUDIT.md](SECURITY_AUDIT.md)。最小隔离运行步骤见 [SAFE_DEMO.md](SAFE_DEMO.md)。默认开发节点没有认证；不要把未开启 `OIN_PUBLIC_LOCKDOWN` 的节点直接暴露到公网。公共测试节点见上文「测试节点访问」。

完整工程与协议设计见 [docs/OIN_MVP_Engineering_Design.md](docs/OIN_MVP_Engineering_Design.md)。部署、独立性、密钥轮换、威胁模型与验收步骤见 [docs/Deployment_and_Operations.md](docs/Deployment_and_Operations.md)。签名描述符与可替换 Bootstrap 发现原型的配置、边界和验证方式见 [docs/architecture/discovery-bootstrap-api.md](docs/architecture/discovery-bootstrap-api.md)。受哈希锁定的依赖安装、更新和审查流程见 [docs/security/dependency-locking.md](docs/security/dependency-locking.md)。

第二阶段生产化前验证的审计、节点独立性、故障恢复、安全、离线验证、性能、连续运行与验收证据位于 [docs/operations/](docs/operations/)。当前结论是 **PARTIAL PASS**：协议闭环已通过本地隔离节点验证，但尚未完成 7 天、跨宿主的长期运行验证；详见 [production-validation-report.md](docs/operations/production-validation-report.md)。

本仓库采用 WARC/WACZ 保存网页归档；签名只证明 Observer 的陈述和存档字节完整性，不证明网页内容为真实事实。RFC 3161 时间戳可通过 API 的 `tsa_url` 选项接入，且始终作为 detached evidence，而不是覆盖 Observer 声明时间。

## API

节点启动后 OpenAPI 页面位于 `http://localhost:8001/docs`。关键资源包括：

| Endpoint | 目的 |
| --- | --- |
| `POST /v1/captures` | 捕获公开 URL 并产生已签名 Observation |
| `POST /v1/takedown` | 提交已签名下架请求；验签失败 403，重复提交 409 |
| `GET /v1/takedown/{id}` | 查询已受理的下架请求 |
| `GET /v1/objects/{id}/observations` | 列出同一 Object 的**全部** Observation |
| `GET /v1/objects/{id}/conflicts` | 返回 divergence / temporal variation 关联 |
| `GET /v1/observations/{id}/proof` | 获取透明日志包含证明 |
| `POST /v1/replication/pull` | 从同伴节点差集拉取并独立验证 |
| `GET /v1/verify/{id}` | 便利的节点侧验证；不替代离线 verifier |
| `GET /v1/discovery/descriptor` | 公开本节点经 Ed25519 签名、短期有效的 Operator Descriptor；需显式配置公开端点。 |
| `GET /v1/discovery/peers` | 返回本节点与本地 Bootstrap Bundle 中通过验签、未过期的候选 Operator；不自动复制。 |

## 开发检查

```bash
ruff check oin network-demo/tools/operator.py network-demo/tests/test_network_demo.py tests/security
pytest -q tests
pytest -q network-demo/tests
python3 tests/performance/benchmark_metadata.py --output /tmp/oin-performance.json
```

许可证：Apache-2.0。
