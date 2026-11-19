# 变更记录

## OpenClaw channel 0.2.2

宿主已在原进程报告插件 `0.2.2` 及已校验的版本配置，群和私聊仍由同一组织 Agent 各自处理。本轮加载后未发出新的真人任务。此前私聊已实测模型中止；新版本的持久取消关联已在两个隔离真实 SDK 验证。 E160 上一笔未知入站保留，严格回切仍会拒绝。 [现场验证](docs/resident-openclaw-pilot.md#现场加载版本与本轮试用)

## E160 · 组织宿主再次接管

完整回切后，钉钉群聊和私聊重新接入原组织 Agent，两份原会话均可续问。真人私聊的 `/stop` 已中止模型；该次入站仍缺少持久取消关联。[收据与适用范围](docs/resident-openclaw-pilot.md#再次接管与运行中取消)

## OpenClaw channel 0.2.1

A same-sender cancellation before any delivery records the canceled input and its stop message in one transaction. A previously submitted send, interrupted owner or uncertain I/O retains its original delivery state. The terminal record survives restart. Local tool actions that already completed may still be visible in the agent workspace.

## E159 · 常驻组织 OpenClaw 现场验收

群聊和私聊分别完成两轮交办，收到宿主原文和按原名返回的文件。钉钉通道单独断开期间的一条新私聊在恢复后回复一次。随后完整回切原双路执行器，复核七条物理回执。 [现场验收](docs/resident-openclaw-pilot.md#现场验收)

## OpenClaw channel 0.2.0

- Reuse an existing organization agent while preserving one session and reply destination per DingTalk conversation.
- Receive original files with OpenClaw 2026.7.1-2 and 2026.11.3. The July SDK supports reactive replies and declines proactive sends without a durable host intent.
- Start a named consumer at its reviewed handover cursor while keeping the physical route under one execution lock.

## 2026-11-19 · 阶段收尾

按普通账号 IM、程序消费和可选 OpenClaw 重整 README、入门及运行手册。已有其他消息渠道的宿主可从[组织工作区试点](docs/resident-openclaw-pilot.md)核对版本、绑定、文件交付与回退。

## E156 · PR #9合并及核心部署

E156：PR #9已合并，实际部署`d444ccf`、26模块及三受管服务已按收据核验；版本、归属和边界见[部署记录](docs/156-native-channel-deployment.md)。 原E154未知保持，OpenClaw真实双路文件证据保留；本次不签全部产品完成。

## E155 · 双路文件验收通过，合并与部署另记

E155 双路文件验收通过：群聊采用全新独立的商品目录颜色筛选任务，私聊按其真实文件接收证明核定；两路collector的modelAndTransportPassed与accepted均为true。客户端文件分别核对字节、SHA-256及唯一名称，公开记录只保留摘要和长度。 E154旧43出库单的未知投递与附件未提交仍保留当时事实；新筛色任务不是重试，不关闭旧原键，也不补造旧任务交付。 双路文件验收已满足，可进入[PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)的合并检查；是否已合并以实际GitHub回执为准。部署收据尚待单独取得，不由本次验收推定正式部署。 [证据范围](docs/155-openclaw-two-route-file-acceptance.md)。

## E154 · OpenClaw 候选现场实测（部分完成）

- 内置 gateway 的产品模式直接交付宿主正文和产物，原接单提示和短任务号可通过诊断模式开启。
- 原生通道私聊14B真实read/write及客户端文件已验，结果20、9字节和精确名称匹配。群模型43正确，但正文投递未知、附件未提交。
- 首次私聊4B把预期20写成10，客户端下载也确认是10；下一次14B算对20，但与旧输出重名，客户端保存时加了 `(1)`，精确文件名未通过。最终私聊改用未占用的新名称通过，前两次记录仍保留。
- 钉钉遇到同名文件可能添加 `(1)` 等序号；需要精确名称时，应选择本会话/钉盘尚未占用的输出名。以客户端另存后的实际字节、SHA-256和名称验收，不额外要求图形编辑器。

本候选本机回归为569项Python测试和14项Node测试；测试通过不代替真实群聊接收，也不扩写为多环境安装或本PR云CI结果。 [实测范围](docs/154-openclaw-real-files-and-client-receipts.md) · [PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)（合并与部署收据）

记录影响使用者的变化。源码中的包版本当前为 `0.1.0`，不表示已发布正式版本、存在远端 release 或通过全部验收。精确部署与证据见[当前总览](docs/102-user-requirements-and-roadmap.md)，完整历史见[证据账本](plans/completion/EVIDENCE.md)。

## Unreleased

### 项目许可与协作

- 主代码采用 MIT；原第三方声明保留。已公开[GitHub仓库](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge)，版本仍为开发阶段。

### 已实现与验证

- 固定 loopback HTTP 服务启动不再等待反向主机名解析；保留真实 TCP 绑定、线程、端口和认证行为。托管 macOS 两版本的实际阻塞栈已定位，修复已通过隔离源码与安装验证。[平台范围与原失败](docs/149-github-public-launch-and-ci.md)

- 配置助手 `select` 为同账号新增会话时继承已有图片上传 helper，避免新增路由原生图片在上传前失败；同步修正 `migrate` 离线、`select` 需只读 DWS 核对目标的帮助。源码与独立安装验证已完成。[验证范围](docs/145-delivery-and-recovery-closeout.md)
- E150 将固定 DWS 的语音标记与原件接入独立 consumer，冻结源码和同 wheel 的两种 Python 安装各通过 533 项合成测试。E151 又在群聊和私聊验证了真实语音入站与播放，两次同会话转发都只有无播放控件的占位文字。[实现](docs/150-native-voice-and-acceptance-scope.md) · [现场结果](docs/151-native-voice-and-image-saving.md)
- 群、私聊各一条既有双 PNG 组合已从客户端逐图保存并从磁盘打开，四张图片的 SHA-256 按发送顺序匹配原件。[保存方法](docs/151-native-voice-and-image-saving.md)

E150已部署产品 `0e151fb`：25模块与同一已测MIT wheel及实际启动来源/配置一致；原三受管服务恢复，99任务/240 Agent outbox/session与原绑定保持，固定cut补读及零积压审查通过。部署后60秒12采样零记录错误，截止覆盖与启动来源核验通过。

### 文档

- 重整产品入口、首次运行路径、用户/维护/历史导航，以及贡献与安全说明；不改变产品代码或原验收判据。
- 区分 R07 已有群/私聊真实附件任务、双图保存和任意多文件单气泡的验证范围；保留 E131 群双图任务失败。E028 已证明正常自动续期，失效 refresh 凭据恢复仍未证；零记录错误作为独立观察指标，不改写原 R13 判据。

原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。

## 0.1.0 — 当前开发版本

以下为已经实现或验证的开发里程碑，日期不是正式发布日期。

### 2026-11-17

- 私聊原生引用补齐 UI、history 和 consumer 证据；源关系保持，未触发额外任务。群/私聊引用双向已有真实验证。
- 恢复本机原生截图路径后，核对两路既有图文组合的完整文字、双图顺序、发送者与 AI 标识；逐图客户端保存仍失败，未扩大为完整组合验收。[阶段记录](docs/147-native-ui-recovery-and-dm-quote.md)

### 2026-11-16

- 历史同步失败或不完整时持续显示错误状态，避免重启或显式同步掩盖失败。
- 隔离损坏图片标记、单条附件缓存 I/O 与循环链接问题，允许后续合法消息继续消费。
- 增加绑定精确 Git 提交、验证记录和已测 wheel 的离线导出工具。[交付说明](docs/144-offline-release-export.md)
- 本机 HTTP 客户端统一直连并拒绝重定向，避免代理环境将本机接口请求转交其他地址。
- 提供单条文字＋有序 PNG/JPEG 的组合发送；API、官方原件和用户端可见层分别验收。该阶段部署产品为 `2b479a8`。[部署记录](docs/143-parallel-hardening.md)

### 更早的基础能力

- 独立 CLI、loopback HTTP API、持久 consumer；group/direct 多路由与显式身份。
- 持久发送回执、幂等、未知状态对账、原件缓存与摘要校验。
- 可选 gateway 的任务/session/outbox、发送人白名单、取消和恢复；Kimi/Codex/Pi 有各自真实验证范围，当阶段OpenClaw尚缺真实模型验收；后续原生通道私聊实测见E154。

历史失败、未证类型与长期可靠性证据保持在[验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md)。本记录不承诺任意格式、所有组织、所有模型或持续无错误运行。
