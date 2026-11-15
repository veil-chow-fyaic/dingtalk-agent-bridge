# 群引用双向真实 UI 与事件链路

2026-11-15，E130。现有 `reply_to` 经受管 HTTP 在 AIC 群发送一次引用，veil 原生客户端显示源消息、发送者、回复及 AI 标识。该引用卡片出现明确“回复”入口，veil 从此入口发送一次原生引用；实际 history 和持久 consumer 都保留引用目标与原文。矩阵新增群出站、群入站两格：51通过、12阻塞、1部分。私聊入站引用及其余缺口不豁免，7个 MUST 仍未完整。

## 执行与证据

1. 只读核对原 manager 三服务归属、loopback health 两路同步完成、DWS ready、98任务和零未决投递；未发认证或诊断探针。取两路六库前后只读事务快照，各库独立，不称共同原子点或历史截止覆盖。
2. veil 在授权群原生发送一条新的普通文字，包含中文、换行和 emoji。当前受管 history 收到后，以已观察源 ID 调用一次 `/v1/send`，固定原 key，不重发。HTTP 200，约1.31秒，回执 confirmed；原生 UI 和回读 history 均确认引用关系。
3. 群引用卡片上新出现明确“回复”按钮。点击后保存带引用的输入框，再由 veil 原生发送一次普通回复。实际 `quotedMessage.messageId` 指向 liev 的引用回复，原文与该回复 history 正文精确一致；consumer 的规范化 quote 保留 ID、会话、发送者名称和正文。
4. 新增恰好三条 transport/history/inbox 消息、一条 confirmed delivery。两路全部98任务、238条 Agent outbox、session/meta 与旧记录逐字段保持；三条新 inbox 均 normalized、无错误且 cursor 已覆盖。没有触发 Agent，没有服务操作、部署、绑定迁移或凭据操作。

实际现场继续为 E123/e7d82cc、AIC Kimi/原私聊 Pi。E127/500191a 的22模块候选仍未部署，本次 UI 成功不能当作 OpenClaw 真实验收。

## 复核及保留的边界

[只读审计工具](../scripts/accept_group_quote_ui.py)对已捕获资料执行33检查，结果见[脱敏证据](../evidence/2026-11-15/group-quote-ui-validation.json)。四个独立篡改负例（出站引用 ID、入站引用正文、额外任务、UI 图片字节）均被拒绝；不调用服务或重新发送。原始请求、六库、原消息、5组 AX/截图、初次/最终审计和负例只留 `local/group-quote-20261115`。

初次审计误将 consumer 成功状态写为 `acked`，实际 schema 为 `normalized`，导致该检查失败；原失败保留，仅修复审计并增加规范化引用检查，没有产品修复或重新执行 UI。应用名称查询“钉钉”失败后使用已发现的 bundle ID 成功，不属于登录故障。

原生回复带自动 mention，history 正文包含其显示文本和额外空格；AX 输入位置将 mention 投影为“未知”，截图显示实际名称。因此只要求新正文完整包含、引用原文与实际 history 精确相等，不把渲染正文与用户输入逐字等同。上游 quotedMessage 本次仅给发送者名称，未给 sender ID；规范化 senderId 保持空，不推造 ID。未验跳回原文、已读状态、任意嵌套层数、引用附件组合。

本次纠正了把“旧客户端入站引用入口未找到”外推成“群出站引用也必须等待新 API”的过宽阻塞。已有实现且未验的矩阵格可以独立执行；同一路径已过样本不重做。下一检查未验群多附件组合的明确原生入口，私聊入站引用只在明确新入口出现后执行，旧右键/菜单/快捷键路径仍停止重复。
