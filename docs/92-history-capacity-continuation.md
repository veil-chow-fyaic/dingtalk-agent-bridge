# E079：历史补读容量停滞

1001条合成消息超过当前每轮1000条上限时，连续三轮（首轮后重启bridge）插入数为1000、0、0。第1001条始终缺失，watermark正确保留未完成，但补读没有向后推进。源码与E073同wheel的Python3.14/3.11均复现，独立探针退出2；这是一项未解决缺陷，不是通过的验收。

[脱敏复现及官方契约验证](../evidence/2026-11-12/history-capacity-regression.json)。运行`PYTHONPATH=. python3 scripts/probe_history_capacity.py`只使用合成提供方、临时SQLite和一次bridge重建，不执行官方binary、HTTP、认证或UI。结果不能替代现场1001条历史验证，也没有重放旧任务。原始输出及冻结探针位于local/history-capacity-20261112。

## 官方负责分页，bridge负责持久接续

固定官方v1.0.67 peeled commit为63a7c4906c7dee10750011ea309b9eb78abb7eb0。

- [chat_messages.go](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/smart/chat_messages.go)：达到page_limit/result_limit时可能提供nextPageToken，complete=false且没有失败ledger的有界结果可正常返回；出现不安全的页内截断时可能不提供可续页边界，不能自行猜游标。
- [history_cursor.go](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/smart/history_cursor.go)：page-token绑定会话、方向、发送者条件和原start/end。续页必须保留原时间窗口；bridge只持久化不透明token，不复制官方编码或按最后一条时间戳跳过。
- 官方两个合成Go测试`TestCrossPlatformCoverageChatMessagesPageAllPublishesBoundedContinuation`和`TestCrossPlatformCoverageOptimizationHistoryCursorBinding`均通过。使用现有固定源码与本地Go、GOPROXY=off/GOSUMDB=off/GOTOOLCHAIN=local；不是官方真实CLI调用。首次PATH无go失败保留，随后使用已存在的明确toolchain路径。

当前Bridge.sync每次以当前时间重建窗口、重复page-all上限，却忽略nextPageToken，所以在积压期间每次读回相同前缀。不能通过增加page-limit、提高轮询频率、推进watermark或把partial写成complete掩盖该问题。

## 下一步与当前边界

准备同一实现的候选修复：原窗口、官方token与事件在同一SQLite事务提交；每轮仍只执行一个有界history请求；重启接续旧窗口，完成后才推进到该窗口原end。失败ledger、无安全token、重复token及损坏持久状态需明确停留/报错，不越过未读数据。验证包括超过1000条、重启、窗口后新消息、事务回滚和游标失败。

E074待决计划冻结21个产品模块；为保持用户尚未答复的一次查询方案不变，候选先在仅含源码/合成测试的local目录验证，不修改当前产品或计划。候选不是已应用/部署的修复。三个服务和operator_suspended保持停机；无真实DWS调用，不据此恢复后台。原R13/可靠性和UI缺项保持，E079不改变验收等级或格子。
