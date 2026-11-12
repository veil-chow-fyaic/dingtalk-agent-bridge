# 运行、接入与恢复

2026-11-12，E095当前状态：用户完成登录并授权回主线、新AIC专用群。三个受管服务运行，双路history-only15秒；实际部署E093冻结产品、cut/积压审查及UI证据见[恢复记录](100-aic-group-resume-and-files.md)。仅新AIC测试群＋原两人私聊可测试，企业大群禁测；心跳PAUSED。系统Keychain/auth/doctor诊断等仍禁止，故障持久暂停、不自动反复认证。旧入口已[存档](history/through-E076/README.md)，[完整验收](../plans/completion/ACCEPTANCE_MATRIX.md)仍未完成。
## 安装与工作目录

需要Python≥3.11及POSIX；运行包仅使用标准库，构建需要setuptools。macOS arm64已有实际验证，Linux未实机认证。DWS及可选图片上传补充分别配置，不捆绑账号数据或二进制。新使用者在自己的项目检出中执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab-service --help
```

六个安装入口为`dab`、`dab-bridge`、`dab-agent`、`dab-consume`、`dab-doctor`、`dab-service`，分别对应HTTP客户端、传输、可选执行器、持久消费、诊断及进程管理。下文`python3 -m ...`应使用安装了包的解释器；源码检出也可直接运行。所有服务以**启动工作目录**作为配置、账本、文件及任务根目录，不从site-packages寻找业务数据。

从[路由模板](../config.routes.example.json)及[执行器模板](../config.agent.example.json)填入独立核实的身份和会话；模板占位符不能直接运行。`accountId`为本地别名，`profile`是官方授权上下文，`selfSenderId`须用本人实际消息字段核对。私聊另需`peerOpenDingTalkId`。多路由及迁移见[通用工具](22-generic-tool-and-consumer.md)。

路由模板默认history轮询，本机当前也仅使用history，不启动共享bus。独立部署如需官方事件提示，应先核共享bus生命周期和清理边界，再明确添加`receiveMode: "stream_hint"`。提示仅唤醒history，15秒轮询继续兜底。原生PNG/JPEG上传需另配`imageUploadBinary`，构建及官方边界见[图片补充说明](../integrations/dws_image_upload/README.md)。不要把未配置的能力当默认可用。

## 当前本机部署与管理

本机固定官方DWS v1.0.67，旧全局版本保留。liev是普通真人账号，官方调用使用显式profile；`--as`仅在声明该参数的具体命令适用，不能通用追加；veil是客户端测试用户。客户端显示liev及“通过AI发送”，`[Agent]`仅为文字前缀，没有新建bot。群/私聊各一个gateway；群要求白名单发送者的`/agent`前缀，私聊白名单文字或附件可交办，liev自身回复不触发。当前只在新AIC测试群和原两人私聊验收；企业大群/旧群不得发送测试。

统一管理器拥有传输及两个gateway；以下读取本地进程与准入状态，不调用DWS，不把状态检查当作新增验收：

```bash
python3 -m dingtalk_bridge.service_manager status
python3 -m dingtalk_bridge.dws_access status
```

E095已按用户新授权恢复普通业务，不再等待E074/E090旧许可。正常受管维护使用`dab-service --agent-config PATH start`等参数并保留原配置与账本；重载前确认无运行/排队任务和未决投递，仅代码受影响的gateway维护应保留transport。凭据故障触发持久暂停后不得自动解除或反复认证；`resume --confirm-retry`只解除本地防护，不修复钥匙串。两个旧一次核验key均已消费，绝不作为维护探针重复执行。

启动时先传输、后显式选入的gateway，停止顺序相反。只需通用IM工具时可不选gateway；不会自动承接模型任务。管理器按实际进程归属发SIGTERM，不接管已有端口或强杀共享DWS bus。状态在`local/runtime/managed-processes.json`，日志为`managed-transport.log`和`managed-agent-N.log`。旧`service_ctl.py`/`agent_ctl.py`及历史PID文件不管理当前进程，不能混用。管理器参数及当时实验见[历史管理器验收](40-service-manager-and-restart-ui.md)，不能直接照抄历史恢复动作。

没有开机自启，也未授权重启本机。状态只说明本地归属和存活，不能证明认证、模型或真实UI成功。E062已修复实际捕获的TERM后同启动时间E退出过渡：只继续有界观察，不追加信号或提前判已停止。其他身份变化仍拒绝，未观察的历史错误不能断言同因；若再次发生，先读同次私有诊断及status，不按旧PID强杀，见[退出过渡修复](79-manager-exiting-transition.md)与[诊断边界](57-manager-identity-diagnostics.md)。

前台诊断同样会调用DWS，本机禁止额外auth/doctor诊断，不能通过前台绕过故障暂停或与当前服务重复运行。正常独立部署前台/后台不能同时占用同一实例；传输可单独改`--port`用于隔离诊断，**随包CLI、gateway、consumer及管理器使用127.0.0.1:18768，没有统一改端口参数**。

## 本机令牌与接口

HTTP只绑定loopback；所有接口要求Bearer token。首次启动生成`local/runtime/http-token`并设0600，它不是钉钉OAuth令牌。客户端默认从当前目录读取，也可用`dab --token-file PATH`选择已授权本地令牌文件；不要把令牌写进源码或打印出来。

当前服务已运行；以下为本地HTTP读取示例，不为查询另起一套服务：

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

附件缓存丢失或摘要变化会报错；核对后可显式`attachments --repair`取回原件，新目录/manifest替换缓存指向，旧文件保留。首次与缓存共用完整性校验；成功清单通过同目录0600临时文件、文件fsync及原子replace发布，写失败保住旧好清单，崩溃遗留临时文件不用于读取。未fsync目录，不宣称掉电持久保证。见[原子清单验证](76-atomic-download-manifest.md)。不要删除仍被消费者引用的文件。

可选gateway保存任务、native session及outbox，执行器可替换。Kimi已有真实Read/Write/Bash与同会话文件交付；它及提示词、官方工具上下文均不是OS沙箱。`runtime.timeoutSeconds`默认600，必须有限且大于0，启动前拒绝NaN/无穷/bool等。超时不自动重做；已产生的文件或外部效果可能存在，先核对。父进程丢失的独立守护会清理正常同组后代，不能保证守护自身被强杀、恶意脱组或外部效果回滚，见[父进程守护](63-runtime-parent-death-guard.md)及[真实超时](64-runtime-timeout-and-installed-wheel.md)。

E068新增每路poll_error_detail（固定脱敏code/component/action/message）；credential_store_unavailable表示官方DWS读现有macOS登录密钥失败，不证明过期/锁定，不能据此直接reset。后续E072增工作区dws_access、E073办公入口共享暂停，已随E095部署加载现场，详见[诊断](85-credential-store-health-diagnostics.md)和[受管调用](88-dws-process-containment.md)。发生凭据存储/超时/进程中断时持久暂停后续受管DWS调用；不自动探测是否恢复。保留账本，先查本地诊断，再按明确批准的一次核验方案处理，不连跑只读请求或改组织扩大监听。默认首次/每30分钟深扫最近24h、普通水位前5分钟补读，每次最多20页/1000条；E084已持久化原窗口和nextPageToken，超本轮容量在后续有界调用接续，重启不丢游标。complete=false不算追平；长停机按watermark覆盖原窗口，恢复须达到固定cut且无待续窗口，无watermark首次仅24h，不能保证更早或平台不可见历史。Stream是提示而非独立完整消息源。升级DWS先隔离版本/摘要，再验证契约，不能先覆盖可用基线。

## 验证与共享边界

最近验证的版本、完整测试结果及保留的失败以[当前状态](17-requirements-progress-review.md)为准；本文不再固定易过期的测试计数。旧实验复核检查各自冻结安装，不拿当前源码替换历史被测版本。

```bash
python3 scripts/run_tests_with_evidence.py
python3 scripts/verify_handoff.py
```

诊断入口在测试fixture清理前保留manager同次拒绝观察，输出到被Git忽略的`local/test-evidence/`；预期负向用例也会留记录，须关联测试结果判定。诊断写入失败使入口失败，不掩盖原错误。单元测试不需账号数据；本机UI审计需要对应`local/`原始证据。API、实际工具、可见回复和客户端下载打开分别验收，不能互相替代。原24h观察仍须等待真实时间，历史不可达/错误/维护不抹掉。外部会话、原生语音条、独立video及部分引用/组合仍有缺口，详见矩阵。

产品、合成fixtures、脱敏evidence可共享；`local/`内的身份配置、OAuth、本机令牌、原聊天/AX/截图、账本和下载件不入Git、不整包分享。官方办公API仍由相同精确profile的DWS承接，DM显式启用上下文，群关闭；E073生成的受管入口支持doc/todo/calendar/mail/drive/minutes六类，固定身份/JSON，保持官方双流及退出码。它不是OS权限隔离，没有新增bot，见[入口边界](89-supervised-official-office-entrypoint.md)。

异常raw或资源引用结构保存在consumer的quarantined状态，游标可继续处理后续合法消息；不为无法规范化的输入创建Agent任务或猜身份。原始事件留本地inbox，只读排查后再明确用户意图，不能自动重放。见[异常消息隔离](70-malformed-message-isolation.md)。

附件缓存命中同时核成功/完整标志、预期资源集合、路径、SHA和准确字节数；损坏缓存拒绝返回，不自动下载或改清单。显式attachments --repair重新调用官方下载到新attempt目录，旧原件保留。见[缓存完整性](71-download-cache-integrity.md)。
