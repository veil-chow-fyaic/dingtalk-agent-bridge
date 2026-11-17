# 运行、接入与恢复

E143（2026-11-16）已部署产品2b479a8（25模块，含历史错误可见、异常附件消费隔离及此前HTTP直连修复），AIC Kimi/原私聊Pi绑定保持；两路composition真实发送/history/官方下载原件已验。OpenClaw代码随包部署但未绑定/真实模型/UI验收。最近真实UI仍E131，Kimi Code订阅访问403仍未解除。版本、矩阵和启动条件统一见[当前总览](102-user-requirements-and-roadmap.md)。


两个gateway的网络变量已在私有runtime.environment持久配置，E116无代理manager启动及E120 Codex实际env_ready已验。重载仍先读[风险及恢复顺序](114-dws-risks-and-resolution.md)，只用原manager与当前归属，不重放local一次性脚本。auth/doctor/Keychain操作仍禁止，凭据故障保持暂停，不自动认证；完整MUST未完成。

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

以下为读取已有服务本地HTTP状态的示例；仅需要时调用，不为查询另起一套服务，也不把health当作模型/API可用探针：

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
| POST /v1/send | idempotency_key＋text/file/image/composition四选一；纯文本可加reply_to；composition已部署，客户端验收未完整 |
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

可选gateway保存任务、native session及outbox，执行器可替换。Kimi已有真实Read/Write/Bash，Codex和Pi也已完成实际Python/同会话/文件/取消UI；Pi图片能力未声明；执行器、提示词及官方工具上下文均不是OS沙箱。`runtime.timeoutSeconds`默认600，必须有限且大于0，启动前拒绝NaN/无穷/bool等。超时不自动重做；已产生的文件或外部效果可能存在，先核对。父进程丢失的独立守护会清理正常同组后代，不能保证守护自身被强杀、恶意脱组或外部效果回滚，见[父进程守护](63-runtime-parent-death-guard.md)及[真实超时](64-runtime-timeout-and-installed-wheel.md)。

E068新增每路poll_error_detail（固定脱敏code/component/action/message）；credential_store_unavailable表示官方DWS读现有macOS登录密钥失败，不证明过期/锁定，不能据此直接reset。后续E072增工作区dws_access、E073办公入口共享暂停，已随E095部署加载现场，详见[诊断](85-credential-store-health-diagnostics.md)和[受管调用](88-dws-process-containment.md)。凭据存储失败、受管DWS进程超过90秒期限、进程中断/无主占位、清理不完整或准入状态损坏会持久暂停后续受管调用；不自动解除暂停或探测凭据恢复。API返回的`request_timeout`等普通业务错误不等于该进程超时：guard仍ready时，history按原轮询继续，后续成功会清除对应poll_error；这不允许自动重发未知投递。保留账本，先查本地诊断，再按明确批准的一次核验方案处理，不连跑只读请求或改组织扩大监听。默认首次/每30分钟深扫最近24h、普通水位前5分钟补读，每次最多20页/1000条；E084已持久化原窗口和nextPageToken，超本轮容量在后续有界调用接续，重启不丢游标。complete=false不算追平；长停机按watermark覆盖原窗口，恢复须达到固定cut且无待续窗口，无watermark首次仅24h，不能保证更早或平台不可见历史。Stream是提示而非独立完整消息源。升级DWS先隔离版本/摘要，再验证契约，不能先覆盖可用基线。

## 验证与共享边界

最近验证的版本、完整测试结果及保留的失败以[当前状态](17-requirements-progress-review.md)为准；本文不再固定易过期的测试计数。旧实验复核检查各自冻结安装，不拿当前源码替换历史被测版本。

```bash
python3 scripts/run_tests_with_evidence.py
python3 scripts/verify_handoff.py
```

诊断入口在测试fixture清理前保留manager同次拒绝观察，输出到被Git忽略的`local/test-evidence/`；预期负向用例也会留记录，须关联测试结果判定。诊断写入失败使入口失败，不掩盖原错误。单元测试不需账号数据；本机UI审计需要对应`local/`原始证据。API、实际工具、可见回复和客户端下载打开分别验收，不能互相替代。reliability-20261111及aic-persistent-env-20261113两份旧观察均已结束，故障/维护/版本和缺截止事实保留；R13仍需新的合规自然失效refresh、长期覆盖及完整截止证据，不能重置或重审旧run。外部会话、原生语音条、独立video及部分引用/组合仍有缺口，详见矩阵。

