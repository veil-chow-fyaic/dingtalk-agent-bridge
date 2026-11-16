# 文档导航

工作交接：[HANDOFF](../plans/completion/HANDOFF.md)。E135只读检查修正心跳PAUSED事实并指出R13独立采集缺口；未启动新业务实验。

当前结论只在[需求、交付现状与后续路线](102-user-requirements-and-roadmap.md)汇总；执行动作以[当前任务](../plans/completion/CURRENT_MISSION.md)、[TODO](../plans/completion/TODO.md)和[AGENTS](../AGENTS.md)为准。E132整理文档，E133新增独立IM组合发送，E134于2026-11-16部署2467fe2并补群/私聊真实API及原件证据；组合客户端UI仍未验。

| 要解决的问题 | 阅读入口 |
|---|---|
| 做什么、做到哪里、还差什么 | [当前总览](102-user-requirements-and-roadmap.md) |
| 安装、运行和恢复 | [运行手册](15-service-runbook.md) · [通用接入经验](11-onboarding-lessons.md) |
| 接口、配置和持久消费 | [CLI/HTTP/consumer](22-generic-tool-and-consumer.md) · [中立接入边界](21-existing-runtime-integration.md) · [OpenAPI](../api/openapi.json) |
| 运行器实际支持到哪一步 | [接入表](architecture/agent-integration-map.md) · [中间件架构](architecture/dingtalk-agent-middleware.md) |
| 最新真实UI及保留的失败 | [E130群引用双向](131-group-quote-ui.md) · [E131群双图与Kimi拒绝](132-group-multi-image-and-provider-denial.md) |
| 最近部署 | [E134组合API与部署](135-composition-api-deployment.md)；Pi历史真实UI见[E123](124-pi-deployment-and-ui.md) |
| 尚未完整验收范围 | [E127 OpenClaw薄适配](128-openclaw-adapter.md)（E134代码随包部署、未配置绑定/真实模型UI） · [E128父进程死亡/恢复](129-openclaw-gateway-lifecycle.md) · [E117官方取消候选](117-dws-cancellation-candidate.md) |
| 故障已修什么、还缺什么 | [风险与关闭条件](114-dws-risks-and-resolution.md) · [E124观察收尾](125-observation-closeout-and-qwen-transactions.md) |
| 官方/社区来源与采用情况 | [参考目录](references/README.md) · [采用账](references/adoption-plan.md) · [CEO深挖](references/ceo-deep-dive.md) |
| 执行与验收 | [计划入口](../plans/completion/00-README.md) · [PRD](../plans/completion/01-PRD.md) · [矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) · [最终自检](../plans/completion/10-自检清单.md) |
| 追溯全部文件 | [完整文档索引](INDEX.md) · [证据登记](../plans/completion/EVIDENCE.md) · [推进账本](../plans/completion/PROGRESS_LEDGER.md) · [偏差日志](../plans/completion/99-执行偏差日志.md) |

编号不等于证据ID，例如docs/132对应E131。阶段报告保留其当时版本、失败和下一步，并在页首标明历史范围；其中“当前、暂停、待许可、未接入”均按该报告时点解释，不能作为今天的操作指令。冻结归档和原证据不重写，新增说明不回填历史结果。

[文档索引数据](documentation-index.json)逐文件区分现行手册、阶段报告、验收基线、累计账本、冻结归档和合成素材；[只读文档检查](../scripts/review_documentation.py)核全覆盖、历史正文及入口状态。链接/JSON/SHA由[handoff检查](../scripts/verify_handoff.py)另外核对；文档检查通过不等于产品或现场验收通过。
