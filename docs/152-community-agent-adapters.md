# 普通账号 IM 通道怎样接入 OpenClaw、Hermes 和 DeepSeek Harness

2026-11-18 · E152 · 选型记录。核对了原始需求讨论、初版 PRD、本仓实现，以及下列项目的发布记录、接口和源码。本轮核验范围是社区实现与宿主契约。本仓已验的执行器和拟新增的接法在文末分列。

## 用户需要完成的事

在钉钉群聊或私聊发送文字、图片或文件，程序以普通账号收到消息和原件，让指定 Agent 在对应会话中使用工具处理，再将可打开、下载的结果送回原会话。群里没有 @ 的普通消息也能进入通道，哪些消息交给 Agent 执行由路由策略决定。换执行器时，账号、会话隔离和投递对账仍由同一套 bridge 负责。[原始范围整理](12-requirements-and-scope.md) · [验收基线](../plans/completion/01-PRD.md) · [已交付的 CLI、HTTP 与 consumer](22-generic-tool-and-consumer.md)

普通账号是为了沿用用户已有的聊天关系。跨组织覆盖仍待授权样本，多人现场测试暂缓。办公工具优先通过 DWS 按需调用。用户已明确将程序以真人账号主动发原生语音条暂缓，音频出站可发 WAV 文件，手机发来的原生语音已能接收和播放。原 R06 的部分通过状态继续记录。[能力表](102-user-requirements-and-roadmap.md) · [媒体验收](151-native-voice-and-image-saving.md)

## 现成项目能用到哪一步