产品、合成fixtures、脱敏evidence可共享；`local/`内的身份配置、OAuth、本机令牌、原聊天/AX/截图、账本和下载件不入Git、不整包分享。官方办公API仍由相同精确profile的DWS承接，DM显式启用上下文，群关闭；E073生成的受管入口支持doc/todo/calendar/mail/drive/minutes六类，固定身份/JSON，保持官方双流及退出码。它不是OS权限隔离，没有新增bot，见[入口边界](89-supervised-official-office-entrypoint.md)。

异常raw或资源引用结构保存在consumer的quarantined状态，游标可继续处理后续合法消息；不为无法规范化的输入创建Agent任务或猜身份。原始事件留本地inbox，只读排查后再明确用户意图，不能自动重放。见[异常消息隔离](70-malformed-message-isolation.md)。

附件缓存命中同时核成功/完整标志、预期资源集合、路径、SHA和准确字节数；损坏缓存拒绝返回，不自动下载或改清单。显式attachments --repair重新调用官方下载到新attempt目录，旧原件保留。见[缓存完整性](71-download-cache-integrity.md)。

## E134组合部署与证据边界

本次按原manager归属停止gateway/transport，保留六库；通用部署计划器因WAL/SHM旁文件拒绝，原记录保留。随后在全部数据拥有者停止且持有manager、DWS和每路bridge/consumer锁时，以SQLite只读事务及backup单独审查；未删除旁文件、checkpoint源库或修改计划器判据。transport-only补到固定cut后再停传输，同一SQLite快照核watermark及无history_window、任务/session/原key和零候选积压，最后恢复两gateway。详见[部署证据](135-composition-api-deployment.md)，这些是一次性现场结果，不能直接重放local脚本。

两条自身组合消息不会生成模型任务，gateway inbox的pending_media符合自身消息过滤；通过API下载及离线materialize不改变该inbox状态。API原件校验不等同客户端保存。UI恢复后只核E134既有消息，不重复发送来补截图。回滚仍须保留新增两条confirmed投递及消息，不能用部署前六库覆盖。

## runtime网络配置

在私有Agent JSON的runtime.environment中声明所需HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY，默认空映射继承父环境。只支持这些键的大写/小写，null或空值清除；配置同步大小写并保留回环绕过，不改变HOME/认证/transport。OpenClaw同样先经过这层网络变量白名单，随后只从该结果保留最小子进程环境；其专用宿主JSON的env只允许shellEnv.enabled=false，不能混同为禁止bridge的runtime.environment网络配置。配置值不进入Git或诊断日志。[配置规则与故障分类](115-runtime-environment-and-dws-diagnostics.md)。

部署证据：87a3d39由无代理环境manager启动，两个实际Kimi子进程通过持久配置获得所需网络；群/私聊工具和文件UI通过。常规重载须等任务/outbox终态、按manager归属停止再修改配置；transport改动另按固定cut补读/停机积压审查流程。回滚代码前先核旧版对runtime.environment的支持，不能直接回退到忽略该字段的版本后声称网络配置仍有效；保留原库/会话和所有失败回执。


## 执行器配置与证据范围

通用Agent模板的runtime指定kind、binary、有限timeoutSeconds及可选model/environment。kind实现包括kimi、codex、pi、openclaw；已实现、已部署和真实验收的范围分开见[接入表](architecture/agent-integration-map.md)。Kimi的历史真工具成功不能解除E131订阅访问403，恢复需要既有服务访问的新证据，不能自动登录、改凭据或切换runtime重试。

Pi使用固定0.84.2的JSON print模式、完整UUID和独立session目录，关闭扩展/skills/prompt templates/themes自动发现；终态要求agent_settled、最后assistant stopReason=stop和exit0。Pi与OpenClaw均未声明image_files，不能靠模型配置声称支持图片。

OpenClaw适配代码已随E134部署，尚未配置绑定或进行真实模型/UI验收；固定官方41f2b981/2026.11.3，走agent --local及stdin，非Gateway远端turn或ACP。配置还要求runtime.model和runtime.openclaw的configPath（绝对路径）、configSha256（64位小写SHA），绑定agent main；JSON在任务workspace外且每次校验摘要。专用JSON只接受[实现中明确的结构](../dingtalk_bridge/openclaw_runtime.py)：三处workspace占位、单个明确provider/model、禁插件/任意层include/宿主env覆盖，不合并系统默认配置。既有合成样例只是测试数据，不是可用provider凭据。

