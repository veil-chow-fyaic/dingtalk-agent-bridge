# 钉钉 bridge 工作约定

## 同一项目与续作入口

只在`/Users/veil/Projects/dingtalk-agent-bridge`修改本项目，复用`codex/complete-bridge`，单Agent，不自行派子Agent、不另开实现或改参考仓库。聊天目录仅为入口。先读`plans/completion/`的CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志；验收以01-PRD和ACCEPTANCE_MATRIX为准。历史入口已[按字节归档](docs/history/through-E076/README.md)，旧“下一步”不是当前指令。

交付runtime/组织无关的普通账号IM工具：群聊/私聊收发、任务、上下文、原件与同会话交付。官方DWS负责身份、通讯、资源和办公；bridge补路由、白名单、任务、会话、幂等及恢复。至少一个本地执行器即可；Kimi真实Read/Write/Bash已满足，Codex超时独立跟踪。不要把测试群写成产品固定组织。

## 当前停机约束与待决许可

E071事故后用户已确认弹窗停止，要求回到主线；三个真实服务停止，工作区operator_suspended保持。禁止真实DWS/auth/doctor/Keychain读取、锁定或解锁、自动恢复；禁止file-DEK、reset、删凭据、复制token、改权限、重启Mac，以及绕过SecurityAgent/Terminal工具限制。不再等待弹窗名称、第二账号或系统密码，也不重复让用户输密码。

E082：用户已明确允许并执行原key `dab-auth-read-20261112`的一次查询；官方因不支持脚本强加的`--as`返回validation/unknown_flag、退出3，receipt为failed且attempted=true。这是命令准备错误，认证是否恢复仍未知；三个服务和operator_suspended保持。原key已消耗，禁止重试/换key/删receipt，不能把一次许可扩成修正后再查或后台恢复。当前不再等待这次许可答复，也不再执行docs/90旧准备命令；先离线修官方参数契约，再说明具体方案，任何新真实调用或后台恢复均需明确允许。详见[失败与边界](docs/94-single-read-unsupported-flag.md)。

E089：用户已明确允许追加一次及新记录dab-auth-read-fixed-20261112，核冻结提案后执行1次，官方exit0/targetMatched/readable，暂停未变且三个服务仍停止。此次许可已履行，不再待答复；两个key都禁止重试/覆盖/换key。一次凭据读取可用不等于auth login已解决、后台或所有API恢复。E090私聊恢复方案（docs/97）仍未授权；用户的回复要求先讲清主线、DWS边界、群验收、认证原因及现成channel，不是允许启动，也不是未收到答复。E091已核一手资料并写入docs/98；不重复催问，不再新增等待许可的审批/巡检工具。不能写活动配置、resume或启动服务。

E091复用决策：Qwen Code官方DWS channel是普通账号群/私聊的主要设计参考，源码已核；它的附件契约、队列丢弃和长文截断不能直接替代本项目原件交付与保留失败记录。DWS dev connect及钉钉官方OpenClaw connector属于bot路线；社区dws-codex-bridge为数字员工/指定群且UNLICENSED，不直接复制。保留当前runtime通用实现，只补明确产品缺口；不将基础通讯能力已通等同于全体验收。心跳当前PAUSED，保持该状态。

E072持久暂停/最多两调用/进程守护、E073办公入口防护及E074history双路方案已离线验证，尚未部署。官方Stream bus按身份共享且Setsid脱组，不能杀共享bus；foreground只运行bus，不能当消费修复。候选恢复用既有history-only、15秒补读，实际配置仍stream_hint、尚未改动。当前包装器不是OS沙箱，不能覆盖恶意脱组、守护本身被杀或系统失效。

## 身份与范围

liev是由显式DWS profile绑定的真人普通账号，veil为客户端真人测试用户；界面显示liev和“通过AI发送”，`[Agent]`是文本前缀，没有创建bot。原veil/liev私聊授权保持。历史曾明确允许原3人群测试；当前聊天工作区指令要求多人实测暂跳过，因此新增多人群测试暂跳过，后续按最新用户指示与账本核对，不能拿旧范围盖过最新限制。没有缺第二账号的问题。

