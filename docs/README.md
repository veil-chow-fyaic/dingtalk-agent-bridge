# 文档导航

当前选型以公开 GitHub/钉钉官方实现为先，默认 DWS 授权真人账号。历史编号文档保留原证据，不把旧“下一步”当当前操作指令。

| 目的 | 入口 |
|---|---|
| 先看现成项目与采用顺序 | [公开参考目录](references/README.md) · [逐项采用清单](references/adoption-plan.md) · [固定来源 catalog](references/catalog.json) |
| 了解中间件和身份边界 | [架构与真人账号](architecture/dingtalk-agent-middleware.md) · [Agent 官方接入面](architecture/agent-integration-map.md) |
| 查当前任务与操作范围 | [AGENTS](../AGENTS.md) · [CURRENT_MISSION](../plans/completion/CURRENT_MISSION.md) · [关键路径](../plans/completion/CRITICAL_PATH.md) |
| 查已实现和未验收项 | [PRD](../plans/completion/01-PRD.md) · [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) · [EVIDENCE](../plans/completion/EVIDENCE.md) |
| 查产品接口 | [通用 CLI/HTTP/consumer](22-generic-tool-and-consumer.md) · [官方/自研边界](25-official-boundary-and-scenarios.md) |
| 查当前认证和停机事实 | [主线复盘](98-channel-mainline-and-reuse-review.md) · [事故记录](87-authentication-popup-incident.md) · [尚未授权的恢复提案](97-private-chat-recovery-proposal.md) |
| 追溯旧实现和旧说明 | [旧入口归档](history/through-E076/README.md) · [历史 WeCom 对照](03-wecom-reference.md) · [执行偏差](../plans/completion/99-执行偏差日志.md) |

目录分工：`architecture/` 保存现行设计，`references/` 保存公开参考选型及固定来源，编号文档保存阶段研究/实现/验证，`../evidence/` 保存脱敏结果，`../plans/completion/` 保存唯一活动任务。源代码仍在 `../dingtalk_bridge/`；参考源选摘在不入 Git 的 `local/references/`，不移动运行数据或账号配置。

本轮整理没有新增真实 UI 通过项，没有部署第三方 channel，也没有恢复 DWS 服务。auth login 与跨设备可复用性仍未证解决。
