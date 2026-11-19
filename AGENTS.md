# 钉钉 bridge 工作约定

E160 的群聊、私聊已在完整回切后重新接入同一组织 OpenClaw，各有唯一执行 owner，独立 transport 核心仍为 `d444ccf`。接续前分别核宿主实际加载版本、具名消费者和路由锁。旧现场取消输入仍 `unknown`，当前严格回切会拒绝；保留该输入和 E154 旧群发送的不同账本，均不得重放。 [E160 现场与测试收据](evidence/2026-11-19/openclaw-resident-reentry-and-cancel.json)

## 工作位置和读取顺序

仅在 `/Users/veil/Projects/dingtalk-agent-bridge` 修改，核心交付保留 `codex/complete-bridge`，新阶段使用从公开 main 派生的专用分支，保留已合并的 `codex/native-agent-channel` 历史。用户2026-11-16明确要求sub agents分别实现与推进，取代旧单Agent/不派生限制：主Agent统管集成、提交和一切现场业务/维护；子Agent仅在各自/tmp冻结源码候选中实现及离线验证，不改运行产品、采集器、配置或业务数据，不递归派生。不另开产品实现、不改参考仓库。用户2026-11-17已明确要求整理文档并更新GitHub，取代旧不远程发布限制；主Agent负责同步，目标/可见性/主代码许可依用户选择，首次推送额外核历史私密材料。未授权向上游项目发issue/PR。用户已确认公开仓库`veil-chow-fyaic/dingtalk-agent-bridge`及MIT。GitHub GH007拒绝原提交邮箱；本地原分支/证据SHA保留，发布使用只改作者/提交者邮箱的等树隔离副本及映射，不关闭邮箱隐私保护或强推重写现有远端。聊天目录只是入口。先读本文件与 plans/completion 的 INIT、CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志，沿用同一[PRD](plans/completion/01-PRD.md)、[矩阵](plans/completion/ACCEPTANCE_MATRIX.md)和[最终自检](plans/completion/10-自检清单.md)。历史“下一步”不是当前指令。

当前能力见[需求与交付总览](docs/102-user-requirements-and-roadmap.md)，媒体操作见[E151 实测](docs/151-native-voice-and-image-saving.md)，全部资料见[索引](docs/INDEX.md)。现场部署、文档 HEAD 与 GitHub HEAD 分别计证。

## 产品与当前执行边界

交付runtime/组织无关的普通账号IM工具，CLI/HTTP/consumer独立，gateway可选。DWS负责身份、通讯、历史、资源、办公，bridge补路由/白名单/任务/session/幂等/原件/恢复。原R09至少一个执行器已满足；Kimi/Codex/Pi各自已验范围保留，Pi图片及内置OpenClaw CLI适配的真实模型/UI未验；E155原生通道双路文件已有真实样本，E154旧未知另记，不追加四runtime全过门槛。

优先使用官方 DWS，以用户能收发、获取、处理和播放的结果判断媒体能力。群和私聊均已实证 WAV 文件、MP4 视频卡片，以及原生语音入站和客户端播放。程序主动发音频可用 WAV 附件。独立 video 协议尚未验证。

E130群引用双向已过；E131文字＋双PNG入站原件一致，但Kimi2.1.1返回provider.auth_error 403、订阅没有Kimi Code访问权限，任务failed/runtime_terminal_missing，无工具/完成事件、结果或重做。需既有Kimi服务访问恢复的新证据才继续群模型任务；禁止登录修复/复制token/换runtime绕过，不重发E131。DWS当时ready不能否定Kimi失败，也不能把403归成DWS凭据故障。E133用户明确授权复查的一次最小请求仍为同类403，无周限额/重置时间证据；不循环探测。Kimi是可选执行器，其故障只限制对应模型任务，不阻塞通用IM通道主线。

原生语音条出站仍缺普通账号官方创建接口。E151 里两个同会话转发均只有文字占位，无音频资源和播放控件；不重复相同路径。E134 两条组合消息已在 E151 通过会话文件入口逐张保存并打开四张原图；保留 E011/E146 气泡点击失败记录。R07 原判据已有 E095 和 E017/E026 证据。任意普通多文件单气泡仍未实现。[关键路径](plans/completion/CRITICAL_PATH.md)

## 授权与身份

正常受管DWS业务和既有恢复授权保持；仅 **AIC测试群及原veil/liev私聊**，企业大群/旧群禁止。不加人、不建bot、不改权限、不再索取第二账号。测试群不是产品固定组织。

veil是原生客户端真人，liev是显式profile绑定的DWS真人；UI发送者及“通过AI发送”分别取证，[Agent]只是前缀。不跟随默认账号切换，不以显示名授权，不外推跨组织权限。群普通消息/文件只收不执行，需/agent；群文件用--files明确关联，私聊按白名单交办，自身回复不触发。未知投递只按原key对账，不换key或UI补发。

## 认证、调用与恢复

用户先前自行登录及重启后的恢复事实保留，最初系统钥匙串根因未知，不宣称根治。禁止助手执行真实auth/login/doctor、Keychain读取/锁/解锁、自动认证修复、file-DEK/reset/删凭据/复制token/改权限/重启Mac或绕系统工具限制；不索取密码或弹窗信息。正常业务沿官方凭据机制执行不等于认证修复许可。

