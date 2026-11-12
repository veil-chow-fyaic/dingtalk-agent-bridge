# 通用CLI、HTTP路由与持久消费

2026-11-12，E077当前停机边界更新。公共工具不依赖固定组织、模型或Agent runtime；官方DWS是传输后端，原生UI只用于用户视角验收，不是自动发送后端。liev普通账号与veil两人私聊、原两人群均有实际证据；历史原3人群曾获许可，最新聊天入口要求多人实测暂跳过；不把它固定成产品组织。旧运行入口已[按字节存档](history/through-E076/README.md)。当前真实服务停机、operator_suspended保持；下文是接口契约，不授权执行真实查询/发送或启动后台，E074一次核验许可仍待决。

## 调用方式

从服务工作目录执行；安装后的`dab`等价于`python3 -m dingtalk_bridge.cli`。服务、随包CLI/gateway/consumer使用127.0.0.1:18768；CLI可改`--token-file`，没有远程地址或统一端口选项。运行管理与安装见[运行手册](15-service-runbook.md)。

```bash
python3 -m dingtalk_bridge.cli health
python3 -m dingtalk_bridge.cli conversations
```

以下是独立部署参数模板。discovery、sync、reconcile及附件下载都可能调用真实DWS，即使只读也可能触发鉴权，当前事故停机期禁用。A/C/M/BUSINESS-KEY须换成自己已验证的账号别名、会话、消息及业务键，不能直接作为健康探针发送：

```text
python3 -m dingtalk_bridge.cli --account-id A discovery --cursor 0 --limit 50
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C events --after 0 --limit 100 --wait-seconds 25
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --text-stdin
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --text TEXT --reply-to M
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --file local/outbox/result.pdf
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --image local/outbox/result.png
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C status --key BUSINESS-KEY
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C reconcile --key BUSINESS-KEY
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C reconcile --key BUSINESS-KEY --rejection-evidence local/rejection-log.json
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C attachments --message-id M --repair
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C sync --deep
```

这些send是互斥的独立用法示例，不能用同一个业务键轮流发送不同内容。全局选择参数在子命令前；`--text`、`--text-stdin`、`--file`、`--image`四选一，stdin读至EOF。`--reply-to`只配纯文本，且原消息已在选定路由观察、发送者已知。文件/图片是服务工作目录的允许相对路径，不是HTTP上传；文件≤20MiB、原生PNG/JPEG≤2MiB且需图片补充配置。

成功HTTP响应以JSON输出；HTTP错误以非0退出。202仍会退出0，必须检查state，不能自动重试未知结果。status只读已有投递；reconcile查询原task，或显式用匹配的本机官方日志完成窄拒绝审计，均不发送。repair重新下载原件到新目录并更新缓存清单，旧件不覆盖。完整输入见[OpenAPI](../api/openapi.json)，未知发送与恢复规则见运行手册。

附件接口的200返回资源清单，需检查`ok`、`partial`、`failedCount`。首次下载与缓存命中均核资源标识/唯一性、路径、字节数；首次计算SHA，缓存还比对已存SHA。坏首次响应返回502且不写成功清单；合法部分结果或缺少必要资源返回`ok:false`，后续只读下载可重试。坏缓存必须显式repair；repair的新响应若校验失败，原好清单和旧文件保留。[验证边界](75-fresh-download-integrity.md)。成功清单在同目录私有临时文件完整写入并fsync后原子替换；写失败保旧，崩溃遗留临时文件不用于缓存读取，不宣称掉电持久。[提交边界](76-atomic-download-manifest.md)

## 配置、发现与状态隔离

[路由模板](../config.routes.example.json)可配置多个账号/会话。`accountId`为稳定本地别名，`profile`为DWS认证上下文；同别名不能映射多个profile。`conversationId`为稳定原生ID，name只展示。group使用openConversationId，direct另需真实`peerOpenDingTalkId`并调用官方私聊参数，不塞进group参数。

