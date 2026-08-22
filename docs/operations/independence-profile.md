# OIN MVP 第二阶段：Observer Independence Profile

**验证环境：** 同一受控 sandbox host 上的三进程隔离测试。
**重要限制：** 本文件记录可观察到的部署属性，不证明三个节点属于不同组织、云服务商、物理机器、地区或网络自治域。

| 属性 | Observer A | Observer B | Observer C |
| --- | --- | --- | --- |
| Observer ID | `oin:observer:sha256:37fb12cb1e704b20ff5aace496861b6e53aca5d0b83016e3960282910b8998d2` | `oin:observer:sha256:7e1ef8e741ff722ecb071f00723effb6a346c0ecb9cdf78e317a915251f3b538` | `oin:observer:sha256:c58b70cb1e55b8b8d786fa87c46ed7f7402e3864d0e7cb9aac1b1e0885d2c94f` |
| Operator | `stage2-local-test-harness` | `stage2-local-test-harness` | `stage2-local-test-harness` |
| Machine | `shared-sandbox-host` | `shared-sandbox-host` | `shared-sandbox-host` |
| Provider | `sandbox` | `sandbox` | `sandbox` |
| Region | `not-independently-verified` | `not-independently-verified` | `not-independently-verified` |
| Network | loopback-only | loopback-only | loopback-only |
| API process | `127.0.0.1:8201` | `127.0.0.1:8202` | `127.0.0.1:8203` |
| Deployment ID | `stage2-a` | `stage2-b` | `stage2-c` |
| Database | SQLite `/tmp/oin-stage2/a/oin.db` | SQLite `/tmp/oin-stage2/b/oin.db` | SQLite `/tmp/oin-stage2/c/oin.db` |
| Archive storage | FileStorage `/tmp/oin-stage2/a/artifacts` | FileStorage `/tmp/oin-stage2/b/artifacts` | FileStorage `/tmp/oin-stage2/c/artifacts` |
| Observer private key | independent PEM in `a/keys` | independent PEM in `b/keys` | independent PEM in `c/keys` |
| Transparency log | `oin-log-observer-a` | `oin-log-observer-b` | `oin-log-observer-c` |
| Software version | `oin-mvp/0.1.0` | `oin-mvp/0.1.0` | `oin-mvp/0.1.0` |

## Verified statements

A、B、C 运行在不同 API 进程，使用不同 `OIN_DATA_DIR`、独立 SQLite 文件、独立 archive 根目录、独立 Ed25519 Observer keypair 和独立透明日志 key。三个 Observer ID 在启动后经节点 API 读取并确认互不相同。节点之间的 Observation 同步仅通过 HTTP replication API 执行；测试流程不通过共享数据库读取或写入其他节点的数据。

## Non-verified statements

本环境不能验证操作员独立性、provider 独立性、物理宿主独立性、地区独立性、自治网络独立性或故障域独立性。该环境仅适合验证 OIN 协议在隔离进程与隔离持久目录条件下的可靠性，不可作为“3 个独立组织 Observer 已运行”的证据。
