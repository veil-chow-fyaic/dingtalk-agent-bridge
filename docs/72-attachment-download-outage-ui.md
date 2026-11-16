# 私聊附件下载故障与原任务自动恢复

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E055。仅阻断私聊官方DWS `chat +messages-mget` 子进程HTTP网络115.987秒。veil原生上传65B CSV后，消息已进入bridge，但附件任务保持waiting_media且没有启动runtime。故障中另发一次status，原生客户端完整显示“执行中0、排队0、等待附件1”。解除故障后，同一消息自动完成下载、真实Python处理及192B JSON回传；原件已通过钉钉保存并在Quick Look全文打开。

## 有界故障与官方边界

临时私有launcher仅处理私聊route的messages-mget，其余命令直接exec固定官方v1.0.67。只在该子进程环境设置HTTP(S)代理到本机已绑定、未监听的套接字，最长180秒；参数、profile、官方binary保持。CLI原始stdout/stderr和退出码逐次留local，再原样传回bridge，没有伪造JSON成功或改系统代理、凭据、权限、旧缓存。

实际14次官方读取下载退出1，原始错误为io_timeout/request_timeout，并包含proxyconnect tcp证据。history与Stream保持工作，两个会话水位继续更新；只有附件API失败。该结论不等于CDN传输中断、完整主机断网或失效refresh恢复。

115.987秒手动移除故障标记，早于180秒自动截止；恢复时三个受管进程的PID、启动时间和记录相同。设置/撤除launcher分别需要空闲维护停启，维护与恢复阶段分开记录；不把维护重启当自动恢复。结束时服务配置恢复原始字节，DM官方工具上下文指回官方binary，manager及live doctor通过。

## 用户视角与独立证据

| 阶段 | 已观察与核对结果 |
|---|---|
| 准备 | veil原生发送一次说明；liev回复“等待该CSV”，未读取旧附件或提前计算 |
| 上传 | 故障窗口中原生单次上传65B CSV；卡片可见，bridge收到原messageId |
| 等待 | 原任务waiting_media，inbox media_failed；冻结时已有11次失败、runtime日志不存在、无结果文件 |
| 控制 | 原生单次status即时完成，完整三行状态回复在客户端可见，未被附件等待堵住 |
| 恢复 | 不重发、不重启，原messageId一次成功下载并物化；runtime文件创建晚于解除时间 |
| 实际工具 | Kimi一次Bash运行Python，csv.DictReader读取本轮附件，Decimal逐行累加，hashlib计算原件SHA，写JSON；工具输出与独立预期一致 |
| 交付 | liev完整回复“3行，数量合计18，总金额77.59”；192B JSON客户端下载完成、Quick Look完整显示5字段 |
| 原件 | 输入fixture、官方缓存、runtime副本三份同字节；输出生成件、outbox件、官方资源件、客户端下载件四份同字节 |
| 后续 | 清理后继续只读观察超过60秒，无新增任务/回复/回声执行，旧记录和会话保持 |

准备、附件、status是三个原生消息与三个新completed记录，新增六条confirmed回复；不是单消息多附件。DM65任务/160outbox（159确认1旧拒绝）/169传输/235事件；群3/7/12/76及全部旧记录/日志不变。全程无需第二次授权，没有增加联系人或新bot。

[只读审计](../scripts/accept_attachment_outage_ui.py)52项与[结果](../evidence/2026-11-12/attachment-outage-ui-ledger.json)可复核；[8项内存负向](../evidence/2026-11-12/attachment-outage-audit-negative.json)拒绝错误输入、错误金额/客户端字节、缺状态视图、Quick Look busy、没有官方失败、过早执行及伪造发送者。原始证据不修改。

产品代码沿用E054：已安装Python3.14/3.11各180项，不因新增审计声称增加180个UI测试。本段无产品修复。合成CSV可共享；账号、原始CLI/聊天/AX/截图、输入输出原件及运行日志仅在local/attachment-outage-20261112。

原观察PID97881和11月11日19:36:08起点保持，1477样本约12.312小时。维护新增1个不可达样本，累计7，历史3poll_error及全部维护保留；尚未满24h。入站引用、原生语音/独立video、原群第三人范围及失效refresh缺口未改绿，项目未完成。
