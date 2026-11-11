# DingTalk Agent Bridge

通用钉钉 IM 工具：任意 Agent/程序通过统一 CLI 或 HTTP 接入普通账号私聊、群聊及组织工具，不依赖特定组织或 Agent runtime。官方 DWS 优先；AX只补已证实缺口，不预设完整移植WeCom。

**2026-11-11双账号基础UI验收通过：veil在客户端交办，liev真人账号自动回复。**原群和私聊均完成文字任务、Kimi执行、文件回传、客户端下载打开；另通过CSV上传计算、多轮上下文、普通群消息不触发和重启不重跑。当前为DWS `--as user`，没有创建bot。详见[最新双账号验收](docs/27-two-account-ui-acceptance.md)；自动测试与UI观察分开记录。

2026-11-12最新：[Stream真实断连与模型失败保留](docs/44-stream-network-recovery-and-runtime-failure.md)。已建立的WebSocket实际断开89.446秒，history继续承接任务；恢复后同一daemon重新收事件、无重复。A实际计算后模型输出不合JSON契约，失败提示UI可见且原失败保留；B新任务3127完成，37B文件客户端下载打开。50项审计/4项负向检查/131项回归通过，装置已撤除。

前轮补验：[两段长回复原生界面核对](docs/42-long-bubble-native-ui.md)和[私聊历史接口真实断网恢复](docs/43-history-network-outage-recovery.md)。断网78.310秒期间，veil仅发送一次任务，恢复后自动补收，Kimi实际计算1591、文件回传并客户端下载打开；没有重发或靠重启完成恢复。22项长文/42项恢复审计及5项负向检查通过。原配置已恢复；引用、完整Stream断网、凭据过期和24h仍缺。

2026-11-12办公接入：[官方工具上下文与真实私聊任务](docs/41-official-office-agent-ui.md)。veil交办、Kimi使用绑定liev身份的官方DWS完成文档/本人待办/本人日程/未发送草稿，三个任务九条确认回复，三份报告均客户端下载打开。新上下文默认关闭，现场只对私聊启用；不另造办公API，也不是强制权限沙箱。原报告的密送字段过度推断已通过只读任务更正，原件保留。最终126项回归、69项只读审计及干净安装通过；整个项目仍待余下UI、真实失效凭据恢复和24h验收；Stream断连已在E024独立补验。

图片接入：[原生图片 bridge 与实际 Kimi 结果交付](docs/33-native-image-bridge.md)。本地上传→独立 image 已实现，私聊两份原件客户端下载、Quick Look 打开及字节校验通过；其中一份由 veil UI 交办、Kimi 实际生成。官方 v1.0.67 缺独立上传叶子，以隔离补充命令复用官方上传/鉴权，原版 DWS 不变。原群现为3人，新群图测试待范围确认；JPEG等未由PNG结果外推。

音视频进展：[WAV/MP4私聊双向、实际分析与客户端下载打开](docs/34-audio-video-file-progress.md)，四格与两份Kimi报告通过。MP4按file发送，但客户端呈现可播放视频卡片；WAV语音条和独立video协议仍未证实，群四格待范围确认。

最新文件验收：[XLSX/ZIP八格双向与实际任务](docs/31-xlsx-zip-ui-acceptance.md)。四份客户端原件下载后打开/解包，两个Kimi任务及TXT客户端下载打开通过；此前[DOCX四方向](docs/30-docx-ui-and-reliability-start.md)保留。24h观察于11月11日19:36启动，尚未达时长。

任务控制：[私聊状态、实际取消与新会话隔离](docs/36-task-control-ui.md)完成9次UI请求、14条确认回复；修复空闲状态误报排队1。该阶段95项回归通过，旧失败记录保留。

多文件：[两份文件上传与后续合并任务](docs/37-multiple-files-and-followup.md)。一次多选被客户端拆成两条消息，两个附件任务实际读取；后续同会话合并得到40，TXT客户端下载打开及50项只读检查通过。没有将此标成单条多附件或自动合批。

