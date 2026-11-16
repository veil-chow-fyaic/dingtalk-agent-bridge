# Agent接入面与验证范围

E132（2026-11-16）按本项目实现及已有证据更新。协议研究、适配器实现、部署和真实用户闭环分别计证；原R09至少一个本地执行器已满足，不增加四类全部通过门槛。版本/现场现状统一见[总览](../102-user-requirements-and-roadmap.md)。

| 运行器 | 本项目实际路径 | 已验证的范围 | 当前边界 |
|---|---|---|---|
| Kimi Code | CLI stream-json，原生session；工作区文件输入 | 历史Read/Write/Bash、群/私聊文件交付、续接/控制样本；E115/E116持久网络环境和两路UI | AIC保持Kimi；E131 2.1.1返回订阅服务访问403，只有版本事件，无工具/结果；E133用户授权最小请求仍同类403、无周限额明确信息，需既有访问恢复证据；不阻塞IM通道 |
| Codex | exec/resume、JSON事件和结构化结果；原生SIGINT→turn/interrupt | E119修复取消，E120真实Python/续接/取消/下载UI；旧E118迟到写入失败保留 | 旧私聊原生new归档后已迁Pi；未实现独立App Server adapter，旧超时不再被写成当前“尚不可用” |
| Pi | 0.84.2 / 914cf147，JSON print模式；完整UUID/独立session目录 | E122契约/396×3，E123真实Python、续接、取消/文件UI | 已部署原私聊；关闭扩展/skills/prompt templates/themes自动发现；image_files未声明 |
| OpenClaw | 2026.11.3 / 41f2b981，agent --local、stdin、完整UUID预入账、整对象JSON | E127薄适配/423×3及完整CLI合成6样本18检查；E128父进程死亡/gateway恢复/new两turn25检查及新增3专项×3 | 候选500191a未部署，真实模型/DWS/UI未验；image_files未声明；不是ACP或远端Gateway适配 |

## 共同契约与各自终态

本项目统一能力、session兼容性、任务输入、终态、取消和产物，原生协议留在[agent_runtime.py](../../dingtalk_bridge/agent_runtime.py)与[openclaw_runtime.py](../../dingtalk_bridge/openclaw_runtime.py)。收到响应、退出0、模型自述完成均不能单独判成功。

Pi要求agent_settled、最后assistant stopReason=stop及exit0，agent_end可能之后重试，不能提前交付。OpenClaw要求完整JSON、匹配session、明确stop、exit0、无error/timeout或未解决工具失败；length不是完整，replayInvalid可标记成功副作用，不能单独判失败。合成null被provider规范化为stop时，不能还原未暴露字段。

原生会话绑定runtime契约；变更先new归档、零未决、显式binding迁移，不能仅换kind/模型后把旧session交给另一CLI。取消/超时/父死亡清理按运行器原生机制及有界守护处理，不保证恶意脱组或外部效果回滚。详见[运行手册](../15-service-runbook.md)。

## OpenClaw配置和归属

E127使用外置不可变专用JSON路径/SHA和agent main绑定，三个workspace占位定位本代目录；独立home/state/cache/profile、最小环境、禁插件/ACP/任意层include/宿主env覆盖。bridge网络白名单先应用，再筛最小环境；不会复制既有runtime凭据。系统HOME同名profile存在时拒绝，未把保护钩子声称OS沙箱。

agent exec每次新UUID，不直接满足多轮；远端Gateway turn不随本地CLI退出自动停止。当前采用local唯一宿主，不能同时启动另一个通道插件消费同一路消息。未来若走插件/Gateway，须单独设计turn归属和远端取消，不把本轮local合成证据外推过去。

## 研究来源与历史范围

E092的[固定catalog](../references/catalog.json)保留当时Codex App Server、Pi RPC、Kimi ACP、OpenClaw plugin/Gateway候选资料；它不是当前实际采用协议列表。Pi后来采用JSON print，OpenClaw后来采用local；Kimi仍为CLI，没有把ACP研究当已接入。

固定来源与验证分别见[Pi契约](../123-pi-runtime-contract.md)、[Pi UI](../124-pi-deployment-and-ui.md)、[OpenClaw入口研究](../126-openclaw-turn-entry-contract.md)、[薄适配](../128-openclaw-adapter.md)、[生命周期](../129-openclaw-gateway-lifecycle.md)。参考源码/测试存在不等于上游测试通过；E128没有重跑423全量，不称426×3。真实provider/UI及图片能力按各自证据声明。
