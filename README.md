# DingTalk Agent Bridge

通用钉钉 IM 工具：任意 Agent/程序通过统一 CLI 或 HTTP 接入普通账号私聊、群聊及组织工具，不依赖特定组织或 Agent runtime。官方 DWS 优先；AX只补已证实缺口，不预设完整移植WeCom。

**2026-11-11双账号基础UI验收通过：veil在客户端交办，liev真人账号自动回复。**原群和私聊均完成文字任务、Kimi执行、文件回传、客户端下载打开；另通过CSV上传计算、多轮上下文、普通群消息不触发和重启不重跑。当前为DWS `--as user`，没有创建bot。详见[最新双账号验收](docs/27-two-account-ui-acceptance.md)；自动测试与UI观察分开记录。

图片接入：[原生图片 bridge 与实际 Kimi 结果交付](docs/33-native-image-bridge.md)。本地上传→独立 image 已实现，私聊两份原件客户端下载、Quick Look 打开及字节校验通过；其中一份由 veil UI 交办、Kimi 实际生成。官方 v1.0.67 缺独立上传叶子，以隔离补充命令复用官方上传/鉴权，原版 DWS 不变。原群现为3人，新群图测试待范围确认；JPEG等未由PNG结果外推。

音视频进展：[WAV/MP4私聊双向、实际分析与客户端下载打开](docs/34-audio-video-file-progress.md)，四格与两份Kimi报告通过。MP4按file发送，但客户端呈现可播放视频卡片；WAV语音条和独立video协议仍未证实，群四格待范围确认。

最新文件验收：[XLSX/ZIP八格双向与实际任务](docs/31-xlsx-zip-ui-acceptance.md)。四份客户端原件下载后打开/解包，两个Kimi任务及TXT客户端下载打开通过；此前[DOCX四方向](docs/30-docx-ui-and-reliability-start.md)保留。24h观察于11月11日19:36启动，尚未达时长。

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
| 开通与办公 | [06人工清单](docs/06-human-checklist.md) · [11经验库](docs/11-onboarding-lessons.md) · [19办公与权限](docs/19-office-tools-and-permissions.md) |
| 客户端与身份 | [27双账号私聊/群聊与文件验收](docs/27-two-account-ui-acceptance.md) · [26真实UI输入、结果打开及发送身份](docs/26-ui-acceptance-and-sender-identity.md) |
| 官方与自研边界 | [25官方入口、复用范围与场景验收](docs/25-official-boundary-and-scenarios.md) |
| 本聊天续作 | [24本地 Agent 使用与验收](docs/24-local-agent-product-and-acceptance.md) · [23迁移、发现、持续接收与版本限制](docs/23-continuation-and-migration.md) |
| 实现与接入 | [03 WeCom对照](docs/03-wecom-reference.md) · [04架构](docs/04-architecture.md) · [10协议](docs/10-protocol-notes.md) · [15服务运维](docs/15-service-runbook.md) · [21通用边界](docs/21-existing-runtime-integration.md) · [22工具接口与消费](docs/22-generic-tool-and-consumer.md) |
| 验收与交接 | [05测试协议](docs/05-validation.md) · [20最新实测/复现](docs/20-gap-acceptance-and-reproduction.md) · [13清单](docs/13-roadmap-and-backlog.md) · [17总状态](docs/17-requirements-progress-review.md) |
| 来源与历史 | [08来源](docs/08-sources.md) · [09决策沿革](docs/09-decisions.md) · [07最初本机实验](docs/07-local-results.md) · [14 v1.0.61基线](docs/14-solo-test-report.md) · [16 v1.0.67首版服务](docs/16-implementation-acceptance.md) |

07/14/16保留当时的日期、软件版本和数量；当前结论以17/13为准。每条能力区分官方契约、上游报告、本机API、原件、客户端呈现、对端实收，不从单人结果外推全钉钉覆盖。

## 当前环境与可运行内容

用户已授权：客户端veil（组织名周威），DWS精确绑定liev；只监听原内部群和这两人的私聊。组织/profile是鉴权路由上下文，不是产品固定租户。旧周威账本与配置备份保留。

隔离DWS v1.0.67、全局v1.0.61保留。HTTP+SQLite监听127.0.0.1:18768，官方Stream提示唤醒history，另每15秒补读两个指定会话；群和私聊各一个Kimi gateway，仅允许veil发任务，liev自身消息忽略，无开机自启。70事件/5任务/14投递是docs/27的历史基线；新增媒体、事件、恢复任务见docs/28–29，以实时status为准。私聊直接发文字/附件，群以 `/agent` 开头。Kimi没有OS级沙箱，未对任意联系人开放。

```bash
python3 scripts/service_ctl.py status
python3 scripts/agent_ctl.py status
python3 scripts/agent_ctl.py --config local/agent-direct-config.json status
python3 scripts/accept_media_matrix.py
python3 -m unittest discover -s tests -v
python3 scripts/verify_handoff.py
```

以上不发送消息。启动/停止、令牌、消费游标和未知投递对账见docs/15。请不要为查看结果重跑写入实验。

## 目录与共享边界

- `docs/`：34份当前/历史分明的知识文档。
- `evidence/`：脱敏实测与公开来源/Help，`handoff-manifest.json`记录可交接文件摘要。
- `fixtures/`：合成素材；`scripts/`：基线、显式实验、服务管理和完整性校验。
- `dingtalk_bridge/`、`tests/`：实验服务、本地 Agent gateway 和84项回归。
- `local/`：忽略的二进制、账号配置、原始回复、令牌、数据库、附件及日志。**不整包分享这个目录。**

已建立本地Git分支`codex/complete-bridge`及基线标签`baseline/ui-2026-11-11`；没有发布远程。提交钩子检查暂存blob中的已知账号ID/令牌和私密路径。`plans/completion/`是唯一活动任务/证据账本，Codex心跳每30分钟续跑（依赖机器与应用在线）。本轮留存的测试对象和清理边界见docs/19、20；未经核实不批量删除。
