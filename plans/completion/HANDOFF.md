# 钉钉 bridge 当前接手入口

2026-11-16，E142。用户要求负责后续全部闭环，不再安排定时任务。项目尚未完成；旧E135停止指令、E139恢复心跳和E140等待截止后部署的安排均已被后续用户指令及实际执行取代。

仅在`/Users/veil/Projects/dingtalk-agent-bridge`，复用`codex/complete-bridge`，单Agent，不派生、不另建实现、不远程发布。先读[AGENTS](../../AGENTS.md)、[当前任务](CURRENT_MISSION.md)、[关键路径](CRITICAL_PATH.md)、[TODO](TODO.md)；需求解释见[总览](../../docs/102-user-requirements-and-roadmap.md)，沿用同一[PRD](01-PRD.md)、[矩阵](ACCEPTANCE_MATRIX.md)、[最终自检](10-自检清单.md)。

## 当前实物

- 实际部署产品`10758ebcd78a4631c2831ebf93b8f5219443805d`，25产品模块，与E140冻结候选及同wheel一致；三个验证环境各477方法通过。后续文档HEAD不是产品部署版本。
- E142已完成停gateway/封调用/排空/备份、E141通用空WAL审查、应用修复、transport-only固定cut覆盖、再停传输审零积压/未知及恢复原三服务。99任务/240 Agent outbox/session/配置/群Kimi与私聊Pi绑定保持。
- 实际25模块启动来源和解析配置一致，CLI health/conversations通过；60秒采集12样本、零记录错误、固定cut账本/来源/seal通过。这不是24h或自然refresh通过。
- 私有部署证据：`local/loopback-deployment-20261116/`；无凭据候选包在其`bundle/`。E140原验证：`local/loopback-client-20261116/`；不要重跑这些目录中的现场部署脚本。

## 观察与调度

原`startup-provenance-24h-20261116`为部署已验证修复而主动中止：1.82小时、218采样、signal退出，未满24h、原固定cut未覆盖；seal和原记录保持。审查在新部署目录的`interrupted-observation-review.json`，不重置、不把它算通过。

新`loopback-http-24h-20261116`：北京时间2026-11-16 17:19:08开始，固定2026-11-17 17:19:08截止，30秒采样。`local/loopback-deployment-20261116/observation-launch.json`保存归属，日志为同目录`long-capture.log`，原始证据在`local/service-observations/loopback-http-24h-20261116/`。到期审原run，输出放run目录外，分别核完整性、错误、截止账本覆盖、启动来源及自然refresh；零事件不等于无丢失或自然续期。

原bridge自动化已删除，没有替代聊天定时任务。诊断采集器不是聊天自动唤醒，不承诺结束会话后Agent继续执行。观察不是独立工作的前置；必要变更必须保留中断/版本变化事实，不能假保连续。

## 尚缺的事实

普通账号、runtime/组织无关IM为主线，DWS CLI优先。文字、常用文件、图片、WAV/MP4双向原件已有实测，MP4客户端视频卡片和播放已验；语音条及独立video协议未验不能误写成音视频文件不支持。R09至少一个执行器已满足，不加四runtime全过门槛。

51通过/11阻塞/2部分，7 MUST R01/R04/R06/R07/R12/R13/R14未完整。E134既有两条组合消息的客户端呈现/发送者/AI标识/逐图保存待验，不能重发补截图；私聊入站引用需明确新原生入口。原生工具多次failedToCreateImageDestination后保持loop guard，不能换底层方式、改权限或重启绕过。Kimi两次403只限制相应模型，不重探、不重发失败任务、不换绑定绕过。真实UI恢复及自然refresh目前没有新证据。

只在AIC测试群及原私聊，禁止认证修复/真实auth或doctor/Keychain操作/复制token/加人权限。DWS固定local/bin/v1.0.67。必要维护与未知发送按AGENTS；共享bus不杀，凭据故障不自动恢复，无开机自启。

原始身份/聊天/截图/日志/DB/下载仅local。阶段事实见[E142](../../docs/142-local-http-deployment.md)、[证据](EVIDENCE.md)、[进度账本](PROGRESS_LEDGER.md)和[偏差日志](99-执行偏差日志.md)，不要照抄历史下一步。
