# 用户需求、交付现状与后续路线

更新：2026-11-17，E147。用户明确授权sub agents分别实现推进；主Agent负责集成、提交及现场操作。DWS CLI优先、实际需求驱动。**核心功能可受控使用，长期无人值守成熟度及全部原MUST仍未通过。**

2026-11-17 E146：ImageIO日志确认本次截图临时目标ENOENT，补建缺失目录后原CUA读取/点击/截图恢复；目录消失机制未知。原私聊一次原生引用经UI/history/consumer验证且未触发任务，R04通过。E134两路完整图文/发送者/AI标识已见，逐图保存仍失败；52通过/10阻塞/2部分，剩R01/R06/R07/R13四项MUST。产品2b479a8、固定v67及原观察不动，11月17日18:29:37固定截止，无调度。

本轮[新安装修复与故障恢复](145-delivery-and-recovery-closeout.md)包含准确测试层次及候选补丁。DWS原因与完整取消候选见[E145](146-dws-root-cause-and-integration.md)。现行动作见[TODO](../plans/completion/TODO.md)，最新部署见[E143](143-parallel-hardening.md)。最近原生UI为E146：私聊引用入站通过，E134两路组合可见层补齐；逐图客户端保存仍未成功。

E147已整理[首次使用](getting-started.md)、[四项任务路线图](ROADMAP.md)、贡献/安全/变更入口及CI工程规范；验证与GitHub实际状态见[阶段记录](148-github-project-maintenance.md)。目标/可见性/许可待用户选择，未推送或声称托管CI通过。原产品、现场验收及观察不因此升级。

## 产品和原验收范围

主线是官方DWS真人账号的通用钉钉IM通道：群/私聊收发、历史、引用、媒体原件、路由、幂等和持久消费可独立使用。可选Agent接入后，另提供真实任务、多轮上下文和同会话结果交付；模型订阅不构成通道开发或验收的统一前提。

CLI/HTTP/consumer独立，gateway可选；账号、组织、会话及runtime通过配置选择，不新建bot或固化测试组织。官方身份、通讯、历史、资源和办公直接复用DWS；bridge负责路由、白名单、持久任务/session/outbox、原件摘要、幂等、取消及恢复。

原[PRD](../plans/completion/01-PRD.md)保持17项：R01–R14为MUST，R15–R17为SHOULD。R09要求至少一个本地执行器，已满足；四runtime全部真实通过不是新增门槛。办公更多流程、外部群/跨组织、流式审批仍按SHOULD，不通过增加成员或权限扩大现场范围。

## 按实际使用解释媒体能力

“文件语义”只是DWS使用的传输类型，不代表只能传不可预览的附件。MP4已经在钉钉中显示视频卡片并实际播放；不能把“独立video协议未验”缩写成“视频不支持”。以下是已有实测范围，不把历史任务成功说成当前每个可选模型都可用。

| 用户要做的事 | 已验证程度 | 边界 |
|---|---|---|
| 收发TXT/CSV/PDF/DOCX/XLSX/ZIP | 群/私聊双向原件、下载打开；代表性真实工具处理及结果回传 | 非所有复杂文档/宏/加密/超大文件认证 |
| 收发PNG/JPEG图片 | 群/私聊双向；原生图片气泡、查看器、下载原件及实际读图/处理已有样本 | 原图image路径≤2MiB，较大走文件；不外推所有图片格式 |
| 收发音频文件 | WAV群/私聊双向，原件下载和播放器打开；实际音频分析、另有21.93秒合成语音经官方听记转写样本 | 未验聊天语音条；未单独认证MP3/M4A、长录音或自动转写所有输入 |
| 收发视频文件 | MP4群/私聊双向；钉钉视频卡片/播放、下载、系统打开及实际ffprobe/抽帧分析 | 样本约1秒、小型H.264；未外推长视频/所有编码，独立video消息协议未验 |
| 多个文件交给同一任务 | 多条附件消息关联到一个任务已有实测，多个输出可逐件交付 | 不等于任意多个文件合在一个消息气泡 |
| 一条文字加多图 | 双PNG入站原件已验；私聊有实际任务/报告。两路出站组合API/history/四张官方原件已过 | E146两路客户端完整呈现/发送者/AI标识已验，逐图保存仍未成功；代码支持1–9图，真实只验双PNG。群新任务Kimi403另计 |

证据入口：[四方向矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)、[音视频实际表现](34-audio-video-file-progress.md)、[出站图文实测](135-composition-api-deployment.md)。当前输出单文件限制20MiB。首选现有DWS发送/下载/Markdown能力；独立image上传仅补官方内部上传能力的CLI入口，复用官方认证/实现，没有另造通讯协议。bridge补持久消费、路由、幂等、原件和可选任务管理。

E139用户追问支持程度并明确DWS优先，尚未批准原基线改级。保留“语音条/独立video未验”的历史格，但只有真实用户行为缺口才驱动新增实现，协议名称本身不构成另造通道的理由。

## 版本与证据层次

