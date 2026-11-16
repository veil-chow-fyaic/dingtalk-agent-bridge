# 身份、会话覆盖与 bot 限制：证据裁决

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


核对日期 2026-11-11。DWS 以 v1.0.67 为契约基线。这里回答用户最初的疑问：是否能用官方原生能力代替普通账号 AX bridge。结论是 **DWS 用户身份值得作为主路线；标准应用 bot 的群 @ 接收不能满足普通非 @ 群消息要求；跨组织/外部会话尚不能承诺全部打通，也没有依据断言所有钉钉 bot 都不能加入外部群。**

## 证据口径

“契约”是官方声明；旧“本机”记录来自单人内部群；最新指定两账号群/私聊UI见docs/27；“上游报告”不是本机通过或永久政策；“未知”附验证路径。INTERNAL_GROUP、NORMAL、EXTERNAL 等以查询/报告实际字段为准，不能把群名、普通群、外部群、含外部成员群混为一类。用户是管理员也不扩大群授权范围。

## 身份 × 会话矩阵

| 身份 / 会话 | 加入或访问 | 普通非 @ 接收 | 历史 | 主动发送与媒体 | 权限/结论 |
|---|---|---|---|---|---|
| DWS 用户 / 当前内部群 | 本机已绑定liev所在原群 | receive_group契约存在；veil非自身消息经历史入站通过 | 本机分页通过 | 本机文本、附件、内联图片通过；原生音视频未通过 | 管理员 CLI 开通 + 用户 OAuth + 同 profile + 本人会话权限 |
| DWS 用户 / 同组织私聊 | receive_o2o 契约存在 | 契约不要求@；veil私聊普通文本入站通过 | liev视角历史读取通过 | liev回复、TXT/CSV及客户端下载打开通过 | 必须先解析真实对方和会话 ID；不能以群通过替代 |
| DWS 用户 / 跨组织、外部联系人私聊 | 官方说明 openDingTalkId 适用于这些身份 | 有 openDingTalkId 参数；实际覆盖未知 | 现场跳过 | 现场跳过；参数存在不等于对方可达 | 不得将外部 openDingTalkId 塞入 --user；与对方私聊用 receive_o2o |
| DWS 用户 / 外部群或跨组织群 | #937 报告可查询外部群历史 | #937 报告注册失败/不投递；v1.0.67 本机未验证 | 上游有成功对照 | 本机未知 | 群主/成员与群类型要分别记录；不能以 Stream ready 判通过 |
| DWS 用户 / 含外部成员的群 | 先查群实际类别及成员属性 | 不单凭“有外部人”推断成功/失败 | 未单独验证 | 未单独验证 | 现场跳过；不得自动归类成内部群或某个 EXTERNAL 类型 |
| 企业内部应用 bot / 同组织内部群 | 官方教程明确这条添加路径 | **标准群入口仅接收 @ bot** | 所引接收文档不提供普通账号全历史承诺 | 有机器人主动发送/媒体 API；不等于用户发送 | app 所属组织、应用可见性、能力与权限均相关；不满足本项目全量非 @ 接收 |
| 应用 bot / 人与 bot 单聊 | 官方接收路径存在 | 用户直接发给 bot 可触发 | 不等于读取人与人私聊 | 机器人单聊发送和下载码资源路径存在 | bot 是独立身份，不能替代用户与客户现有会话 |
| 应用/智能 bot / 跨组织或含外部成员群 | 同组织教程不证明所有类型外部禁止；#937 作者称目标外部群已有 intelligent bot 工作 | 具体 bot 类型/群属性未完整核定；不能承诺无 @ | 未证实全历史 | 未证实所有类型完整媒体 | **未知，不沿用企微禁止结论。**第三方企业应用、旧机器人、智能机器人分别验证 |
| 自定义 Webhook / 已允许添加的群 | 群允许配置后可推送；外部群加入边界未独立证实 | **不支持消息接收** | 无普通会话历史能力 | 群推送；不是 user 身份，也没有用户 IM 全能力 | 无私聊；官方提示退场，具体日期/新建可用性未核定；不选作本项目主通道 |
| 任意上述身份 / 企业外微信客户 | 现有资料不足以证明直接访问 | 未知 | 未知 | 未知 | 官方能力目录另有“钉钉客联/互通群/跨端消息”，只能作为独立产品调查线索，不能推定与微信客户互通或 DWS 已封装 |

## 三个容易混淆的事实

1. `receive_user` 是“指定发送人在单聊及群聊发来的消息”；`receive_o2o` 才是“与指定人的单聊”。sender 快捷模式不能当作只监听私聊。群用 openConversationId，用户用 userId 或明确的 openDingTalkId，不互相猜换。
2. bot 群接收与用户个人事件是两套入口。bot 有媒体示例，不代表群里所有无 @ 文件/语音/视频均推送给它；单聊样本尤其不能外推群能力。原图下载成功也不等于原生气泡呈现通过。
3. #937 原报告外部群有失败与内部/NORMAL 成功对照，后续 v1.0.64/65 评论没有核实群类型；截至本次查询仍 open，不宣称最新版本必坏或已修复。#1429 是加密资源特定问题，不是所有图片失效。

## 官方机器人本地接入补充

固定版DWS已有dev connect（机器人Stream→本地CLI），并非只有业务API；还有官方OpenClaw Connector。这两条入口应在bot场景优先评估，但不等价于当前普通账号既有会话。已核对本机Help及固定版教程，未新建机器人或改变实测范围。来源和完整自研边界见[docs/25](25-official-boundary-and-scenarios.md)。

## 验证路径与当前路线

外部会话恢复测试时，逐例记录实际群类别、成员组织、身份类型、组织 profile、订阅类型、ready、另一人无 @ 消息、历史、发送回执、原件摘要和对端呈现。当前用户已授权并通过veil与liev原群/私聊UI；其他成员与外部会话仍未验证。

目前保留 DWS 用户身份 + 本项目限定历史补读实验服务。Stream 作为待验收入站主候选；应用 bot 可作为明确 bot 对话场景的补充，不承担本项目全会话桥。尚无证据要求立即写完整 AX backend。对具体群先验证事件和历史，再决定历史补偿或局部 AX；发送结果未知时绝不自动跨后端重发。

## 一手来源

- [官方同组织内部群 bot 测试教程](https://opensource.dingtalk.com/developerpedia/docs/explore/tutorials/stream/bot/go/test-bot/)：支持该教程的加入条件和群 @ 接收，非全类型外部禁止政策。
- [应用机器人接收](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/appbot/receive/)、[机器人分类](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/overview/)、[Webhook 说明](https://open-dingtalk.github.io/developerpedia/docs/learn/bot/webhook/overview/)；[退场公告](https://open.dingtalk.com/document/orgapp/webhook-bot-offline-notice)本次仅取得页面外壳，未确认具体日期。
- [固定版 DWS README](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/README_zh.md)、[事件表](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-keys.md)、[媒体契约](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-chat/references/chat/message-media.md)。
- [#937](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/937)、[#1429](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1429)；状态/摘要见 [来源快照](../evidence/2026-11-11/boundary-sources.json)。
- [官方能力目录](https://open.dingtalk.com/document/ability/map?categoryName=音视频)：钉钉客联、服务群、音视频会议是不同产品能力线，尚未实测。
