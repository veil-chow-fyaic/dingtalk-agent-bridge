# OpenClaw 官方入口与终态契约 E125

2026-11-15固定官方 [openclaw/openclaw@41f2b981](https://github.com/openclaw/openclaw/tree/41f2b981d240cab9e55b07cba991282a795317b5)，17份官方文档/源码/测试文件留在local，[逐文件摘要](references/openclaw-turn-contract.json)可复核。只运行无依赖的结果分类函数，没有安装或启动OpenClaw、模型、Gateway、认证或插件。当前PATH未找到OpenClaw。现有bridge产品和Kimi/Pi绑定不变，OpenClaw支持仍未声明。

## 入口选择

| 官方入口 | turn及状态归属 | 与bridge要求的关系 |
|---|---|---|
| `agent exec --json` | 命令持有一次embedded执行及清理；保留state目录要求独占。`agent-exec.ts:93`每次 `randomUUID()`，opts无resume/session选择器 | 适合独立一次任务，**保留目录不等于续接会话**。不能直接作为现有gateway的持久session适配器 |
| `agent --local --session-id … --json` | 显式embedded执行；`runWithLocalStateOwner`拒绝外部所有者，全turn持锁；支持明确session选择 | 当前优先候选，但需固定私有state/config、原生JSON/退出、会话续接和取消清理实证后才能接入 |
| `agent` 默认Gateway模式 | OpenClaw Gateway持有turn，CLI只是客户端；信号会尝试按已接收runId执行chat.abort | CLI退出不证明远端工具已停。通信丢失不自动回退local或再执行；不能套用仅杀本地子进程的适配方式 |
| `/v1/responses` | OpenClaw Gateway执行，endpoint默认关闭，须明确配置与operator认证；显式session或response续接 | 属于另一宿主协议，需单独确认取消/断连/会话映射；不能把它当成本地CLI等价入口 |

依据：[CLI文档](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/docs/cli/agent.md)、[exec实现](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/src/commands/agent-exec.ts)、[Gateway/local分派](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/src/commands/agent-via-gateway.ts)、[HTTP文档](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/docs/gateway/openresponses-http-api.md)。桥接输出仍应只由bridge发送，不能开启OpenClaw `--deliver`形成第二发送方。

## 终态不能只看一段文本

`agent exec`有 `ok/status/final/payloads/sessionId` JSON及退出码；成功0、失败1、超时2。清理失败可把原成功改为错误，信号另走130/143。其默认读取配置、已有登录和插件，`--auth-env-only`才跳过配置和存储凭据，但该模式不能与config/override混用。这里是固定源码说明，未读取真实凭据，也不采用默认凭据继承来做探针。

`agent --local`与exec的JSON不能混用解析器。前者内存终态通过 `Symbol.for("openclaw.agentRunTerminalOutcome")` 携带，CLI把它映射为退出码；Symbol不进入JSON。还须验证结果meta、错误payload、真实清理和退出，不能要求不存在的exec顶层status，或只因拿到文本就成功。参见[终态载体](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/src/channels/turn/agent-run-terminal-outcome.ts)及[最终处理](https://github.com/openclaw/openclaw/blob/41f2b981d240cab9e55b07cba991282a795317b5/src/agents/command/post-run.ts)。

## 本轮实际执行的验证

[可复现工具](../scripts/probe_openclaw_result_contract.mjs)先核固定文件SHA再import原始 `agent-exec-result.ts`。使用Node v26.3.1原生TypeScript支持，只执行 `classifyAgentExecResult`；不加载完整CLI或provider。

14检查通过：正常结果、剔除reasoning/commentary、可见文本回退、错误payload及投影、aborted、meta.error、error stopReason、fallback耗尽、timeout两种来源、incomplete_turn错误保留及缺失用量不补造。空文件和修改源码两个负例均在import前被拒绝。

另记录两个边界事实：给这个内部函数只有 `stopReason=length`而无上游meta.error，或完全没有stopReason，它仍分类ok。这说明**该函数单独不能作为可信完成证明**。完整上游调用链会提供额外终态/不完整错误，本轮没有运行整个CLI，不能据此断言真实CLI一定把截断当成功。没有把函数通过当作会话/取消/工具或UI通过。见[脱敏执行证据](../evidence/2026-11-15/openclaw-entry-contract-validation.json)。

复现需提供与摘要匹配的本地官方文件，命令不会联网下载或启动OpenClaw：

```sh
node scripts/probe_openclaw_result_contract.mjs /path/to/fixed/src/commands/agent-exec-result.ts
```

下一步沿 `agent --local` 查明配置隔离、完整JSON与session持久化接缝，再用无凭据/合成provider验证官方完整入口的状态锁、输出和取消；未具备条件前不注册产品runtime、不迁移现有聊天、不读取或复制其他CLI登录数据。四runtime全过仍不是原R09新增门槛。E124原观察和Qwen强杀证明保持，不重复运行。最终49/14/1及7 MUST缺口不变。
