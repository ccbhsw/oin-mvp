# OIN 项目状态

## 当前状态概述

OIN MVP 已形成从公开 URL 捕获、WARC/WACZ 封装、SHA-256 内容与归档哈希、Ed25519 签名、Merkle 透明日志、多 Operator 复制、冲突保留到离线验证的第一条协议闭环。当前实现能够证明“某个 Observer 在某时刻签署了某份观察和归档字节”，但不裁决观察内容的事实真伪，也尚未解决开放网络的节点发现、稳定身份恢复和可持续激励问题。

当前版本仍属于生产化前验证阶段。仓库现有复制流程依赖调用者显式配置 peer URL；API 查询发现与网络节点发现不是同一能力。默认 API 没有认证和限流，不应直接暴露到公网。

## 已完成的工作

| 工作项 | 状态 | 说明 |
| --- | --- | --- |
| WARC/WACZ 捕获 | 已完成 | 支持公开 URL 捕获与归档哈希校验 |
| Ed25519 签名 | 已完成 | Observation manifest 可离线验签 |
| 多 Operator 复制 | 已完成 | 入站副本独立验证后写入本地日志 |
| 冲突保留 | 已完成 | 保留 divergence、temporal variation 等观察差异，不自动裁决 |
| Merkle 透明日志 | 已完成 MVP | 支持 checkpoint 与 inclusion proof 原型 |
| 离线验证器 | 已完成 | 可在不访问 OIN 网站的情况下验证归档、哈希、签名和证据 |
| InformationObject Schema v1 | 已完成 | Pydantic v2 严格模型、JSON Schema 输出、签名与恶意超大字段测试已在 Phase 1 检查点提交。 |
| 签名 Operator Descriptor | 已完成原型 | Ed25519 自验证描述符、有效期、能力与端点约束已实现。 |
| 静态 Bootstrap Discovery API | 已完成原型 | `GET /v1/discovery/descriptor` 与 `/v1/discovery/peers` 仅发布本地显式配置和本地 Bundle 中验签、未过期的候选节点；不自动复制。 |
| Discovery 来源审计 | 已完成原型 | Bundle 哈希变化时写入节点签名、哈希链式本地审计记录，保留接纳/拒绝计数并可检测篡改。 |
| Python 依赖锁定 | 已完成 | Python 3.11 构建、运行时与开发依赖均固定版本并附 SHA-256 哈希；全新锁定环境已通过 66 项主测试。 |
| 托管激励现实检验 | 研究完成，未验证 | 已排除“陌生节点免费长期保存任意数据”假设；首选自有保存价值、成员制和有偿 custody，并须由真实试点证伪。 |
| 研究文档 | 已完成本批 | 已新增 Discovery、身份、第一批 Operator、地域风险与 custody 激励研究。 |

## 正在进行的工作

**真实 Operator 试点——材料已就绪，尚未招募。** 已准备待批准的招募说明、资格问卷、聚合成本账本和共同失败域模板；尚未联系、接纳或代表任何真实机构。Discovery 原型现可发布短期签名描述符、公开经验证的静态 Bundle，并在本地记录 Bundle 来源哈希、接纳/拒绝结果和签名审计链；它仍不产生保存义务或信任。经济研究已将“陌生人免费托管”标记为失败假设。身份锚定模型的升级仍属于红灯决策，必须等待人类审查。

## 四份研究文档完成状态

| 文档 | 状态 | 核心结论 |
| --- | --- | --- |
| `docs/research/discovery_reality_check.md` | 已完成 | 推荐多 bootstrap + 签名描述符，辅以可选 relay，后续再评估受限 DHT 的混合方案 |
| `docs/research/identity_rotation_proposals.md` | 已完成 | 保留 Ed25519 历史身份，新增稳定 subject 层；DID、DNS 和多签恢复分层使用，先经红灯审查 |
| `docs/research/first_operators_hypothesis.md` | 已完成 | 优先寻找公共数字保存机构与开放知识机构作为互补锚点，而非追求无差别节点数量 |
| `docs/research/geo_risk_matrix.md` | 已完成 | 按法域、数据类型、传播动作和 Operator 角色分层处理，不能把“公开”解释为“可永久复制” |

## 下一步计划

第一，为两个相互独立的试点 Operator 编写 Bundle 互换、跨托管复制、节点退出与恢复的最小实验，并明确记录操作成本与失败证据。第二，在不触及身份锚定红灯决策的前提下，为描述符来源、撤销事件和发现失败补充可验证的审计记录。第三，在扩大公开 Discovery 之前完成数据保护影响评估、版权通知/反通知流程、抓取授权边界和三地法律审查。第四，以真实存储、带宽、人工值守和合规成本为依据，形成非代币化的初步 custody 激励假设与可证伪实验；不得预先承诺收益。
