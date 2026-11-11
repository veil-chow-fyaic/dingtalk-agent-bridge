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
