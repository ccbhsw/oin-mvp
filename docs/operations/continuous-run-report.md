# OIN MVP 第二阶段：Continuous Run Report

**当前结论：** NOT VERIFIED for 7-day continuous operation.
**原因：** 当前验证环境是会休眠的 sandbox，未提供三个独立长期宿主、Docker runtime 或连续 7 天运行窗口。不能把短期三进程试验描述为连续运行验证。

## 本阶段已执行的短时真实运行证据

A、B、C 在独立数据根目录和独立 API 进程中启动。A 真实捕获 `https://example.com`；B 在 A 离线期间真实捕获 `https://www.iana.org/domains/example`；节点之间完成 HTTP replication。A 的数据库删除后可从 C 重建历史 metadata。具体证据见 `failure-recovery-report.md`。

| 指标 | 当前实测 | 说明 |
| --- | --- | --- |
| 固定 URL 集合 | 2 个真实 URL | 仅用于短时闭环，不等同于要求中的 20–50 URL。 |
| 真实 capture | 2 次以上 | A 与 B 均成功生成 WACZ Observation。 |
| 复制 | A→B、A→C、B→C、B→A、C→A | 已在故障与恢复流程中实际执行。 |
| signing failure | 0 | 本次短时样本未出现。 |
| verification failure | 0（正常包） | 断开 Observer 后离线验证为 VALID。 |
| archive generation failure | 0 | 本次短时样本未出现。 |
| HTTP errors / timeout | 0 | 样本不足，不能推导长期成功率。 |
| storage failure | 0 | FileStorage 测试范围内；S3 未实测。 |

## 7 天运行计划

长期验证必须在三个长期在线、互相隔离的宿主上执行。每个节点应使用独立 key、database、archive storage、日志目录、对象存储凭据与定时任务。每个节点每天按固定集合独立捕获 20 个稳定公开 HTTPS URL，并记录：URL、HTTP 状态、headers、redirect chain、raw/archive hash、Observation ID、Observer ID、signature、耗时、错误分类与 replication 状态。

建议的最低频率是每节点每 URL 每 6 小时一次。对于 20 URL、3 节点、7 天，该计划将产生 6,720 次预定 capture 尝试。报告应在连续周期结束后补充成功率、timeout、redirect、archive/signing/replication/verification/storage failure 计数，并保留原始 operation log。

## 通过条件

只有在三个长期节点实际运行满 7 天、没有无法解释的 Observation 丢失、所有归档均可抽样验证、节点故障恢复经真实网络验证后，才可将本报告从 `NOT VERIFIED` 改为 `VERIFIED`。
