# DingTalk Agent Bridge

通用普通账号IM工具：通过CLI、HTTP或持久consumer承接群聊/私聊文字、文件和任务，可选本地Agent执行并把结果交回原会话。接口不绑定组织或runtime。当前本机Kimi已实际接通，Codex超时独立跟踪；没有创建bot。

**项目尚未完整验收，当前真实服务停止。** E071认证弹窗事故后用户已确认弹窗停止；三个服务和operator_suspended保持，真实DWS/auth/doctor/Keychain禁用。E074一次只读核验已提问待决，成功也不包含后台恢复；具体步骤见[单次方案](docs/90-guarded-recovery-read-plan.md)。

## 当前实现与验证

- E070群文件显式关联、E072持久暂停与进程清理、E073官方办公受管入口已提交，尚未部署。官方共享Stream bus无独占退出权；候选恢复使用已有history-only 15秒补读，现场配置未改。
- E074源码及Python3.14/3.11隔离安装包各244项，21模块与同一wheel匹配；E076另为验收核对工具5专项三环境。既有结果不是本轮新UI通过，也不拼成执行249项。
- 当前矩阵64格：37历史通过、25阻塞、2部分；14项MUST仍9项未完整覆盖。API、工具执行、UI可见和客户端下载打开分别取证。[只读声明核对](docs/91-acceptance-coverage-review.md)不代替原始证据复核。
- E075交接包固定f0d2911，包含已验E073 wheel和当时539项manifest；未包含后续变更。仅local/handoff-f0d2911-20261112/bundle为payload，父目录与其他local内容不得分享。[冻结交接](docs/80-offline-handoff-export.md)

## 使用与事实边界

veil是客户端真人用户，liev经DWS `--as user`回复，界面显示liev和“通过AI发送”；`[Agent]`只是前缀。历史两账号群/私聊的基础闭环已有证据。原3人群曾获许可，但最新聊天入口要求多人实测暂跳过；私聊已有授权保持，后续按最新范围执行。

官方DWS负责身份、通讯/历史、资源及办公API；bridge补路由、白名单、队列、会话、幂等、文件与恢复。固定v1.0.67缺本地CHAT_IMAGE上传叶子，隔离补充复用官方源码鉴权/上传，不改原版binary。原生PNG/JPEG≤2MiB，更大图片走file；bridge输出单文件20MiB。WAV/MP4文件和客户端播放不等于原生语音条或独立video协议。

独立部署需要Python≥3.11/POSIX和自己的官方DWS身份配置；当前只在macOS实机验过。配置模板不含账号数据，不能直接作为健康探针使用。CLI/HTTP/consumer可独立使用；本地执行器、提示词和办公wrapper不是OS沙箱。

| 需要了解的内容 | 入口 |
|---|---|
| 当前任务、授权、禁止项 | [AGENTS](AGENTS.md) · [关键路径](plans/completion/CRITICAL_PATH.md) |
| 需求与逐格证据 | [PRD](plans/completion/01-PRD.md) · [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) |
| 当前进度 | [执行摘要](docs/13-roadmap-and-backlog.md) · [需求回顾](docs/17-requirements-progress-review.md) |
| 安装、运行、恢复 | [运行手册](docs/15-service-runbook.md) · [通用工具契约](docs/22-generic-tool-and-consumer.md) |
| 官方与自研边界 | [边界研究](docs/25-official-boundary-and-scenarios.md) · [办公入口及共享bus](docs/89-supervised-official-office-entrypoint.md) |
| 参考与执行器接入 | [WeCom](docs/03-wecom-reference.md) · [runtime边界](docs/21-existing-runtime-integration.md) · [本地Agent](docs/24-local-agent-product-and-acceptance.md) |
| 事故与防护 | [事故记录](docs/87-authentication-popup-incident.md) · [受管进程](docs/88-dws-process-containment.md) |
| 证据与历史 | [EVIDENCE](plans/completion/EVIDENCE.md) · [推进账本](plans/completion/PROGRESS_LEDGER.md) · [旧入口原文](docs/history/through-E076/README.md) |

以下只读取本地文件，不调用DWS；当前覆盖命令返回2表示仍有验收缺口：

```bash
python3 scripts/review_acceptance.py --require-covered
python3 scripts/verify_handoff.py
```

产品回归使用`python3 scripts/run_tests_with_evidence.py`，仅在变更需要时运行。旧UI实验按各自冻结版本只读复核，不重复发送。原reliability-20261111的故障和维护全部保留，真实时长届满仍需判定完整性与失败处置，不能宣称连续健康24h。

代码、合成fixtures、脱敏evidence与文档可入Git；身份、凭据、原聊天/AX/截图、日志、数据库和下载件只留local。未知投递同key对账，禁止换key或UI补发。当前分支codex/complete-bridge，无远程发布；MUST/UI与完整自检未全部满足前不标完成、不停heartbeat。
