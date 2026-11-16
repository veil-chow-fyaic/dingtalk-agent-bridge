# 标准化引用保留来源身份

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E034。复核发现`project()`只保留quotedMessage的正文和附件，原消息ID、会话、发送者元数据丢失。现每一层quote增加`id`、`conversationId`、`senderId`、`senderName`，正文及附件顺序保持。缺失、空白或非字符串元数据明确为null；DWS只给显示名时不会猜senderId。顶层消息的身份、白名单、fromSelf和执行指令继续由实际入站发送者决定，引用内容不获得执行权限。schemaVersion仍为1，增加兼容字段；历史已入账模型不自动重写或重新执行。

先新增三个来源字段回归并观察旧实现KeyError，再修复。新增gateway集成回归证明：未授权发送者引用授权者的消息仍不能创建任务；授权请求的原消息ID进入runtime上下文，重启不重复执行。154项全量回归通过（含E031的11项观察器工具测试）。干净导出、新venv安装wheel，六入口可运行，18模块摘要完全一致，无local账号资料。

7条既有官方quotedMessage事件（群6、私聊1）仅离线只读回放到独立私有consumer，来源ID/会话/显示名与官方原字段一致、senderId全部保持未知，重开SQLite后字段/游标不变。没有把历史群样本当新增双账号群UI测试，也没有发新消息。23项只读审计和篡改来源ID负向验证通过，命令`python3 scripts/accept_quote_identity.py`。共享证据为quote-identity-ledger.json、quote-identity-install.json、quote-identity-negative.json；原始样本、临时consumer和构建只在local/quote-identity-20261112。

只在空闲时经现有manager归属校验停止并重新启动两个gateway。传输PID、原24h观察器和起点保持，维护单列；旧任务/outbox/传输/事件/运行日志/session逐项不变，live doctor通过。DM44/109/118/163、群3/7/12/76，没有新任务或投递。CLI新调用直接加载新投影；运行中的两个gateway已加载。

入站引用的真实UI仍未通过。[官方手册](https://notes.dingtalk.com/p/Y7kmby3lP40KXLq2/docs/Y7kmbqkvyernKXLq)描述消息旁的更多菜单；本轮检查两个AX侧按钮，一个无变化，另一个打开编辑历史（已关闭），均未出现引用。两次观察后停止该入口，不重复旧右键/坐标路径。私有证据local/quote-side-menu-20261112；没有发普通文字冒充引用。仅已完成E027私聊出站引用UI，不据本代码修复把入站UI改绿。
