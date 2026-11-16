# Codex 原生取消与部署 E119

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


E118表明仅终止CLI进程组不能停止Codex另建会话的工具：返回取消后约90秒仍写入late。该失败原件保留，不能以cleanup_complete或立即检查无文件替代实际退出验证。

依据固定Codex 0.164.0源码 [exec ctrl_c处理](https://github.com/openai/codex/blob/6aaac694803004a63c6f393d153c96d22521a6b9/codex-rs/exec/src/lib.rs)，对受管Codex先发SIGINT，由官方执行器调用turn/interrupt，最多等5秒，再执行原有限进程组清理。只向仍持有的子进程PID发信号，不扫描杀共享服务。清理期间保持stdout可写并排空，避免取消事件堵管。Kimi/DWS不启原生中断参数。

日志明确cleanup_scope=owned_cli_process_group，独立工具清理仍须验；这不是OS沙箱，不能保证任意恶意脱组任务或撤销已经发生的外部副作用。

## 对应验证

- 旧源码合成取消/超时/父进程SIGKILL共3方法全部失败，新源码7方法通过，包含超过1MB取消输出、拒绝信号和超时边界。
- 冻结源码、同一wheel Python3.14及3.11，各374方法通过；21模块及许可一致。第一次Py3.14全量有1项fixture启动竞态错误，原日志保留；仅将该测试的2秒取消计时放在合成后代ready之后，原生产超时和清理断言不变，最终三套冻结测试一致通过。
- 新的真实Codex只执行一次：工具设30秒后写入late，开始后取消，1.714秒后返回；跨过计划写入期限继续观察，4个已观察的自有进程、4个进程组均退出，无late。保留E118反例，不用新成功覆盖旧失败。
- 验证过程中曾短暂修改运行checkout的guard；gateway仍旧模块，但history子调用可能读到候选文件。已在原24h观察记此混用区间，后续验证改用冻结目录。不能声称该段统一版本。

## 部署检查点

冻结验证成功后，按归属停gateway，持久暂停新DWS调用并排空在途，再停transport；保存六库快照。只应用两个候选模块，显式迁移私聊runtime binding至Codex，原session历史及89旧任务/旧outbox保持。此提交时三服务停机，下一步固定cut只启transport补读，停机审查积压后启动AIC Kimi/私聊Codex。真实UI任务/下载/续接/取消尚待下一证据，不提前宣称通过。

资料：[脱敏核验](../evidence/2026-11-13/codex-native-interrupt-validation.json)。原始日志、配置、账本及延迟文件只在local/codex-native-interrupt-20261113及local/codex-persistent-env-20261113。

官方DWS取消双层候选仍未部署；系统钥匙串根因/自然刷新未证，49/14/1、7 MUST缺口不变。
