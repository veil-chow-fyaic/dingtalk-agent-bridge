# 明确拒绝终态、审计对账与客户端失败提示

2026-11-11，E018长文首段的原始 `outcome_unknown` 已对账为 `rejected`。这表示发送被拒绝，不是投递成功。原始行完整保存在追加的审计表，原实验快照未修改，原正文没有重发。liev 在真实私聊中显示一次“部分回复未送达”提示；veil 用 UI 发送 `/agent status`，可见“结果未确认0、已拒绝1、投递失败0”。

## 本次对账依据

官方 DWS 本机日志的 `jsonrpc_request_body.arguments_summary` 保留原始uuid和接收目标，即使正文被脱敏，仍能绑定到原幂等键。相同execution_id的开始/请求/结束记录构成唯一时间窗口，窗口内的唯一business_error明确为 `invalid_request` / `PARAM_ERROR`，且报告5120上限、实际6220。6220与本地持久payload的UTF-16长度相同。

对账入口还校验：目标和text类型、命令明确失败、没有交错执行、载荷fingerprint相符、原状态为unknown、没有taskId/messageId，且history中没有对应完整正文。不用“搜索不到”单独证明未送达。官方请求日志中原uuid仅出现一次；本段不调用发送接口处理原正文。

新增 `rejection_audit` 保存原delivery整行、完整导入证据、证据SHA-256、来源和记录时间；当前delivery只将state改成rejected，保留key/payload/fingerprint和错误。原outbox随后读取该终态，保留原job和内容，不重新运行Kimi。

这是本机操作者显式提供可信日志后的窄范围对账，不能自动采纳聊天附件中的“失败证明”，也不是对日志真实性的数字签名验证。当前旧日志导入只支持已验证的普通账号text长度拒绝格式；字段缺失、别的目标/uuid、交错请求、大小不符等都拒绝。不能借该入口把不明网络超时或任意业务失败判成未发送。

## 官方错误与自研职责

后续DWS调用若直接返回明确的 `reason=invalid_request` 且 `server_error_code=PARAM_ERROR`，发送阶段记录拒绝终态与诊断证据；只有错误码而没有明确reason不够。超时、无效响应、未知业务错误仍保持unknown。如果已有发送taskId，拒绝的是后续状态查询，不能据此把已提交的发送记成被拒绝。

自研只补状态分类、持久审计、幂等和失败通知。DWS仍负责发送、身份、鉴权与官方回执；没有另造发送API，没有在客户端补发失败正文。

`rejected`是新增的终态，CLI/HTTP调用者应停止自动发送重试。普通 `reconcile` 仍查询已有官方任务；缺taskId时不会猜测。

显式旧日志对账用法：

```bash
dab --account-id 'your-account' --conversation-id 'your-conversation' \
  reconcile --key 'original-idempotency-key' \
  --rejection-evidence local/rejection-log.json
```

文件必须位于当前项目的私有local目录、至多1MiB，内容为官方JSON日志记录数组。相同证据重复对账只返回原结果；不同证据不能覆盖已有审计。不要对本次已经完成的实验再执行写操作，复核用下方只读脚本。

## 用户看到的行为

gateway在同一SQLite事务中保存终态和一条稳定key的失败提示。提示发送失败也不会递归生成更多提示；重启测试证明同任务只通知一次。原任务执行结果保留，执行完成和回复送达分别统计。

现场共新增1个status控制任务、2条confirmed回复（失败提示和状态回答）、0次runtime执行。状态回答显示执行中0/排队0/等待附件0，已完成30、已取消1、需处理历史记录1；回复未确认0/已拒绝1。查询时确认72条不含它自己随后发出的状态回答；最终私聊outbox为73 confirmed和1 rejected。

doctor新增终态失败检查；本机33项检查，仍保留2个warning：这次拒绝、此前保留的blocked任务。不是删除失败历史来得到全绿。

## 验证与交接

```bash
python3 scripts/accept_rejection_reconciliation.py
python3 scripts/accept_long_text_ui.py
python3 -m unittest discover -s tests -v
```

现场34项只读检查通过；缺失UI提示案例和错误审计摘要的内存负向实验均被拒绝。新增9项自动回归及子案例覆盖误绑定、错误长度、交错日志、已有task/history、证据替换、发送与查询拒绝差异、通知持久化/重启幂等；全量108项通过（10.187秒）。自动测试没有故意向真实会话再发送非法长文。

E018只读审计新增严格允许的unknown→rejected对账检查：必须有原行和摘要匹配的审计记录，其他字段不变；没有泛化忽略state/receipt差异。E018冻结证据仍保留原失败，未重新生成其历史报告。

原始UI/官方日志/账号信息/前后账本保留在 `local/rejection-reconciliation-20261111/`。公开证据为 `rejection-reconciliation-ledger.json`、`rejection-reconciliation-ui.json`、`rejection-audit-validation.json`。

本段维护重启传输和两个gateway，已记入原24h观察器；观察器没有重置。完整长聊天气泡、引用UI、统一后台管理、办公工具及24h终检仍未完成，原群3人范围问题尚待答复。拒绝处置闭环不等于整个项目完成。
