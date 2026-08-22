# OIN MVP 第二阶段：Performance Report

**范围：** 本地 SQLite metadata benchmark；单进程、FileStorage 未计入、无网络、无 S3、无 PostgreSQL、无 Docker。
**重要边界：** 该结果衡量当前 `Repository.save_observation()` 的本地 ORM 写入、Object history 查询和 replication ID 列表生成，不是公网 capture、WARC/WACZ 生成、归档上传或跨节点复制吞吐声明。

## 实测结果

| Observation records | Ingest time | Ingest rate | Object history query | ID list query | SQLite DB size | Peak RSS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.333 s | 300.631/s | 0.005 s | 0.001 s | 675,840 B | 68,468 KiB |
| 1,000 | 3.207 s | 311.825/s | 0.034 s | 0.005 s | 5,365,760 B | 79,712 KiB |
| 10,000 | 32.018 s | 312.322/s | 0.419 s | 0.039 s | 52,744,192 B | 169,736 KiB |
| 100,000 | 331.607 s | 301.562/s | 9.264 s | 0.378 s | 527,024,128 B | 1,037,140 KiB |

基准命令为：

```bash
python3 tests/performance/benchmark_metadata.py --output /tmp/oin-performance.json
```

## 结果解释

修复 `observations(observer_id, raw_content_hash)` 的错误唯一约束后，同一 Observer 可以在不同 capture time 保存相同 raw content 的多个 Observation。该修复是 OIN 历史完整性所必需的；基准也确认 100,000 条相同内容、不同时间的 Observation 可以写入。

第一个明显瓶颈是**同一 Object 的完整 Observation history 物化**。在 100,000 条记录时，`observations_for_object()` 将全部 ORM 对象加载到内存，查询耗时约 9.26 秒，进程 peak RSS 超过约 1 GiB。OID list 查询仍在约 0.38 秒，单条 ingest 保持约 302/s，但 100,000 条同 Object 的无分页 history API 不适合生产交互查询。

## 建议

不应为此次 benchmark 重写 OIN 协议或删除历史。下一步应在不改变“所有 Observation 仍可获取”的原则下，给 Object history API 增加明确的 cursor/page size，并提供完整导出端点；数据库层保留 `(object_id, captured_at)` 索引。生产规模应迁移至 PostgreSQL 并重新测量，且单独测量 archive storage、WACZ 大小、S3 上传和 replication 网络延迟。
