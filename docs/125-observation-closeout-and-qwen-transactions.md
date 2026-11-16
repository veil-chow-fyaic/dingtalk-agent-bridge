# 原观察收尾与 Qwen 事务对照 E124

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-15：原 `aic-persistent-env-20261113` 已自然到期，记录完整性通过，但不满足连续健康结论。Qwen 接纳/完成语义已与现有 inbox、job、outbox 对照，并新增五个实际子进程 SIGKILL 边界验证；现有实现无需重写。产品21模块仍为 E122/e7d82cc，本轮没有重载服务、调用真实 DWS、发送消息或修改会话绑定。

## 原24小时观察的实际结果

窗口为北京时间2026-11-13 17:08:49至11-14 17:08:49，原run未重启、延长或重置。2879次采样、最大间隔30.315秒，13项完整性检查通过；完整时长只证明按约定完成采样。

| 观察事实 | 结果与限制 |
|---|---|
| 不可达 | 14次，分为18:04:21–18:06:51的6次、18:42:21–18:45:51的8次；这是采样时刻范围，不是精确故障持续时间 |
| 轮询错误 | 16个采样、24个路由错误记录；采样中的 `poll_error_detail` 均为空，不能从这些记录推导DNS/TCP/代理/认证根因 |
| 维护与版本 | 原9条维护保留，包括E118/E119混用、E120/E123首次启动失败及恢复；不能声称统一加载版本覆盖整个窗口。旧对账脚本窄字段口径计4条版本元数据，另2条有 `loadedCodeSha256`、1条有候选/恢复版本，不能把4当作实际仅4条有版本记录 |
| 捕获事件 | 新增32条，后续只读账本逐条保留，捕获序号范围精确一致，无重复或超出最后捕获序号的事件 |
| 六库保留 | 11月15日后续快照均SQLite integrity_check=ok。启动时88任务、216 outbox、227 transport deliveries、322 events、321 inbox行全部原字段保留；当下98任务、238 outbox、249 transport deliveries、354 events、353 inbox行 |
| 历史失败 | 当前任务84 completed、6 failed、5 cancelled、2 interrupted、1 blocked；outbox237 confirmed/1 rejected，transport248 confirmed/1 rejected，均未改绿或重投 |

审计使用六个独立SQLite只读连接备份，未停服务，**不是六库共同原子快照，也不是11月14日截止时刻快照**。数据库没有可倒推入库时刻的证据；后续保存完好不能追补历史cut完整覆盖。原观察四文件及旧 `reliability-20261111` 未修改。自然凭据续期、最初系统根因和长期可靠性仍未证明，R13保持未完成。

## Qwen 语义映射和取舍

固定参考 [Qwen dws-channel.ts@41a3b9f5](https://github.com/QwenLM/qwen-code/blob/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/packages/channels/dws/src/dws-channel.ts)，不是声称跑过上游测试；本轮不复制第三方源码。

| 参考机制 | 本项目已有边界 | 本轮证明 |
|---|---|---|
| `receiveImMessage` 分离 admitted/completed（1954起） | `Inbox.ingest` 原子保存消息和cursor；`Gateway.intake` 从持久inbox形成job及ack | 接纳不代表工具执行或消息送达。inbox提交前强杀两者均回滚；job/ack提交前强杀后，从已落库inbox恢复，无需重读事件 |
| `scheduleMessage` 对话调度（2185起） | 每路独占Inbox锁、持久job顺序、running状态先落库 | 工具已产生副作用、终态事务未提交时，重启标interrupted并明确提示，不重跑工具或发成功产物 |
| completed生命周期 | 可信runtime结果经校验/冻结后，结果job与文本/文件outbox同一事务提交；交付状态单独跟踪 | 完成提交后强杀只恢复投递；completed不被当作confirmed |
| 同key投递检查点 | transport持久幂等账本与gateway outbox分工 | 合成transport已接收但gateway尚未保存回执时强杀；恢复第四次调用仍复用原key及原payload，只有3个唯一接收key |

Qwen `admitMessage`（2129起）在队列满时可能对at/direct采用未持久停放的调度；`rememberImDelivery`（1297起）有满队列淘汰、检查点写失败仍发送的策略。本项目不采用这些降级，也不把它的 admitted 等同于本项目持久入库。这里只映射通用生命周期，保留现有更严格持久化与未知结果不重放边界，不移植业务宿主。

## 新验证及完成范围

新增 [五个强杀方法](../tests/test_admission_completion_crash.py)，从真实SQLite COMMIT前钩子终止自有合成worker，由重开连接检查已提交状态；另覆盖提交后、合成transport接收后。外部工具副作用另存独立SQLite，每场景跨强杀和两次恢复始终仅1次；产物SHA、原key/payload、终态及二次恢复不变均断言。没有模型、网络或DWS进程。

冻结源码Python3.14.6、原同wheel安装Python3.14.6与3.11.15各运行5方法全部通过；21产品模块及包内许可字节一致，安装测试目录没有源码package。测试素材冻结摘要记录于[脱敏证据](../evidence/2026-11-15/observation-and-transaction-validation.json)。E122原396×3保留，本轮没有声称新跑401全量或上游测试；E078已过群文件强杀样本未重复。

当前UI49通过/14 blocked/1 partial，14 MUST中7未完整，不因新增离线证明而关闭。最近真实UI仍E123：AIC Kimi、原私聊Pi，Codex归档及各自已验范围保留。下一独立项是OpenClaw官方入口、唯一turn宿主、终态/取消与状态隔离契约；再决定是否能薄适配。DWS仅凭新的具体阶段证据继续诊断，原生媒体/引用/组合没有新入口就不重试。最终干净交接仍待完成，不重导E121旧包。

原始观察、六库及日志仅在 `local/observation-closeout-20261115` 和 `local/admission-completion-20261115`，不入Git。

E125后续仅离线读取既有安全DWS调用日志：原窗口40次、窗口后至读取另30次api/request_timeout，均exit1/stage=request且providerExecutionStarted=false。前者38 history/2 other、3268–3872ms，后者30 history/3266–3395ms。见[脱敏汇总](../evidence/2026-11-15/observation-existing-dws-diagnostics.json)。这是逐调用诊断，不能与16个周期poll_error采样互换，仍无更具体连接阶段。
