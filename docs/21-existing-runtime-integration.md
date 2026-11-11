# 通用工具边界与参考实现

2026-11-11，按用户最新澄清修正：**本项目交付通用 IM bridge，并接入本机 Kimi/Codex 完成真实任务；不要求用户另选 runtime 才能继续开发。**任何 Agent/程序可以通过 CLI 或 HTTP 使用其消息、附件与投递能力。当前指定组织和单人群仅是现场测试范围。

## 已撤销的错误前提

此前把“核实团队实际运行的 runtime、再做挂接”列为必过关卡，是错误的范围收窄，现从计划、需求和总状态中移除。没有安装某个 OpenClaw 扩展不阻塞本工具。另一个项目的 Bot-only 产品约束只约束那个项目，不限制本项目的普通账号能力。

组织/profile 是 DWS 的认证与路由上下文；会话通过稳定ID定位；它们不等于产品必须绑定某个组织，也不需要在代码中写公司名。多账号、多会话是工具路由能力。账号登录/平台资源授权仍由钉钉本身决定，不能通过通用接口消除真实平台权限。

## 本地参考资料及采用方式

| 项目 | 固定本地版本 | 采用方式 |
|---|---|---|
| `/Users/veil/Projects/wecom-bridge` | `1ee7f8ca34b544495cd6770343bdb5177baef453` | 参考HTTP发送、WebSocket事件、组织/会话定位、投递账本、媒体和恢复。组织字段用于路由，不是某个组织专属产品 |
| `/Users/veil/Projects/wecom-agent-gateway` | `8f7e2416a28720d3884f2a3b7a5336b7a51aadb7` | 参考中立消息模型、parts、引用和能力声明；不修改其Bot-only策略，也不将它的部署列为本工具前置 |
| `/Users/veil/Projects/agent-facade` | 本轮只读README/runtime接口 | 该仓库说明验证runtime已停止/项目暂停；不唤醒或修改它，不以其可用性判定本工具完成 |

本项目保持独立，不要求接入者采用OpenClaw、Codex、某模型或业务框架。当前提供HTTP游标消费与CLI，未宣称与WeCom WebSocket线协议完全兼容；需要该兼容性时独立扩展。

## 已实现的中立接入能力

- 账号＋会话路由：`Hub`管理多个group/direct worker，DWS profile仅留在内部配置；每路独立消息游标、附件、发送幂等账本。
- CLI与HTTP：列会话、事件、文本/文件/图片发送、查询投递、对账、附件下载/修复；[完整使用说明](22-generic-tool-and-consumer.md)。
- 持久收件箱：事件及游标同事务提交；按消费者独立持久化；下载失败保留pending/failed，后续可恢复。
- 中立消息模型：有序text/image/file parts、结构化quote、原件路径/大小/SHA256；不将引用附件重复放入正文。
- 保守消费：本人和未知sender不生成可触发项；无法解释的资源不当成纯文本完整消息；不把raw CLI对象直接交给模型。

上述传输和通用consumer本身不运行模型。新增独立agent_gateway已使用本机Kimi执行授权任务并回传，任务、会话与投递单独持久化；allowSelfCommands只允许已核验本人的显式/agent指令，不关闭通用consumer的本人过滤。真实接入见[docs/24](24-local-agent-product-and-acceptance.md)。

## 通用consumer阶段验收与当前接入

接入runtime之前，18条既有真实合成消息只读消费通过，2条引用、13个媒体部件，12条有媒体的消息完成下载校验；18条全部被self过滤，readyForRuntime=0。重启consumer再读fetched=0，消息总数不变。两个账号/三个会话含DM的路由、参数与幂等隔离有确定性测试；这不冒充多个真实账号现场验收。

当前已增加两轮Kimi实际任务、5条confirmed回复，完整账本25条；51项回归通过。Codex adapter保留但请求超时，不称实测可用。公共契约和可替换runtime是通用性要求；真实执行闭环同样属于用户最新明确的交付要求。
