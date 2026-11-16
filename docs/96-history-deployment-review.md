# E085：只读部署差异与账本清单

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


当前具体恢复候选已由[E090仅私聊方案](97-private-chat-recovery-proposal.md)收窄：群transport与gateway都不恢复。下文E085/E086原两路清单与步骤保留历史，不作为启动授权。

新增scripts/prepare_history_deployment.py，只生成本地私有审查材料，没有apply、start、send、auth或网络入口。当前清单位于local/deployment-reviews/history-deployment-20261112/plan.json；它不是恢复许可，也不能直接部署。

实际只读检查了当前两路的六份bridge/tasks/inbox账本：未完成任务0，未确认原投递key 0，历史非成功任务8。失败、blocked、interrupted、cancelled等记录未删除或改绿。未配置的旧账号数据库保持字节/时间/权限不变，但本次不宣称对它们全部完成了服务端对账。配置、全部被保全的本地账本、暂停状态和原查询计划/回执共20文件未变。[11项审计与安全摘要](../evidence/2026-11-12/history-deployment-review-validation.json)。

## 读取边界

工具只取得已有manager、DWS操作和各路bridge/inbox进程锁的read-only fd，非阻塞排他检查；不创建这些锁、不发信号、不构造Bridge/Gateway/Inbox，也不调用可能在构造时将running改为interrupted的产品对象。现存进程不归这些锁管理的情形不在本工具证明范围。

SQLite只有在拒绝全部wal/shm/journal旁文件之后，才用mode=ro、immutable和query_only读取；不检查点、不删除旁文件、不忽略未合并WAL。前后输入摘要/大小/mtime/inode必须一致。若占用、旁文件、身份绑定不匹配或输入改变，则失败而不修现场。

清单保存原任务/投递key、状态、逐行/逐表摘要与未决项，避免把unknown换key或自动重放；原聊天、任务model、payload、session和token值不复制。记录当前21模块与E084验证版本的匹配、配置文件摘要及仅receiveMode从stream_hint到history的拟议差异；身份、白名单、runtime均无拟议变更。15秒是既有transport默认轮询间隔，清单不更改它。群范围仍按最新用户指示；列出群配置不等于允许多人UI测试。

清单只写local的独占0700目录和0600文件，已有key不覆盖；源配置、源码、数据库或旁文件变化后检查失败。可只读核已生成材料：

```bash
python3 scripts/prepare_history_deployment.py --key history-deployment-20261112 --check
```

即使检查通过，输出仍固定newDwsCallsAllowed=false、backgroundStartAllowed=false；认证状态仅引用E082 failed，绝不视为已恢复。

## 验证

7个专项在源码及E084产品的隔离Python3.14/3.11各通过，安装来源与21模块逐份核对。覆盖真实CLI生成/检查/过期退出、两路全状态保留、进程锁、旁文件、身份错误/缺库、读中/读后变化、symlink、写一次、私有权限和版本不符；mock阻断进程/网络/worker构造，原件逐字节/mtime/mode比较。首轮2失败来自fixture把sqlite连接上下文误认为会关闭连接，遗留WAL被工具正确拒绝；显式关闭合成连接后验证通过，旧失败保留。

没有新产品wheel、全量重跑或269项全量主张；E084三套262仍是其冻结结果。本阶段新增真实DWS/UI为0，没有新核验key或后台恢复。

## E086：已有Agent会话的升级边界

[两项专项及8项核验](../evidence/2026-11-12/official-context-upgrade-validation.json)在源码、E084已安装Python3.14/3.11各通过，21产品模块未改。合成旧工作区含schema1原binary上下文、一个已完成任务、一个失败任务、原native session及用户文件。重开不执行旧任务、不重发已确认key；新明确任务运行前刷新schema2受管入口及正确参数说明。新入口在operator_suspended下退出75，合成底层程序调用0，原会话/代数/任务/回执/产物/笔记/暂停字节保持。另一个用例关闭办公能力时仅清理生成上下文，新任务仍接原session。

