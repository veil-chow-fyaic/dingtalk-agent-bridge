# 常驻Stream唤醒与双账号停机补漏：2026-11-11

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


延续原群、veil与liev的私聊范围。veil通过钉钉原生UI输入，liev由官方DWS用户身份发送；没有新增bot、账号权限或第三方联系人。此前独立订阅16条业务事件见[docs/28](28-media-matrix-and-real-events.md)，本轮验证它接入实际服务后的行为。

## 实现和官方边界

当前两个精确路由已设`receiveMode=stream_hint`。官方`dws event consume`分别订阅指定群和指定对端o2o；bridge验证会话、message_id，接收到事件后合并短时唤醒，调用官方history读取完整内容并提交SQLite，再供通用HTTP/CLI消费者读取。15秒定时补读继续兜底。事件正文不冒充完整媒体消息，`source`仍是`dws_history`。

本次补充health中的`poll_scheduler`：启动/事件/定时触发、开始完成时间、各类次数；订阅状态补`last_hint_at`。这些值用于判断收到真实业务后是否确实唤醒history，不能只看ready。账户/会话身份仍是显式配置；health只在带token的loopback接口返回。

官方承担事件供给、鉴权/profile、历史和资源接口；自研只补事件到history同步、去重、持久游标、任务/投递账本和恢复。没有再实现一套官方即时消息协议。

## 真实UI实验

| 场景 | 用户操作 | 实际结果 |
|---|---|---|
| LIVE-GROUP-001 | veil群UI发普通文字 | 收到一次，观测到业务hint和stream_hint同步，未生成任务 |
| LIVE-DM-001 | veil私聊UI交办回复任务 | 收到一次，hint唤醒同步；Kimi完成，liev UI显示“实时私聊已收到。” |
| OFFLINE-DM-001 | 停止传输服务、确认HTTP拒绝连接后，veil私聊UI发任务 | 原消息在停机期间发出；重启首次同步补回，任务只执行一次，UI显示“离线私聊已补回。” |
| OFFLINE-GROUP-001 | 服务仍停机时，veil群UI发`/agent`任务 | 重启首次同步补回；UI显示“离线群聊已补回。”，与私聊分开投递 |
| RECONNECT-GROUP-001 | 只向当前服务拥有的群订阅子进程发SIGTERM，自动重连ready后，veil群UI发普通消息 | 服务本身未重启，群订阅connections变为2；业务hint再次唤醒，消息一次入账且未执行任务 |

三个任务分别有一次接收回执和一次最终结果，共6个确认投递。重启前12条任务、28个outbox记录、33份执行日志均保持原样，绑定、generation及两个不同原生session不变。此前图片缺陷留下的blocked任务保留，没有重试旧实验、换key或擦除失败。

独立只读观察器运行约15分钟，892个采样、11条新事件（5入站/6回复），无重复ID；230个无法连接采样对应受控停机。以约1秒间隔读取health与已提交events。在线群/私聊从消息时间到首次API观察分别为3.212/3.507秒，重连后的群消息4.080秒；消息时间只有秒精度，并跨服务/本机时钟，含采样误差，不作为精确SLA。离线两条直到重启才可观察，这是预期补漏，不能计成在线延迟或伪装成未停机。

这里验证了短时优雅停机和一个订阅子进程受控退出。真实网络分区、授权过期、长停机超出历史窗口、24小时运行仍需单独验证。没有关闭系统网络，也没有强杀其他DWS或用户进程。

## 其他补验与回归

补齐之前待测的群PDF客户端流程：下载liev已发的原PDF，另存`group-received.pdf`，Finder Quick Look打开可读正文，3081字节，摘要与fixture相同。此前私聊PDF也已这样验证；出站图片的客户端另存仍待补。

76项自动回归通过。HTTP子进程测试明确先等待ready引发的初始同步结束，再注入业务事件，在60秒fallback之前验证再次唤醒并返回history正文；它与上表真实DWS/UI证据分别记账。新增只读观察器支持有界时长、采样间隔、独占run目录、原子status、SIGTERM收尾；10秒生命周期实测完成20次采样、无失败、正常结束，不能算24h通过。

## 复核与持续运行

- `python3 scripts/accept_stream_integration.py`：只读检查5条固定实验消息、任务/投递和重启前后记录，不发送、不重启。[账本结果](../evidence/2026-11-11/stream-integration-ledger.json)、[UI观察记录](../evidence/2026-11-11/stream-integration-ui-observations.json)。
- `python3 scripts/accept_media_matrix.py`：只读核验8个媒体案例及群/私聊PDF客户端下载原件。[媒体结果](../evidence/2026-11-11/media-matrix-ledger.json)。
- 私有截图/AX、停机前快照在`local/stream-integration-20261111`；15分钟观察在`local/service-observations/stream-ui-20261111`。公开文件只有摘要与合成标记。
- 短时观察示例：`python3 scripts/capture_service_observations.py --seconds 600 --run-id YOUR-UNIQUE-RUN`。24h可用`--seconds 86400 --interval 30`；实际是否仍存活要结合status更新时间和PID验证，不能只相信旧`active=true`。

两个gateway继续只接受veil、忽略liev自身消息。Kimi可执行本地任务但不是OS沙箱；仍不开放不可信成员。下一步沿用[关键路径](../plans/completion/CRITICAL_PATH.md)补其他格式、用户侧控制、可安装交付与办公工具，不把本轮恢复通过当整个项目完成。