宿主使用独立OPENCLAW_HOME/state/cache/profile和最小环境，不改系统HOME；同名系统HOME profile存在时拒绝。这不是OS沙箱，不能保证任意生产binary不读环境外文件。真实模型/UI需要专用现成授权配置；不复制其他runtime的token。启用或更换运行器须遵守下面的new/绑定门槛。E134仅部署产品代码，保留原Kimi/Pi绑定，没有模型请求。

## 执行器更换与回滚（E118–E120）

不要只改runtime.kind后重启：任务库runtime_binding会拒绝不匹配身份，这保护旧会话免被另一CLI错误续接。正常更换先在已授权会话发`/agent new`，等控制任务和其outbox终态，原native session会归档。停目标gateway并保留原配置；`scripts/migrate_agent_runtime_binding.py`以旧/新配置产生私有计划，apply时重核库、配置摘要及归属，事务保留旧绑定。该工具不写配置、不启动服务、不调用DWS或模型；其精确CLI见`--help`，现场实测见[部署UI](121-codex-deployment-and-ui.md)。没有new、存在活动session/未决任务/未确认回执或计划过期时应拒绝，不能手改SQLite绕过。

当前Pi回退到e7d82cc之前会失去Pi适配，须停目标gateway并按原生new/显式binding迁移选择兼容运行器，不能把Pi会话交给旧CLI。代码回滚须保持当前任务/outbox/session账本，不能恢复旧快照覆盖后来的真实消息。先停止相关服务，固定目标commit和wheel并核模块摘要，核目标版本是否支持当前runtime/session契约及runtime.environment。Codex回滚到0c6f2da之前会重新暴露已知取消迟到写入缺口，应保持该gateway停机；若改回Kimi，按上段归档/显式迁移，再按固定cut和积压审查恢复。未知投递只用原key核对。回滚不包含复制令牌、登录修复或杀共享bus；复杂降级有不兼容时保持停止并记录，不声称已自动回滚成功。

## 观察版本与截止账本

新服务ready记录启动源码及实际解析配置摘要，manager与启动前/ready后摘要和PID核对，collector持续采集。旧服务不自动补造来源，需正常受管部署后才具备新证据；不是进程内存或OS证明。正常维护仍按上文固定cut/排空/积压流程。

新观察使用`python3 scripts/capture_service_observations.py --run-id <新的唯一ID> --seconds 86400 --interval 30`。运行时把收尾窗口写入基线，截止后只读等待既有轮询覆盖，30秒开始/45秒完成，保留每次尝试；失败不改cut、不重置旧run。审查用`python3 scripts/review_service_observations.py --run-dir <已冻结的run目录> --require-complete`，输出须在原run目录以外。24h、零记录错误、统一启动来源与自然refresh分开判断；详见[范围](137-startup-provenance.md)。

## 空WAL旁文件的部署审查

通用scripts/prepare_history_deployment.py默认仍拒绝SQLite旁文件。在已有维护授权且gateway/transport都已停止、DWS已封新调用并排空、原owner锁可取得时，可显式增加--allow-empty-wal；仅允许WAL缺失/0字节及遗留SHM，immutable读取主库且保存/重核旁文件原样。非空WAL、任何journal、锁冲突或审查后变化均拒绝，不删除或checkpoint源库来规避。validation必须选本次实际测试版本，不沿用脚本历史默认记录；CLI只产生私有审查，不执行启动/回滚。runtime绑定使用产品共同契约，包含OpenClaw宿主身份。详见[E141](141-deployment-review-and-direct-ownership.md)。

## 可复用离线交付

使用[scripts/export_release.py](../scripts/export_release.py)从指定Git提交和已测wheel生成包，步骤见[离线导出说明](144-offline-release-export.md)。先过manifest/暂存隐私门；导出不运行归档代码、不读账号数据、不部署，不把包校验当最终MUST签署。

## 新增路由的当前已知缺陷

E144确认当前产品2b479a8的`python -m dingtalk_bridge.configure select`生成新路由时遗漏同账号基准路由的`imageUploadBinary`；文本/文件配置仍有效，新路由原生图片会在上传前明确失败。当前两个已配置会话不受影响。修复候选及安装验证见[阶段报告](145-delivery-and-recovery-closeout.md)，尚未应用运行目录。接入新会话时先检查候选JSON是否明确包含所需helper路径；本工具只生成候选，不替你激活配置。`migrate`离线，`select`会通过官方DWS只读核对目标；不应把全部配置命令称为离线。
