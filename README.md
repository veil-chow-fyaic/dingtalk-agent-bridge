# DingTalk Agent Bridge

通用钉钉IM工具，让本地Agent通过CLI或HTTP承接群聊/私聊任务、文件、多轮上下文并将结果回传原会话。接口不绑定组织或runtime；当前本机Kimi已真实接通，Codex adapter保留但请求超时，至少一个执行器门槛已满足。

当前使用普通真人账号：veil在钉钉客户端交办，liev经DWS `--as user`回复，界面显示liev和“通过AI发送”。没有创建bot。原两账号群和私聊的基础双向路径已验；原群后来增加第三人，新增群实验等待范围答复，私聊继续。

**项目尚未完整验收。** E059 Python3.14及最低3.11隔离wheel各191项及新venv六入口/19模块通过；E039旧错误及E059首次全量1个manager关闭错误仍未定位，不能代替未完成的UI格子。E046已补通用父进程守护，真实私聊SIGKILL gateway后自动清理工具、越过期限无晚写、只读核验完整回复UI通过；原中断任务不自动重做。原24h观察于11月11日19:36:08启动，最早11月12日19:36后评估，历史故障和维护保留。

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
- 最新：[历史UI审计与冻结安装版本](docs/66-frozen-install-audit-boundary.md)；[启动前拒绝无效执行时限](docs/65-finite-runtime-deadlines.md)；[真实超时、同进程恢复及最低Python安装验证](docs/64-runtime-timeout-and-installed-wheel.md)；[gateway崩溃后自动清理及真实私聊核验](docs/63-runtime-parent-death-guard.md)；[崩溃结果不确定提示与工具遗留实证](docs/62-crash-recovery-uncertainty.md)；[合成语音经官方听记与报告交付](docs/61-official-minutes-ui.md)；[个人钉盘真实交付与会议下线边界](docs/60-official-drive-and-conference.md)；[真实工具运行中停止gateway及恢复](docs/59-active-gateway-stop-ui.md)；[附件原名与Unicode CSV实际处理](docs/58-attachment-metadata-unicode-csv.md)；[运行器后代清理与真实私聊回归](docs/56-runtime-process-group-cleanup.md)，最终全量中的2个manager关闭错误保持未解决；[EXIF方向6原件与真实归正/下载打开](docs/55-exif-orientation-ui.md)、[错误SHA的明确更正](docs/52-sha-correction-ui.md)、[引用来源元数据修复](docs/53-quoted-source-identity.md)、[21MiB超限提示→新压缩任务→ZIP客户端下载解包](docs/54-output-limit-and-compressed-recovery.md)。原错误/failed记录保留。

[固定版发送组合契约](docs/73-official-send-composition-contract.md)已用18个无账号dry-run核验：重复`--file`只取最后一项，正文与文件互斥，audio/video仍为file，本地图文最多9个引用。46审计/9负向通过；这是CLI计划证据，单消息普通多附件及原生语音仍未通过。

官方DWS负责认证、通讯/历史/资源及办公API；bridge补路由、执行队列、会话、文件、幂等及恢复。固定官方v1.0.67缺本地CHAT_IMAGE上传叶子，隔离补充复用其源码鉴权/上传；≤2MiB PNG/JPEG走image，较大图片走file，bridge输出单文件上限20MiB。官方bot的dev connect/OpenClaw/数字员工是另一身份路线，不能与普通账号混同。

[官方办公接入](docs/41-official-office-agent-ui.md)已完成doc/todo/calendar/未发送draft代表性任务；只对DM显式启用、默认关闭，不是权限沙箱。WeCom/Slack/Telegram参考及适用范围见[WeCom对照](docs/03-wecom-reference.md)、[runtime边界](docs/21-existing-runtime-integration.md)、[本地接入](docs/24-local-agent-product-and-acceptance.md)；开通见[经验手册](docs/11-onboarding-lessons.md)。

E052真实UI：[并发对账终态保护与真实私聊交付](docs/69-monotonic-reconciliation-and-ui.md)。Python3.14/最低3.11隔离wheel各177项；新的145B JSON任务已实际执行、回复可见、客户端下载并打开。

