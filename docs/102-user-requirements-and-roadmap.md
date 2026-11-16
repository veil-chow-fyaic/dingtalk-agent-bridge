# 用户需求、交付现状与后续路线

更新：2026-11-16，E134通用IM组合真实API/原件及部署；E133实现与E132文档修复保留。**真实群/私聊任务与文件交付已经成立，完整产品验收尚未完成。** 本页为当前结论入口；历史实验保留在阶段报告和[EVIDENCE](../plans/completion/EVIDENCE.md)，动作清单在[TODO](../plans/completion/TODO.md)。

## 产品和原验收范围

主线是官方DWS真人账号的通用钉钉IM通道：群/私聊收发、历史、引用、媒体原件、路由、幂等和持久消费可独立使用。可选Agent接入后，另提供真实任务、多轮上下文和同会话结果交付；模型订阅不构成通道开发或验收的统一前提。

CLI/HTTP/consumer独立，gateway可选；账号、组织、会话及runtime通过配置选择，不新建bot或固化测试组织。官方身份、通讯、历史、资源和办公直接复用DWS；bridge负责路由、白名单、持久任务/session/outbox、原件摘要、幂等、取消及恢复。

原[PRD](../plans/completion/01-PRD.md)保持17项：R01–R14为MUST，R15–R17为SHOULD。R09要求至少一个本地执行器，已满足；四runtime全部真实通过不是新增门槛。办公更多流程、外部群/跨组织、流式审批仍按SHOULD，不通过增加成员或权限扩大现场范围。

## 版本与证据层次

| 层次 | 最近有证据的版本/事件 | 结论 |
|---|---|---|
| 最近真实部署 | E133产品 `2467fe2`，E134部署/通道验收 | 23模块与E133冻结验证一致；群Kimi/私聊Pi 0.84.2绑定不变，99任务/240 Agent outbox及session保持 |
| 已部署、尚未完整验收的范围 | E133 composition；包含E127 `500191a` OpenClaw适配 | 组合两路真实发送/history/官方下载通过，客户端呈现/保存未验；OpenClaw代码随包存在，未配置绑定或调用真实provider |
| 最近真实UI | E131 `3a0e3ad` | 群单消息文字＋两PNG入站；Kimi Code订阅访问403，任务失败，接收/失败文字可见 |
| 文档治理E132 | 文档、索引与离线一致性核验 | 历史正文/原标准保持；E134同步部署与分层验收，后续文档HEAD不能冒充部署产品 |

E123现场Pi实际Python533/同session542、JSON/TXT下载打开/SHA、取消95秒无late和9回复均有记录；第一任务是Python算数后write写JSON，不冒称同Python写文件。Kimi/Codex/Pi各自历史通过范围保留，当前Kimi403不能抹除旧成功，也不能以旧成功否定这次拒绝。见[运行器接入表](architecture/agent-integration-map.md)。

## 最近实际推进

| 事件 | 实际产出 | 不应外推的结论 |
|---|---|---|
| E124 | 原AIC观察自然到期收尾，Qwen admitted/completed与现有事务映射，5真SIGKILL方法在冻结源/原wheel双Python分别通过 | 2879采样含14不可达、16 poll_error、9维护；后续六库不是截止/共同原子快照，不称健康24h或自然失效refresh |
| E127–E128 | OpenClaw官方local合成CLI、完整UUID、整JSON终态、取消、父进程死亡、gateway恢复和new隔离 | E127最终423×3；E128只新增3专项×3，不称426全量；真实provider/UI未验 |
| E129 | 固定DWS main增量14提交/23文件核对 | VoIP入会/纪要字段不是IM原生入口；固定chat原文超时未计已读，不凭旧检查声称今天的上游状态 |
| E130 | 群出站reply_to及新卡片“回复”入站，UI/history/consumer双向通过；33检查/4负例 | 无引用sender ID不补造；AX mention未知与截图名称分开；没有产品/部署变更 |
| E131 | 文字＋两新PNG组成一条原生消息和一个任务，顺序、缓存、暂存字节/SHA一致；32审计/5负例 | Kimi只出版本事件，provider.auth_error 403；failed/runtime_terminal_missing，无工具/结果文件/重做。审计通过不是任务成功 |
| E133 | 独立IM组合发送候选：文字＋1–9图、逐原件SHA/有序暂存、一次官方Markdown发送、持久幂等；CLI/HTTP合成链路验证 | 当轮无真实组合发送或原件下载验收；用户授权一次最小Kimi请求仍403，不能断定周限额，详见[阶段结果](134-outbound-composition.md) |
| E134 | 部署2467fe2，群/私聊各一条组合confirmed；文字和两图顺序/history、四张官方下载原件与原件/暂存字节及SHA一致，34检查/5篡改负例 | 无新模型任务；自身消息inbox保持pending_media，离线物化另计。UI读取连续两轮失败，客户端呈现/保存未验，R07不升级；见[阶段结果](135-composition-api-deployment.md) |