这些是服从当前上下文的合成runtime验证，不能证明真实Kimi会忘掉旧会话里的原binary路径；提示词、工作区文件和包装器都不是OS权限隔离。真实恢复后必须用新明确任务验证当前入口及同一session；不能删除旧session、发new或重做历史任务来冒充迁移完成。当前没有修改真实工作区。

## 拟议恢复顺序（尚未授权执行）

1. 原E082失败回执永久保留。追加只读核验必须先取得单独的明确许可，并核docs/94固定提案及原key；可读结果只证明这一次会话查询，不授予持续收发或办公写入。
2. 对当前配置、原账本和代码重新核冻结摘要。E085的0未完成/0未知投递仅指当时已经入库的内容；尚未补入的停机期消息可能带来新任务，不能因此一口气启动三个服务。历史8个非成功任务不清零。
3. 先说明并单独取得history后台方案许可：原身份、白名单、账本和session不变，receiveMode改为history、15秒补读，加载E084验证产品。保留维护区间与原观察，失败后保持暂停，不反复认证。该操作会进行启动会话校验和持续history读取，明显超出一次查询许可。
4. 首阶段只运行受manager管理的transport，两个gateway保持停机；现有manager传入空agent列表即可表达transport-only。transport的poll仅sync入站，不自动调用send；本地HTTP仍有受令牌保护的写入口，因此这不是系统层强制只读沙箱。不得启动办公runtime或用旁路客户端发送。history逐页补齐后停止transport，按原消息/游标及投递key审查新增积压，再决定消费范围。
5. 多人实测当前暂跳过，不能因为恢复transport就启动群gateway。只恢复获准的私聊gateway前须核停机期间未消费消息、已确认outbox和旧session；如有不确定执行/投递，逐原key对账，不改cursor跳过、不换key重发，不删历史失败。
6. 新明确私聊任务先核生成上下文、实际runtime工具、原会话回复及UI下载打开。只有真实证据通过才能更新相应矩阵格；E070群关联仍待范围允许时实测。后续群worker恢复须服从最新授权，不能复用旧三人群许可。

当前只制定顺序，没有执行配置变更、resume、服务启动或真实上下文迁移。下一独立项是只读预览本地尚未消费事件与候选任务，补上E085只核已入库任务的盲区；无法读取的远端停机消息明确保持未知。

## E087：补查尚未消费的本地事件

scripts/review_local_backlog.py以E085冻结清单为前提，持已有owner锁、拒绝SQLite旁文件，只读检查每路consumer cursor、全部已入inbox消息及cursor之后的transport events。复用当前normalize/command_for/file_request做分类，不构造worker，不下载、执行、投递、改cursor或修改session。既有job按原ID与状态单列；它们的未终态审查仍由E085承担，不重复当新任务。

输出区分原任务、任务策略忽略、控制命令、普通文本候选、附件候选、显式文件选择待审、内容阻塞和quarantine。它不模拟cancel/new的队列先后效应、不声称文件选择一定成功、不预先批准群任务；条目只写私有ID/状态/hash，不导出消息正文、command/model或session值。若cursor大于本地最大seq，明确列出而不自动纠正。源snapshot、inbox身份/范围或cursor不一致会拒绝；输出只写一次，不覆盖。

当前实际私有预览local/backlog-reviews/local-backlog-20261112/preview.json：两路本地未消费事件0、新任务或通知候选0、quarantine0；20原文件内容/mtime/权限保持。**远端未同步停机消息仍为unknown**，这些0不是恢复后台的授权。E085的8个历史非成功任务继续保留。

[6专项三环境与11项核验](../evidence/2026-11-12/local-backlog-review-validation.json)包括群普通聊天/私聊任务差异、白名单/自身回复过滤、status/cancel/new、文件待审、旧failed去重、坏事件隔离、过期/旁文件拒绝、cursor异常、跨scope拒绝和真实合成CLI私有写一次。首轮5项中1失败/2错误是fixture使用macOS未规范化临时目录绝对路径；改为规范路径并使负向断言匹配具体拒绝原因，未放宽路径防护。新增跨scope用例后最终6项在源码/E084双Python已安装产品均通过，无新wheel/全量重跑/真实DWS或UI。
