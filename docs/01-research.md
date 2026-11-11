# 研究综述

截至2026-11-11的逐格结论见 [身份与会话边界](18-identity-and-conversation-boundaries.md)，本轮实测和复现见 [docs/20](20-gap-acceptance-and-reproduction.md)。

## 目标与范围

目标是普通员工账号参与已有私聊和群聊：无需所有人改为与独立机器人私聊，普通群消息不要求总是 @ 机器人；文本与媒体要取得真实内容并能回发。组织办公功能由 Agent 调用官方工具。

不把中国 IM 生态的整体印象当成技术结论。钉钉已开放部分用户 IM 能力，但连续双向通信仍有具体缺口。

## 三种入口

1. 群自定义 Webhook：适合推送通知，不是普通账号的双向会话监听。
2. 应用机器人：HTTP/Stream 接收机器人单聊与群 @ 消息，官方 API 主动发送及卡片；与普通员工身份不同。
3. DWS 用户 OAuth：当前用户可见消息、个人 IM 事件、历史查询、资源下载与组织工具。它是本项目首选基础。

官方消息文档明确群成员不能通过 @ 机器人直接发送语音、视频、文件给机器人；机器人向群发送这些类型是另一回事。[机器人消息类型](https://open.dingtalk.com/document/development/robot-message-type)

## DWS 的性质

[DWS 官方仓库](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli)提供 Go CLI、机器可读 Schema、产品命令、Agent skills 和机器人到本地 Agent 的连接器。业务执行涉及 MCP 通道，并不只是传统 REST OpenAPI 的薄封装。[架构](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/architecture.md)

普通业务命令按登录用户权限执行；选择机器人发消息不等于机器人取代用户 OAuth。人与机器人所在群不一致时，搜索与读取能力不能互换。[认证解释 #866](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/866)

2026-11-11 已再次核对官方 release：v1.0.67（11 月 4 日发布）；项目内隔离安装并实测 v1.0.67，全局 v1.0.61 保留。新版内联图片路径已通过资源/API 验证，不能沿用旧版缺口。各结果只归属于其实际测试版本。正式版、main 源码、网页历史快照不能混作一个版本。

## 已有项目

| 项目 | 用途 | 本项目采用方式 |
|---|---|---|
| DWS | 用户 IM、组织工具、本地 Agent 桥接 | 优先能力提供方 |
| 官方 dingtalk-openclaw-connector | OpenClaw 渠道、媒体、卡片、多 Agent | 参考实现，不要求替换现有 runtime |
| soimy/openclaw-channel-dingtalk | 社区渠道与媒体、引用恢复 | 提取测试案例与边界 |
| open-dingtalk Stream SDK | 原生机器人事件和卡片通道 | 需要独立机器人时采用 |
| fyaic/wecom-bridge | AX 收发与投递可靠性 | 复用设计与上层契约，仅在证实必要时实现钉钉 UI adapter |

官方 connector 的 README 建议个人助手用途，并对企业生产部署作保守提示；项目存在不等于本组织端到端验收通过。社区引用恢复也受缓存、回调内容、时间窗口、分页和企业条件限制。

## 组织工具

DWS 已列出 contact/aisearch、chat、doc、sheet、aitable、drive、mail、todo、calendar、minutes、oa、report、ding 等能力。各命令仍受当前账号权限与组织开通约束。

calendar 管日程、参会人、会议室和忙闲；minutes 管听记。当前 v1.0.67 开源版 conference 入口明确不可用，不能将日程预约算作实时视频会议。[正式版源码](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/conference.go)

## 额度与接入条件

本轮用户亲历确认：新组织需要管理员在开发者平台手动开启 CLI 相关访问权限，用户已完成。官方固定版已明确开发者平台 → CLI 访问管理 → 开启；具体人员范围未独立查看，后续组织应先检查此项。针对第三方桌面产品的咨询，项目协作者回复组织授权人员登录即可接入；这不是所有组织、所有资源都已可用的承诺。[#1304](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1304#issuecomment-5761503069)

官方过去的 OpenClaw 免费不限量活动，公告默认截止 2026-03-31、申请豁免最晚到 2026-04-30，不能据此承诺当前免费不限量。以目标组织资源管理为准。[公告](https://open.dingtalk.com/document/development/open-ai-paas-report)

## 当前建议

建立稳定 bridge 服务，包装官方能力并补足事件连续性、媒体和投递对账。先验证官方用户路径，再决定 AX 覆盖范围。不要先完整移植 GUI，也不要因 CLI 有命令就删除 AX 备用方案。
