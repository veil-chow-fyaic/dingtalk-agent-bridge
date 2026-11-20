# 首次使用

已有 OpenClaw 的用户可先完成下述传输配置，再按[原生插件指南](../integrations/openclaw-channel/README.md)接入。已有微信或其他渠道的宿主先核对[组织工作区试点步骤](resident-openclaw-pilot.md)。

这条路径先运行独立 IM 通道：安装 → 配置一个已授权会话 → 启动传输 → 确认收发 → 持久消费。无需先选择模型或启动 gateway。完整参数见[接口参考](22-generic-tool-and-consumer.md)，维护、恢复与回滚见[运行手册](15-service-runbook.md)。

以下命令从一个尚未运行服务的独立源码检出执行。已有部署修改配置或版本时，应按运行手册维护，不直接覆盖当前配置。

## 1. 准备环境

- Python 3.11+、POSIX；macOS arm64 已实机验证。Windows 不因 wheel 标记为 `py3-none-any` 而受支持。
- 官方 DWS CLI；当前桥接契约验证于 v1.0.67，二进制不随 Python 包分发。
- 由操作者在自己的设备完成官方支持的授权，并核实组织开通、账号 profile、会话和资源权限。已有合适组织即可使用，不要求新建组织或 bot。参见[开通经验](11-onboarding-lessons.md)及[固定版本官方说明](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/README_zh.md)。

桌面已登录不代表 DWS 的目标身份已授权。不要导入他人的凭据或整份 `local/`，也不要用模糊会话名称代替已核实的稳定 ID。

