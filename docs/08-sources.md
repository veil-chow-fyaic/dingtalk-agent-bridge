# 资料来源索引

整理更新：2026-11-11。仅 #937/#1429 本轮重新查状态，其他 issue 沿用11-10快照。动态链接会更新；版本相关结论优先引用正式 tag。issue 的 open/closed 仅表示工作流状态，不证明故障已复现或修复。公开 issue 元数据另存 evidence/2026-11-10/upstream-metadata.json。

## 官方文档与项目

| 编号 | 来源 | 支持的结论 |
|---|---|---|
| S01 | [机器人消息类型](https://open.dingtalk.com/document/development/robot-message-type) | 机器人收发类型、群 @ 媒体限制 |
| S02 | [机器人分类](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/overview/) | 应用机器人与群自定义 Webhook 区别 |
| S03 | [机器人接收](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/appbot/receive/) | 单聊/群 @、Stream、下载码 |
| S04 | [群发送 API](https://open.dingtalk.com/document/development/the-robot-sends-a-group-message) | 主动群发 |
| S05 | [单聊发送 API](https://open.dingtalk.com/document/development/chatbots-send-one-on-one-chat-messages-in-batches) | 机器人主动单聊 |
| S06 | [接收媒体下载](https://open.dingtalk.com/document/development/download-the-file-content-of-the-robot-receiving-message) | 下载码换资源 |
| S07 | [媒体上传](https://open.dingtalk.com/document/development/upload-media-files) | 上传与 mediaId |
| S08 | [DWS 仓库](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli) | CLI 定位、模块和登录 |
| S09 | [v1.0.67](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.67) | 公开正式版本 |
| S10 | [DWS 命令 Wiki](https://open.dingtalk.com/dingtalk-dev/wiki) | 历史快照，不能代替当前 Help |
| S11 | [DWS 架构](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/architecture.md) | CLI/MCP 结构 |
| S12 | [机器人快速入门](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/robot-quickstart.md) | dev connect、自研 agent-cmd |
| S13 | [常驻服务](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/connect-daemon-service.md) | daemon 与 OS 服务区别 |
| S14 | [正式版 IM 事件清单](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-keys.md) | 用户事件存在，不代表组织已开通 |
| S15 | [事件输出交接](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/skills/multi/dingtalk-event/references/event-im-output.md) | 媒体事件需进一步查消息资源 |
| S16 | [正式版媒体命令](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-chat/references/chat/message-media.md) | 用户身份发送/下载 |
| S17 | [正式版会议源码](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/conference.go) | conference 不可用 |
| S18 | [额度活动公告](https://open.dingtalk.com/document/development/open-ai-paas-report) | 历史活动到期，非当前不限量承诺 |

## 直接相关的故障与答复

- [#937 外部群事件](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/937)：open；原报告与10-21复测应分开解读，后者群类型未确认。
- [#909 自建应用映射](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/909)：open；默认 OAuth 与自建 App 对照。
- [#1429 加密媒体](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1429)：open；[贡献者说明](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1429#issuecomment-5862334317)确认当时图片/文件资源解密未集成。
- [#1215 SupMate 图片403](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1215)：open；限定企业定制版与样本，非全部钉钉。
- [#1304 第三方产品接入](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1304#issuecomment-5761503069)：closed；协作者回复组织授权人员登录可接入，非所有用例验收。
- [#866 身份说明](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/866)：closed；用户 OAuth 与机器人发送身份分离。
- [#890 多群参数](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/890)：open；旧版本报告，当前版本需单独确认。
- [#42 历史读取演进](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/42)：旧版本缺失已被后续能力替代，不引用旧需求否定当前功能。

## 参考实现

- [官方 OpenClaw Connector](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector)
- [官方引用与多媒体边界](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector/blob/main/docs/COMMUNITY_CAPABILITY_ALIGNMENT.md)
- [社区 soimy 插件](https://github.com/soimy/openclaw-channel-dingtalk)
- [社区消息类型](https://github.com/soimy/openclaw-channel-dingtalk/blob/main/docs/user/features/message-types.md)
- [Python Stream SDK](https://github.com/open-dingtalk/dingtalk-stream-sdk-python)
- [多语言 SDK 导航](https://open-dingtalk.github.io/developerpedia/docs/develop/sdk/overview/)

## 本地材料

wecom-bridge 路径、提交和文件定位见 [实现对照](03-wecom-reference.md)。本机 CLI Help、版本、认证摘要和 AX 合成测试记录见 [本机实验](07-local-results.md)。未下载或复制整份第三方仓库；保留来源链接和必要事实摘要。

## 用户亲历与新组织实测

2026-11-10 用户确认新建弗忧智能科技组织、本人为管理员，并已在开发者平台手动开通 CLI 相关权限。后续本机认证和 profile 查询确认新组织 / 周威已登录。见 [开通经验库](11-onboarding-lessons.md)及[脱敏证据](../evidence/2026-11-10/new-org-onboarding.json)。该来源不能代替后台按钮名称、完整权限集合或新群事件验收。

## 本轮补充的一手来源和固定版本

- S19 [v1.0.67 README](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/README_zh.md)：管理员 CLI 访问入口、readonly、profile及外部联系人参数。
- S20 [同组织内部群添加应用bot教程](https://opensource.dingtalk.com/developerpedia/docs/explore/tutorials/stream/bot/go/test-bot/)：教程范围和群@，不能作全部外部bot禁令。
- S21 [Webhook 生命周期](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/webhook/overview/)及[公告](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice)：仅确认存在退场提示；公告正文未取到，具体日期未核实。
- S22 [平台能力目录](https://open.dingtalk.com/document/ability/map?categoryName=音视频)：音视频会议、客联和服务群等独立能力线，目录不等于DWS实测。
- [前阶段来源元数据与SHA256](../evidence/2026-11-11/boundary-sources.json)、[身份边界裁决](18-identity-and-conversation-boundaries.md)、[新增本机证据](20-gap-acceptance-and-reproduction.md)。前阶段GitHub连接器不可用，采用官方公开HTTP资料；主站部分JS正文不可读取，已标未知，不用搜索空结果证明不支持。
- S23 [v1.0.67用户文件发送源码](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/unified_send.go#L778)：2026-11-11续作经GitHub连接器读取，audio/video映射file，本机dry-run交叉验证。
- S24 [固定版EventKey](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-keys.md)、[事件输出和媒体补读](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-output.md)：限定group/o2o订阅和提示链路设计依据。
- [续作版本与源码定位](../evidence/2026-11-11/upstream-continuation.json)：当日官方latest release为v1.0.67；不据main分支代码宣称本机已升级。

## 本地 Agent 与成熟 IM 插件

- S25 [Codex非交互执行](https://developers.openai.com/codex/noninteractive)：JSONL、结果schema和精确session恢复；本机exec/resume Help交叉核对。
- S26 [Kimi命令参考](https://moonshotai.github.io/kimi-code/en/reference/kimi-command.html)：prompt/stream-json、session、旗标冲突和auto权限。
- S27 [OpenClaw Slack](https://docs.openclaw.ai/channels/slack)：授权、线程/会话、回执/进度、附件和审批的产品分层参照。
- S28 [OpenClaw Telegram会话](https://docs.openclaw.ai/channels/telegram/threads-and-sessions)：topic会话与持久绑定；不是钉钉事件覆盖依据。
- 本地wecom-agent-gateway的Codex app-server与Kimi ACP适配、固定提交及本项目采用方式见[docs/21](21-existing-runtime-integration.md)、[docs/24](24-local-agent-product-and-acceptance.md)。