E053：[异常消息隔离](docs/70-malformed-message-isolation.md)，防止坏引用/附件结构阻塞整批入站。双Python各179项及302条旧官方事件等价回放通过；无新UI发送。

最新失败与验证：E061两个真实独立进程恢复用例通过：同路由锁拒绝、不同路由并行、持锁进程SIGKILL后confirmed保持/执行中转unknown，同key两次重开均不重发。源码/3.14安装包195项通过，3.11全量195项有1个新manager错误，已保住同次ps：TERM后同启动时间的?Es及括号短命令；未改产品/现场或新增UI。 [证据](docs/78-route-process-recovery.md)

此前验证：E060新增清理前诊断测试入口；源码与E059同一已安装产品在Python3.14/3.11各193项通过，每套7份预期负向拒绝记录均保住同次观察，29项审计通过。16次限定真实合成进程复核未复现E059关闭错误，根因仍未解；产品/现网未改、无新UI。 [诊断入口](docs/77-manager-test-evidence-retention.md)

最新修复：E059清单原子提交：真实子进程短写复现旧缓存损坏，同目录0600临时文件写入/fsync/replace后冷/热缓存恢复、提交前SIGKILL保旧通过；2新方法、源码及双Python安装包191项、50缓存57资源只读与28审计，三进程空闲加载。首次全量仍有1个manager关闭身份错误，其精确ps因测试清理丢失，未宣称解决；无新UI。 [报告](docs/76-atomic-download-manifest.md)

此前修复：[附件完成结果调度](docs/74-media-completion-scheduling.md)，避免快速完成结果被下一消息丢弃；4个新增回归、旧wheel两项失败复现、双Python安装包各184项及24审计通过，双gateway空闲加载。无新UI验收。

此前修复：[附件缓存清单完整性](docs/71-download-cache-integrity.md)，六种合成损坏拒绝及显式repair通过，48份既有缓存/55资源只读验证、双Python已安装包各180项通过，无新消息。

最新真实UI：[附件下载故障恢复](docs/72-attachment-download-outage-ui.md)。私聊下载HTTP故障115.987秒，状态命令可用；原附件无需重发/重启完成真实Python处理，192B JSON客户端下载打开，52审计/8负向通过。

## 运行与复核

现行步骤已与已安装命令及HTTP实现逐项核对，见[交接契约复核](docs/67-current-handoff-contract.md)：18帮助/33既有测试通过；旧运行/工具说明已单独存档。[中文与空格路径验证](docs/68-unicode-workspace-install-validation.md)另通过64项既有测试、新同wheel安装六入口及只读doctor。

使用当前checkout。传输监听127.0.0.1:18768，两路官方Stream提示唤醒history、15秒补读，群/私聊各一个Kimi gateway，仅允许已配置发送者。无开机自启；Kimi没有OS级沙箱。现有三个进程由service_manager管理，旧ctl/PID文件不再控制当前部署。

```bash
python3 -m dingtalk_bridge.service_manager status
python3 -m dingtalk_bridge.doctor --agent-config local/agent-config.json --agent-config local/agent-direct-config.json --live
python3 scripts/accept_exif_ui.py
python3 scripts/run_tests_with_evidence.py
python3 scripts/verify_handoff.py
```

以上不发送消息；现场审计需要本机local证据，单元测试和安装不需账号数据。启动/停止详见运行手册，start需显式选入两个gateway配置。未知投递先按原key对账，禁止换key/切UI重发；不要为复核重跑写入实验。

## 共享边界

产品、测试、合成fixtures、脱敏evidence与文档可交接；`local/`包含账号配置、令牌、聊天/AX/截图、数据库、日志和下载件，**不得整包分享或入Git**。manifest记录共享文件摘要，提交钩子扫描暂存blob中的账号ID、令牌和私密路径。

当前分支`codex/complete-bridge`，基线标签`baseline/ui-2026-11-11`，未远程发布。`plans/completion/`是唯一活动计划；heartbeat继续，所有MUST、真实24h与完整自检满足前不标完成。过时入口全文已按字节移入[历史存档](docs/history/through-E035/README.md)，原实验文档保留其日期和版本。
