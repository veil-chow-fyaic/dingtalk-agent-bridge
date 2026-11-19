# 文档导航

已有微信或其他通道的 OpenClaw 可从[同宿主试点指南](resident-openclaw-pilot.md)开始。组织知识、记忆、技能及日常交办的实测范围见[用户任务对照](agent-im-workflows.md)。

按要完成的工作选择入口。第一次使用先运行独立 IM 通道，再按需接入 Agent。当前支持范围统一见[能力总览](102-user-requirements-and-roadmap.md)；[完整索引](INDEX.md)保留全部实现、验收和历史材料。

## 安装与日常使用

| 你要做什么 | 从这里开始 |
|---|---|
| 安装、配置一个会话并完成收发 | [首次使用](getting-started.md) · [身份与组织开通经验](11-onboarding-lessons.md) |
| 通过命令行或 HTTP 收发 | [CLI / HTTP / consumer](22-generic-tool-and-consumer.md) · [OpenAPI](../api/openapi.json) |
| 配置多个账号、群聊或私聊 | [路由模板](../config.routes.example.json) · [配置与迁移](23-continuation-and-migration.md) |
| 持续接收事件和文件原件 | [持久消费边界](22-generic-tool-and-consumer.md#持久消费边界) |
| 接收语音、播放音视频或保存组合图片 | [媒体实测与客户端操作](151-native-voice-and-image-saving.md) · [当前媒体能力](102-user-requirements-and-roadmap.md#实际能力) |
| 配置原生 PNG/JPEG 发送 | [图片上传补充工具](../integrations/dws_image_upload/README.md) |
| 使用离线安装包 | [源码与已测 wheel 的导出、校验和安装](144-offline-release-export.md) |

CLI、HTTP 和 consumer 可独立使用。DWS 身份、会话与资源权限需要操作者自行核实；模板中的会话不是默认组织。未知投递只按原 key 查询和对账，不换键或改用客户端补发。

## 接入 Agent

| 场景 | 文档与验证范围 |
|---|---|
| 已有 OpenClaw Gateway，希望从钉钉交办任务 | [原生通道安装与使用](../integrations/openclaw-channel/README.md) · [双路真实文件验收](155-openclaw-two-route-file-acceptance.md) |
| 使用可选 gateway 调用现有运行器 | [运行器接入表](architecture/agent-integration-map.md) · [接入边界](21-existing-runtime-integration.md) · [执行器配置模板](../config.agent.example.json) |
| 了解 OpenClaw、Hermes、DeepSeek Harness 的接入方式 | [宿主接口与社区方案调查](152-community-agent-adapters.md) |
| 理解通道、宿主和执行器如何分工 | [中间件架构](architecture/dingtalk-agent-middleware.md) · [官方与社区参考](references/README.md) |

原生 OpenClaw 已在既有组织工作区完成群聊、私聊的文件交办、独立两轮会话和钉钉通道断开恢复。内置 CLI 适配另有验证范围。 [组织宿主现场验收](resident-openclaw-pilot.md#现场验收)

## 运行、恢复与排错

| 问题 | 阅读入口 |
|---|---|
| 启停服务、升级、迁移或回滚 | [运行手册](15-service-runbook.md) |
| 凭据故障、进程暂停、超时或未知投递 | [风险与恢复条件](114-dws-risks-and-resolution.md) · [受管调用边界](88-dws-process-containment.md) |
| 核对部署版本、服务归属和短观察 | [最近部署记录](156-native-channel-deployment.md) |
| 了解正常自动续期与未验证异常 | [正常续期实测](47-natural-auth-rollover.md) · [当前可靠性范围](ROADMAP.md#r13原观察错误恢复与续期分项判定) |
| 处理安全问题或提交私密漏洞报告 | [安全说明](../SECURITY.md) |

普通 history 业务错误与凭据/受管进程持久暂停的处理不同。部署版本、文档 HEAD、已测包和宿主状态分别记录；一个服务可达或一次测试通过不能代替真实接收确认。

## 开发与维护

| 工作 | 阅读入口 |
|---|---|
| 提交代码或文档 | [贡献指南](../CONTRIBUTING.md) · [变更记录](../CHANGELOG.md) · [仓库约定](../AGENTS.md) |
| 查看下一阶段工作 | [路线图](ROADMAP.md) · [当前任务](../plans/completion/CURRENT_MISSION.md) · [活动清单](../plans/completion/TODO.md) |
| 接手维护 | [HANDOFF](../plans/completion/HANDOFF.md) · [关键路径](../plans/completion/CRITICAL_PATH.md) |
| 理解实现采用了哪些参考 | [参考目录](references/README.md) · [采用清单](references/adoption-plan.md) |
| 检查文档、验收声明与提交范围 | [文档检查](../scripts/review_documentation.py) · [验收检查](../scripts/review_acceptance.py) · [清单检查](../scripts/verify_handoff.py) · [测试入口](../scripts/run_tests_with_evidence.py) |

贡献者在自己的检出中工作；仓库约定中原维护工作区的绝对路径与现场身份只适用于原维护现场。不要复制账号数据、聊天、截图、数据库或下载材料到提交中。

## 验收与历史证据

[原始 PRD](../plans/completion/01-PRD.md)、[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)与[最终自检](../plans/completion/10-自检清单.md)保存原判据。项目尚未通过全部媒体验收；已验证能力和剩余范围以[总览](102-user-requirements-and-roadmap.md)为准。

| 要核对的事实 | 记录 |
|---|---|
| 原生 OpenClaw 双路文件、真实模型与客户端接收 | [成功样本](155-openclaw-two-route-file-acceptance.md) · [保留的错误、重名与未知投递](154-openclaw-real-files-and-client-receipts.md) |
| 原生语音入站、转发限制和四张原图保存 | [真实客户端媒体验证](151-native-voice-and-image-saving.md) |
| 最近合并、实际部署、26模块与服务归属 | [部署收据与范围](156-native-channel-deployment.md) |
| 历史安装验证、24小时运行错误与恢复 | [部署与观察审计](150-native-voice-and-acceptance-scope.md) · [早期观察收尾](125-observation-closeout-and-qwen-transactions.md) |
| 托管 CI、启动故障与修复 | [公开仓库、平台检查与根因记录](149-github-public-launch-and-ci.md) |
| 更早的实现和实验 | [完整索引](INDEX.md) · [证据登记](../plans/completion/EVIDENCE.md) · [推进账本](../plans/completion/PROGRESS_LEDGER.md) · [执行偏差](../plans/completion/99-执行偏差日志.md) |

[索引数据](documentation-index.json)区分现行说明、阶段历史、验收基线与累计账本。历史页中的“当前、下一步、暂停”只描述当时情况，不是今天的操作指令。后续成功不改写旧失败或未知投递，合成测试不替代真实模型、客户端下载或长期运行证据。
