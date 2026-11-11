# DingTalk Agent Bridge

通用钉钉IM工具，让本地Agent通过CLI或HTTP承接群聊/私聊任务、文件、多轮上下文并将结果回传原会话。接口不绑定组织或runtime；当前本机Kimi已真实接通，Codex adapter保留但请求超时，至少一个执行器门槛已满足。

当前使用普通真人账号：veil在钉钉客户端交办，liev经DWS `--as user`回复，界面显示liev和“通过AI发送”。没有创建bot。原两账号群和私聊的基础双向路径已验；原群后来增加第三人，新增群实验等待范围答复，私聊继续。

**项目尚未完整验收。** 最终全量160项有2个manager关闭身份错误待定位；运行器17项、新venv六入口及18模块摘要通过，不能代替未完成的UI格子。原24h观察于11月11日19:36:08启动，最早11月12日19:36后评估，历史故障和维护保留。

## 当前入口

| 要了解的内容 | 文档 |
|---|---|
| 需求、身份、真实进度 | [当前总状态](docs/17-requirements-progress-review.md) |
| 每一方向/类型是否真的通过 | [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) |
| 下一步、阻塞与结束条件 | [关键路径](plans/completion/CRITICAL_PATH.md) · [执行摘要](docs/13-roadmap-and-backlog.md) |
| 官方能力与自研边界 | [官方边界](docs/25-official-boundary-and-scenarios.md) · [身份与外部会话](docs/18-identity-and-conversation-boundaries.md) |
| 安装、运行与接入 | [只读doctor/安装](docs/35-install-and-doctor.md) · [统一管理器](docs/40-service-manager-and-restart-ui.md) · [运行手册](docs/15-service-runbook.md) · [CLI/HTTP/consumer](docs/22-generic-tool-and-consumer.md) |
| 证据与只读复核 | [EVIDENCE](plans/completion/EVIDENCE.md) · [推进账本](plans/completion/PROGRESS_LEDGER.md) |

## 已有代表性闭环

- [双账号任务与文件](docs/27-two-account-ui-acceptance.md)，[PNG/PDF](docs/28-media-matrix-and-real-events.md)、[DOCX](docs/30-docx-ui-and-reliability-start.md)、[XLSX/ZIP](docs/31-xlsx-zip-ui-acceptance.md)，[原生PNG](docs/33-native-image-bridge.md)、[JPEG实际旋转](docs/48-jpeg-ui-rotation.md)、[WAV/MP4文件](docs/34-audio-video-file-progress.md)。通过范围以矩阵为准。
- [状态/取消/新会话](docs/36-task-control-ui.md)、[长文分段](docs/38-long-text-limit-and-regression.md)、[完整气泡UI](docs/42-long-bubble-native-ui.md)、[拒绝反馈](docs/39-rejection-reconciliation-and-feedback.md)、[私聊出站引用](docs/46-quoted-text-reply.md)。
- [history故障恢复](docs/43-history-network-outage-recovery.md)、[Stream真实断连](docs/44-stream-network-recovery-and-runtime-failure.md)、[自然凭据轮换](docs/47-natural-auth-rollover.md)；不等于失效refresh恢复或24h通过。
- 最新：[运行器后代清理与真实私聊回归](docs/56-runtime-process-group-cleanup.md)，最终全量中的2个manager关闭错误保持未解决；[EXIF方向6原件与真实归正/下载打开](docs/55-exif-orientation-ui.md)、[错误SHA的明确更正](docs/52-sha-correction-ui.md)、[引用来源元数据修复](docs/53-quoted-source-identity.md)、[21MiB超限提示→新压缩任务→ZIP客户端下载解包](docs/54-output-limit-and-compressed-recovery.md)。原错误/failed记录保留。

官方DWS负责认证、通讯/历史/资源及办公API；bridge补路由、执行队列、会话、文件、幂等及恢复。固定官方v1.0.67缺本地CHAT_IMAGE上传叶子，隔离补充复用其源码鉴权/上传；≤2MiB PNG/JPEG走image，较大图片走file，bridge输出单文件上限20MiB。官方bot的dev connect/OpenClaw/数字员工是另一身份路线，不能与普通账号混同。

[官方办公接入](docs/41-official-office-agent-ui.md)已完成doc/todo/calendar/未发送draft代表性任务；只对DM显式启用、默认关闭，不是权限沙箱。WeCom/Slack/Telegram参考及适用范围见[WeCom对照](docs/03-wecom-reference.md)、[runtime边界](docs/21-existing-runtime-integration.md)、[本地接入](docs/24-local-agent-product-and-acceptance.md)；开通见[经验手册](docs/11-onboarding-lessons.md)。

## 运行与复核

使用当前checkout。传输监听127.0.0.1:18768，两路官方Stream提示唤醒history、15秒补读，群/私聊各一个Kimi gateway，仅允许已配置发送者。无开机自启；Kimi没有OS级沙箱。现有三个进程由service_manager管理，旧ctl/PID文件不再控制当前部署。

```bash
python3 -m dingtalk_bridge.service_manager status
python3 -m dingtalk_bridge.doctor --agent-config local/agent-config.json --agent-config local/agent-direct-config.json --live
python3 scripts/accept_exif_ui.py
python3 -m unittest discover -s tests
python3 scripts/verify_handoff.py
```

以上不发送消息；现场审计需要本机local证据，单元测试和安装不需账号数据。启动/停止详见运行手册，start需显式选入两个gateway配置。未知投递先按原key对账，禁止换key/切UI重发；不要为复核重跑写入实验。

## 共享边界

产品、测试、合成fixtures、脱敏evidence与文档可交接；`local/`包含账号配置、令牌、聊天/AX/截图、数据库、日志和下载件，**不得整包分享或入Git**。manifest记录共享文件摘要，提交钩子扫描暂存blob中的账号ID、令牌和私密路径。

当前分支`codex/complete-bridge`，基线标签`baseline/ui-2026-11-11`，未远程发布。`plans/completion/`是唯一活动计划；heartbeat继续，所有MUST、真实24h与完整自检满足前不标完成。过时入口全文已按字节移入[历史存档](docs/history/through-E035/README.md)，原实验文档保留其日期和版本。
