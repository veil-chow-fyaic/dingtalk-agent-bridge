# 续作前置核对

1. 读AGENTS、[HANDOFF](HANDOFF.md)、[当前任务](CURRENT_MISSION.md)；保留原核心工作树，复用独立工作树，从已核实的受保护 main 派生本阶段分支，先核未提交改动归属。
2. 按 E156 收据核当前产品 `d444ccf`、26 个模块、原群 Kimi 与私聊 Pi 的执行归属。公开 main 和文档 SHA 分别核对。常驻接管前检查 E154 旧群原键及隔离收据、其他未决和待处理输入。 [E156 部署](../../docs/156-native-channel-deployment.md)
3. R06 部分通过。E151 真实语音入站及四张组合原图保存已验，两路转发只留下文字。遇到新的普通账号原生发送入口后再核出站；既有通过项及相同失败路径不重跑。
4. 仅为下一动作核必要现场状态；维护先gateway停、封调用/排空/transport停/持锁备份，transport-only同快照watermark≥固定cut且无history_window，再停审积压后恢复。故障不自动resume。
5. 原run已收尾，不重置/重审/补截止；两并发/90+15秒/固定v67和授权会话不变。凭据/系统/共享bus禁令依AGENTS。
6. 提交前review_documentation、review_acceptance、verify_handoff写manifest后复核、verify_privacy暂存blob和git diff --check。公开MIT及GitHub更新已有授权；仅邮箱等树规范化发布，原身份/聊天/截图/日志/DB不上传。

未通过coverage保持真实结果；无聊天定时任务，全部MUST及自检满足才签署。
