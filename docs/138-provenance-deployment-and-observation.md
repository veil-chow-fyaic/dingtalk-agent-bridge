# 启动来源正式部署与新实际观察

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->

E138，2026-11-16。部署产品`f322402`（E137，24模块）；不是本阶段后续文档HEAD。原99任务、240 Agent outbox、session、配置及Kimi/Pi绑定保留，无新业务消息、模型任务或UI验收。

先停gateway、封新调用并排空，停transport后保存六库；对存在的SQLite旁文件采用持有归属锁的只读事务＋backup审查，不删旁文件、不把它们当成空。只启transport补读固定cut，同一SQLite快照watermark达cut且没有history_window后再封调用/停传输，核零候选任务/未知模型/未决投递，恢复原三服务。启动证据在三个服务均核验通过，DWS持久准入ready；不调用auth/login/doctor，也没有凭据修复。

60秒实际短采集`startup-provenance-short-20261116`完成12采样，零记录错误/新事件；截止账本、两路覆盖、预声明收尾、统一启动来源及seal均通过。实际elapsed包含约9秒收尾，未改原60秒cut。短采集不是24h或消息收发成功证明。

新观察`startup-provenance-24h-20261116`在北京时间**2026-11-16 15:20:14**启动，固定截止为**2026-11-17 15:20:14**，86400秒、30秒采样。仅在新版本稳定后启动，旧两run不重置或追加。到期按原run自动保存账本并单独review；自然失效refresh仍需其本身证据，启动不算完成。没有开机自启；机器离线或睡眠会如实形成缺口。

原bridge心跳实查PAUSED且仍绑定旧聊天。本轮已询问是否恢复并迁到当前聊天，在答复前保持暂停；观察器是当前显式启动的独立进程，不是恢复了心跳。

无凭据候选包在`local/startup-provenance-20261116/bundle/`：f322402源码归档751文件、750项manifest全匹配，同一已测试wheel24模块一致、无已知私有值。源包与wheel的源码/文档冻结边界见CHECKS/README，不称最终全产品交付。原生媒体、私聊入站引用、E134组合客户端闭环及自然refresh等仍缺。

[脱敏结果](../evidence/2026-11-16/startup-provenance-deployment.json)；原始维护/六库/版本记录在`local/startup-provenance-20261116/deployment/`，短采集审查及候选包在上级目录。真实24h原始只在`local/service-observations/startup-provenance-24h-20261116/`。
