# DWS风险、已验证处置与未解决根因

E150当前产品0e151fb、固定DWS v1.0.67。原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。 原Keychain直接失败点和保护层已定位，永久根因仍未知；E146临时截图目录ENOENT修复是独立UI问题。详见[本次结果](150-native-voice-and-acceptance-scope.md)。

**结论：尚未找到本机最初系统钥匙串故障的确定根因和永久修复。已查到失败层级、一个独立可复现的官方取消缺口，并部署了防止故障扩散的bridge防护；用户重新登录/重启后业务恢复已实测。恢复、止损、根因修复是三个不同结论。**

## 逐项区分原因与方案

| ID / 现象 | 已确认与仍未知 | 已做且验证过 | 尚需完成的解决方案与关闭条件 |
|---|---|---|---|
| D01 macOS密钥读取exit51，auth login拒绝覆盖旧槽 | E094系统日志：屏幕密码解锁成功后SecKeychainLogin=-25293，发生在DWS业务API前，普通终端也失败。CUA Guardian同期出现是相关性，最终触发原因未知 | 用户新终端登录成功；后来用户重启/重登，E112两路实际任务恢复。不是受控对照，不能确定哪一步修了哪个组件 | 保留系统钥匙串，停止主动锁/解锁实验。跟踪上游确认及明确修复版本；只有对本机问题适用的修复证据和后续实际运行才能收口。隔离执行主机是待设计备选，未实施/未证能根治；不无限重复本机诊断 |
| D02 官方等待超时不取消底层keyring调用 | 固定v67 worker只超时返回；依赖用无context的exec.Command。E094合成子进程复现“外层返回、内层仍活”。default-keychain预检查还在超时范围外 | bridge E072/73/E108受管调用、两并发、有限请求/清理、持久暂停、归属日志已部署；不杀共享bus | 上游修复应把deadline传至实际子进程、覆盖预检查、取消后回收并安全保留错误分类。E117原双层候选保留；E145已补相对依赖接线、原测试签名迁移、完整CLI/原测试编译、17+5方法普通/race验证。仍是本地候选、未发布依赖或替换官方CLI；本轮主源Darwin文件与v67同字节。外层防护不能撤销系统已排队的窗口 |
| D03 access token自动刷新 | 官方说明access约2h、refresh约30d，v67提前5分钟刷新。#1132确有多槽位失配缺陷，维护者称v62修复；不能将其套作本机-25293原因 | E028曾观察自然预刷新及跨旧到期同步。v61/v67均已核双锁/组织镜像/legacy fallback；没有“v61完全无修复”结论 | E028正常access自动预刷新及跨旧到期同步已经证明；无效refresh凭据的恢复仍未证，两者分别记录，不新增后者为原R13强制门槛。只用业务自然运行及可安全取得的既有脱敏元数据，不读/打印token；无法证明轮换时写unknown。没有“每日必须登录”的设计要求 |
| D04 终端v61与服务v67混用 | 版本差异是真实的，是否造成这次事故未知 | 项目固定v1.0.67及显式profile；未覆盖用户全局CLI | 建立统一入口/版本矩阵；升级先隔离比契约/摘要，再受管部署和UI，不承诺升级即修好。新设备独立官方登录，绝不复制本机token |
| D05 bridge持久暂停dws_process_interrupted | 直接触发是无主active调用槽。E107最初中断来源因旧日志无PID/阶段而未知；E112重启前history未release可追溯 | E108记录attempt/PID/操作/阶段；E112保留残留和原账本，核无主再显式resume、补读、审查后恢复 | 暂停是防重放保护，不是登录失效证据。E115/E116已补安全错误信封，86旧任务/回执不重放；更长窗口及故障恢复证据继续积累。缺失的旧原因不事后编造 |
| D06 事故弹窗被我们放大 | 当时未先隔离后台调用，又安排锁定/解锁；处置错误，不能归咎用户 | 相关操作停用；办公和通讯共同走受管暂停，不再反复要求密码 | 不使用login/doctor作为高频健康检查，不自动解除暂停，不照社区评论停系统守护/绕权限；同一路径两轮无新证据就停止 |
| D07 Kimi OAuth端点连接超时 | E112两任务在auth.kimi.com连接失败，DWS仍能收任务/回失败通知。现有系统代理与gateway环境不同；独立Python可达不能证明Kimi网络栈可达 | 两空闲gateway继承本机已有代理后，新两路真实工具/文件/UI成功，原两失败保持 | E115/E116已完成runtime.environment持久配置及无代理manager重启、真实工具env_ready=true/两路下载UI。有效样本不等于唯一根因，更不是DWS auth修复 |
| D08 DWS conversation-info request_timeout | E112启动首读约3.87s失败，只有reason/traceback，未保存结构化错误信封；网络/上游deadline/其他原因尚不能分清 | 新的无凭据网络证据后，同目标受管业务读约1.14s成功，再进行有界恢复；原失败保留 | E115已实现安全category/reason/exit/耗时/阶段，合成错误和写日志失败已验；E116真实58个正常result已落日志。原E112缺失信封不可补造，后续真实失败再归因，不反复重启 |
| D10 Kimi Code服务访问403 | E131 Kimi2.1.1 stderr为provider.auth_error 403，明确订阅无Kimi Code访问权限；stdout只有版本事件。DWS同期ready/同步完成，两条反馈confirmed | 群双PNG原件已物化，任务failed/runtime_terminal_missing，无工具/结果文件/重做；32只读审计及5负例保留失败 | 需既有Kimi服务访问恢复的新证据；不登录修复/复制token/换runtime绕过，不重发E131。E133最小请求仍同类403，无周限额/重置时间；只影响对应模型任务，不阻塞IM通道工作。不是DWS凭据故障，也不是已证网络超时根因 |
| D09 UI failedToCreateImageDestination | E146系统ImageIO日志为截图临时目标ENOENT，实查目标目录缺失；目录为何消失未知，不能归因Keychain | 仅创建缺失目录且mode0700；未改既有权限或重启。11:08:55原getApp成功，后续AX/点击/滚动/截图成功；E133/E134/E141/E145旧失败保留 | 本次原生入口已恢复，不称永久根治；组合完整图文/身份可见与逐图保存分开，保存重复E011三点击失败后停止；不把UI问题与DWS凭据问题混同 |

