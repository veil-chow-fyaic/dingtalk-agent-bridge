# 协议与实现备忘

这些说明用于选型与后续编码，必须按固定 CLI/API 版本再核对。不能据机器人字段推断用户事件载荷。

## 机器人通道

Stream 模式支持机器人回调、事件及卡片，适合没有公网回调入口的本机部署；HTTP 回调需要独立处理来源验签。机器人消息 topic 为 `/v1.0/im/bot/messages/get`，不是 DWS 个人事件的 EventKey。

接收类型覆盖 text、richText、picture、audio、video、file。非文本消息常通过 downloadCode 换取临时下载地址；回调有时只提供语音识别文字，原音频是否拿到应另记。群聊语音、视频、文件入站限制见官方消息类型文档。

机器人发媒体优先使用 API。模板包括 sampleText、sampleMarkdown、sampleImageMsg、sampleAudio、sampleFile、sampleVideo；文件先上传取得 mediaId。视频有视频资源、封面、尺寸、时长等字段，语音/视频时长单位不能混用。官方文档列举语音 ogg/amr、视频 mp4、文件 xlsx/pdf/zip/rar/doc/docx，不能外推为任意格式皆支持；大小、频率、格式转码以实际接口和客户端验收为准。

sessionWebhook 有过期时间；长任务最终交付应使用已验证的主动发送路径。机器人发送群聊需要正确 openConversationId 与 robotCode；AppKey、agentId、robotCode、unifiedAppId 各自语义不能因示例相似而互换。

来源：[消息类型](https://open.dingtalk.com/document/development/robot-message-type)、[接收机制](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/appbot/receive/)。

## DWS 个人事件

核心事件包括 user_im_message_receive_o2o、receive_group、receive_user、receive_o2o_all、receive_group_all，以及 @、已读、撤回、reaction、群生命周期。不同事件需要不同目标参数。

高层入口 `event +listen-im` 编译用户意图为底层事件；`event consume` 用于精确 EventKey 与订阅控制。stdout 是 NDJSON，stderr 有 ready marker；订阅创建、IPC 建立和真实业务事件到达是不同阶段。stdin 生命周期、SIGTERM 和订阅所有权影响清理，不使用 kill -9 当常规退出。

同一 profile 内解析和消费；群目标用 openConversationId，用户目标区分 userId 与 openDingTalkId。事件中的 message_id/conversation_id 用于精确查询，sender 显示名不能重新当稳定路由键。self-loop 过滤意味着自己发的消息可能不在个人事件中；需要历史补读或独立出站账本。

来源：[事件契约](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/event-subprocess-contract.md)、[事件输出](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/skills/multi/dingtalk-event/references/event-im-output.md)。

## 下载与确认

消息内容、资源发现、签名 URL、文件 GET、文件解析分别记录结果。下载 URL 短期有效且可能携带凭据，不进入日志或长期文档。DWS 查询要检查完整性与逐项下载台账，不只检查进程退出码。

发送若返回 openTaskId，继续查原任务；不要重复提交。原生 message ID、机器人 processQueryKey、AX 本地临时 ID 保留各自类型。消息删除/撤回接口的 ID 不一定与发送/读取 ID 通用。

## 初轮命令选择

本项目优先用户身份，不需要先启动 `dev connect` 或创建机器人。若后续需要独立机器人，`dev connect --unified-app-id ...` 可桥接本地 Agent；自研一次性 CLI 可研究 `--agent-cmd`，但文本标准输出不等于完整媒体协议。官方/社区插件提供卡片、媒体和多 Agent 的参考，不要求引入第二套完整 runtime。
