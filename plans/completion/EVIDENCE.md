# 证据台账
| ID | 等级 | 结论 | 可检查资料 | 剩余限制 |
|---|---|---|---|---|
| E001 | L5 | veil→liev原群/私聊、TXT/CSV、3个文件下载打开、上下文、无循环与重启 | docs/27；evidence/2026-11-11/two-account-ui-observations.json及two-account-ui-ledger.json | 其他媒体/外部/实时事件未通过 |
| E002 | L3 | 73自动测试及已知ID/令牌脱敏扫描；Git基线166b11b、baseline/ui-2026-11-11 | scenario-regression.json；git show；handoff-manifest.json | 单元测试不代替UI；还需持续隐私门 |
| E003 | L1 | 完整用户消息复盘与本计划，区分MUST/SHOULD、Kimi已满足任选执行器 | 01-PRD.md、CURRENT_MISSION.md | 计划不代表实现完成 |
| E004 | L5 | PNG/PDF群/私聊双向UI发送/可见，8案例10资源摘要一致；群/私聊PDF客户端下载打开；图文识别双端UI结果正确 | docs/28；media-matrix-ledger.json；本机local/ui-matrix-20261111 | 未下载打开所有出站图片；其他类型继续测 |
| E005 | L4 | 独立DWS Stream真实群5/私聊11事件，全部history匹配、无重复、正常退出 | media-matrix-ledger.json；本机local/event-captures/ui-matrix-20261111 | 仍非服务唤醒/断连/长期验收；跨时钟延迟仅样本估计 |
| E006 | L3/L5 | 图片资源别名误拦截修复；75项核心回归＋新增Git暂存隐私测试；真人图文任务验收 | scenario-regression.json；代码与docs/28 | 原blocked保持审计，未静默重跑；隐私扫描只覆盖已知值/私密路径/私钥模式 |
| E007 | L4/L5 | 常驻Stream业务唤醒、双账号服务停机补漏、群订阅子进程自动重连；5条UI消息、3任务6回复，12旧任务/28旧投递/33日志保持 | docs/29；stream-integration-ledger.json；stream-integration-ui-observations.json | 优雅进程中断非网络分区/凭据过期，24h未通过 |
| E008 | L4/L5 | DOCX四方向4资源、两份客户端下载原件均相同且TextEdit打开；Kimi实际提取TXT回传，客户端保存打开一致 | docs/30；docx-ui-ledger.json；docx-ui-observations.json | 单段落OOXML样本，不代表复杂版式/宏；XLSX/ZIP后续见E010 |
| E009 | L4运行中 | 24h只读观察19:36:08启动，30秒采样，非通过结论 | reliability-start.json；本机local/service-observations/reliability-20261111 | 未满24h，需PID/新鲜度/完整记录终检，不以启动当完成 |
| E010 | L4/L5 | XLSX/ZIP八格、8资源、四份客户端下载原件打开/解包一致；两个Kimi任务6投递、两份TXT结果客户端下载打开 | docs/31；xlsx-zip-ui-ledger.json；xlsx-zip-ui-observations.json；xlsx-zip-audit-validation.json | 简单双单元格XLSX、单文本ZIP，不含公式/宏/加密/恶意解包覆盖 |
| E011 | L4/L5 | 确认旧Markdown出图与原生图的查看器差异；官方已有mediaId独立image私聊发送、查看器、下载原件Quick Look打开、字节一致 | docs/32；native-image-direct-ledger.json；native-image-ui-observations.json | bridge仍Markdown路径未修，群原生图未验；不得标旧实验已下载或全产品图片完成 |
| E012 | L3/L4/L5 | bridge本地上传→独立image与Kimi实际生成PNG私聊交付，2份客户端下载Quick Look打开、原件相同，51旧投递/14旧任务/34旧agent投递保持；84回归 | docs/33；native-image-bridge-ledger.json；native-image-bridge-ui.json；native-image-build-validation.json | 群现3人待范围确认；JPEG/大图/动画与自动恢复上传未知未通过；部署维护不等于同版本24h |
| E013 | L4/L5 | liev→veil私聊WAV文件确认投递、客户端下载与资源原件一致，Quick Look音频播放器打开1秒；8项检查 | docs/34；wav-direct-file-ledger.json；scripts/accept_wav_direct.py | 仅八格首格；MP4未发送；不是原生语音条/听觉质量验收 |
| E014 | L4/L5 | WAV/MP4私聊双向四格4资源；两个真实Kimi任务6确认回复，两份分析TXT客户端下载打开且相同；MP4客户端视频卡片/播放/下载/系统打开通过 | docs/34；audio-video-direct-ledger.json；audio-video-direct-ui.json；audio-video-audit-validation.json；54项检查 | 群4格待范围答复；WAV无语音条，file协议MP4播放不等于独立video协议；仅合成1秒样本 |
| E015 | L3/L4 | 可安装包0.1.0、5入口、工作目录token修复、只读脱敏doctor；干净暂存树导出/新venv/最终模块摘要、93回归通过；现场31检查、1历史blocked警告 | docs/35；clean-install-validation.json；doctor-live.json；scenario-regression.json | 无新UI投递；未统一后台管理；只验macOS/Python3.14.6；不证明模型可调用/进程代码版本/24h |
| E016 | L3/L4/L5 | 私聊9次真实UI请求/14确认回复/4次Kimi；修复状态查询自身排队；sleep实际取消、子进程结束/超时长无文件、队列继续437、新native会话隔离 | docs/36；task-controls-ledger.json；task-controls-ui.json；100只读检查与2负向检查；95回归 | 仅私聊；等待附件取消仅自动测试；不是OS沙箱或撤销已完成副作用；维护已记录 |
| E017 | L4/L5 | 一次两文件多选上传被客户端分成两消息；各Kimi Read，后续同会话合并生成40，结果客户端下载Quick Look打开、字节一致；3任务7回复/50只读检查/2负向检查 | docs/37；multi-attachment-ledger.json；multi-attachment-ui.json；multi-attachment-audit-validation.json | 非单条多附件/自动合批，join沿用先前读取上下文未重开文件；引用仍待测 |
| E018 | L3/L4/L5部分 | 真实UI发现长文6008字符被拒绝（6220 UTF-16>5120），已修复含前缀分段/新发送前校验；99回归、不同内容新任务两段确认；两个8039B结果客户端下载Quick Look打开；56只读检查/2负向检查 | docs/38；long-text-ledger.json；long-text-ui.json；long-text-audit-validation.json | 原unknown明确拒绝证据保留、未重投，终态对账待补；官方TrimSpace去1尾LF；完整长气泡UI未逐段确认；维护采样不可用1次 |
| E019 | L3/L4/L5 | 原长度拒绝绑定官方uuid/目标/执行编号/窗口和载荷后记rejected，原unknown完整审计；未重发，UI部分失败提示+status未知0/拒绝1；108回归/34只读检查/2负向检查 | docs/39；rejection-reconciliation-ledger.json；rejection-reconciliation-ui.json；rejection-audit-validation.json | 旧日志导入仅明确text长度拒绝，不将未知网络结果推成失败；完整长气泡/引用仍待UI；终态失败warning保留 |
| E020 | L3/L4/L5 | 统一管理器六入口、新wheel/17模块同摘要、119回归；现网重复start同PID/stop逆序/restart新PID；旧35任务81outbox94传输83运行文件保持，1实际Kimi任务3确认回复、35B结果客户端下载Quick Look打开；39审计/2负向检查 | docs/40；service-manager-ledger.json；service-manager-install-validation.json；service-manager-ui.json；service-manager-audit-validation.json | 无开机自启/自动监督/崩溃原子spawn；仅macOS实机，非网络/凭据失效恢复；短文字气泡未独立观察；24h继续 |

| E021 | L3/L4/L5 | 默认关闭的路由绑定官方CLI上下文；liev四类办公对象、3个实际Kimi任务9确认回复，三报告客户端下载Quick Look打开；126回归/69只读审计/3负向检查/干净wheel六入口18模块 | docs/41；evidence/2026-11-12/office-agent-*.json；historical-manager-audit-validation.json | 非强制权限沙箱/服务端幂等；密送读字段缺失已更正，草稿箱单独读证；办公对象本身未在veil UI打开；24h继续 |

| E022 | L5只读补验 | 旧E018两段4892/1967字符完整聊天AX匹配，7个首尾/边界视口核对，零新消息/任务；22审计/2负向检查 | docs/42；long-bubble-ui-ledger.json；long-bubble-audit-validation.json | 不逐行像素验收；引用菜单仍未成功，AI搜索摘要不作证据 |
| E023 | L4/L5 | 私聊history子进程HTTP实际故障78.310秒、5次官方超时；veilUI一次任务，恢复自动补收/Kimi Python1591/3确认回复/36B客户端下载Quick Look打开；42审计/3负向检查，配置已恢复 | docs/43；history-network-recovery-ledger.json；history-network-audit-validation.json | 非完整Stream/整机断网、非授权过期；短文字气泡未独立观察；24h原观察5.57h/669样本/4不可用继续 |

| E024 | L3/L4/L5 | 已建立Stream WebSocket实际切断89.446秒，同一bus/consumer恢复7提示，history兜底无重复；2真实UI/Kimi任务，A格式错误failed及提示保留，B3127/37B客户端下载打开；131回归/50审计/4负向检查，装置已撤 | docs/44；stream-network-recovery-ledger.json；stream-network-audit-validation.json；stream-network-test-validation.json | A未成功交付；未逐条保存原始Stream载荷，非同时整机断网/失效凭据；24h原观察6.01h/5不可用继续 |

| E025 | L5只读补验 | 原E001的79B CSV从既有私聊下载、Quick Look表格实际打开并核对36/18/TOTAL54，原件一致；22审计/2负向检查、零新增消息/任务、账本保持 | docs/27补节；csv-client-open-ledger.json；csv-client-audit-validation.json；ACCEPTANCE_MATRIX.md | 不是新群CSV或编辑验收；引用修改/帮助菜单无入口，未发送引用；24h原观察6.31h/5不可用继续 |

