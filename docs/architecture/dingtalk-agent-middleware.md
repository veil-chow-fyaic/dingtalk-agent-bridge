# 钉钉 ↔ 主流 Agent 中间件

状态：E092设计，E097核对当前实现及[统一需求/路线](../102-user-requirements-and-roadmap.md)。优先采用GitHub社区/钉钉官方作业，默认DWS真人账号。CEO现为任务/交付/runtime契约优先参照，Qwen为DWS通道组件参照，不表示新增适配器已实现。

## 身份决策

默认消息主体是 **DWS 显式 profile 授权的真人账号**。Agent 是执行器，不能把 runtime 的名称、模型选择或机器人 appId 变成发言身份。当前测试的 liev/veil 仅为配置实例，产品不绑定人名或组织。

bot/数字员工不是自动替代或故障回退。DWS 失败不自动切 bot、AX 或另一账号发送。普通账号的操作依然受官方开放能力、组织授权、会话成员关系和资源权限共同限制；“真人在客户端可见”不等于 DWS 已开放同一 API。

对每个具体身份/会话分别记录：发现会话、历史、事件、文字发送、引用、文件上传/下载、原生媒体、办公资源。内部群、外部群、含外部成员群、跨组织私聊不能混为一个通过项。

[官方仓库 #937](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/937)截至本轮仍 open：原报告存在外部群历史可读而个人事件失败的对照；后续评论群类型未核实，不能泛化为所有当前外部群都失败或已修复。只有某目标历史确实可读时，才可选 history 补读；不得伪称它是实时 Stream。跨组织/客户场景继续按原矩阵待验，不套用企业微信、Slack、Telegram 或飞书的权限结论。

## 分层与现有代码位置

```mermaid
flowchart LR
  H[钉钉真人账号会话] <--> D[官方 DWS]
  D <--> T[通道适配：事件 / 历史 / 资源 / 回执]
  T <--> C[中间件：路由 / 会话 / 任务 / 交付账本]
  C <--> A[可替换 Agent adapter]
  A <--> R[Codex / OpenClaw / Pi / Kimi Code]
```

| 层 | 当前文件 | 复用来源/边界 |
|---|---|---|
| 官方调用和暂停 | `dws_access.py`、`official_proxy.py` | 官方 DWS；不复制认证、token 或 OAuth 状态机 |
| 收发与路由 | `core.py`、`stream.py`、`routing.py` | 优先对照 Qwen DWS client/stream；保留已验的固定身份、持久续页及未知发送对账 |
| 中立消息和原件 | `message_model.py`、`consumer.py` | 有序 parts、quote、sender、原件路径/大小/SHA；不能因参考实现只接 text 就丢附件 |
| 会话/任务/交付 | `agent_gateway.py`、既有 SQLite 账本 | Qwen 队列/会话、CEO 文件回执与恢复设计；保持既有任务和终态 |
| 本地执行 | `agent_runtime.py`、`runtime_guard.py` | 当前仅 Codex/Kimi CLI；后续按各官方协议隔离，不把协议字段放进 DWS 层 |
| 对外工具面 | CLI、HTTP、`consume.py` | 任意宿主可独立消费；不要求安装某一个 Agent 框架 |

以上是现有模块映射，不为整理目录搬动产品文件、数据库或运行配置。短期保持当前 Python 传输/账本，通过窄接缝引入采用的组件；没有依赖/测试收益依据时不整体改写语言或 fork 一个大型宿主。

## 必须统一的语义

- 身份键与会话键分离：固定 DWS profile/账号、conversation、可选 thread；runtime session 另存绑定，不能用昵称或默认登录账号猜目标。
- 单一执行归属：同一路消息只由一个任务宿主运行。独立中间件可拥有任务；OpenClaw 原生插件模式由 OpenClaw 拥有 Agent turn，中间件只提供通道。两者不能同时消费同一路而重复执行。
- 收消息、触发任务分离：群普通消息可收，但只按明确策略触发；自消息过滤不通过屏蔽整段历史实现。
- 任务完成与投递完成分离：模型声明“已发送”不是回执；submitted、confirmed、outcome_unknown、rejected/failed 保持可区分。只在原 key/原任务上对账。
- 文件是原件交付：明确输入能力、物化路径、摘要和保留时间；发送前固定字节，输出由宿主校验并回原会话。图片/文件与语音条/独立视频类型分开。
- 能力按证据声明：支持文字不推断支持任意附件；不支持的能力显式报告，不能用文件名占位假装模型已读。
- 通道权限与 Agent 工具权限分离：DWS 真人账号有权限，不等于聊天中的任意人能调用该账号全部办公能力。触发白名单和受管工具入口继续有效。

## 当前部署与后续接缝

E095用户自行新终端登录成功后，已部署E093/661b67c的21模块并恢复三个受管服务，双路history-only15秒；E096新AIC群原生PNG已验。仅新AIC测试群及原两人私聊，企业大群/旧群禁测；自动心跳仍PAUSED。E097只审资料，不新增现场健康或发送证据。认证已恢复不等于根因根治或跨设备长期保证；助手auth/doctor/系统Keychain操作仍禁止。

通用目标不等于本轮已实现四个可用 adapter。当前 Kimi 有真实闭环，Codex CLI超时未解决，Pi/OpenClaw 尚未接入。原“至少一个本地执行器”门槛保持；四类适配属于后续扩展路线，不能用研究完成冒充运行完成。

下一代码接缝见[CEO C02–C06](../references/ceo-deep-dive.md)：发送事实负例、轻量runtime终态/能力/错误协议、会话兼容性。现有consumer独占flock和gateway绑定有效，未来租约按多宿主实际需求引入，不为模仿上游重复实现。所有adapter仍共用同一通道和交付账本。
