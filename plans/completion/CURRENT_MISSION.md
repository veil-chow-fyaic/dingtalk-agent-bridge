# 当前任务

交付通用普通账号DingTalk IM bridge：群聊/私聊双向文字和媒体原件、真实本地Agent任务、上下文与同会话交付，CLI/HTTP/consumer不绑定runtime或组织。官方DWS优先，自研仅补明确缺口；Kimi已满足至少一个本地执行器，Codex超时独立可选跟踪。

工作区为/Users/veil/Projects/dingtalk-agent-bridge，分支codex/complete-bridge，模式build，单Agent。本计划是唯一活动计划，不重新实现或修改参考仓库，不远程发布。需求与结束条件保持[01-PRD](01-PRD.md)；结果见[矩阵](ACCEPTANCE_MATRIX.md)，详细错误与阶段事实见EVIDENCE、PROGRESS_LEDGER及99-执行偏差日志。

E071事故后用户确认弹窗停止；三个真实服务及operator_suspended保持停机状态。真实DWS、auth、doctor、Keychain和系统恢复操作禁用，不能以继续任务为由自动恢复。E082用户已允许并执行原key一次查询，因脚本错误追加--as而validation/unknown_flag失败；attempt已保留，不重试/换key。E089修正后追加一次已获准且exit0/目标匹配，当前一次读取可用；两个许可均已履行，不再待答复或重试。E090私聊恢复提案尚无后台许可；用户已回复方向和故障问题，不是启动许可。auth login与底层故障根因仍未证解决。

E091已完成[主线与现成channel复用核对](../../docs/98-channel-mainline-and-reuse-review.md)：DWS是已验基础通讯底座，bridge负责通用任务/会话/附件及可靠交付；Qwen Code普通账号DWS channel是主要参考，bot/数字员工路线明确分开。保留当前实现，只补具体验收缺口，不再增加恢复审批工具或用离线数量代替UI。心跳保持既有PAUSED状态。

E092按用户纠偏，当前优先公开GitHub/钉钉官方现成DWS真人账号通道；停止以本地WeCom/本地Agent适配器为选型主线。[公开目录](../../docs/references/README.md)固定13来源/69文件、许可和采用边界；Qwen为通道主体参照，CEO为文件交付/回执专项，bot仅辅助设计。先按[采用清单](../../docs/references/adoption-plan.md)核上游组件与实际缺口，再实现窄补充；Codex/OpenClaw/Pi/Kimi协议资料为后续扩展，未新增adapter或部署。默认身份决策不等于跨组织/外部群API已验。

原veil/liev私聊授权保持。历史曾授权原3人群；当前聊天入口要求多人实测暂跳过，后续按最新用户指示核对。身份白名单不扩大，不加第三人、建bot、改权限。没有缺第二账号的问题。

E093已落第一项公开参考代码改造：[CEO原定文件摘要校验](../../docs/references/artifact-digest-adoption.md)。修复任务产物排队后变化仍发送，保留原key回执优先/未知只对账，旧队列只从原任务证据补摘要。11新增专项，最终三环境全量各291/21模块/12核验通过，未部署/真实迁移/UI；原MUST矩阵保持。Qwen消息模型较窄，未替换现有原件/引用契约。下一独立工作核其admitted/completed接纳与任务入库关系，发现具体缺口再改。

代码：E070群文件关联、E072进程/暂停、E073官方办公入口已提交未部署；E074既有history双路与一次核验方案通过离线验证。共享Stream bus无独占退出权，候选后台恢复用history-only 15秒补读，现场配置尚未修改。后台恢复需另行明确允许。

验证：E084已应用E080续页补丁，与E083参数修复组合后实际三套全量262/21模块、10审计通过，未部署。E083254/E080候选259为历史冻结版本；E074244及E076工具5专项保持历史范围。E075交接固定f0d2911，未包含其后变更，不重复导出凑进展。当前64格37历史通过、25阻塞、2部分；14 MUST中9项未完整覆盖，不能用测试数量抵消UI缺项。

原reliability-20261111及全部故障/维护继续保留，最早11月12日19:36:08后按真实样本终检；满时长也不等于连续健康。MUST/UI、实际观察、失败处置、隐私/检出/交接终检未全部满足前，不标完成或停heartbeat。[旧入口原文](../../docs/history/through-E076/README.md)仅供追溯。