| 层次 | 最近有证据的版本/事件 | 结论 |
|---|---|---|
| 最近真实部署 | 产品 `2b479a8`，E143部署/短采集 | 25模块启动来源/配置一致；群Kimi/私聊Pi 0.84.2绑定不变，99任务/240 Agent outbox及session保持 |
| 已部署、尚未完整验收的范围 | E133 composition；包含E127 `500191a` OpenClaw适配 | 组合两路真实发送/history/官方下载通过，E146客户端完整呈现/身份/AI标识已验，逐图保存未成功；OpenClaw代码随包存在，未配置绑定或调用真实provider |
| 最近真实UI | E146，运行产品仍2b479a8 | 私聊原生引用UI/history/consumer通过且无任务副作用；两路既有组合完整文字/双图/身份/AI标识可见，逐图保存失败保留 |
| 文档治理E147 | 用户入口、CI工程规范、完整索引和离线核验 | 历史正文/原标准保持；GitHub目标待定，尚无托管CI结果，文档HEAD不能冒充部署产品 |

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
| E146 | 原CUA临时截图目录补建后恢复；E134既有两路图文/身份/AI标识可见；一次私聊原生引用UI/history/consumer通过，R04收口 | 目录消失机制未知；E011三点击保存仍失败，R07不改级；99jobs/240outbox/tasksmeta及delivery/manager/25模块保持，原观察不动；见[阶段报告](147-native-ui-recovery-and-dm-quote.md) |

E132保存的2026-11-16 09:44（北京时间）本地只读状态核对：三个受管进程running，DWS准入ready，两路last_sync complete。99任务（84 completed、5 cancelled、7 failed、1 blocked、2 interrupted）；240 Agent outbox（239 confirmed、1 rejected）。这是一个时点的已保存状态，不是新UI或连续健康证明。09:44核对时HEAD仍为E131，未发现其后新任务或提交；这一段心跳等待不能算实质推进。E134的后续部署/API实测另列，未把等待时长计为进度。

## 验收与剩余工作

[矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)64格为 **52通过、10阻塞、2部分**；14 MUST为 **10通过、2部分、2未完成**。这是覆盖分布，不是项目完成百分比。四项未完整为R01/R06/R07/R13。R04已由E146私聊引用补齐。R12资料及R14 Git/隐私/可复核检出按自己的原判据通过，不再循环依赖全部功能完成；总体交付签署仍未完成。

| 缺口 | 已有事实 | 下一条能推进的证据/退出条件 |
|---|---|---|
| R04 私聊入站引用（已完成） | E146一次原生引用UI/history/consumer保留精确源关系，未递归旧双图、未触发任务 | 原判据收口，旧失败保留；不重跑该样本 |
| R06 原生语音4格、独立video4格 | 音视频文件原件可获取/播放；没有对应原生协议闭环 | 目标身份可用的原生协议入口或真实事件，四方向逐格核类型、原件及用户呈现 |
| R07 出站组合2阻塞、群/私聊入站各部分 | E134两路组合API/history/官方原件与E146完整图文/身份/AI标识已验；E131群双PNG入站保持 | 逐图客户端保存打开/SHA仍缺，重复E011三点击失败后停止，需新可验证入口，不重发。普通多文件和模型任务另计；群模型需既有Kimi访问恢复证据，不登录修复/复制token/换runtime绕过、不重发E131 |
| R13 长期与自然失效refresh | 旧run的失败/维护/中断及缺截止事实封存；E143已部署2b479a8、短采集通过，新的parallel-hardening run正在运行 | 固定截止后审查原run的账本、采样错误和启动来源，不提前通过；自然续期事实另计。不依赖Kimi/UI，不改token/时钟、不重置旧run或用事后快照补造 |
| R01 新增路由图片配置 | E144新安装发现select遗漏既有imageUploadBinary；最小候选及安装后的双路图片/CLI/HTTP/consumer流程已过 | 原固定cut结束审计后按维护规范集成并验证当前服务；现有路由不受影响，不为该配置助手缺陷打断已运行的固定观察。R12/R14已各自通过；全部MUST最终签署仍另计 |

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

[AGENTS](../AGENTS.md)约束执行，[关键路径](../plans/completion/CRITICAL_PATH.md)给启动条件；全部双方明确的MUST及最终自检满足才标完成。E141已删除调度且不创建替代任务；当前观察的自动采集/收尾不等于聊天自动唤醒或产品验收通过。

E140的[本机HTTP隔离修复](140-local-http-and-actionable-followup.md)已于E142应用并部署为10758eb。三客户端共用直连/拒绝重定向；冻结源码与同wheel安装Python3.14/3.11各477方法通过，现场25模块完全一致。本轮另外核对实际启动来源/CLI/短采集，没有重跑或虚增全量测试数量。

E141完善[通用部署审查](141-deployment-review-and-direct-ownership.md)：显式空WAL/遗留SHM只读检查，非空WAL/journal/锁冲突/变化仍拒绝；调用统一runtime绑定核对。工具及测试已入主工程，冻结源码和两个既有安装环境各12专项通过，不改变运行产品或原MUST判定。

E143实际补齐了日常可靠性缺口：失败的历史同步不再显示无错误，坏图片标记不会被其他合法图片掩盖，单条缓存不可读/循环链接不会阻塞后续正常消息。新[离线导出入口](144-offline-release-export.md)绑定已提交源码、已测wheel及验证记录。E146已补两路组合可见层和私聊入站引用；逐图客户端保存、长期及自然refresh仍未完成。
