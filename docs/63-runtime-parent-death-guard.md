# E046：gateway 崩溃后的执行器自动清理

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12。E045 发现的工具遗留已补通用生命周期守护，并用新的 veil→liev 原生私聊任务验证。旧 E045 的失败、晚写文件与人工清理证据原样保留；本次不重做旧任务。

## 实现与验证边界

LocalRuntime 创建仅 gateway 持有写端的 pipe，启动独立 runtime_guard。守护进程持有实际 CLI 的 Popen，CLI 在独立进程组中运行且不继承 pipe。gateway 正常结束、异常退出或被 SIGKILL 后，pipe EOF 让守护清理 CLI 及同组工具；清理期间不提前回收 leader，避免复用 PID 的误信号。沿用 TERM→有界等待→KILL→回收，完成后写私有 stderr 事件。该机制不绑定 Kimi 或 Codex，不改变输出契约、native session、outbox key 或自动重做策略。

实际 CLI 提前退出时立即结束并报告未完成，不再等整个任务超时。18项真实进程测试涵盖正常完成、超时、取消、已退出 leader 的后代、Codex 管道及新父进程丢失场景；新用例结束独立 driver，验证 CLI 和忽略 TERM 的工具清理、释放工具后无迟到写入。Python 3.14 全量164项通过，Python 3.12 运行器18项通过。干净导出新 wheel、新 venv 六入口与19模块摘要一致，包内无 local。两 gateway 在空闲时加载新代码，传输和原观察器保持。

这不是 OS 沙箱：守护自身被 SIGKILL、恶意工具脱离进程组、已经完成的外部副作用不在本次清理保证内。因此恢复仍发送“执行结果未确认，未自动重做”的准确提示，不承诺副作用回滚。

## 真实用户路径

veil 原生私聊发一次 DAB-GUARD-20261112-046。Kimi 前台 Python 写 started 标记、sleep(75)，最后才应写 late。控制器确认 Python→Shell→Kimi→runtime_guard→gateway 的现场父子链，并将 gateway 与 manager 的 PID、启动时间及完整命令匹配，随后只向该 gateway 发 SIGKILL。

独立守护记录 gateway_pipe_closed/cleanup_complete；约0.365秒后原五个进程均消失。**测试控制器没有向后代发送任何清理信号**。确认清理后正常启动 gateway，原任务从 running 变为 interrupted/process_restart、result=null；没有重放或回传局部文件。不确定提示在 veil 聊天窗口完整可见。

开始后204.16秒（已越过75秒工具等待和80秒观察护栏）started保持原内容、late仍不存在。veil再发送一个明确只读任务，Kimi实际Python读取存在性和marker，工具输出 started_exists=true、late_exists=false；liev完整回复“marker=DAB-GUARD-20261112-046；started存在；late不存在。”已在原生聊天窗口目视确认。没有文件产物，未重做原任务，native session保持。

## 可复核证据

- `scripts/accept_runtime_parent_guard_ui.py`：42项只读审计通过；5个内存负向拒绝错误父子归属、人工清理冒充自动、过早观察、出现晚写、重启后才清理。共享 runtime-parent-guard-ui-ledger/audit-negative.json。
- runtime-parent-guard-validation/install.json：164全量、双Python运行器各18项、六入口19模块、doctor与精确观测时长。
- 私有原始命令、ID、任务/投递、工具日志、AX/截图和进程证据仅在 local/runtime-parent-guard-20261112。第一次 follow-up 截图只有接收提示，另存 attempt；最终完整回复另外取证，未重发。
- DM59任务/147outbox（146确认1旧拒绝）/156传输/216事件；新增两任务四文字确认。群3/7/12/76和全部旧账本/日志保持。当前快照传输25113、群gateway46420、私聊gateway47099；控制前仍必须重新验证归属。
- 原观察1290样本约10.752小时，6不可达、3poll_error及维护均保留，未满24h，未重启观察器。历史 manager during-shutdown 错误根因仍未解释，本修复不消除那两次失败。

下一段回到 C01 明确新入口/官方契约：单消息普通多附件、原生媒体或入站引用只在取得新证据后执行；群新增实验继续等待第三人范围答复。真实失效 refresh、完整24h与终检仍缺，项目未完成、heartbeat保持。
