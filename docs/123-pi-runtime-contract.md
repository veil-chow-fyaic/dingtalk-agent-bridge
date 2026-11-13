# Pi 原生执行器契约 E122

Pi复用现有任务、session、outbox、工作区、文件交付和取消机制。DWS继续使用显式profile真人身份；执行器切换不引入新钉钉bot，不改群或组织权限。AIC保持Kimi，原私聊从Codex通过显式new和binding迁移进入Pi；E122提交时服务停机待补读和新UI，不把本地运行算作钉钉验收。

## 固定官方依据

本机官方包`@earendil-works/pi-coding-agent`版本0.84.2，源码固定[914cf147](https://github.com/earendil-works/pi/tree/914cf1472e715297caa30db4b9535d534a9eb718)，MIT。只借用官方协议和生命周期，不复制整个业务宿主、不安装升级执行器。

- [JSON事件协议](https://github.com/earendil-works/pi/blob/914cf1472e715297caa30db4b9535d534a9eb718/packages/coding-agent/docs/json.md)：session头、assistant message_end、agent_end、agent_settled各有含义。agent_end可能后接重试，不能直接交付。
- [print模式](https://github.com/earendil-works/pi/blob/914cf1472e715297caa30db4b9535d534a9eb718/packages/coding-agent/src/modes/print-mode.ts)及[自有shell工具清理](https://github.com/earendil-works/pi/blob/914cf1472e715297caa30db4b9535d534a9eb718/packages/coding-agent/src/utils/shell.ts)：SIGTERM有自身工具清理。沿既有guard有界终止，不把Codex专属SIGINT开关套到Pi。
- 安装版本的agent_settled没有新版文档中的aborted字段。依据实际版本要求最后assistant stopReason为stop；若未来事件携带aborted则只接受false。不能把main文档字段强加给旧版本。

## 适配与边界

命令使用`--mode json --print --session-dir`，原生会话放当前gateway工作区的`.pi-sessions`，只接受完整规范UUID续接。禁用自动发现extensions、skills、prompt templates和themes；不修改HOME、凭据或默认模型。持久网络环境仍由通用runtime.environment配置。

只有session一致、最终agent_settled、最后assistant stopReason=stop、合法text/files JSON和进程exit0全部满足才交付。拒绝错误/取消/length/toolUse、缺终态、重复session、终态后新turn、无效协议和非零退出。工具输出不能伪装成assistant最终结果。事件按LF解析，文本内Unicode分隔符不拆坏JSON。

配置可使用`{"kind":"pi","binary":"/absolute/path/to/pi","timeoutSeconds":60}`。首次安装和授权由已有运行器环境负责；bridge不自动登录。原gateway已经有会话时，先原生`/agent new`归档，确认零未终态任务/回执，停gateway，再使用`migrate_agent_runtime_binding.py`审查及应用；不得只改kind硬绕绑定。回切也执行同样过程，不把Pi UUID交给Codex。

当前声明文字、普通工作区文件、工具、续接、取消和结构化结果。**图片能力暂未声明**：含图片参数的任务明确拒绝，不把模型支持猜成适配层验收。OpenClaw尚未接入。四种执行器全过不是新增原PRD门槛，Kimi和Codex既有真实验收保持。

## 验证与失败保留

22新增方法含原生工具清理、取消/超时/父进程死亡、协议反例及只读配置检查；最终冻结源码和同wheel的Python3.14、3.11各396通过，21模块、171份测试/工具/素材字节、六入口和许可一致。最初三套396各有一个旧Codexfixture失败：1秒冷启动可能先于合成handler安装；旧产品也复现，原日志保持。修为handler和工具ready后只对宿主测试时钟模拟到期，原清理断言和生产期限不变。

实际Pi三轮使用同一session：Read/Write产生469和480文件；前两轮没有执行要求的Python，因此只计文件工具和续接。第三轮实际bash/Python计划30秒后写late，开始后取消；延迟230秒复核4个自有运行器/工具进程均退出且没有late。真实本地三轮发生在最终畸形消息分类与图片metadata收紧之前，不能冒称最终冻结版UI；最终版另做部署验收。这也不是OS沙箱或任意脱组进程保证。

[脱敏冻结核验](../evidence/2026-11-13/pi-runtime-validation.json)。原始source、日志、进程、配置和六库备份仅local/pi-adapter-20261113。原24h观察记录本次维护，不重置；Keychain系统根因和自然续期未证，49/14/1及7 MUST缺口不变。

## 剩余消息入口复核

本次读取DWS v1.0.68 release及main固定[c4be030e的chat文档](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/c4be030ea0470457faea167760613372d761fc5c/skills/mono/references/products/chat.md)，没有找到能替代既有结论的新原生语音/video、引用或单消息多附件入口。audio/video仍走file别名；文本加本地文件是两个消息。最新applicationToken第三方事件发送不等于IM媒体接口。没有为无新入口重复旧发送探针，未升级DWS；这不证明社区所有项目均不存在相关实现。
