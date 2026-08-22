# OIN 地域风险矩阵：中国大陆、欧盟与美国

> **法律免责声明：**本文是工程风险初筛，不是正式法律意见；上线、跨境传输或应诉前应由相应法域律师审查。

## 1. 边界

“开放信息”只表示资源可公开取得，不能推出没有版权、个人信息、商业秘密或国家安全属性，也不能推出任何人有权复制。OIN 签名证明 Observer 签署了某时点观察和归档字节，不证明内容为真或再发布合法。公开索引、完整归档、跨境复制和公众下载是不同处理行为，不能由 `public=true` 覆盖。

Schema 应区分 `source_publicly_retrievable`、`license_basis`、`personal_data_present`、`jurisdiction`、`retention_class`、`legal_request_status` 和 `access_policy`。原始载荷、哈希索引、公开目录和跨境副本应分层治理。

## 2. 风险矩阵

| 法域 | 规则 | OIN 风险 | 优先动作 |
| --- | --- | --- | --- |
| 中国大陆 | 网络安全法、数据安全法、个人信息保护法及出境规则 | 数据分类分级、个人信息/重要数据、内容治理、出境 | 法域隔离、最小采集、分类、评估、本地化 |
| 欧盟 | GDPR、DSA、eIDAS | 删除权与永久归档；hosting 义务；签名资格误读 | controller/processor 分析、DPIA、请求流程 |
| 美国 | DMCA、Section 230、CFAA、CCPA/CPRA | 版权通知、第三方责任、越权抓取、州级权利 | 授权抓取、notice-and-action、州法矩阵 |

## 3. 中国大陆

三部法律分别涉及网络安全、数据分类分级和个人信息处理合法性、个人权利及出境条件。[1] [2] [3] 境内 Operator 向境外复制个人信息时，可能触发出境、重要数据识别和影响评估要求。[4]

“签名而不裁决事实”不是内容免责。违法、侵权或敏感内容的提交、复制、索引和下载可能分别产生风险；境内节点应有保全、阻断、报告和执法协作流程，并对未知高风险对象复核。

## 4. 欧盟

GDPR 的冲突在于不可变历史与访问、更正、删除或限制处理权。删除权并非绝对，但 OIN 不能只以“不可篡改”为由拒绝；应区分删除载荷、隐藏访问、保留哈希和法律保全，并记录依据。[5]

若节点属于 hosting/intermediary service，DSA 可能要求 notice-and-action、决定理由和透明度，具体取决于服务性质与规模。[6] eIDAS 可作签名、时间戳和信任服务参照，但 OIN Ed25519 不自动等同于合格电子签名。[7]

## 5. 美国

DMCA §512 的 safe harbor 依赖指定代理、通知/反通知和重复侵权人政策，不是保存公开网页的通用许可证。[8] Section 230 对第三方内容仅提供有限保护，不覆盖版权等例外；节点自身编辑材料仍有风险。[9] CFAA 要求公开 URL 抓取不得绕过认证或技术控制，并应保留授权和日志。CCPA/CPRA 等州法可能提供通知、访问、删除和退出权，适用取决于门槛。[10] [11]

## 6. 初步建议

OIN 不应承诺“任何人、任何内容、永久不可删除”。应先限定公开可抓取且许可基础可记录的对象，配置 Operator 法域/访问政策，并实现软删除与法律保全状态，使删除公开副本不等于篡改历史。扩大 Discovery 前完成 DPIA、版权流程、授权测试和三地法律审查。

## References

[1]: https://www.npc.gov.cn/englishnpc/c23934/202012/8d7c8f6d6b8d4f4f9f5c0efc2bb2e8b3.shtml "Cybersecurity Law of the PRC"
[2]: https://www.npc.gov.cn/englishnpc/c23934/202106/7c5f0e4f5c2a4c80b0a4c9a3f1c8d6c1.shtml "Data Security Law of the PRC"
[3]: https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm "中华人民共和国个人信息保护法"
[4]: https://www.cac.gov.cn/2021-10/29/c_1637102874600858.htm "数据出境安全评估办法"
[5]: https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng "GDPR, EUR-Lex"
[6]: https://eur-lex.europa.eu/eli/reg/2022/2065/oj/eng "Digital Services Act, EUR-Lex"
[7]: https://eur-lex.europa.eu/eli/reg/910/2014/oj/eng "eIDAS, EUR-Lex"
[8]: https://www.law.cornell.edu/uscode/text/17/512 "17 U.S.C. §512"
[9]: https://www.law.cornell.edu/uscode/text/47/230 "47 U.S.C. §230"
[10]: https://oag.ca.gov/privacy/ccpa "California Attorney General: CCPA"
[11]: https://www.law.cornell.edu/uscode/text/18/1030 "18 U.S.C. §1030 CFAA"
