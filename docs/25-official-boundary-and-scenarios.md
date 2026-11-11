# 官方工具与自研边界及场景验收

2026-11-11 核对。GitHub latest release 仍为 DWS v1.0.67；本机使用同版隔离二进制。**平台业务能力优先调用官方工具；自研层负责普通账号会话进入本机 Agent 后的执行策略、持久状态与交付恢复。机器人场景已有官方本地 Agent 接入，不应重复实现后称其为平台缺口。**

## 本次纠正的遗漏

DWS 已有 `dws dev connect`：使用机器人凭证连接本地 Codex 等渠道，支持会话记忆和重置；自定义 CLI 可走 `--agent-cmd`。本机 Help 还列出白名单、限流、工作目录、守护进程、卡片和可配置确认闸。此前只描述 DWS 业务命令而未将这个入口纳入路线比较，是调查不完整，现予纠正。[固定版机器人教程](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/docs/robot-quickstart.md)

它使用机器人身份，教程场景是群中 @ 机器人，不等价于普通账号读取人与人的既有会话。Kimi 不在该版本 Help 的内置渠道列表中；custom 单次 stdout 接入不能自动当作已具备 Kimi 原生 session 续接。当前未创建/添加机器人或启动此入口，故只确认官方契约与本机命令存在，不标现场通过。

另有钉钉官方 OpenClaw Connector，提供机器人通道、会话与媒体处理、交互卡片及办公集成；它要求 OpenClaw 宿主，不能直接作为本项目普通账号路线的等价替换。[官方 Connector](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector/blob/88df00ee594072e9941ef3f71da90a37f3291ad3/README.md)

## 能力归属

| 能力 | 官方入口 | 我们应补什么 | 当前边界 |
|---|---|---|---|
| 认证、刷新、组织账号 | DWS auth/profile、系统凭据存储 | 精确选择已授权 profile，报错与运维 | 不复制凭据，不自行实现 OAuth，不用群名猜账号 |
| 群/私聊历史和发现 | chat +chat-list、+conversation-info、+chat-messages | 配置允许路由、游标、去重、补读和完整性判断 | 历史索引延迟属于平台约束，不能宣称实时全收 |
| 实时事件 | event +listen-im / consume、官方 Stream | 重连、限定订阅、事件到任务的持久消费及补全 | 目前仅可选事件提示唤醒历史；完整业务事件尚未验收 |
| 文本、图片、文件、引用 | chat +messages-send / reply | 稳定回复目标、持久发送键、丢失回包对账 | 用户身份与 bot 身份分别验收，未知结果不切后端重发 |
| 下载、资源读取 | chat +messages-mget --download-resources 等 | 有序 parts/引用、缓存哈希、任务输入隔离、失败重试 | 图片/文件内容解析由 Agent/工具做，不能只给路径就称理解通过 |
| 流式文本卡片 | chat +messages-send-card / update-card | 绑定任务与 bizId、限频更新、结果校验 | 本轮官方 API 接受创建/更新；无独立内容验证，尚未接进 gateway |
| 交互表单与审批卡 | 官方 Connector / A2UI 相关入口 | 在所选身份下绑定授权人、请求、有效期和执行 | streaming text helper 不支持 action callback，不能冒充审批完成 |
| 文档、表格、日历、待办、邮件、钉盘、会议纪要 | DWS 对应产品 shortcuts / 原子命令 | 向 Agent 提供所需官方能力及资源/动作边界、审计 | 已有代表性手工编排实测；全套办公尚未接成 Kimi 受控工具 |
| DWS 未封装的开放平台能力 | 核实后选择 OpenAPI/官方 SDK；DWS api 可作为原始调用入口 | 最小适配、身份与权限验证 | 原始 API 不是任意权限代理，不因缺 shortcut 就立刻写 AX |
| 机器人接本地 Agent | dws dev connect；或官方 OpenClaw Connector | 仅补实际不满足的 runtime/部署需求 | bot 路线应优先评估官方接入，不另造同类全栈 |
| 普通账号接本机 Kimi | DWS 用户消息 + 本项目 gateway | 显式触发、持久任务、精确 session、取消、产物与恢复 | 指定veil→liev群/私聊UI通过；非OS沙箱，不开放任意成员 |
| 桌面操作缺口 | 官方能力核实失败后才考虑 AX | 只针对有证据的具体缺口 | 本项目尚无 AX backend，不能说原生音视频已有兜底 |

Help 决定当前二进制接受的命令和参数，schema 补充效果/风险/幂等契约；两者不证明账号权限。业务结果仍需实测。DWS 中的 MCP 服务发现和 `mcp` 命令也不等于本项目已经交付了一个通用 MCP server。[DWS 固定版说明](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/README_zh.md)

