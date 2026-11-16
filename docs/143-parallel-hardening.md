# 并行修复集成、正式部署与可复用交付

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-16，E143。用户明确授权三个sub agents分别推进可靠性、消息交互与交付；各自/tmp冻结源码候选，主Agent审查、集成及现场操作，未派生更多Agent或创建调度。

修复实际历史partial/failedCount/failures使last_sync不完整却健康假绿的问题：持久推导HistoryIncomplete，显式sync及重启仍可见，正常安全分页不报错；不改调用/水位/发送重试。混合消息中每个图片标记必须解析，截断/坏标记不能被其他合法图掩盖；原文和顺序保留。附件缓存I/O/循环软链接故障只隔离该消息，不阻塞后续文字、不退游标或自动下载，显式恢复保留。

主审补出了Python3.11 pathlib循环链接RuntimeError，最窄识别其ELOOP来源，其他程序/SQLite错误继续上抛。新export_release工具绑定Git commit/tree、manifest与已测wheel，核全部包字节/许可/六入口/版本/Python约束/RECORD，拒绝私有路径/数据库/链接/混装/覆盖；不读本机账号配置或认证，不执行归档内容，不能替代已知秘密扫描。

首次并行3×504均有失败：合成进程未就绪及提前timeout；首次串行源504仍一项CLI-exit例提前timeout。原记录不删除，也不宣称并行是已证唯一原因。单例诊断0.856秒通过并记录cli_exit/cleanup，不能替代全量。修正测试目的：CLI退出清理例使用10秒安全上限且子进程存活30秒，防自然结束造成假通过；严格terminal_missing/ready/无late断言保留，真实0.3/2/4秒deadline用例和产品超时策略不动。

最终冻结源码Python3.14.6、同wheel独立安装Python3.14.6/3.11.15各504方法通过，25模块一致；没有把早期失败套件或子Agent局部测试凑成通过数。见[冻结验证](../evidence/2026-11-16/parallel-hardening-validation.json)。

产品2b479a8经停gateway、封调用/排空、停transport、持锁备份/通用空WAL审查后应用；transport-only同SQLite快照覆盖固定cut，无history_window，再封停审积压/未知后恢复原三服务。原99任务/240 outbox/session/配置/绑定保持；新CLI、25模块启动来源/实际配置及60秒12采样零错误/截止seal通过。无业务消息、模型或UI新验收。

原loopback-http观察主动中止，1.106小时/133样本，含1次DWSBusinessError，未满24h且原cut未覆盖；原记录保留，未断言上游错误根因。新parallel-hardening观察北京时间2026-11-16 18:29:37开始，固定2026-11-17 18:29:37截止，只有本地有界采集，无聊天调度。长期/自然refresh仍未通过，零新事件不能冒充无丢失。

同版本源码与已测wheel由新通用工具导出至local/parallel-hardening-20261116/bundle；校验记录和完成标记在包内。源码文档提交与实际产品提交分列，模块必须相等。仍是受控试用候选，非全部MUST签署。见[部署证据](../evidence/2026-11-16/parallel-hardening-deployment.json)及[导出步骤](144-offline-release-export.md)。
