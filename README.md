# DingTalk Agent Bridge

> E107当前：三个受管进程运行，但DWS业务调用因dws_process_interrupted持久暂停（11月13日09:33的记录），两路history窗口待核，远端积压未知。E104运行器/会话契约已实现，冻结源码/双Python各331通过，尚未部署；E105 Codex60秒请求仍超时，CUA绑定图像错误阻止新UI。E106205条已采事件与后续账本一致，不能称健康24h。49/14/1、7 MUST未完整，心跳PAUSED。[当前状态](docs/110-interrupted-history-current-state.md) · [代码与边界](docs/107-runtime-and-session-contracts.md)。

通用普通账号IM工具：通过CLI、HTTP或持久consumer承接群聊/私聊文字、文件和任务，可选本地Agent执行并把结果交回原会话。接口不绑定组织或runtime。当前本机Kimi已实际接通，Codex超时独立跟踪；没有创建bot。

选型优先采用公开GitHub/钉钉官方实现：**官方DWS做通讯底座，Qwen作通道组件参照，CEO作任务/交付/执行器契约参照**。默认DWS授权真人账号；bot项目仅参考可拆交互。[统一需求与路线](docs/102-user-requirements-and-roadmap.md) · [CEO源码深挖](docs/references/ceo-deep-dive.md) · [参考目录](docs/references/README.md) · [文档导航](docs/README.md)

**项目尚未完整验收；E095曾恢复两路，E107当前受管调用再次暂停。** 用户提供liev登录成功截图，并限定群测试只在新建AIC测试群；企业大群及旧群禁止再测。E095已完成精确绑定、保留旧账本、history补读审查和三个服务恢复；心跳仍PAUSED。截图原件仅local，Git保存脱敏摘要，见[本轮实际验收](docs/100-aic-group-resume-and-files.md)。
## 当前实现与验证

- E103传输加载E102/3fa5011，gateway保留E099/e27547b，包含E070群文件关联、E072/E073受管防护、E084持久history续页；与冻结源码一致，双路history-only15秒补读，无Stream消费者。官方共享bus不杀，foreground不当消费者。
- E092整理13项公开参考来源、69份选摘文件的固定版本/摘要/许可，明确采用边界；没有运行上游服务/测试、移入其实现或新增UI通过项。本地WeCom资料不作为当前选型依据。
- E093实际采用社区的[文件摘要校验](docs/references/artifact-digest-adoption.md)，补上排队后产物变更缺口。新任务file/image携带原定SHA256，已发送原key继续对账；MIT许可随包保留。11项新增专项，最终源码/双Python安装包各291项、12项冻结核验通过；E095部署同一源码，本轮未重跑全量。
- E095新增群TXT入站/CSV双向三格，Kimi求和43、CSV/TXT由钉钉下载并打开；私聊493/JSON也通过。E098媒体及E100长文/控制补验后，当前矩阵64格：49通过、14阻塞、1部分；14项MUST仍7项未完整覆盖。API、工具执行、UI可见和客户端下载打开分别取证。[只读声明核对](docs/91-acceptance-coverage-review.md)不代替原始证据复核。
- E075交接包固定f0d2911，包含已验E073 wheel和当时539项manifest；未包含后续变更。仅local/handoff-f0d2911-20261112/bundle为payload，父目录与其他local内容不得分享。[冻结交接](docs/80-offline-handoff-export.md)

## 使用与事实边界

veil是客户端真人用户，liev经显式profile绑定的DWS普通账号回复，界面显示liev和“通过AI发送”；`[Agent]`只是前缀。历史两账号群/私聊的基础闭环已有证据。当前唯一群测试范围为用户新建AIC测试群，成员2人已核；原私聊授权保持，企业大群和旧群禁止再测。

官方DWS负责身份、通讯/历史、资源及办公API；bridge补路由、白名单、队列、会话、幂等、文件与恢复。固定v1.0.67缺本地CHAT_IMAGE上传叶子，隔离补充复用官方源码鉴权/上传，不改原版binary。原生PNG/JPEG≤2MiB，更大图片走file；bridge输出单文件20MiB。WAV/MP4文件和客户端播放不等于原生语音条或独立video协议。

独立部署需要Python≥3.11/POSIX和自己的官方DWS身份配置；当前只在macOS实机验过。配置模板不含账号数据，不能直接作为健康探针使用。CLI/HTTP/consumer可独立使用；本地执行器、提示词和办公wrapper不是OS沙箱。

| 需要了解的内容 | 入口 |
|---|---|
| 当前任务、授权、禁止项 | [AGENTS](AGENTS.md) · [关键路径](plans/completion/CRITICAL_PATH.md) |
| 需求与逐格证据 | [PRD](plans/completion/01-PRD.md) · [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) |
| 当前进度 | [E097需求/进度/规划总复盘](docs/102-user-requirements-and-roadmap.md) · [活动任务表](plans/completion/TODO.md) |
| 安装、运行、恢复 | [运行手册](docs/15-service-runbook.md) · [通用工具契约](docs/22-generic-tool-and-consumer.md) |
| 官方与自研边界 | [边界研究](docs/25-official-boundary-and-scenarios.md) · [办公入口及共享bus](docs/89-supervised-official-office-entrypoint.md) |
| 公开参考与执行器接入 | [官方/GitHub参考](docs/references/README.md) · [中间件架构](docs/architecture/dingtalk-agent-middleware.md) · [官方Agent接口](docs/architecture/agent-integration-map.md) |
| 事故与防护 | [事故记录](docs/87-authentication-popup-incident.md) · [受管进程](docs/88-dws-process-containment.md) |
| 证据与历史 | [EVIDENCE](plans/completion/EVIDENCE.md) · [推进账本](plans/completion/PROGRESS_LEDGER.md) · [旧入口原文](docs/history/through-E076/README.md) |

以下只读取本地文件，不调用DWS；当前覆盖命令返回2表示仍有验收缺口：

```bash
python3 scripts/review_acceptance.py --require-covered
python3 scripts/verify_handoff.py
```

产品回归使用`python3 scripts/run_tests_with_evidence.py`，仅在变更需要时运行。旧UI实验按各自冻结版本只读复核，不重复发送。原reliability-20261111的故障和维护全部保留，真实时长届满仍需判定完整性与失败处置，不能宣称连续健康24h。

代码、合成fixtures、脱敏evidence与文档可入Git；身份、凭据、原聊天/AX/截图、日志、数据库和下载件只留local。未知投递同key对账，禁止换key或UI补发。当前分支codex/complete-bridge，无远程发布；MUST/UI与完整自检未全部满足前不标完成、不停heartbeat。

E096又补齐AIC群[原生PNG交付](docs/101-aic-group-native-png.md)：Kimi实际Pillow生成、原生图片气泡/查看器、客户端下载/Quick Look、原件SHA一致。群JPEG/WAV/MP4文件、长文/控制随后E098/E100已过，其他原生协议/引用/组合缺口仍保留。
