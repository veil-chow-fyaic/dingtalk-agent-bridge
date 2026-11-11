# 项目工作约定

当前交付目标：通用钉钉IM工具＋真实本地Agent接入，群聊/私聊交办任务、附件、多轮上下文和结果交付；不绑定组织或runtime。先读README、plans/completion/INIT.md与CURRENT_MISSION.md及当前状态文件、docs/43（history网络恢复）、42（长气泡UI）、41（官方办公接入及真实私聊任务）、40（当前进程管理器）、17（总状态）、13（摘要）、25（官方边界）、15（运维）；其他阶段文档按任务索引读取。docs/07、14、16、23、24、26中的历史数量和部署不要当当前配置。

## 最新授权与真实部署（2026-11-11）

用户明确将DWS授权改为liev，客户端登录veil（当前组织显示周威），授权用veil向liev发私聊和原群任务、查看liev回复。旧“单人群/跳过私聊与多人”限制已被这次明确授权替代；仍仅限这两个指定账号、原群及其私聊，不扩成全组织/任意业务联系人。用户自己添加liev和群成员，助手未邀请/审批。

当前发送主体liev真人账号，DWS --as user，非bot。[Agent]仅文字前缀，客户端左侧显示liev回复和“通过AI发送”。DWS默认profile切换不会覆盖bridge显式绑定；不能静默跟随默认账号。两个活跃路由均精确指定liev profile，selfSenderId/允许veil的sender ID按当前上下文重新解析并以实际收发核验。

本轮通过真实UI输入/发文件：群667与TXT；私聊697与TXT、多轮蓝鲸482；CSV上传后合计54及TXT。三个TXT均客户端下载、TextEdit打开且SHA-256与生成件一致；群普通消息不执行、回复无循环、群私聊原生session分开。5任务（群1/私聊4）、14确认投递、70事件快照；只上传附件会单独触发任务，后续文字另一个任务。UI有些任务已回复但原消息仍未读，不能将DWS读取当已读回执。73项自动测试与UI证据分层。

真实配置local/service-config.json含两个liev路由，各自新状态目录。原周威单群配置备份local/ui-two-account-20261111/previous-*.json，旧legacy账本原位保留且不再激活；禁止将旧stateStorage=legacy迁到新profile。新gateway initialCursor仅初始化全新consumer一次（群49/私聊1），重启持久cursor优先，不回放旧任务。

127.0.0.1:18768传输服务，两路已启用stream_hint唤醒history，15秒定时补读兜底（docs/29）。群gateway local/agent-config.json；私聊gateway local/agent-direct-config.json。当前三个进程由dingtalk_bridge.service_manager管理，status只读；start须显式选入两个--agent-config，旧*_ctl.py/PID文件不再管理当前进程（docs/40）。均仅允许veil且allowSelfCommands=false。无开机自启。实际runtime是已登录Kimi；Codex CLI已登录但真实请求超时，adapter保留。Kimi工作区提示词不是OS沙箱，不能开放任意成员执行。E021仅私聊启用officialDwsTools，群仍关闭；上下文不授予额外写权限。

## 证据、身份和资料边界

必须从钉钉客户端UI发任务、看可见回复、下载打开文件。API成功、历史回读、单元测试不能冒充用户侧验收。当前双账号UI证据见docs/27，原单账号UI历史见docs/26。local/ui-two-account-20261111和local/ui-acceptance-20261111的原始截图含私人侧栏，仅本机保存，不纳入共享manifest。令牌、OAuth、账号配置、签名URL、未筛选业务消息也只放local/。

固定实验DWS v1.0.67在local/bin/v1.0.67，保留全局v1.0.61。官方优先：DWS负责身份/权限/profile、聊天/历史/资源、办公API；自研补普通账号任务队列、会话、白名单、文件、幂等和恢复。官方已有dev connect机器人到本地Agent、OpenClaw Connector，不再声称bot接入全须自研。没有创建bot。