E118 Codex取消迟到写入是保留的历史失败，不能归因DWS/auth；E119原生SIGINT修复及E120真实延迟验收已完成，见[修复](120-codex-native-interrupt.md)与[UI](121-codex-deployment-and-ui.md)。随后原私聊经new归档/显式绑定迁至Pi，不能继续执行旧“回滚Kimi/等待修复”指令。CLI组cleanup_complete仍不保证任意恶意脱组工具已停。

D01直接故障点已定位但根因未定，D02是已复现未上游修复的独立缺口，D05包含已修观察/恢复不足，D07已有持久配置及重启UI证据，但原唯一因果仍未知。它们不是“每天同一个DWS崩溃”。本次长期观察的完整性、错误和恢复分别见E150；不保证上游永不出错。

## 官方与社区证据怎么用

- [官方认证参考](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/skills/mono/references/global-reference.md)、[提前刷新实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/auth/token.go#L247)：期限与续期机制不是“保证每个环境都不出错”。
- [DWS #1132维护者结论](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1132#issuecomment-5762379764)：E113核对时closed。原报告为Windows、自建应用direct模式；修复含组织槽回退/同步及legacy全局槽。不能照抄用户评论中的复制token方案，也不能仅凭v62数字反推v61源码没有相关分支。
- [DWS #476](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/476#issuecomment-5762849801)：完整OAuth与access-only登录需要区分；不是所有2小时失败都一个病因。
- [Codex #60687](https://github.com/openai/codex/issues/60687)：E113核对时open，症状与本机日志吻合；唯一社区评论的“根因已定”不是官方确认，不采纳其系统操作建议。
- [PR #1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)：无法安全判断的旧登录态拒绝覆盖是保护行为，不应先reset绕过去。
- [官方Darwin源码](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/keychain/keychain_darwin.go)、[go-keyring v0.2.8](https://github.com/zalando/go-keyring/blob/v0.2.8/keyring_darwin.go)：D02的固定来源；[合成复现](../evidence/2026-11-12/dws-keychain-timeout-probe_test.go)2项通过/1helper跳过仅证明缺陷被复现，非修复通过。
- E129固定核对的稳定release为[v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)。E111固定差异审查未发现internal/auth及Darwin文件修改，不承诺升级解决D01/D02，本次不升级。
- [Kimi官方环境说明](https://www.kimi.com/code/docs/kimi-code-cli/configuration/env-vars.html)、[相近网络报告](https://github.com/MoonshotAI/kimi-cli/issues/2650)：环境变量是可核的线索，社区相似症状不等于本机确诊。

更详细的原始诊断/时间线：[E094](99-dws-base-failure-diagnosis.md)、[E111](112-dws-refresh-and-reboot-review.md)、[E112](113-reboot-recovery-and-runtime-network.md)。历史停机或待许可段落只描述当时状态，不是当前操作命令。

## 可复用的故障处置顺序

1. **判层**：进程停止、guard暂停、DWS业务错误、runtime错误、UI工具错误分别记录。先读已有本地账本/日志，不先启动auth/doctor或请求密码；manager running、HTTP healthy、released都不等于任务送达。
2. **止损**：凭据存储失败、受管DWS进程90秒超时、进程中断/无主占位、清理不完整或准入状态损坏触发guard持久暂停，不能自动解除。API `request_timeout`等普通业务错误不等于guard暂停；guard仍ready时允许原history轮询继续，后续成功可清除poll_error，不需为此执行resume。只通过原manager和进程归属处理本实例；禁止杀共享bus，禁止绕过系统/工具限制。发送结果不明保持原key，不能换key或UI补发。
3. **留证**：安全保存版本、时间、操作类别、阶段、错误分类、原投递/任务状态。原始数据只留local。若旧记录缺字段，明确缺失，不凭mtime或退出码猜原因。
4. **有依据再恢复**：用户已授权正常恢复范围，不重复索要旧许可；系统/凭据修改不在其中。若出现同一凭据故障，不用恢复授权扩大成认证修复。正常恢复先transport，gateway停机；同一SQLite快照满足watermark≥固定cut且无history_window，封新调用并排空在途后停transport、核积压及未知投递，再恢复允许的gateway。
5. **验证用户结果**：新且明确的合成任务，查实际工具、同会话回复、客户端下载打开及摘要；旧失败不重做。再观察真实时间，记录维护和故障，不能成功一次就标根治。

新设备从官方支持的独立登录开始，记录OS/DWS/runtime版本、网络环境、组织开通及精确身份/会话，再在专用测试范围验收。尚无跨设备证据，不能保证不会复发；本机代理配置和测试群不得变成产品默认值。

## 待实施、可审查的修复工作

- **本项目已完成E115/E116**：runtime环境持久配置、安全DWS错误信封及针对验证，已部署并经群/私聊真实工具和下载UI验收。[实现](115-runtime-environment-and-dws-diagnostics.md)、[部署](116-persistent-environment-deployment-ui.md)。E124已收尾原AIC观察，故障/维护/缺截止保留；不把两项实现等同底层根治或持续健康。
- **官方DWS取消缺口**：基于固定源码做最小候选/合成回归，覆盖预检查、实际子进程取消、回收和错误传播；不运行真实Keychain。可形成上游报告草稿，包含固定版本、已公开复现及预期行为；未经用户指示不发布issue/PR。E117已完成[双层候选与合成回归](117-dws-cancellation-candidate.md)及[报告草稿](118-dws-cancellation-upstream-draft.md)；E145已完成本地完整源码集成及构建/合成验证，未发布上游或部署；不称D01已修复。
- **系统钥匙串根因**：追踪#60687及相关官方发布说明；只在新证据出现时更新结论，不继续本机锁屏/钥匙串复现实验。若长期部署确需环境隔离，先提出具体受支持方案与成本，独立设备验收后才称有效。
- **运行验收**：R13证据分别记录版本、维护、调用错误、正常续期与无效refresh未知项、同次截止账本；旧reliability-20261111及aic-persistent-env-20261113均已结束并保持原样，不能重置/重审或补造截止。主动破坏refresh凭据不是必要验证手段，无法安全取得的真实失效证据继续记未知，不混同已证的正常续期或增加原判据。

文档中的“已修复”必须指具体缺陷、产品版本和验证；“已恢复”只描述当次运行；“未知”要带下一条能改变判断的证据。没有这三项，不能向用户承诺底层已解决。

## E120新增实际故障分类

0c6f2da部署首次conversation-info返回category=api、reason=request_timeout、stage=request、exit=1、耗时3870ms、providerExecutionStarted=false。三服务未启动成功，未发UI任务；原失败保留。相同网络配置下显式一次有界恢复成功，随后9新回复confirmed/history及真实UI通过。没有认证错误证据，不能将这次故障归因为授权自动过期或Keychain；也不能以恢复成功证明网络/官方服务根因。原D01保持未知，未执行真实auth/doctor/Keychain操作。

## E123重复出现的请求期限错误

本次首启仍为api/request_timeout、stage=request、exit1，3872ms，未开始provider执行；无凭据TLS两官方域名成功，环境网络变量均空，一次有界分阶段恢复后UI通过。固定v67 transport/client.go将该reason映射自context.DeadlineExceeded，并有默认3秒DialContext；耗时只是线索，缺具体连接阶段证据，尚不能定为TCP/DNS/代理或服务端。没有认证错误，也没有通过改超时或Keychain止损。下次仅按新阶段证据收敛，原D01/D08未关闭。[本次证据](124-pi-deployment-and-ui.md)。

## E125/E129后仍不能定位连接细阶段

E125只整理既有窗口内40次、窗口后30次同类request_timeout，仍未给出DNS/TCP/代理/服务端细阶段；E129固定main 4cc7767c相对c4be030e的14提交/23文件无相关细阶段变化。固定chat原文请求25秒0字节超时未算已读。没有新证据不重复真实探针，也不把D10模型服务访问拒绝混入DWS故障统计。原始日志仅local，具体登记见[E125](126-openclaw-turn-entry-contract.md)、[E129](130-dws-entry-delta-review.md)、[E131](132-group-multi-image-and-provider-denial.md)。