本轮保存了 [本机命令核对](../evidence/2026-11-11/official-contract-audit/index.json) 与 [来源版本和摘要](../evidence/2026-11-11/official-boundary-sources.json)。核查中 `event subscribe --help` 被当前 CLI 拒绝；实际入口为 `event consume` / `event +listen-im`，不凭命令名称猜接口。

## 自研与官方重叠部分的取舍

官方 dev connect 已有一部分相同的 session、白名单和进程管理能力；我们这部分实现是普通账号路线的宿主编排，不是钉钉缺少这些通用功能。若以后选择机器人身份，先验证官方入口的覆盖与故障恢复，能满足就直接复用。

DWS 已负责实际外部调用及其回执；本项目账本保留的是跨进程重启、重复事件、HTTP 回包丢失和 Agent 工具执行状态。两者责任不同：发送成功不代表任务成功；任务成功也不代表文件已投递。未知发送不能重复提交，运行中的工具任务重启后也不能自动重做。

当前办公接入应继续复用官方产品命令/skills，而非自写文档、日程、邮件 REST 客户端。后续所需自研是选定账号与资源、动作授权、结果回读和任务关联；不再把整套 DWS 业务接口复制进 bridge HTTP。

## 本轮验收结果

当前73项本地自动测试全部通过（首阶段71项＋新部署基线2项），逐项结果见 [回归台账](../evidence/2026-11-11/scenario-regression.json)。新增 6 个单人群现场场景：执行中状态、真实取消、取消控制、XLSX 双文件交付、新会话、图片理解；12 条 Agent 回复均 confirmed。两份回传文件下载摘要一致；图片实际调用 ReadMediaFile 与 Bash，内容及320×180尺寸与原图相符；new前后原生session不同。详见 [现场证据](../evidence/2026-11-11/agent-scenarios.json)。

最新代码重启后，8条任务、17条投递、原生会话与执行日志再次逐项比较一致，见[重启复核](../evidence/2026-11-11/agent-scenario-restart.json)。

单账号阶段历史快照：总账本44条事件、8条任务/控制记录（7完成、1取消）、17条Agent回复已确认。官方卡片另计一次创建/一次更新，结论仅为 [API接受但内容未独立验证](../evidence/2026-11-11/official-card-acceptance.json)。

## UI验收口径纠正

本页前阶段的Agent场景主要从DWS/API发起、由服务端历史与日志验收，不能等同于客户端完整验收。用户纠偏后新增真实UI输入、回复可见、下载打开文件验证，单账号阶段见[docs/26](26-ui-acceptance-and-sender-identity.md)，最新双账号见[docs/27](27-two-account-ui-acceptance.md)。当前veil客户端输入、liev真人身份回复，原群与独立私聊均已部署并通过UI，仍无bot。

## 场景覆盖台账

下表旧`单人群现场通过`仅指当时单人群或本人合成资源；新增`双账号UI`指docs/27的veil客户端与liev独立对端；`自动测试`含模拟平台回执，不能替代独立对端；`进程测试`运行真实子进程但使用合成模型事件；`契约核对`没有实际业务操作。