## 2. 安装和查看帮助

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab --help
.venv/bin/dab-consume --help
.venv/bin/dab-service --help
```

源码安装的构建阶段可能获取 setuptools；运行时无第三方 Python 依赖。已有交付包可选择[离线 wheel 安装](144-offline-release-export.md)。六个入口为 `dab`、`dab-bridge`、`dab-consume`、`dab-agent`、`dab-service` 和 `dab-doctor`；查看 `--help` 不读取账号或调用 DWS。

## 3. 配置自己的会话

在这个工作目录创建私有配置：

```bash
umask 077
mkdir -p local
cp -n config.routes.example.json local/service-config.json
```

用编辑器打开 `local/service-config.json`。模板包含群聊和私聊两条占位路由；第一次可只保留一条，并替换其中所有占位值。保留多条时，每条都必须有效。

| 字段 | 如何填写 |
|---|---|
| `accountId` | 自定稳定本地别名，例如 `personal`；同别名始终对应一个 `profile` |
| `profile` | 已核实的 DWS 认证上下文，服务调用时显式传入 |
| `conversationId` | 目标会话真实 `openConversationId`，不能填显示名称 |
| `conversationType` | 群聊填 `group`，私聊填 `direct` |
| `peerOpenDingTalkId` | 私聊必填：已解析核实的对方 ID；不能从名字猜测 |
| `selfSenderId` | 该 DWS 身份实际消息中的发送者 ID，用于识别自身消息 |
| `binary` | 官方 DWS 可执行文件路径；绝对路径或相对本工作目录均可，模板路径需实际存在 |
| `name` | 仅供显示，不承担授权或路由判断 |
| `historyTimezone` | 无时区历史时间的解释时区；模板为 `Asia/Shanghai` |

默认通过 history 轮询，先不要增加 `stream_hint`。如需原生 PNG/JPEG 发送，另按[图片上传补充](../integrations/dws_image_upload/README.md)准备 `imageUploadBinary`；文本和普通文件不需要它。源码中的 `configure select` 已修复为同账号新增路由继承已有 helper；原账号没有配置该字段时仍需自行填写。生成后核对候选配置，不把另一个账号的 profile 或权限借给新路由。

配置助手的 `migrate` 是离线迁移；`select` 会调用 DWS 只读核对目标，两者都只生成新候选文件、不激活监听。使用已有单路账本时，先读[迁移说明](23-continuation-and-migration.md)，不要手动清除 `stateStorage=legacy`。

## 4. 启动独立传输

保持这个终端运行：

```bash
.venv/bin/dab-bridge --config local/service-config.json
```

**此时开始真实 DWS 业务调用**：先核对目标，再轮询已配置会话。首次正常启动生成 `local/runtime/http-token`，HTTP 仅监听 `127.0.0.1:18768`。配置、账本、缓存和本机令牌都以当前工作目录为根。

在另一个终端进入同一目录，读取本地状态：

```bash
.venv/bin/dab health
.venv/bin/dab conversations
```

检查返回的路由、`poll_error`、完整同步状态和 `dws_access`。HTTP 可达只证明本机接口工作，不代表消息已送达或模型可用。若准入已持久暂停，先按[故障分类与恢复](114-dws-risks-and-resolution.md)处理，不循环登录或自动解除暂停。

正常结束前台传输用 `Ctrl-C`。需要后台管理时改用[原管理器流程](15-service-runbook.md#当前本机部署与管理)，不要同时运行前台与管理器实例。随包 CLI、gateway、consumer 固定连接默认端口，没有统一远程地址/端口选项。

## 5. 验证一次收发

先由已授权的另一端发送一条测试文字，使用事件接口读取。下面的 `ACCOUNT`、`CONVERSATION`、`BUSINESS-KEY` 是参数占位符，执行前替换为自己的路由与新业务键；全局选择参数必须写在子命令前。

```text
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION events --after 0 --after-revision 0 --limit 100
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION send --key BUSINESS-KEY --text "首次通道验证"
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION status --key BUSINESS-KEY
```

`send` 会真实发送。每个新的发送意图用独立 key，核对这一个 key 的回执及另一端实际 UI。同 key 重试只能查询/复用同一投递，不能拿同 key 换内容；结果未知时不要换 key 重发。CLI 退出 0 或 HTTP 202 不代表 `confirmed`，`confirmed` 也不证明对方已读。

完成后可扩展文件、引用和图文组合，完整用法见[接口参考](22-generic-tool-and-consumer.md)。文件必须在服务工作目录允许的 `fixtures/` 或 `local/outbox/` 内；上限、原件摘要与实际客户端保存应分别核对。

WAV 音频文件和 MP4 视频文件已有群聊、私聊双向原件与播放证据。原生语音可在两路接收、播放并交给独立 consumer。bridge 主动发音频请使用 WAV 附件。固定 DWS 的原生语音转发在两路都只留下占位文字。要保存组合图片，可从会话「文件」进入「图片及视频」，选中缩略图，在查看器中下载并保存。两条既有双 PNG 消息的四张原图已逐张核对。[媒体实测与操作路径](151-native-voice-and-image-saving.md)

## 6. 用独立 consumer 持续接收

consumer 保存事件游标与规范化 inbox，可按需下载原件，不调用模型、不自动回复。每个账号/会话使用独立名字，同名消费者不能并发写入。

```text
.venv/bin/dab-consume --config local/service-config.json --name my-reader --account-id ACCOUNT --conversation-id CONVERSATION
.venv/bin/dab-consume --config local/service-config.json --name my-reader --account-id ACCOUNT --conversation-id CONVERSATION --follow --wait-seconds 25 --max-batches 10
```

第一条只处理一批；第二条跟随最多 10 批。复用同一名字和路由会继续已保存游标。`--max-batches 0` 持续到中断；`Ctrl-C` 正常结束。状态位于 `local/consumers/my-reader/`。附件物化可能调用真实 DWS 下载，因此这不是纯离线操作。

`normalized` 表示这一条成功规范化，不表示任何 Agent 已处理；`pending_media`、`media_failed`、`quarantined` 保留不同问题，不能通过删除账本或改名重建消费者掩盖。

语音入站代码只把 DWS 的明确语音标记与对应资源归一化为 `audio`，原件完整下载并校验后才可消费；不会自动录音、转写或调用模型。DWS 提供的转写正文原样保留，不替代音频原件。已有 inbox 行不会因升级自动重新解析。

## 下一步

- 接自己的程序：[HTTP/OpenAPI](../api/openapi.json)与[consumer边界](22-generic-tool-and-consumer.md#持久消费边界)。
- 让模型执行任务：先看[实际运行器支持](architecture/agent-integration-map.md)，再准备[独立执行器配置](../config.agent.example.json)。明确 `allowedSenderIds` 后按运行手册启用 gateway；不要把任务执行混入基础通道验证。
- 维护与升级：[运行手册](15-service-runbook.md)、[已知风险](114-dws-risks-and-resolution.md)、[当前验收范围](102-user-requirements-and-roadmap.md)。

自建 HTTP 消费者可在 `/v1/events` 同时传入 `after` 与 `after_revision`。事务内保存普通事件、`revisions` 和返回的两个游标 `next_cursor`、`next_revision_cursor`。修订项含 `revision` 和保留原 `seq` 的 `event`。旧 transport 只返回消息游标时仍可正常读取。内置持久 consumer 已实现双游标。