普通账号覆盖外部业务的动机保留；bot类型需独立调查，不照搬企微规则。官方契约、源码、上游报告、服务端实测、UI、独立对端分层。Stream ready不等于业务入站，file不等于原生音视频，用户读取不等于标记已读。当前未通过：Codex实际执行、原生音视频、完整Stream网络中断/授权过期恢复（history HTTP故障补漏已过E023）、bot/外部客户UI、完整办公接入、24/72h可靠性、恶意隔离。

## 持续工作规则

在本项目修改代码资料，不修改参考/Users/veil/Projects/wecom-bridge或复制其他项目账号数据。本地Git已初始化，分支codex/complete-bridge，基线166b11b/tag baseline/ui-2026-11-11；未发布远程。pre-commit运行暂存内容隐私检查和handoff核验。活动执行计划只有plans/completion，docs/13为摘要。

实测用DAB标记和稳定幂等键；未知先对账，不换key或切AX重发。已完成写入实验不重放，复核优先scripts/accept_media_matrix.py（只读）；accept_two_account_ui.py是此前基线的全量任务审计，新发现保留的blocked会令其all_jobs_completed为false，不能删除失败来变绿。共享交接scripts/verify_handoff.py；更新后显式--write-manifest并再次核验。单元回归和UI验收都需真实结果，不用文件数量或测试数量代替完成。

继续独立推进，不把阶段汇报当停工理由。不要重新索取已经授予的这两个账号测试权限；真实外部依赖如实记录，不能称全项目或所有情形均完成。

## 2026-11-11 19:05续跑检查点
PNG/PDF群/私聊双向8案例、10资源摘要一致；私聊PDF客户端下载并Quick Look打开。真实有限Stream捕获群5/私聊11事件，全部匹配history、无重复，退出码0；这不是常驻服务已启用Stream（当前仍history）。真人PNG的双资源别名曾使一条DM任务blocked；已以下载SHA相同证明别名再合并语义，未知/不同内容仍拒绝。新DM图在前/群图在后任务均完成320×180并UI核对；原blocked保留审计，不静默重跑。完整复核scripts/accept_media_matrix.py；docs/28。76项自动测试。长期任务heartbeat id=bridge，每30分钟附着当前聊天，机器/Codex在线时续跑；无新结果保持安静。

## 2026-11-11 常驻事件与恢复检查点
当前以docs/29覆盖上段19:05的部署描述：两路stream_hint已启用，保留15秒history补读。veil真实UI 5条消息→3任务6回复，短停机时群/私聊任务补回且UI可见；受控终止一个服务拥有的群订阅子进程后自动重连，新消息正常。12旧任务、28旧投递、33旧执行日志与session保持，不重放历史。群PDF已客户端下载打开，摘要一致。只读复核scripts/accept_stream_integration.py；网络分区/过期凭据/24h仍未完成。

## 2026-11-11 19:52续跑检查点
DOCX群/私聊×双向4案例通过，四资源＋两份客户端下载原件字节一致；两份DOCX在TextEdit打开，私聊Kimi提取TXT也客户端下载打开并校验。证据docs/30、scripts/accept_office_files.py，只读复核；不要重发固定key。XLSX/ZIP仍只有历史API证据，本轮probe只是预览。
24h只读观察于19:36:08启动，run=reliability-20261111，30秒采样，预计次日19:36后才可能达时长；不能标通过。续跑先核对local/service-observations该run的status更新时间、PID所属命令及日志，不删除/重启覆盖中断。下一步C01 XLSX/ZIP、原生媒体等；服务/gateway持续运行、未扩大授权。

## 2026-11-11 20:20 XLSX/ZIP检查点
XLSX/ZIP八格传输、8资源完整，四份客户端下载原件分别在Numbers打开/系统解包后TextEdit打开；两个DM实际Kimi任务、6确认投递、两份提取TXT客户端下载打开通过。群普通文件和liev自身文件不触发。只读脚本scripts/accept_extended_office_files.py：73项案例检查＋精确覆盖，通过缺资源/损坏客户端负向注入。docs/31与E010。下一步出站PNG客户端下载、音视频及引用多附件；不得重发这些固定实验。24h观察连续89样本/约44分钟/0不可用，仅短期进展。

