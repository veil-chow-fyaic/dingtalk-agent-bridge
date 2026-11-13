# DingTalk Agent Bridge

E123：e7d82cc已部署，AIC Kimi和原私聊Pi运行；Pi实际Python/续接/取消/JSON与TXT客户端下载打开通过，Kimi/Codex原验收保持。独立24h观察保留所有维护和故障，项目未完成。[最新验收](docs/124-pi-deployment-and-ui.md)。

使用官方DWS授权的真人账号，将钉钉群聊/私聊接入可替换Agent的通用中间件。CLI、HTTP及持久consumer可独立使用；可选gateway负责本地执行、会话和结果交付。组织、账号、测试群及运行器均为配置，没有新建bot。

**已完成真实群/私聊任务和文件闭环，尚未完成长期可靠性及全部验收。** 2026-11-13最近现场证据E123：e7d82cc的21模块已部署；Pi私聊实际工具/同session/原生取消及文件下载打开通过，AIC保持Kimi。

[需求、产出与下一步](docs/102-user-requirements-and-roadmap.md) · [DWS风险及解决进度](docs/114-dws-risks-and-resolution.md) · [文档导航](docs/README.md)

## 现有能力与边界

- 官方DWS负责身份、通讯/历史、资源和办公；bridge负责多路由/白名单、持久任务/会话/发件箱、原件缓存、文件摘要、幂等及恢复。固定v1.0.67，history-only每15秒补读，不启动Stream消费者或杀共享bus。
- Kimi实际Read/Write/Bash和交付已验；Codex原生中断修复后已部署并完成私聊实际执行/续接/取消/下载UI，Pi E123文字/文件/续接/取消UI已验，图片和OpenClaw未验，不能冒称四者所有能力已支持。通用runtime能力、可信终态和会话兼容性契约已部署。
- 文本、长文、常用文档、PNG/JPEG、WAV/MP4文件以及状态/取消/new有真实证据。原生语音条、独立video、部分引用及单消息多附件仍缺；音视频文件可播放不等于原生协议。
- 原生图片上传仅作固定官方缺口的薄补充：PNG/JPEG≤2MiB，较大走file；输出单文件20MiB。运行器及工具wrapper不是OS沙箱。
- DWS故障持久暂停、两并发、有限调用/清理与归属日志已部署；**钥匙串事故根因和永久修复未定**。重新登录/重启后的恢复不证明根治；普通终端直接DWS不受bridge防护。
- runtime.environment已持久配置并验证：manager无代理变量启动后，群/私聊任务均检查env_ready=true。DWS调用安全保留错误分类/exit/耗时；三服务运行，心跳ACTIVE，无开机自启。当前AIC独立24h只读观察运行中。

## 产出入口

| 内容 | 路径 |
|---|---|
| 产品与安装 | [源码](dingtalk_bridge/) · [六CLI入口](pyproject.toml) · [运行手册](docs/15-service-runbook.md) |
| 接口与配置 | [OpenAPI](api/openapi.json) · [路由模板](config.routes.example.json) · [执行器模板](config.agent.example.json) |
| 社区作业与采用账 | [公开参考](docs/references/README.md) · [CEO深挖](docs/references/ceo-deep-dive.md) · [采用清单](docs/references/adoption-plan.md) |
| 需求与验收 | [PRD](plans/completion/01-PRD.md) · [矩阵](plans/completion/ACCEPTANCE_MATRIX.md) · [最近UI](docs/116-persistent-environment-deployment-ui.md) |
| 当前工作 | [关键路径](plans/completion/CRITICAL_PATH.md) · [TODO](plans/completion/TODO.md) · [AGENTS](AGENTS.md) |
| 开通与故障经验 | [接入经验](docs/11-onboarding-lessons.md) · [风险/根因/恢复方案](docs/114-dws-risks-and-resolution.md) |
| 可复核历史 | [EVIDENCE](plans/completion/EVIDENCE.md) · [推进账本](plans/completion/PROGRESS_LEDGER.md) · [脱敏证据](evidence/) |

CEO提供任务/交付/运行器契约参考，Qwen提供通道接纳边界参考；没有整体移植第三方业务应用。CEO C01摘要、C02发送事实、C03能力/终态、C04会话兼容性已落实，保留来源与MIT许可；C06网络环境构造已由E115/E116采用、部署并真实UI验证。

独立部署需要Python≥3.11/POSIX、自己的官方身份与专用测试会话；macOS已实机验，其他OS未实机认证。不要复制local或套用本机恢复脚本。当前现场仅准AIC测试群及原veil/liev私聊，企业大群/旧群禁止测试；账号/群不是产品固定常量。

以下只读本地文件，不调用DWS；覆盖命令当前返回2表示仍有缺口：

```bash
python3 scripts/review_acceptance.py --require-covered
python3 scripts/verify_handoff.py
```

代码变更按需使用`python3 scripts/run_tests_with_evidence.py`，不重复既有UI发送凑数量。未知投递按原key对账，禁止换key或UI补发。旧reliability-20261111故障/维护保留，未证明当前部署健康24h。

Git只收代码、合成素材、脱敏证据及文档；账号ID、凭据、原聊天/截图、数据库、运行日志和下载件只留local或私有工具记录。E075和E121包均为固定历史版本；Pi版安装已验，最终项目交接仍受MUST缺口约束。分支codex/complete-bridge，仅本地提交，未远程发布。
