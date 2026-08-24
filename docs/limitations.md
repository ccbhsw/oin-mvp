# OIN 已知限制与设计空白

## 1. 时间戳新鲜度（部分收窄）

- **这次改了什么**：同一 `raw_content_hash` 在节点上已有至少一条 observation 时，再次提交必须携带可绑定当前已签名 manifest 的 RFC 3161 凭证，否则拒绝写入，错误码 `TIMESTAMP_EVIDENCE_REQUIRED`。首次出现的 content_hash 仍允许 `local-declaration`。verify 会标明证据类型是 `local-declaration` 还是 `rfc3161`；若是后者，额外展示 TSA 时间与 Observer `captured_at` 的差值，该差值只作展示，不作为拒绝条件。
- **仍未覆盖**：如果攻击者只提交一次（库里没有同一 content_hash 的历史记录），伪造的 `captured_at` 仍然无法被发现。这不是“漏洞已修复”，只是把“可无限重签换本地时间”收窄为“首次仍可单方声明时间，重复内容必须有第三方时间戳”。
- **其它边界**：凭证校验在能提供 TSA CA（`tsa_ca_pem` 或 `OIN_TSA_CA_PEM`）时用 OpenSSL 验签；没有 CA 时只要求 token 可解析且 imprint 绑定当前 manifest。历史数据不会被补盖章。主流程已接入 `local_declaration` / `obtain_rfc3161_token` 与重复内容的 `TIMESTAMP_EVIDENCE_REQUIRED`，本次未再改时间戳实现。

## 2. 文本/文件的 canonical_id 没有命名空间和归属校验

- **现状**：网页对象的身份来自 `object_id(canonical_url, resource_type)`，URL 本身接近全局唯一，两个人存同一个网址本来就该算同一对象。文本和文件捕获把用户自填的 `canonical_id` 编进同一套 `object_id`：相同标识符会被当成同一对象的不同版本，进入同一个冲突集。
- **仍未覆盖**：`canonical_id` 是自由文本，没有命名空间、没有归属、也没有防碰撞。两个互不相关的人各自用「笔记」「声明」「1」这种常见词，内容会被绑到一起；别人也可以故意选用你可能用的词，把自己的文本塞进你的历史版本里造成混淆。这不是这次捕获扩展要解决的范围，只是最小实现下已知的设计缺口。
- **其它边界**：未提供 `canonical_id` 时每次捕获是独立对象，不会撞进已有冲突集。网页捕获路径没有改，也不使用 `canonical_id`。

## 3. 验证器异构性独立性待完全闭合

Node.js 验证器由同一执行上下文参考 Python 源码实现，待后续由独立执行者复现确认。
