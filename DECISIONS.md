# OIN 已做决策

当前 Schema 采用 **Pydantic v2**，并以显式字段校验和可序列化模型作为实现基线。Discovery 原型采用签名 Operator Descriptor 与多 bootstrap 的起点，推荐逐步扩展为可选 relay、再评估受限 DHT 的混合方案。描述符使用 Ed25519 公钥、确定性 operator_id、能力、端点、协议版本和有效期；未经验签的描述符不得进入本地注册表。节点 Discovery API 仅发布本地显式配置和静态 Bundle 中已验签、未过期的描述符，不自动抓取或复制；详见 [ADR-0001](docs/decisions/ADR-0001-discovery-bootstrap-api.md)。身份轮换不在本阶段改变既有 observer_id 含义，相关恢复方案保留为红灯决策。