| E026 | L4/L5 | 私聊单条文字＋两PNG，1真实Kimi/3确认回复；两原件实际ReadMediaFile/Bash测量，420B报告客户端下载打开；38审计/3负向检查 | docs/45；multi-image-ui-ledger.json；multi-image-audit-validation.json | 非任意文件/群/出站多附件；初始两Read错误保留；短回复未单独UI观察；24h继续 |

| E027 | L3/L4/L5 | 通用reply_to接官方DWS；137回归/干净wheel六入口18模块、30审计2负向；1私聊引用气泡真实UI源/回复/AI标识可见，无runtime回声 | docs/46；quote-reply-ui-ledger.json；quote-reply-validation.json；quote-reply-install.json | 入站/群引用及跳回源未过；stop PID保护错误保留后独立确认停完再启动；24h原观察6.86h/6不可用 |

| E028 | L4 | 官方自然access预刷新59只读采样、expiry延长及轮换后双路完整同步，19审计/3负向；账本无新增、原观察器归属保持 | docs/47；auth-rollover-ledger.json；auth-rollover-validation.json | 非失效refresh/重新授权/Stream重鉴权；采样保留1次维护URLError；24h冻结7.07h/6不可用 |

| E029 | L4/L5 | JPEG原件实际读图/旋转，1任务4确认回复；原生图片查看器及图片/报告下载打开，同字节；43审计/3负向 | docs/48；jpeg-ui-ledger.json；jpeg-audit-validation.json | 仅私聊小JPEG；客户端追加.png后缀但内容JPEG；短回复未单独观察，原24h7.47h/6不可用 |

| E030 | L3/L4 | 管理器发信号前退出竞态实际合成进程先失败、窄修复；13管理器/139全量、干净wheel六入口18模块；现场无重启/账本保持 | docs/49；manager-exit-race-validation.json；manager-exit-race-install.json | E027 during-shutdown错误根因仍未知；不作为新UI/24h通过证据 |

| E031 | L3/L4阶段 | 只读时长/计数/序列/归属/缺口工具，11新增测试；917真实样本122事件与冻结账本一致，24h门返回2 | docs/50；reliability-progress-review.json；reliability-review-validation.json | 7.640h非24h；6不可达/3poll_error/14维护保留，不证明上游无漏或同版本零中断 |

| E032 | L4/L5文件通过、文字错误 | 超2MiB PNG走file，3147861B原件/198B报告下载Quick Look打开；28文件审计2负向 | docs/51；large-png-ui-ledger.json；large-png-audit-validation.json | 原模型短SHA错误保留，task_fully_correct=false；未发更正；仅私聊出站file，不扩大image上限 |

## E033 — SHA更正与两次模型错误保持
- docs/52-sha-correction-ui.md；scripts/accept_sha_correction_ui.py：37检查与2负向注入通过。
- evidence/2026-11-12/sha-correction-ui-ledger.json、sha-correction-audit-negative.json。
- 两次原生veil输入/liev完整回复可见；第一结论误判保留，第二实际Python判prefix false并明确更正。2任务4确认回复，无文件输出，既有15exports含mtime保持。
- local/sha-correction-ui-20261112仅本机；原E032和第一次followup语义验收不改绿，无部署变动。

## E034 — 引用来源字段修复
- docs/53；scripts/accept_quote_identity.py，23检查及篡改来源ID负向拒绝；154全量回归/干净wheel六入口18模块。
- quote-identity-{ledger,install,negative}.json；私有local/quote-identity-20261112、quote-side-menu-20261112。
- 7条既有官方引用离线标准化/持久重开，不修改历史模型或授权；两gateway已加载，传输/原观察不重启，无新任务/消息。原生入站引用仍未过。

## E035 — 输出文件限额及新压缩任务恢复
- docs/54；scripts/accept_output_limit_ui.py，38审计/2负向；156全量回归，新venv六入口18模块一致。
- output-limit-ui-ledger.json、output-limit-install.json、output-limit-audit-negative.json；私有local/output-limit-ui-20261112。
- 原生veil两次不同任务：21MiB生成后failed并明确提示，后续只压缩旧源，新ZIP客户端下载/系统解包与原件相同；2任务5确认回复、源mtime保持。DM46/114/123/170、群保持。只重启两gateway，传输/原观察保持。

## E036 — 当前交接入口与历史原文分开
- README/AGENTS/PREFLIGHT/docs13/docs17改为当前状态；原全文保存docs/history/through-E035，与2bb8530版本逐字节/SHA一致。
- current-handoff-consolidation.json确认原CURRENT_MISSION、PRD编号/等级/验收正文及18产品模块不变；仅更新当前证据列，不降低门槛，不新增UI通过。
- 下一独立项是带EXIF方向JPEG的私聊输入/原件/实际处理；群、入站引用、失效refresh及24h缺口保持。

## E037 — EXIF方向6原件与实际归正
- docs/55；scripts/accept_exif_ui.py，47只读检查及4负向通过；exif-ui-ledger.json、exif-audit-validation.json。
- 原生veil单条图文、原件23810B/Orientation=6保持、Kimi真实读图/Bash归正，30666B PNG与462B报告客户端下载Quick Look打开；完整短回复正确可见。
- 一任务四确认，DM47/118/127/175、群保持；同native session，无部署变更。仅方向6样本、不外推镜像/动画/群；入站图片独立查看器未开。私有local/exif-ui-20261112。

## E038 — 原生入口补核，仍阻塞
- docs/25补节、native-entry-review.json，Mac9.0.5/59563623；输入框加号没有展开可识别菜单，格式工具栏误入口已恢复，零消息/录音/权限变更。
- 两路任务/outbox/传输/events/meta均不变；不是“客户端不支持语音”的证明。DWS audio/video仍为file，普通单消息多文件无新增契约。停止同一路径，转做独立运行边界。

## E039 — 同组后代清理、兼容等待与真实交付
- docs/56；scripts/accept_runtime_cleanup_ui.py：33审计/2负向；runtime-group-install、runtime-cleanup-validation、runtime-cleanup-ui-ledger、runtime-cleanup-audit-negative.json。
- 旧实现两条真实进程复现会在返回后继续写；修复保留leader身份直到同组清理，新增4项，Python3.12的17运行器测试通过。初始160全绿，最终兼容补丁全量160有2个既有manager关闭身份错误，未解决；187观察/6次带诊断执行未复现，不覆盖失败。
- 一次veil原生交办，真实Python计算/写文件，liev完整回复及16B TXT客户端下载Quick Look打开；DM48/121/130/179、群保持。UI在兼容补丁前；补丁后新安装/空闲重载/doctor单列，不重发冒充UI。
- 原观察1107样本9.225h/6不可达，未满24h；私有local/runtime-orphan-20261112。下一段补manager失败私有诊断，原缺口保持。

## E040 — manager私有诊断与双Python完整回归
- docs/57；manager-identity-install.json、manager-identity-diagnostic-validation.json。相同ps观察记录expected/current/raw到0600本地错误日志；status只读，写失败仍拒绝，无额外信号。
- manager15项；Python3.14/3.12各162全量通过。64次限定关闭实验未复现，停止该路径；E039两次历史错误和E027未知根因不改为已修复。
- 干净wheel六入口18模块通过；现网三个PID及两路全部账本/会话/日志保持，无新消息/重启。原观察9.4h/1128样本，未满24h。私有local/manager-identity-diagnostic-20261112。

## E041 — 原始附件名与Unicode/BOM CSV
- docs/58；附件原名/类型/字节数/SHA及安全路径独立传runtime，缺失名null；163全量、Python3.12 gateway34、新wheel六入口18模块通过。
- 原生准备任务后上传135B中文/空格/emoji名CSV，实际csv+Decimal处理、175B CSV与572B JSON均客户端下载Quick Look打开，原名/三行/57.00正确。48审计4负向；LF原件保留，Quick Look视觉扁平化另记。
- 两任务六确认，DM50/127/136/187、群保持；两gateway空闲加载，传输/原观察未重启。1150样本9.584h未满24h。私有local/unicode-csv-ui-20261112。

## E042 — 真实工具中停止私聊gateway并恢复
- docs/59；scripts/accept_active_gateway_stop_ui.py 41只读检查/4负向通过；active-gateway-stop-ui-ledger与active-gateway-stop-audit-negative.json。
- veil真实私聊，确认Python→Shell→Kimi→gateway归属后正常stop；四进程退出、取消反馈UI可见；104.38秒后无晚写，恢复后实际只读检查及703完整回复。首次取消日志仅版本元事件，真实命令证据来自现场ps与开始标记。
- 两任务四确认，DM52/131/140/193；群、旧记录/日志、传输和原观察保持，同native session。1175样本9.792h仍未满24h，产品沿用E041，历史manager错误不改绿。私有local/active-stop-ui-20261112。

## E043 — 官方会议边界与个人钉盘真实交付
- docs/60；conference固定v1.0.67源码/Help明确下线，本机退出5；日程会议、实体会议室、听记分开，8边界检查通过，official-office-boundary.json。
- 一次原生私聊交办，Kimi实际官方mySpace/根目录查询、唯一意图/一次+upload/按ID+info和+download，57B原件比对，IM完整回复和客户端下载Quick Look打开。39审计4负向，drive-ui-ledger和drive-audit-negative.json。
- DM53/134/143/197、群/旧日志保持，同session无部署变化；1200样本10.001h未满24h。私有local/office-boundary-20261112；下段合成语音本人听记，不录环境/发卡片，未知按原ID对账。

