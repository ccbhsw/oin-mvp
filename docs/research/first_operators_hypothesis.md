# 第一批 Operator 假说：谁会真正加入 OIN？

## 冷启动为何重要

OIN 已有捕获、签名、复制和离线验证闭环，但网络价值来自相互不控制的观察。没有第一批 Operator，Discovery 没有对象，冲突保留没有独立参照，独立性 Profile 也没有样本。候选者应按既有痛点与 OIN 证据模型匹配，而非只看“是否喜欢去中心化”。以下是假说，不是机构承诺。

## 候选一：Internet Archive 或同类公共保存机构

Internet Archive 长期保存网页和数字资料，WARC 也是网页归档标准容器。[1] 这类机构的痛点是来源证明、跨机构冗余、服务连续性和法律响应，而不只是存储容量。OIN 可把 Observer 签名、WARC/WACZ 哈希、Merkle proof 和独立副本放进离线可验证证据包。

它可能愿意，因为 OIN 加强跨机构保存和故障恢复；加入成本却包括持续节点、带宽、对象存储、个人信息与版权投诉，并把声誉与“保留冲突而不裁决真伪”相连。其拒绝理由可能是未审核材料、地域访问和法律政策不允许复制。切入点应是小规模试点，只发布政策允许的公共档案，并强调签名不是内容背书。

## 候选二：Wikimedia Foundation 或其技术伙伴

Wikimedia 生态面对版本历史、引用稳定、镜像差异和编辑争议，基金会使命是让知识自由可得。[2] OIN 可成为 MediaWiki 之外的 Observation 层：不同 Operator 保存页面、PDF 或数据集的时点版本，分开记录提交者和捕获者，不让单一页面状态覆盖冲突。成本包括 Schema 对接、隐私/删除政策、重复存储、值班运维和恶意提交处理。

它可能愿意，因为外部时点证据有助研究与引用；也可能担心 OIN 把未审核材料包装成“开放知识”。较安全方式是可退出 federation：只复制符合自身政策的对象，并以 `independence_profile` 公开资金、行政和托管关系，避免把一个基金会误算成多个独立节点。

| 候选 | OIN 价值 | 成本与阻力 |
| --- | --- | --- |
| 公共保存机构 | 来源连续性、跨机构副本 | 存储、法务、内容责任 |
| 开放知识机构 | 版本与引用可审计 | Schema、隐私、治理整合 |

## 第一人与第十人、网络效应

第一个参与者承担“建路”成本：共同定义 Schema、复制、争议和退出流程，短期没有网络效应，却获得制度影响力。第十个参与者承担“验证”成本：可先观察故障率、法律响应和独立性证据，并立即获得冗余。前者需要共同设计权和小试点，后者需要标准安装和可预测成本。

网络效应的最低条件不是神奇节点数，而是三个以上相互不控制的 Operator、两个以上托管/法域、同一批高价值对象的重复观察和稳定离线验证器。第六至第十个参与者带来不同地域、使命和来源后，独立性分析才开始产生信息价值。因此第一阶段应寻找一个公共保存锚点和一个开放知识锚点，而非追求数量。

## References

[1]: https://archive.org/about/ "Internet Archive: About"
[2]: https://wikimediafoundation.org/our-work/ "Wikimedia Foundation: Our work"
[3]: https://www.iso.org/standard/57284.html "ISO 28500:2017 WARC"
[4]: https://www.dpconline.org/handbook/technical-solutions-and-tools/warc "Digital Preservation Coalition: WARC"
