# 钉钉 bridge 当前接手入口

2026-11-16 E143：三个子Agent完成可靠性、消息消费和可复用交付候选，主Agent审查后统一部署产品2b479a8。25模块及实际配置启动来源、三服务/CLI/60秒实际采集通过，原99任务/240 Agent outbox/session/绑定保持。最终冻结源码及同wheel独立安装Python3.14/3.11各504方法通过，早先失败与测试契约修正保留。新run `parallel-hardening-24h-20261116` 固定北京时间2026-11-17 18:29:37截止，只有本地证据采集；聊天定时任务仍已删除。原loopback-http run主动中止、未满24h，不能合并计时或算通过。

用户已明确要求sub agents分工，取代旧单Agent条款；主Agent统一集成、提交和现场操作。仅复用原项目`/Users/veil/Projects/dingtalk-agent-bridge`与`codex/complete-bridge`，不重写、不远程发布、不安排聊天定时任务。先读[AGENTS](../../AGENTS.md)、[当前任务](CURRENT_MISSION.md)、[关键路径](CRITICAL_PATH.md)、[TODO](TODO.md)；产品初衷与实际能力见[总览](../../docs/102-user-requirements-and-roadmap.md)，原[PRD](01-PRD.md)/[矩阵](ACCEPTANCE_MATRIX.md)/[最终自检](10-自检清单.md)保持。

实际部署产品`2b479a891833c21c7e03c389f92a4a77ce3ee366`，25模块与E143冻结源码/同wheel一致，源码Python3.14及安装Python3.14/3.11各504通过。首次并行三组失败、首次串行源一项提前timeout均保留；修正一个CLI-exit清理测试场景（10秒安全上限、30秒子进程寿命防自然退出假过），真正0.3/2/4秒deadline用例及产品策略不改。文档HEAD不是部署产品版本。

E143实际受管维护、通用空WAL审查、固定cut同SQLite快照覆盖、封停积压审查及恢复完成。99任务/240 Agent outbox/session/配置/群Kimi与私聊Pi绑定保留；无新模型或业务消息。新CLI/启动来源及60秒12样本零错误、截止/seal通过，不等于24h或自然续期通过。

当前私有阶段：`local/parallel-hardening-20261116/`，含agent-reviews、validation、部署前后六库/审查、短采集、最终核对及bundle。通用导出入口`scripts/export_release.py`，用法见[说明](../../docs/144-offline-release-export.md)。不要执行历史local部署脚本来巡检，不重用已消费key。

旧`loopback-http-24h-20261116`主动中止：1.106小时/133采样，signal退出，记录1次DWSBusinessError；原时间/seal不改，未满24h。审查在新阶段`interrupted-observation-review.json`，不写回旧run。更早startup-provenance的1.82小时/218样本中断同样保留。

新`parallel-hardening-24h-20261116`于北京时间2026-11-16 18:29:37开始、固定2026-11-17 18:29:37截止，间隔30秒。归属在新阶段`observation-launch.json`，日志`long-capture.log`，原证据在`local/service-observations/parallel-hardening-24h-20261116/`。到期审原run，输出放run外；分别核完整性、错误、固定cut账本、来源和自然refresh。无聊天自动唤醒，不承诺结束会话后Agent自行执行；必要变更保留中断事实，不能重置计时掩盖。

核心文字、常用文件、图片、WAV/MP4双向已验，MP4客户端卡片/播放已验。语音条/独立video未验不能误报成音视频文件不支持；DWS优先，不只为协议名字另造实现。CLI/HTTP/consumer独立，gateway可选；R09至少一个执行器已满足。

51/11/2、7 MUST R01/R04/R06/R07/R12/R13/R14仍未完整。E134既有两条组合客户端呈现/发送者/AI标识/逐图保存仍缺，不能重发；私聊入站引用需新原生入口。UI多轮failedToCreateImageDestination后不重试或换底层绕过。Kimi两次403不重探、不重发、不换绑定绕过；只限制对应执行器。认证、群范围、固定DWS、未知发送/维护和隐私边界按AGENTS。

阶段事实见[E143](../../docs/143-parallel-hardening.md)、[证据](EVIDENCE.md)、[账本](PROGRESS_LEDGER.md)、[偏差日志](99-执行偏差日志.md)。历史停止/调度/单Agent指令不覆盖用户最新授权。