## E044 — 合成语音听记分析及私聊报告交付
- docs/61；scripts/accept_minutes_ui.py 51只读检查/5负向通过，minutes-ui-ledger.json 与 minutes-audit-negative.json。
- 两次原生输入：准备后单次WAV上传；提示无原稿或答案。Kimi一次官方创建/原taskUuid独立读回，转写/摘要/三行动项准确，关键词空列表明确报告；2125B报告客户端下载Quick Look打开并核尾页。
- DM55/139/148/204，群/旧证据及native session保持，无部署变化。原观察1229样本10.243h/6不可达仍未满24h。私有local/minutes-ui-20261112；不算原生语音条、独立会议、独立待办指派通过。

## E045 — 崩溃不确定提示及真实工具遗留
- docs/62；隔离真实Gateway/LocalRuntime实证parent death后工具写入，先失败回归后修正误称停止；163全量与新wheel六入口18模块通过，crash-notice-validation/install。
- veil单次真实任务，确认Python/Shell/Kimi/gateway归属后只SIGKILL私聊gateway；75.105秒后实际late文件存在。明确身份清理所有原进程后恢复，原任务interrupted不重做、新提示UI可见；新只读核验实际工具/完整回复通过、文件mtime与字节保持。43审计5负向，crash-recovery-ui-ledger/audit-negative；自动父进程丢失清理仍缺。
- DM57/143/152/210，群及旧账本保持；两gateway加载提示修复，传输/原观察保持，1261样本10.510h仍未满24h。私有local/crash-recovery-20261112。另核官方语音手册仅列手机步骤，无新Mac入口。

## E046 — 通用父进程守护与真实gateway崩溃自动清理
- docs/63；LocalRuntime pipe生命周期＋独立守护持有CLI直至同组清理，正常完成/取消/超时继续；164全量、双Python运行器各18项、新wheel六入口19模块通过。
- 新veil原生任务确认五进程父子链后仅SIGKILL私聊gateway，0.365秒后自动全部退出，测试控制器对后代零信号；204秒无晚写，原interrupted/no result不重做。新只读Python及完整liev回复UI可见。
- 42审计5负向；runtime-parent-guard-validation/install/ui-ledger/audit-negative.json。DM59/147/156/216，群3/7/12/76与旧记录/日志保持；两gateway已加载，transport/原观察保持。1290样本10.752h仍未满24h；非OS沙箱，不覆盖守护自身SIGKILL。私有local/runtime-parent-guard-20261112。

## E047 — 真实运行器超时及最低Python已安装包验证
- docs/64；新增准确deadline/未重做/可能已有副作用提示；旧实现回归先失败，3.14全量165、3.12 gateway35通过。最低3.11.15在无源码包/账号数据的测试目录安装同wheel，全量165项通过；六入口19模块摘要保持。
- veil真实150秒Python等待，runtime90.399秒超时failed，无结果且自动工具清理；155.203秒无晚写，同gateway/session下一只读Python计算703，完整回复UI可见。随后精确恢复原600秒配置，仅空闲重载DM。
- 42审计5负向，runtime-timeout-validation/install/ui-ledger/audit-negative.json。DM61/151/160/222、群及旧记录保持；原观察1315样本10.960h未满24h；私有local/runtime-timeout-ui-20261112。无新C01入口，不重复菜单/试探发送。

## E048 — 执行时限配置边界
- docs/65；共享有限正数校验用于LocalRuntime构造/run、Gateway状态创建前及只读doctor。拒绝NaN/无穷/bool/非数字/零负数/巨整型，默认600及正小数保持。
- 4新增回归；旧doctor参数化11失败保留；Python3.14与最低3.11隔离已安装wheel各169项通过，新wheel六入口19模块一致，20项部署/账本不变核验通过。
- runtime-timeout-config-validation/install.json；无新消息/旧UI重跑，配置/两路全部旧账本及日志保持，gateway空闲加载。原观察1329样本11.077h未满24h；下一项修历史审计与当前源码混比。私有local/runtime-timeout-config-20261112。

## E049 — 历史UI冻结安装审计
- docs/66；五个审计旧安装与当前源码混比导致唯一失败，现分别核冻结源码/安装目录/wheel总摘要及模块集合摘要，当前版本差异独立展示false。
- E039/E041/E045/E046/E047完整只读审计通过，旧报告SHA不变；实际报告10内存负向和Python3.14/3.11各3专项通过。frozen-install-audit-validation.json。
- 无产品修改、构建、重启或新消息；两路旧账本/日志12项不变。原观察1338样本11.152h未满24h，下一C11运行文档/CLI帮助/HTTP契约/配置例子一致性核对；私有local/frozen-install-audit-20261112。

## E050 — 当前运行/CLI/HTTP/模板交接核对
- docs/67；运行手册/通用工具重写为现态，两份旧全文与aaa5cf2逐字节归档；OpenAPI补已实现的rejection_evidence、413/500与202解释，旧安装页标明历史检查点。
- 隔离3.11已安装wheel：18帮助、33既有HTTP/拒绝/迁移/路由测试通过；13核验与12账本保持检查通过，handoff-contract-validation.json。JSON语法及实现对照，不冒称完整第三方OpenAPI规范认证。
- 19产品模块/三进程/所有旧记录不变，无新消息或UI；原观察1358样本11.319h/6不可达、原3poll_error保持，未满24h。私有local/handoff-contract-20261112；下一独立工作目录路径边界，原群/UI入口loop guard保持。

## E051 — 中文/空格安装与工作目录
- docs/68；公开tests/scripts/fixtures移到中文/空格工作目录，TMPDIR同样包含中文空格，六组64既有测试通过，包含实际HTTP和runtime子进程；用原E048已安装wheel，不含源码包或账号数据。
- 另在中文/空格venv离线安装同wheel，六入口及合成中文配置/二进制路径doctor通过，19模块一致；11核验及12现场保持通过，workspace-path-validation.json。64测试与新中文venv入口测试范围分列，不称新增64测试或新UI通过。
- 产品、三进程和旧记录不变。原观察1373样本11.444h/6不可达，历史3poll_error保留；下一段仅对具体剩余MUST找新可证分支，既有UI/菜单不重复。私有local/workspace-paths-20261112。

## E052 — 并发对账终态保护与真实部署UI
- docs/69；core对账/晚错误更新增加终态条件，旧线程8失败及旧E048安装HTTP4失败原样保留。新增5测试方法，Python3.14与最低3.11隔离已安装wheel各177项通过，新wheel六入口19模块，22核验通过。
- 新veil原生私聊一次交办，Kimi真实Python算平方/总和写145B JSON，liev完整回复及文件卡片可见；客户端下载Quick Look打开，四份原件同SHA。accept_reconcile_race_ui.py 36审计、7内存负向通过；reconcile-race-{validation,install,ui-ledger,audit-negative}.json。
- 三进程已空闲重载，配置字节不变；DM62/154/163/226、群3/7/12/76，旧记录/日志/session保持。原观察1402样本11.686h/6不可达，历史3poll_error及维护保留，未满24h。并发故障为隔离验证，不冒称真实失效凭据恢复；私有local/reconcile-race-20261112。

## E053 — 异常消息隔离与后续任务继续
- docs/70；显式raw/list/ref对象校验转既有quarantined，不扩大程序错误捕获；旧2方法2失败15错误保留。18合成形状及后续合法任务/重启不重放通过，双Python179全量、新wheel六入口19模块。
- accept_message_shape.py 25审计通过，message-shape-install/validation.json；302条旧官方事件（含7引用）新旧投影相等，原件只读。没有新增引用UI或异常平台返回的声明。
- 仅两gateway空闲重载，transport和原观察保持；DM62/154/163/226、群3/7/12/76及旧日志/config/session不变。原观察1424样本11.870h仍未满24h，6不可达/历史3poll_error保持；私有local/message-shape-20261112。

## E054 — 附件缓存清单完整性
- docs/71；缓存补核成功/完整标志、预期资源集合及准确字节数，损坏要求显式repair到新attempt目录，保留旧原件；旧1方法6失败保留。修复后6场景/重启/repair/再次命中通过，源码及双Python已安装包各180项。
- accept_download_cache.py 22审计；download-cache-install/validation.json。48现场清单55资源只读验证、网络调用0、清单不改；无真实损坏注入、重新下载或新UI。
- 三进程空闲加载、配置/旧记录/session不变，DM62/154/163/226、群3/7/12/76保持。原观察1442样本12.020h未满24h，6不可达/历史3poll_error保持；私有local/download-cache-20261112。

## E055 — 真实附件下载故障与原任务恢复
- docs/72；仅私聊官方mget子进程代理网络隔离115.987秒，14次原始官方io_timeout/request_timeout失败；history/Stream保持，原CSV waiting_media且未运行，status完整UI可见。
- 原消息恢复后一次成功下载/一次真实Python csv+Decimal+SHA，192B JSON客户端下载Quick Look全文打开；输入3份/输出4份原件相等。accept_attachment_outage_ui.py 52审计8负向，attachment-outage-ui-ledger/audit-negative.json。
- 3新任务6确认，DM65/160/169/235、群3/7/12/76及旧记录/session保持；设置/撤除有维护，恢复不重启或重发，配置精确恢复，product仍E054/180项。原观察1477样本12.312h、7不可达（维护增1）及旧3poll_error保留，未满24h。私有local/attachment-outage-20261112。

| E056 | 2026-11-12 | 固定DWS发送组合18个无账号dry-run；重复file末项覆盖、互斥、9/10图引用及audio/video=file，46审计9负向，现网与E054产品保持 | [报告](../../docs/73-official-send-composition-contract.md)、[合成CLI计划](../../evidence/2026-11-12/send-contract-probe.json)、[审计](../../evidence/2026-11-12/send-contract-audit.json)；`PYTHONPATH=. python3 scripts/accept_send_contract.py`；原始首次类别失败与快照local/send-contract-20261112 | CLI计划不是UI，单消息普通附件/原生媒体未改绿，原观察约12.545h未满24h |

