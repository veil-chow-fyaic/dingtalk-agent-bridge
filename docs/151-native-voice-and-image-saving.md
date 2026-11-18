# 原生语音和组合图片的现场验收

2026-11-18，在同一个普通账号的授权群聊和私聊中实测。运行产品为 `0e151fb`，官方 DWS 固定为 v1.0.67。群聊、私聊都能接收手机原生语音并取得音频原件，两条既有图文消息中的四张 PNG 都能通过 Mac 钉钉逐张下载。程序发送可播放的原生语音条仍有缺口。[脱敏实测记录](../evidence/2026-11-18/native-voice-and-gallery.json)

## 接收语音

在手机钉钉目标会话中切换到语音，按住说话，松开发送。接收端可从 `dab events` 取得本会话的消息 ID，再用 `dab attachments` 获取原件。持久 consumer 将转写正文和音频分别保存在有序的 `text` 和 `audio` 项中。转写内容由上游提供。[钉钉用户手册](https://alidocs.dingtalk.com/i/p/dBgX4oYWY1aaEz8e/docs/ZX6GRezwJlddqOdBionY1gaMJdqbropQ?dontjump=true)

| 真实来源 | 下载的原件 | 钉钉播放条 | 接收验证 |
|---|---|---|---|
| 群聊手机录音 | 11,674 字节，4.32 秒 | 显示 0:04，点击后出现倍速与运行计时 | 一个音频资源，独立 consumer 就绪，完整解码 |
| 私聊手机录音 | 9,932 字节，3.68 秒 | 显示 0:03，点击后出现倍速与运行计时 | 一个音频资源，独立 consumer 就绪，完整解码 |

两份原件均为单声道 Ogg/Opus。已逐条核对原消息、会话、发送者、下载资源、文件长度和 SHA-256。群里的普通语音遵循原有策略，只接收，按消息 ID 获取即可。私聊网关按其已配置的交办策略处理。时长取自原件解码工具，客户端单独记录显示秒数。两个样本覆盖短录音，长录音、转写准确率和声学质量没有单独评测。

## 发送语音

普通账号要由程序传声音，可发送 WAV 附件。群聊、私聊都已经验证接收、下载和播放。要由人发出带时长的聊天语音条，可直接在手机钉钉按住说话。[双路音频文件证据](102-user-requirements-and-roadmap.md)

```sh
dab --account-id "$ACCOUNT" --conversation-id "$CHAT" attachments --message-id "$MESSAGE"
dab --account-id "$ACCOUNT" --conversation-id "$CHAT" send --key "$KEY" --file local/outbox/voice.wav
```

对于程序主动创建新的原生语音条，固定 DWS 的普通用户发送接口把 `audio` 映射到文件。另一个候选是官方单条转发。本次在两路各取刚收到的真实语音，用相应源消息 ID 向原会话执行一次。首次 CLI 要求本地写入确认，按原 UUID 补上确认后，两次官方业务回执均成功。核对回执中的目标会话和新消息 ID，两条新消息都来自发送账号，历史正文只剩字面文字 `[语音]`，资源为零。收件客户端也都只显示字面文字 `[语音]`，没有时长或播放控件。该转发路径无法交付这两条录音的声音。[普通用户身份契约](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chat/identity_contract.go#L24) · [单条转发实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chat/chat_message.go#L2223)

开放平台另有接收 `voice` 参数的开发者接口，需要 ISV 或企业凭证，并受企业接收方范围限制。它无法满足这个工具既定的普通账号身份和组织无关要求。如果官方新增可由普通账号从本地音频创建语音的契约，可分别用群、私聊核验新消息的真实播放器和音频资源。[开放平台接口及调用条件](https://developer.alibaba.com/docs/api.htm?apiId=37159)

## 逐张保存一条消息里的图片

1. 打开原会话，点右上方文件夹图标，进入「图片及视频」。
2. 按消息时间和缩略图找到目标，打开某一张。可在查看器核对分享人和时间。
3. 点查看器右上方「下载」，选择本地目录并保存。返回列表，对下一张重复。
4. 若需要原件校验，可与发送方 SHA-256 比对。程序消费者也可按同一消息 ID 用上面的 `attachments` 命令获取原件。

实测使用 11 月 16 日原有的两条图文消息，群聊和私聊各含两张不同 PNG。四张都在钉钉查看器逐张打开并下载，保存后从磁盘逐张用 Finder 快速查看。四个文件都独立于原输入和 DWS 缓存，按发送顺序与原输入、索引到的官方原件逐字节相同，SHA-256 见脱敏记录。先前在气泡内双击或右键失败的观察仍有效。任意普通文件合为单条消息和群模型任务另列在矩阵中。[原图文投递](135-composition-api-deployment.md) · [先前客户端观察](147-native-ui-recovery-and-dm-quote.md) · [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)
