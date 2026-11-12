# 文档导航

当前选型以公开 GitHub/钉钉官方实现为先，默认 DWS 授权真人账号。历史编号文档保留原证据，不把旧“下一步”当当前操作指令。

| 目的 | 入口 |
|---|---|
| 最新代码/部署 | [CEO发送凭据修复E102与真实UI E103](106-send-evidence-contract.md) |
| 最新真实UI与观察终检 | [群长文与控制E100](104-aic-group-long-text-and-controls.md) · [原24h记录E101](105-original-24h-observation.md) |
| 用户需求、真实进度、接下来做什么 | [E097统一复盘与路线](102-user-requirements-and-roadmap.md) · [CEO源码深挖](references/ceo-deep-dive.md) |
| 先看现成项目与采用顺序 | [公开参考目录](references/README.md) · [逐项采用清单](references/adoption-plan.md) · [固定来源 catalog](references/catalog.json) |
| 了解中间件和身份边界 | [架构与真人账号](architecture/dingtalk-agent-middleware.md) · [Agent 官方接入面](architecture/agent-integration-map.md) |
| 查当前任务与操作范围 | [AGENTS](../AGENTS.md) · [CURRENT_MISSION](../plans/completion/CURRENT_MISSION.md) · [关键路径](../plans/completion/CRITICAL_PATH.md) |
| 查已实现和未验收项 | [PRD](../plans/completion/01-PRD.md) · [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) · [EVIDENCE](../plans/completion/EVIDENCE.md) |
| 查产品接口 | [通用 CLI/HTTP/consumer](22-generic-tool-and-consumer.md) · [官方/自研边界](25-official-boundary-and-scenarios.md) |
| 查当前恢复与事故事实 | [主线复盘](98-channel-mainline-and-reuse-review.md) · [事故记录](87-authentication-popup-incident.md) · [E095实际恢复及新群UI](100-aic-group-resume-and-files.md) |
| 追溯旧实现和旧说明 | [旧入口归档](history/through-E076/README.md) · [历史 WeCom 对照](03-wecom-reference.md) · [执行偏差](../plans/completion/99-执行偏差日志.md) |

目录分工：`architecture/` 保存现行设计，`references/` 保存公开参考选型及固定来源，编号文档保存阶段研究/实现/验证，`../evidence/` 保存脱敏结果，`../plans/completion/` 保存唯一活动任务。源代码仍在 `../dingtalk_bridge/`；参考源选摘在不入 Git 的 `local/references/`，不移动运行数据或账号配置。

E095已部署本项目E093冻结源码并恢复两路，新增群TXT/CSV真实UI证据；用户提供登录成功截图。没有部署第三方整套channel，跨设备长期认证与全部MUST仍未完成。

最新原生图片验收：[E096 AIC群PNG](101-aic-group-native-png.md)，真实工具、原生气泡、查看器、下载/系统打开与原件摘要分别取证。