| E057 | 2026-11-12 | 快速附件完成结果仅原消息消费/优先候选/取消清理；4新回归，旧源码/wheel各2失败，源码与双Python已安装wheel各184项、24审计 | [报告](../../docs/74-media-completion-scheduling.md)、[审计](../../evidence/2026-11-12/media-slot-validation.json)、[安装](../../evidence/2026-11-12/media-slot-install.json)；`PYTHONPATH=. python3 scripts/accept_media_slot.py`；raw local/media-slot-20261112 | 仅双gateway空闲加载，原记录/传输/观察保持；无新UI，原观察12.712h未满24h |

## E058 — 首次下载完整性
- [docs/75](../../docs/75-fresh-download-integrity.md)；22坏首次/3部分/4坏缓存/失败repair保旧及本地HTTP 502→同消息200→命中缓存，5新方法；旧源码16失败10错误、旧wheel18失败10错误保留。
- 源码/双Python已安装wheel各189项、六入口19模块；50既有缓存57资源只读禁网、24审计通过，三进程空闲加载。配置/旧账本/session/运行日志及原观察保持；12.921h/7不可达，无新UI。
- [安装](../../evidence/2026-11-12/fresh-download-install.json)、[审计](../../evidence/2026-11-12/fresh-download-validation.json)；`PYTHONPATH=. python3 scripts/accept_fresh_download.py`，raw local/fresh-download-20261112。

## E059 — 清单原子提交
- E059清单原子提交：真实子进程短写复现旧缓存损坏，同目录0600临时文件写入/fsync/replace后冷/热缓存恢复、提交前SIGKILL保旧通过；2新方法、源码及双Python安装包191项、50缓存57资源只读与28审计，三进程空闲加载。首次全量仍有1个manager关闭身份错误，其精确ps因测试清理丢失，未宣称解决；无新UI。
- [docs/76](../../docs/76-atomic-download-manifest.md)、[安装](../../evidence/2026-11-12/atomic-manifest-install.json)、[28项审计](../../evidence/2026-11-12/atomic-manifest-validation.json)。`PYTHONPATH=. python3 scripts/accept_atomic_manifest.py`；raw local/atomic-manifest-20261112，原观察13.121h/7不可达。

## E060 — 测试清理前诊断留存
- E060新增清理前诊断测试入口；源码与E059同一已安装产品在Python3.14/3.11各193项通过，每套7份预期负向拒绝记录均保住同次观察，29项审计通过。16次限定真实合成进程复核未复现E059关闭错误，根因仍未解；产品/现网未改、无新UI。
- [docs/77](../../docs/77-manager-test-evidence-retention.md)、[29项核验](../../evidence/2026-11-12/manager-test-evidence-validation.json)；`PYTHONPATH=. python3 scripts/accept_manager_test_evidence.py`。原观察13.229h/7不可达；原始日志local/manager-shutdown-20261112，新诊断local/test-evidence，均不入Git。

## E061 — 路由进程锁与新关闭故障
- E061两个真实独立进程恢复用例通过：同路由锁拒绝、不同路由并行、持锁进程SIGKILL后confirmed保持/执行中转unknown，同key两次重开均不重发。源码/3.14安装包195项通过，3.11全量195项有1个新manager错误，已保住同次ps：TERM后同启动时间的?Es及括号短命令；未改产品/现场或新增UI。
- [docs/78](../../docs/78-route-process-recovery.md)、[23项审计](../../evidence/2026-11-12/route-process-recovery-validation.json)。私有local/route-process-20261112，观察13.354h/7不可达。

## E062 — 已观察退出过渡窄修复
- E062修复已捕获的TERM后同启动时间E退出过渡误拒：只继续有界观察，不追加信号或提前当作停止；其他身份变化/发信号前/超时保持拒绝。旧源码/wheel各2失败，精确原始观察旧拒绝/新待退出均只1次TERM；源码及新wheel双Python各197项、六入口19模块与26审计通过。manager按次执行，现场三进程无需重启；无新UI，未观察历史错误不回填根因。
- [docs/79](../../docs/79-manager-exiting-transition.md)、[安装](../../evidence/2026-11-12/manager-exit-install.json)、[26项审计](../../evidence/2026-11-12/manager-exit-transition-validation.json)。raw local/manager-exit-20261112；原观察13.421h/7不可达。

## E063 — Git离线交接核验
- E063已从Git提交82e1c2a导出不含.git/local的源码，492项manifest前后匹配；单独准备构建依赖后，16步离线构建/新3.11安装、六入口及197项通过，19审计通过。产品/现网/旧记录保持，交接包与私有日志分开；无新增UI验收，原观察13.621h/7不可达。
- [docs/80](../../docs/80-offline-handoff-export.md)、[构建](../../evidence/2026-11-12/clean-handoff-build.json)、[19审计](../../evidence/2026-11-12/clean-handoff-validation.json)。raw local/clean-handoff-20261112；只bundle子目录为脱敏交接payload。

## E064 — 图片补充独立构建与覆盖保护
- E064修复图片补充构建器覆盖已有输出/生成测试文件的缺口；4新方法、源码及双Python已安装runtime连同公开构建器各201项、独立官方源码真实Go构建与22审计通过。官方binary/现场补充/配置不变，未部署、无新UI。
- [docs/81](../../docs/81-image-build-ownership.md)、[22审计](../../evidence/2026-11-12/image-build-validation.json)；`PYTHONPATH=. python3 scripts/accept_image_build.py`。旧4方法3失败1错误、网络克隆超时、真实Go和安装日志均保留local/image-build-20261112；隔离配置仅生成log，未声称始终空目录或字节可复现。

## E065 — 真实Keychain读取故障，尚未恢复
- E065当前真实故障：09:25后两路history失败，官方退出51为macOS Keychain读取DWS登录密钥失败；doctor退出0但auth fail，默认钥匙串/网络检查pass。未注入、未改凭据或重启；等待用户恢复现有密钥访问，恢复后核原进程自动同步/旧账本不重放。原观察09:39快照14.047h、7不可达、30poll_error（继续累计），未满24h。
- [docs/82](../../docs/82-live-keychain-read-failure.md)、[脱敏事实](../../evidence/2026-11-12/live-keychain-failure.json)；原始官方输出/observer报告local/sync-failure-20261112。不冒称refresh过期、恢复通过或doctor健康；已请求用户恢复现有访问，无新UI发送。

## E066 — 官方v1.0.68相关源码边界
- 只读官方发布与53提交218文件比较，macOS Keychain与image_upload原件逐字节相同、chat差异未新增上传叶子。没有安装/执行新版或改变现场，不把Windows隔离改动当macOS修复。
- [docs/83](../../docs/83-official-v1.0.68-boundary-review.md)、[证据](../../evidence/2026-11-12/official-v68-boundary.json)；原始选取响应/源码local/dws-v68-review-20261112。升级前须另验解密/分页partial语义；E065仍待恢复。

## E067 — 钥匙串UI和用户输入密码后的核对
- 已定位dws-cli条目、未显示密码/改访问设置；Apple只读status=7，用户输入系统密码后官方auth仍fail；原记录保持。单次系统读取stdout丢弃/51且无stderr，不猜根因。
- [docs/84](../../docs/84-keychain-ui-followup.md)、[证据](../../evidence/2026-11-12/keychain-user-followup.json)。原始local/sync-failure-20261112；Terminal UI被工具安全限制拒绝，无绕行；已请用户手动执行准备好的官方只读诊断，结果待到达。

E067补充：用户普通终端已运行，10:07官方auth仍fail；[结果](../../evidence/2026-11-12/keychain-terminal-followup.json)，不再按后台专属问题处理。官方reset范围已核，未执行；重启Mac仅可选用户安排，尚未发生。

## E068 — 凭据存储故障脱敏诊断
- E068补凭据存储故障的固定脱敏health/doctor诊断，精确官方错误前缀＋category/code才归类，不扩成过期/锁定；6新增方法含真实合成CLI/HTTP恢复、未知投递同key重启不重发，源码及新wheel双Python各207项、六入口19模块/20审计通过。尚未加载现场，原进程/配置/账本/观察保持，真实E065仍未恢复。
- [docs/85](../../docs/85-credential-store-health-diagnostics.md)、[安装](../../evidence/2026-11-12/credential-health-install.json)、[20审计](../../evidence/2026-11-12/credential-health-validation.json)；`PYTHONPATH=. python3 scripts/accept_credential_health.py`。原始local/credential-health-20261112；E063/E064冻结审计修正/2负向通过，旧报告字节保持。

## E069 — 当前源码与安装包交接更新
- E069已重新导出提交a83d3fd的源码和已验证E068同一wheel；512项冻结manifest、19模块及归档/安装包摘要匹配，无已知私有值。沿用源码与双Python安装包各207项结果，本次没有重跑测试或宣称新部署/UI通过。最新交接payload仅local/handoff-a83d3fd-20261112/bundle；E063旧包保持历史记录。
- [docs/80](../../docs/80-offline-handoff-export.md)、[六项核验](../../evidence/2026-11-12/handoff-refresh-validation.json)。实际payload的SHA256SUMS再次独立核验通过；不是最终交付，E065/UI/24h保留。

## E070/E071 — 群文件交办与事故停机
- [E070实现与216项验证](../../docs/86-explicit-group-file-tasks.md)，早于事故的冻结快照不是当前在线证明。
- [E071事故事实与边界](../../docs/87-authentication-popup-incident.md)，用户确认弹窗停止；认证未恢复，无新UI验收。

## E072 — DWS受管调用防护
- [实现/边界](../../docs/88-dws-process-containment.md)、[隔离安装](../../evidence/2026-11-12/dws-containment-install.json)、[冻结审计](../../evidence/2026-11-12/dws-containment-validation.json)。12新增方法、源码及双Python各228项；真实认证调用0、未部署/UI未测。独立bus和直接办公CLI仍是部署阻塞。