长文修复：[真实超限失败与UTF-16分段](docs/38-long-text-limit-and-regression.md)。实测发现官方普通账号text上限5120个UTF-16单位，已修复含前缀的分段并新增发送前校验；新任务两段确认、文件客户端下载打开，99回归通过。原失败快照保留，官方会裁掉末尾换行；两段完整气泡的原生AX及首尾/分段边界视口已补验，见[docs/42](docs/42-long-bubble-native-ui.md)。拒绝终态后续已按E019对账。

拒绝处理：[有证据的终态对账与真实UI失败提示](docs/39-rejection-reconciliation-and-feedback.md)。原超限发送现为rejected，原unknown与日志完整存档，未重发；客户端可见部分回复未送达及未确认0/拒绝1，108回归通过。

恢复验收：[常驻Stream唤醒与双账号停机补漏](docs/29-stream-service-and-offline-recovery.md)。veil真实UI发出5条实验消息，3个任务与6个回复通过；服务停机补读、订阅子进程重连及旧任务不重跑已有现场证据。

媒体扩展：[PNG/PDF双向、真人图片缺陷修复与真实事件](docs/28-media-matrix-and-real-events.md)。8个传输案例、10份资源原件一致；群/私聊识图任务UI通过，真实Stream采到16条业务事件。尚未完成所有格式及长期稳定性。活动长任务见[续跑入口](plans/completion/INIT.md)。

目标是把钉钉作为本地 Agent 的工作入口：群聊/私聊交办、附件输入、执行反馈、连续上下文与结果交付。bridge 保持通用，同时交付可用的具体 runtime 接入。官方已有 `dws dev connect` 机器人本地接入；我们补的是普通账号路线的执行与恢复。官方/自研边界、71项回归和新增现场场景见 [能力边界与场景台账](docs/25-official-boundary-and-scenarios.md)。先看 [实际使用与验收](docs/24-local-agent-product-and-acceptance.md)。

## 先读这五份

| 要回答的问题 | 入口 |
|---|---|
| 用户真正需求、现在完成多少、还缺什么 | [总状态与需求追溯](docs/17-requirements-progress-review.md) |
| bot是否受限，普通账号能覆盖哪些外部会话 | [身份×会话证据矩阵](docs/18-identity-and-conversation-boundaries.md) |
| 新项目怎样接入、管理员要做什么、踩过什么坑 | [开通手册与经验](docs/11-onboarding-lessons.md) |
| 哪些已经实测，怎样复现且不重复发消息 | [最新验收与配方](docs/20-gap-acceptance-and-reproduction.md) |
| 剩余工作的状态、依赖和验收条件 | [当前执行清单](docs/13-roadmap-and-backlog.md) |

## 完整文档索引

| 分类 | 文档 |
|---|---|
| 需求与研究 | [01综述](docs/01-research.md) · [02能力](docs/02-capability-matrix.md) · [12需求边界](docs/12-requirements-and-scope.md) · [18身份与外部会话](docs/18-identity-and-conversation-boundaries.md) |
| 开通与办公 | [06人工清单](docs/06-human-checklist.md) · [11经验库](docs/11-onboarding-lessons.md) · [19办公与权限](docs/19-office-tools-and-permissions.md) · [41官方办公Agent闭环](docs/41-official-office-agent-ui.md) |
| 客户端与身份 | [27双账号私聊/群聊与文件验收](docs/27-two-account-ui-acceptance.md) · [26真实UI输入、结果打开及发送身份](docs/26-ui-acceptance-and-sender-identity.md) |
| 官方与自研边界 | [25官方入口、复用范围与场景验收](docs/25-official-boundary-and-scenarios.md) |
| 本聊天续作 | [24本地 Agent 使用与验收](docs/24-local-agent-product-and-acceptance.md) · [23迁移、发现、持续接收与版本限制](docs/23-continuation-and-migration.md) |
| 实现与接入 | [03 WeCom对照](docs/03-wecom-reference.md) · [04架构](docs/04-architecture.md) · [10协议](docs/10-protocol-notes.md) · [15服务运维](docs/15-service-runbook.md) · [21通用边界](docs/21-existing-runtime-integration.md) · [22工具接口与消费](docs/22-generic-tool-and-consumer.md) |
| 验收与交接 | [05测试协议](docs/05-validation.md) · [20最新实测/复现](docs/20-gap-acceptance-and-reproduction.md) · [13清单](docs/13-roadmap-and-backlog.md) · [17总状态](docs/17-requirements-progress-review.md) |
| 来源与历史 | [08来源](docs/08-sources.md) · [09决策沿革](docs/09-decisions.md) · [07最初本机实验](docs/07-local-results.md) · [14 v1.0.61基线](docs/14-solo-test-report.md) · [16 v1.0.67首版服务](docs/16-implementation-acceptance.md) |

