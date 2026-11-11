# 运行、接入与恢复

2026-11-12，E050核对、E052更新。本文描述当前操作方式；旧部署命令、计数和阶段追加已[按字节存档](history/through-E049/README.md)。当前版本仍为实验交付，完整验收未完成，逐格结果见[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)。

## 安装与工作目录

需要Python≥3.11及POSIX；运行包仅使用标准库，构建需要setuptools。macOS arm64已有实际验证，Linux未实机认证。DWS及可选图片上传补充分别配置，不捆绑账号数据或二进制。新使用者在自己的项目检出中执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab-service --help
```

六个安装入口为`dab`、`dab-bridge`、`dab-agent`、`dab-consume`、`dab-doctor`、`dab-service`，分别对应HTTP客户端、传输、可选执行器、持久消费、诊断及进程管理。下文`python3 -m ...`应使用安装了包的解释器；源码检出也可直接运行。所有服务以**启动工作目录**作为配置、账本、文件及任务根目录，不从site-packages寻找业务数据。

从[路由模板](../config.routes.example.json)及[执行器模板](../config.agent.example.json)填入独立核实的身份和会话；模板占位符不能直接运行。`accountId`为本地别名，`profile`是官方授权上下文，`selfSenderId`须用本人实际消息字段核对。私聊另需`peerOpenDingTalkId`。多路由及迁移见[通用工具](22-generic-tool-and-consumer.md)。

路由模板默认history轮询；要启用官方事件提示，明确添加`receiveMode: "stream_hint"`。提示仅唤醒history，15秒轮询继续兜底。原生PNG/JPEG上传需另配`imageUploadBinary`，构建及官方边界见[图片补充说明](../integrations/dws_image_upload/README.md)。不要把未配置的能力当默认可用。

## 当前本机部署与管理

本机固定官方DWS v1.0.67，旧全局版本保留。liev是普通真人账号，官方调用使用`--as user`；veil是客户端测试用户。客户端显示liev及“通过AI发送”，`[Agent]`仅为文字前缀，没有新建bot。群/私聊各一个gateway；群要求白名单发送者的`/agent`前缀，私聊白名单文字或附件可交办，liev自身回复不触发。原测试群增至3人后新增群实验暂停，等待范围答复；两人私聊继续有效。

统一管理器拥有传输及两个gateway。以下status/doctor只读；stop/start会改变运行状态，维护前先确认任务空闲：

```bash
python3 -m dingtalk_bridge.service_manager status
python3 -m dingtalk_bridge.doctor --agent-config local/agent-config.json --agent-config local/agent-direct-config.json --live
python3 -m dingtalk_bridge.service_manager stop
python3 -m dingtalk_bridge.service_manager --agent-config local/agent-config.json --agent-config local/agent-direct-config.json start
```

启动时先传输、后显式选入的gateway，停止顺序相反。只需通用IM工具时可不选gateway；不会自动承接模型任务。管理器按实际进程归属发SIGTERM，不接管已有端口或强杀共享DWS bus。状态在`local/runtime/managed-processes.json`，日志为`managed-transport.log`和`managed-agent-N.log`。旧`service_ctl.py`/`agent_ctl.py`及历史PID文件不管理当前进程，不能混用。详情见[管理器与恢复](40-service-manager-and-restart-ui.md)。

没有开机自启；机器重启后从同一工作目录按上述显式配置启动。status只说明归属和存活，doctor不证明模型可调用或真实UI成功。现存历史manager关闭身份保护错误尚未定位；若再次发生，先读私有诊断及status，不放宽保护或按旧PID强杀，见[诊断边界](57-manager-identity-diagnostics.md)。

前台诊断先停止受管实例，再运行`python3 -m dingtalk_bridge --config local/service-config.json --port 18768 --poll-seconds 15`；前台退出后才恢复管理器。传输可单独改`--port`用于隔离诊断，**随包CLI、gateway、consumer及管理器使用127.0.0.1:18768，没有统一改端口参数**。

## 本机令牌与接口

HTTP只绑定loopback；所有接口要求Bearer token。首次启动生成`local/runtime/http-token`并设0600，它不是钉钉OAuth令牌。客户端默认从当前目录读取，也可用`dab --token-file PATH`选择已授权本地令牌文件；不要把令牌写进源码或打印出来。

不发送消息的检查：

```bash
python3 -m dingtalk_bridge.cli health
python3 -m dingtalk_bridge.cli conversations
```

| 方法与路径 | 输入及语义 |
|---|---|
| GET /v1/health | 同步、poll_error、Stream提示与轮询状态；不是投递验收 |
| GET /v1/conversations | 当前配置路由；不暴露认证profile |
| GET /v1/discovery | account_id、cursor、limit；只发现会话，不激活路由 |
| GET /v1/events | after、limit（1–200）、wait_seconds（0–30）；返回events/next_cursor |
| POST /v1/sync | 可选deep=true；有界补读，complete=false不推进水位 |
| POST /v1/send | idempotency_key＋text/file/image三选一；纯文本可加reply_to |
| GET /v1/deliveries/{key} | 已持久化状态；未找到404，不发送 |
| POST /v1/reconcile | idempotency_key；可选本机rejection_evidence，见下文 |
| POST /v1/attachments | message_id、可选repair=true；仅选定路由已观察消息 |

多路由会话级GET在query、POST在JSON同时提供`account_id`/`conversation_id`；仅单路时兼容省略。discovery按账号选择；health/conversations为整体视图。具体参数及状态码见[OpenAPI](../api/openapi.json)。POST正文上限1MiB，文件内容不内嵌JSON；服务器读取本地允许路径。

send只有`state=confirmed`返回200，其他状态返回202，**202/CLI退出0并不代表发送成功**；重复调用可能读到旧rejected。confirmed也不证明对方已读。E052保证并发对账的晚结果/错误不覆盖已提交终态，原key/task/message保持；矛盾终态需另行核查。`reply_to`只支持本路由已观察且发送者已知的原消息，来源纳入幂等摘要，由官方再核原消息及收件人。

## 文件、任务和恢复

文件路径只允许工作目录`fixtures/`或`local/outbox/`下的安全相对路径，解析符号链接后仍须在范围内。发送前按内容摘要staging。单文件上限20MiB是bridge策略；原生image仅PNG/JPEG且≤2MiB、不自动压缩，较大图片使用file。gateway超限任务failed并给出压缩/拆分建议，不自动重新生成或投递。官方CLI会TrimSpace，精确尾空白等内容应以文件交付。

`upload_unknown`表示图片上传结果不明、尚未调用消息发送；官方没有该上传任务对账接口。`outcome_unknown`表示发送阶段可能执行：有task ID只查询原任务，没有则保留未知并结合原日志/历史核对。**禁止换key、自动重发或切UI补发**。同key改内容拒绝；确为另一项用户意图才用新key。

明确长度拒绝可显式提供`rejection_evidence`：它是服务工作目录`local/`下的官方日志JSON路径（解析符号链接后仍须位于local内）；需匹配原uuid/目标/执行窗口/实际长度并核验持久payload摘要，不接受聊天附件自证。有task ID不能仅凭状态查询报错推成发送拒绝。该操作只把符合条件的未知记录审计为rejected，不发消息；细节见[拒绝对账](39-rejection-reconciliation-and-feedback.md)。

附件缓存丢失或摘要变化会报错；核对后可显式`attachments --repair`取回原件，新目录/manifest替换缓存指向，旧文件保留。不要删除仍被消费者引用的文件。

可选gateway保存任务、native session及outbox，执行器可替换。Kimi已有真实Read/Write/Bash与同会话文件交付；它及提示词、官方工具上下文均不是OS沙箱。`runtime.timeoutSeconds`默认600，必须有限且大于0，启动前拒绝NaN/无穷/bool等。超时不自动重做；已产生的文件或外部效果可能存在，先核对。父进程丢失的独立守护会清理正常同组后代，不能保证守护自身被强杀、恶意脱组或外部效果回滚，见[父进程守护](63-runtime-parent-death-guard.md)及[真实超时](64-runtime-timeout-and-installed-wheel.md)。

poll_error出现时保留账本，检查日志、官方授权及选定会话只读请求，修复后补读；不改组织或扩监听范围。默认首次/每30分钟深扫最近24h、普通水位前5分钟补读，每次最多20页/1000条；complete=false不算追平，超窗口或超容量仍可能漏。Stream是提示而非独立完整消息源。升级DWS先隔离版本/摘要，再验证契约，不能先覆盖可用基线。

## 验证与共享边界

E052当前产品在Python3.14及最低3.11隔离已安装wheel各177项、六入口/19模块通过；包括并发对账测试及既有历史审计工具测试。当前任务与记录数以[当前状态](17-requirements-progress-review.md)和实时只读结果为准。旧实验复核检查各自冻结安装，不拿当前源码替换历史被测版本。

```bash
python3 -m unittest discover -s tests
python3 scripts/verify_handoff.py
```

单元测试不需账号数据；本机UI审计需要对应`local/`原始证据。API、实际工具、可见回复和客户端下载打开分别验收，不能互相替代。原24h观察仍须等待真实时间，历史不可达/错误/维护不抹掉。外部会话、原生语音条、独立video及部分引用/组合仍有缺口，详见矩阵。

产品、合成fixtures、脱敏evidence可共享；`local/`内的身份配置、OAuth、本机令牌、原聊天/AX/截图、账本和下载件不入Git、不整包分享。官方办公API仍由相同精确profile的DWS承接，DM显式启用上下文，群关闭；没有通用任意命令代理或新增bot。