## 2026-11-11 20:36原生图片检查点
旧Markdown出站PNG可见但当前私聊客户端不能打开查看器/保存，真人原生PNG可打开作为对照。官方Shortcut已有--msg-type image --media-id，新的独立类型实验DAB-NATIVE-PNG-20261111-direct-001已经SUCCESS，UI下载原件Quick Look打开与fixture一致；脚本accept_native_image.py只读。docs/32/E011，私密intent/send/status及截图在local/native-png-20261111。bridge仍使用Markdown，未修改发送代码；下一步优先查官方本地上传取mediaId、持久化分阶段状态和失败对账，再接入群/私聊验证。不得将原生实验当作旧Markdown已客户端下载。

## 2026-11-11 21:10 原生图片实现检查点
已实现本地图片上传→独立image发送，原版DWS仍v1.0.67；imageUploadBinary指向隔离的本地补充入口（非官方发布命令），源码固定v1.0.67，只增加叶子/注册并复用官方CHAT_IMAGE上传和鉴权。上传/投递分阶段持久化，未知不重试，旧Markdown key不重放。PNG/JPEG原生上限2MiB、不压缩；新image无配置明确拒绝，不降级Markdown。私聊bridge fixture＋veil UI交办Kimi实际生成96×64蓝色PNG均完成独立图片查看器、客户端下载、Quick Look打开、字节一致。84回归、6 Go叶子用例/schema完整性、22项只读检查通过；docs/33/E012。
20:53发现原群现有3人（既有两账号外新增成员），没有在群发本轮图片，已发异步范围确认问题；这是新变化，不是缺第二账号。保持两账号白名单，不扩大执行人；未获答复继续私聊音视频/引用多附件和独立代码工作。群gateway尚未重启加载新图片artifact选择，私聊gateway已加载；传输两路已加载。
20:54部署重启传输，私聊gateway随后重启；24h观察run不变，maintenance.ndjson记录维护，不冒充零中断/同一版本24h。原51条bridge投递、私聊14旧任务34旧投递保持。原始证据local/native-image-bridge-20261111，只读复核scripts/accept_native_image_bridge.py。下一步C01私聊音视频原件与原生类型，原群范围确认后补原生图；心跳继续。

## 2026-11-11 21:20 下一段WAV检查点
原生图片实现已提交c090085。随后完成liev→veil私聊WAV文件：固定key DAB-MATRIX-20261111-direct-wav已confirmed，UI文件卡片下载，32044B客户端下载与原件一致，Finder Quick Look音频播放器显示1秒；8项只读检查通过。docs/34，scripts/accept_wav_direct.py。不是原生语音条。WAV/MP4探针已新增；MP4仅预览未发送。下一步veil UI上传WAV到liev私聊并核验实际任务，再做MP4私聊双向；原群3人范围问题仍待回复，不重发已确认WAV，不等待群确认停止其他工作。

## 2026-11-11 21:42 音视频私聊闭环
WAV/MP4私聊双向四格、4资源原件、2个真实Kimi分析任务6回复、2份报告客户端下载Quick Look打开通过；54项只读审计及缺资源/损坏下载负向检查通过，旧账本逐行保持。docs/34/E014，scripts/accept_audio_video_direct.py。MP4虽官方按file发送，UI实际为可播放视频卡片，客户端播放/保存/系统打开均通过；不能笼统再说视频无播放能力，也不能推成独立video协议/语音条通过。原群4格待范围答复，下一步私聊引用、多附件与任务控制。观察run不变，约2小时，未满24h。

## 2026-11-11 22:03 安装与诊断检查点
已交付pyproject安装包0.1.0与五个入口，CLI默认token路径修为工作目录；doctor离线只读、live只GET本机health，脱敏检查配置/身份绑定/构建摘要/账本/最近完整同步，不发消息/修复/续授权。干净暂存树导出不含账号状态，新venv安装与入口/模块摘要通过；93项回归通过，现场31检查保留1个历史blocked警告。docs/35/E015。统一多worker后台管理尚未交付，未重启运行服务/gateway。引用附件UI菜单因CUA坐标windowNotFound受阻，AX右键无菜单；未发引用消息，窗口已恢复原显示器，证据quote-ui-attempt.json。下一步优先真实UI文本命令status/cancel/new与多附件，另以已验证键盘动作或修复坐标处理引用；不要重复无效坐标点击。24h原观察器仍在，约2小时28分，不重置/不标通过。

