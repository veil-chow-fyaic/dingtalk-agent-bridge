# 采用与改造清单

E092建立，E113同步实际采用状态，2026-11-13。先看公开DWS真人账号项目，再决定复用；本地旧项目不作为选型优先来源。E093已采用[CEO文件摘要校验](artifact-digest-adoption.md)，保留MIT及回归，E095已经部署，E095/E096有真实UI交付。CEO C02/C03/C04随后已实现，E109部署、E112真实续接和文件UI通过；其他条目仍为对照候选，不表示已经移植。最新[CEO深挖](ceo-deep-dive.md)固定新版31份资料，旧采用版本不变。

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

## 下一次代码工作应交付什么

1. C01–C04已落地并由E112补真实UI，不再重做。下一项借CEO C06环境构造和错误分类，补本项目runtime持久启动环境及安全DWS错误信封；现实现已有同等或更强行为则保留。Qwen `DwsImDispatch` admitted/completed与入库事务对照继续作为通道专项，不先改造成大型宿主依赖。
2. 使用上游对应测试场景和本项目合成 fixture 验证语义。未知字段、身份切换、重复事件、分页断点、文件摘要改变、发送超时后重启均应覆盖；不得启动真实 DWS 来跑第三方测试。
3. 真正采用源码时保留许可证/版权/NOTICE，记录源 commit 和逐文件修改；只在本项目增加窄接口，不修改参考快照或本地旧项目。
4. 通道接口稳定后，再按[Agent接入图](../architecture/agent-integration-map.md)实现可替换适配器；各 adapter 共用中立场景，原生协议留在边界内。先有真实闭环再声明支持，不以命令能启动当接入完成。

E097只有可复用资料、源码对照与取舍整理，没有运行上游测试；“测试文件存在/已检查”与“本次测试通过”分开。现场最后已证为E112三服务恢复及真实任务/下载、仅新AIC群和原私聊；心跳PAUSED。所有原授权和认证事故禁止项继续有效。

E102落实CEO发送凭据负例及官方投影边界，见[回执契约](../106-send-evidence-contract.md)：8新方法、旧22失败，三环境307通过，core窄修复已在E103部署transport并真实群Python1387/UI通过。C03能力/终态与C04兼容性已由E104实现、E109部署、E112真实UI通过，下一接缝为启动环境及安全错误观察。
