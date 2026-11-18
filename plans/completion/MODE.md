# 主Agent负责、隔离并行推进

复用同一项目和 PRD/验收矩阵。核心分支为 `codex/complete-bridge`，新阶段开发分支为 `codex/native-agent-channel`。用户要求sub agents分别实现与测试，主Agent负责整合审查、实际服务/UI、提交和GitHub管理；子Agent只在各自/tmp冻结源码候选工作，不递归派生、不操作真实凭据/服务/聊天。

每段实现、测试或验收后继续下一项可做工作，约45分钟落准确证据和下一步。全部剩余项依赖外部条件时如实保持未完成；不把检查次数、文档数量或等待时长算产品进度。API、原件、客户端呈现、保存打开和执行器任务分别验收。

用户2026-11-17要求整理所有文档并更新GitHub，已取代旧“不远程发布”。上传范围仍排除local及私有原始材料，用户已明确目标`veil-chow-fyaic/dingtalk-agent-bridge`、公开仓库和MIT许可，保留第三方原声明。仓库工程规范不等于全部产品验收通过。

原聊天自动化已删除，不再创建定时任务。原固定观察已自然截止并完成一次审计，结果见[HANDOFF](HANDOFF.md)，不重置旧run或用后续快照补造截止。现状见[总览](../../docs/102-user-requirements-and-roadmap.md)，执行顺序见[关键路径](CRITICAL_PATH.md)。现场范围及认证/系统禁令见[AGENTS](../../AGENTS.md)。
