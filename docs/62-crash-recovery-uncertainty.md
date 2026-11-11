# E045：崩溃后的不确定结果与真实私聊核验

2026-11-12。修正崩溃恢复时误称“任务停止”的提示，保留 interrupted 与不自动重做。**父进程被 SIGKILL 后自动清理执行器/工具尚未实现**；本次现场由测试控制器核对具体进程归属后清理，不能算产品自动恢复清理通过。

## 复现与修改

隔离目录使用真实 Gateway/LocalRuntime 和合成 Python provider。确认 provider 属于测试 driver 后，仅结束 driver；重新打开原任务库时原实现发出“因服务中断而停止”，但此前启动的 provider 随后仍写出合成文件。恢复没有重执行，说明“不重做”正确、“已经停止”并不成立。首次控制器因 import path 缺失在结束 driver 后报错；沿原目录接着读证、释放同一个 provider，没有启动第二个任务。失败日志保留。

恢复提示现为：“上次任务执行期间服务中断，执行结果未确认，未自动重做。工具可能仍在执行或已产生结果；请先核对后再决定如何继续。”任务状态、稳定 outbox key、原记录和投递逻辑不变。先失败的回归验证旧提示错误；修复后163全量通过。增强既有测试，确认连续两次恢复不重执行、只发送一次不确定提示。干净导出新 wheel、六入口、18模块摘要一致通过；两 gateway 空闲正常加载，传输和原观察器保持。

## veil → 实际工具 → gateway 崩溃 → liev UI

veil 从原生两人私聊发送一次合成任务。Kimi 实际前台 Python 写 started 标记，sleep(75)，再写 late 文件。控制器读取现场 Python → Shell → Kimi → gateway 父子链，并与 manager 的 PID、启动时间、完整命令身份一致后，仅向该私聊 gateway 发 SIGKILL。不是根据消息中任意 PID 直接操作，也没有强杀传输、群或观察器。

gateway 消失后 Python 仍存活，开始后75.105秒实际出现28B late 文件，内容为测试标记、703和一个 LF。随后控制器逐个比对先前确认的后代身份，仅对仍存活者发 TERM，确认四个原进程全部消失后，才正常启动私聊 gateway。测试维护窗口另记。重启将原 running 标为 interrupted/process_restart，无结果、无自动文件交付，不自动再次执行。

liev 的新不确定提示在 veil 客户端完整可见。之后 veil 发起独立只读核验，Kimi 实际读取两个文件，回复存在、marker与准确 repr；完整回复 UI 可见，两文件内容摘要和mtime均未变，没有回传文件。原任务保持 interrupted，后续任务 completed；同 native session。即使本次已显式清理，通用恢复提示仍不能依赖测试控制器的额外动作假定“所有工具已停”。

## 证据与保留缺口

- `scripts/accept_crash_recovery_ui.py` 43项只读审计通过；5个内存负向拒绝错误父进程、仍活 gateway、过早观察、未完成清理及重启后才清理。共享 crash-recovery-ui-ledger.json 明确 automatic_descendant_cleanup_after_gateway_sigkill=false。
- crash-notice-validation.json、crash-notice-install.json记录回归/新安装；live doctor通过。私有命令、ID、截图、日志和两个原文件只在 local/crash-recovery-20261112。
- DM57任务/143outbox（142确认1旧拒绝）/152传输/210事件；新增两任务四文字确认。群3/7/12/76及所有旧任务/投递/日志保持。当前传输25113、群gateway38976、私聊gateway40346；这些仅是本阶段快照，控制前仍需验证归属。
- 原观察1261样本10.510h，6不可达、3poll_error及维护保留，未满24h。历史 manager during-shutdown错误仍未解释。

下一关键修复是通用执行器的父进程丢失处理：先在隔离进程中验证独立生命周期守护，证明父进程退出可触发已持有执行器的清理、正常完成/取消/超时仍可靠、无错误PID信号，再做新的真实私聊回归。本次“未重做＋提示准确”不能抵消工具遗留和潜在并发执行风险；不重跑本次已确认故障，也不把状态改为 cancelled/completed。

## 同轮原生入口边界

[官方语音手册](https://notes.dingtalk.com/p/Y7kmby3lP40KXLq2/docs/Y7kmbqkq01jQMXLq)明确将麦克风/按住说话步骤列在手机端，未提供本页电脑端步骤。公开页JS渲染后已读证；不能据此断言Mac没有语音能力，也不能把手机步骤作为当前Mac可用入口。native-voice-manual-review.json保留边界，未录音、未新增语音消息；引用旧菜单路径不再重试。
