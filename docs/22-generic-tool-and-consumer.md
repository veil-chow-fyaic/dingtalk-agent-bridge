# 通用 CLI、HTTP 路由与持久消费

本工具不依赖指定组织或指定Agent运行时。实现使用Python标准库。DWS是当前传输后端；AX只在证实必要时增加。当前线上测试仍只涉及已授权单人群，通用性测试采用隔离fixture。

## 使用方式

从项目目录执行，任意Agent可将相同命令作为工具调用。无需提供模型、prompt或runtime地址。

```bash
python3 -m dingtalk_bridge.cli health
python3 -m dingtalk_bridge.cli conversations
python3 -m dingtalk_bridge.cli --account-id <账号别名> --conversation-id <稳定会话ID> events --after 0
```

发送命令有真实副作用，下面是参数模板，不是要重发的验收步骤：

```text
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --text-stdin
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C send --key BUSINESS-KEY --file local/outbox/result.pdf
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C status --key BUSINESS-KEY
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C reconcile --key BUSINESS-KEY
python3 -m dingtalk_bridge.cli --account-id A --conversation-id C attachments --message-id M
```

text-stdin从标准输入读取，文件与图片仍受运行手册的路径边界约束。附件缓存缺失/改变时报错；明确需要重新下载时使用 attachments --repair，新目录取得原件后更新缓存清单，不覆盖原文件。所有响应为JSON；失败HTTP以非0退出，202的未知/提交中状态仍要检查state。

## 配置与路由

[多路由模板](../config.routes.example.json)中的routes可包含任意多个账号/会话。accountId是稳定本地别名，profile是DWS认证上下文，conversationId是实际会话ID；同一个accountId不能映射多个profile。组织名不参与服务路由，name仅展示。

- group：通过群openConversationId读/发。
- direct：配置实际conversationId和对方peerOpenDingTalkId，调用DWS的--open-dingtalk-id，不把私聊塞进--group。
- 启动按原生稳定ID校验目标，不因群改名改变路由；不自动猜同名会话。
- GET /v1/conversations列出当前配置路由；GET /v1/discovery（CLI discovery）分页发现账号可见会话，保留完整性与稳定ID。configure select精确核对后生成候选配置，不自动启用新会话；私聊peer仍需独立解析。见[续作说明](23-continuation-and-migration.md)。
- 多路由请求必须同时提供account_id与conversation_id；只配置一路时保留旧省略参数兼容。未知或不完整路由返回400，不降级到默认群。
- 配置v2每路状态在local/runtime/routes/<认证上下文与会话摘要>/，不共享发送键或游标。旧单路配置继续使用原local/runtime，保持本机原账本（迁移时18条，当前25条）。现提供configure migrate：原路由stateStorage=legacy继续使用原目录，不移动数据库/附件，不改变发送fingerprint；本机已完成迁移。新增路由仍使用独立摘要目录。不要删除原路由legacy标记或重试未知发送。

HTTP沿用localhost:18768和本机Bearer token。所有会话级GET通过query携带路由，POST通过JSON携带路由。[OpenAPI](../api/openapi.json)描述可接入面；配置profile和OAuth凭据不通过列会话接口暴露。

## 持久消费与消息完整性

```text
python3 -m dingtalk_bridge.consume --name MY-CONSUMER --account-id A --conversation-id C
```

每次有界读取最多200条，保存到local/consumers/MY-CONSUMER/inbox.sqlite3。一个consumer名字绑定一个账号/会话；多会话消费者分别命名。重复运行从原游标继续；同进程锁防并发写入。默认一次性shadow消费；--follow用最长30秒长轮询持续读取，--max-batches可限制批次。不运行Agent、不自动回复。`--hydrate-self`仅用于已授权测试原件核对，不关闭self过滤。

收件箱先同事务持久化原事件及消费游标，再下载媒体，避免大附件阻塞入账。状态为pending_media、media_failed、normalized或quarantined。失败不会丢消息；再次运行可重试只读下载。`Inbox.ready()`只返回fromSelf=false且没有解析缺口、附件路径与摘要仍有效的消息；不表示Agent已处理成功。下游若需任务执行、确认/租约和回复队列，应在该公共边界实现，当前未提供完整任务调度器。

DWS历史正文是平台文本投影：当前识别实际出现的图片mediaId占位、文件fileId和quotedMessage，将其恢复为按出现顺序排列的parts。顶部resourceRefs可能包含引用资源，只在quote中放一份。未知格式、资源位置不明或引用跨会话时保留问题/隔离，不声称任意富文本无损支持。naive历史时间按historyTimezone（默认Asia/Shanghai）解析并标timeZoneAssumed；不会将采集时间当消息时间。

## 延迟索引与缓存恢复

普通补读从水位前5分钟开始；首次及每30分钟追加一次最近24小时有界深扫描，原生ID去重。`sync --deep`可明确触发。部分读取不推进普通/深扫描水位；每次仍最多20页/1000条。超过24小时才入索引或单窗口超过上限的情况仍未解决，不承诺零漏消息。

下载每次新尝试使用独立目录；部分失败不发布成功manifest。显式repair重新取原件并校验消息/会话身份、文件路径和摘要。旧缓存保留，所以尚需磁盘配额与保留期工程。禁止自动删除仍被消费者引用的文件。

## 本轮证据

[真实只读验收](../evidence/2026-11-11/generic-bridge-acceptance.json)：18条消息、2条引用、13个媒体部件；18条self过滤；consumer重启无重；错误账号拒绝；深扫描无重；图片cache repair摘要一致。没有新增群消息、邮件、日程或模型调用。

传输/consumer阶段39项确定性测试覆盖多账号/同ID会话隔离、DM参数、同键跨会话独立、批次回滚、游标重启、未知sender、媒体顺序/引用/失败恢复、深扫描迟到消息、缓存破损与修复。新增迁移、发现、长轮询、订阅范围/优雅停止、HTTP契约和媒体队列饥饿测试。私聊/跨组织真实现场依用户要求暂跳过；原生音视频、Stream业务投递、长期可靠性仍未通过。

## 本地执行层

公共CLI/HTTP和通用consumer仍无runtime依赖。最新交付增加独立Kimi gateway，保存精确原生session、任务队列和outbox；原单人群显式本人命令的两轮任务已实际完成，见[docs/24](24-local-agent-product-and-acceptance.md)。当前全套51项测试。上文18条是runtime接入前的快照，不替代当前25条账本。