| 场景 | 验证层级与结果 | 证据/测试定位 |
|---|---|---|
| 文字发送、历史分页、同 ID 去重 | 现场通过 + 自动测试 | docs/14、16、20；test_core |
| TXT/PNG/PDF/ZIP/WAV/MP4/DOCX/XLSX 原件 | 现场下载摘要通过 | docs/20；音视频在这里是文件 |
| 多图内联及引用文件 | 现场 API/原件/本机客户端通过 | docs/20；test_routing_consumer |
| 多账号、同 ID 跨会话、DM 参数 | 自动测试通过；本轮指定两账号群/私聊UI通过 | test_multiroute_identity_and_idempotency_isolation |
| 未授权 sender、普通本人消息、回复回声 | 自动测试通过 | test_owner_commands_and_echo_filter |
| 未授权及自身回复附件不下载 | 自动测试通过 | test_unauthorized_and_echo_attachments_are_not_downloaded |
| 缺 sender、未知资源、跨会话引用 | 自动测试拒绝/隔离 | test_core；test_unknown_media_and_cross_scope_quote_fail_closed |
| 已接收任务与实际工具执行 | 单人群现场通过 | local-agent-loop；agent-scenarios |
| TXT 输入、生成文件、回传下载校验 | 单人群现场通过 | local-agent-loop |
| XLSX 真解析、两个文件回传 | 单人群现场通过 | agent-scenarios：A1 文本、B1 数值1、总和1 |
| 图片查看与尺寸读取 | 单人群现场通过，实际图像工具及像素检查 | agent-scenarios；识别文字与原图一致，320×180 |
| 原生 session 多轮记忆 | 单人群现场通过 | 两轮同 ID，第二轮无工具仍记住代号 |
| new 清空绑定、另开工作区 | 自动测试及单人群现场 | test_reset_session_does_not_mix_previous_context；agent-scenarios |
| 群与私聊原生上下文隔离 | 自动测试＋双账号UI通过 | test_direct_task_and_group_have_separate_native_sessions |
| 执行中 status / cancel | 自动测试及单人群现场通过 | 真实 sleep 任务取消，计划中的末尾文件未产生 |
| 附件失败、恢复与原件篡改 | 自动测试通过 | test_media_failure_recovery_does_not_lose_cursor |
| 附件卡住时控制指令仍可用 | 自动测试通过 | test_stalled_download_does_not_block_status_or_cancel |
| 模型失败后队列继续 | 自动测试通过 | test_runtime_failure_does_not_block_next_job |
| 进程无终态、异常 JSON、过多产物 | 进程测试拒绝 | test_agent_runtime_process |
| 进程超时、取消、未退出、stdin 卡住 | 进程测试通过，子进程回收 | test_agent_runtime_process |
| JSONL 最后一行无换行 | 进程测试暴露后修复通过 | test_completed_terminal_without_final_newline |
| 文件越界、符号链接、缺失、超过20MiB | 自动测试拒绝 | test_agent_gateway；test_core |
| 消息已提交但 HTTP 回包丢失 | 自动测试通过，同 key 对账 | test_response_lost_keeps_same_key_and_payload |
| 投递未知、任务执行被中断 | 自动测试通过，不自动重发/重做 | test_unknown_delivery_is_reconciled_without_new_key；test_crashed_execution_is_not_replayed |
| 正常重启后重复消费 | 单人群现场及自动测试通过 | local-agent-loop；重启任务/日志/outbox比较 |
| 断线短停机、迟到索引、部分历史 | 短停机现场 + 故障自动测试 | docs/20；test_late_index_recovered_by_deep_scan |
| HTTP token、错误路由、进程单实例 | 自动测试通过 | test_stream_http；test_core；test_continuation |
| 官方流式卡片创建/更新 | API 接受，内容验证未通过 | official-card-acceptance；不可写成 UI 完整验收 |
| 文档/待办/日程/未发送草稿 | 本人代表操作现场通过 | docs/19；不代表全部办公或 Kimi 已能调用 |
| 官方 dev connect / OpenClaw Connector | 契约与 Help 核对；未现场启动 | 未创建机器人，不改变既有用户身份路线 |
| 指定两账号的私聊/群聊/CSV任务/3个TXT下载打开 | 双账号UI通过 | docs/27；5任务14投递、真实输入与可见liev回复 |
| 外部群/客户/原生对端播放 | 未验收 | 不以本轮内部两账号外推 |
| Codex 实际模型调用 | 两次超时，未通过 | local-runtime-preflight；合成 Codex 事件测试不改变此结论 |
| 原生语音条/视频、完整 Stream 业务事件 | 未通过 | v1.0.67 audio/video 映射文件；Stream ready 不等于业务送达 |
| 24/72h、令牌真实到期、压力与大规模积压 | 未完成 | 短时故障注入不能代替长周期现场 |

这些是明确列出的场景覆盖，不是“所有可能输入都验证过”。任何新能力应同时增加成功、权限/身份错误、部分失败、重试/重启和交付验证，失败或跳过不能计入通过。

## 本轮修复与复现

测试中也遇到macOS子进程退出与进程组信号竞争，补充先回收、再仅针对owned子进程处理的路径和故障注入测试。

运行时补读 EOF 前未换行的 JSON 事件；Codex stdin 改为可取消的非阻塞写入；Kimi 超大 prompt 提前拒绝并要求附件输入。附件下载改为单个后台只读请求，SQLite 状态仍由 intake 线程处理，避免慢下载阻塞控制消息；仅下载被授权任务所需附件。仍不宣称 Kimi 有 OS 沙箱。

```bash
python3 scripts/verify_scenarios.py
python3 scripts/agent_scenario_probe.py inspect
python3 scripts/accept_agent_scenarios.py
python3 scripts/verify_handoff.py
```

以上不向钉钉发送新消息。`agent_scenario_probe.py <case> --execute` 是显式写入探针，原始结果和请求指纹保存在 local/；禁止为了查看结果重发旧任务。不要给官方卡片创建伪造不存在的幂等参数：它由本地 intent 阻止重复提交，返回不明必须保留未知。

E018现场边界：官方普通账号text服务端拒绝超过5120 UTF-16单位（含前缀）；隔离v1.0.67官方Str读取参数还会TrimSpace。自研只补正确分段与调用前长度校验，不改官方鉴权或另造发消息API。新的长文两段确认与文件UI证据见docs/38；原首段拒绝/无taskId/unknown保留，不冒充已投递。

E019补充：官方错误的invalid_request+PARAM_ERROR可在首次发送阶段明确拒绝；已有taskId的查询错误仍属待对账。自研新增带原行/证据摘要的拒绝终态记录、原uuid绑定的官方日志显式导入和一次性用户提示；没有替代官方发送/鉴权，也不将网络超时自动判失败。真实UI和108回归见docs/39。