07/14/16保留当时的日期、软件版本和数量；当前结论以17/13为准。每条能力区分官方契约、上游报告、本机API、原件、客户端呈现、对端实收，不从单人结果外推全钉钉覆盖。

安装与运行：[统一后台管理与真实重启验收](docs/40-service-manager-and-restart-ui.md)提供六个入口、传输＋可选多gateway启动/停止；119项回归和新wheel验证通过，真实私聊任务结果已客户端下载打开。[只读doctor](docs/35-install-and-doctor.md)保留独立诊断语义。

## 当前环境与可运行内容

用户已授权：客户端veil（组织名周威），DWS精确绑定liev；只监听原内部群和这两人的私聊。组织/profile是鉴权路由上下文，不是产品固定租户。旧周威账本与配置备份保留。

隔离DWS v1.0.67、全局v1.0.61保留。HTTP+SQLite监听127.0.0.1:18768，官方Stream提示唤醒history，另每15秒补读两个指定会话；群和私聊各一个Kimi gateway，仅允许veil发任务，liev自身消息忽略，无开机自启。70事件/5任务/14投递是docs/27的历史基线；新增媒体、事件、恢复任务见docs/28–29，以实时status为准。私聊直接发文字/附件，群以 `/agent` 开头。Kimi没有OS级沙箱，未对任意联系人开放。

```bash
python3 -m dingtalk_bridge.doctor --agent-config local/agent-config.json --agent-config local/agent-direct-config.json --live
python3 -m dingtalk_bridge.service_manager status
python3 scripts/accept_media_matrix.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_handoff.py
```

以上不发送消息。启动/停止、令牌、消费游标和未知投递对账见docs/15。请不要为查看结果重跑写入实验。

## 目录与共享边界

- `docs/`：44份当前/历史分明的知识文档。
- `evidence/`：脱敏实测与公开来源/Help，`handoff-manifest.json`记录可交接文件摘要。
- `fixtures/`：合成素材；`scripts/`：基线、显式实验、服务管理和完整性校验。
- `dingtalk_bridge/`、`tests/`：实验服务、本地 Agent gateway 和131项回归。
- `local/`：忽略的二进制、账号配置、原始回复、令牌、数据库、附件及日志。**不整包分享这个目录。**

已建立本地Git分支`codex/complete-bridge`及基线标签`baseline/ui-2026-11-11`；没有发布远程。提交钩子检查暂存blob中的已知账号ID/令牌和私密路径。`plans/completion/`是唯一活动任务/证据账本，Codex心跳每30分钟续跑（依赖机器与应用在线）。本轮留存的测试对象和清理边界见docs/19、20；未经核实不批量删除。

通用纯文本引用回复：`dab ... send --key STABLE_KEY --reply-to SOURCE_MESSAGE_ID --text TEXT`；源必须已在所选路由观察到。HTTP同名字段reply_to，未知投递不重发；私聊原生UI已验，详情与未验边界见[引用回复](docs/46-quoted-text-reply.md)。
