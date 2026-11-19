# 当前任务池

- [x] E164 完成旧输入核对、双路回切和再次接管。
- [x] E165 交付按群参与、连续附件与原件关联，并在原组织宿主完成真实 GitHub 工具及两路混合文件验收。 [业务样本和模型限制](../../docs/agent-im-workflows.md)

唯一活动清单；标准在[PRD](01-PRD.md)/[矩阵](ACCEPTANCE_MATRIX.md)，现状在[总览](../../docs/102-user-requirements-and-roadmap.md)，全部既有工作在[EVIDENCE](EVIDENCE.md)/[账本](PROGRESS_LEDGER.md)。

- [x] E152 核对原始需求与三类宿主的普通账号社区项目、官方协议、媒体与可靠性边界。[E152 适配器调查](../../docs/152-community-agent-adapters.md)
- [x] E153 新分支实现产品/诊断呈现和 OpenClaw 原生通道。[E153 实现与验收](../../docs/153-channel-presentation-and-openclaw.md)
- [x] E154原生OpenClaw私聊14B真实read/write、正文及客户端唯一9字节文件通过；4B错误和14B重名失败保留。
- [ ] E154 旧群原键只在出现可核对的新回执时复核。E156 已把这一个键单独隔离。正文request_failed/outcome_unknown，无openTaskId/messageId且历史未命中，附件未提交；不换键重发。
- [x] E155原生通道双路真实模型/运输及客户端文件验收；新群商品筛色任务独立于旧43未知。
- [x] E159 已有组织 OpenClaw 接管原授权钉钉双路，验证文件任务、独立两轮、无桥接前缀和仅断开钉钉通道后的恢复。 [E159 现场收据](../../evidence/2026-11-19/openclaw-resident-live-pilot.json)
- [x] E163 工作区身份知识已在原群确认，隔离 SDK 已验证日期文件读取及工作区技能。 [用户场景](../../docs/agent-im-workflows.md)
- [x] 原组织宿主恢复后，两条原输入各处理一次。真实记忆检索、技能手册三项判断和私聊 TSV 下载已验。
- [x] E166 按组织自身权限从钉钉临时查询未同步的 PR，核对真实拒绝原因并移除桥内工具。
- [x] E166 以实际两表对账完成宿主工具、正文、文件及钉钉接收端验收。
- [ ] 若宿主获配可用的公开数据源，复验实时外部查询。该项与 IM 传输验收分别记录。
- [x] E162 群聊真实取消已验证模型中止、零次发送尝试和唯一持久关联。 [现场收据](../../evidence/2026-11-19/openclaw-resident-live-group-cancel.json)
- [x] E161 核验运行中插件版本、同一消费者和两条原宿主会话。 [现场记录](../../docs/resident-openclaw-pilot.md#现场加载版本与本轮试用)
- [x] E160 真实 `/stop` 中止模型，未观察到最终正文或迟到投递。再次接管保留双路会话，后续独立查询正常。
- [x] E164 已隔离原发起人叫停的历史入站，保留 `unknown`。真实回切和再接管、新私聊续问均通过。 [E160 现场与测试收据](../../evidence/2026-11-19/openclaw-resident-reentry-and-cancel.json)
- [x] 第一轮六阶段完整回切已恢复原两个 gateway，核对原程序与会话、七条试点物理回执和 E154 原隔离。 [回切步骤](../../docs/15-service-runbook.md#已有-openclaw-的常驻钉钉试点)
- [x] [PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)四项CI通过并合并；[E156部署收据](../../docs/156-native-channel-deployment.md)核对26模块、原三服务及短观察。该次部署仅启用原内置执行器。
- [ ] 复用 ACP 对接 Hermes、DeepSeek Harness，按各自宿主验证会话与任务交付；Hermes 自带 Gateway 通过外部平台插件接入。
- [x] 通用CLI/HTTP/consumer、双路文字/常用文件/PNG/JPEG/WAV/MP4、引用、持久任务/session/outbox与原件同会话交付。
- [x] E150三处产品修复：无DNS启动、新路由图片helper继承、原生语音标记与原件消费；533项源码及双Python安装各通过，独立审查完成。
- [x] 原parallel-hardening固定24h run自然收尾审计，失败/错误原样保留，不重置。原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。
- [x] E150按停gateway/封排空/持锁备份/transport-only固定cut/停传输审积压/恢复完成部署与短观察。E150已部署产品 `0e151fb`：25模块与同一已测MIT wheel及实际启动来源/配置一致；原三受管服务恢复，99任务/240 Agent outbox/session与原绑定保持，固定cut补读及零积压审查通过。部署后60秒12采样零记录错误，截止覆盖与启动来源核验通过。
- [x] R01按已验新配置/安装/部署证据收口；R07按E095群真实工具/原件回传和E017/E026私聊证据收口，原判据不变。
- [x] R13按原持久收发/重复/断线/未知/附件/重启/可观察错误判据及实际24h审计判断；正常access续期E028已证，invalid refresh恢复未证、零错误false分别保留。
- [x] E151 真实原生语音群/私聊入站。两条音频已下载、完整解码、进入独立 consumer 并在客户端播放。
- [ ] R06 原生语音出站（按用户意见暂缓）。固定 DWS 新建音频走 file，两次同会话转发均缺音频资源和播放控件。替代为 WAV 文件；独立 video 协议格继续未验，MP4 卡片和播放已验。
- [x] E151 组合图片逐图保存。群/私聊两条既有双 PNG 消息共四张，客户端保存、磁盘打开与原顺序 SHA-256 全部通过。
- [ ] 任意普通多文件同一气泡尚未实现。
- [ ] 全部MUST及最终自检签署，当前fullProductAcceptance=false，剩R06。

## 仓库与后续演进

公开MIT仓库、受保护main/四环境CI、安装与许可门、问题/里程碑、隐私和完整清单已建立。本次最终文档/证据通过PR同步，实际CI和远端SHA以发布回执为准，不与原本地SHA或部署SHA混用。

用户要求已授权事项直接闭环，不要靠定时提示推动；原bridge聊天自动化已删除。仅对明确新入口或真实缺口继续，不重复旧受阻点击/403探测，不以巡检或文档数量充进度。

E154旧未知投递及OpenClaw未覆盖的真实生命周期、Pi图片、R15办公更多流程、R16跨组织/多人、R17流式/审批、C05多宿主仅实际需求和现成授权条件具备时独立推进。R09至少一个执行器已满足。现场范围、凭据及系统禁令保持AGENTS。
