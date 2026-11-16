# DingTalk Agent Bridge

项目初衷、已证能力和未完项见[统一总览](docs/102-user-requirements-and-roadmap.md)；继续工作见[任务池](plans/completion/TODO.md)。[HANDOFF](plans/completion/HANDOFF.md)保留交接时点和后续更新，不把历史停止指令当成当前状态。

使用官方 DWS 授权的真人账号，将钉钉群聊、私聊接入可替换 Agent 的通用中间件。CLI、HTTP 和持久 consumer 可独立使用；可选 gateway 管理本地任务、原生会话和结果交付。账号、组织、会话及运行器均通过配置选择。

**已有真实任务和文件交付闭环，项目仍未完成。** 当前结论统一见[需求、进度与下一步](docs/102-user-requirements-and-roadmap.md)。E138（2026-11-16）部署产品 `f322402`，24模块启动来源可追溯、实际短采集通过，新24h观察进行中。E134两路文字＋双PNG组合confirmed及官方下载四原件证据保留。最近真实 UI 仍是 E131，组合客户端呈现/逐图保存尚未验。OpenClaw代码随包部署，尚未绑定或进行真实模型/UI验收。

## 能力与限制

- 官方 DWS 提供身份、通讯、历史、资源及办公；bridge 提供多路由、白名单、持久任务/session/outbox、原件缓存、摘要校验、幂等及恢复。现场固定 DWS v1.0.67、history-only 每15秒补读。
- Kimi、Codex、Pi 各自有真实工具、续接、取消或交付的登记证据，范围见[运行器接入表](docs/architecture/agent-integration-map.md)。E131 的 Kimi Code 订阅访问403使该次任务失败；需既有服务访问恢复的新证据才能继续群模型任务。DWS ready 不代表模型可用。E133按用户要求做了一次最小请求，仍为订阅访问403，无周限额/重置时间信息；这只限制对应模型任务，不阻塞通用IM通道工作。
- 文字、长文、常用文档、PNG/JPEG、WAV/MP4文件和任务控制已有真实样本；群引用双向已过。私聊入站引用、原生语音/独立video、单消息附件组合仍有缺口。文件可播放不等于原生媒体协议。
- E133新增、E134已部署`composition` / `dab send --composition-json`：字面文字＋1–9张有序PNG/JPEG，每张要求原始SHA256且≤2MiB；复用官方Markdown单消息入口。CLI/HTTP独立于runtime，未知结果不自动重传；客户端下载原件仍未验，普通多文件组合仍不支持。见[接口说明](docs/22-generic-tool-and-consumer.md)。
- 原生图片窄补充复用固定官方上传入口：PNG/JPEG≤2MiB，较大走file；单个输出文件≤20MiB。执行器和工具 wrapper 不是 OS 沙箱。
- 受管 DWS 有持久暂停、最多两并发、90秒请求与最多15秒清理。系统钥匙串根因、自然失效刷新和长期可靠性尚未证实；两个旧观察 run 已结束，失败和缺截止证据保留。

## 使用与资料

| 内容 | 入口 |
|---|---|
| 安装、运行、恢复和回滚 | [运行手册](docs/15-service-runbook.md) · [接入经验](docs/11-onboarding-lessons.md) |
| CLI / HTTP / consumer | [接口说明](docs/22-generic-tool-and-consumer.md) · [OpenAPI](api/openapi.json) |
| 独立配置 | [路由模板](config.routes.example.json) · [执行器模板](config.agent.example.json) |
| 现状、缺口和证据 | [当前总览](docs/102-user-requirements-and-roadmap.md) · [PRD](plans/completion/01-PRD.md) · [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) |
| 最近现场 | [E134组合API/部署](docs/135-composition-api-deployment.md) · [E130群引用](docs/131-group-quote-ui.md) · [E131群双图与模型拒绝](docs/132-group-multi-image-and-provider-denial.md) |
| 续作 | [AGENTS](AGENTS.md) · [关键路径](plans/completion/CRITICAL_PATH.md) · [TODO](plans/completion/TODO.md) |
| 全部文档和历史范围 | [导航](docs/README.md) · [完整索引](docs/INDEX.md) · [证据账本](plans/completion/EVIDENCE.md) |
| 官方与社区取舍 | [架构](docs/architecture/dingtalk-agent-middleware.md) · [公开参考](docs/references/README.md) · [采用清单](docs/references/adoption-plan.md) |

需要 Python≥3.11/POSIX；macOS arm64已实机验，其他OS未实机认证。独立使用者配置自己的官方身份和专用会话，不能复制本机local。现场仅准AIC测试群及原veil/liev私聊，企业大群/旧群禁测；这些名称不是产品常量。

以下检查只读本地文件，不调用 DWS；覆盖检查返回2表示尚有缺口：

```bash
python3 scripts/review_documentation.py
python3 scripts/review_acceptance.py --require-covered
python3 scripts/verify_handoff.py
```

代码变更按需执行[测试入口](scripts/run_tests_with_evidence.py)，不重复已过UI发送凑数量。未知投递只按原key核对。Git仅收代码、合成素材、脱敏证据和文档；身份、凭据、原聊天/截图、数据库、日志与下载仅留local。E075/E121交接包各属历史版本，最终当前版交接仍待全部MUST及[最终自检](plans/completion/10-自检清单.md)。原分支本地提交，不远程发布。
