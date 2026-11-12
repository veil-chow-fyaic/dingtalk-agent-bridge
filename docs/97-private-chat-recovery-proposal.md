# E090：私聊分阶段恢复提案，尚未授权执行

E089修正后一次会话查询已成功。当前仍operator_suspended、三个服务停止；这份提案不授权任何后台调用。原E082失败、E089成功两个key均已attempt，只可复核。按事故后的AGENTS约定，恢复后台需要用户另行明确同意。

E091更新：用户已经回复，但内容是要求讲清主线、DWS能力/群验收/认证与现成项目，不是许可。[澄清与复用决定](98-channel-mainline-and-reuse-review.md)已记录；本提案继续未执行，不重复催问、不新增恢复审批工具。下面保留原冻结方案供后续明确授权时审查。

私有提案在local/deployment-proposals/private-chat-recovery-20261112/proposal.json，候选配置在同目录candidate-service-config.json；[7项静态核验和摘要](../evidence/2026-11-12/private-chat-recovery-proposal-validation.json)。原活动配置未改。提案固定E084的21模块、原配置/私聊Agent配置、E089成功receipt、原失败receipt、DWS环境、官方binary/图片补充摘要及E085/E087审查材料，执行前全部复核；任一不一致不能静默替换计划。

## 具体变化

活动路由临时只保留既有veil/liev私聊，将该路receiveMode从stream_hint改为history。群路由从活动配置中暂时移除，群transport读取和群gateway都不恢复；原群配置、数据库、任务、消息及失败记录原位保留并保全原配置。不是删群、移成员或改权限。私聊的profile、账号、peer、白名单、runtime、stateStorage与原session不变，不调用new、不改cursor。

阶段一只启动manager管理的transport，两个Agent仍停机。在启动前记录UTC恢复cut，按15秒间隔补读，观察最多300秒后停止transport并恢复operator_suspended。启动会校验私聊目标并调用真实DWS，之后history会触发凭据读取。transport自身不执行Agent或主动发消息；它的HTTP写入口仍存在且受令牌保护，所以不能把该阶段称为OS强制只读，期间不允许额外写客户端。

停止后按E088核watermark至少达到cut、无history_window，再按E085/E087核旧key、任务和本地候选。必须无未确认原投递、无未终态任务、无未经审查的新任务/通知候选、原终态记录/session保持；远端仍未知或任一条件不满足就继续停机，不修改watermark/cursor跳过，不自动重跑阶段一。原8个历史非成功任务不删、不改绿。

只有方案获准且上述条件全部满足，才进入阶段二：恢复transport和原私聊gateway，群仍停用。随后在原授权的两人私聊进行一个新的合成任务及真实UI回复/文件验收，核原session生成的新受管办公上下文。之后按原任务持续推进私聊缺项；不恢复多人群测试，不重放已确认实验，不发送业务消息或另开bot。

## 时间与失败边界

15秒是轮询间隔，**不是后台DWS请求的deadline**。当前E084传输调用实际默认90秒，另有最多15秒清理；全工作区最多2个DWS调用，manager各组件启动/停止等待45秒。阶段一300秒观察之外可能还有启动/清理等待，不承诺总耗时恰好5分钟。候选没有偷偷加未支持的CLI flag或改调用超时。

凭据存储故障、DWS超时或不确定清理触发持久暂停；停止受manager归属的服务，保留原失败/维护/未完成窗口，不自动认证重试或再次resume。任何系统窗口都不需要用户反复输密码；不执行auth、doctor、钥匙串锁定/解锁/reset或系统权限操作。共享Stream bus不启动也不强杀。本阶段仍可能发生系统授权提示，成功的一次查询不保证长期无故障。

目前仅静态验证单私聊候选与原路由存储/身份相同、产品版本匹配、成功回执绑定和私有文件权限；没有新后台或UI结果，没有新增测试数量主张。原reliability-20261111保留全部故障与本次维护，不重置为健康24h。

该具体方案已于提交36ebaa1后单独向用户申请后台许可；用户随后要求澄清产品与故障问题，尚未授权。不重复询问，不提前应用候选。私有提案SHA256为8c7e23032fbed7d3cec53fe7ea5d1e8133bba93005fa5b6b5ee5ea2865236ae2；候选配置SHA256为f52b30d7e3ede8955188c86aa1f489bc92b236d097fb2d818e89e54aa9945831。

## E095 后续状态（覆盖本页当时的待许可/停机）

用户已在新终端完成登录并提供liev成功截图，要求回主线；又明确新AIC测试群可继续，企业大群禁测。E095按新授权、新群与E093产品实际恢复history双路并完成群/私聊文件UI，见[记录](100-aic-group-resume-and-files.md)。旧E090的E084冻结提案不宣称被原样执行，旧两次query key仍保留不重放；E094诊断不被写成因果根治。系统Keychain/auth诊断等仍禁止。
