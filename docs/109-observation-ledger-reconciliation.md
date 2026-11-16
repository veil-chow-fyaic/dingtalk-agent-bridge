# 原观察与持久账本对账

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-13，E106。使用新只读工具[scripts/reconcile_observation_snapshot.py](../scripts/reconcile_observation_snapshot.py)，不实例化Bridge/Hub、不调用HTTP/DWS、不接触凭据。结果为[8项核验](../evidence/2026-11-13/observation-ledger-validation.json)。

原reliability-20261111采到的205条事件（原群9、私聊196）在11月13日只读SQLite事务中全部以同seq、完整event对象、同账号/会话精确匹配。baseline到最后capture的实际数据库行集合也一致，不将AUTOINCREMENT序号空洞误当丢消息。当前原群12confirmed；原私聊171confirmed、1rejected，拒绝记录保持。

私聊库还有4条位于最后capture之后的记录，单列为未观测增量。现有events表没有入库时间，消息创建时间也不等于本机入库时间，不能用当前账本补造原窗口截止快照。因此只确认“已采到的事件均完整持久化且采样区间相符”，**不能证明原窗口截止时没有其他已入库消息、上游没有漏发或完整窗口已经逐条对账**。没有新增ledger.json到原run。

原baseline/status/observations/maintenance四文件SHA与E101相同，52条维护全保留，其中13条有某种版本元数据，记录格式并不统一，不能从Git HEAD或这些局部字段推定每个时段的实际加载版本。原1059 unavailable、168 poll_error和所有维护继续保留。新AIC路由不在原baseline，当前AIC部署长期覆盖仍缺，R13不改为通过。

新增4个合成方法验证：原拒绝/unknown保持、缺失/正文变更/错scope/重复行拒绝、采样区间内遗漏行检出、带旧消息时间戳的后来入库行不能冒充窗口覆盖。冻结源码及E104既有wheel的双Python各跑4专项，8核验通过，21产品模块原字节；不宣称重跑全量335。旧E104331全量证据仍只指其冻结版本和当时测试。

只读命令，输出必须位于原run目录外：

```sh
python3 scripts/reconcile_observation_snapshot.py --run-dir local/service-observations/reliability-20261111 --output local/observation-ledger-review.json
```

退出0只表示该次采样区间对账及原件保持通过；必须同时阅读historicalWindowCutoffProven=false等限制，不把退出0当全部可靠性验收。
