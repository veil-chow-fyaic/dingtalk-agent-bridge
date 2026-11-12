# 当前任务

交付通用普通账号DingTalk IM bridge：群聊/私聊双向文字和媒体原件、真实本地Agent任务、上下文与同会话交付，CLI/HTTP/consumer不绑定runtime或组织。官方DWS优先，自研仅补明确缺口；Kimi已满足至少一个本地执行器，Codex超时独立可选跟踪。

工作区为/Users/veil/Projects/dingtalk-agent-bridge，分支codex/complete-bridge，模式build，单Agent。本计划是唯一活动计划，不重新实现或修改参考仓库，不远程发布。需求与结束条件保持[01-PRD](01-PRD.md)；结果见[矩阵](ACCEPTANCE_MATRIX.md)，详细错误与阶段事实见EVIDENCE、PROGRESS_LEDGER及99-执行偏差日志。

E071事故后用户确认弹窗停止；三个真实服务及operator_suspended保持停机状态。真实DWS、auth、doctor、Keychain和系统恢复操作禁用，不能以继续任务为由自动恢复。E082用户已允许并执行原key一次查询，因脚本错误追加--as而validation/unknown_flag失败；attempt已保留，不重试/换key。认证仍未知，不再等待已到达的答复；先离线修官方参数边界，新的真实查询或后台恢复需新明确许可。

原veil/liev私聊授权保持。历史曾授权原3人群；当前聊天入口要求多人实测暂跳过，后续按最新用户指示核对。身份白名单不扩大，不加第三人、建bot、改权限。没有缺第二账号的问题。

代码：E070群文件关联、E072进程/暂停、E073官方办公入口已提交未部署；E074既有history双路与一次核验方案通过离线验证。共享Stream bus无独占退出权，候选后台恢复用history-only 15秒补读，现场配置尚未修改。后台恢复需另行明确允许。

验证：E074三套全量244/21模块，E076工具5专项三环境。E075交接固定f0d2911，未包含其后变更，不重复导出凑进展。当前64格37历史通过、25阻塞、2部分；14 MUST中9项未完整覆盖，不能用测试数量抵消UI缺项。

原reliability-20261111及全部故障/维护继续保留，最早11月12日19:36:08后按真实样本终检；满时长也不等于连续健康。MUST/UI、实际观察、失败处置、隐私/检出/交接终检未全部满足前，不标完成或停heartbeat。[旧入口原文](../../docs/history/through-E076/README.md)仅供追溯。
