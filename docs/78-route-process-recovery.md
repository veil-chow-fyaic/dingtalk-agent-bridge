# 路由进程锁与死亡后的持久投递

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E061。既有single_owner只验证同进程第二个Bridge对象，本段用真实独立进程核内核锁与SQLite恢复，provider为无账号合成对象。

两个场景分别在投递confirmed后，以及provider已进入发送调用但尚未返回时暂停。另一个进程争用同一路由立即被拒且不调用发送；独立路由可打开空账本，原owner保持存活。随后仅通过保存的Popen句柄SIGKILL自建owner，实际退出码-9；错误profile重开仍拒绝，再按原profile连续重开两次。

已确认记录仍confirmed；原executing转outcome_unknown，不猜测外部是否收到。相同key/body返回原记录且provider发送0次，改body仍拒绝；两条事件/一条投递不重复，每个场景整个provider边界只进入一次。正常close后下一进程也可重开。没有真实DWS消息、现场故障或UI结论。

新增两项在源码及两个安装环境中均通过。源码/3.14全量195项通过；**3.11全量195项有1个manager错误，不能写成全绿**。E060入口成功保住触发拒绝的同次观察：stop-after-signal、相同lstart、状态?Es、命令变为(python3.11)。本机man ps将E解释为正在退出。这是本次错误的明确证据，不证明所有E039/E059历史错误同因。

下一段只修已经发TERM后的同启动时间E过渡：继续在原时限内观察到真正退出，不追加信号，不提前当作stopped；其他身份变化及发信号前变化仍立即拒绝。先按捕获形状复现，并核拒绝边界和超时，再考虑部署。原失败日志/原始ps保持，不为取绿覆盖重跑。

23项证据审计通过，其中明确核3.11失败及诊断已保存。现场三个进程、两路旧记录、E059产品和原观察保持；约13.354h、7不可达，24h未满。

```bash
PYTHONPATH=. python3 scripts/accept_route_process_recovery.py
```

[审计与日志摘要](../evidence/2026-11-12/route-process-recovery-validation.json)。私有子进程结果、全量日志、精确失败路径在local/route-process-20261112；诊断只留local，不入Git。