## E073 — 官方办公入口与共享bus边界
- [实现报告](../../docs/89-supervised-official-office-entrypoint.md)、[安装](../../evidence/2026-11-12/official-proxy-install.json)、[冻结审计](../../evidence/2026-11-12/official-proxy-validation.json)、[官方bus源码边界](../../evidence/2026-11-12/official-bus-ownership-boundary.json)。三套237、9新增方法，真实DWS调用0；仅新增本地operator_suspended状态。

## E074 — history双路和单次核验准备
- [方案](../../docs/90-guarded-recovery-read-plan.md)、[安装验证](../../evidence/2026-11-12/recovery-plan-installed.json)、[15项冻结审计](../../evidence/2026-11-12/recovery-plan-validation.json)。7新增方法、源码/双Python已安装产品各244项，复用E073同wheel和21模块；准备计划未执行，真实DWS调用0、服务全停、暂停保持。
- 原始local/recovery-plan-20261112；只读复核`PYTHONPATH=. python3 scripts/accept_recovery_plan.py`。真实一次查询的许可独立于后台恢复，不把离线测试标UI通过。

## E075 — 停机期间冻结交接
- [交接说明](../../docs/80-offline-handoff-export.md)、[8项核验](../../evidence/2026-11-12/handoff-e075-validation.json)。f0d2911归档/539manifest、21模块与E073wheel、全部Python测试与E074冻结套件一致；三套244为既有结果，本次未重跑、真实DWS为0。payload仅local/handoff-f0d2911-20261112/bundle。

## E076 — 验收声明只读核对
- [说明](../../docs/91-acceptance-coverage-review.md)、[64格与14 MUST报告](../../evidence/2026-11-12/acceptance-coverage.json)、[11项验证](../../evidence/2026-11-12/acceptance-review-validation.json)。37格历史通过/25阻塞/2部分，MUST仍9项未完整覆盖；原64格与PRD判据保持。
- 新工具5专项在源码/隔离3.14/隔离3.11通过，未重跑全量244或改产品；首轮中文相邻E编号漏检失败已保留并修复。真实DWS为0，查询许可仍待决。

## E077 — 当前运行入口与事故约束一致
- [旧10份入口](../../docs/history/through-E076/README.md)按860a2b5原字节归档；[10项核验](../../evidence/2026-11-12/current-entry-consolidation.json)确认PRD、MUST/64格、21模块和E076工具/测试不变，E074查询计划未执行且仍匹配。
- 当前AGENTS/任务/前置/关键路径及运行手册移除旧待密码/解锁/直接重启指令，明确真实读取与后台恢复分别待允许；群范围遵守最新入口多人暂跳过。仅文档修改，无新全量/UI/部署。

## E078 — 群文件关联的持久断点
- [功能补充](../../docs/86-explicit-group-file-tasks.md)、[10核验/逐场景记录](../../evidence/2026-11-12/group-file-recovery-validation.json)。2专项三环境覆盖两次实际合成子进程SIGKILL及late history；一次下载/执行/确认，原blocked不复活。产品21模块不变，无真实DWS/UI或全量重跑。

## E079 — history容量停滞已复现，尚未修复
- [原因/官方边界](../../docs/92-history-capacity-continuation.md)、[10项复现核验](../../evidence/2026-11-12/history-capacity-regression.json)。1001条三轮1000/0/0，首轮后重启仍漏1；源码/双Python同wheel均退出2。两官方合成Go契约测试通过不抵消bridge失败。
- 产品21模块/E074待决计划保持；无真实DWS/HTTP/UI。下一步在local源码候选实现原窗口与opaque token的持久接续，当前缺陷仍开放。

## E080 — history持久续页候选，未应用
- [候选说明/补丁](../../docs/92-history-capacity-continuation.md)、[14核验及冻结摘要](../../evidence/2026-11-12/history-continuation-candidate.json)。8新方法、候选源码与新wheel双Python各259通过；1001条改为1000/1/0，5000条有界推进，事务/重启/失败/循环token不越过缺口。
- 当前21模块/一次计划保持，产品仍有E079缺陷；仅local候选和公开补丁，真实DWS/UI为0。编排错cwd及旧runner空发现ok:true/0已记，不计通过；下一独立项修runner。

## E081 — 测试入口零发现拒绝
- [说明](../../docs/93-empty-test-discovery.md)、[8项核验](../../evidence/2026-11-12/empty-test-discovery-validation.json)。新增2方法，旧2失败；源码/双Python同E073产品各4专项通过。无匹配CLI退出1、summary明确no_tests_executed，非空实际执行通过。
- 产品21模块和E074 checker不变，无真实DWS/新UI/新wheel/全量重跑；不得将E080候选259与本次2新增相加成261全量。

## E082 — 一次许可已履行，官方参数失败
- [失败/边界](../../docs/94-single-read-unsupported-flag.md)、[脱敏回执](../../evidence/2026-11-12/single-read-unsupported-flag.json)。用户明确允许后原key仅执行1次；未知--as导致validation/unknown_flag、exit3，未取得会话结果；暂停保持，三服务停止。
- 命令准备错误和合成测试遗漏由bridge承担；认证仍未知，原attempt与raw不改，禁止重试/换key。下一离线项修核验/办公参数并用固定官方树校验，再继续候选与只读部署工具。

## E083 — 官方命令参数契约修复
- [说明](../../docs/95-official-argument-contract.md)、[14项冻结审计](../../evidence/2026-11-12/official-argument-contract-validation.json)。移除核验/办公入口强加--as，profile/json绑定保持；新增failed原key跨代码变更不重调回归。源码/双Python新wheel各254、六入口21模块通过。
- 独立固定官方声明树：旧8参数组unknown_flag失败、新8通过；六族518命令解析、11无解析导航占位单列。只有ParseFlags，不执行CLI/鉴权/业务。原E082 raw/receipt字节保持，新增真实调用0、未部署。

## E084 — 持久续页应用及整体产品验证
- [说明](../../docs/92-history-capacity-continuation.md)、[10项冻结核验](../../evidence/2026-11-12/history-continuation-applied-validation.json)。core/8方法与E080逐字节一致，其余20模块保留E083；源码/双Python新wheel实际各262、六入口21模块通过。
- 未部署/改配置/重放任务；E082真实receipt/raw原字节保持，无新真实DWS或UI。下一段继续只读部署差异与账本清单工具。

## E085 — 只读部署差异与账本清单
- [说明](../../docs/96-history-deployment-review.md)、[11项核验](../../evidence/2026-11-12/history-deployment-review-validation.json)。7专项三环境；既有owner锁、无旁文件只读SQLite、原绑定/状态/hash、不覆盖/变更拒绝。
- 本地两路六库0未完成/0未确认key、8历史非成功保留；20原文件字节/mtime/权限不变，私有清单可校验且无执行入口。无产品变更/新wheel/全量269/真实DWS/UI。

## E086 — 旧官方上下文与持久会话升级
- [说明/具体恢复顺序](../../docs/96-history-deployment-review.md)、[8项核验](../../evidence/2026-11-12/official-context-upgrade-validation.json)。2专项源码及E084安装包双Python通过；旧schema1刷新受管入口、暂停拒绝底层调用，关闭办公清理生成文件，原session/完成与失败任务/回执/用户文件保留。
- 仅合成runtime，无真实会话迁移/UI/DWS、新wheel或全量重跑。真实模型旧记忆不由提示词消除；21模块、20原文件及待决提案保持。恢复分transport补读/停机核积压/按授权单路gateway，不自动全启。

## E087 — 尚未消费本地事件只读预览
- [说明](../../docs/96-history-deployment-review.md)、[11项核验](../../evidence/2026-11-12/local-backlog-review-validation.json)。6专项三环境，复用当前纯分类逻辑、原ID去重/控制和文件待审、冻结/旁文件/cursor/scope拒绝；不构造worker或执行任务。
- 当前两路0未消费本地事件/0新候选/0quarantine，远端未补消息仍unknown；20原文件、E084产品、追加核验提案保持。原5项首轮1失败/2错误保留，最终6项无新全量/UI/真实DWS。

## E088 — 长停机首次恢复窗口
- [说明](../../docs/92-history-capacity-continuation.md)、[7核验](../../evidence/2026-11-12/history-outage-window-validation.json)。3专项三环境，两种会话的72h watermark、旧失败冻结窗口先完成再补尾、无watermark24h范围已验；产品未改。
- 停机后必须核watermark达到固定恢复cut且history_window清空，旧窗口complete不等于已补齐当前；只核固定官方两源码文件，没有真实调用/UI/全量重跑。

## E089 — 明确授权的修正后追加一次读取成功
- [说明](../../docs/94-single-read-unsupported-flag.md)、[7核验及脱敏回执](../../evidence/2026-11-12/corrected-single-read-validation.json)。用户明确允许追加一次和新记录，匹配冻结提案后仅1次真实conversation-info：exit0/targetMatched/readable，暂停保持、三服务停止，E082旧失败原位。
- 一次凭据读取已证可用，非全平台/后台/UI恢复；两个key均已attempt，不重试/换key。后台授权尚无，先形成具体分阶段方案。

## E090 — 仅私聊分阶段恢复提案
- [具体方案](../../docs/97-private-chat-recovery-proposal.md)、[7项静态核验](../../evidence/2026-11-12/private-chat-recovery-proposal-validation.json)。私有候选仅激活原direct/history，群transport/gateway停用、原数据保留；身份/白名单/runtime/账本位置不变。
- 待后台明确许可；阶段一最多300秒观察后停机核cut/未决/候选，全部满足才恢复私聊gateway。15秒轮询与90秒RPC/15秒清理分清；原配置未改、无真实调用/UI或新增测试。

