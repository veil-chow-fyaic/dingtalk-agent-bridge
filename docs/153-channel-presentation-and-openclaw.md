# E153 · 聊天正文与 OpenClaw 原生通道

以下保留E153阶段的实现/合成测试和当时现场状态；后续私聊真实文件及群未知投递见[E154](154-openclaw-real-files-and-client-receipts.md)，合并/部署收据见[PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)。

开发分支 `codex/native-agent-channel` 从已验证的公共主分支 `e4b650f` 建立。现场运行的版本仍是 E150 的 `0e151fb`。本阶段的次序是查清用户看见的消息由谁生成，调整内置 gateway 的默认呈现，再把同一套普通账号收发接到现有 OpenClaw Gateway。

## 一条消息由谁决定

| 用户看到的内容 | 来源 | E153 分支的行为 |
|---|---|---|
| 回复正文和结果文件 | 宿主或调用方提供，bridge 负责路由、文件完整性及对账 | CLI、HTTP 和原生插件不加署名或任务号。内置 gateway 的默认产品模式直接交付正文及原文件名。宿主自己写的 `[Agent]` 照常发送 |
| 以往的 `[Agent] 已接收任务 <短编号>` | 内置 Python gateway 生成，任务号取自本地账本 | `chatPresentation: "product"` 跳过常规接单通知。仅发送附件的任务直接交付原件。显式状态、新会话、取消和需用户处理的失败会给出可读反馈 |
| 本地任务编号、执行诊断、投递回执 | bridge 的任务和 outbox 账本 | 产品模式仍保存。内置 gateway 的 `"diagnostic"` 模式可恢复旧的聊天调试呈现。升级前已入账的投递保持原始载荷和幂等键 |
| 客户端的发送人和“通过 AI 发送” | 普通账号身份、DWS 的 AI 标签元数据和钉钉客户端 | 使用默认官方标签，与聊天正文独立。[DWS 标签定义](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/runner.go#L41-L46) |

只读统计四份本地历史 gateway 账本中的已确认文字，214 条都以 `[Agent]` 开头，其中 98 条是接单通知。这是对旧版本实际投递的统计。普通账号群和私聊使用同一呈现规则。[gateway 实现](../dingtalk_bridge/agent_gateway.py) · [配置示例](../config.agent.example.json)

**示例。** 宿主返回“表格已整理好。”和 `本周汇总.xlsx` 时，用户收到这句正文和这个文件。宿主只返回文件时，用户只收到文件。常规结果超过官方单条限制时，gateway 和插件按 5120 个 UTF-16 单元分段，保留 Unicode 字符。固定 DWS 的群、私聊发送与引用命令都会裁去每条文字首尾空白。需要保留每个字节时发送文件原件。

原先 bridge 还会拦截文字中的 `![`，内置 gateway 会改写该标记。核对实际快捷命令后已移除这项限制。固定版 `+messages-send --text` 以 text 类型返回，`+messages-reply` 同样走文字类型。四个入口用固定 DWS 源码和模拟 RPC 分别验证，字面 Markdown 内的路径不会变成图片上传。[发送实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chat/unified_send.go#L391-L409) · [引用实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chat/lark_alignment.go#L264-L277) · [复现方法](../integrations/dws-contract/README.md)

## OpenClaw 怎样接已有会话

`OpenClaw Gateway → 原生 ChannelPlugin → 本机 bridge → 普通账号 DWS`。OpenClaw 选择 Agent、会话、工具和公开回复。bridge 负责获取事件与原件、按原账号和会话投递、持久保存消费位置、投递键与回执。安装和配置见[插件指南](../integrations/openclaw-channel/README.md)。

- 私聊可直接交办任务。群里普通消息可接收，只有来自许可发送者的 `/agent` 指令触发执行。群里处理自己的既有文件，可在钉钉里引用该条文件并附上指令。缺少可信引用发送者时跳过文件任务。
- 同一条路由交给一个执行方。新侧车复用既有 gateway 的进程锁，使用独立的 consumer 账本。接手现有路由时先核积压、执行归属和已验证的起始游标。填写 0 会从可见历史开始，后续重启沿用已持久化的游标。
- 正在运行的任务被打断时保留未确认状态。尚未开始的消息留在 SQLite，可在重启后按序领取。执行期间可以处理同一发送者的取消指令。未知投递按原键对账，取消无法撤回已经产生的外部副作用。
- 已交付的内置 `openclaw agent --local` 执行器是另一种用法。两条真实路由仍由原执行器持有，普通账号群与私聊的原有产品实测见[通用 IM 能力表](102-user-requirements-and-roadmap.md)。

## 验证范围

- 用 OpenClaw 2026.11.3（`41f2b981`）实际安装、启用并加载插件。首轮宿主集成发现带附件的可见回复经 `block` 交付，遗漏该回调时两条任务只生成本地文件。修复后支持宿主的完成内容及媒体回调，工具、推理和诊断事件不转成聊天正文。
- 用真实 OpenClaw Gateway、bridge HTTP、独立 Python 侧车和 SQLite，配合本机合成模型服务及 DWS 替身跑了群聊、私聊各两轮。各自读取所引原件、用真实 read/write 工具生成并回传独立文件、在第二轮延续自己的上下文，共六次模拟发送。待四个任务完成入账后重启，无重复执行或重复投递，取消运行中的额外任务后无迟到发送。[可复现的宿主测试](../scripts/probe_openclaw_native_channel.py)
- 从真实 `openclaw message send` 入口连续发两条相同正文，两次各自得到一个确认 ID。再向指定群发送说明及附件，核对原文件名和字节。三次命令共四个不同的物理投递键。宿主回执与原键在两个 bridge 路由的确认账本一致。无稳定意图 ID 的主动请求可以改走带显式业务键的 bridge CLI。[主动收发用法](../integrations/openclaw-channel/README.md)
- 整合候选的本机回归通过 563 项 Python 测试及 12 项 Node 测试。解析器、Gateway、侧车和真正钉钉端的验证范围逐项记录。[结构化结果](../evidence/2026-11-18/host-presentation-and-channel.json)
- 新接法仍缺真实模型结合钉钉客户端的现场验收。Hermes 和 DeepSeek Harness 继续按已选 ACP 路线推进。原 R06 语音出站按用户意见暂缓。[后续选择](152-community-agent-adapters.md)
