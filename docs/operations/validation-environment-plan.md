# OIN MVP 第二阶段：验证环境计划

## 目标与边界

第二阶段将以现有协议和数据模型为基线，不重写 OIN 架构。验证分为两个严格区分的层次：当前工作环境中的**隔离进程可靠性测试**，以及未来在独立长期宿主上的**持续运行验证**。前者可以验证密钥隔离、数据库隔离、文件系统隔离、复制、故障恢复、篡改拒绝和离线验证；后者才可以对 7 天持续运行、网络中断、不同网络和宿主独立性作出真实陈述。

> 不能将同一宿主中的三个进程描述为三个独立组织或三个独立云节点。其唯一可证明的独立性属性是独立进程、独立配置、独立 SQLite 数据库、独立目录、独立 archive storage 和独立 Ed25519 密钥。

## 当前可执行的隔离进程环境

验证网络使用 Observer A、B、C 三个 API 进程，每个进程拥有独立根目录 `/tmp/oin-stage2/{a,b,c}`、独立 `OIN_NODE_NAME`、SQLite 文件、私钥、透明日志目录和 archive 目录。节点只通过 HTTP API 复制；测试不直接读取其他节点数据库。每个节点将建立并注册其 Independence Profile。

| Observer | 进程端口 | 数据根目录 | 数据库 | Archive storage | 明确可观察的独立性 |
| --- | --- | --- | --- | --- | --- |
| A | 8201 | `/tmp/oin-stage2/a` | `a/oin.db` | `a/artifacts` | 独立进程、配置、文件系统、SQLite、key |
| B | 8202 | `/tmp/oin-stage2/b` | `b/oin.db` | `b/artifacts` | 独立进程、配置、文件系统、SQLite、key |
| C | 8203 | `/tmp/oin-stage2/c` | `c/oin.db` | `c/artifacts` | 独立进程、配置、文件系统、SQLite、key |

此层验证不会声称不同 provider、region、machine、operator 或 network。它将这些属性记录为 `same sandbox host` / `not independently verified`。

## 长期运行验证的必要环境

满足附件中“7 天连续”和“真正隔离”验收项，至少需要三台长期在线的 Linux 宿主或三套彼此隔离的容器宿主。每台必须拥有独立持久卷、私钥、数据库、对象存储凭据、日志目录、定时任务和网络身份；数据库与 archive storage 不能由三节点共用。生产化部署说明已保留在 `docs/Deployment_and_Operations.md`。

| 方案 | 能验证的结论 | 代价与限制 | 适用性 |
| --- | --- | --- | --- |
| 当前隔离进程测试 | 协议、复制、故障、篡改、离线验证和相同宿主内的恢复 | 不能证明跨宿主独立性或连续 7 天运行 | 立即执行的可靠性与安全测试 |
| 三个长期独立 Linux 宿主 | 7 天连续运行、独立数据边界、真实网络中断和节点消失恢复 | 需要持久服务器、对象存储与访问权限 | Production Validation PASS 的必要条件 |

## 运行测试的 URL 集

持续运行阶段使用 20 个稳定公开 HTTPS URL。当前隔离进程阶段仅选择少量公开 URL 验证真实捕获，以避免将短期测试误称为持续 crawl。URL 集与每次 capture 结果会写入 `docs/operations/continuous-run-report.md`；在未完成 7 天前，该报告会明确标记为 `NOT VERIFIED`。

## 安全前置条件

当前 capture API 存在 SSRF、无限响应体和未认证 API 的 P1 风险。第二阶段将先建立失败测试，再以最小修正方式阻断 localhost、私网、link-local、metadata endpoint、非 HTTP(S) scheme 和 redirect 到被禁止地址。未完成这些修正前，验证网络只能绑定本地回环地址，不能对不可信互联网开放。