## 2026-11-11 22:24 任务控制检查点
真实UI发现status空闲误报queued1，已改先完成自身再统计，中文状态回复；两次后续查询验证空闲0/0和实际执行1/排队1。Kimi真实Bash/Python sleep120被veil cancel停止，已观察子进程结束、超过120秒无取消输出，队列下一任务437正常。seed/new/check验证generation仅+1、native session先解除再换新、UI不携带旧口令。9请求14确认回复4次runtime、100只读检查/负向检查、95回归通过；docs/36/E016。旧20任务/50agent投递/63传输投递保持。两个gateway均空闲维护重启，群现在也加载原生图结果选择；传输/24h观察器不重启，维护有记录。当前DM会话generation1，旧generation0及session证据保留。下一段多附件与统一管理，引用坐标路径不盲重试。

## 2026-11-11 22:39 多文件后续任务检查点
Finder多选两份合成TXT/CSV一次粘贴，钉钉拆成两消息/两任务，各真实Read；后续合并任务沿用同native会话，Write报告17+23=40，客户端文件卡片下载、Quick Look打开、摘要相同。3任务7回复、50只读检查及2负向检查通过，docs/37/E017。不是单消息多附件、无自动合批，join没有重读原件。旧29任务/64Agent投递/77传输投递保持，无部署重启。24h原观察器约3小时、采样新鲜，不标通过。下一段C04统一后台管理/配置引导，C01长文与有证据的引用入口；原群仍待范围答复。

## 2026-11-11 长文修复检查点（E018）
6942字符UI粘贴触发转文档提示，已取消未发送。3588字符输入完整入站，Kimi6825字符回复首段6008字符/6220 UTF-16被官方PARAM_ERROR明确拒绝，上限5120；旧unknown无taskId保留、不重发。已改含前缀UTF-16分段+新发送前校验，99回归通过；空闲维护重启传输/两gateway，原24h观察器不变。不同内容的新任务3592字符→两段5063/2037 UTF-16全confirmed，两份8039B文件均客户端下载Quick Look打开。官方Str会TrimSpace，固定第一段末尾LF少1，文件原件不变；完整长气泡UI未逐段观察。docs/38和56项只读审计，旧失败未改绿。当前DM31任务/72outbox（71确认1原unknown），历史blocked/cancelled保持。下一步优先补明确拒绝分类/证据化终态对账与失败反馈，不换key重投；再统一后台管理及引用/长文UI。观察约3h27、415样本1不可用（维护有记），不能称24h通过。

## 2026-11-11 E019 拒绝终态与用户提示
原长文首段现为rejected：显式导入绑定原uuid/目标/执行编号/唯一时间窗的官方长度拒绝日志，完整原unknown行和证据存入rejection_audit；原正文未重发（官方请求计数仍1）。后续明确invalid_request+PARAM_ERROR在发送阶段分为拒绝，有taskId的查询拒绝不误判。gateway原子记录终态+稳定key失败通知。真实UI可见部分回复未送达；veil status显示未确认0/拒绝1，旧blocked/cancelled保留。108回归、34只读审计及2负向检查通过，docs/39/E019。当前DM32任务/74outbox（73确认1拒绝），本段新增1状态任务/2确认回复/0runtime；两个gateway和传输已维护重启。E018冻结证据不改，审计只允许有原行摘要证明的终态转换。下一步C04统一后台管理/配置引导，C01引用/长气泡UI，C05办公；原24h观察器继续、不重置。

