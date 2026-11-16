# 采用与改造清单

E092建立；E132于2026-11-16同步实际采用状态，来源索引/许可证及原实验不改。先看公开DWS真人账号项目，再决定复用；本地旧项目不作为选型优先来源。E093已采用[CEO文件摘要校验](artifact-digest-adoption.md)，保留MIT及回归，E095已经部署，E095/E096有真实UI交付。CEO C02/C03/C04随后已实现，E109部署、E112真实续接和文件UI通过；C06环境由E115/E116完成，Qwen事务映射由E124完成；未列已采用的条目仍为候选，不表示已经移植。最新[CEO深挖](ceo-deep-dive.md)固定新版31份资料，旧采用版本不变。

| 工作项 | 优先取材位置 | 本项目接缝 | 采用前必须核对 |
|---|---|---|---|
| DWS 消息与引用、固定 profile | Qwen `packages/channels/dws/src/dws-client.ts` 及测试 | `core.py` / `message_model.py` | 固定官方参数树；群/私聊 ID 域；保留 typed quote 与原件，不只传正文 |
| 事件生命周期、接收启停与自消息过滤 | Qwen `dws-event-stream.ts`、`dws-channel.ts`、相关测试 | `stream.py` / `routing.py` | 共享 bus 归属、禁用范围与晚事件；不照搬更广的全群订阅 |
| 补读和重复触发 | Qwen history/cursor；CEO `dws_client.py` 与消息路由说明 | `core.py` 的持久窗口/opaque token、consumer | 比较既有1001/5000积压、断点和late history测试；不倒退为每轮从第一页或仅固定24h |
| 文件发送与读回 | CEO `app/dingtalk_file_delivery.py`、`tests/test_dingtalk_file_delivery.py` | `agent_gateway.py` 的输出冻结、outbox、reconcile | 文件名/摘要/目标/generation一致；保存原生回执后再读回；重启不能重新上传 |
| 发送事实 | CEO `app/dingtalk_send_evidence.py`、对应测试；OpenClaw Slack `send.reconcile.test.ts` | 既有投递状态/错误反馈 | 模型自己写的 messageId 不作为发送证明；不能复用业务专用旁路或普通失败自动换generation规则 |
| 合并消息后的去重 | OpenClaw Telegram `message-dispatch-dedupe.ts` | consumer 的逻辑消息身份 | 接收事件去重与任务去重分层；key带账号/会话/消息，不以正文去重 |
| 持久会话/线程 | Qwen 会话策略；OpenClaw Telegram `thread-bindings-persistence.ts` | gateway session绑定 | 不照搬读取失败返回空绑定的降级；现有session不能静默丢失或自动换新 |
| 执行器能力/错误/终态 | CEO `agent_runtime_contracts.py`、`codex_runtime_adapter.py`及测试 | `agent_runtime.py`薄适配器 | 静态能力与实际健康/验收分开；工具429不当provider错误，不自动切账号或重放任务 |
| 会话兼容性/归属 | CEO consumer契约指纹与session lease、对应测试 | gateway binding、consumer独占锁 | 已有flock不能漏报；契约变化不静默丢session，租约仅在多宿主确有需求时增加 |
| 私聊代答交互 | `dsh-dingtalk-self` 的 DWS/pipeline/attachments | 后续用户体验层 | 不采用删除代码/截断任务结果、读取其他宿主凭据、忙时自动新session的策略；其关闭原生AI角标也不照搬 |

## 不整包搬入的具体原因

Qwen 与宿主 `@qwen-code/channel-base`、配对/调度/状态存储耦合；发送主体是合适的真人账号，但输出长文截断、满队列丢弃和checkpoint失败后继续发送不符合本项目既有标准。先提取独立 DWS 子模块或按相同契约移植，不能把整套 Qwen runtime 当中间件依赖。

CEO不仅有DWS文件/回执，还有发送事实校验、runtime契约、会话兼容性和归属测试；现提升为这些领域的优先参照。但整套服务包含办公业务、管理者画像、A/B审核和登录协调。只采用小范围通用机制，不能用其认证恢复、业务重试或进程清理覆盖本项目已验边界。具体可取和不可取见[逐项源码判断](ceo-deep-dive.md)。

`dsh-superagent-dws` 自述真实事件负载和单聊回复仍待验证；全群订阅、自动安装DWS/登录不是当前默认。`dws-message-cache` 聚焦只读采集；其设计可借鉴，但不能承担发件箱/任务。两者未确认许可证，不导入产品代码。

钉钉官方 bot connector、soimy、Hermes 和 DWS dev connect 的身份路线不同；只能复用明确可拆出的格式、交互或宿主接口，不能让 bot 的权限范围悄悄收窄真人账号需求。

## 已完成与剩余采用工作

| 项 | 已完成 | 后续边界 |
|---|---|---|
| CEO C01–C04 | 摘要门槛、发送事实、runtime能力/终态、会话兼容性；E109/E112部署及UI | 不重做；旧C02假凭据/冲突/跨任务回执负例保留，未知不重发 |
| CEO C06 | E115/E116持久网络环境和安全DWS错误信封；E120 Codex及E123 Pi后来各自完成真实闭环 | 不把网络可达等同模型成功，不引入认证恢复/自动failover |
| Qwen admitted/completed | E124映射inbox/job/outbox既有事务；5真SIGKILL方法冻结源/原wheel双Python各通过 | 等价实现不重写，不采用满队列丢弃/落盘失败继续发送降级 |
| Pi | E122固定914cf147/0.84.2，E123真实文字/文件/续接/取消UI | 图片未声明 |
| OpenClaw | E125入口研究、E126完整合成宿主、E127薄适配、E128父进程死亡/gateway恢复/new | 代码随E134部署，未配置绑定/真实provider/UI；不是远端Gateway或插件模式的证明，不重复旧样本 |
| C05租约 | 当前已有consumer flock和gateway绑定 | 仅真实多宿主场景需要时增加，不为模仿上游重写 |

真正采用源码时固定commit、逐文件范围、依赖和许可证/NOTICE，保留本项目异常语义，按变更运行有意义的验证。源码或测试文件已阅读不等于测试已运行；合成provider不等于真实模型或用户UI。E097的31文件深挖是研究交付，E093实际导入范围另记。

现场/版本以[总览](../102-user-requirements-and-roadmap.md)为准：最后部署2467fe2/E134，最近真实UI E131，OpenClaw 500191a代码随包部署但未配置绑定/真实模型验收。原E125“local待核”、旧E116“最近现场”、Codex“仍待验”的描述不再是当前指令。

官方取消候选E117仍未完整上游集成/部署/发布。剩余主线回到私聊入站引用、原生语音/video、单消息组合及R13可靠性；群模型当前需既有Kimi Code服务访问恢复证据。没有对应新证据不循环重跑，也不新增四runtime全过门槛。
