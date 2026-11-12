# 钉钉 bridge 工作约定

> E100/E101最新检查点：群长文双向、上下文/status/cancel/new完成真实UI与21项只读核验；49/64通过、14blocked、1partial，7 MUST未完整。两个gateway已加载E099/e27547b，transport保持E093身份；冻结源码/双Python各299项是E099原验证。原24h记录完整但有1059 unavailable/168 poll_error，不能称连续健康。下一步CEO C02发送事实负例对照，C03/C04契约与余下UI缺口继续；心跳PAUSED、三服务运行。 见[本轮闭环](docs/104-aic-group-long-text-and-controls.md)。下文旧阶段记录只代表当时版本。

## 同一项目

只在 `/Users/veil/Projects/dingtalk-agent-bridge` 修改，复用 `codex/complete-bridge`，单Agent，不自行派生、不另开实现或改参考仓库。聊天目录仅为入口。先读 plans/completion 的 CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志；验收以01-PRD和ACCEPTANCE_MATRIX为准。历史阶段和旧“下一步”不作为当前指令。

交付runtime/组织无关的普通账号IM工具：群/私聊双向文字、媒体原件、任务、上下文与同会话交付。官方DWS负责身份、通讯、历史、资源和办公；bridge补路由、白名单、任务、会话、幂等、文件及恢复。至少一个本地执行器即可；Kimi真实工具已满足，Codex超时独立跟踪。公开官方/GitHub优先，E097按用户偏好深挖CEO任务/交付/runtime契约，Qwen继续作通道参照，见docs/references；不转成本地WeCom考古或为四runtime重造中间件。

## 最新授权与当前现场（E095）

用户在新终端完成dws auth login并提供liev成功截图，要求回主线快速推进；随后明确群测试恢复，**仅限新建AIC测试群，禁止企业大群及原群测试**。原veil/liev两人私聊授权保持。这覆盖此前多人暂跳过、E090待许可和E094底座优先的历史限制，不重复索取恢复授权。

已受管核精确新群ID/身份、UI成员2人，归档原配置；旧企业群退出活动配置、三库原字节保留，新群独立路由/账本。私聊配置不变。E093/661b67c的21模块已部署，与冻结源码一致。双路history-only每15秒补读，经transport先行/cut审查后两个gateway已恢复；三个服务运行，心跳独立保持原PAUSED。详见[本轮实测](docs/100-aic-group-resume-and-files.md)。

E070显式群文件关联已实际通过：普通两文件不执行，明确命令关联唯一任务，Kimi求和43，CSV/TXT在钉钉下载并用Numbers/TextEdit打开、SHA一致；私聊计算493/JSON下载快速查看也通过。当前矩阵41/64格通过、22阻塞、1部分；MUST仍有缺口，未完成。后续补群媒体/长文/控制，只用新AIC范围，不重放已过实验。

## 认证事故与受管调用

用户登录成功和当前真实业务可用已证，不再把旧认证问题当主线卡点；E094的系统故障和不确定因果保留，不宣称根治或跨设备长期稳定。截图原件/授权地址/账号ID只留local，Git仅摘要。

仍禁止助手重新登录、auth/doctor诊断、系统Keychain读取/锁定/解锁、file-DEK/reset/删凭据/复制token/改权限/重启Mac及绕过SecurityAgent/Terminal限制；不索取密码、弹窗名称或第二账号。普通受管DWS业务调用使用官方凭据机制。故障暂停后不自动恢复或反复要求密码，先记同次证据和止损，不能重复事故处理。

DWS使用持久暂停、最多两并发、90秒请求与最多另15秒清理；官方办公六族也走受管wrapper。守护不是OS沙箱，不能保证恶意脱组或系统失效隔离。官方Stream bus按身份共享且Setsid脱组，无独占退出权，不杀共享bus，不用foreground冒充消费者。当前history-only不启动Stream。

两个历史一次查询key均已消费：dab-auth-read-20261112（E082错误--as失败）、dab-auth-read-fixed-20261112（E089成功）。原receipt保留，禁止重试/覆盖/换key；本轮正常业务恢复不重做旧查询。E090冻结E084的旧提案保持历史，实际恢复按E095新授权/新群/E093执行。

## 身份、文件与运行边界

liev是显式profile绑定的真人普通账号，veil为客户端真人用户；界面显示liev和“通过AI发送”，[Agent]只是前缀，没有创建bot。白名单/profile/selfSenderId固定，不跟随默认账号切换；不加第三人、不扩全组织监听、不建bot、不改成员权限、不远程发布。测试群是配置，不是产品固定组织。

群普通消息/文件只收不执行，需/agent；群文件用--files明确关联，私聊白名单可交办，自身回复不触发。未知投递按原key对账，不换key或UI补发。保留全部历史failed/blocked/cancelled/rejected和错误结论。

- 官方binary固定local/bin/v1.0.67，全局版本保留，不静默升级。图片上传补充只填本地CHAT_IMAGE缺口，复用固定官方源码鉴权/上传、不改原binary；PNG/JPEG≤2MiB走image，更大走file，输出单文件20MiB。
- WAV/MP4原件与客户端播放不等于原生语音条/独立video。官方重复file只取末项、正文与file互斥、图文最多9本地图引用（E056），无新入口不重跑探针。
- DM启用官方办公上下文，群关闭。doc/todo/calendar/mail/drive/minutes受管固定身份，schema2在E095实际工作区生成；不冒称本轮重测全部办公功能。
- 127.0.0.1:18768与三个进程由service_manager归属管理，无开机自启；不凭旧PID发信号。
- 原run=reliability-20261111起点11月11日19:36:08，故障/维护全部保留；满24小时不等于连续健康。E028自然预刷新不等于失效refresh恢复，不改token/时钟造故障。

## 执行、证据与完成

每段实际推进代码/工具/真实验收，约45分钟更新证据与准确下一步；同路径两轮无新证据停止重复。引用旧右键/坐标/快捷键/设置/侧按钮入口已loop guard，只有明确新入口再试。API、工具执行、UI可见、客户端下载打开分别计证，离线数量不能抵消UI缺项。

产品当前冻结验证为E093源码/双Python新wheel各291项、21模块/12核验；本轮部署相同源码，不称重新执行291。E084262/E074244/E075旧交接分别保持历史版本。代码修复选对应验证，文档改动做链接/摘要/隐私核验；安装核冻结源码/当次测试，不混比HEAD。verify_handoff先写manifest再只读核对，verify_privacy扫描暂存blob，git diff --check；小步本地提交。

账号ID、凭据、原聊天/截图/AX/数据库/日志与下载件仅local，不整包交接。最终MUST/UI、真实观察/失败处置、隐私/检出/交接自检全部满足才完成并停心跳。正常未变安静，只汇报实质里程碑、失败、完成或必要用户动作。

E096补齐群PNG出站原生气泡/查看器/下载/Quick Look及SHA一致，九项只读核验；已有样本不重做。下一项只补JPEG/WAV/MP4和群长文/控制，见[记录](docs/101-aic-group-native-png.md)。

E097已复盘原聊天14条用户消息及本聊天全部纠偏，统一入口为[需求与路线](docs/102-user-requirements-and-roadmap.md)。当前8格群媒体/长文尚待测试，另外14 blocked涉及协议/引用/组合、1partial；总41/22/1不变。独立代码工作优先[CEO C02–C04](docs/references/ceo-deep-dive.md)，真实差距才采用；31文件研究不是新UI或上游测试通过。活动TODO已清理，旧停机阶段原文归档，不能重开旧许可流程。
