# 身份轮换提案：公钥丢失后的恢复与迁移

> 这是身份锚定模型的**红灯决策**，最终变更须人类审查；研究和 Schema 编码不应暂停。

## 当前问题

OIN MVP 用 Ed25519 公钥哈希派生 `observer_id`，Observation 直接绑定该公钥；无 DID、域名绑定或恢复根。丢失私钥不会使历史签名失效，旧公钥仍可验签；但新公钥无法证明继承旧身份，历史记录遂成为“密码学有效、治理上孤儿”的数据。若允许任何新 key 自称继承，攻击者也能伪造连续性。现有设计的旧/新 key 交叉签署 rotation statement 只覆盖正常轮换。

## 方案 A：DID 文档

可将稳定的 `did:oin:`、`did:web:` 或外部 DID 作为 subject，把 Ed25519 key 放入 DID Document 的 `verificationMethod`，并登记旧 observer_id、端点和 key-status。W3C DID Core 定义 DID Document、verification methods 和 services，但更新授权由具体 method 决定；`did:key` 直接由公钥派生，换 key 就换 DID，不适合作为稳定轮换身份。[1] [2]

DID 的优点是历史关联、撤销和端点表达统一；`did:web` 易运维，却引入域名、DNS、TLS 和宿主服务信任根；自定义 `did:oin` 可把更新写入透明日志，但需承担解析、缓存、撤销与离线快照复杂度。不可逆影响是验证器必须理解 DID method，且域名控制权可能成为身份连续性的一部分；既有 Observation 不能被新签名覆盖。

## 方案 B：多签/社会恢复

保留原生 Ed25519，并预登记 3-of-5 guardian。guardian 对“新 key 继承旧 observer_id”签署声明，写入旧新公钥、阈值、原因、时间和有效区间，再入透明日志。这借鉴以太坊账户抽象的可编程验证与 guardian 恢复思路，但不应照搬链上账户模型。[3]

多签不依赖域名，适合由不同法域、托管方或机构成员共同控制；代价是 guardian 成为治理根，存在串通、丢失、胁迫和社会工程风险。恢复声明一旦公开就是历史解释的一部分，不能物理删除；只能追加争议、撤销或更高优先级事件。验证器须区分数学验签、阈值满足和当前信任策略。

## 其他方案与倾向

DNSSEC、TLS 或 `/.well-known` 可证明域名控制，但不证明组织未变更，只应作附加证据。我的倾向是**不废弃 Ed25519，新增稳定 subject 层**：正常轮换继续交叉签名；机构可选 `did:web`/`did:oin`；高价值 Operator 再启用 3-of-5 恢复；DNS 仅作佐证。Schema 可预留 `subject_id`、`key_status`、`rotation_statement`、`recovery_statement`，但审查前不得改变 `observer_id` 含义。

## References

[1]: https://www.w3.org/TR/did-1.0/ "W3C Decentralized Identifiers v1.0"
[2]: https://w3c-ccg.github.io/did-key-spec/ "The did:key Method"
[3]: https://eips.ethereum.org/EIPS/eip-4337 "ERC-4337 Account Abstraction"
[4]: https://datatracker.ietf.org/doc/html/rfc8032 "RFC 8032 EdDSA"
