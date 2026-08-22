# Discovery Bootstrap API 原型

## 目的与边界

本实现将已有的 `OperatorDescriptor` 和 `BootstrapRegistry` 接入 Observer 节点，提供一个**可替换、只读、静态配置驱动**的节点发现入口。它解决的是“新节点可以从多个独立入口获得哪些候选 Operator 的可验证描述符”，而不是全局搜索、内容索引、声誉评估或真相裁决。

> 描述符验签只能证明持有对应 Ed25519 私钥的一方发布了该描述符；它**不证明**端点可用、Operator 独立、保存能力充足或其观察内容为真。

该选择遵循现有研究的分阶段建议：以多 Bootstrap 和短期签名描述符作为可运行起点，而不假装纯 DHT 可以消除初始信任与 Sybil 风险。[1] [2]

| 端点 | 行为 | 安全属性 |
| --- | --- | --- |
| `GET /v1/discovery/descriptor` | 返回本节点即时签名的短期 Operator Descriptor | 无显式公共端点配置时返回 `503`，避免发布猜测或私有地址。 |
| `GET /v1/discovery/peers` | 返回本节点描述符与本地 Bootstrap 文件中通过验签、未过期的描述符 | 只读；不会抓取远程 URL，也不会替调用者建立复制关系；首次观察到某个 Bundle 哈希时会写入本地审计记录。 |

## 显式配置

节点运营者必须声明自己希望公开的端点。服务不会依据监听地址、请求头或容器网络猜测公开 URL。

```bash
export OIN_DISCOVERY_ENDPOINTS='https://node-a.example.org,https://mirror-a.example.org'
export OIN_DISCOVERY_REGION='ZZ'
export OIN_DISCOVERY_CAPABILITIES='capture,replication,verification'
export OIN_DISCOVERY_DESCRIPTOR_TTL_SECONDS='86400'
# 可选：经人工审阅、仅含公开描述符的静态 Bundle。
export OIN_DISCOVERY_BOOTSTRAP_PATH='./data/discovery/bootstrap.json'
# 可选：本地、节点签名的 Bundle 导入审计日志；默认位于 data/discovery/。
export OIN_DISCOVERY_AUDIT_PATH='./data/discovery/bootstrap-audit.jsonl'
oin serve --port 8001
```

`OIN_DISCOVERY_DESCRIPTOR_TTL_SECONDS` 必须在 **300 秒至 604,800 秒**之间。`ZZ` 仅表示运营者未声明地区；它不是地理独立性或法域合规的证明。静态 Bundle 使用 `BootstrapRegistry.export_bundle()` 的 JSON 结构，并可由任意独立镜像分发。

## 验证与输入边界

| 控制项 | 当前规则 | 解决的风险 |
| --- | --- | --- |
| 描述符签名 | 每条描述符必须通过 Ed25519 验签，且 `operator_id` 必须由其公钥确定性派生 | 伪造描述符、身份混淆。 |
| 有效期 | `expires_at` 必须晚于 `updated_at`；响应仅保留未过期条目 | 无限期传播过期端点。 |
| Bundle 大小 | 最大 262,144 字节、最多 128 条描述符 | 元数据膨胀与解析型拒绝服务。 |
| 单条限制 | 最多 8 个端点、32 个 capability；端点最多 2,048 字符 | 单一描述符资源消耗。 |
| 网络动作 | 发现端点不访问远程端点，不主动拉取、不自动复制 | SSRF、意外流量与隐式信任。 |
| 配置失败 | 缺失或无效公开元数据返回 `503` | 将错误配置误包装成可用发现记录。 |
| 来源审计 | 仅在 Bundle 哈希改变时追加本地 JSONL 记录；记录包含 Bundle SHA-256、接纳/拒绝数、活跃数、前序事件哈希与节点 Ed25519 签名 | 让运营者事后验证本地配置来源和导入结果，避免每次只读请求重复写入。 |
| 审计完整性 | 加载时逐条验证事件 ID、签名和哈希链；最多 512 条事件 | 发现本地审计篡改、截断或无限增长。 |

## 非目标与后续演进

本原型没有在网络中自动导入 Bundle，也没有基于发现结果自动发起 replication pull。这样可以把“描述符是否密码学有效”和“是否信任其作为复制对象”分开。Operator 或客户端仍须显式决定来源与复制策略。

未来需要先进行威胁建模和多 Operator 实验，再评估来源审计、Bundle 签名者、relay、受限 DHT 和抗 Sybil 措施。不得将原始归档、隐私数据或完整内容索引放入发现层。联邦系统的实践表明，服务间传播可以使用显式端点而非唯一全球目录，但入口选择与治理仍是独立问题。[3]

## 验证命令

```bash
ruff check oin network-demo/tools/operator.py network-demo/tests/test_network_demo.py tests
pytest -q tests
pytest -q network-demo/tests
```

本轮在受控环境中通过了 `ruff`、主测试套件（66 项）和 Discovery 相关测试（32 项）。Bootstrap 审计测试覆盖了有效来源记录、无效描述符计数、同一 Bundle 去重与本地审计篡改拒绝。网络演示套件依赖对 `https://example.com` 的真实 TLS 捕获；本环境于 2026-08-21 出现 TLS 握手超时，因此该外部依赖验证被标记为未完成，而不是实现通过。

## References

[1]: ../research/discovery_reality_check.md "OIN Discovery 现实检验"
[2]: https://www.bittorrent.org/beps/bep_0005.html "BEP 5: DHT Protocol"
[3]: https://www.w3.org/TR/activitypub/ "W3C ActivityPub"