合成文字、文件、任务及下载打开仅在当前授权测试范围。两路绑定准确profile、selfSenderId与发送者白名单，不跟随默认账号切换。群普通消息只收不执行，群任务需`/agent`，私聊白名单文字/附件可交办；自身回复不触发。E070群文件显式关联已提交但未部署/UI未验。旧周威/legacy账本原位保留；组织、身份和runtime都是配置。不加第三人、不扩全组织监听、不建bot、不改成员/权限、不远程发布。

## 固定边界与证据

- 固定官方v1.0.67在local/bin/v1.0.67，全局v1.0.61保留。E066已核v1.0.68没有已证钥匙串/图片缺口修复，不重做同类调查或静默升级。
- 图片补充仅填明确的本地CHAT_IMAGE上传缺口，复用固定官方源码鉴权/上传，不改原版binary。PNG/JPEG≤2MiB走image，更大走file；bridge输出单文件20MiB。WAV/MP4原件文件和MP4客户端播放不能代替语音条/独立video。
- E056固定发送契约已验：重复file只取末项、正文与file互斥、图文最多9个本地引用（并发3）；计划/压缩显示不等于原件UI。无新入口不重跑旧探针。
- DM显式启用官方办公上下文，群关闭；E073六类doc/todo/calendar/mail/drive/minutes走同一暂停与守护，身份参数固定。既有会话旧上下文需要恢复时核对，不冒称已迁移。官方bot/dev connect/OpenClaw/数字员工是另一路线。
- 本机传输固定127.0.0.1:18768；三进程由service_manager归属管理，旧ctl/PID文件不控制当前部署，无开机自启。不能凭历史PID发信号。
- 原run=reliability-20261111起点11月11日19:36:08，历史观察PID97881仅作归属核对线索；不得删除、重置或覆盖原样本。最早11月12日19:36:08后按真实样本终检，全部故障/维护保留；满24h不等于连续健康。E028自然预刷新不是失效refresh恢复，不改token/时钟或撤授权造故障。
- E027/E039/E059未观察到根因的历史manager失败保留；E062只修有证据的TERM后同启动时间E退出过渡。不重复限定循环，只有新失败时读同次私有诊断；全量测试使用run_tests_with_evidence.py。

## 执行与完成

每段实际推进代码、工具或真实验收；每约45分钟记录实质进展和精确下一步。完成一段继续独立项；同一路径两轮无新证据触发loop guard，停止重复。入站引用旧右键/坐标/快捷键/设置/侧按钮路径已停止，只有明确新入口才再试。用户未答复不等于许可，不靠巡检或重做已过测试凑进展。

已有实验只读复核。未知投递先按原key对账，不换key或UI补发；已确认实验不重放，历史failed/blocked/cancelled/rejected及错误结论不删除。API、工具执行、UI可见、客户端下载打开分别计证，模拟/测试数量不能代替UI。平台不支持或未知如实保留，不自动改绿。

修复有对应验证，按功能和验收小步本地提交。安装验证核冻结源码、wheel和当次测试，不拿HEAD混比旧证据；文档变更以链接/摘要/隐私验证为主，不重复无关全量。更新manifest后只读复核；verify_privacy扫描暂存blob。账号ID、凭据、原聊天/截图/AX、数据库、日志与下载件只留local，不能整包交接或公开。

当前E084已应用E080续页core/8方法并保留E083参数修复；源码/双Python新wheel实际各262项、六入口21模块/10审计通过，未部署。E083254与E080候选259保持历史版本。E074244/E076工具5专项等保持历史范围，不混加测试数。E075固定f0d2911交接包保持历史版本。E076声明核对为37/64格历史通过、27格未完整通过，14 MUST仍9项未完整覆盖；不等于独立审查了全部原证据。

只有MUST/UI与完整自检、真实观察和失败处置均满足才标完成并停heartbeat。当前未完成；SHOULD保持原级别。正常未变安静，只有实质里程碑、失败、完成或必要用户动作汇报。
