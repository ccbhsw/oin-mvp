# OIN 异构验证器交叉验证与根因调查最终报告

## 1. 执行上下文与审计声明
- **执行上下文归属**：本次“根因排查”与 `cross_verify.py` 脚本修正由同一个执行上下文完成。Node.js 验证器的初始实现亦由本次调查执行者完成。
- **审计声明**：
> “本次排查显示两端失败路径不同（Python 端因 `Path Length: 0` 且计算出的 Root 与 Expected Root 不一致导致校验失败；Node.js 端因 `proof.inclusion_path` 为 `undefined` 触发 `TypeError` 并在 `try...catch` 中被捕获返回 `false`），但因排查与实现由同一上下文完成，尚不能完全排除同源判断偏差的可能。”

## 2. 根因复核与修正验证
### 2.1 Merkle 验证失败根因 (Case 0)
- **原始报错复核**：
    - **Python**：在 `merkle_debug.log` 中显示 `Path Length: 0`，最终计算根哈希与预期不符。
    - **Node.js**：触发 `TypeError: Cannot read properties of undefined (reading 'map')`。
- **根因确认**：`cross_verify.py` 错误调用 `MerkleLog.append()`，该方法不返回 `inclusion_path`。必须调用 `log.proof(observation_id)` 才能获取完整证明。
- **修正措施**：已将 `cross_verify.py` 中的方法调用修正为 `log.proof()`。
- **字段级差异比对**：
    - **旧 Proof 字段**：`['entry', 'checkpoint']`
    - **新 Proof 字段**：`['entry', 'inclusion_path', 'checkpoint']` (新增 `inclusion_path` 字段)

### 2.2 最终交叉验证结果
重新生成数据后，Python 与 Node.js 验证器对全部 5 个用例的验证结果如下：

| 测试用例 | Python (Sig/Merkle) | Node.js (Sig/Merkle) | 结论 |
| :--- | :--- | :--- | :--- |
| 0. 基准合法数据 | **True / True** | **True / True** | **一致通过** |
| 1. 篡改公钥 | False / False | False / False | 一致拒绝 |
| 2. 篡改叶子哈希 | True / False | True / False | 一致拒绝 |
| 3. 时间戳篡改并重签 | **True / False** | **True / False** | 一致识别 |
| 4. 截断签名 | False / False | False / False | 一致拒绝 |

## 3. 协议未定义项与设计空白 (Case 3 定性)
**用例 3 验证确认**：
当前协议在时间戳篡改场景下，对内部自洽的重签名 + 新时间戳无拦截能力（只要签名与内容匹配，`signature_valid` 即返回 `True`）。
- **设计空白**：此为已确认真实可利用的设计空白。目前验证器仅负责“数据自洽性”校验，不包含“业务合规性”（如时间戳新鲜度）校验。
- **后续建议**：后续需在协议层增加受信任第三方时间戳（RFC 3161）或透明度日志承诺的时间戳校验机制，不能在本次任务中擅自修补验证器逻辑。

## 4. 历史全链路测试审计
- **状态修正**：原《阿里云两节点真实网络测试报告》中第 5 步 (REPLICATE / VERIFY) 的 PASS 结论已撤回。
- **审计证据**：机器 B 日志显示全链路测试期间未调用 `/v1/verify/` 接口。当时的 PASS 仅代表数据同步成功。
- **闭环确认**：本次交叉验证已完成对异构验证逻辑的补全验证。

## 5. 最终结论状态
> 本次交叉验证的 5 个用例结果一致（基于已修正的测试数据）。但由于本次排查与 Node.js 初始实现由同一执行上下文完成，尚不构成完全独立的异构验证，缺口部分收敛，未正式闭合。建议后续由独立执行者复现一次作为最终确认，再正式标记闭合。

---
**报告人：OIN 审计组
**日期**：2026-08-22
