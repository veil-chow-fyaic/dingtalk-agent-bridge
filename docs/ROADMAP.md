# 交付路线图

E166 已在原组织宿主加载 0.2.5（来源 `5d1c09e`），独立 transport 仍为 E156 的 `d444ccf`。钉钉插件负责消息、原件和回复投递。工具、数据源、凭据和执行权限归宿主。 本阶段以宿主原有工具验收。业务查询权限、网络可用性及新的业务连接由宿主运营方管理。 [现场收据](../evidence/2026-11-19/host-owned-tools-and-channel-boundary.json)

实际宿主、版本及取消边界见[组织试点结果](resident-openclaw-pilot.md#现场加载版本与本轮试用)。

核心 IM 已可使用。CLI、HTTP 和持久 consumer 独立，模型、会话及回复正文由可选的 Agent 宿主负责。E155 已通过 OpenClaw 原生通道群聊及私聊的真实文件交办与客户端下载。E156 核对了 `d444ccf` 的 26 个运行模块，部署时三项服务为 transport、群 Kimi 和私聊 Pi。 [能力总览](102-user-requirements-and-roadmap.md) · [E155 文件验收](155-openclaw-two-route-file-acceptance.md) · [E156 部署](156-native-channel-deployment.md)

常驻组织 OpenClaw 已完成授权群聊和私聊的文件任务、两轮续接及通道恢复。第一轮完整回切和再次接管已通过；E164 解决了旧取消输入的回切阻塞，保留历史状态并验证无重放。E154 的旧群发送保留原键。Hermes、DeepSeek Harness 随后分别评估 ACP 接入。 [现场验收](resident-openclaw-pilot.md#现场验收) · [适配器选型](152-community-agent-adapters.md)

原 PRD 的 14 项 MUST 已通过 13 项。剩余 R06 中，普通账号主动发送原生语音条已按用户意见暂缓，可发送 WAV 原件。 [PRD](../plans/completion/01-PRD.md) · [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)

## R01：配置与目标环境交付

**已完成。** 源码中的配置助手 `select` 已修复同账号新增路由漏继承 `imageUploadBinary` 的问题；不会因此赋予另一账号的 profile 或权限。独立安装、CLI/HTTP/consumer 与图片契约已有验证。HTTP 服务启动也已移除对反向 DNS 查询的依赖，保留真实 loopback 绑定、端口和认证行为。[配置证据](145-delivery-and-recovery-closeout.md) · [实际 CI 根因](149-github-public-launch-and-ci.md)

**E150阶段现场核验已完成。** E150当时部署产品 `0e151fb`：25模块与同一已测MIT wheel及实际启动来源/配置一致；原三受管服务恢复，99任务/240 Agent outbox/session与原绑定保持，固定cut补读及零积压审查通过。部署后60秒12采样零记录错误，截止覆盖与启动来源核验通过。 版本与已测wheel/启动来源逐项核对，R01按原判据收口；后续文档HEAD另计。

## R06：原生语音双向与准确媒体能力

**已经可用的文件能力。** WAV/MP4 群/私聊双向原件、下载、播放已验，MP4 在钉钉中已有视频卡片。语音文件和聊天语音条不同；独立 `video` 协议标签未验，不等于视频卡片/播放不支持，也不构成另造通道的理由。[私聊音视频](34-audio-video-file-progress.md) · [群音视频](103-aic-group-media-and-result-contract.md)

**入站已验。** 群聊 4.32 秒（11,674 字节）、私聊 3.68 秒（9,932 字节），两条 Ogg/Opus 单声道原件均完整解码、进入独立 consumer 的 ready 队列，并在钉钉客户端播放。[E151 实测](151-native-voice-and-image-saving.md)

**出站仍受限。** 固定 DWS v1.0.67 的 `audio` 按文件发送。两路各转发原语音一次，都只得到文字 `[语音]`，资源数为 0，客户端没有播放控件。尚无可用的普通账号原生语音创建入口；发音频可用已验的 WAV 文件。后续如官方提供普通账号原生语音上传及发送契约，再用同一身份核对接收方可播放的语音气泡、原件和历史资源。

## R07：附件任务核心与组合体验分开核对

**原判据已有证据。** R07 要求“附件能进入 Agent、真实工具完成工作、文件回原会话”。[E095](100-aic-group-resume-and-files.md) 已在群完成两条附件关联一个任务、真实 Python 处理、同群两份文件交付及客户端下载打开/SHA；[E017](37-multiple-files-and-followup.md)、[E026](45-single-message-two-images.md) 补私聊多文件和单消息双图处理。无需用私聊证据替代群，也不因后续某次模型失败否定已验证的核心能力。

**组合消息的实测范围**

- [E131](132-group-multi-image-and-provider-denial.md) 群双 PNG 当次 Kimi 403，未执行工具、未交付文件。该任务继续失败；不循环探测、重发或换 runtime 绕过。只有既有服务恢复的新证据且仍需该样本时，再验证新的明确任务。
- E134/E146 核对了双路图文的官方原件、客户端呈现和发送身份。E151 改从会话「文件」的「图片及视频」逐张打开查看器并保存，四张磁盘原件均与原发送顺序和 SHA-256 匹配。[现场记录](151-native-voice-and-image-saving.md)
- 初始矩阵已有“单消息多附件”四方向，格子继续保留。原 R07 必要列未写任意附件必须合成一个气泡或每张内嵌图必须原生另存；这些组合边界与核心文件任务分别报告，不能自动追加为所有原有任务都要重做的门槛。

**现成使用方式。** 多文件一起处理采用已验的多条附件关联；原件交付采用逐条原生 image/file。双 PNG 图文可逐图保存。需要一次取得多个普通文件时可交付一个 ZIP；任意普通多附件单气泡仍未实现。

## R13：原观察、错误恢复与续期分项判定

**已有证据。** 原要求为持久收发、去重/断线/未知状态、附件完整性/重启和可观察错误。E144 保存窗口中 31 次 history 错误后两路均自行恢复，最长观测上界 47.764 秒；这不是零错误或上游无丢失证明。[错误恢复记录](145-delivery-and-recovery-closeout.md)

[E028](47-natural-auth-rollover.md) 已证明正常自动续期：官方在旧 access 到期前更新有效期，跨旧到期点后双路完整同步继续。过期或撤销 refresh 凭据后的恢复仍未证，系统凭据故障永久根因也未解决。不要把这些异常场景与正常自动续期混为一项“从未通过”。

2026-11-17 截止的 24 小时观察覆盖了当时部署的版本。2877 次采样中服务均可达，29 条路由错误均观察到后续恢复；严格的零错误指标未通过。E156 的新版本有独立的 60 秒、13 次采样及启动来源核验。 [原观察与恢复](150-native-voice-and-acceptance-scope.md) · [E156 观察](156-native-channel-deployment.md)

## SHOULD：独立演进，不增加核心交付门槛


| 项目 | 已有基础 | 下一步与验收 | 启动条件/边界 |
|---|---|---|---|
| R15 官方办公流程 | 受管 DWS 文档、待办、日程、邮件、个人钉盘、听记已有局部闭环 | 根据一个实际用户工作流补精确对象、权限、结果回读和必要客户端交付；密送等仅在其独立读取证据存在后声明 | 办公可选；默认策略不扩大，不因会议/文档能力增多而替代 IM 验收 |
| R16 跨组织/外部联系人 | 身份与路由隔离已实现，同组织证据保留 | 未来用用户已有且明确授权的真实外部联系人/会话，核可见性、发送者、收发/资源访问和明确拒绝；按普通账号/bot 分层记录 | 当前多人暂跳过；不加人、不建 bot、不改权限；没有授权样本就维持未验 |
| R17 流式卡片、审批、执行中追问 | 状态/取消/new 和任务审计已具备 | 由一个实际交互需求选择官方可用入口，核审批前无副作用、拒绝/取消/超时、重连不重复；先确定普通账号与 bot 的能力边界 | 不把完整管理平台列核心阻塞，不因有卡片 API 就替用户启用新身份 |
| 既有执行器与多宿主并发 | Kimi/Codex/Pi 各自已验范围；原生 OpenClaw 双路文件已验，内置 CLI 适配有合成契约验证 | E154 旧未知按原键保留。旧取消输入的回切审查与 Pi 图片分别跟踪；多宿主并发按实际需求安排 | 原 R09 已满足；不索取/复制其他 runtime 凭据，不以四 runtime 全过为前置。C05 不凭假设扩建 |

## GitHub 跟踪与交付

既有四个跟踪项保留在[原 MUST 交付验收里程碑](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/milestone/1)：[R01 配置集成](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/issues/1)、[R06 媒体范围](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/issues/2)、[R07 组合图片与多文件](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/issues/3)、[R13 可靠性](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/issues/4)。按本次原判据复核更新每项的核心结论与扩展缺口，不因 issue 标题或历史状态自行增加门槛，也不隐藏失败。

不按格式、方向或历史阶段拆出重复 issue。主维护者负责最终范围、发布及现场核对；原身份、聊天、截图、日志、数据库、下载和凭据不进 GitHub。更新本项目的授权不等于向上游发 issue/PR。全部约定 MUST 和[最终自检](../plans/completion/10-自检清单.md)满足后才签最终交付。