受管调用最多两并发、90秒请求＋最多15秒清理，凭据故障持久暂停、不自动恢复。办公doc/todo/calendar/mail/drive/minutes六族同样受管；DM显式启用，群关闭。两个旧查询key dab-auth-read-20261112、dab-auth-read-fixed-20261112均已消费，不重试或换key。

共享Stream bus按身份Setsid脱组，无本实例独占退出权，不杀共享bus、不用foreground冒充消费者。现场history-only15秒；独立 transport 由原 manager 管理，新增钉钉侧车由既有 OpenClaw 宿主管理，无开机自启，不按历史PID发信号。运行器、清理守护、OpenClaw保护钩子均不是OS沙箱，不保证恶意脱组隔离或回滚外部副作用。

必要恢复先transport，gateway保持停止；同一SQLite快照watermark≥固定cut且无history_window，封新调用/排空/停transport后核积压及未知，再恢复允许的执行。last_sync.at不是覆盖。runtime更换先原生new归档、零未决、显式binding迁移，不能只改配置或手改SQLite。

## 固定版本和证据

- 官方binary固定local/bin/v1.0.67，不静默升级。CHAT_IMAGE窄补充复用固定官方认证/上传，不改原binary；PNG/JPEG≤2MiB用image，较大用file，单个输出文件20MiB。
- WAV/MP4原件可播放不替代语音条/独立video。E017拆条、E056重复file只留末项/正文互斥/最多9图计划不是组合闭环，无新证据不重跑。
- E115/E116环境与安全错误信封已部署；E117原取消候选保留；E145已完成本地完整CLI/原测试编译及跨层合成验证，未上游发布或部署。E123/E125 request_timeout缺连接细阶段，不断言DNS/TCP/代理/服务端原因，不再真实探针。
- 原reliability-20261111已由E101/E106收尾相关审计，aic-persistent-env-20261113已由E124收尾；故障、维护、版本和缺截止事实保留。旧run不重置、不重审、不用新计时掩盖失败；E028正常access预刷新及跨旧到期同步已证；无效refresh凭据恢复未证。本次原run审计结论见E150，不给旧run补造截止。
- CEO C01–C04/C06、Qwen事务映射已完成，不重复移植；C05仅实际多宿主需求再做。官方/GitHub固定来源优先，不转回本地WeCom考古；未授权不上游发issue/PR。
- E127最终423×3和E128新增3专项×3分别记证，不称426全量。E121为982ae49历史包，不重导或当当前Pi/OpenClaw交接。

## 执行与收口

找未完成且能独立推进的项实际完成；每段代码/工具/真实UI推进后继续，约45分钟落证据、准确下一步及小步本地提交。同路径两轮无新证据停止，转独立项；全部剩余项需外部条件时保持未完成，不制造巡检/重复测试/假通过。正常不变安静，仅实质里程碑、失败、完成或必要用户动作汇报。

测试按当次冻结源码/安装版本核对。API、模型工具、UI可见、客户端下载打开分别计证，审计通过不替代任务成功。失败和初审误判保留，不改旧记录追补事实。

当前说明写入总览/任务池，阶段结果追加到证据和账本，不再在多个入口叠加“历史当前状态”。更新[文档索引](docs/documentation-index.json)并运行review_documentation；verify_handoff先写manifest再核对，verify_privacy扫描暂存blob，git diff --check。账号ID、凭据、原聊天、截图、日志、数据库和下载只在local或私有工具记录，不入Git、不整包交接。

全部MUST及最终自检满足才可标完成；用户要求交接不等于完成。E135暂停是历史，E141已按用户明确指示删除全部本任务调度，由本Agent直接推进；不新建替代定时任务。调度与业务服务分开，唤醒次数、空等和离线时间不计进度。当前未完成。

E140的共用本机HTTP直连/拒绝重定向修复已于E142应用并部署为10758eb；25模块与477×3验证候选及同wheel一致。补丁只是历史交付材料，不再次应用。新观察不作为其他独立工作的前置，发生必要维护时如实记中断，不能保计时而搁置已完成修复。

E141维护工具：prepare_history_deployment.py --allow-empty-wal只允许WAL不存在/严格0字节及遗留SHM；必须原owner锁/operator_suspended，非空WAL或任何journal仍拒绝，不能删旁文件绕过。不再把历史“需要新授权”字符串当作重复索取本会话已有许可的理由。工具不执行部署，现场停止/排空/cut/积压顺序仍按上文。

E144配置候选与E149 HTTP启动修复已随E150合入部署，不再次应用补丁。R12资料/R14 Git隐私检出按原判据已经通过，R01部署收口；原24h run已完成一次审计，不重置/重审。

E150历史部署为0e151fb/25模块；E156 的核心部署与 E159 新增宿主侧车分别按收据登记，后续文档提交不冒充运行产品。公开发布保留本地原SHA与只改邮箱的等树映射；受保护main走PR和四检查，不强推/跳过保护，GitHub测试合并SHA、实际mainSHA与现场部署分别记录。公开贡献者在自己的clone工作，本文件绝对路径/现场身份仅原维护workspace适用。