## E091 — 主线与现成 channel 一手复核
- [决策说明](../../docs/98-channel-mainline-and-reuse-review.md)、[来源与边界](../../evidence/2026-11-12/channel-mainline-source-review.json)。Qwen固定41a3b9f文档/两源码/许可及社区Codex固定60a0a64 README与本轮main读取相同；区分普通账号、bot、数字员工和MCP工具。
- DWS基础通讯可作底座，群完整矩阵未过；E089只证一次读取，auth login/根因/跨设备仍未证。用户回复是澄清要求不是E090许可；三个服务/暂停保持，无真实调用/新UI/产品修改。

## E092 — 公开 DWS 真人账号参考与项目资料整理
- [公开参考目录](../../docs/references/README.md)、[固定来源及摘要](../../docs/references/catalog.json)、[采用清单](../../docs/references/adoption-plan.md)、[架构/身份](../../docs/architecture/dingtalk-agent-middleware.md)、[6项资料核验](../../evidence/2026-11-12/public-reference-catalog-validation.json)。12公开仓库及1套官方协议文档、69文件；逐文件SHA/字节/固定来源、许可文件及21产品模块/原验收不变已核。官方网页与Markdown表示的URL首轮相等断言失败已保留并按精确URL对修正，源字节未变。
- 用户纠正本地研究优先级后，活动catalog移除两份本地WeCom参考；Qwen DWS为通道主体参照，CEO文件/原生回执专项、DSH/缓存部分参考，bot不替换真人身份。第三方实现未移入、上游测试未执行、真实DWS/UI为0；新四runtime适配器未实现，群/auth login缺口保持。README旧E074待决已纠正到E089一次成功与E090未授权；服务/配置/暂停未改。

## E093 — 采用社区文件摘要门槛并验证中间件接缝
- [采用记录](../../docs/references/artifact-digest-adoption.md)、[11新增/三环境291与12冻结核验](../../evidence/2026-11-12/artifact-digest-adoption-validation.json)。Qwen消息/引用接口不足以替代现有原件模型，未整体搬入；CEO固定bd3de36的MIT摘要校验适配到gateway/CLI/HTTP/Bridge，许可证按字节保留并随wheel打包。
- 旧代码已复现排队后修改文件仍confirmed；新任务绑定原SHA，旧未终态队列只采用原任务证据，缺证不发送；新不符请求不上传/预留，原key则回执优先并只对账。文件/原生图片、重启、回执丢失、源件删除、并发、真实合成HTTP/CLI均已验。首轮5专项断言错误/三套290的3失败/并发探针失败保留；最终独立冻结源、测试、wheel三套各291通过，21模块与六入口匹配。
- 无真实DWS/auth/UI/现场账本迁移，E090旧提案及真实配置未改、未授权恢复。矩阵与PRD未改，新增离线验证不抵消UI缺项；新代码未部署。

### E094｜DWS底座分层定位与官方超时复现

- [诊断](../../docs/99-dws-base-failure-diagnosis.md)、[脱敏证据](../../evidence/2026-11-12/dws-base-failure-diagnosis.json)、[独立Go复现](../../evidence/2026-11-12/dws-keychain-timeout-probe_test.go)。公开OpenAI #60687是用户报告，无已核维护者修复；本机只读日志09:25:20屏幕解锁后SecKeychainLogin -25293，紧邻原两路最后成功同步和Guardian活动。系统故障层已定位，Computer Use因果未定。
- 原字节官方worker/合成子进程复现等待超时但子进程仍活，最后自清理；正常完成对照通过，共2通过/1helper跳过，v1.0.68同Darwin源。未运行官方TestMain/DWS/security，未修改参考仓库或产品，未重跑291项全量。
- 原始系统日志留local/dws-base-diagnosis-20261112，仅固定事件/摘要入Git。真实DWS/Keychain0、未启动服务/心跳；auth login未重测，长期稳定未验收。E028事故前自然预刷新、E089事故后一次成功都保留原范围。优先底座，不新增审批工具或扩上层功能。

## E095 — 用户登录证据、AIC限定恢复与真实文件闭环
- [实测记录](../../docs/100-aic-group-resume-and-files.md)、[22项只读核验](../../evidence/2026-11-12/aic-resume-validation.json)。用户新终端登录截图只留local；精确AIC新群及UI两成员核对，旧企业群退出配置/三库不变、私聊配置不变；E093的21模块原字节加载，三服务history-only恢复。
- veil原生上传TXT/CSV为两消息，普通内容0任务；显式关联唯一Kimi任务，Bash/Python实际求和43，liev回同群四个confirmed回执。CSV/TXT客户端下载、Numbers/TextEdit打开，输入和输出SHA一致。新增群TXT入站/CSV双向三格通过，不称单消息多附件。
- 私聊唯一新任务Python493、72B JSON三回执confirmed，钉钉下载/Finder快速查看及SHA通过；旧8非成功任务保留，实际办公上下文schema2生成，不冒称本轮重测办公API。恢复停transport中断较新history窗口已记录，完成原窗口一次而非删游标。
- 本轮无产品修改/全量重跑；当前40/64格通过、22blocked、2部分，R05补齐后8 MUST仍不完整。原24h故障/维护与两个历史query key保留；心跳PAUSED、服务运行；企业群禁止再测。

## E096 — AIC群原生PNG出站闭环
- [UI/原件记录](../../docs/101-aic-group-native-png.md)、[九项只读核验](../../evidence/2026-11-12/aic-group-png-validation.json)。veil原生发送唯一任务，Kimi实际Python/Pillow生成640×360/4762B PNG并ReadMediaFile；image payload绑定原SHA，三个confirmed。
- liev普通账号原生图片气泡/独立查看器、客户端下载成功、Finder快速查看实际打开，标记/21/22/TOTAL43可见，下载件与产物字节一致。工具超时/0尺寸截图及保存面板输入问题按现场复核，没有重投或配置修改。
- 群PNG出站由部分转通过，当前41/64通过、22blocked、1部分；8 MUST仍有缺口。无产品修改/全量重跑，范围仍仅新AIC群和原私聊。

## E097 — 全部用户需求复盘与CEO源码深挖
- [统一需求/进度/路线](../../docs/102-user-requirements-and-roadmap.md)、[CEO深挖](../../docs/references/ceo-deep-dive.md)、[31文件来源](../../docs/references/ceo-deep-dive-index.json)、[资料与不变性核验](../../evidence/2026-11-12/requirements-ceo-review-validation.json)。直接读取原聊天全部14条用户消息，并结合本聊天纠偏/授权；真人账号、通用runtime、官方/GitHub优先、真实UI和新AIC专用范围统一，不新增验收门槛。
- CEO固定92e360ed，31公开文件逐一核Git blob/大小/SHA；旧bd3de36采用和MIT保持。深入发送事实/文件回执、session归属与兼容性、runtime能力/失败分类及Codex环境，明确已有flock/摘要不能误报缺失；宽松发送审核、业务重试、认证协调和部分清理不采用。C02–C04为下一窄接缝，未复制新产品代码、未运行上游测试或服务。
- 活动TODO旧停机阶段按HEAD原字节归档，架构/采用表/PRD证据列和当前计划一致更新。21产品模块、所有现有测试、配置模板、原17判据和等级不变；矩阵仍41/22/1、MUST6通过/5部分/3未完成。没有新DWS、UI、部署或健康证据，没有改变心跳/服务。当前未完成。

## E098 — AIC群JPEG/WAV/MP4双向闭环
- [真实UI/失败记录](../../docs/103-aic-group-media-and-result-contract.md)、[16项只读核验](../../evidence/2026-11-12/aic-group-media-validation.json)。JPEG真实读图/Pillow旋转，WAV wave/MP4 ffprobe实际分析，原件一致；原生图片/音视频卡片、客户端下载、Quick Look及报告TextEdit通过。新增六格，47/16/1，8 MUST仍不完整。
- AV原任务JSONDecodeError保持failed、无产物发送；独立UI只读交付任务核SHA后交三现有产物。三任务10confirmed；原配置不变。JPEG模型内部两次Pillow调用及客户端.jpg.png命名差异保留，不宣称原生语音/video协议。

## E099 — runtime结果契约与可解释失败
- [实现和边界](../../docs/103-aic-group-media-and-result-contract.md)、[9项冻结核验](../../evidence/2026-11-12/runtime-result-contract-validation.json)。CEO C03设计参考，新增8方法；冻结源码/双Python新wheel各299，21模块/六入口一致。typed错误、exact schema、无解释文字抽取、失败不重放、既有产物及session保留。
- 实际E098触发问题，E099修复错误分类和操作指引，不能保证模型总能给合法JSON；原failed不迁移。当前检查点未重载gateway，真实UI仍E093；下一段仅管理器有界重载gateway、transport保持，再补群长文/控制。

## E100 — E099受管重载及AIC群长文/控制闭环
- [真实UI记录](../../docs/104-aic-group-long-text-and-controls.md)、[21项只读核验](../../evidence/2026-11-12/aic-group-controls-validation.json)。两idle gateway加载e27547b，transport身份/旧账本/session保持；无auth/doctor，未重跑原299。
- veil原生2816字符命令，Kimi真实Python生成60行5699B TXT，5196字符回复分两段，AX全文/首尾视口、客户端下载/TextEdit打开/SHA一致。上下文无工具回答60/1830/2；三条相同status有不同消息ID。
- 实际sleep Python执行中status=1，UI cancel及停止确认、两进程消失、182.588秒无晚文件；同会话下一实际Python1517。UI new后代次1/native session不同，真实Python检查空exports，旧口令不知；旧任务和其他路由不变。10任务/控制、18confirmed，取消保留。49/14/1，R08通过，仍7 MUST未完整。

