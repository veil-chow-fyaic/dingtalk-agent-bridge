# Stream真实断连、历史兜底与模型失败保留

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E024。共享personal Stream已建立的WebSocket隧道被实际关闭89.446秒；官方daemon报告重连，历史补读继续工作。撤除故障后，同一daemon/consumer/bridge进程恢复Stream事件，未重启或重发来完成恢复。两条veil原生UI任务各只执行一次：A产生模型输出格式失败并在客户端提示，B完成3127并交付37B文件，客户端下载Quick Look打开且原件一致。

## 可控故障装置

固定v1.0.67的 `internal/event/source/personal.go` 使用Gorilla默认Dialer；本机固定依赖v1.5.0的默认Dialer采用 `http.ProxyFromEnvironment`。先用官方status与父PID核对：只有两个consumer，均由本bridge传输拥有，复用同一账号级bus。空闲维护停止manager并确认零consumer后，才终止身份已核实的旧bus；没有对其他daemon、整机网络或凭据操作。

[network_fault_proxy.py](../scripts/network_fault_proxy.py)只在127.0.0.1随机端口提供CONNECT隧道。本次仅允许dingtalk.com及其子域443端口；不解密TLS、不记录载荷或认证头。临时launcher仅给 `event consume` 及它启动的daemon设置代理，history/发送命令、Kimi和原生客户端继续直连。

观察到 `wss-open-connection.dingtalk.com` 的已建立连接，且lsof证实bus连接本地代理后，才开启120秒上限故障。工具关闭该现存隧道并拒绝重连；在89.446秒主动移除标记。官方source从connected变reconnecting，窗口中重连计数6、随后总计7；新WebSocket隧道在恢复后建立。一次gm.mmstat.com请求因不在允许域内被拒绝，没有扩张允许范围；它不作为Stream故障证据。

工具不是生产传输后端。四个真实本机socket测试覆盖活动隧道切断/新连接拒绝/恢复、到期恢复、目标限制、畸形或无界故障标记拒绝，并检查不记录测试载荷及认证头。180秒是合法故障标记的硬上限；畸形标记失败关闭、需明确移除。

## 两条用户任务的不同结果

| 案例 | 原生UI与实际执行 | 结果 |
|---|---|---|
| A：断连期间 | veil发送41×47任务一次；Stream提示计数仍0，history收到任务；Kimi实际Bash/Python计算1927并写工作区文件 | 模型最终没有返回JSON，反而续写了一个虚构的下一任务提示。gateway拒绝解析，保留failed/JSONDecodeError和原始日志，liev显示“本次任务未完成，已保留记录”；未交付局部文件、未执行虚构指令、未自动重试 |
| B：恢复之后 | veil发送不同的53×59任务一次，补充要求只处理当前任务并遵守JSON格式；Kimi真实Bash/Python计算3127 | 完成，3条确认回复；文件卡片→客户端下载→Quick Look显示两行结果，37B与生成件/SHA-256一致 |

A是模型响应违约，不是合法JSON被解析器误判；没有放宽解析、从错误文本中捞取JSON或自动再跑工具。新增真实子进程回归验证：工具已经写出局部文件时，格式错误仍拒绝、执行次数保持一次、日志/局部文件保留、没有validated-response。该测试和已有队列继续行为共同约束失败处理，不把A改成成功。

恢复后私聊收到7条有效Stream提示，旧消息补到时没有重复任务。该轮记录计数及官方source状态，没有另存每个原始Stream payload，所以不宣称逐条payload匹配；此前独立payload证据仍见E005。B短结果气泡没有单独观察，用户侧通过依据为输入/确认/文件卡片/下载/打开。群无新消息或任务。

## 恢复、验证与复核

故障恢复期间同一bus、同一两个consumer和同一三个bridge PID保持。部署和撤除装置的停启另记维护。撤除时再次核对consumer归属及零consumer、终止只属于测试的proxied bus；精确恢复原配置、DM官方工具上下文，manager启动正常、proxy退出、live doctor通过。历史失败/取消/拒绝及运行文件全部保留。

```bash
python3 scripts/accept_stream_network_recovery.py
python3 -m unittest discover -s tests -v
```

50项只读审计、4项证据负向注入通过：缺实际隧道切断、把A改为完成、损坏下载、缺恢复提示均被拒绝。131项回归通过；18个产品模块摘要与E021部署版本一致，此轮新增测试工具/测试/审计，没有修改产品运行代码。共享证据：[现场账本](../evidence/2026-11-12/stream-network-recovery-ledger.json)、[审计负向验证](../evidence/2026-11-12/stream-network-audit-validation.json)、[回归与代码摘要](../evidence/2026-11-12/stream-network-test-validation.json)。原始截图、日志、socket/PID、配置与任务记录仅留本机 `local/stream-network-20261112/`。

原24h观察器未重置，冻结722样本/约6.01小时/累计5不可用（本轮维护新增1），仍未满24h。本次证明Stream连接失联后的history兜底与Stream恢复，不是整机同时断网、无限断网或真实失效凭据验证。A完整任务交付失败保持可见，B成功不能抵消它。