E132保存的2026-11-16 09:44（北京时间）本地只读状态核对：三个受管进程running，DWS准入ready，两路last_sync complete。99任务（84 completed、5 cancelled、7 failed、1 blocked、2 interrupted）；240 Agent outbox（239 confirmed、1 rejected）。这是一个时点的已保存状态，不是新UI或连续健康证明。09:44核对时HEAD仍为E131，未发现其后新任务或提交；这一段心跳等待不能算实质推进。E134的后续部署/API实测另列，未把等待时长计为进度。

## 验收与剩余工作

[矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)64格为 **51通过、11阻塞、2部分**；14 MUST为 **7通过、4部分、3未完成**。这是覆盖分布，不是项目完成百分比。七项未完整为R01/R04/R06/R07/R12/R13/R14。

| 缺口 | 已有事实 | 下一条能推进的证据/退出条件 |
|---|---|---|
| R04 私聊入站引用1格 | 群双向及私聊出站已验；E027旧私聊截图没有群卡片同样的明确回复控件 | 明确新的私聊原生回复入口，再核目标ID/原文、history/consumer和UI；不重跑旧右键/菜单/快捷键 |
| R06 原生语音4格、独立video4格 | 音视频文件原件可获取/播放；没有对应原生协议闭环 | 目标身份可用的原生协议入口或真实事件，四方向逐格核类型、原件及用户呈现 |
| R07 出站组合2阻塞、群/私聊入站各部分 | E017普通文件拆条；E056为最多9图计划；E133实现、E134部署并验两路组合API/history/官方逐原件；E131群双PNG原件入站已验 | UI恢复可读后核E134既有消息的发送者/AI标识、完整图文和逐图保存摘要，不重复发送。普通多文件单消息仍缺入口；当前原生UI连续两轮failedToCreateImageDestination，停止同路径重试。任务处理/交付另计，群模型部分先需既有Kimi Code访问恢复的新证据，不登录修复/复制token/换runtime绕过，不重发E131 |
| R13 长期与自然失效refresh | 两个旧run已结束，失败/维护及缺截止事实封存；预刷新不等于自然失效refresh | 合规自然业务下的新续期事实、稳定版本长期覆盖与同次截止账本；不改token/时钟、不重置旧run或用事后快照补造 |
| R01/R12/R14 最终通用交付 | 文档、模板、离线安装和历史包已有；E132补文档一致性 | 全部MUST满足后，冻结当前版干净检出/安装/许可/模板/隐私/manifest及最终自检；E121旧包不能代表Pi/OpenClaw版 |

已有明确入口但未验的项可独立推进，不能一概要求“新API”；受阻旧路径的loop guard保持。没有新入口/外部条件时保持未完成，不循环重做旧实验。OpenClaw真实模型/UI属于独立产品演进，需专用现成授权配置；无此条件不复制其他runtime凭据。CEO C01–C04/C06及Qwen事务对照已完成，不重复实现；C05租约仅有多宿主实际需要时做。

## 产出、运行与约束

| 产出 | 入口 |
|---|---|
| 产品/安装/六CLI | [源码](../dingtalk_bridge/) · [pyproject](../pyproject.toml) · [运行手册](15-service-runbook.md) |
| 通用接口/配置 | [OpenAPI](../api/openapi.json) · [路由模板](../config.routes.example.json) · [执行器模板](../config.agent.example.json) · [接口手册](22-generic-tool-and-consumer.md) |
| 参考采用和来源 | [采用账](references/adoption-plan.md) · [固定catalog](references/catalog.json) · [CEO来源](references/ceo-deep-dive-index.json) |
| 证据/问题/自检 | [EVIDENCE](../plans/completion/EVIDENCE.md) · [风险清单](114-dws-risks-and-resolution.md) · [最终自检](../plans/completion/10-自检清单.md) |
| 全部资料 | [导航](README.md) · [完整索引](INDEX.md) · [本轮文档修复](133-documentation-consistency.md) |

只在AIC测试群及原veil/liev私聊实测；企业大群/旧群禁测，不加人/bot/权限。原生客户端veil和显式profile真人liev的身份/AI标识分别取证。禁止真实auth/login/doctor、Keychain读/锁/解锁、认证修复、复制token、改权限、重启Mac或绕系统工具限制，不索取密码/第二账号。

正常受管业务与已有恢复授权保持；凭据故障持久暂停，不自动恢复。恢复先transport，gateway停机核同一SQLite快照watermark≥固定cut且无history_window，停传输核积压后再开放执行；last_sync.at不代替覆盖。未知投递原key对账，不补发。原始身份、聊天、截图、数据库、下载和日志只留local。

[AGENTS](../AGENTS.md)约束执行，[关键路径](../plans/completion/CRITICAL_PATH.md)给启动条件；全部MUST及最终自检满足才标完成并停心跳。