## E101 — 原24小时记录完整性终检
- [记录与限制](../../docs/105-original-24h-observation.md)、[13项完整性核验](../../evidence/2026-11-12/reliability-original-24h-review.json)。原run达到24h结束，2878样本/205事件/52维护，最大gap30.748秒，0重复事件。
- 1059 unavailable（681 URLError/378 HTTPError）和168 poll_error样本保留。378 HTTPError均仍有health但路由集与旧baseline不同、0事件捕获，符合旧群退出后冻结查询不再适用；原记录没有精确HTTP状态，不猜404或全部DWS宕机。
- 未重置/启动新run；原事件最终账本对照未做、当前AIC部署没有24h覆盖。完整记录不是健康通过，R13仍未完成。

## E102 — CEO发送凭据负例与身份校验
- [官方/社区边界与修复](../../docs/106-send-evidence-contract.md)、[13项冻结核验](../../evidence/2026-11-12/send-evidence-contract-validation.json)。固定CEO源码摘要复核，固定官方投影源码说明first ID与请求task回填边界；新代码/测试自写，不运行上游服务或真实DWS。
- 旧E099冻结产品跑新8方法，22失败子场景；初6方法18失败记录也保留。新core拒绝投影/底层冲突、错task终态、非法/冲突消息ID、被引用源ID、嵌套显式失败/其他契约；仅可信SUCCESS确认，原key重启不重发、原pending和终态竞态保持。
- 冻结源码/同一wheel双Python各307通过，21模块/六入口/许可相同，只有core产品模块变化；13核验通过。无新UI，49/14/1及7 MUST缺口保持。本检查点未部署，下一步受管重载transport并作唯一合成群任务验收，不改E101原观察记录。

## E103 — 回执校验部署与真实群任务
- [部署与UI](../../docs/106-send-evidence-contract.md)、[15项核验](../../evidence/2026-11-12/send-evidence-deployment-validation.json)。3fa5011冻结21模块一致，仅原manager重载transport；两gateway进程、旧任务/回执/投递/session/config保持，三服务运行。
- veil原生新任务一次，Kimi实际Python1387，liev两气泡及AI标识可见；两个不同task/message回执与传输账本一致。两路history维护后完整同步、无poll_error；无auth/doctor、旧key重放或新矩阵通过格。
- 首审计字段误猜导致1项失败留local，改核真实last_sync.at/complete后15项通过。原24h run未改，49/14/1、7 MUST未完整；下一项C03/C04，不重做已过UI。

## E104 — CEO能力/终态与会话兼容性
- [具体实现](../../docs/107-runtime-and-session-contracts.md)、[13核验](../../evidence/2026-11-13/runtime-session-contract-validation.json)。旧冻结4实际合成CLI负例全失败；新增24方法，源码/同wheel双Python各331通过，21模块/六入口/许可与冻结源一致。
- 错session、Codex异常退出、复用旧run/旧输出拒绝；静态能力≠健康，未知错误不凭文字判认证。冻结每任务契约，旧session缺metadata/不兼容明确blocked，new归档历史，不重放。
- 初开发329项1失败/5错误保留；已修二次wait与补办公升级显式审查。真实旧会话未迁移/未部署，三服务仍E103部署；CUA正确bundle两次failedToCreateImageDestination，停止路径，无消息/UI通过增量。49/14/1与7 MUST缺口保持。

## E105 — Codex固定本机参数与新有界超时
- [诊断](../../docs/108-codex-cli-timeout-diagnostic.md)、[记录](../../evidence/2026-11-13/codex-cli-timeout-diagnostic.json)：本机0.164.0完整start/resume帮助解析通过；新任务唯一一次，60.110秒超时，CLI内部Reconnecting2/5，只有thread/turn started+error，无工具/产物，守护清理完成。
- 未改配置/HOME/凭据/模型，旧日志保持；不推定根因，不重试或提高timeout，不计第二runtime/新UI。产品仍E104候选、部署仍E103。

## E106 — 原观察已采事件与后续账本一致
- [结果/边界](../../docs/109-observation-ledger-reconciliation.md)、[8核验](../../evidence/2026-11-13/observation-ledger-validation.json)：205捕获事件完整同seq/正文/账号/会话匹配，采样区间行集合一致；之后4行单列，不能按消息时间倒推入库截止。
- 原四文件SHA与E101相同，52维护/13带局部版本字段及旧故障保持。新4专项源码/双Python旧E104wheel均通过，产品21模块不变；无335全量主张、真实调用或UI。原窗口全量截止与当前AIC长期覆盖仍不足，R13不改绿。

## E107 — 真实业务暂停的只读证据
- [当前状态](../../docs/110-interrupted-history-current-state.md)、[快照](../../evidence/2026-11-13/interrupted-history-snapshot.json)：三个进程仍running，但闩为dws_process_interrupted、mtime09:33:56，slot0 active/slot1 ready；两slot lsof未报告句柄，两路last_sync约09:33且窗口未完。
- 已入库0未知投递不代表远端无积压；本轮真实DWS0/恢复0，守护文件与配置未改。只存state/reason缺归属阶段，不能推定Keychain复发或精确根因；E104仍未部署。该状态覆盖旧“可用”快照，下一项只读/合成诊断，不盲目清闩。

## E108 — 调用归属日志与有界恢复准备
- [实现/恢复次序](../../docs/111-dws-interruption-recovery.md)、[9冻结核验](../../evidence/2026-11-13/dws-call-journal-validation.json)：6新增方法、源码/同wheel双Python各341，21模块一致。真实合成SIGKILL及释放落盘失败复现active残留；不外推为本次最初中断根因。
- 用户明确授权本轮恢复，三服务已受管停止、任务/会话备份，0未决投递/执行；仅同AIC/原私聊。当前未清闩/调用，下一步固定cut补读、停机积压审查、原session迁移及UI。


## E109 — AIC/私聊真实恢复及契约部署
- [恢复记录](../../docs/111-dws-interruption-recovery.md)、[25项当前状态核验](../../evidence/2026-11-13/dws-recovery-deployment-validation.json)。用户最新指令授权执行；首次只完成旧窗口，误用last_sync.at判定cut；停机审查本地零积压后提前启动gateway。后续按持久watermark核实两路已覆盖cut且无未完窗口，旧82任务仍全部未变；原门槛失败保留。
- 审查E103原进程/旧E099配置后显式迁移两session，82任务/旧回执保持；三个服务加载997e9fa冻结21模块，DWS ready。两个新合成出站均confirmed，官方history正文/自身身份一致，consumer已收且无新任务；28真实调用短时检查点无新故障。
- CUA重置后仍图像创建错误，未取得新客户端UI；未冒称veil入站任务或新版下载打开通过。旧矩阵/长期故障保留，下一步工具恢复后新任务真实UI，不重复探针、resume、登录或钥匙串。


## E110 — 已解锁桌面下的UI服务阻塞
- 用户确认解锁，钉钉直接/重置后两次与Finder独立绑定均failedToCreateImageDestination；0输入/发送/新DWS探针，不是新UI通过。[记录](../../evidence/2026-11-13/unlocked-desktop-ui-blocker.json)。
- 本地日志没有进一步根因；13:02三服务/两路同步/DWS ready。官方泛用指引建议重启应用，未保证修复该错误；下一动作仅用户正常重开Codex，不碰Mac重启/权限/凭据。产品仍997e9fa，无新测试，原341冻结不重跑。


## E111 — 官方续期反馈、版本差异及用户重启
- [研究](../../docs/112-dws-refresh-and-reboot-review.md)、[摘要](../../evidence/2026-11-13/auth-refresh-reboot-review.json)：官方2h/30d自动续期，#1132明确v1.0.62修复；终端v1.0.61与bridge v1.0.67构建revision静态核对，v68无auth/Darwin改动。Codex#60687仍open，不能当已确认根因。
- 用户重启后三服务停止、guard ready但slot0 active；829 invoking/828 released，未释放history可定位，非认证失败证明。CUA可重新读取钉钉；未发送/恢复、无新任务或UI文件通过，无DWS/auth/Keychain调用。


## E112 — 重启补读、运行器网络调整与真实UI
- [恢复及验收](../../docs/113-reboot-recovery-and-runtime-network.md)、[34核验](../../evidence/2026-11-13/reboot-recovery-ui-validation.json)。首次会话读取request_timeout保留；成功业务读后，固定cut补读、gateway停机核积压、三服务恢复，82旧任务/session/回执保持。
- 两条E112真人任务遇Kimi OAuth连接超时，失败提示均UI可见，未执行工具/交付/重做。现有系统代理与父环境差异核实后，独立13.68秒成功，只重载两gateway继承代理，原transport不动。
- 两新E112B任务Python1517/1003、旧session1387/493、liev文字/文件、客户端两下载件Quick Look及SHA通过；10回复confirmed且history一致。产品21模块仍997e9fa，未重跑341；49/14/1不变，长期和全项目仍未完成。

## E113 — 主线产出整理、风险根因与当前入口纠偏
- 用户要求整理项目主线/剩余工作/产出/踩坑；[统一总览](../../docs/102-user-requirements-and-roadmap.md)、[DWS风险表](../../docs/114-dws-risks-and-resolution.md)、[接入经验](../../docs/11-onboarding-lessons.md)已更新。E112是最近真实现场，本轮不运行DWS/auth/Keychain/服务/UI，不增加通过格。
- [公开来源复核](../../evidence/2026-11-13/mainline-risk-review-sources.json)：#1132 closed且维护者v62说明、#60687 open且未获官方因果确认、最新release v68；未升级或发布外部消息。D01系统根因、D02取消缺口、D05暂停、D07执行器网络等分开，恢复/止损不叫根治。
- E097–E107旧状态从活动入口移除；C03/C04已部署/UI通过，下一段P0启动环境/安全错误信封/当前长期观察。原PRD判据/级别、14MUST判定、64格状态及产品/测试字节保持；[文档核对结果](../../evidence/2026-11-13/mainline-risk-review-validation.json)。历史失败、reliability及E075旧包范围保持。

