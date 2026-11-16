# 通用接入续作：迁移、会话发现、持续接收与版本限制

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


本页保留 runtime 接入之前的续作验收快照（18 条事件、39 项回归）。当前 Kimi 实际接入、25 条事件、51 项回归见 [docs/24](24-local-agent-product-and-acceptance.md)；不要把本页历史数量当作当前账本。

2026-11-11。接续原对话后，重新读完全部用户要求、核对原代码与26项测试；本次新增13项测试，合计39项通过。本页描述新增交付，当前总状态仍以 [17](17-requirements-progress-review.md)、工作清单以 [13](13-roadmap-and-backlog.md) 为准。

## 已解决的实际问题

| 问题 | 修复与验证 |
|---|---|
| v1单路转v2多路由会改用空账本 | 迁移将原路由标为 `stateStorage: legacy`，原地继续使用数据库、staged和downloads；不移动文件，不改变幂等payload中的路径。真实18条事件、4条投递记录逐字段一致 |
| 本人附件可能占满每轮hydrate的前20条 | 先过滤不参与下载的sender，再应用批量限制；25条本人附件后的一条他人附件能被处理。属于确定性测试，不冒充他人现场入站 |
| 账号别名与另一账号profile文本相同会误报重复 | 分开检查公开路由键与认证身份键；仍拒绝真正重复会话和多个legacy状态占用者 |
| 上游缺少messages字段却宣称complete | 拒绝该响应，不推进同步水位 |
| Agent只能重复短轮询 | events增加最长30秒等待；同一路由最多16个等待者。数据库提交后唤醒，断开后可从原seq继续；空等待不改游标 |

真实迁移证据：[continuation-acceptance.json](../evidence/2026-11-11/continuation-acceptance.json)。没有发送新消息，也没有办公写入。

只读复核命令：`python3 scripts/accept_continuation.py`。它读取原迁移前快照核对账本、发现元数据并有界续读shadow消费者，不发送、不订阅。若后续实际新增消息导致快照不一致，应分析增量，不能覆盖原快照伪造通过。

## 会话发现与选择

```bash
python3 -m dingtalk_bridge.cli --account-id A discovery --limit 50 --cursor 0
```

`GET /v1/discovery?account_id=A&limit=50&cursor=0` 只读DWS当前账号可见的会话元数据，不读取消息正文，不添加监听。结果带稳定ID、类型、展示名、是否已配置和分页完整性。存在下一页时继续传next_cursor；缺失分页证明不宣称全集完整。不要按同名候选第一项猜目标。

本机读取到12个候选；当前仍只启用原单人群。发现私聊不等于私聊收发通过；列表中的owner ID也不能当作对端ID。私聊选择仍需独立确认 `peerOpenDingTalkId`。

显式准备另一个会话的配置（模板，不是本轮扩大监听的操作）：

```text
python3 -m dingtalk_bridge.configure --config local/service-config.json --output local/proposed-routes.json select --account-id A --conversation-id C --type group
python3 -m dingtalk_bridge.configure --config local/service-config.json --output local/proposed-routes.json select --account-id A --conversation-id C --type direct --peer-id PEER
```

选择时用官方conversation-info再次核对精确会话ID；私聊与群聊使用不同参数。输出仅生成新文件、权限0600；不会激活新路由，不覆盖运行配置，不创建群。真实新增会话仍须在用户指定范围内。

## 保留状态的配置迁移

```bash
python3 -m dingtalk_bridge.configure --output local/service-config.v2.json migrate
```

生成v2配置后，检查原账号别名、profile、conversationId和selfSenderId保持一致，原路由有 `stateStorage: legacy`。停服务，备份原配置，再原子替换运行配置并启动。新添加路由不带legacy，使用其独立摘要目录。全程保留旧配置及数据库；无需复制/删除SQLite、附件、消费者或令牌。

本机已经执行上述迁移和重启；备份仅在 `local/continuation-20261111/`。旧consumer仍继续原游标，fetched=0；18条本人消息、2条引用、13个媒体部件保持一致。回退配置格式也使用同一原账本，不通过恢复旧数据库回退，以免丢掉新增投递记录。该标记不能用于给另一身份“继承”账本。

## 持续消费与可选订阅

```text
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C events --after CURSOR --wait-seconds 25
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C --follow
```

consumer提交事件与游标后才下载媒体；`--max-batches` 可做有界运行，Ctrl-C正常关闭。网络故障退出后重跑同一consumer即可从提交游标继续。没有模型调用、自动回复、处理租约或业务ACK；`ready`不是业务已经完成。

每条route可显式设置 `receiveMode: stream_hint`，重启后启用DWS个人事件订阅。默认 `history`。群只订阅 `user_im_message_receive_group`；私聊只订阅 `user_im_message_receive_o2o`，不使用全部群/全部私聊监听。固定版本[EventKey契约](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-keys.md)支持这一映射。

事件只用于提前唤醒历史读取：先核对conversation_id和message_id，不把可能只有描述的媒体事件正文作为完整内容传给Agent。上游[事件输出文档](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-event/references/event-im-output.md)明确媒体需进一步读取。重复提示合并唤醒，消息仍按原生ID去重；监听断开采用退避重连，历史轮询始终保留。健康接口公开连接状态、ready和计数，不公开订阅凭据或原事件。

真实12秒生命周期验证：ready一次，业务事件0条，退出码0；退出后active subscriptions=0、consumers=0。[证据](../evidence/2026-11-11/stream-lifecycle.json)。共享bus进入300秒空闲回收，不强杀。**这没有验证业务事件投递、索引延迟或实时消息完整性。**本机常驻配置仍为history，仅本轮短时测试开启订阅；订阅提示不是独立于历史索引的完整接收后端。

## 原生音视频：固定版本结论已闭环

本次查询官方发布接口，最新稳定版仍为 [v1.0.67](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.67)。固定源码 `executeMessagesSendUserFile` 把file/audio/video统一上传为文件，调用 `send_personal_message` 时明确为 `msgType=file`；[代码定位](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/unified_send.go#L778)。本机对WAV/MP4分别dry-run，均得到effectiveMessageType=file，没有发送。[证据](../evidence/2026-11-11/native-media-boundary.json)、[版本记录](../evidence/2026-11-11/upstream-continuation.json)。

因此普通账号通过当前DWS这两个发送入口不能生成原生语音条/视频消息。文件原件传输已通过；原生发送需求仍未实现。该结论不外推到所有钉钉API或未来版本。继续工作应针对新的官方用户媒体入口，或以已证实缺口为依据研究局部AX，不重复上传相同WAV/MP4期待不同消息类型。

## 尚未关闭的关卡

- 他人无@入站、人与人私聊、外部会话和对端播放仍为用户要求的skipped_by_user。
- 订阅提示后的精确消息补全、复杂富文本/转发/撤回、超过1000条历史窗口，以及超过24小时才索引的消息仍有缺口。
- 24/72小时观察、令牌过期、长断网、磁盘配额/资源保留和完整办公功能仍未完成。新增13项测试证明本次修改，不替代这些验收。

当前交付是改进后的通用实验工具，不以任一业务runtime接入作为前置，也未声称整个产品已验收完成。
