# 当前任务池

E126当前状态（2026-11-15）：OpenClaw官方41f2b981已在local冻结构建，65,102原文件未改；完整agent --local九样本验stdin/同session/跨state隔离/实际Python499/独占锁/取消/工具期限及终态。取消与deadline各7自有进程退出，28/13秒无late；length虽exit0仍为partial，必须核stop。冻结工具21检查20过，1个guard聚合把已阻止的build-info探测误计凭据；原exit1保留，独立离线24检查及5反例、2源固定负例通过，非重跑全量。独立HOME/state/config/cache及新profile；早期mac-control.token读取在open前被拦截，无真实凭据读取，login-shell探测仍被拦；不是OS沙箱或任意生产配置已隔离。尚未注册/迁移/部署OpenClaw，下一段薄适配及绑定/终态回归。21产品模块仍e7d82cc、最近真实部署/UI E123，原观察/Qwen已收尾不重做；49/14/1及7 MUST缺口不变。见[完整宿主证据](../../docs/127-openclaw-local-host-validation.md)。

这是唯一活动清单；[PRD](01-PRD.md)/[矩阵](ACCEPTANCE_MATRIX.md)是原判据，[路线总览](../../docs/102-user-requirements-and-roadmap.md)解释交付物。阶段历史继续留EVIDENCE/Git，不执行旧文“下一步”。

## 已完成，保留证据而不重做

- [x] 通用CLI/HTTP/consumer、多路由/显式真人身份、群显式任务/私聊白名单、持久任务/session/outbox、原件及同会话交付。
- [x] Kimi真工具；群/私聊常用文件、图片、WAV/MP4文件、长文、status/cancel/new的登记样本。E112新版群1517/TXT、私聊1003/JSON真实工具/续接/下载打开/SHA。
- [x] CEO C01摘要、C02回执、C03能力/可信终态、C04会话协议；E109部署997e9fa和原session显式迁移，E112真实UI完成。不能再写“待部署”。
- [x] E084持久history续页；E072/73防护和E108 PID/阶段调用日志已部署。E112正确cut/停机积压审查后恢复，原82任务及回执保持，新增两失败两完成分开。
- [x] E101原24h记录完整性、E106205已捕事件后续账本一致；旧故障/52维护保留，不称健康24h。
- [x] E113统一需求/产出/当前入口/风险手册/经验/CEO状态；复核#1132 closed、#60687 open、最新release v68。没有新产品/UI/健康通过项。

## P0 — 下一段必须推进

- [x] E115/E116已实现、三环境357验证并部署；两路真实Python、环境检查及下载打开通过。通用runtime启动环境配置与验证：重载后实际继承、transport/HOME/凭据不变、localhost不受外部代理影响；不固化本机端口。合成验证后部署并新任务UI，普通重启不再丢失E112所需条件。
- [x] E115/E116已实现、三环境357验证并部署；两路真实Python、环境检查及下载打开通过。DWS安全错误信封：category/reason/exit/耗时/阶段脱敏保留；对应负例与错误日志写失败验证，未知副作用不重发。不能只有笼统request_timeout。
- [x] E117官方取消缺口双层候选、15方法普通/race、18核验及上游草稿；仅合成进程，未集成/部署/发布。系统钥匙串根因仍开放，只在官方新证据出现时复核，不重复系统实验。
- [x] E124原aic-persistent-env-20261113观察自然到期，13完整性检查、32捕获事件对账及后续六库保留审计；14不可达/16错误采样/9维护保留，原run不改。
- [ ] R13自然失效refresh/长期可靠性证据及完整截止覆盖仍缺；后续快照不能追补当时事实，不用elapsed time或released声称刷新/健康已过。

## P1 — 剩余验收与封版

- [x] E119/E120 Codex原生中断、绑定迁移及真实私聊工具/续接/取消/文件UI，89旧任务保持；旧E118失败保留。
- [ ] 14 blocked和1partial逐项寻找新入口/官方能力，验引用、原生语音/video及单消息组合。没有新入口停止同路径；不得默默删除MUST。
- [x] E121当前982ae49干净导出/离线安装、六入口/许可/模板/回滚说明与683manifest通过；固定包已留。最终项目封版仍受下一项完整MUST审计约束。
- [ ] 14 MUST/64格/证据/隐私/manifest一致终审；R01/R04/R06/R07/R12/R13/R14仍未完整。全部满足才完成，不用文档数量替代用户验收。

## 独立推进和条件扩展

- [x] E120 Codex实际Python、同session、取消延迟观察、客户端下载原件打开全部通过；未重登录/改HOME/扩大timeout。
- [x] E122/E123 Pi 0.84.2按同契约接入，396×3及私聊实际Python/续接/取消/文件UI通过；图片能力未声明。
- [x] E125固定OpenClaw官方17文件，区分exec新session/local独占/Gateway远端归属，原结果函数14检查及2源码篡改负例；没有完整CLI/宿主验证。
- [x] E126 OpenClaw local完整合成宿主九样本及24离线复核：stdin/整对象JSON、同session/跨state、Python499、独占锁、取消/期限；冻结guard聚合失败及原始日志保留。
- [ ] OpenClaw薄适配：明确profile/config/state及完整UUID、终态严格核对/原生SIGINT/绑定兼容性，再按授权决定真实模型/UI；四runtime全过不是原R09新增门槛。
- [x] E124 Qwen admitted/completed与inbox/job/outbox事务边界已对照，5真实SIGKILL方法在冻结源/同wheel双Python各通过；现有实现无需重写，上游满队列/落盘失败降级不采用。
- [ ] CEO C05多宿主租约只在实际场景需要时做；当前flock不是已知缺陷。
- [ ] 办公更多流程/外部群/跨组织/流式审批保持R15–R17 SHOULD，不擅加成员/改权限或冒称已支持。

只在新AIC和原两人私聊实测；企业大群/旧群禁测。禁止auth/doctor/Keychain及自动修复，未知投递原key核对；旧查询key已消费。详细次序见[关键路径](CRITICAL_PATH.md)，正常不循环巡检/重复实验。


## E126 — OpenClaw完整本地宿主与隔离边界
- [记录](../../docs/127-openclaw-local-host-validation.md)、[证据](../../evidence/2026-11-15/openclaw-local-host-validation.json)：固定41f2b981/36文件；65,102源文件未改，local构建成功。9个CLI样本验stdin/续接/跨state、Python499/JSON、锁拒绝、SIGINT130/期限1、7自有进程及28/13秒无late、length exit0/显式partial、null原始finish规范化stop。
- 冻结21检查20过/1guard元数据误计，原exit1不改；独立24复核、5篡改反例及2源固定负例通过。全新profile避免App凭据命名空间，早期token open前被阻止；login-shell PATH探测保持拒绝，不称任意配置或OS沙箱已安全。无产品/服务/真实模型/UI变更，49/14/1及7 MUST保持。下一段薄适配/绑定和终态回归，不重跑旧观察/Qwen/UI。
