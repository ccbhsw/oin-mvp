# OIN Local Network Demo

本目录把仓库已有的 HTTP capture、WARC/WACZ、SHA-256、Ed25519 和离线验证核心组合成一条可运行的多 Operator 链路：

> `Capture → Evidence → Sign → Operator A export → Operator B import/verify → A evidence loss → B recovery source → Operator C import/verify`。

它是**LOCAL SIMULATION**：A、B、C 有不同的密钥和数据根目录，但仍在同一 sandbox、同一操作者和同一文件系统内运行。它证明可移植 artifact、验证和 custody 机制可以运行；不证明真实组织、地理、法律、资金或网络独立性。

## 前置条件

在仓库根目录使用 Python 3.11+、Node.js 22+ 和现有项目依赖。首次安装可运行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-build.lock
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
```

所有演示命令从仓库根目录执行：

```bash
cd /home/ubuntu/oin-mvp
```

## 快速运行

使用一个不纳入版本控制的运行根目录。下列命令把每个 Operator 放到独立路径；实际部署时，这些路径可分别位于不同机器和组织。

```bash
RUN=/tmp/oin-network-demo
A=$RUN/operator-a
B=$RUN/operator-b
C=$RUN/operator-c
rm -rf "$RUN"

python3 network-demo/tools/operator.py init "$A" --operator-id did:oin-local:operator-a
python3 network-demo/tools/operator.py init "$B" --operator-id did:oin-local:operator-b
python3 network-demo/tools/operator.py init "$C" --operator-id did:oin-local:operator-c
```

### 1. Operator A 真实 capture、WACZ 打包和离线验证

```bash
python3 network-demo/tools/operator.py capture "$A" https://example.com --archive-format wacz
```

命令输出中的 `observation_id` 是后续 export 所需的值。将它复制为 shell 变量，例如：

```bash
OBS='oin:observation:sha256:把上一步输出的值粘贴到这里'
python3 network-demo/tools/operator.py export "$A" "$OBS" --output "$RUN/a-export.zip"
```

A 的 evidence bundle 位于：

```text
$A/evidence/<observation-id-安全文件名>/
├── observation.json
├── raw.wacz
├── observer-public.json
└── evidence.json
```

`raw.wacz` 内含 WARC response、页面索引和 `datapackage.json` resource digest。`operator.py verify` 不访问任何 Operator 服务，只使用上述 bundle：

```bash
python3 network-demo/tools/operator.py verify "$A/evidence/<observation-id-安全文件名>"
```

### 2. B 通过 portable export 导入并保留 A 的原始 issuer

```bash
python3 network-demo/tools/operator.py import "$B" "$RUN/a-export.zip"
```

导入程序在复制前验证：outer ZIP、export signer、descriptor 与 exporter key、bundle 文件 digest、manifest、Ed25519 observation signature、WACZ resource digest、WARC response payload hash、对象 ID 和 URL canonicalization。成功后，B 写入自己的 `replication-records/*.json`，其中 `original_issuer` 仍为 A 的 observer ID；B 只以 `importer`、`custodian` 和 `replica` 出现。

### 3. A 离线、B 保留有效副本、A 从 B 恢复

B 可以重新签署一个由 B 输出的 transport export，同时不改写原始 evidence 的 signer：

```bash
python3 network-demo/tools/operator.py export "$B" "$OBS" --output "$RUN/b-export.zip"
python3 network-demo/tools/operator.py availability "$A" offline

python3 network-demo/tools/operator.py history https://example.com \
  --operator did:oin-local:operator-a="$A" \
  --operator did:oin-local:operator-b="$B"
```

此时结果应包含 A 的 `UNAVAILABLE_OPERATOR` 与 B 的有效证据，汇总状态为 `PARTIAL_SCOPE`。为演练恢复，可在确认 A 的本地 evidence 已不可用后从 B export 恢复：

```bash
python3 network-demo/tools/operator.py recover "$A" "$RUN/b-export.zip"
python3 network-demo/tools/operator.py availability "$A" online
```

`recover` 会先运行 import 级验证，再写入 `recovery/recovery-*.json`。恢复不是对网页内容作事实判断；它只恢复经验证的 artifact 与 custody 记录。

### 4. Operator C 加入网络

```bash
python3 network-demo/tools/operator.py import "$C" "$RUN/b-export.zip"
```

C 无需接触 A 的运行目录或私钥，只接收 B 提供的 portable ZIP。其本地 receipt 会保留 A 的 `original_issuer`、B 的 source export digest 和 C 的 replica custody。

### 5. History View、范围与冲突

History View 必须显式声明查询范围：

```bash
python3 network-demo/tools/operator.py history https://example.com \
  --operator did:oin-local:operator-a="$A" \
  --operator did:oin-local:operator-b="$B" \
  --operator did:oin-local:operator-c="$C"
```

| 状态 | 严格含义 |
| --- | --- |
| `VERIFIED` | 所声明范围中存在至少一条完整验证通过的 evidence statement，且没有不同有效 digest。 |
| `PARTIAL_SCOPE` | 范围中至少一个 Operator 不可用，或有记录但无可验证副本。 |
| `NO_MATCH_IN_DECLARED_SCOPE` | 已查询的范围中没有匹配；不代表全球没有历史。 |
| `UNAVAILABLE_OPERATOR` | 已声明 Operator 在本次查询中不可访问。 |
| `CONFLICT` | 同一 target 有不同的有效 evidence artifact digest；系统保留全部记录，不判定事实真伪。 |

为产生一个新的独立 statement，可让 C 再次 capture 相同 target：

```bash
python3 network-demo/tools/operator.py capture "$C" https://example.com --archive-format wacz
```

随后三 Operator 的 History View 会保留 A 证据的多个 custody copy 和 C 的新 evidence，不将其中任何一个自动覆盖。

## Python 与 Node.js 独立验证

Node verifier 不导入 Python `oin` 包或 Python verifier 代码。它独立处理 ZIP/WACZ、WARC、SHA-256、canonical JSON、Ed25519、observation identity 及 export signer binding：

```bash
node network-demo/tools/node_verifier.mjs verify-bundle "$B/evidence/<observation-id-安全文件名>"
node network-demo/tools/node_verifier.mjs verify-export "$RUN/b-export.zip"
```

Node 也可用自身的 crypto 和 ZIP writer 生成 transport export；Python Operator 可以导入并验证该文件：

```bash
node network-demo/tools/node_verifier.mjs create-export \
  "$C/evidence/<observation-id-安全文件名>" \
  "$C/descriptors/operator-descriptor.json" \
  "$C/keys/observer-private.pem" \
  "$C/keys/observer-public.json" \
  "$RUN/node-created-export.zip"

python3 network-demo/tools/operator.py import "$B" "$RUN/node-created-export.zip"
```

## 运行测试

```bash
python3 -m ruff check network-demo/tools/operator.py network-demo/tests/test_network_demo.py
node --check network-demo/tools/node_verifier.mjs
python3 -m pytest -q network-demo/tests
python3 -m pytest -q tests
```

## 目录与密钥安全

`network-demo/operator-a`、`operator-b`、`operator-c` 是空目录骨架。真实运行 material 写入 `network-demo/run-artifacts/` 或用户选择的 `RUN` 目录，且被 `.gitignore` 排除。不要提交 `keys/observer-private.pem`、真实 evidence 或 export 包；私钥权限由初始化工具设置为仅 owner 可读。

## 已知限制

当前 capture 是受大小、重定向和公开网络地址限制保护的 HTTP GET，不是浏览器渲染级归档，也不会捕获登录页面、客户端脚本行为、视频流或受认证内容。当前 timestamp 是 signer 的 local declaration，不是第三方可信时间戳。当前 file transport 演示可替换为 HTTPS 对象存储或下载 endpoint，但不实现全球 discovery、访问控制、长期保存 SLA、法律可采性、组织独立性或共识。

详细模型见 [ARCHITECTURE.md](ARCHITECTURE.md)，实际测试证据见 [TEST_REPORT.md](TEST_REPORT.md)。
