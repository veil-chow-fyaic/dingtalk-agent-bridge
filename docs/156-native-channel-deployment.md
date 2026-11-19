# E156 · 原生通道合并与核心部署

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


PR #9的四项必需CI已通过，于`2026-11-19T02:35:34Z`合并。实际部署、三服务启动与短观察按独立收据核对；不是从合并或磁盘集成推定上线。

| 对象 | 精确身份 |
|---|---|
| E155本地公开源码基线 | `92b4f4bb04beb8e4791006a659c08aba58d7bfaf` |
| GitHub main合并 | `d59e7e40997498f6aacc9bded22a1f588c9de0ac` |
| 现场实际部署 | `d444ccf9f720b10c77b961b2bedd33476fb8d46d` |
| 上述源码的相同树 | `19fad29acc98af10807b774a24825116cefb0f54` |
| 后续文档HEAD | 由独立文档PR记录；不冒充实际部署 |

26个产品模块与冻结源码逐字节相符，实际启动与配置来源通过。transport、原群Kimi gateway及原私聊Pi gateway运行，默认product呈现；临时canary真实宿主已停止。本次没有把OpenClaw设为常驻执行器，也不证明Kimi既往403访问故障已恢复。

双路在同一SQLite快照内覆盖固定cut `2026-11-19T02:39:55.752100Z`，无待续history窗口。业务状态保持；已有一笔未知投递按精确私有收据隔离，仍为未知且未重发/未标成功，其他pending和unknown均为0。公开只保留隔离收据摘要，不发布原键或会话标识。

部署后短观察从`2026-11-19T02:46:27.409401Z`至`2026-11-19T02:47:27.424897Z`，实际60.00505337497452秒/13采样；不可达、错误采样及路由错误记录均为0，截止覆盖与启动来源复核通过。该窗口不替代E150旧产品24小时审计，也不证明今后零故障或自然refresh。

上线核对了原有的 101 个任务和 245 条 Agent 发件记录，并比对原会话、游标和绑定。切换时先持锁备份八份数据库。两份退役的 OpenClaw 收件库含已提交的 WAL，审查从封存的主库和日志副本重建完整视图，再校验每份逻辑备份。旧群正文仍按原键对账，原输入不会被恢复后的群执行器再次领取。

E155真实双路模型/运输/客户端下载证据保持；E154的4B错误、同名加序号及旧群未知保持原阶段事实。真实多轮、取消和恢复仍分别验收。原PRD、64格矩阵及最终自检不改：14项MUST中13项通过、R06部分，UI仍54通过、6阻塞、4部分；fullProductAcceptance=false。

[PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9) · [脱敏部署收据](../evidence/2026-11-19/native-channel-deployment.json) · [E155文件验收](155-openclaw-two-route-file-acceptance.md) · [E154保留记录](154-openclaw-real-files-and-client-receipts.md)。