## 2026-11-11 E020 统一管理器已迁移
当前传输/群gateway/私聊gateway由dingtalk_bridge.service_manager拥有，local/runtime/managed-processes.json记录归属；旧scripts/*_ctl.py与旧PID文件不再管理当前进程。查看用python3 -m dingtalk_bridge.service_manager status；start必须显式带两个--agent-config，stop无需配置列表。无开机自启/自动监督，SIGTERM超时不强杀。详见docs/40。
11项真实子进程测试及119全量通过；干净新wheel/venv六入口、17模块摘要相同。现场重复start同PID、逆序stop、重新start新PID；旧35任务/81outbox/94传输/83运行文件保持。veil原生私聊一个新任务→Kimi Write 19×31=589→liev3确认回复，35B文件客户端下载Quick Look打开且字节一致，39只读检查及2负向检查通过。当前DM33任务/77outbox（76确认1拒绝），旧blocked/cancelled保留。原24h观察不重置，511样本约4.25h/累计3不可用，迁移维护已记；未满24h。下一步C05 liev官方办公闭环，C01引用/长气泡新UI路径；原群范围问题仍待答复，不重复坐标失败路径。

## 2026-11-12 E021官方办公接入检查点
仅DM启用officialDwsTools，群关闭；新增上下文固定路由binary/profile，无令牌，默认关闭，不是OS沙箱/强制CLI白名单。Kimi用官方doc/todo/calendar/mail完成四类合成对象，veil原生UI三个任务→9确认回复，760B/1243B/2020B三报告均客户端下载Quick Look打开且原件一致。B密送表述过度推断已由只读C更正，原报告/失败只读命令保留，草稿箱另有读证；日程默认提醒/会议字段已报告。69只读检查/3负向检查，最终干净126回归、六入口/18模块同摘要通过，docs/41。复核accept_official_office_agent.py，不重发A/B/C、不重新创建四对象。
当前DM36任务/86outbox（85确认1拒绝），群3任务/7outbox不变；旧blocked/cancelled及全部日志保持。两次空闲manager stop/start已记录维护，原24h观察run/PID/起点未变，604样本约5.03h/累计3不可用，尚未满时长。下一段C01引用/完整长气泡有效新UI路径（旧坐标/PageUp不重复），C02实际网络/凭据恢复与最终交接；原群第三人范围问题仍待答复，独立私聊继续。

## 2026-11-12 E022/E023长文与网络恢复检查点
E018旧两段长回复已在主聊天完整AX逐字比对并核对7张首尾/边界视口，无新消息，22审计/2负向检查；docs/42。原生会话搜索→点击结果→selectText可定位正文；右键仍无引用菜单，Command+Up会切侧栏会话，禁止盲重试，不把AI搜索摘要当消息正文。
私聊history HTTP子进程实际断网78.310秒（官方5次io_timeout），veilUI发一次任务；恢复自动补收，Kimi Python计算1591，三确认回复、36B客户端下载Quick Look打开通过，42审计/3负向检查；docs/43。非完整Stream/整机断网或凭据过期。测试launcher已撤除，local/service-config.json精确恢复，DM生成上下文回到原官方binary；三个manager进程当前健康，setup/cleanup维护已记，恢复期间无重启/重发。
当前DM37任务/89outbox（88确认1拒绝），群3任务/7outbox不变，旧blocked/cancelled保持。原观察run/PID/起点不变，冻结669样本约5.57h/累计4不可用（清理维护新增1），未满24h。只读复核accept_long_bubble_ui.py和accept_history_network_recovery.py，不重复新旧实验。下一段先查可隔离的官方Stream连接/凭据失效机制或引用有效新入口，不能撤真实授权/改整机网络；无法安全隔离就具体记阻塞，转最终MUST/矩阵/边界缺口自检与独立实现。原群范围仍待答复。

01:25只读补查：官方event status显示两consumer共享账号级personal bus，父PID均属当前bridge，idle/inferred不是新实收证据。SDK代理/共享daemon的限定断连方案仍需验证，见docs/43。官方另有dingtalk-tag connect已发布数字员工路线（独立员工profile/设备绑定），本机Help/固定源码已确认并补docs/25；没有发布/绑定员工，不将其混为liev真人路线。
