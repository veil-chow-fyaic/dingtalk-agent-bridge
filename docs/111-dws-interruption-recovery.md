# DWS中断占位的定位与恢复

2026-11-13，E108。用户明确要求查清并恢复AIC测试群/原私聊、部署并做真实UI；该指示授权本轮有界恢复，覆盖旧计划“不恢复”的等待状态。钥匙串、auth/login/doctor、凭据改动等禁令不变。

直接触发点是DWSAccess.lease取得已无主的slot锁后，读到旧active占位，按既有规则持久暂停。原slot0 active与闩原件已保留；三个原服务PID从前晚持续存活，09:33管理器无重启记录；当前未见配置DWS/图片binary进程。旧格式没有调用PID/阶段，不能把最初中断者写成已知，也不能据此说认证失效。

补充私有调用日志：每次随机attempt、slot、调用者PID、时间、封闭调用类别和reserving/reserved/invoking/released/raised/release_failed等阶段。不记录参数、账号、正文、stdout/stderr或令牌；两个并发槽串行追加完整JSON，fsync落盘。日志写失败单独提示，不改已有回执/暂停语义。显式resume和无主占位也记证；不新增自动重试或认证恢复。

六个专项用真实合成进程SIGKILL、释放落盘故障复现残留和暂停，并验证显式恢复、两槽归属、参数不入日志及日志失败不改结果。冻结源码/同wheel双Python各341通过，21模块、六入口、许可一致，见[冻结验证](../evidence/2026-11-13/dws-call-journal-validation.json)。停止/备份两个空闲gateway和transport后，旧session/历史/拒绝/失败保持。

下一步在同一恢复attempt执行：持有两槽锁确认无主后显式resume，只启transport，90秒请求限时和15秒清理保持，最多观察5分钟；必须先结束原history_window并覆盖本轮固定cut。先阻止新调用、等在途读完成再停transport审查积压；不通过中断正在执行的读请求制造另一暂停。随后按冻结旧E099配置/原进程证据显式迁移会话契约，原ID不变，恢复两gateway；真实UI另记，不将API成功当UI通过。

本文件初始检查点尚未执行真实恢复；实际结果在后续章节补充。CUA重置后仍failedToCreateImageDestination，已询问桌面是否解锁；这不阻止先恢复底层，不用其他UI技术绕过工具限制。