| 宿主 | 普通账号 DWS 先例 | 已发布的宿主能力与采用判断 |
|---|---|---|
| OpenClaw | `cuyua9/openclaw-dingtalk-auto-reply` 读取私聊、回复文字。源码使用固定 DWS 路径，按发送者、时间和内容辨认消息，并写入 OpenClaw 会话文件。所核版本没有群聊和媒体收发。[DWS 实现](https://github.com/cuyua9/openclaw-dingtalk-auto-reply/blob/17caf9f1763a8cb8a6220c84819ba6afa4e68acb/src/dingtalk_auto_reply_openclaw/dws.py) · [同步代码](https://github.com/cuyua9/openclaw-dingtalk-auto-reply/blob/17caf9f1763a8cb8a6220c84819ba6afa4e68acb/src/dingtalk_auto_reply_openclaw/sync.py) | 钉钉维护的连接器 v0.8.27 已发布，具备多账号、文本和媒体出口，IM 使用企业应用机器人和 Stream。社区 soimy v3.9.1 有通过的 CI，可参考其媒体与恢复用例。适合本项目直接采用的是宿主公开的 `ChannelPlugin` 接口。[官方版本](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector/releases/tag/v0.8.27) · [身份要求](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector/blob/88df00ee594072e9941ef3f71da90a37f3291ad3/docs/DINGTALK_MANUAL_SETUP.md) · [社区 CI](https://github.com/soimy/openclaw-channel-dingtalk/actions/runs/40541850855) · [宿主 SDK](https://github.com/openclaw/openclaw/blob/e13cf15ece9bbd969b7362927c315362c90c97ff/docs/plugins/sdk-channel-plugins.md) |
| Hermes | `pyinx/dws-hermes-connector` 以普通账号轮询群聊和私聊，可发文字。所核版本仅一次提交，测试模拟宿主和 CLI，作者列明图片与文件出站缺失。单会话读取失败时共享轮询水位仍可能前移。可参考事件映射。[能力说明](https://github.com/pyinx/dws-hermes-connector/tree/5aaf2e753dea7debaf91ee1c3d5a155a72c5be8c) · [轮询实现](https://github.com/pyinx/dws-hermes-connector/blob/5aaf2e753dea7debaf91ee1c3d5a155a72c5be8c/gateway/platforms/dws_dingtalk.py) | Hermes v0.23.2 已发布，内置钉钉使用机器人。已有 Hermes Gateway 可以通过外部插件注册 `BasePlatformAdapter`，把事件交给宿主，把发送委托给 bridge。由 bridge 启动 Hermes 执行任务时可用 `hermes acp`。[发布版](https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.2) · [内置驱动说明](https://github.com/NousResearch/hermes-agent/blob/ae2a81ccc00e9b7c06301523e5bb09608397149c/website/docs/user-guide/messaging/dingtalk.md) · [外部插件接口](https://github.com/NousResearch/hermes-agent/blob/ae2a81ccc00e9b7c06301523e5bb09608397149c/website/docs/developer-guide/adding-platform-adapters.md) |
| DeepSeek Harness | 有两种互补的真实项目。HiQ-AI 的 `dingtalk-dsh-assistant` 对接登记的群，有 DSH 会话、任务和投递回查，普通私聊入口已关闭。MinEagle 的 `dsh-dingtalk-self` 以本人身份读写指定私聊、绑定工作区，可回传本地文件。可借鉴群任务与私聊文件两个场景。[HiQ 群接入](https://github.com/HiQ-AI/dingtalk-dsh-assistant/blob/3006a159879e92e0b3c252b22d7ca59e737eafec/README.md) · [MinEagle 私聊接入](https://github.com/MinEagle/dsh-dingtalk-self/blob/f3b17ad461b6587ec6337f3a54ecf88560c27717/README.md) | 官方 Harness 提供 `dsh acp`，支持会话、取消与工具事件。此次核到的 v0.2.2-rc.4 为预发布。图片取决于模型能力，普通文件需传入运行器可访问的已校验资源。钉钉团队另有 Stream 机器人连接器，可选 DWS 用于办公工具。[Harness 版本](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.2-rc.4) · [ACP 契约](https://github.com/deepseek-ai/deepseek-harness/blob/3f321d32bfe382212a8ed8785c1d47a5a300aa23/packages/acp/acp/README.md) · [钉钉团队连接器](https://github.com/DingTalk-Real-AI/dsh-dingtalk/blob/137ea79505e6317d98c1db643f0fbae138e016c8/README.md) |

固定 DWS v1.0.67 的 `dev connect` 对 OpenClaw、Hermes 输出各自的接入指引。评估一个“钉钉插件”时，需要顺着收消息、发消息两个实际调用确认使用哪种身份。插件附带个人 DWS 工具，也可能通过机器人接收聊天。[DWS 固定版说明](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/skills/mono/references/products/dev.md#L282)

## 拟采用的接法与验收顺序

1. **先让已有 OpenClaw 用户能把 bridge 加为通道。** 通过原生 `ChannelPlugin` 将已配置路由的入站消息与可读取附件交给 OpenClaw，由其现有 Agent 和会话处理。文本和媒体出口都回到 bridge 的发送接口。本仓已有的 `openclaw agent --local` 是从 bridge 启动执行器的入口，真实 CLI 配合合成模型已验，真实模型与钉钉交付待验。两种模式由每条路由选择唯一执行方。[本仓执行器记录](architecture/agent-integration-map.md) · [SDK](https://github.com/openclaw/openclaw/blob/e13cf15ece9bbd969b7362927c315362c90c97ff/docs/plugins/sdk-channel-plugins.md)
2. **为 bridge 启动的 Hermes、DeepSeek Harness 复用 ACP。** 先验已发布的 Hermes，再以 DSH 为第二种实现验证能否复用。可先评估现成 ACP 客户端 `acpx` 的会话、取消和持久行为，v0.22.0 的注册表已有 DSH，支持自定义启动命令。对已绑定的 Hermes 会话要验证恢复原上下文，其 `resume_session` 在找不到原会话时会新建。分别记录绑定的程序版本、真实文件输入输出、可取消阶段和断线行为。[acpx 适配表](https://github.com/openclaw/acpx/blob/v0.22.0/docs/agents.md) · [Hermes 会话实现](https://github.com/NousResearch/hermes-agent/blob/ae2a81ccc00e9b7c06301523e5bb09608397149c/acp_adapter/server.py#L680-L705) · [DSH ACP](https://github.com/deepseek-ai/deepseek-harness/blob/3f321d32bfe382212a8ed8785c1d47a5a300aa23/packages/acp/acp/README.md)
3. **让已有 Hermes Gateway 用户沿用宿主配置。** 用外部 `ctx.register_platform` 插件接同一 bridge，在 Hermes 平台列表提供普通账号通道。先复用 OpenClaw 首次集成中验过的账号、会话、消息与附件映射。每个适配器按实际验证的输入与输出公布能力。[平台插件契约](https://github.com/NousResearch/hermes-agent/blob/ae2a81ccc00e9b7c06301523e5bb09608397149c/website/docs/developer-guide/adding-platform-adapters.md)

**第一个可交付样例**

在授权的群与私聊各收一条带文件的任务，宿主调用真实工具读取文件并生成可下载的结果；第二轮能引用第一轮内容。核对两路的结果和原件摘要、群内普通未触发消息的可见性、两个会话互不串线。使用既有 consumer 时，下游需持久记录已接收的消息 ID 和宿主处理状态，consumer 的 ready 只表示附件就绪；重启重读不能重复执行或发两次，投递未知时按原键对账。取消单列验收，核对宿主确实停止及后续无迟到交付。[消费与幂等接口](22-generic-tool-and-consumer.md)

这些是适配器的交付验收项。现有核心 IM 与已验执行器可继续使用，原 R09「至少一个执行器」已满足。本次评估没有安装候选、切换账号或调用模型，三个宿主的新接法仍处于选型阶段。[已交付能力](102-user-requirements-and-roadmap.md)
