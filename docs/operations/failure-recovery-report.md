# OIN MVP 第二阶段：Failure and Recovery Report

**环境：** 同一 sandbox host 的 A/B/C 隔离 API 进程；此报告不声称跨宿主独立性。
**结果：** 本报告内列出的隔离进程故障和复制恢复测试通过。

## 已执行场景

### 1. A 捕获并复制至 B/C

Observer A 对 `https://example.com` 进行了真实公开 HTTPS 捕获，生成 Observation `oin:observation:sha256:e13641c93cd1b197f511bfd512402bc3d186e2e757f49010f2647ba6b62332c9`。其 raw content hash 为 `sha256:ff67a9d764d6a2367a187734e697f6a53217db9a21c101d410a113ca871a299d`，archive hash 为 `sha256:dd19d49b2611e9387d12bf85b9950cab8bd15e8acdb94873c8578712fa9bdb42`。B 与 C 分别通过 HTTP pull 返回 `created`。

### 2. 人工 Conflict Preservation

B 使用其独立 Ed25519 私钥对同一 Object 导入不同的原始 HTML 内容。系统产生 `observation_divergence`，`is_conflict_candidate=true`，没有覆盖或删除 A 的 Observation。C 从 B 同步后，该 Object 的 Observation 数为 2。

### 3. A 离线、B/C 继续工作

停止 A 后，B 对 `https://www.iana.org/domains/example` 创建新的 Observation，C 从 B 执行 pull。在结果中，C 接收到了 1 条 `created` Observation，同时对已存在记录返回 `already_present`。这表明重复同步不会覆盖已有 Observation，且 B/C 可在 A 离线期间继续生成与复制历史。

### 4. A 恢复后差集同步

重新启动 A 后，A 从 B pull，结果包含 2 条 `created` 和 1 条 `already_present`。A 因而恢复了离线期间 B 产生的历史以及 B 的冲突 Observation，而没有重写已存在的 A Observation。

### 5. 删除 A 的本地数据库后从 C 恢复

停止 A，删除 `/tmp/oin-stage2/a/oin.db`，保留 A 的独立 key 和本地文件根目录，然后重新启动 A。A 从 C pull 后返回 3 条 `created`、0 条 `already_present`。B 在 A 离线期间生成的新 Observation 可由 A 查询到，证明 metadata database 丢失后可由复制 peer 重建 Observation history。

### 6. B 或 C 分别离线

停止 B 时，A 与 C 的 `/healthz` 均返回 `{"status":"ok"}`。恢复 B 后停止 C，A 与 B 的 `/healthz` 均返回 `{"status":"ok"}`。随后已恢复 C，最终三节点健康。

## 结论与边界

| 要求 | 判定 | 证据边界 |
| --- | --- | --- |
| A 离线后 B/C 可继续运行 | VERIFIED | 同一宿主的独立进程测试。 |
| 已复制 A 数据在 B/C 可用 | VERIFIED | B/C 复制并保持 Observation。 |
| A 恢复后可差集同步 | VERIFIED | A 从 B 收到缺失 Observation。 |
| 删除 A SQLite 数据后可恢复 | VERIFIED | A 从 C 重建 3 条 Observation metadata。 |
| B/C 分别离线不影响其他节点健康 | VERIFIED | 健康端点实际返回 ok。 |
| 真实跨网络、跨 provider 故障恢复 | NOT VERIFIED | 需要长期独立宿主。 |
| PostgreSQL backup/restore | NOT VERIFIED | 当前为 SQLite 本地恢复测试。 |

> FileStorage 中已有 archive 的恢复写入是幂等写入；本测试验证了可通过 peer 重新建库，不替代完整 storage 删除后的恢复或 PostgreSQL 备份恢复测试。
