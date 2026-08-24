# OIN 已知限制与设计空白

## 1. 时间戳新鲜度（部分收窄）

- **这次改了什么**：同一 `raw_content_hash` 在节点上已有至少一条 observation 时，再次提交必须携带可绑定当前已签名 manifest 的 RFC 3161 凭证，否则拒绝写入，错误码 `TIMESTAMP_EVIDENCE_REQUIRED`。首次出现的 content_hash 仍允许 `local-declaration`。verify 会标明证据类型是 `local-declaration` 还是 `rfc3161`；若是后者，额外展示 TSA 时间与 Observer `captured_at` 的差值，该差值只作展示，不作为拒绝条件。
- **仍未覆盖**：如果攻击者只提交一次（库里没有同一 content_hash 的历史记录），伪造的 `captured_at` 仍然无法被发现。这不是“漏洞已修复”，只是把“可无限重签换本地时间”收窄为“首次仍可单方声明时间，重复内容必须有第三方时间戳”。
- **其它边界**：凭证校验在能提供 TSA CA（`tsa_ca_pem` 或 `OIN_TSA_CA_PEM`）时用 OpenSSL 验签；没有 CA 时只要求 token 可解析且 imprint 绑定当前 manifest。历史数据不会被补盖章。主流程已接入 `local_declaration` / `obtain_rfc3161_token` 与重复内容的 `TIMESTAMP_EVIDENCE_REQUIRED`，本次未再改时间戳实现。

## 2. 验证器异构性独立性待完全闭合

Node.js 验证器由同一执行上下文参考 Python 源码实现，待后续由独立执行者复现确认。
