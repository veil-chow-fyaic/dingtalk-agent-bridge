# 钉钉 bridge 工作约定

E125当前状态（2026-11-15）：OpenClaw官方41f2b981的17份入口/宿主源码已固定；agent exec每次新session，不能用state-dir冒充续接，优先核agent --local的明确session/独占状态契约。原结果分类函数14检查及2源码篡改负例通过，另2不完整输入边界保留；不是完整CLI/取消/续接或支持声明，未安装/调用OpenClaw或凭据。E124原24h观察已收尾，2879采样/13完整性，14不可达/16错误采样/9维护及缺截止快照保留；88起点任务/216 outbox保持，当前98任务。既有安全日志窗口内40、之后至本次读取30次API超时都仅stage=request，无新阶段根因或真实探针。Qwen5强杀方法×3环境已过，21产品模块仍e7d82cc，最近真实UI仍E123（AIC Kimi/原私聊Pi），本轮无部署变更。49/14/1、7 MUST缺口不变。见[最新契约](docs/126-openclaw-turn-entry-contract.md)。

## 同一项目与当前检查点

只在 `/Users/veil/Projects/dingtalk-agent-bridge` 修改，复用 `codex/complete-bridge`，单Agent，不派生、不另开实现、不改参考仓库、不远程发布。聊天目录仅为入口。先读plans/completion的CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志；同一01-PRD与ACCEPTANCE_MATRIX标准，历史“下一步”不当当前指令。

交付runtime/组织无关的普通账号IM工具：群/私聊双向文字、媒体原件、任务、上下文及同会话交付。CLI/HTTP/consumer不绑定测试组织或Agent。官方DWS负责身份、通讯、历史、资源和办公，bridge补路由、白名单、任务、会话、幂等、文件与恢复。至少一个本地执行器即可；Kimi真工具已满足，Codex已验并保留旧超时/取消失败，Pi E123文字/文件/续接/取消UI已验，Pi图片和OpenClaw未验。公开官方/GitHub优先；CEO任务/交付/runtime契约优先参考，Qwen作通道参照，不转回本地WeCom考古。

E103历史检查点：transport已加载E102/3fa5011的发送凭据校验；两个gateway保留E099/e27547b的结果契约。E102只改core，其他20模块与E099相同。固定源码/同wheel双Python各307通过，21模块/六入口/许可已核；这是E102冻结验证，不反复重跑。三个受管服务运行，history-only15秒，心跳独立保持PAUSED。

E100群长文/上下文/status/cancel/new真实UI及21核验；E103新任务Python1387、两确认回执、真实群UI及15核验。当前49/64通过、14blocked、1partial，14 MUST中7未完整，项目未完成。详见[长文控制](docs/104-aic-group-long-text-and-controls.md)、[发送凭据及部署](docs/106-send-evidence-contract.md)。C03/C04已于E109部署并显式迁移原会话，E112已补新版两路任务/文件UI，E115/E116持久配置和安全错误诊断也已部署/UI通过，下一步当前独立持续观察及剩余协议/执行器，不重做已过样本。

## 授权与身份范围

用户完成新终端dws auth login并提供liev成功截图，随后明确只在专用 **AIC测试群** 测试，原veil/liev两人私聊授权保持。禁止企业大群及旧群测试。此授权覆盖此前停机待许可和多人暂跳过，不再索取第二账号或旧恢复许可。新群精确路由/白名单已绑定；旧企业群退出活动配置，原库留存；不加第三人、不建bot、不改权限。

veil是客户端真人用户，liev是显式profile绑定的DWS真人普通账号，UI显示liev和“通过AI发送”；[Agent]只是前缀。不跟随默认账号切换，普通账号权限不外推跨组织。测试群只是配置，不是固定产品组织。

群普通消息/文件只收不执行，需/agent；群文件用--files明确关联，私聊白名单可交办，自身回复不触发。未知投递只按原key对账，不换key或UI补发；失败、取消、拒绝及历史unknown处理证据全部保留。

## 认证事故与受管调用

用户登录和真实业务恢复已证，旧事故不再当主线卡点；系统故障与不确定因果保留，不宣称根治或跨设备长期稳定。助手仍禁止auth/login/doctor真实诊断、系统Keychain读取/锁定/解锁、file-DEK/reset/删凭据/复制token/改权限/重启Mac及绕过SecurityAgent/Terminal工具限制。不索取密码、弹窗名称或第二账号。

正常受管DWS业务调用沿用官方凭据机制；持久暂停、最多两并发、90秒请求加最多15秒清理，办公六族同样走wrapper。凭据故障则暂停，不自动恢复/反复认证。两个一次查询key（dab-auth-read-20261112、dab-auth-read-fixed-20261112）已消费，原receipt保留，禁止重试或换key。

官方Stream bus按身份共享并Setsid脱组，无独占退出权，不杀共享bus，不用foreground冒充消费者。当前history-only不启Stream。守护和运行器不是OS沙箱，不保证恶意脱组/系统失效隔离。127.0.0.1:18768及三个服务由原manager归属管理，无开机自启，不按旧PID发信号。E116两gateway从私有runtime.environment读取已有HTTP(S)代理，manager无代理变量启动的两路真实工具已验；transport配置未变，产品默认不固化本机代理端口。

## 文件、参考与证据边界

- 官方binary固定local/bin/v1.0.67，不静默升级。CHAT_IMAGE上传窄叶子复用固定官方源码认证/上传，不改原binary；PNG/JPEG≤2MiB用image，更大用file，输出单文件20MiB。
- WAV/MP4原件和播放器通过不等于原生语音条/独立video协议。E056重复file仅末项、正文/file互斥、图文最多9本地图引用边界保留，无新入口不重复探针。
- DM官方办公上下文启用、群关闭；doc/todo/calendar/mail/drive/minutes固定身份受管。不将新聊天验证外推所有办公API。
- E093 CEO文件摘要已部署；E099结果分类及E102回执一致性已落实。C03能力/终态和C04兼容性已由E109部署/E112真实续接UI通过；C06启动环境及错误观察已由E115/E116完成，下一项当前独立观察及剩余协议/执行器。参考源码不等于上游测试通过。
- 原reliability-20261111窗口11月11日19:36:08至12日19:36:08已结束，E101完整性13检查通过；1059 unavailable/168 poll_error/52维护保留，不重置或称连续健康24h。当前AIC部署长期覆盖、最终账本核对仍缺。新维护另记，不改已封存原run。

## 执行与完成

每段推进代码/工具/真实UI，约45分钟记录证据及准确下一步；同路径两轮无新证据停止重复、转独立项。引用旧右键/坐标/快捷键/设置/侧按钮路径已loop guard，只有新入口才试。API、工具、UI、客户端下载打开分别计证，离线数量不抵消UI。

代码修复有对应验证；安装比当次冻结源码/测试，不能混比HEAD。小步本地提交，verify_handoff先写manifest再核对，verify_privacy扫描暂存blob，git diff --check。账号ID、凭据、聊天、截图、数据库及下载件只留local或私有工具记录，不入Git、不整包交接。

全部MUST/UI、真实故障处置及检出/交接/隐私自检满足才完成并停心跳。当前未完成，E114心跳ACTIVE负责续作；业务服务状态与调度状态分开。正常不变安静，仅实质里程碑、失败、完成或必要用户动作汇报。
