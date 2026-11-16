# 并发对账终态保护与真实私聊交付

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E052。修复两个对账请求并发时，较慢的旧状态或查询错误覆盖已确认投递的问题。修复后，首个已提交的confirmed/failed/rejected终态保持；原key、task ID和message ID不会被晚返回的请求改回未知或提交中。

## 缺陷、修复与失败保持

HTTP服务按线程处理请求，官方状态查询在SQLite锁外执行。旧代码无条件写回查询结果：请求A阻塞时，请求B可能已确认成功；A稍后返回PENDING/FAILED就会覆盖B，还可能清空message ID。send内部首次状态查询若较慢地报授权/超时/PARAM_ERROR，也会把另一请求已confirmed的记录改成outcome_unknown。

新增[线程竞态测试](../tests/test_reconcile_race.py)用事件闸控制顺序，旧实现4个方法产生8个失败；再用[真实HTTP与合成CLI子进程](../tests/test_reconcile_http.py)对旧E048已安装包重现4种失败。旧失败日志保留，未用现场旧投递造故障、换key或重发。

[core.py](../dingtalk_bridge/core.py)在同一SQL更新条件中排除终态，晚错误由共用方法同样保护。网络调用仍在锁外，避免慢查询阻塞其他会话；同key重复查询/重启不重新发送。若平台返回互相矛盾的终态，保留先前已提交结论，需要另行核查，不依到达顺序反复改写。

没有并发终态时，未知发送/查询失败仍保持原不确定规则；不把授权错误当明确未发送。没有重新实现官方OAuth、刷新或重试，也不声称真实失效refresh恢复已完成。

## 代码、安装与部署验证

[验证报告](../evidence/2026-11-12/reconcile-race-validation.json)22项通过。新增5个测试方法，含多个并发子场景：慢PENDING/冲突终态、慢授权错误/超时/PARAM_ERROR、同key重读、task/message保留、重启后终态不退回且不再调用发送。

Python3.14完整177项、最低3.11.15隔离已安装wheel完整177项通过。3.11测试目录刻意不放产品源码包或账号local数据，确认从site-packages导入；新wheel六入口、19模块与冻结源码/安装包/部署摘要一致。[安装报告](../evidence/2026-11-12/reconcile-race-install.json)

两路无排队/运行/待媒体任务时，统一管理器正常停启传输与双gateway加载新版。身份归属保护没有放宽，账号配置字节保持；维护写入原观察日志，原观察器不重置。重载前后两路旧任务/outbox/meta/deliveries/events/日志保持，live doctor通过。历史manager关闭错误未因此标为根因已解决。

## 用户视角的独立部署回归

veil在原生钉钉与liev私聊中只发送一次新合成任务：实际计算[11,13,17]的平方与总和，写JSON并回传。Kimi实际Bash调用Python，以列表计算`x * x`和`sum(squares)`，写入新exports文件。没有从提示获取答案，没有重做旧任务或调用办公工具。

liev普通账号在客户端回复“平方列表：[121, 169, 289]；总和：579。”及145字节JSON卡片，均带AI发送标识。文件通过钉钉保存窗口实际下载，再在访达Quick Look完整打开，marker、输入、平方和总和均可见；生成件、gateway交付件、官方资源下载件、客户端下载件四份字节摘要一致。

[只读UI审计](../scripts/accept_reconcile_race_ui.py)36项通过，[结果](../evidence/2026-11-12/reconcile-race-ui-ledger.json)与[7项内存负向](../evidence/2026-11-12/reconcile-race-audit-negative.json)可复核。负向包括错误计算、篡改客户端下载、缺原件、错误工具结果、缺完整回复、Quick Look仍busy及伪造发送者；原始证据没有修改。

并发竞态由隔离线程/HTTP确定性验证，真实UI任务验证部署后正常交付，两者分开计证；没有声称在真实钉钉制造了同一竞态。客户端原始聊天、AX/截图、下载件、工具日志与安装/失败日志仅在`local/reconcile-race-20261112/`。

新增1任务、3条确认投递；DM62任务/154outbox（153确认1旧拒绝）/163传输/226事件，群3/7/12/76保持，同native session。所有旧记录/日志保持。原观察1402样本、11.686小时、6不可达，历史3poll_error及维护仍保留；未满24h，整体项目未完成。
