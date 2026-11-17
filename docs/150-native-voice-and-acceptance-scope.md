# E150：原生语音入站实现与验收范围复核

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-17。本次补齐一个实际代码缺口：固定 DWS 已有原生语音历史标记和原件下载能力，bridge 先前没有将该标记解析为可下载、可消费的媒体。修复后，语音正文、资源及引用关系进入既有原件校验链路。**这是入站实现和合成验证，尚非真实语音条双向验收。** 普通账号原生语音条出站仍未实现。

候选登记为 `0e151fb78a61e44cf2d593c58ac559bd9d598f9c`，DWS 保持 v1.0.67。候选冻结时运行产品仍为 `2b479a8`，原固定观察尚未收尾；不能用候选提交或测试通过代替部署、24h 和客户端证据。

E150已部署产品 `0e151fb`：25模块与同一已测MIT wheel及实际启动来源/配置一致；原三受管服务恢复，99任务/240 Agent outbox/session与原绑定保持，固定cut补读及零积压审查通过。部署后60秒12采样零记录错误，截止覆盖与启动来源核验通过。

原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。

原MUST仍缺：R06；真实未验格保持，尚未完成全部验收。

## 入站修复与官方边界

固定官方提交 [`63a7c49`](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/tree/63a7c4906c7dee10750011ea309b9eb78abb7eb0) 的 [connect_chatrecord 实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/helpers/connect_chatrecord.go#L256)和[配套 fixture](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/helpers/connect_chatrecord_test.go#L37)包含 语音消息标记（mediaId 资源引用），可伴随转写正文。官方[资源下载](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/helpers/chat.go#L7855)以 mediaId、原消息及会话身份取得音频资源；本次所读文件均与固定源码归档逐字节一致，没有升级或修改 DWS。

旧 bridge 把带语音资源引用的消息记为 `unpositioned_resources`，没有媒体 part，因而无法进入原件物化和 ready 队列。本次只扩展 [message_model](../dingtalk_bridge/message_model.py) 的有序标记解析：语音成为 `audio`，转写正文与图片/语音顺序保持；缺资源、残缺标记和无法定位的资源继续阻断 ready。引用资源留在原引用消息，既有账号、会话、发送者和群执行策略不变。

原件仍经现有 `+messages-mget --download-resources` 取得，沿用本路已读消息、返回消息/会话、缓存目录、完整下载、大小与 SHA 校验。没有新增下载协议、自动转写或模型调用。已持久化 inbox 不会因升级自动重新解析；真实续验应使用部署后新接收的授权消息。

出站的[原子发送](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/helpers/chat.go#L4326)和[统一发送](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chat/unified_send.go#L836)均将普通用户 `audio` 映射为 file，不能产生聊天语音条。[Raw OpenAPI](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/app/api_command.go#L74)需要自有应用凭据，不是当前普通用户身份的替代入口。

本轮在原授权群和私聊检查 Mac 9.0.5（59563623）的输入框及更多菜单，未见录制语音入口；没有发送消息、发起通话、录音或改权限。观察来自当次 CUA AX/截图，未另保存原始截图文件，私有记录仅保留摘录。它不证明所有 Mac 版本都不支持。官方普通用户市场目录另按“消息”“聊天”各查询一次，分别返回 10/7 项，其中官方 6/4 项；没有建立相关普通账号原生语音服务入口，因此未猜 MCP ID、未调用 tools/list 或业务工具。市场并非账号所有内部服务的完整目录，这也不是“官方永远不支持”的结论。

## 验证范围与保留失败

六个新增语音专项先在旧解析器上失败，修复后通过；相关 68 项专项通过。真实代码路径包含 Bridge、Inbox、SQLite、原件文件及重启缓存；仅 DWS 响应边界和内容使用合成数据。覆盖正文/混合媒体顺序、引用来源、缺失或伪标记、跨账号/会话、错误原件及后续消息继续消费，未调用真实 DWS 或模型。

首轮完整验证为 532 项：源码和 Python 3.14 安装通过，Python 3.11 安装出现一次 Stream 清理测试读取 `child.pid` 缺失，原失败保留，系统细因未知。后续只拆分该测试的启动准备与真实超时清理契约，增加一项测试，产品逻辑未因此改变。最终冻结源码、同一 wheel 的 Python 3.14.6 与 3.11.15 独立安装**分别 533 项、0 failure、0 error**，每个环境只运行一次；不把首次失败改成通过。

结果见[首轮记录](../evidence/2026-11-17/native-voice-inbound-initial.json)和[最终验证](../evidence/2026-11-17/native-voice-inbound-validation.json)。最终复用已包含语音修复的同一 wheel，SHA256 为 `865d05154cc61e0011d2333a00f6ff9f86564607ef1e74f04a3c9b5a4eff60ed`；后续仅测试文件变化，没有重复构建新 wheel。合成原件字节不证明音频可播放，测试数量也不证明真实语音、现场部署或24h通过。

## 媒体与文件能力

| 用户要做的事 | 已有实现和真实证据 | 未实现或未验证范围 |
|---|---|---|
| 收发常用文件与图片 | TXT/CSV/PDF/DOCX/XLSX/ZIP、PNG/JPEG 的群/私聊双向原件及客户端获取已有样本 | 不外推全部格式、编码、超大或复杂文件；详见[矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) |
| 收发音频文件 | WAV 群/私聊双向原件、客户端下载和播放器已有真实验证 | 不是聊天语音条；不外推 MP3/M4A、长录音或自动转写所有输入 |
| 收发视频文件 | MP4 群/私聊双向原件；钉钉视频卡片、实际播放、下载及系统打开已有证据 | 约1秒小型 H.264 样本，不外推全部编码/时长；独立 video 协议未验，不影响已证明的客户端能力 |
| 接收原生语音条 | 入站解析、转写正文保留及原件到 consumer 的代码已实现，群/私聊合成链路通过 | 群入站、私聊入站的真实语音资源、编码/时长、播放和部署后 consumer 交付均未验 |
| 发送原生语音条 | 当前固定 DWS 可发送音频文件 | 群出站、私聊出站的原生语音条未实现、未验；没有已确认的普通账号官方发送入口 |
| 多个文件交给同一任务 | E095 群两条附件关联一个任务，真实工具处理、同群两输出及逐件下载打开/SHA；E017 私聊同会话合并处理 | 不等于任意多个附件合成一个气泡 |
| 单条文字加多图 | E026 私聊双 PNG 真实工具和报告；E131 群双 PNG 入站原件；E134 两路组合 API/history/四原件及 E146 完整呈现/发送者/AI 标识 | E131 对应 Kimi 任务403失败无交付；组合逐图客户端下载仍失败或未证；1–9图为代码范围，真实只验双PNG |

文件播放证据：[私聊音视频](34-audio-video-file-progress.md)、[群音视频](103-aic-group-media-and-result-contract.md)。出站单文件上限仍为20MiB，原生 image 使用 PNG/JPEG ≤2MiB。用户要求继续找语音双向办法；若现有范围确实做不到，保留上述实现/未实现清单并推进其他独立工作，不用文件语义冒充语音条，也不只为另一协议名称新增通道。

## R07：核心任务闭环不由组合扩展格抵消

对初始 PRD（本地提交 `c3e1b17`）与当前版本逐项复核，17项级别及判据文本未变。原 R07 是“附件能进入Agent、真实工具完成工作、文件回原会话”。[E095](100-aic-group-resume-and-files.md) 已从群原生 UI 上传 CSV/TXT、显式关联同一任务、真实 Python 计算，回到同群交付两个文件，再由客户端下载、Numbers/TextEdit打开并比对 SHA。[E017](37-multiple-files-and-followup.md) 和 [E026](45-single-message-two-images.md) 另证私聊多文件、单消息双 PNG。不能把这些仅表述为 API 成功，也无需拿私聊代替群证据。

初始矩阵已包含单消息多附件四方向，相关格子继续保留；原 R07 必要列没有要求任意文件必须在同一气泡或每张内嵌图必须通过原生菜单另存。R07核心能力与这些组合边界分项报告。[E131](132-group-multi-image-and-provider-denial.md) 的群双图任务403失败、无实际工具/文件结果，以及 [E146](147-native-ui-recovery-and-dm-quote.md) 的组合逐图保存失败均保留，不重发、换模型绕过或改绿。模型订阅问题只限制对应执行器。

用户曾明确要求真实 UI 交办、查看回复、打开文件，见[原反馈与验收](26-ui-acceptance-and-sender-identity.md)。本次复核没有取消这项体验要求：普通文件任务已有该链路，组合内每张图的保存体验仍单列不足。

## R13：续期、错误和24h分别记证

原 R13 判据为“持久收发、重复/断线/未知状态/附件完整性/重启、可观察错误”；[原自检](../plans/completion/10-自检清单.md)要求真实24h，没有“24h零网络错误”条款。现有[审计脚本](../scripts/review_service_observations.py)的 `zero_recorded_errors` 和 `stability_pass` 是更严格的独立指标，仍按其定义如实记录，不能改成 true，也不能直接等同原 R13 的全部结论。[E144](145-delivery-and-recovery-closeout.md) 已保留31次 history 错误及两路后续自动恢复，不能声称零错误或据此证明上游无丢失。

[E028](47-natural-auth-rollover.md) 已证明正常自动续期：在旧 access 到期前观测到有效期延长，跨旧到期点后两路完整同步继续。该次仍有维护期间本机 health 错误，不掩盖。失效/撤销 refresh 凭据后的恢复、需要重新授权的场景以及系统凭据故障根因未证；它们不应被混写为正常自动续期从未成功。[后续认证复核](112-dws-refresh-and-reboot-review.md)保留区别。

原run已按固定截止自然封存并审计。原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。 该窗口的产品为2b479a8，新产品0e151fb另有部署/短观察证据，不混用版本或补造截止。

## 本次交付证据

[实际部署及短观察](../evidence/2026-11-17/native-voice-deployment.json) · [原24h审计](../evidence/2026-11-17/parallel-hardening-24h-review.json) · [全窗口错误恢复](../evidence/2026-11-17/parallel-hardening-24h-recovery.json) · [语音入口调查](../evidence/2026-11-17/native-voice-capability-review.json) · [原判据复核](../evidence/2026-11-17/original-criteria-review.json)。
