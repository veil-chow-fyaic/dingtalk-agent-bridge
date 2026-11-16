# DWS中断占位的定位与恢复

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-13，E108。用户明确要求查清并恢复AIC测试群/原私聊、部署并做真实UI；该指示授权本轮有界恢复，覆盖旧计划“不恢复”的等待状态。钥匙串、auth/login/doctor、凭据改动等禁令不变。

直接触发点是DWSAccess.lease取得已无主的slot锁后，读到旧active占位，按既有规则持久暂停。原slot0 active与闩原件已保留；三个原服务PID从前晚持续存活，09:33管理器无重启记录；当前未见配置DWS/图片binary进程。旧格式没有调用PID/阶段，不能把最初中断者写成已知，也不能据此说认证失效。

补充私有调用日志：每次随机attempt、slot、调用者PID、时间、封闭调用类别和reserving/reserved/invoking/released/raised/release_failed等阶段。不记录参数、账号、正文、stdout/stderr或令牌；两个并发槽串行追加完整JSON，fsync落盘。日志写失败单独提示，不改已有回执/暂停语义。显式resume和无主占位也记证；不新增自动重试或认证恢复。

六个专项用真实合成进程SIGKILL、释放落盘故障复现残留和暂停，并验证显式恢复、两槽归属、参数不入日志及日志失败不改结果。冻结源码/同wheel双Python各341通过，21模块、六入口、许可一致，见[冻结验证](../evidence/2026-11-13/dws-call-journal-validation.json)。停止/备份两个空闲gateway和transport后，旧session/历史/拒绝/失败保持。

本轮执行方案为：持有两槽锁确认无主后显式resume，只启transport，90秒请求限时和15秒清理保持，最多观察5分钟；必须先结束原history_window并覆盖本轮固定cut。先阻止新调用、等在途读完成再停transport审查积压；不通过中断正在执行的读请求制造另一暂停。随后按冻结旧E099配置/原进程证据显式迁移会话契约，原ID不变，恢复两gateway；真实UI另记，不将API成功当UI通过。

上文初始检查点未执行真实恢复；以下E109已执行。CUA重置后仍failedToCreateImageDestination，已询问桌面是否解锁；这不阻止先恢复底层，不用其他UI技术绕过工具限制。


## E109：已真实恢复和部署

用户本轮恢复指令已执行，不再等待旧的恢复许可。12:25先启动transport，完成原history_window；两路当次同步complete、无poll_error。恢复脚本误把last_sync.at（调用开始时间）当作历史覆盖截止，实际上这时只读完09:33旧窗口，不能证明停机期已补齐。先持久阻止新调用，等两槽在途读自然结束，再停机审查，没有中断正在执行的DWS。当时两路本地未消费事件均为0，但这不能证明远端停机消息为空；该门槛错误导致gateway提前启动。后续补读后按持久watermark重新核实两路覆盖固定cut、无未完窗口，82旧任务仍完全相同，没有观察到新增任务或旧失败重放。原始错误结果留local，不能倒称原阶段通过。

两个原gateway配置与E103进程归属/E099旧协议证据对应；SQLite备份后显式写入兼容契约，原session ID/代次/绑定、82任务、回执不变。12:26三个服务受管启动并加载997e9fa的21个冻结模块，含E104契约与E108调用日志。新列runtime_context对旧任务保持NULL，不倒填历史。

向AIC群和原私聊各发送一条新的合成文本探针，仅一次。两条官方回执均confirmed，message ID与本地投递一致，后续官方history回读正文完全一致、from_self=true，consumer已消费且没有创建新任务。12:29检查点累计28次真实受管调用完成，无新的暂停/credential故障；此计数是短时检查点，不是长期稳定证明。官方binary/profile/两路白名单保持，未调用auth/login/doctor或操作钥匙串。

[25项当前状态核验](../evidence/2026-11-13/dws-recovery-deployment-validation.json)检查点通过，结论只涵盖更正后的当前状态，明确不为原门槛背书。源码/安装包仍是E108同一冻结341项，没有把文档提交后的HEAD混称另一轮测试。原始配置、进程、两阶段记录、备份、回执和历史回读均仅留local/history-recovery-20261113；原reliability run不变。

**UI尚未闭环。** CUA重置和正确bundle仍报failedToCreateImageDestination；应用清单显示钉钉运行，磁盘尚有48GiB，不证明桌面解锁，也不足以定位工具错误。没有绕用其他UI技术或假装veil发消息。本轮仅liev出站和history回读通过；新版真人入站任务、相同session真实续接与客户端下载打开待工具恢复。待决桌面状态问题只提一次，不需要密码。旧49/64、7 MUST缺口不因此改绿。

旧09:33暂停的直接原因是无主active槽，已核无持锁调用后显式释放，通道实际恢复。旧状态没有PID/阶段，因此最初中断为何发生仍不能确诊；不能把恢复成功写成DWS认证根治。新日志补足下一次中断的归属证据，保守暂停和两并发/90+15秒防护保持。


## E110：桌面解锁后的UI工具核验

用户已确认Mac解锁且桌面正常。钉钉重新绑定失败，重置CUA JavaScript会话后再绑定仍失败；独立Finder绑定也报相同failedToCreateImageDestination。失败发生在读取界面之前，没有操作输入框或发送任何新消息。不能把它继续归因锁屏或DWS，也不能假定修改屏幕权限就会解决。

今日Codex/app-server日志未检到该错误，按实际控制服务进程名读取最近macOS日志亦无匹配；没有因此重跑旧故障路径。13:02只读本地状态显示三服务运行、DWS ready、两路约13:01:51完整同步且无poll_error；三服务均已独立运行于PPID1。未执行新的DWS探针或产品测试。

[官方截图故障指引](https://learn.chatgpt.com/docs/appshots#limits-and-troubleshooting)包含重启桌面应用，但未说明这个精确错误的成因。下一步仅建议用户保存工作后正常退出/重开Codex，作为恢复控制服务的尝试，不保证修复；无需重启Mac、重新登录DWS、处理密码或修改权限。原测试授权保持，工具恢复后继续原两路新任务/UI，旧探针只读复核。[脱敏记录](../evidence/2026-11-13/unlocked-desktop-ui-blocker.json)。


## E112后续
用户自行重启后UI读取恢复，三个无自启服务重新按固定cut/停机审查恢复；首次网络超时保留。随后解决Kimi本轮网络环境差异，两路新任务及文件下载打开已验，见[完整记录](113-reboot-recovery-and-runtime-network.md)。E110不再是当前阻塞。
