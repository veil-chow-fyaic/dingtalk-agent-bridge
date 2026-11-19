# 当前接手事实

**现场部署和执行归属。** 独立 transport 继续使用 E156 核对的 26 个核心模块 `d444ccf`。首轮试点中原群、私聊各由既有组织 OpenClaw 唯一执行，完整回切的恢复检查确认原两路 gateway 已接回。插件和隔离 Python 侧车来自 `2388a04`（PR #13），原内置 gateway 的任务与会话绑定保留。 [E159 现场收据](../../evidence/2026-11-19/openclaw-resident-live-pilot.json)

**已验范围。** 原生 OpenClaw 用真实模型在群聊和私聊读取原件、写出结果，钉钉收件方核对了正文、文件名和原件摘要。E154 一笔旧群正文没有官方任务 ID 或消息 ID，附件未提交。其输入已执行，固定截止点下按原键隔离；新群任务的成功回执单独保留。 [E155 双路收件](../../docs/155-openclaw-two-route-file-acceptance.md) · [E154 原记录](../../docs/154-openclaw-real-files-and-client-receipts.md)

**接续工作。** 两路已通过真实文件任务、第二轮追问和仅断开钉钉通道后的恢复。积压的一条新私聊在恢复后回复一次。七条本轮物理回执已纳入完整回切审查；后续再次接管和执行中取消分别计证。 [试点收据与操作](../../docs/resident-openclaw-pilot.md#现场验收) · [任务池](TODO.md)

## 较早版本与证据

- E150 是核心 `0e151fb` 的 25 模块部署，当时保留了 99 个任务及 240 条 Agent 发件记录。历史安装、首轮测试失败及复核计数均见原记录。[E150 验收](../../docs/150-native-voice-and-acceptance-scope.md)
- E150 的固定 24 小时观察有 2,877 个样本、29 条路由错误记录。各项已观测错误均有后续同路完整同步；截止覆盖、启动来源检查通过，严格零错误未通过。E156 的 60 秒观察另计。[DWS 风险与恢复证据](../../docs/114-dws-risks-and-resolution.md)
- GitHub 仓库采用 MIT，受保护 main 的合并记录与现场安装版本分别核对。[E156 部署记录](../../docs/156-native-channel-deployment.md)

## 能力与下一步

E151 群聊 4.32 秒（11,674 字节）、私聊 3.68 秒（9,932 字节），两条 Ogg/Opus 单声道原件均完整解码、进入独立 consumer 的 ready 队列，并在钉钉客户端播放。固定 DWS v1.0.67 的 `audio` 按文件发送。两路各转发原语音一次，都只得到文字 `[语音]`，资源数为 0，客户端没有播放控件。尚无可用的普通账号原生语音创建入口；发音频可用已验的 WAV 文件。需要新的官方普通账号创建契约，才有条件继续核验群和私聊原生出站。[步骤和结果](../../docs/151-native-voice-and-image-saving.md)

E151 用原 E134 两条图文消息完成了会话文件查看器逐图保存、磁盘打开及 SHA-256 核对。E011/E146 的气泡点击失败仍按当时结果记录。R07 核心依据 E095 等通过；任意多文件同一气泡仍缺。E131 Kimi 403 及原 R13 观察结果保留。

原验收表未完为R06及矩阵保留交互格，原生OpenClaw已通过E155双路文件实测；E154旧未知、其余宿主及生命周期分别推进，见[关键路径](CRITICAL_PATH.md)和[总览](../../docs/102-user-requirements-and-roadmap.md)。全部MUST尚未通过，不发布稳定完成声明。

## 操作边界

核心 IM 仍在原 checkout，E153 开发在同项目独立工作树，主Agent统管现场/提交/GitHub，子Agent隔离/tmp；不复制账号数据、不建新产品。仅AIC和原私聊；Kimi两次403无恢复证据不探测/重发/换runtime。未知投递只原key对账。DWS固定v1.0.67，两并发/90+15秒，凭据故障持久暂停。禁止真实auth/login/doctor、Keychain读锁解锁、token复制/reset、权限改变/重启Mac或绕系统限制。共享Setsid bus不杀，无开机自启。

必要维护按AGENTS原顺序，保留新DB行不能用旧备份覆盖。聊天自动化已删除，不重建。所有原始身份/聊天/截图/日志/DB/下载只留local；索引、manifest、暂存隐私和diff门通过后小步提交。
