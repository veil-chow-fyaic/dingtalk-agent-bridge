# 本机HTTP修复实际部署与交付候选

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-16，E142。将E140已完整验证的本机HTTP直连/拒绝重定向修复实际应用并提交为10758eb，25模块逐字节等于已测候选和同wheel。源码与同wheel安装Python3.14/3.11各477方法通过为E140既有证据，本轮没有重跑全量或称482通过。

原startup-provenance-24h-20261116观察经核原PID/归属后正常SIGTERM收尾；运行1.82小时、218样本、零记录错误，但未满24h且原固定cut未覆盖，evidence_valid/stability_pass为false。原开始、截止、seal和失败事实保留，审查放run外。不能为了保计时把已完成修复搁置一天，也不能把新run当原run续表。

实际维护先停gateway、封新DWS调用/排空，再停transport、备份六库；E141通用--allow-empty-wal在原owner锁下成功，无手动删除/修改SQLite旁文件。应用精确候选后transport-only补历史；同一SQLite快照watermark覆盖固定cut且无history_window，再封停审零积压/未知后恢复原三服务。99任务/240 Agent outbox/session/配置/绑定保持，群Kimi、私聊Pi不变，无新模型任务或业务消息。

25模块启动来源及实际解析配置一致；使用新CLI health/conversations读取两条路由正常。60秒真实run loopback-http-short-20261116：12采样、零错误、截止账本/来源/seal通过；不算24h。

新有界本地采集loopback-http-24h-20261116于北京时间2026-11-16 17:19:08启动，固定2026-11-17 17:19:08截止，每30秒采样。原bridge聊天自动化仍已删除，无替代定时任务；采集器只读本地HTTP/SQLite、自行封存，不唤醒聊天或维护业务。时间未到，自然refresh仍缺，不宣称完成。

当前无凭据源码及E140已测wheel候选包在local/loopback-deployment-20261116/bundle/；源码来自本阶段文档提交，产品模块仍10758eb，二者分别核对。包校验记录单独保存，不包含本机账号/DB/下载/日志或官方DWS二进制。安装和当前运行/维护说明在包内源码文档，仍非全部MUST最终交付。

第一次本轮来源核对使用手写Projects大小写路径，manager归属字符串检查正确拒绝；改用现有cwd规范路径后通过。此失败发生在只读来源核对之前，未开始采集/维护，没有修改manager记录或绕过校验。

[脱敏部署证据](../evidence/2026-11-16/local-http-deployment.json)。私人日志/六库/观察审查只在local/loopback-deployment-20261116。UI/原生语音/私聊引用/长期与自然续期仍未完整，51/11/2和七MUST保持。
