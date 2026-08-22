# Discovery 现实检验：引导节点还是纯 DHT？

> 本文为架构研究草案，最终协议需经威胁建模和 Operator 审查。

## 现状

OIN 目前有按 Object、Observation、历史和冲突查询的 API“发现”，但没有**节点发现**。复制要求调用者显式提供 peer URL，并依据 `/v1/replication/ids` 维护清单。因此新节点不知道有哪些 Operator，网络仍依赖配置文件、硬编码地址或人工分发；API 查询不能替代 bootstrap。

## 纯 DHT

Kademlia 以 XOR 距离和 `FIND_NODE/FIND_VALUE` 建立分布式路由。BitTorrent BEP 5 证明无中心 tracker 的种子查找可运行；IPFS 也采用 Kademlia 风格路由，但仍把 bootstrap peers 视为保持路由表健康的必要机制。[1] [2] 纯 DHT 的优点是无单一目录、开放加入和较强可用性；缺点是新节点仍须初始入口，Sybil 可占据路由空间，恶意节点可拒绝服务或返回假端点。DHT 解决“去哪里问”，不解决“谁可信”。

对 OIN，DHT 还会放大 Operator 枚举、流量和隐私风险。Operator 是承担归档、复制和法律响应的责任主体，不是匿名块存储；把完整内容索引或个人信息放入 DHT，会使撤回、限速和合规隔离更困难。

## 签名描述符与 relay

建议定义签名 `Operator Descriptor`，包含 operator_id、公钥、端点、协议版本、能力、地区、更新时间和过期时间。客户端先验签描述符，再验证 Observation 签名、归档哈希和 Merkle 证据。它兼容现有 HTTPS pull/push、易缓存和审计；代价是 bootstrap 仍是入口瓶颈，若所有客户端只配置同一批节点，入口会事实中心化。

ActivityPub 的经验是联邦而非全球 DHT：W3C 规范定义 server-to-server 投递、Actor 的 inbox/outbox 和 shared inbox。[3] OIN 可设只传播描述符、checkpoint 摘要和可验证索引的 relay，但 relay 可能遗漏、过滤或集中流量，不能成为唯一来源。

| 方案 | 优点 | 风险 | 适配 |
| --- | --- | --- | --- |
| 纯 Kademlia | 开放、无单一目录 | bootstrap、Sybil、投毒 | 中 |
| bootstrap+签名描述符 | 简单、可验证 | 入口治理 | 高 |
| 联邦 relay | 传播快、可控 | 过滤、集中 | 中高 |
| 混合 | 可替换、韧性高 | 复杂度上升 | 最高 |

## 推荐与影响

推荐分阶段混合：先用多 bootstrap 发布签名描述符，再增加可选 relay，最后评估受限 DHT；DHT 只存短期端点和内容寻址元数据，不存原始归档或个人信息。客户端应能手工导入 bundle，并记录端点来源。Schema 需增加描述符过期、撤销、能力、来源证明和发现失败事件。目标是**可替换发现层**，而非假装无需初始信任。

## References

[1]: https://www.bittorrent.org/beps/bep_0005.html "BEP 5: DHT Protocol"
[2]: https://libp2p.io/docs/kademlia-dht/ "libp2p Kademlia DHT"
[3]: https://www.w3.org/TR/activitypub/ "W3C ActivityPub"
[4]: https://atproto.com/specs/architecture "AT Protocol Architecture"
