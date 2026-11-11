# 证据台账
| ID | 等级 | 结论 | 可检查资料 | 剩余限制 |
|---|---|---|---|---|
| E001 | L5 | veil→liev原群/私聊、TXT/CSV、3个文件下载打开、上下文、无循环与重启 | docs/27；evidence/2026-11-11/two-account-ui-observations.json及two-account-ui-ledger.json | 其他媒体/外部/实时事件未通过 |
| E002 | L3 | 73自动测试及已知ID/令牌脱敏扫描；Git基线166b11b、baseline/ui-2026-11-11 | scenario-regression.json；git show；handoff-manifest.json | 单元测试不代替UI；还需持续隐私门 |
| E003 | L1 | 完整用户消息复盘与本计划，区分MUST/SHOULD、Kimi已满足任选执行器 | 01-PRD.md、CURRENT_MISSION.md | 计划不代表实现完成 |
| E004 | L5 | PNG/PDF群/私聊双向UI发送/可见，8案例10资源摘要一致；群/私聊PDF客户端下载打开；图文识别双端UI结果正确 | docs/28；media-matrix-ledger.json；本机local/ui-matrix-20261111 | 未下载打开所有出站图片；其他类型继续测 |
| E005 | L4 | 独立DWS Stream真实群5/私聊11事件，全部history匹配、无重复、正常退出 | media-matrix-ledger.json；本机local/event-captures/ui-matrix-20261111 | 仍非服务唤醒/断连/长期验收；跨时钟延迟仅样本估计 |
| E006 | L3/L5 | 图片资源别名误拦截修复；75项核心回归＋新增Git暂存隐私测试；真人图文任务验收 | scenario-regression.json；代码与docs/28 | 原blocked保持审计，未静默重跑；隐私扫描只覆盖已知值/私密路径/私钥模式 |
| E007 | L4/L5 | 常驻Stream业务唤醒、双账号服务停机补漏、群订阅子进程自动重连；5条UI消息、3任务6回复，12旧任务/28旧投递/33日志保持 | docs/29；stream-integration-ledger.json；stream-integration-ui-observations.json | 优雅进程中断非网络分区/凭据过期，24h未通过 |
