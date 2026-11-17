# 通用CLI、HTTP路由与持久消费

实际产品0e151fb/E150；E134两路composition发送/history/官方原件已验，E146完整图文/身份/AI标识已验但逐图保存未成功。E146私聊原生引用UI/history/consumer通过。公共工具独立于组织、模型和runtime；现状见[总览](102-user-requirements-and-roadmap.md)。聊天调度已删除，业务服务独立；范围与禁止项见[AGENTS](../AGENTS.md)。

## 调用方式

从服务工作目录执行；安装后的`dab`等价于`python3 -m dingtalk_bridge.cli`。服务、随包CLI/gateway/consumer使用127.0.0.1:18768；CLI可改`--token-file`，没有远程地址或统一端口选项。运行管理与安装见[运行手册](15-service-runbook.md)。

```bash
python3 -m dingtalk_bridge.cli health
python3 -m dingtalk_bridge.cli conversations
```

以下是独立部署参数模板。discovery、sync、reconcile及附件下载都可能调用真实DWS，即使只读也可能触发官方鉴权，只在已确认范围通过受管入口调用，不另开认证诊断。A/C/M/BUSINESS-KEY须换成自己已验证的账号别名、会话、消息及业务键，不能直接作为健康探针发送：

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

这些send是互斥的独立用法示例，不能用同一个业务键轮流发送不同内容。全局选择参数在子命令前；`--text`、`--text-stdin`、`--file`、`--image`、`--composition-json`五选一，stdin读至EOF。`--reply-to`只配纯文本，且原消息已在选定路由观察、发送者已知。文件/图片是服务工作目录的允许相对路径，不是HTTP上传；文件≤20MiB、原生PNG/JPEG≤2MiB且需图片补充配置。

E093增加文件/图片的可选`--expected-sha256`，HTTP/Python字段为`expected_sha256`：小写64位hex，与真正交给发送快照的字节核对。新请求不一致返回409 `artifact_integrity_mismatch` / `delivery_attempted:false`，不上传或创建投递；已存在相同key与原定摘要则返回原回执并允许对账，不因生产者文件后来变动/删除而重发。新Agent结果自动携带任务完成时的原摘要，旧未终态队列只能从原任务已存摘要补齐，无证据时保持未决。普通调用者未传此字段仍使用当次文件字节，不能声称绑定更早的版本。[采用与验证](references/artifact-digest-adoption.md)

成功HTTP响应以JSON输出；HTTP错误以非0退出。202仍会退出0，必须检查state，不能自动重试未知结果。status只读已有投递；reconcile查询原task，或显式用匹配的本机官方日志完成窄拒绝审计，均不发送。repair重新下载原件到新目录并更新缓存清单，旧件不覆盖。完整输入见[OpenAPI](../api/openapi.json)，未知发送与恢复规则见运行手册。

附件接口的200返回资源清单，需检查`ok`、`partial`、`failedCount`。首次下载与缓存命中均核资源标识/唯一性、路径、字节数；首次计算SHA，缓存还比对已存SHA。坏首次响应返回502且不写成功清单；合法部分结果或缺少必要资源返回`ok:false`，后续只读下载可重试。坏缓存必须显式repair；repair的新响应若校验失败，原好清单和旧文件保留。[验证边界](75-fresh-download-integrity.md)。成功清单在同目录私有临时文件完整写入并fsync后原子替换；写失败保旧，崩溃遗留临时文件不用于缓存读取，不宣称掉电持久。[提交边界](76-atomic-download-manifest.md)

## 文字＋多图单消息（E133实现，E134部署/API验收）

CLI用`send --key BUSINESS-KEY --composition-json local/composition.json`。文件是调用端读取的JSON；其中图片路径相对于**服务**工作目录。HTTP向`POST /v1/send`传`idempotency_key`和`composition`对象，与顶层text/file/image/reply_to/expected_sha256互斥。不依赖gateway、Kimi或其他runtime。JSON结构模板如下，摘要必须换成调用者确认过的真实原件SHA256：

```json
{
  "text": "两张原图，按下列顺序",
  "images": [
    {"path": "local/outbox/first.png", "sha256": "填写第一张原件的64位小写SHA256"},
    {"path": "local/outbox/second.png", "sha256": "填写第二张原件的64位小写SHA256"}
  ]
}
```

images为1–9个有序条目，每项只允许path和sha256；text可省略。路径限定fixtures/或local/outbox/，PNG/JPEG每份≤2MiB，无bridge压缩；缺失、扩展名/文件头/摘要/大小错误在新投递入账和DWS调用前拒绝；完整图像解码仍由官方加载器判定。重复图片仍占引用数并保持位置；不代表上游上传次数。文字按字面转义，不能插入额外Markdown/HTML/远程图片；整个生成正文含图片路径不得超过5120 UTF-16单元，超限拒绝、不拆条。

一次调用先核全部原件，原子发布内容寻址暂存，再持久化一个投递键，调用固定官方`+messages-send --markdown`。官方内部完成本地图上传及一条图文消息发送；bridge不按图片循环发消息。顺序、正文、各原件摘要/名称进入指纹，同key不同内容拒绝；已入账同key即使生产者文件删除仍返回原回执。中断、上传/发送结果不明统一保持原key的outcome_unknown，不自动重传/改key/降级成多条独立图片；有task_id才继续原task对账。

