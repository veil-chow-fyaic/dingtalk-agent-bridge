# E079：历史补读容量停滞

**当前状态：E084已将E080原样core/测试补丁应用到当前源码，与E083官方参数修复组合验证；源码及新wheel双Python各262通过。未部署，真实补读/UI仍未复验。下文E079/E080保留当时事实。**

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

## E080：候选补丁及冻结验证

[候选补丁](patches/history-continuation-E080.patch)基于640570a，只改core.py并新增8个专项方法；[14项审计及版本摘要](../evidence/2026-11-12/history-continuation-candidate.json)。它尚未应用到当前产品、未部署，当前产品仍有E079缺陷。待决查询的21模块和checker仍完全匹配既有计划；不得自动应用候选后悄悄替换查询计划。

候选在首次请求前保存固定窗口；成功页的事件和续页token在同一SQLite事务中提交。请求失败保留窗口与旧token，页消息/事务失败不推进；只有完整结果才写原窗口end为watermark并删除续页状态。失败ledger、partial、矛盾的complete/hasMore、无安全token及循环token均不能跳过缺口。token由官方生成并解码，bridge只检查非空可打印长度/持久结构；每窗口最多4096个续页检查点，超过时明确错误、不自行丢弃或换窗口。每轮仍一条有界history调用，不提高并发或后台频率。

合成1001条（首轮后重建bridge）变为1000/1/0，全量无丢失或重复；5000条五轮各1000，首轮后重建也继续。新消息在旧窗口end之后，只在下一窗口入库；读失败/partial/失败ledger保持游标；重复/循环/损坏状态拒绝；SQLite在续页checkpoint或完整watermark处ABORT后，重启按原位置接续。优化模式Python的8专项也通过，不依赖assert执行校验。

源码Python3.14与候选新wheel隔离安装Python3.14/3.11各执行259项，通过；六入口仅运行help，21模块按冻结源码核对，安装套件无源码包。259属于此候选的冻结版本，不是当前已应用产品或真实UI结果。原始冻结源码、wheel、测试及日志只在local/history-continuation-20261112；这不是再次导出E075交接包。

两次命令编排用了错误cwd，修改/补丁生成在触达目标前失败，随后改为明确路径；第一次空测试发现被旧runner写成ok:true/0，日志保留且不计作任何通过。真正8专项/259全量均检查了非零实际数量。该runner漏洞作为下一独立修复，不能以最终候选通过覆盖它。

应用安排：先等既有一次查询许可及同key结果结束，再决定是否应用候选、核冻结字节并更新恢复方案；任何后台启动仍需另行明确同意。期间可继续独立工具/证据缺口工作。不得借候选之名执行真实DWS或重试旧认证。

## E084：应用并核整体产品

[10项冻结审计](../evidence/2026-11-12/history-continuation-applied-validation.json)确认core.py和8方法逐字节匹配E080候选，其余20模块逐字节匹配E083。源码、Python3.14和3.11新wheel实际各执行262项，六入口/21模块及冻结测试匹配，不是把旧测试数相加。核验脚本保留E083正确参数，E082真实receipt/raw字节不变。三个服务继续停止，现场配置与账本未改，没有新真实调用或新查询key。

## E088：长停机与首次恢复窗口

[3专项三环境/7核验](../evidence/2026-11-12/history-outage-window-validation.json)使用固定合成时间，不改系统时钟、真实账本或真实DWS。group/direct均验证：72小时前watermark仍从其前5分钟开始，定期24h深读不会截掉更早积压；先前失败已冻结的窗口保持原end，恢复后先完成旧范围，下一轮再覆盖整个72h间隔，恰等于旧end的消息进入下一范围，按消息ID去重。无watermark的新部署只读过去24h，deep=true也不是全历史扫描。

固定官方63a7c49的message_time_range.go使用[start,end)、不在该解析器中强加24h截断；history_cursor.go绑定原起止时间。两文件与固定提交逐字节一致。本次未运行官方CLI或新Go测试，不把源码局部审查当服务端保留期/任意范围可用性的证明。

没有发现这些窗口场景的产品缺陷，因此不改21模块、不重建wheel、不重跑全量。新增测试在源码及E084已安装3.14/3.11各3项通过。恢复判据应记录本轮固定恢复cut，停机后核每路watermark>=cut且无未完成history_window；仅见一次last_sync.complete=true可能只是旧窗口结束，不能据此开启gateway。远端可见性与停机期任务授权仍需实际补读和审查。
