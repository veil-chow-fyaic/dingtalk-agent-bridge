# 重启恢复、执行器网络与新版真实UI闭环

2026-11-13，E112。沿用户已有恢复授权，只操作AIC测试群和原两人私聊。产品保持997e9fa的21模块，未改产品、全局DWS、身份、凭据或系统代理；没有auth/doctor/Keychain操作。此前E108冻结源码/同wheel双Python341项仍是原测试，不称本轮重跑。

## 恢复与保留的失败

重启前14:18:20的history调用遗留active槽，三服务已停止。先保留槽文件/日志、六个SQLite备份、82旧任务及回执，再用原受管resume确认两槽无主后恢复；没有按旧PID发信号。

14:40首次transport启动的会话校验返回request_timeout，约3.87秒后释放调用槽，进程退出；gateway尚未启动，没有发送消息。该错误是官方业务调用返回的超时分类，没有证据证明token失效。原history-attempt/result和启动日志保留。随后无凭据的公开域名TLS检查通过，一次同目标受管读取约1.14秒成功；才在新记录中再次进行恢复，不循环重启。

第二次只启transport，固定cut为14:43:42；群watermark到14:44:02、私聊到14:44:05，均无history_window。在gateway停机期间核实覆盖，再封新调用、等待在途读取释放、停机核本地积压。10项审查通过，0未消费事件/0待处理候选，82旧任务和旧投递不变。随后恢复三服务，保持原profile、路由、白名单和session。此次正确使用持久watermark，没有重演E109的last_sync.at门槛错误。

## 首轮真人任务发现Kimi自己的续期连接失败

CUA重启后能正常读取钉钉。veil在群和私聊各发送一次E112任务，liev接收回执均可见；两次Kimi都在访问auth.kimi.com的OAuth token端点时Connect Timeout，事件只有system.version，没有工具执行记录。bridge按已部署的终态契约标记failed/runtime_terminal_missing，文字失败提示实际送达两端，未假报完成、未产物投递、未自动重做。原两个任务保留。

只读网络对照发现：macOS已有本机HTTP/HTTPS/SOCKS代理，gateway父环境无HTTP_PROXY/HTTPS_PROXY等变量。[Kimi官方环境文档](https://www.kimi.com/code/docs/kimi-code-cli/configuration/env-vars.html)说明没有这些变量时直连；[社区相近报告](https://github.com/MoonshotAI/kimi-cli/issues/2650)也记录过OAuth连接超时，即便独立HTTP探针成功，不能仅凭探针归因账号失效。

本机Python无凭据请求在直连及现有代理下均返回405，TLS也通过；这不证明Kimi内置HTTP路径同样可用。独立Kimi任务只继承现有代理变量，13.68秒返回预期JSON及可信session终态，没有调用工具。随后只受管重载两个空闲gateway，让它们继承同一现有代理，NO_PROXY保留回环；transport进程、任务/回执/session和配置原字节不变。没有修改系统代理、CLI登录或权限，也没有降低TLS校验。

**范围限制：**这是运行环境调整后真实成功，不是唯一根因或长期根治证明。网络变量当前属于两个gateway进程的启动环境，普通无变量重启不会自动继承本次设置。下一实现应给通用启动配置加入可验证的环境声明及重启证据，不把本机端口写成产品默认值，不修改HOME或复制认证资料。当前脚本与精确环境记录只留local，历史一次性恢复脚本不可直接重复执行。

## 网络调整后的两路真实闭环

两条E112B是独立的新验收指令，明确保留前两条失败任务，不重放旧job/key。操作主体仍是veil客户端和liev普通真人账号；“通过AI发送”为客户端展示。

| 会话 | 真实执行与续接 | 用户端交付 |
|---|---|---|
| AIC测试群 | 同一原session回忆E103结果1387，实际Python计算41×37=1517 | liev完成文字、32B TXT；钉钉下载后Finder快速查看显示old_result=1387/new_result=1517 |
| 原私聊 | 同一原session/工作区读取旧JSON值493，实际Python计算17×59=1003 | liev完成文字、46B JSON；钉钉下载后Finder快速查看显示493/1003 |

两个下载文件均与运行器产物及原定SHA256一致；不是预置本地文件冒充下载。旧两个E108探针只读确认可见，没有重发。本轮10条新回复（含两失败通知）均confirmed且官方history自身回读一致，无自身消息生成任务。

一次Finder切换出现frontmostApplicationChanged，重读现态后才继续；Quick Look两个内容均真实可见。原始聊天/截图留私有CUA记录，运行日志、数据库、下载件及脚本留local/reboot-recovery-20261113。

[34项最终核验](../evidence/2026-11-13/reboot-recovery-ui-validation.json)通过：82旧任务/旧回执保持、两个旧session契约及代次保持、两失败和两完成、真实Python、新10回复/历史回读、两个下载件内容及摘要、三个归属进程、两路同步、21产品模块一致。当前新版任务/续接/文件UI缺口已补；没有新增矩阵媒体格，49/14/1及7 MUST不完整仍保持。自然续期与长期可靠性、受限协议、Codex及最终交接继续；不能把本次成功称为健康24h或全部完成。
