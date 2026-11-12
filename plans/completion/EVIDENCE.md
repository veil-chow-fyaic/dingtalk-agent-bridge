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
