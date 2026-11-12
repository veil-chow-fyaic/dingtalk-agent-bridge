# 需求回顾与当前真实进度

> E100/E101最新检查点：群长文双向、上下文/status/cancel/new完成真实UI与21项只读核验；49/64通过、14blocked、1partial，7 MUST未完整。两个gateway已加载E099/e27547b，transport保持E093身份；冻结源码/双Python各299项是E099原验证。原24h记录完整但有1059 unavailable/168 poll_error，不能称连续健康。下一步CEO C02发送事实负例对照，C03/C04契约与余下UI缺口继续；心跳PAUSED、三服务运行。 见[本轮闭环](104-aic-group-long-text-and-controls.md)。下文旧阶段记录只代表当时版本。

E097已完整复盘全部用户输入，当前总入口为[需求/进度/路线](102-user-requirements-and-roadmap.md)与[CEO深挖](references/ceo-deep-dive.md)。下列是部署/验收摘要；活动次序见关键路径。

用户要把钉钉作为本地Agent的群聊/私聊工作入口，承接任务、文件、多轮补充和结果交付，并有可复用的官方能力/自研边界、开通经验、验证和Git历史。通用IM层不绑定组织或runtime，Kimi已满足至少一个本地执行器；不是要求新建bot或一整套管理平台。

E095用户完成新终端登录并提供截图，群范围限定新AIC测试群；原私聊继续、企业大群禁测。三服务已用E093冻结产品恢复，history-only，心跳仍PAUSED。当前真实群TXT/CSV与私聊JSON闭环见[docs/100](100-aic-group-resume-and-files.md)。认证事故及执行错误继续保留，不把本次恢复写成跨设备根治。
| 目标 | 已有范围 | 仍缺/限制 |
|---|---|---|
| 身份与通用接口 | 真人veil交办、真人liev经DWS回复/AI标识；CLI/HTTP/consumer、多路由隔离 | 仅新AIC测试群获准，企业大群禁测；外部/bot无现场结论 |
| 任务与执行器 | Kimi实际Read/Write/Bash、多轮、同会话文件交付 | Codex超时独立跟踪；不是OS沙箱 |
| 文件与媒体 | PDF/DOCX/XLSX/ZIP历史四方向；私聊TXT/CSV、PNG/JPEG、WAV/MP4文件、下载打开 | E095群TXT入站/CSV双向补齐；群新媒体；原生语音/独立video不能用文件替代 |
| 文字、引用、组合 | 私聊长气泡、出站引用、单条两PNG、分条文件合并 | 群长文/引用、私聊入站引用、其他单条多附件；旧入口loop guard保持 |
| 控制与恢复 | 私聊status/cancel/new、真实取消/运行器崩溃清理/超时、未知不重做；限定网络/下载故障恢复 | 群控制、长期认证、完整观察/失败处置未完成；旧失败不被新绿抹除 |
| 官方工具与补充 | 官方身份/通讯/历史/资源/办公；仅图片上传明确缺口作薄补充，E073办公入口受管 | 共享Stream bus无独占退出依据；已部署history-only，不运行Stream消费者 |
| 安装与证据 | E093源码/双Python各291、21模块；E095部署相同产品，22只读核验；E075仅历史交接 | 最终封版/完整验收未做；未远程发布 |

当前[矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)64格中41通过、22阻塞、1部分；14 MUST中6已覆盖、5部分、3未完成。[声明核对工具](91-acceptance-coverage-review.md)检查缺失/重复/等级/引用，不证明私有UI证据或当前健康。原始判据和逐格内容保持，不能用测试数量掩盖缺口。

普通账号路线保持明确：显式profile绑定liev（--as只用于具体声明该参数的命令），`[Agent]`只是文本前缀，没有创建独立bot。官方bot/dev connect/OpenClaw/数字员工另列研究；不把同组织两账号结果外推任意外部类型。最新授权仅新AIC测试群和veil/liev私聊；旧企业群退出活动配置，不再以第二账号或旧恢复许可停工。

官方v1.0.67固定，旧全局版本保留；E066新版调查已有结果，不重复同类探针。图片原生上限2MiB、文件输出20MiB与WAV/MP4 file协议限制均保留。官方办公仅DM显式启用，群关闭；doc/todo/calendar/draft、个人钉盘、合成听记有代表性真实证据，不等于所有办公权限或密送/外部/独立会议通过。

原reliability-20261111起点11月11日19:36:08，所有实际失败及维护原样保留；最早11月12日19:36:08后评估真实24h。时长届满不等于连续健康；不重置样本，也不通过改token/时钟/撤授权造故障。

[PRD](../plans/completion/01-PRD.md)维持原MUST/SHOULD；[关键路径](../plans/completion/CRITICAL_PATH.md)决定下一步，完整细节见[证据台账](../plans/completion/EVIDENCE.md)。旧状态原文按字节[存档](history/through-E076/README.md)，不得执行其中过时的认证或启动步骤。
