# 当前接手事实

E155 双路文件验收通过：群聊采用全新独立的商品目录颜色筛选任务，私聊按其真实文件接收证明核定；两路collector的modelAndTransportPassed与accepted均为true。客户端文件分别核对字节、SHA-256及唯一名称，公开记录只保留摘要和长度。 [E155收据](../../evidence/2026-11-19/openclaw-two-route-file-acceptance.json)。

E154旧43出库单的未知投递与附件未提交仍保留当时事实；新筛色任务不是重试，不关闭旧原键，也不补造旧任务交付。

E156：PR #9已合并，实际部署`d444ccf`、26模块及三受管服务已按收据核验；版本、归属和边界见[部署记录](../../docs/156-native-channel-deployment.md)。

首次私聊4B把预期20写成10，客户端下载也确认是10；下一次14B算对20，但与旧输出重名，客户端保存时加了 `(1)`，精确文件名未通过。最终私聊改用未占用的新名称通过，前两次记录仍保留。 [脱敏结果](../../evidence/2026-11-19/openclaw-real-files-and-client-receipts.json)。

2026-11-18，E152。用户已将普通账号原生语音出站暂缓，当前主线是普通账号 IM 与外部 Agent 的对接。社区项目和官方契约已核对。首个交付目标为已有 OpenClaw 用户接入群和私聊，后续分别验证 Hermes、DeepSeek Harness。[E152 适配器调查](../../docs/152-community-agent-adapters.md)

## 版本与证据

- E150历史运输部署检查点：`0e151fb78a61e44cf2d593c58ac559bd9d598f9c` / E150，25模块。当前文档HEAD可能更后，不能冒充部署。
- E150历史已测MIT wheel（不代表E156的26模块安装包）：`865d05154cc61e0011d2333a00f6ff9f86564607ef1e74f04a3c9b5a4eff60ed`；[验证](../../evidence/2026-11-17/native-voice-inbound-validation.json)为源码/Python3.14安装/Python3.11安装各533通过；[首轮失败](../../evidence/2026-11-17/native-voice-inbound-initial.json)保留。
- 本次私有实现/测试/入口调查在`local/native-voice-20261117/`；维护/六库备份/新固定cut/积压/启动来源在`local/native-voice-deployment-20261117/`。该次E150维护核对99任务/240 Agent outbox/session与群Kimi/私聊Pi绑定；E154临时canary阶段已结束；E156实际执行归属和短观察见上方部署记录。
- 原run `parallel-hardening-24h-20261116`固定北京时间2026-11-17 18:29:37.189681结束并已审；审计在`local/observation-reviews/parallel-hardening-20261117/`，原run不修改/重审/补造。原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。
- GitHub公开MIT、受保护main。原本地提交与邮箱规范化公开提交保留等树映射，GitHub合并HEAD/CI测试HEAD另记；最新推送回执在`local/github-publication-20261117/`。不重写原历史、不关闭邮箱隐私、不强推、不跳过检查。

## 能力与下一步

E151 群聊 4.32 秒（11,674 字节）、私聊 3.68 秒（9,932 字节），两条 Ogg/Opus 单声道原件均完整解码、进入独立 consumer 的 ready 队列，并在钉钉客户端播放。固定 DWS v1.0.67 的 `audio` 按文件发送。两路各转发原语音一次，都只得到文字 `[语音]`，资源数为 0，客户端没有播放控件。尚无可用的普通账号原生语音创建入口；发音频可用已验的 WAV 文件。需要新的官方普通账号创建契约，才有条件继续核验群和私聊原生出站。[步骤和结果](../../docs/151-native-voice-and-image-saving.md)

E151 用原 E134 两条图文消息完成了会话文件查看器逐图保存、磁盘打开及 SHA-256 核对。E011/E146 的气泡点击失败仍按当时结果记录。R07 核心依据 E095 等通过；任意多文件同一气泡仍缺。E131 Kimi 403 及原 R13 观察结果保留。

原验收表未完为R06及矩阵保留交互格，原生OpenClaw已通过E155双路文件实测；E154旧未知、其余宿主及生命周期分别推进，见[关键路径](CRITICAL_PATH.md)和[总览](../../docs/102-user-requirements-and-roadmap.md)。全部MUST尚未通过，不发布稳定完成声明。

## 操作边界

核心 IM 仍在原 checkout，E153 开发在同项目独立工作树，主Agent统管现场/提交/GitHub，子Agent隔离/tmp；不复制账号数据、不建新产品。仅AIC和原私聊；Kimi两次403无恢复证据不探测/重发/换runtime。未知投递只原key对账。DWS固定v1.0.67，两并发/90+15秒，凭据故障持久暂停。禁止真实auth/login/doctor、Keychain读锁解锁、token复制/reset、权限改变/重启Mac或绕系统限制。共享Setsid bus不杀，无开机自启。

必要维护按AGENTS原顺序，保留新DB行不能用旧备份覆盖。聊天自动化已删除，不重建。所有原始身份/聊天/截图/日志/DB/下载只留local；索引、manifest、暂存隐私和diff门通过后小步提交。
