# 异常消息隔离与后续任务继续

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E053。修复异常消息正文或资源引用结构导致整个入站批次回滚的问题。异常消息保存在本地quarantined记录中，不创建Agent任务；同一批后续合法消息仍可进入原有白名单与执行流程。

旧实现对raw、resourceRefs元素直接调用get。若raw不是对象，或普通消息/引用中的资源列表含null、字符串、数字，会抛出未被隔离分支处理的AttributeError。入站事务因此回滚，下一轮再次读到同一消息，阻塞后续消息。空对象resourceRefs还有另一问题：会被当成空列表接受。固定官方v1.0.67的chat_result_contracts及chatmsg投影使用资源对象数组；没有把错误形状猜成合法附件。

[message_model.py](../dingtalk_bridge/message_model.py)现显式检查raw为对象、resourceRefs为列表、每项资源引用为对象，异常转成已有的ValueError隔离路径；没有扩大捕获所有程序错误，也没有改变批次跨会话、身份和顺序校验。已有深引用、跨会话引用及未知资源规则保持。原始事件仍存在本地inbox，状态可只读检查；异常输入不会被静默执行或通过显示名猜身份。

[新增回归](../tests/test_message_shape.py)覆盖18种形状：4种非对象raw，7种异常resourceRefs分别出现在外层和引用。逐例验证前后正常消息、隔离原件、游标推进和重启保持；另将18条异常与一条合法授权任务混合交给Gateway，只有合法任务执行和产生三条合成投递，重启后不重放。旧实现2方法产生2失败和15错误，日志保留；修复后通过。

Python3.14源码全量179项通过；Python3.14与最低Python3.11.15另在同一无源码包/账号数据目录使用各自新venv的已安装wheel，全量各179项通过。新wheel六入口/19模块与冻结源码、安装包一致，测试目录没有产品源码包或账号数据。[安装报告](../evidence/2026-11-12/message-shape-install.json)

另对既有两路全部302条官方事件离线回放，其中7条带引用；新旧完整规范化模型逐条相等。原件只读，没有发送或改写旧聊天、任务和会话。[审计](../scripts/accept_message_shape.py)25项通过，[验证报告](../evidence/2026-11-12/message-shape-validation.json)明确保留范围：异常形状来自合成测试，并未声称钉钉实际返回过这些值；旧引用离线回放也不算新入站引用UI通过。

两路空闲后通过manager身份检查正常停启gateway，transport保持原进程，live doctor通过。账号配置字节、全部旧jobs/outbox/meta/deliveries/events及runtime日志不变。DM62/154/163/226、群3/7/12/76保持，无新消息或UI实验。原观察器PID和起点保持，1424样本、11.870小时、6不可达，历史3poll_error及维护保留，尚未满24h。原始数据、失败/安装/部署日志及302条投影仅保存在local/message-shape-20261112。

E052真实私聊计算、145B JSON客户端下载打开的证据仍按当时版本保留；本次没有重新发送它。群范围、入站引用/原生媒体入口和真实失效refresh仍按原矩阵列缺口，项目未完成。
