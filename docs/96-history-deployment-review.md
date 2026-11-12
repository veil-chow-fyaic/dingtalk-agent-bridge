# E085：只读部署差异与账本清单

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
