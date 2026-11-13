# 文档导航

2026-11-13 E120：当前0c6f2da已部署，AIC Kimi/私聊Codex运行；Codex工具/续接/取消及下载UI通过，心跳ACTIVE。当前独立24h观察保留维护/故障，系统Keychain最初根因与完整验收仍未完成。

[Codex取消修复及UI](121-codex-deployment-and-ui.md) · [官方取消候选（未部署）](117-dws-cancellation-candidate.md) · [持久配置与安全诊断](115-runtime-environment-and-dws-diagnostics.md) · [部署及真实UI](116-persistent-environment-deployment-ui.md)

| 要解决的问题 | 当前入口 |
|---|---|
| 项目做什么、有什么产出、还差什么 | [需求/交付/路线总览](102-user-requirements-and-roadmap.md) |
| DWS究竟哪里坏了、什么已修/未修 | [风险与解决进度](114-dws-risks-and-resolution.md) |
| 开通时怎样避免踩坑 | [通用接入经验](11-onboarding-lessons.md) |
| 安装、运行和恢复 | [运行手册](15-service-runbook.md) · [通用CLI/HTTP/consumer](22-generic-tool-and-consumer.md) |
| 最新真实UI、恢复与保留的失败 | [E120 Codex部署及私聊UI](121-codex-deployment-and-ui.md) · [E116两路持久环境UI](116-persistent-environment-deployment-ui.md) |
| 当前部署代码与离线验证 | [E119 Codex原生中断/374回归](120-codex-native-interrupt.md) · [E115持久环境/诊断](115-runtime-environment-and-dws-diagnostics.md) |
| 官方/GitHub有什么可抄 | [参考目录](references/README.md) · [CEO源码深挖与采用状态](references/ceo-deep-dive.md) · [采用清单](references/adoption-plan.md) · [固定来源](references/catalog.json) |
| 通用设计及官方/自研边界 | [中间件架构](architecture/dingtalk-agent-middleware.md) · [Agent接入面](architecture/agent-integration-map.md) · [身份边界](25-official-boundary-and-scenarios.md) |
| 继续工作的唯一清单 | [AGENTS](../AGENTS.md) · [CURRENT_MISSION](../plans/completion/CURRENT_MISSION.md) · [关键路径](../plans/completion/CRITICAL_PATH.md) · [TODO](../plans/completion/TODO.md) |
| 验收标准和证据 | [PRD](../plans/completion/01-PRD.md) · [矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) · [EVIDENCE](../plans/completion/EVIDENCE.md) |
| 追溯事故/观察/诊断 | [E094系统日志与取消缺口](99-dws-base-failure-diagnosis.md) · [E111续期研究](112-dws-refresh-and-reboot-review.md) · [Codex超时](108-codex-cli-timeout-diagnostic.md) · [原24h](105-original-24h-observation.md) |
| 历史纠偏与旧资料 | [执行偏差](../plans/completion/99-执行偏差日志.md) · [旧入口归档](history/through-E076/README.md) · [历史WeCom参照](03-wecom-reference.md) |

architecture保存设计，references保存公开选型及固定来源，编号阶段文档保存当时实现/失败/验证，evidence保存脱敏结果，plans/completion保存同一活动任务。源码在dingtalk_bridge，私有现场在local，不搬动数据库或账号配置来“整理”。

历史文档的“待许可、未部署、下一步”只对当时有效。当前群只允许AIC测试群，原私聊保持，企业大群禁测；心跳ACTIVE。49/14/1及7项MUST未完整，不能用旧文章的成功/失败覆盖当前判定。

- [E119 Codex原生中断与有限清理](120-codex-native-interrupt.md)

- [E120 Codex部署与真实私聊验收](121-codex-deployment-and-ui.md)

- [E121当前版干净交接与回滚边界](122-current-clean-handoff.md)

- [E122 Pi执行器契约与验证](123-pi-runtime-contract.md)