这是官方Markdown图文入口，不能外推为独立原生image卡片或普通文件附件数组。E134群/私聊各一条文字＋两张新PNG confirmed；history保留文字和图序，四张官方下载原件与源/暂存字节及SHA一致。E146客户端完整文字/双图顺序、发送者/AI标识已验；逐图保存重复E011三点击仍失败后停止，客户端原件尚未验；1–9图及JPEG的全范围仍按E133合成验证计。E011旧内联图原件获取失败保留，不能用本次成功改写。gateway仍逐件交付，自身媒体过滤后可保持pending_media，不触发runtime；离线物化另计。[实现验证](134-outbound-composition.md) · [真实API验证](135-composition-api-deployment.md)

## 配置、发现与状态隔离

[路由模板](../config.routes.example.json)可配置多个账号/会话。`accountId`为稳定本地别名，`profile`为DWS认证上下文；同别名不能映射多个profile。`conversationId`为稳定原生ID，name只展示。group使用openConversationId，direct另需真实`peerOpenDingTalkId`并调用官方私聊参数，不塞进group参数。

模板未写`receiveMode`时使用history；显式`stream_hint`增加官方事件唤醒，定时补读仍保留。原生image另配`imageUploadBinary`；不能仅凭模板存在认为已启用。自己的执行器配置从[Agent模板](../config.agent.example.json)独立准备，白名单、身份及runtime二进制需实际核实，`officialDwsTools`默认关闭。

GET conversations只列当前配置；discovery分页发现可见会话，不激活监听。`configure select`只读核对目标并生成新候选文件，不改当前配置；direct需要独立解析peer。下列也仅为参数模板：

```text
python3 -m dingtalk_bridge.configure --config local/service-config.json --output local/candidate.json select --account-id A --conversation-id C --type direct --peer-id P
python3 -m dingtalk_bridge.configure --config local/legacy-config.json --output local/candidate.json migrate
```

输出必须不存在，避免覆盖；E150实际产品0e151fb的select已从所选account的首条基准route继承其已有`imageUploadBinary`，不从其他路由或账号借用，也不凭空补路径；`receiveMode`仍不继承。新路由启用前须显式核对候选选项，见[实现与部署](150-native-voice-and-acceptance-scope.md)。它不能给未知accountId自动授权。旧单路迁移为`stateStorage=legacy`，保留原数据库/附件/fingerprint，不移动或复制账号数据；不能删除legacy标记造成同一路由读到新空账本。新路由使用`local/runtime/routes/<认证上下文与会话摘要>/`，键和游标彼此隔离。迁移历史见[续作说明](23-continuation-and-migration.md)。

多路由会话请求必须同时给account_id/conversation_id，单路兼容省略；错误/不完整选择返回400，不降级到默认群。GET选择放query，POST放JSON。discovery仅按账号选择；health/conversations是全局视图。列会话不暴露profile或OAuth，但事件/附件正文仍是私有聊天数据。

## 持久消费边界

```text
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C --follow --wait-seconds 25 --max-batches 10
```

每批最多200条，保存到`local/consumers/MY-CONSUMER/inbox.sqlite3`。一个名字绑定一个账号/会话；多路分别命名，锁防同名并发写入。默认一次有界shadow消费；`--follow`长轮询，wait为1–30秒，`--max-batches 0`持续至中断。不会调用模型或自动回复；`--hydrate-self`只允许下载自身消息附件用于核对，仍不让self进入ready。

Inbox先同事务写原事件与游标，再物化媒体。pending_media、media_failed、normalized、quarantined分别保留状态；正常运行时下一次可重试只读下载；E072凭据/超时等暂停生效后不再启动真实DWS，不以下载重试绕过暂停。`Inbox.ready()`只返回fromSelf=false、解析完整且附件路径/摘要仍有效的消息，不等于下游已执行成功。通用consumer不提供任务确认/租约或模型调度；独立可选gateway另有任务/会话/outbox，任意runtime也可自行实现消费策略。

历史正文是平台投影；当前恢复实际图片/语音mediaId、文件fileId、quotedMessage为有序parts；E150语音标记归一化为audio，复用原件物化，真实语音四方向仍未验，引用资源不重复放顶层。quote保留id/conversationId/senderId/senderName，缺senderId保持null，显示名不是授权依据；旧入账不重写。未知格式、位置不明或跨会话引用保留问题/隔离，不能宣称任意富文本无损。naive时间按historyTimezone（默认Asia/Shanghai）解析，并标记timeZoneAssumed。

普通水位前5分钟补读；首次及每30分钟追加最近24h深扫，`sync --deep`可显式触发。每次最多20页/1000条，部分读取不推进水位；E084已持久化原history_window和nextPageToken，超本轮容量在后续有界调用续读，重启保留游标。恢复要同一快照watermark≥固定cut且无待续窗口；首次无水位仅覆盖最近24h，平台不可见历史及超出补读窗口的迟到索引仍不保证。缓存每次尝试独立目录，部分失败不发布成功manifest；磁盘配额/保留期尚未实现，禁止自动清理仍被引用文件。

## 证据与限制

有时间范围的本地统计、部署版本、UI矩阵及未完成项见[当前状态](17-requirements-progress-review.md)和[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)。Kimi/Codex/Pi各自真实工具与交付证据保留；E131 Kimi订阅访问403导致该次任务失败，OpenClaw仅候选合成验证。通用工具无需启动任何runtime。群/私聊、音视频file、引用气泡、双PNG组合各按实际范围记录，不能推广成所有方向、语音条、任意单消息多文件或外部群通过。WeCom模型仅为参考，本项目没有兼容其WebSocket接口的承诺。

产品与合成fixture可分享；身份/令牌、聊天、UI及原始运行证据留本机`local/`。复核已完成实验只读，不再次发送。历史失败、未知和平台阻塞保持原状态，24h按真实时长单独判定。
