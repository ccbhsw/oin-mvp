# CHANGELOG

## 2026-08-22

### 撤回
- 撤回全链路测试报告中第 5 步（REPLICATE/VERIFY）的 PASS 结论。原因：审计发现当时未实际调用验证接口，该结论仅代表数据同步成功，不代表验证逻辑通过。修正后的验证结果详见交叉验证报告。
- 原始报告文件：docs/experiments/alicloud_test_report.md
