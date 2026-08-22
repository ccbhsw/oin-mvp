# OIN Network Demo：实现边界

本目录是现有 `oin/` MVP 核心模块之上的**可运行网络演示扩展层**。它不修改或替代 `oin.capture`、`oin.observation`、`oin.identity`、`oin.verifier` 的既有核心逻辑；它只将已有的 capture、WARC/WACZ、SHA-256、Ed25519 签名和离线验证能力放入三个可拆分 Operator 的目录与交换边界中。

## 运行边界

当前演示在一个 OIN Core sandbox 内以三个本地目录运行：`operator-a`、`operator-b` 和 `operator-c`。每个目录都拥有独立的 Ed25519 密钥、身份文件、证据存储、导出目录、导入目录及复制记录。演示只证明**LOCAL SIMULATION** 的机制与可移植性，不能证明真实组织、法律主体、资金、地理位置或网络控制面的独立性。

未来拆分到独立机器时，每个 Operator 只需要携带其自身目录，并通过普通文件传输或 HTTP 下载获得对方导出的 artifact。导入程序只读取输入的 export artifact 与公开 descriptor；它不会读取远端 Operator 的内部运行目录、数据库或私钥。

## 证据与交换

网页证据使用既有 MVP 产生的 WARC 或 WACZ。WACZ 是证据归档；导出时使用标准 ZIP 作为普通传输容器，并在其中保留原始 offline bundle 文件：`observation.json`、`raw.wacz`、`observer-public.json` 和可选 `evidence.json`。传输容器不被命名为新的证据标准，也不取代 WARC/WACZ。

签名仅证明某个 Ed25519 signer 对 manifest 的签署及签署后字节未被改动；它不证明网页内容为真、网页作者身份为真，或 capture 时刻由第三方见证。

## 身份与 custody 规则

`original_issuer` 永远来自原始 manifest 的 `observer.observer_id`。一个导入 Operator 只能在本地 replication record 中声明 `importer`、`custodian` 和 `replica`；它不得覆写证据包的原始 signer 或 manifest。每次导入必须先对 artifact 运行独立验证，然后生成 `ACCEPTED` 或 `REJECTED` receipt。

## 查询范围与状态

History View 仅对请求中列出的 `declared_scope` 作出结论。没有匹配时输出 `NO_MATCH_IN_DECLARED_SCOPE`，不得声称不存在全网历史。声明范围内有不可读 Operator 时输出 `UNAVAILABLE_OPERATOR` 或 `PARTIAL_SCOPE`。多个有效且不同的 evidence digest 关联同一 target 时，输出 `CONFLICT` 并保留所有 statement，不自动裁决真伪。

| 机器可读状态 | 含义 |
| --- | --- |
| `VERIFIED` | artifact、manifest、签名、签名者身份与证据绑定均通过。 |
| `INVALID_SIGNATURE` | manifest 或 statement 的 Ed25519 签名不能通过。 |
| `INVALID_BINDING` | artifact digest、payload digest、manifest 或 signer 绑定不一致。 |
| `MALFORMED_ARTIFACT` | WARC/WACZ/ZIP 或所需文件不能被读取。 |
| `TIMEOUT` | capture 或获取对方 export 在限定时间内未完成。 |
| `NOT_FOUND` | 当前 endpoint 或导入集合中没有所请求 artifact。 |
| `UNAVAILABLE_OPERATOR` | 已声明 Operator 在本次查询中无法访问或本地模拟为离线。 |
| `MISSING_REPLICA` | 声称存在的本地 replica 文件缺失。 |
| `CONFLICT` | 同一 target 有两个或以上不同的有效 statement/evidence，均被保留。 |
| `NO_MATCH_IN_DECLARED_SCOPE` | 在列明且可查询的 Operator 范围内没有匹配；不代表全球不存在。 |

## 失败策略

未通过验证的导入不会写入可接受的 custody 存储；会在 importer 的 `replication-records/` 写入 `REJECTED` receipt。对 malformed artifact、错误签名、错误 binding、404、timeout、离线和缺失副本分别保留相应机器可读结果，供测试报告引用。

## 明确不在本演示范围内

本演示没有实现浏览器渲染级采集、认证页面采集、全球 discovery、跨组织访问控制、法律证据可采性、第三方可信时间戳担保、持久对象存储 SLA、共识或 token。HTTP capture 的结论限于所获得的 HTTP 事务及其 WARC/WACZ 表达。
