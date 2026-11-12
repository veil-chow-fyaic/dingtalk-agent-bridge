# Agent 接入面：通道选型之后的扩展

E092，2026-11-12。本页只固定公开官方协议依据，不表示四种适配器已经实现。先采用现有 DWS 真人账号通道的成熟部分，再接 Agent；不能让本地 runtime 研究替代这一步。

| 执行器/宿主 | 公开官方接入面 | 需要归一的行为 | 本项目事实 |
|---|---|---|---|
| Codex | [App Server](https://learn.chatgpt.com/docs/app-server)：默认 stdio JSONL；initialize/initialized、thread/start/resume、turn/start/interrupt、turn/completed | 请求接收和 turn 终态分开；原生 thread 持久绑定；处理服务端请求/工具审批；按实际安装版本生成 schema 后核契约 | 现有 CLI 路径超时独立跟踪；没有实现新 App Server adapter。WebSocket 为实验且不受支持，不作为默认 |
| Pi | [固定版 RPC](https://github.com/earendil-works/pi/blob/ab74d46243e741e20077d244d30d2d673de40b5f/packages/coding-agent/docs/rpc.md)：`pi --mode rpc` | 自定义 JSONL，不是 ACP/JSON-RPC 2.0；prompt 的 started/queued/handled 不等于完成；需要等待 agent_settled，不能把 agent_end 当最终静止 | 尚未接入；保留原生 session、abort 和严格 LF 分帧语义 |
| Kimi Code | [固定版 ACP](https://github.com/MoonshotAI/kimi-code/blob/410814349d4677fc2844ad79069b0ad4a751303a/docs/en/reference/kimi-acp.md)：`kimi acp`，stdio JSON-RPC | 初始化协商、session/new/load/resume、prompt/cancel；权限请求与客户端文件/terminal 能力独立声明 | 既有 Kimi CLI 已有真实 Read/Write/Bash 和文件交付；ACP 是后续候选，未安装/升级替换 |
| OpenClaw | [Channel plugin SDK](https://github.com/openclaw/openclaw/blob/7b303779c41f9b67ba4291f646ce447e01fad868/docs/plugins/sdk-channel-plugins.md) 或独立 [Gateway 协议](https://github.com/openclaw/openclaw/blob/7b303779c41f9b67ba4291f646ce447e01fad868/docs/gateway/protocol.md) | 插件模式由 OpenClaw 持有 Agent turn/session，中间件提供 DWS 通道；独立 Gateway adapter 是另一种部署，不重复消费同一会话 | 尚未接入；不默认开放 OpenResponses HTTP，官方文档说明其全 operator/owner turn 权限语义需要另行映射 |

上表源码与文档的 commit、选中文件和 SHA256 见 [catalog](../references/catalog.json)。Codex 为带日期的官方网页快照，不能当作本机 binary 的 schema；Pi 仓库迁移后的实际地址为 `earendil-works/pi`。Kimi 旧 `kimi-cli` 仓库已归档，当前资料来自 `kimi-code`，不据此自动升级已验证的执行器。

中间件统一的是会话绑定、任务输入、进度、终态、取消和产物；原生协议保留在各 adapter 内。附件先保存原件和摘要，再按实际能力传图片、文本资源或可访问路径。Kimi 本次固定 ACP 声明支持图片、不支持音频提示，并会丢弃嵌入 blob 资源，不能把“有 ACP”推断成任意二进制都能读。

今后每个 adapter 的完成判据包括：同会话续接、并发隔离、接受后失败、取消/超时、重启后的原生 session 保持、附件读写及原会话交付。上游文档和现有 Kimi 通过项都不能代替另一个 adapter 的真实验证。

E097新增[CEO runtime契约/会话兼容性采用方案](../references/ceo-deep-dive.md)，帮助归一能力、终态与失败；本页四接口的研究状态不变。先保持Kimi已验路径、诊断Codex，再按共同契约逐个适配；不能照搬CEO自动failover或业务审核政策。
