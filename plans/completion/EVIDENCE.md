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