模板未写`receiveMode`时使用history；显式`stream_hint`增加官方事件唤醒，定时补读仍保留。原生image另配`imageUploadBinary`；不能仅凭模板存在认为已启用。自己的执行器配置从[Agent模板](../config.agent.example.json)独立准备，白名单、身份及runtime二进制需实际核实，`officialDwsTools`默认关闭。

GET conversations只列当前配置；discovery分页发现可见会话，不激活监听。`configure select`只读核对目标并生成新候选文件，不改当前配置；direct需要独立解析peer。下列也仅为参数模板：

```text
python3 -m dingtalk_bridge.configure --config local/service-config.json --output local/candidate.json select --account-id A --conversation-id C --type direct --peer-id P
python3 -m dingtalk_bridge.configure --config local/legacy-config.json --output local/candidate.json migrate
```

输出必须不存在，避免覆盖；select不会自动继承`receiveMode`或`imageUploadBinary`，新路由启用前显式核对这些选项。它不能给未知accountId自动授权。旧单路迁移为`stateStorage=legacy`，保留原数据库/附件/fingerprint，不移动或复制账号数据；不能删除legacy标记造成同一路由读到新空账本。新路由使用`local/runtime/routes/<认证上下文与会话摘要>/`，键和游标彼此隔离。迁移历史见[续作说明](23-continuation-and-migration.md)。

多路由会话请求必须同时给account_id/conversation_id，单路兼容省略；错误/不完整选择返回400，不降级到默认群。GET选择放query，POST放JSON。discovery仅按账号选择；health/conversations是全局视图。列会话不暴露profile或OAuth，但事件/附件正文仍是私有聊天数据。

## 持久消费边界

```text
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C --follow --wait-seconds 25 --max-batches 10
```

每批最多200条，保存到`local/consumers/MY-CONSUMER/inbox.sqlite3`。一个名字绑定一个账号/会话；多路分别命名，锁防同名并发写入。默认一次有界shadow消费；`--follow`长轮询，wait为1–30秒，`--max-batches 0`持续至中断。不会调用模型或自动回复；`--hydrate-self`只允许下载自身消息附件用于核对，仍不让self进入ready。

Inbox先同事务写原事件与游标，再物化媒体。pending_media、media_failed、normalized、quarantined分别保留状态；正常运行时下一次可重试只读下载；E072凭据/超时等暂停生效后不再启动真实DWS，不以下载重试绕过暂停。`Inbox.ready()`只返回fromSelf=false、解析完整且附件路径/摘要仍有效的消息，不等于下游已执行成功。通用consumer不提供任务确认/租约或模型调度；独立可选gateway另有任务/会话/outbox，任意runtime也可自行实现消费策略。

历史正文是平台投影；当前恢复实际图片mediaId、文件fileId、quotedMessage为有序parts，引用资源不重复放顶层。quote保留id/conversationId/senderId/senderName，缺senderId保持null，显示名不是授权依据；旧入账不重写。未知格式、位置不明或跨会话引用保留问题/隔离，不能宣称任意富文本无损。naive时间按historyTimezone（默认Asia/Shanghai）解析，并标记timeZoneAssumed。

普通水位前5分钟补读；首次及每30分钟追加最近24h深扫，`sync --deep`可显式触发。部分读取不推进水位，每次最多20页/1000条；更晚索引/超容量仍可能漏。缓存每次尝试独立目录，部分失败不发布成功manifest；磁盘配额/保留期尚未实现，禁止自动清理仍被引用文件。

## 证据与限制

实时统计、已安装包版本、UI矩阵及未完成项见[当前状态](17-requirements-progress-review.md)和[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)。Kimi已有真实工具及交付，Codex响应超时单独跟踪；通用工具无需二者运行。群/私聊、音视频file、引用气泡、双PNG组合各按实际范围记录，不能推广成所有方向、语音条、任意单消息多文件或外部群通过。WeCom模型仅为参考，本项目没有兼容其WebSocket接口的承诺。

产品与合成fixture可分享；身份/令牌、聊天、UI及原始运行证据留本机`local/`。复核已完成实验只读，不再次发送。历史失败、未知和平台阻塞保持原状态，24h按真实时长单独判定。