## E114 — 原长任务心跳恢复与阶段执行门槛
- 用户要求安排长过程闭环；复用bridge，官方工具update为ACTIVE、每30分钟，并读回原target/配置核实；没有重复任务、新线程、子Agent或另一目标系统。[调度证据](../../evidence/2026-11-13/long-run-resume.json)。
- Rose文件化续作沿用本目录，M1环境、M2错误、M3观察、M4剩余UI、M5执行器、M6封版及阻塞转项/退出条件见[里程碑](09-执行时序与里程碑.md)。本轮仅安排执行，无新DWS/产品/UI验收，最后业务现场仍E112，原49/14/1及7 MUST不完整。

## E115 — runtime环境持久配置与DWS安全错误诊断
- runtime.environment只配置子进程网络变量，大小写统一/空值清除/回环绕过/合法性校验，原身份和session保持；聊天及办公受管日志增加安全结果分类、exit/耗时，不改变回执与自动重试策略。
- [说明](../../docs/115-runtime-environment-and-dws-diagnostics.md)、[冻结证据](../../evidence/2026-11-13/runtime-environment-diagnostics-validation.json)：16新增方法；冻结源码/同wheel Python3.14及3.11各357通过，11核验、21模块/六入口/许可一致。初轮2产品失败已修；冻结测试布局15失败/2错误已纠正，原日志保留。
- 尚未部署，本段之后立即按当前授权受管重载及两路真实UI任务/文件下载打开。旧Keychain根因和长期可靠性未关闭，测试不产生真实DWS调用。

## E116 — 无代理manager启动、持久配置生效与双端UI
- 87a3d39实际部署，保留86旧任务、回执及原session。先停gateway、封新调用排空后停transport；固定cut补读达watermark且无history_window，再停机核0积压，恢复三服务。
- veil原生UI在AIC/原私聊交办两新任务，实际Python及环境读取：1517→2021/TXT 47B、1003→1159/JSON 68B，env_ready=true。liev六回复confirmed/history回读，两个原件从钉钉下载并Quick Look打开/SHA一致。
- [记录](../../docs/116-persistent-environment-deployment-ui.md)、[38核验](../../evidence/2026-11-13/runtime-environment-deployment-ui.json)均过；截止审计58个真实DWS result具exit/阶段/耗时且无错误，不能当自然刷新或健康24h。
- aic-persistent-env-20261113独立24h/30秒只读观察已启动，21模块/配置/manager/六库基线留local，旧reliability保留；项目49/14/1及7 MUST缺口不变。

## E117 — 官方取消缺口双层候选和合成回归
- [候选及限制](../../docs/117-dws-cancellation-candidate.md)、[本地上游草稿](../../docs/118-dws-cancellation-upstream-draft.md)、[脱敏18核验](../../evidence/2026-11-13/dws-cancellation-candidate-validation.json)。固定v67及keyring v0.2.8，只向新local目录应用候选；预检查/读/写同deadline、owned child取消回收、late结果/写保护、Set启动前校验。
- DWS10方法/3子用例、依赖5方法/7子用例，普通与race四次均过；每套1helper正常跳过。最终公共工具核固定源/补丁/测试及完整方法集合，0项/缺方法/失败拒绝；18核验通过。不是bridge新增15项或上游全量通过，原357未重跑。
- 未运行真实DWS/Keychain，未部署/发布，参考源/21产品模块保持；当前三服务与原观察run不变。上游依赖API、旧测试签名、全CLI集成仍需审查；原无效DEK/并发写/读回fallback政策未改。D01根因、49/14/1与7 MUST缺口不变。

## E118 — Codex新环境真实工具、取消失败及显式迁移工具
- [完整记录](../../docs/119-codex-environment-and-cancellation-gap.md)、[脱敏结果](../../evidence/2026-11-13/codex-persistent-env-and-migration-validation.json)。同CLI/60秒，新持久环境实际Python1961/19.64秒、同session1968/17.02秒通过；第三取消任务11.68秒返回后，工具约90秒仍写late，失败保留，不能称Codex可部署。
- veil UI new及liev回执可见，原session归档；第一次切换只到manager runtime binding拒绝，原Kimi已恢复，群/transport不动，两维护记原观察。新增迁移脚本要求停机/显式new/零未决，冻结10专项三环境通过；真实迁移未执行。原88任务及原E105失败保留，21产品模块不变。
- 固定Codex6aaac69源码已找到ctrl_c→turn/interrupt新依据，下一段原生中断及晚写验证，之后再UI。guard cleanup_complete只能证明原进程组，早先取消通过口头结论已撤回。

| E119 | L3/L4 | Codex原生中断；旧3失败/新7方法，冻结源码/同wheel双Python374；真实取消4进程退出且延迟无late；显式binding迁移保持89任务 | docs/120；codex-native-interrupt-validation | 三服务部署停机，UI未验；原观察记录混用/维护；非系统根治 |

| E120 | L4/L5 | 0c6f2da部署，AIC Kimi/私聊Codex；89旧任务保持，实际Python1829/同session1836、两文件客户端下载打开SHA、取消104秒无late/4进程退出；9回执history、30核验 | docs/121；codex-deployment-ui-validation | 首次DWS启动API超时保留，原观察维护/混用；非认证根治/自然刷新/24h；七MUST仍缺 |

| E121 | L3 | 固定982ae49干净683manifest、新wheel离线安装/六入口/许可/空状态；与E119产品/测试/scripts/fixtures/integrations逐字节相同，19核验/13离线步骤 | docs/122；current-clean-handoff-validation | 复用374×3不声称新跑，非最终项目验收或真实破坏性回滚；现场不变 |

| E122 | L3/L4 | Pi 0.84.2原生JSON/session/settled/退出契约，22新方法；最终396×3/21模块；本地Read/Write续接与真实Python取消、延迟230秒/4进程；94旧任务binding迁移保持 | docs/123；pi-runtime-validation | 三服务部署停机，待补读与Pi UI；旧fixture失败保留，图片/OpenClaw未验 |

| E123 | L4/L5 | e7d82cc部署，AIC Kimi/私聊Pi；94旧任务保持，实际Python533/同session542、JSON/TXT客户端下载Quick Look/SHA、cancel95秒无late/3自有进程；9回复history、31核验 | docs/124；pi-deployment-ui-validation | 首启3872ms API超时保留，一次有界恢复；非系统根治/自然刷新/24h，Pi图片/OpenClaw未验 |

## E124 — 原观察收尾与Qwen事务强杀边界
- [完整记录](../../docs/125-observation-closeout-and-qwen-transactions.md)、[脱敏证据](../../evidence/2026-11-15/observation-and-transaction-validation.json)：原run自然到期，2879采样/13检查、32捕获事件逐条对账；14不可达/16 poll_error采样/24路由错误/9维护保留，不称健康24h。后续六库保留起点88任务/216 outbox原字段，当前98任务；非截止或六库共同原子快照。
- Qwen固定41a3b9f5 admitted/completed映射现有持久事务，不复制上游源码或弱化落盘边界；新5个SIGKILL方法验证cursor/inbox、job/ack、工具副作用/终态、终态/outbox、provider接收/本地回执，跨两次恢复不重跑工具、原key/payload保持。冻结源Py3.14/原同wheelPy3.14与3.11各5通过；21产品/许可相同，未重跑396全量，未调用真实DWS或修改部署。
- R13真实失效refresh/系统根因和历史截止缺口仍在；49/14/1、7 MUST未完整不变。下一独立项OpenClaw宿主契约，旧UI/原观察/Qwen已过强杀样本不重复。

## E125 — OpenClaw官方入口及无凭据结果函数验证
- [契约与限制](../../docs/126-openclaw-turn-entry-contract.md)、[17文件摘要](../../docs/references/openclaw-turn-contract.json)、[执行证据](../../evidence/2026-11-15/openclaw-entry-contract-validation.json)。官方41f2b981：exec每次randomUUID，无resume选择器；local支持明确session并拒绝外部状态所有者；Gateway持有turn，退出/断连不能当工具停止。当前PATH无OpenClaw，未安装或读取凭据。
- 只import固定官方agent-exec-result.ts，Node26.3.1执行14检查通过，空/变更源码2负例在import前拒绝；仅length或缺stopReason的内部输入仍分类ok，证明不能只用该函数认定完整成功，不据此称真实CLI有截断漏洞。未运行上游全量/完整CLI/取消/续接；产品21模块与现有部署不变。
- [既有DWS日志补证](../../evidence/2026-11-15/observation-existing-dws-diagnostics.json)：原窗口10686响应诊断含40次api/request_timeout，3268–3872ms（38 history、2 other）；窗口后截至本次读取7830诊断含30次history同类错误，3266–3395ms。全部exit1/stage=request/providerExecutionStarted=false；与周期采样分母不同，不抵扣或替代原16错误采样，不推断DNS/TCP/代理/认证根因或自然刷新。无新增真实探针。


## E126 — OpenClaw完整本地宿主与隔离边界
- [记录](../../docs/127-openclaw-local-host-validation.md)、[证据](../../evidence/2026-11-15/openclaw-local-host-validation.json)：固定41f2b981/36文件；65,102源文件未改，local构建成功。9个CLI样本验stdin/续接/跨state、Python499/JSON、锁拒绝、SIGINT130/期限1、7自有进程及28/13秒无late、length exit0/显式partial、null原始finish规范化stop。
- 冻结21检查20过/1guard元数据误计，原exit1不改；独立24复核、5篡改反例及2源固定负例通过。全新profile避免App凭据命名空间，早期token open前被阻止；login-shell PATH探测保持拒绝，不称任意配置或OS沙箱已安全。无产品/服务/真实模型/UI变更，49/14/1及7 MUST保持。下一段薄适配/绑定和终态回归，不重跑旧观察/Qwen/UI。
